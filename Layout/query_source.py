"""Resolve named layout sources against the project's physical evidence."""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile

from Layout.project import ROOT, config, evidence

DESIGN = Path("Layout/design/manifest.json")
CURRENT = Path("Layout/results/current.json")
PROFILE = Path("Layout/specs/layout-query-t28.json")
CACHE = Path("work/layout/query-inputs")
ARTIFACTS = {"manifest": "manifest.json", "gds": "fixture.gds", "cdl": "reference.cdl"}
SELECTORS = ("comparator/current", "cdac/review", "cdac/filled")


class SourceMismatch(ValueError):
    """A recorded identity or hash disagrees with the selected source."""


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def require_match(field, actual, expected):
    if actual != expected:
        raise SourceMismatch(f"{field} — expected {expected!r}, found {actual!r}")


def select(root, key):
    design = read_json(root / DESIGN)
    module, variant = key.split("/")
    cell = design["cells"][module]
    if module == "comparator":
        report_path = Path(cell["report"])
        report = read_json(root / report_path)
        current = read_json(root / CURRENT)[module]
        identity, view, top = cell["core_evidence"], cell["view"], cell["core"]
        require_match("Current comparator evidence", current["physical_evidence"], identity)
        require_match("Comparator report evidence", report["physical_evidence"], identity)
        require_match("Comparator report cell", report["core"], top)
        require_match("Comparator report geometry", report["geometry_sha256"], current["geometry_sha256"])
        hashes = {"gds": report["gds_sha256"]}
        geometry = current["geometry_sha256"]
    else:
        review = cell["paired_review"]
        report_path = Path(review["report"])
        report = read_json(root / report_path)
        top = cell["filled"]
        require_match("CDAC report cell", report["cell"], top)
        hashes = {"cdl": report["independent_reference_cdl_sha256"]}
        if variant == "review":
            identity, view = review["physical_evidence"], review["view"]
            require_match("CDAC review evidence", report["official_verification_evidence"], identity)
            require_match("CDAC review view", report["view"], view)
            hashes["gds"] = report["independent_review_stream_sha256"]
            geometry = report["published_geometry_sha256"][top]
        else:
            current = read_json(root / CURRENT)[module]
            identity, view = current["physical_evidence"], current["view"]
            hashes["gds"] = current["gds_sha256"]
            geometry = current["functional_geometry_sha256"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,55}", identity):
        raise ValueError("Invalid physical evidence identity")
    target = {
        "library": report["library"], "cell": top, "view": view, "technology": design["technology"],
    }
    record = {
        "id": identity,
        "scope": "combined_fill_evidence" if variant == "filled" else "prefill_stream",
        "top": top,
    }
    authorities = [DESIGN, report_path]
    if variant != "review":
        authorities.append(CURRENT)
    if variant == "filled":
        record["trial_evidence"] = current["trial_evidence"]
        record["functional_geometry_sha256"] = geometry
    else:
        record["geometry_sha256"] = geometry
    return target, record, hashes, set(cell.get("fill_masters", ())), authorities


def validate_bundle(directory, target, record, hashes, fill_masters):
    manifest = read_json(directory / ARTIFACTS["manifest"])
    identity = record["id"]
    if manifest.get("error"):
        raise SourceMismatch(f"Physical evidence {identity} contains a run error")
    require_match("GDS top", manifest["top"], record["top"])
    require_match("Recorded GDS SHA256", manifest["gds"]["sha256"], hashes["gds"])
    view = manifest.get("oa_view", "layout")
    fills = set(manifest["gds"]["labels"]).intersection(fill_masters)
    if record["scope"] == "combined_fill_evidence":
        require_match("Fill derivation stage", manifest["derived_from"]["stage"], "combined")
        require_match("Fill trial source", manifest["derived_from"]["plan_evidence"], record["trial_evidence"])
        require_match("Functional geometry", manifest["functional_geometry_sha256"], record["functional_geometry_sha256"])
        require_match("Utility fill masters", sorted(fills), sorted(fill_masters))
    else:
        require_match("Stream library", manifest["library"], target["library"])
        require_match("Stream view", view, target["view"])
        require_match("Stream geometry", manifest["gds"]["structural_sha256"][record["top"]], record["geometry_sha256"])
        require_match("Utility fill in prefill stream", sorted(fills), [])

    references = {
        value for name, value in manifest.get("source_sha256", {}).items()
        if name.lower().endswith(".cdl")
    }
    if "cdl" in hashes:
        if references and hashes["cdl"] not in references:
            raise SourceMismatch("Recorded CDL disagrees with the independent reference")
        reference = hashes["cdl"]
    elif len(references) == 1:
        reference = references.pop()
    else:
        raise SourceMismatch("Physical evidence must identify the saved reference CDL")
    verified = {"gds": hashes["gds"], "cdl": reference}
    for role, expected in verified.items():
        require_match(f"{role.upper()} file SHA256", sha256(directory / ARTIFACTS[role]), expected)
    stream = {
        "library": manifest["library"], "view": view,
        "geometry_sha256": manifest["gds"]["structural_sha256"][record["top"]],
    }
    return stream, verified


def fetch_bundle(identity, directory):
    remote = evidence(identity)
    names = tuple(ARTIFACTS.values())
    command = "tar -chf - -C " + shlex.quote(remote) + " " + " ".join(names) + "\n"
    with tempfile.TemporaryFile() as archive:
        subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", config()["host"], "bash -s"],
            input=command.encode(), stdout=archive, stderr=subprocess.PIPE, timeout=40, check=True,
        )
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode="r:") as bundle:
            members = bundle.getmembers()
            if sorted(member.name for member in members) != sorted(names) or any(
                not member.isfile() for member in members
            ):
                raise SourceMismatch("Evidence transfer lacks a unique regular file for each query input")
            for name in names:
                with bundle.extractfile(name) as source, (directory / name).open("xb") as output:
                    shutil.copyfileobj(source, output)


def collect_bundle(directory, target, record, hashes, fill_masters):
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory.parent, prefix=".collect-") as staging:
        stage = Path(staging)
        fetch_bundle(record["id"], stage)
        validate_bundle(stage, target, record, hashes, fill_masters)
        # Check any existing files before publishing missing files.
        directory.mkdir(exist_ok=True)
        for name in ARTIFACTS.values():
            path = directory / name
            if path.exists():
                require_match(name, sha256(path), sha256(stage / name))
        for name in ARTIFACTS.values():
            path = directory / name
            try:
                os.link(stage / name, path)
            except FileExistsError:
                require_match(name, sha256(path), sha256(stage / name))


def resolve(selector, *, root=ROOT, collect=False):
    root = root.resolve()
    key = selector.strip().lower()
    if key == "cdac/current":
        key = "cdac/filled"
    matches = [item for item in SELECTORS if item == key or item.split("/")[0] == key]
    result = {"format": 1, "selector": selector}
    if len(matches) > 1:
        return dict(result, status="ambiguous", candidates=matches), 3
    if not matches:
        return dict(result, status="unknown_selector", candidates=list(SELECTORS)), 2
    key = matches[0]
    try:
        target, record, hashes, fill_masters, authorities = select(root, key)
        directory = root / CACHE / record["id"]
        paths = {role: directory / name for role, name in ARTIFACTS.items()}
        paths["profile"] = root / PROFILE
        result.update(
            selected=key, target=target, evidence=record,
            authorities=[str(root / path) for path in authorities],
            files={role: {"path": str(path)} for role, path in paths.items()},
        )
        missing = [role for role, path in paths.items() if not path.is_file()]
        if collect and set(missing).intersection(ARTIFACTS):
            collect_bundle(directory, target, record, hashes, fill_masters)
            missing = [role for role, path in paths.items() if not path.is_file()]
        if missing:
            return dict(result, status="missing", missing=missing), 3
        stream, verified = validate_bundle(directory, target, record, hashes, fill_masters)
        record.update(stream)
        verified.update(profile=sha256(paths["profile"]), manifest=sha256(paths["manifest"]))
        for role, checksum in verified.items():
            result["files"][role]["sha256"] = checksum
        return dict(result, status="resolved"), 0
    except SourceMismatch as err:
        return dict(result, status="mismatch", error=str(err)), 1
    except FileNotFoundError as err:
        return dict(result, status="missing", missing=[str(err.filename)]), 3
    except subprocess.CalledProcessError as err:
        message = (err.stderr or b"").decode(errors="replace").strip()
        return dict(result, status="error", error=message or f"Evidence transfer exited {err.returncode}"), 2
    except (KeyError, ValueError, OSError, subprocess.TimeoutExpired, tarfile.TarError) as err:
        return dict(result, status="error", error=str(err)), 2
