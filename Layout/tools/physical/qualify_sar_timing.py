"""Read a published SAR OA view, stream it, and run the native T28 checks."""

from __future__ import print_function

import argparse
import fcntl
import glob
import json
import os
from os.path import join
import re
import shutil

import run_physical as native
import workspace


CORE = "sar8_sar_timing_core"
WRAPPER = "sar8_sar_timing"
STD = "tcbn28hpcplusbwp12t30p140"
SOURCE_LIB = "/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/*_spi/TSMCHOME/digital/Back_End/spice/*/*.spi"
DRC_ADVISORIES = {"DIODMY_L:WARNING", "IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1"}


def reference(runtime, output, top, array_source=None):
    paths = glob.glob(SOURCE_LIB)
    if len(paths) != 1:
        raise ValueError("Cannot identify the installed T28 standard-cell SPICE")
    library = native.read(paths[0])
    source = native.read(array_source or join(runtime, "sar-leaves.cdl"))
    blocks = []
    cells = sorted(set(re.findall(r"(?im)^X\S+[^\n]*[ \t]([A-Z0-9_]+)BWP12T30P140[ \t]*$", source)))
    for cell in cells:
        pattern = r"(?ims)^\.subckt[ \t]+" + cell + r"BWP12T30P140\s.*?^\.ends[^\n]*"
        match = re.search(pattern, library)
        if not match:
            raise ValueError("Missing transistor definition for " + cell)
        blocks.append(match.group(0))
    pins = re.search(r"(?im)^\.subckt[ \t]+" + CORE + r"[ \t]+([^\n]+)", source).group(1)
    if top == WRAPPER:
        source += "\n.SUBCKT %s %s\nXCORE %s %s\n.ENDS %s\n" % (top, pins, pins, CORE, top)
    path = join(output, "reference.cdl")
    with open(path, "w") as stream:
        stream.write("\n".join(blocks) + "\n" + source)
    return pins.split(), native.sha(native.raw(path)), native.sha(native.raw(paths[0]))


def verify(cfg, out, identity, view, top, through, staging=None, defer_top_m9=False, array_decaps=False, library=None, standard_delays=False, rc_corner=None):
    rt = cfg["runtime"]
    library = library or ("SAR_PLACEMENT_WORK" if staging else native.LIB)
    cdl = "standard-leaves.cdl" if standard_delays else "array-leaves.cdl" if array_decaps else None
    pins, source_hash, library_hash = reference(rt, out, top, join(staging or rt, cdl) if cdl else None)
    cds = native.read(join(staging or rt, "cds.lib"))
    if not re.search(r"(?m)^DEFINE[ \t]+" + STD + r"[ \t]", cds):
        site = native.read("/home/dmanager/shared_lib/TSMC28/cds.lib")
        definition = re.search(r"(?m)^DEFINE[ \t]+" + STD + r"[ \t]+[^\n]+", site)
        if not definition:
            raise ValueError("Cannot resolve the native standard-cell OA library")
        cds += "\n" + definition.group(0) + "\n"
    native.put(join(out, "cds.lib"), cds.encode("ascii"))
    args = [
        "strmout",
        "-library",
        library,
        "-topCell",
        top,
        "-view",
        view,
        "-strmFile",
        join(out, "fixture.gds"),
        "-cdslib",
        join(out, "cds.lib"),
        "-layerMap",
        join(native.PDK, "tsmcN28.layermap"),
        "-runDir",
        out,
        "-logFile",
        join(out, "stream.log"),
        "-convertPin",
        "geometry",
        "-convertPcellPin",
        "geometry",
    ]
    report = dict(
        id=identity,
        case="sar-timing",
        library=library,
        top=top,
        oa_view=view,
        reference_sha256=source_hash,
        standard_library_sha256=library_hash,
        checks={},
        decks={},
    )

    def save():
        path = join(out, "manifest.json")
        native.put(path + ".new", (json.dumps(report, indent=2) + "\n").encode("ascii"))
        os.rename(path + ".new", path)

    def run(label, setup, command, cwd, timeout):
        if native.tool(setup, command, cwd, join(out, label + ".console"), timeout):
            raise RuntimeError("Native tool failed at " + label)

    try:
        shutil.copyfile(join(rt, "sar_timing.il"), join(out, "sar_timing.il"))
        audit = (
            'load("sar_timing.il")\nif(errset(stAudit("%s" "%s" "%s") t) then exit(0) else exit(1))\n'
            % (library, top, view)
        )
        native.put(join(out, "readback.il"), audit.encode("ascii"))
        run(
            "oa",
            native.CADENCE,
            [
                "virtuoso",
                "-nograph",
                "-nocdsinit",
                "-restore",
                join(out, "readback.il"),
                "-log",
                join(out, "readback.log"),
            ],
            out,
            120,
        )
        run("stream", native.CADENCE, args, out, 180)
        gds = native.gds_identity(join(out, "fixture.gds"))
        if sorted(gds["labels"].get(top, [])) != sorted(pins):
            raise ValueError("Stream ports differ from the electrical interface")
        report["gds"] = gds
        save()
        for stage in ("drc", "lvs", "pex"):
            if through == "stream":
                break
            work = join(out, stage)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            report["decks"][stage] = native.prepare_deck(work, stage, top, distributed_supplies=("VDD", "VSS"))
            if stage == "pex" and rc_corner:
                from sar_rc_corner import select
                report["interconnect_rc"] = select(work, cfg, native.PDK, join(native.RULES, "rcx"), report["decks"][stage], rc_corner)
            if stage == "drc":
                run(
                    stage,
                    native.CALIBRE,
                    ["calibre", "-drc", "-hier", "-turbo", "4", "-nowait", "drc.svrf"],
                    work,
                    600,
                )
                markers = native.drc_rules(join(work, "DRC_RES.db"))
                count = int(
                    re.search(
                        r"TOTAL DRC Results Generated:\s*(\d+)", native.read(join(work, "DRC.rep")), re.I
                    ).group(1)
                )
                if count != sum(markers.values()):
                    raise ValueError("DRC marker counts disagree")
                blocking = sum(n for rule, n in markers.items() if rule not in DRC_ADVISORIES)
                report["checks"][stage] = {
                    "markers": count,
                    "markers_by_rule": markers,
                    "blocking_markers": blocking,
                    "advisory_markers": count - blocking,
                }
                deferred = markers.get("M9.DN.3", 0) if defer_top_m9 else 0
                if deferred:
                    report["checks"][stage]["deferred_to_full_chip"] = {"M9.DN.3": deferred}
                metadata = dict(
                    identity=identity,
                    view=view,
                    cell=top,
                    library=library,
                    gds_sha256=gds["sha256"],
                    geometry_sha256=gds["structural_sha256"][top],
                    labels=sorted(pins),
                    drc_total=count,
                    rules=markers,
                    drc_deck=report["decks"][stage],
                )
                native.put(join(out, "sar-physical.json"), json.dumps(metadata, indent=2).encode("ascii"))
                if top == WRAPPER and blocking > deferred:
                    raise ValueError("Filled SAR wrapper has %d unresolved local DRC markers" % (blocking - deferred))
            elif stage == "lvs":
                run(
                    stage,
                    native.CALIBRE,
                    ["calibre", "-lvs", "-hier", "-turbo", "4", "-nowait", "lvs.svrf"],
                    work,
                    600,
                )
                verdict = re.search(
                    r"(?m)^\s+(CORRECT|INCORRECT)[ \t]+" + top + r"[ \t]+" + top + r"[ \t]*$",
                    native.read(join(work, "lvs.rep")),
                )
                report["checks"][stage] = {"verdict": verdict.group(1) if verdict else "NO_VERDICT"}
                if not verdict or verdict.group(1) != "CORRECT":
                    raise ValueError("Transistor LVS did not match")
            else:
                for step, options in (
                    ("phdb", ["-phdb", "-turbo", "4"]),
                    ("rcc", ["-pdb", "-rcc", "-turbo", "4"]),
                    ("format", ["-fmt", "-all"]),
                ):
                    run(
                        step,
                        native.CALIBRE,
                        ["calibre", "-xrc"] + options + ["-nowait", "pex.svrf"],
                        work,
                        1800,
                    )
                main = join(work, "extracted.scs")
                parasitics = native.read(main + ".pex")
                rail_resistors = {}
                for rail in ("VDD", "VSS"):
                    models = re.findall(r"(?ims)^subckt PM_[^\s]*%" + rail + r"[ \t]+\(.*?^[ \t]*ends\b", parasitics)
                    if len(models) != 1:
                        raise ValueError("Missing or ambiguous distributed supply model for " + rail)
                    count = len(re.findall(r"(?im)^r\S+[ \t]+\([^\n]+\)[ \t]+resistor[ \t]+r=", models[0]))
                    if not count:
                        raise ValueError("Supply model has no extracted resistance for " + rail)
                    rail_resistors[rail] = count
                report["checks"][stage] = dict(
                    distributed_rail_resistors=rail_resistors,
                    bytes=os.path.getsize(main),
                    sha256=native.sha(native.raw(main)),
                    companion_sha256={
                        f: native.sha(native.raw(join(work, f)))
                        for f in os.listdir(work)
                        if f.startswith("extracted.scs.")
                    },
                )
            save()
            if stage == through:
                break
    except Exception as error:
        report["error"] = str(error)
        save()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    parser.add_argument("--module", choices=("sar-timing", "sar-timing-filled"), default="sar-timing")
    parser.add_argument("--view", required=True)
    parser.add_argument("--staging", help="Use this owned workspace's cds.lib and array reference")
    parser.add_argument("--library", choices=("SAR_PLACEMENT_WORK", native.LIB), help="Use a library mapped in the selected cds.lib")
    parser.add_argument("--defer-top-m9", action="store_true", help="Continue extraction for a fill evaluation with a recorded full-chip M9.DN.3 check")
    parser.add_argument("--array-decaps", action="store_true", help="Use the array CDL with the seven characterized decoupling cells")
    parser.add_argument("--standard-delays", action="store_true", help="Use the default DEL schematic and the matching decoupling-cell CDL")
    parser.add_argument("--through", choices=("stream", "drc", "lvs", "pex"), default="pex")
    parser.add_argument("--rc-corner", choices=("cworst_T", "cbest_T"),
                        help="Select the foundry 1P9M 6X1Z1U capacitance corner for the SAR extraction")
    args = parser.parse_args()
    if args.rc_corner and args.through != "pex":
        parser.error("--rc-corner requires --through pex")
    if not re.match(r"\Alayout[a-z0-9_]*\Z", args.view):
        raise ValueError("Invalid SAR OA view")
    cfg = workspace.paths()
    if args.staging:
        args.staging = os.path.realpath(args.staging)
        if os.path.dirname(args.staging) != cfg["state"] or os.stat(args.staging).st_uid != os.getuid():
            raise ValueError("Invalid private layout workspace")
    wrapper = args.module == "sar-timing-filled"
    if args.library == "SAR_PLACEMENT_WORK" and not args.staging:
        raise ValueError("Private OA views require their staging cds.lib")
    if args.defer_top_m9 and not (wrapper and args.staging):
        raise ValueError("Top-level density evaluation requires a filled wrapper and its staging source")
    with open(cfg["lock"], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out = workspace.evidence(args.identity, create=True)
        verify(
            cfg,
            out,
            args.identity,
            args.view,
            WRAPPER if wrapper else CORE,
            args.through,
            args.staging,
            args.defer_top_m9,
            args.array_decaps,
            args.library,
            args.standard_delays,
            args.rc_corner,
        )


if __name__ == "__main__":
    main()
