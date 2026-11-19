"""Build a new gate-driver view and verify its native CDAC integration."""

from __future__ import print_function

import argparse
import fcntl
import glob
import json
import os
import re
import shutil
from os.path import join

import run_physical as native
import workspace


STANDARD_LIBRARY = "tcbn28hpcplusbwp12t30p140"
STANDARD_SPICE = (
    "/home/process/tsmc28n/STD_CELL/" + STANDARD_LIBRARY
    + "_190a/*_spi/TSMCHOME/digital/Back_End/spice/*/*.spi"
)
INPUTS = (
    "build.il", "intent.json", "driver-leaves.cdl", "reference_driver.il",
    "sar_timing.il", "cdac-full-reference.cdl",
)
ADVISORIES = {"DIODMY_L:WARNING", "IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1"}


def independent_reference(out):
    source = native.read(join(out, "driver-leaves.cdl"))
    installed, = glob.glob(STANDARD_SPICE)
    library = native.read(installed)
    definitions = []
    for master in sorted(set(re.findall(r"\b[A-Z0-9_]+BWP12T30P140\b", source))):
        match = re.search(r"(?ims)^\.subckt[ \t]+" + master + r"\s.*?^\.ends[^\n]*", library)
        if not match:
            raise ValueError("Missing installed transistor reference for " + master)
        definitions.append(match.group(0))
    cdac = native.read(join(out, "cdac-full-reference.cdl"))
    native.put(join(out, "reference.cdl"), ("\n".join(definitions) + "\n" + cdac + "\n" + source).encode("ascii"))
    return native.sha(native.raw(installed))


def physical(config, staging, out, identity, from_stream, default_supplies):
    for path in INPUTS + ("run_reference_driver.py", "run_physical.py"):
        shutil.copyfile(join(staging, path), join(out, path))
    intent = json.loads(native.read(join(out, "intent.json")))
    top, view = intent["top"], intent["view"]
    cdac = intent["cdac"]
    cdslib = native.read(join(config["runtime"], "cds.lib"))
    selector = r"(?m)^DEFINE[ \t]+" + STANDARD_LIBRARY + r"[ \t]+[^\n]+"
    if not re.search(selector, cdslib):
        parent = native.read("/home/dmanager/shared_lib/TSMC28/cds.lib")
        cdslib += "\n" + re.search(selector, parent).group(0) + "\n"
    native.put(join(out, "cds.lib"), cdslib.encode("ascii"))
    distributed = () if default_supplies else ("VDD", "VSS")
    result = dict(id=identity, library=native.LIB, case="reference-driver", top=top, oa_view=view,
                  checks={}, decks={}, target_bits=intent["bits"], ports=intent["combined_ports"],
                  distributed_supplies=distributed,
                  input_hashes={p: native.sha(native.raw(join(out, p))) for p in INPUTS},
                  verifier_sha256=native.sha(native.raw(join(out, "run_physical.py"))))
    gds = join(out, "fixture.gds")

    def save():
        path = join(out, "manifest.json")
        native.put(path + ".next", (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("ascii"))
        os.rename(path + ".next", path)

    def run(name, setup, args, directory, limit):
        result["active_step"] = name
        save()
        rc = native.tool(setup, args, directory, join(out, name + ".console"), limit)
        if rc:
            raise RuntimeError("%s exited %d" % (name, rc))

    def stream(name, layout_view, destination, label):
        run(label, native.CADENCE, [
            "strmout", "-library", native.LIB, "-topCell", name, "-view", layout_view,
            "-strmFile", destination, "-cdslib", join(out, "cds.lib"),
            "-layerMap", join(native.PDK, "tsmcN28.layermap"), "-runDir", out,
            "-logFile", join(out, label + ".log"), "-convertPin", "geometry", "-convertPcellPin", "geometry",
        ], out, 180)

    try:
        result["standard_library_sha256"] = independent_reference(out)
        result["reference_sha256"] = native.sha(native.raw(join(out, "reference.cdl")))
        source_gds = join(out, "source_cdac.gds")
        if from_stream:
            prior = workspace.evidence(from_stream)
            record = json.loads(native.read(join(prior, "manifest.json")))
            if ("REFERENCE_BUILD_OK" not in native.read(join(prior, "oa.console"))
                or result["input_hashes"] != record["input_hashes"]
                or native.sha(native.raw(join(prior, "fixture.gds"))) != record["gds"]["sha256"]):
                raise ValueError("The native stream does not match its frozen inputs and OA readback")
            shutil.copyfile(join(prior, "fixture.gds"), gds)
            shutil.copyfile(join(prior, "source_cdac.gds"), source_gds)
            result["stream_source"] = from_stream
        else:
            run("oa", native.CADENCE, [
                "virtuoso", "-nograph", "-nocdsinit", "-log", join(out, "build.log"),
                "-restore", join(out, "build.il"),
            ], out, 180)
            if "REFERENCE_BUILD_OK" not in native.read(join(out, "oa.console")):
                raise ValueError("No saved driver and CDAC integration readback")
            stream(top, view, gds, "stream")
            stream(cdac, intent["cdac_view"], source_gds, "source")
        result["gds"] = native.gds_identity(gds)
        original = native.gds_identity(source_gds)
        result["source_cdac_gds_sha256"] = original["sha256"]
        original_cells = original["structural_sha256"]
        combined_cells = result["gds"]["structural_sha256"]
        # XStream assigns fresh names to evaluated PCells. The root digest
        # already includes the recursive element geometry of every descendant.
        if combined_cells.get(cdac) != original_cells[cdac]:
            raise ValueError("Stream changed the saved CDAC hierarchy")
        result["source_cdac_geometry_sha256"] = original_cells[cdac]
        if sorted(result["gds"]["labels"][top]) != sorted(intent["combined_ports"]):
            raise ValueError("Integration stream port labels differ from its circuit interface")

        for step in ("drc", "lvs", "pex"):
            work = join(out, step)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            result["decks"][step] = native.prepare_deck(work, step, top, distributed_supplies=distributed)
            if step == "drc":
                run(step, native.CALIBRE, ["calibre", "-drc", "-hier", "-turbo", "4", "-nowait", "drc.svrf"], work, 480)
                rules = native.drc_rules(join(work, "DRC_RES.db"))
                total = re.search(r"TOTAL DRC Results Generated:\s*(\d+)", native.read(join(work, "DRC.rep")), re.I)
                if not total or sum(rules.values()) != int(total.group(1)):
                    raise ValueError("DRC rule counts disagree")
                result["checks"][step] = dict(markers_by_rule=rules, markers=int(total.group(1)),
                                               advisories=sorted(set(rules) & ADVISORIES))
            elif step == "lvs":
                run(step, native.CALIBRE, ["calibre", "-lvs", "-hier", "-turbo", "4", "-nowait", "lvs.svrf"], work, 480)
                verdict = re.search(r"(?m)^\s+(CORRECT|INCORRECT)[ \t]+" + top + r"[ \t]+" + top + r"[ \t]*$",
                                    native.read(join(work, "lvs.rep")))
                result["checks"][step] = dict(verdict=verdict.group(1) if verdict else "NO_VERDICT")
                if result["checks"][step]["verdict"] != "CORRECT":
                    raise ValueError("The integrated circuit does not match the independent LVS reference")
            else:
                for label, flags in (("phdb", ["-phdb", "-turbo", "4"]),
                                     ("rcc", ["-pdb", "-rcc", "-turbo", "4"]),
                                     ("format", ["-fmt", "-all"])):
                    run(label, native.CALIBRE, ["calibre", "-xrc"] + flags + ["-nowait", "pex.svrf"], work, 900)
                extracted = join(work, "extracted.scs")
                result["checks"][step] = dict(
                    sha256=native.sha(native.raw(extracted)),
                    bytes=os.stat(extracted).st_size,
                    companion_sha256={name: native.sha(native.raw(join(work, name)))
                                      for name in os.listdir(work) if name.startswith("extracted.scs.")},
                )
            save()
        result["active_step"] = "complete"
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    parser.add_argument("--from-stream")
    parser.add_argument("--default-supplies", action="store_true")
    args = parser.parse_args()
    config = workspace.paths()
    staging = workspace.state(args.identity + ".reference-inputs")
    if os.path.dirname(os.path.realpath(staging)) != config["state"]:
        raise ValueError("The frozen inputs must belong to the native workspace")
    with open(config["lock"], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out = workspace.evidence(args.identity, create=True)
        physical(config, staging, out, args.identity, args.from_stream, args.default_supplies)


if __name__ == "__main__":
    main()
