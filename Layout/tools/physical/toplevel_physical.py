"""Native checks of the ADC core top cell sar8_adc_core, or of its fill wrapper sar8_adc_core_filled (--top), run
inside its own evidence directory.

The launcher (Layout/design/toplevel_route.py) uploads this file with run_physical.py and workspace.py,
the cds.lib and, for a candidate, the merged GDS. The stream comes either from a saved OA view
(strmout under the shared layout lock) or from the uploaded GDS. Stages: drc (Calibre DRC with the
installed cell deck), spice (hierarchical layout netlist with the installed LVS deck, no comparison),
pex (flat Calibre xRC RC and coupling extraction, typical deck), lvs (hierarchical Calibre LVS against an
uploaded source netlist, block masters as HCELLs, optional VIRTUAL CONNECT NAME nets; run in its own job).
Compatible with the host's Python 2.
"""

from __future__ import print_function

import argparse
import fcntl
import json
import os
from os.path import isfile, join
import re
import shutil
import sys

sys.path.insert(0, os.getcwd())
import run_physical as native  # noqa: E402

TOP = "sar8_adc_core"
STAGES = ("stream", "drc", "spice", "pex", "lvs")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--view", help="saved OA view of sar8_adc_core to stream")
    source.add_argument("--gds", help="uploaded GDS in the evidence directory")
    ap.add_argument("--lock", required=True, help="shared layout lock, held only while strmout reads OA")
    ap.add_argument("--through", choices=STAGES, default="drc")
    ap.add_argument("--stages", help="comma-separated subset of drc,spice,pex to run (default: all through --through)")
    ap.add_argument("--hcells", help="file with one block master per line, kept as a subcircuit in the netlist")
    ap.add_argument("--source", help="uploaded LVS source netlist (CDL) for the lvs stage")
    ap.add_argument("--virtual", default="", help="comma-separated net names for VIRTUAL CONNECT NAME (lvs)")
    ap.add_argument("--top", default=TOP, help="top cell (default %s; the fill wrapper sar8_adc_core_filled)" % TOP)
    args = ap.parse_args()
    cell = args.top
    if not re.match(r"\A(sar8_adc_core(_filled)?|sar8_chip_routes)\Z", cell):
        raise ValueError("Unexpected top cell")
    out = os.getcwd()
    if os.path.basename(out) != args.identity:
        raise ValueError("Run inside the evidence directory of " + args.identity)
    wanted = STAGES[1:min(STAGES.index(args.through), STAGES.index("pex")) + 1]
    if args.stages:
        wanted = tuple(s for s in args.stages.split(",") if s)
        if not set(wanted) <= set(STAGES[1:]):
            raise ValueError("Unknown stage in --stages")
    if "lvs" in wanted and (set(wanted) & set(["spice", "pex"]) or not args.source):
        raise ValueError("Run lvs in its own job, with --source")
    report = dict(identity=args.identity, top=cell, library=native.LIB, library_path=native.LIB_PATH,
                  source=dict(view=args.view) if args.view else dict(gds=args.gds), stages=list(wanted),
                  driver_sha256=dict((n, native.sha(native.raw(join(out, n))))
                                     for n in ("toplevel_physical.py", "run_physical.py", "workspace.py", "cds.lib")),
                  checks={}, decks={})
    if args.source:
        report["source_netlist"] = dict(name=args.source, sha256=native.sha(native.raw(join(out, args.source))))

    def save():
        native.put(join(out, "manifest.next"), (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("ascii"))
        os.rename(join(out, "manifest.next"), join(out, "manifest.json"))

    def launch(phase, setup, command, cwd, seconds):
        report["checks"][phase] = dict(status="running", args=command)
        save()
        rc = native.tool(setup, command, cwd, join(out, phase + ".console"), seconds)
        report["checks"][phase].update(status="exited", returncode=rc)
        save()
        if rc:
            raise RuntimeError("%s exited %d" % (phase, rc))

    def hcell_deck(work, stage):
        # Keep every block master as a subcircuit so each top-level net lists the block ports it reaches.
        cells = [c.strip() for c in native.read(join(out, args.hcells)).splitlines() if c.strip()]
        if not cells or not all(re.match(r"\A[A-Za-z0-9_]+\Z", c) for c in cells):
            raise ValueError("Invalid hcell list")
        text = native.read(join(work, "lvs.svrf"))
        primary = 'LAYOUT PRIMARY "%s"' % cell
        if text.count(primary) != 1:
            raise ValueError("Unexpected LAYOUT PRIMARY statement")
        text = text.replace(primary, primary + "\n" + "\n".join("HCELL %s %s" % (c, c) for c in cells))
        native.put(join(work, "lvs.svrf"), text.encode("latin1"))
        report["decks"][stage].update(job_sha256=native.sha(text.encode("latin1")), hcells=cells)

    gds = join(out, "fixture.gds")
    try:
        if args.view:
            if not re.match(r"\Alayout[a-z0-9_]*\Z", args.view):
                raise ValueError("Invalid OA view")
            with open(args.lock, "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                oa = join(native.LIB_PATH, cell, args.view, "layout.oa")
                report["source"]["layout_oa_sha256"] = native.sha(native.raw(oa))
                launch("stream", native.CADENCE,
                       ["strmout", "-library", native.LIB, "-topCell", cell, "-view", args.view, "-strmFile", gds,
                        "-cdslib", join(out, "cds.lib"), "-layerMap", join(native.PDK, "tsmcN28.layermap"),
                        "-runDir", out, "-logFile", join(out, "stream.log"), "-summaryFile", join(out, "stream.sum"),
                        "-convertPin", "geometry", "-convertPcellPin", "geometry"], out, 600)
                if native.sha(native.raw(oa)) != report["source"]["layout_oa_sha256"]:
                    raise RuntimeError("layout.oa changed while streaming")
        else:
            if os.path.basename(args.gds) != args.gds or not isfile(join(out, args.gds)):
                raise ValueError("The GDS must be uploaded into the evidence directory")
            if args.gds != "fixture.gds":
                shutil.copyfile(join(out, args.gds), gds)
        identity = native.gds_identity(gds)
        report["gds"] = dict(sha256=identity["sha256"], without_gds_timestamps=identity["without_gds_timestamps"],
                             top_structural_sha256=identity["structural_sha256"].get(cell),
                             structures=len(identity["structural_sha256"]),
                             top_labels=sorted(identity["labels"].get(cell, [])))
        if cell not in identity["structural_sha256"]:
            raise RuntimeError("The stream has no " + cell + " structure")
        save()
        for stage in wanted:
            work = join(out, stage)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            if stage == "drc":
                report["decks"][stage] = native.prepare_deck(work, "drc", cell)
                launch(stage, native.CALIBRE, ["calibre", "-drc", "-hier", "-turbo", "8", "-nowait", "drc.svrf"],
                       work, 3600)
                text = native.read(join(work, "DRC.rep"))
                count = re.search(r"TOTAL DRC Results Generated:\s*(\d+)", text, re.I)
                if not count:
                    raise RuntimeError("Missing DRC summary count")
                rules = native.drc_rules(join(work, "DRC_RES.db"))
                report["checks"][stage].update(markers=int(count.group(1)), markers_by_rule=rules)
                if sum(rules.values()) != int(count.group(1)):
                    raise RuntimeError("DRC marker counts disagree")
            elif stage == "spice":
                # Layout netlist only: the comparison source is an empty placeholder that is never read.
                native.put(join(out, "reference.cdl"), b"* extraction only\n")
                report["decks"][stage] = native.prepare_deck(work, "lvs", cell)
                if args.hcells:
                    hcell_deck(work, stage)
                launch(stage, native.CALIBRE, ["calibre", "-spice", "layout.sp", "-hier", "-turbo", "8", "-nowait",
                                               "lvs.svrf"], work, 3600)
                netlist = join(work, "layout.sp")
                if not isfile(netlist) or not os.path.getsize(netlist):
                    raise RuntimeError("No layout netlist")
                report["checks"][stage].update(sha256=native.sha(native.raw(netlist)), bytes=os.path.getsize(netlist))
            elif stage == "lvs":
                # Comparison against the uploaded source: prepare_deck points SOURCE PATH at ../reference.cdl.
                shutil.copyfile(join(out, args.source), join(out, "reference.cdl"))
                report["decks"][stage] = native.prepare_deck(work, "lvs", cell)
                if args.hcells:
                    hcell_deck(work, stage)
                names = [n for n in args.virtual.split(",") if n]
                if names:
                    if not all(re.match(r"\A[A-Za-z0-9_!]+\Z", n) for n in names):
                        raise ValueError("Invalid virtual connect name")
                    text = native.read(join(work, "lvs.svrf"))
                    colon = "VIRTUAL CONNECT COLON YES"
                    if text.count(colon) != 1:
                        raise ValueError("Unexpected VIRTUAL CONNECT statement")
                    text = text.replace(colon, colon + "\nVIRTUAL CONNECT NAME " + " ".join('"%s"' % n for n in names))
                    native.put(join(work, "lvs.svrf"), text.encode("latin1"))
                    report["decks"][stage].update(job_sha256=native.sha(text.encode("latin1")),
                                                  virtual_connect_name=names)
                launch(stage, native.CALIBRE, ["calibre", "-lvs", "-hier", "-turbo", "8", "-nowait", "lvs.svrf"],
                       work, 3600)
                text = native.read(join(work, "lvs.rep"))
                verdicts = re.findall(r"(?m)^[ \t]+(CORRECT|INCORRECT|NOT COMPARED)[ \t]+(\S+)[ \t]+(\S+)[ \t]*$", text)
                top = [v for v, a, b in verdicts if a == cell and b == cell]
                if not top:
                    raise RuntimeError("Missing LVS comparison verdict")
                report["checks"][stage].update(verdict=top[-1], cells=[dict(verdict=v, layout=a, source=b)
                                                                       for v, a, b in verdicts])
            else:
                # Flat RC + coupling extraction of the whole core with the installed typical deck; nets are
                # named by the top-level labels (TEXT DEPTH PRIMARY).
                native.put(join(out, "reference.cdl"), b"* extraction only\n")
                report["decks"][stage] = native.prepare_deck(work, "pex", cell)
                for step, command in (("phdb", ["calibre", "-xrc", "-phdb", "-turbo", "8", "-nowait", "pex.svrf"]),
                                      ("rcc", ["calibre", "-xrc", "-pdb", "-rcc", "-turbo", "8", "-nowait", "pex.svrf"]),
                                      ("format", ["calibre", "-xrc", "-fmt", "-all", "-nowait", "pex.svrf"])):
                    launch(step, native.CALIBRE, command, work, 3600)
                extracted = join(work, "extracted.scs")
                if not isfile(extracted) or not os.path.getsize(extracted):
                    raise RuntimeError("PEX did not write the Spectre netlist")
                report["checks"]["pex"] = dict(status="exited", returncode=0, sha256=native.sha(native.raw(extracted)),
                                               bytes=os.path.getsize(extracted),
                                               companion_sha256=dict((n, native.sha(native.raw(join(work, n))))
                                                                     for n in sorted(os.listdir(work))
                                                                     if n.startswith("extracted.scs.")))
            if native.sha(native.raw(gds)) != report["gds"]["sha256"]:
                raise RuntimeError("GDS changed during verification")
            save()
        report["done"] = True
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
