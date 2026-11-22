"""Native checks of the ADC core top cell sar8_adc_core, run inside its own evidence directory.

The launcher (Layout/design/toplevel_route.py) uploads this file with run_physical.py and workspace.py,
the cds.lib and, for a candidate, the merged GDS. The stream comes either from a saved OA view
(strmout under the shared layout lock) or from the uploaded GDS. Stages: drc (Calibre DRC with the
installed cell deck), spice (hierarchical layout netlist with the installed LVS deck, no comparison),
pex (flat Calibre xRC RC and coupling extraction, typical deck). Compatible with the host's Python 2.
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
STAGES = ("stream", "drc", "spice", "pex")


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
    args = ap.parse_args()
    out = os.getcwd()
    if os.path.basename(out) != args.identity:
        raise ValueError("Run inside the evidence directory of " + args.identity)
    wanted = STAGES[1:STAGES.index(args.through) + 1]
    if args.stages:
        wanted = tuple(s for s in args.stages.split(",") if s)
        if not set(wanted) <= set(STAGES[1:]):
            raise ValueError("Unknown stage in --stages")
    report = dict(identity=args.identity, top=TOP, library=native.LIB, library_path=native.LIB_PATH,
                  source=dict(view=args.view) if args.view else dict(gds=args.gds), stages=list(wanted),
                  driver_sha256=dict((n, native.sha(native.raw(join(out, n))))
                                     for n in ("toplevel_physical.py", "run_physical.py", "workspace.py", "cds.lib")),
                  checks={}, decks={})

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

    gds = join(out, "fixture.gds")
    try:
        if args.view:
            if not re.match(r"\Alayout[a-z0-9_]*\Z", args.view):
                raise ValueError("Invalid OA view")
            with open(args.lock, "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                oa = join(native.LIB_PATH, TOP, args.view, "layout.oa")
                report["source"]["layout_oa_sha256"] = native.sha(native.raw(oa))
                launch("stream", native.CADENCE,
                       ["strmout", "-library", native.LIB, "-topCell", TOP, "-view", args.view, "-strmFile", gds,
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
                             top_structural_sha256=identity["structural_sha256"].get(TOP),
                             structures=len(identity["structural_sha256"]),
                             top_labels=sorted(identity["labels"].get(TOP, [])))
        if TOP not in identity["structural_sha256"]:
            raise RuntimeError("The stream has no " + TOP + " structure")
        save()
        for stage in wanted:
            work = join(out, stage)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            if stage == "drc":
                report["decks"][stage] = native.prepare_deck(work, "drc", TOP)
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
                report["decks"][stage] = native.prepare_deck(work, "lvs", TOP)
                if args.hcells:
                    # Keep every block master as a subcircuit so each top-level net lists the block ports it reaches.
                    cells = [c.strip() for c in native.read(join(out, args.hcells)).splitlines() if c.strip()]
                    if not cells or not all(re.match(r"\A[A-Za-z0-9_]+\Z", c) for c in cells):
                        raise ValueError("Invalid hcell list")
                    text = native.read(join(work, "lvs.svrf"))
                    primary = 'LAYOUT PRIMARY "%s"' % TOP
                    if text.count(primary) != 1:
                        raise ValueError("Unexpected LAYOUT PRIMARY statement")
                    text = text.replace(primary, primary + "\n" + "\n".join("HCELL %s %s" % (c, c) for c in cells))
                    native.put(join(work, "lvs.svrf"), text.encode("latin1"))
                    report["decks"][stage].update(job_sha256=native.sha(text.encode("latin1")), hcells=cells)
                launch(stage, native.CALIBRE, ["calibre", "-spice", "layout.sp", "-hier", "-turbo", "8", "-nowait",
                                               "lvs.svrf"], work, 3600)
                netlist = join(work, "layout.sp")
                if not isfile(netlist) or not os.path.getsize(netlist):
                    raise RuntimeError("No layout netlist")
                report["checks"][stage].update(sha256=native.sha(native.raw(netlist)), bytes=os.path.getsize(netlist))
            else:
                # Flat RC + coupling extraction of the whole core with the installed typical deck; nets are
                # named by the top-level labels (TEXT DEPTH PRIMARY).
                native.put(join(out, "reference.cdl"), b"* extraction only\n")
                report["decks"][stage] = native.prepare_deck(work, "pex", TOP)
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
