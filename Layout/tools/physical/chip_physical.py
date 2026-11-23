"""Native checks of the chip cell sar8_adc_chip, run inside its own evidence directory (Stage 5).

The launcher (Layout/design/chip_assembly.py physical) uploads this file with run_physical.py and workspace.py, the
cds.lib (with the IO library), the HCELL list and the LVS source. Stages: stream (strmout of the saved view under
the shared layout lock), drc (the installed chip deck drc_rule_T28_chip: the cell deck with FULL_CHIP and
WITH_SEALRING, including the density, pad-opening and ESD checks), lvs (the installed calibre.lvs with the IO ring
deck's additions: VIRTUAL CONNECT NAME "?", its power and ground name patterns, ERC with cell names; block masters as
HCELLs). Compatible with the host's Python 2.
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

DEFAULT_TOP = "sar8_adc_chip"
STAGES = ("drc", "lvs")
RING_DECK_LINES = ['VIRTUAL CONNECT NAME "?"', 'LVS POWER NAME "VDD?"', 'LVS GROUND NAME "VSS?" "GND?"',
                   "ERC CELL NAME YES CELL SPACE XFORM"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    ap.add_argument("--top", default=DEFAULT_TOP)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--view")
    source.add_argument("--gds", help="uploaded GDS in the evidence directory (an assembly not in OA)")
    ap.add_argument("--lock", required=True)
    ap.add_argument("--stages", default="drc,lvs")
    ap.add_argument("--hcells")
    ap.add_argument("--source")
    args = ap.parse_args()
    TOP = args.top
    if not re.match(r"\A[A-Za-z0-9_]+\Z", TOP):
        raise ValueError("Invalid top cell")
    out = os.getcwd()
    if os.path.basename(out) != args.identity:
        raise ValueError("Run inside the evidence directory of " + args.identity)
    wanted = tuple(s for s in args.stages.split(",") if s)
    if not set(wanted) <= set(STAGES) or ("lvs" in wanted and not args.source):
        raise ValueError("Bad --stages or missing --source")
    if args.view and not re.match(r"\Alayout[a-z0-9_]*\Z", args.view):
        raise ValueError("Invalid OA view")
    if args.gds and (os.path.basename(args.gds) != args.gds or not isfile(join(out, args.gds))):
        raise ValueError("The GDS must be uploaded into the evidence directory")
    report = dict(identity=args.identity, top=TOP, library=native.LIB, source=dict(view=args.view) if args.view else dict(gds=args.gds), stages=list(wanted),
                  driver_sha256=dict((n, native.sha(native.raw(join(out, n))))
                                     for n in ("chip_physical.py", "run_physical.py", "workspace.py", "cds.lib")),
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
        if args.gds:
            shutil.copyfile(join(out, args.gds), gds)
        else:
            with open(args.lock, "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                oa = join(native.LIB_PATH, TOP, args.view, "layout.oa")
                report["source"]["layout_oa_sha256"] = native.sha(native.raw(oa))
                launch("stream", native.CADENCE,
                       ["strmout", "-library", native.LIB, "-topCell", TOP, "-view", args.view, "-strmFile", gds,
                        "-cdslib", join(out, "cds.lib"), "-layerMap", join(native.PDK, "tsmcN28.layermap"),
                        "-runDir", out, "-logFile", join(out, "stream.log"), "-summaryFile", join(out, "stream.sum"),
                        "-convertPin", "geometry", "-convertPcellPin", "geometry"], out, 1800)
                if native.sha(native.raw(oa)) != report["source"]["layout_oa_sha256"]:
                    raise RuntimeError("layout.oa changed while streaming")
        report["gds"] = dict(sha256=native.sha(native.raw(gds)), bytes=os.path.getsize(gds))
        save()
        for stage in wanted:
            work = join(out, stage)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            if stage == "drc":
                path = join(native.RULES, "drc/drc_rule_T28_chip")
                text = native.raw(path).decode("latin1")
                for directive, value in (("LAYOUT PATH", "fixture.gds"), ("LAYOUT PRIMARY", TOP)):
                    text = native.replace_once(text, r'^' + directive + r'[ \t]+"[^"]*"[^\n]*',
                                               '%s "%s"' % (directive, value))
                text = native.replace_once(text, r'^DRC RESULTS DATABASE[^\n]*', 'DRC RESULTS DATABASE "DRC_RES.db" ASCII')
                native.put(join(work, "drc.svrf"), text.encode("latin1"))
                report["decks"][stage] = dict(path=path, sha256=native.sha(native.raw(path)),
                                              job_sha256=native.sha(text.encode("latin1")))
                launch(stage, native.CALIBRE, ["calibre", "-drc", "-hier", "-turbo", "8", "-nowait", "drc.svrf"],
                       work, 7200)
                rep = native.read(join(work, "DRC.rep"))
                count = re.search(r"TOTAL DRC Results Generated:\s*(\d+)", rep, re.I)
                if not count:
                    raise RuntimeError("Missing DRC summary count")
                rules = native.drc_rules(join(work, "DRC_RES.db"))
                report["checks"][stage].update(markers=int(count.group(1)), markers_by_rule=rules)
            else:
                shutil.copyfile(join(out, args.source), join(out, "reference.cdl"))
                report["source_netlist"] = dict(name=args.source, sha256=native.sha(native.raw(join(out, args.source))))
                report["decks"][stage] = native.prepare_deck(work, "lvs", TOP)
                text = native.read(join(work, "lvs.svrf"))
                if args.hcells:
                    cells = [c.strip() for c in native.read(join(out, args.hcells)).splitlines() if c.strip()]
                    if not all(re.match(r"\A[A-Za-z0-9_]+\Z", c) for c in cells):
                        raise ValueError("Invalid hcell list")
                    primary = 'LAYOUT PRIMARY "%s"' % TOP
                    text = text.replace(primary, primary + "\n" + "\n".join("HCELL %s %s" % (c, c) for c in cells), 1)
                    report["decks"][stage]["hcells"] = cells
                colon = "VIRTUAL CONNECT COLON YES"
                if text.count(colon) != 1:
                    raise ValueError("Unexpected VIRTUAL CONNECT statement")
                text = text.replace(colon, colon + "\n" + "\n".join(RING_DECK_LINES))
                native.put(join(work, "lvs.svrf"), text.encode("latin1"))
                report["decks"][stage].update(job_sha256=native.sha(text.encode("latin1")), ring_deck_lines=RING_DECK_LINES)
                launch(stage, native.CALIBRE, ["calibre", "-lvs", "-hier", "-turbo", "8", "-nowait", "lvs.svrf"],
                       work, 7200)
                rep = native.read(join(work, "lvs.rep"))
                verdicts = re.findall(r"(?m)^[ \t]+(CORRECT|INCORRECT|NOT COMPARED)[ \t]+(\S+)[ \t]+(\S+)[ \t]*$", rep)
                top = [v for v, a, b in verdicts if a == TOP and b == TOP]
                report["checks"][stage].update(verdict=top[-1] if top else None,
                                               cells=[dict(verdict=v, layout=a, source=b) for v, a, b in verdicts])
                summary = native.read(join(work, "calibre_erc.sum"))
                erc = dict((k, int(n)) for k, n in re.findall(r"(?m)^RULECHECK\s+(\S+)\s+\.+\s+TOTAL Result Count = (\d+)",
                                                                summary) if int(n))
                report["checks"][stage]["erc_results_by_check"] = erc
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
