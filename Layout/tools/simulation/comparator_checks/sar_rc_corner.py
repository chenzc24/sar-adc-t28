"""Select the SAR metal capacitance corner in a private Calibre xRC job deck."""

from __future__ import print_function

import hashlib
import json
import os
import tarfile


CORNERS = ("cworst_T", "cbest_T")
PACKAGE = "RC_xCalibre_crn28hpc+_1p09m+ut-alrdl_6x1z1u_"


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def mapped_rules(stream, mapping, output=None):
    source = hashlib.sha256()
    applied = hashlib.sha256()
    count = 0
    for line in stream:
        source.update(line)
        if line == b"include xrc_mapping\n":
            line = ("include " + mapping + "\n").encode("ascii")
            count += 1
        applied.update(line)
        if output is not None:
            output.write(line)
    if count != 1:
        raise ValueError("Expected one foundry xRC layer-map include")
    return source.hexdigest(), applied.hexdigest()


def installed_rules(corner, cfg, pdk, site):
    """Run under the physical workspace lock and keep shared PDK files read-only."""
    if corner not in CORNERS:
        raise ValueError("Unsupported SAR capacitance corner: " + corner)
    join = os.path.join
    package = join(os.path.dirname(os.path.dirname(pdk)), "Calibre_xRC1p9m")
    archive = join(package, PACKAGE + corner + ".tar.gz")
    site_rules, mapping = join(site, "rules"), join(site, "xrc_mapping")
    typical = join(package, PACKAGE + "typical", "rules")
    # The archive identity names the cache. A changed foundry archive produces a new job input.
    archive_sha = file_hash(archive)
    cache = join(cfg["state"], "sar-xrc-" + archive_sha[:16])
    if not os.path.isdir(cache):
        os.mkdir(cache, 0o700)
    if os.path.realpath(cache) != cache or os.stat(cache).st_uid != os.getuid():
        raise ValueError("Unowned SAR xRC cache")
    target = join(cache, corner + ".svrf")
    receipt = target + ".json"
    site_hash = file_hash(site_rules)
    mapping_hash = file_hash(mapping)
    if os.path.isfile(receipt):
        with open(receipt) as stream:
            info = json.load(stream)
        if (info["archive_sha256"] != archive_sha or info["effective_rules_sha256"] != file_hash(target)
                or info["mapping_sha256"] != mapping_hash or info["typical_lab_equivalent_sha256"] != site_hash
                or info["typical_foundry_rules_sha256"] != file_hash(typical)):
            raise ValueError("Cached SAR corner differs from the installed package or lab mapping")
        return target, info
    with open(typical, "rb") as stream:
        typical_sha, mapped_typical = mapped_rules(stream, mapping)
    if mapped_typical != site_hash:
        raise ValueError("The foundry typical rules do not reproduce the installed lab rules")
    matches = 0
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if member.name != "rules":
                continue
            if matches or not member.isfile():
                raise ValueError("Ambiguous foundry rules member")
            with open(target + ".tmp", "wb") as output:
                source_sha, effective_sha = mapped_rules(tar.extractfile(member), mapping, output)
            matches += 1
    if matches != 1 or source_sha == typical_sha:
        raise ValueError("Missing or indistinguishable SAR corner rules")
    os.rename(target + ".tmp", target)
    info = dict(corner=corner, stack="1P9M 6X1Z1U UT-AlRDL", package_directory=package,
                archive=archive, archive_sha256=archive_sha, member="rules", foundry_rules_sha256=source_sha,
                effective_rules_sha256=effective_sha, typical_foundry_rules_sha256=typical_sha,
                typical_lab_equivalent_sha256=site_hash, mapping_sha256=mapping_hash)
    with open(receipt + ".tmp", "w") as stream:
        json.dump(info, stream, indent=2)
        stream.write("\n")
    os.rename(receipt + ".tmp", receipt)
    return target, info


def select(work, cfg, pdk, site, metadata, corner):
    path = os.path.join(work, "pex.svrf")
    with open(path, "rb") as stream:
        deck = stream.read()
    original = ("include " + os.path.join(site, "rules") + "\n").encode("ascii")
    if hashlib.sha256(deck).hexdigest() != metadata["job_sha256"] or deck.count(original) != 1:
        raise ValueError("Unrecognized Calibre extraction deck or technology include")
    target, info = installed_rules(corner, cfg, pdk, site)
    updated = deck.replace(original, ("include " + target + "\n").encode("ascii"))
    with open(path + ".tmp", "wb") as stream:
        stream.write(updated)
    os.rename(path + ".tmp", path)
    metadata["job_sha256"] = hashlib.sha256(updated).hexdigest()
    metadata["support"]["interconnect_rc"] = info
    return info
