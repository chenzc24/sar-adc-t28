"""Native checks of one top cell of SAR_ADC_T28_LAYOUT (chip-level objects and the chip), run inside its own
evidence directory.

The launcher (Layout/design/chip_objects.py) uploads this file with run_physical.py and workspace.py, the cds.lib
and, for a candidate, a GDS. The stream comes either from a saved OA view (strmout under the shared layout lock)
or from the uploaded GDS. Stages:
- drc: Calibre DRC with an installed deck: `cell` (drc_rule_T28_cell), `chip` (drc_rule_T28_chip: FULL_CHIP and
  WITH_SEALRING), or `chip-noseal` (the chip deck with WITH_SEALRING switched off, for a die without a seal ring);
- lvs: hierarchical Calibre LVS against an uploaded source netlist, with optional HCELLs, VIRTUAL CONNECT NAME
  nets and VIRTUAL CONNECT COLON NO; the same run writes the deck's ERC results, which are counted per check.
Compatible with the host's Python 2.
"""

from __future__ import print_function

import argparse
import fcntl
import glob
import json
import os
from os.path import isfile, join
import re
import shutil
import sys

sys.path.insert(0, os.getcwd())
import run_physical as native  # noqa: E402

STAGES = ("drc", "lvs")
STD_SPICE = ("/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/*_spi/TSMCHOME/digital/Back_End/spice/"
             "*/*.spi")
# The IO ring deck's additions without its VIRTUAL CONNECT NAME "?" (chip_physical.py RING_DECK_LINES).
RING_DECK_LINES = ['LVS POWER NAME "VDD?"', 'LVS GROUND NAME "VSS?" "GND?"', "ERC CELL NAME YES CELL SPACE XFORM"]
DRC_DECKS = {"cell": "drc/drc_rule_T28_cell", "chip": "drc/drc_rule_T28_chip", "chip-noseal": "drc/drc_rule_T28_chip"}


def erc_counts(path):
    """Results per ERC check from the ASCII ERC database (same layout as an ASCII DRC database)."""
    text = native.read(path)
    return dict((rule, int(n)) for rule, n in re.findall(r"(?m)^([A-Za-z0-9_.:-]+)\r?\n(\d+) \d+ \d+ ", text) if int(n))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    ap.add_argument("--top", required=True)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--view", help="saved OA view of the top cell to stream")
    source.add_argument("--gds", help="uploaded GDS in the evidence directory")
    ap.add_argument("--lock", required=True, help="shared layout lock, held only while strmout reads OA")
    ap.add_argument("--stages", default="drc", help="comma-separated subset of drc,lvs")
    ap.add_argument("--deck", choices=sorted(DRC_DECKS), default="cell")
    ap.add_argument("--source", help="uploaded LVS source netlist (CDL)")
    ap.add_argument("--hcells", help="file with one cell per line, kept as an HCELL in LVS")
    ap.add_argument("--virtual", default="", help="comma-separated net names for VIRTUAL CONNECT NAME")
    ap.add_argument("--colon-no", action="store_true", help="VIRTUAL CONNECT COLON NO (full-chip setting)")
    ap.add_argument("--std-cells", action="store_true", help="add foundry standard-cell bodies to the source")
    ap.add_argument("--flat", action="store_true", help="flat DRC (net-based rules such as LUP under-report with -hier)")
    ap.add_argument("--select-prefix", default="", help="comma-separated rule-name prefixes: DRC SELECT CHECK only those")
    ap.add_argument("--ring-deck", action="store_true",
                    help="LVS with the IO ring deck's power/ground names and ERC cell names, joining only --virtual names")
    args = ap.parse_args()
    out = os.getcwd()
    if os.path.basename(out) != args.identity:
        raise ValueError("Run inside the evidence directory of " + args.identity)
    top = args.top
    if not re.match(r"\A[A-Za-z0-9_]+\Z", top):
        raise ValueError("Invalid top cell")
    wanted = tuple(s for s in args.stages.split(",") if s)
    if not wanted or not set(wanted) <= set(STAGES):
        raise ValueError("Unknown stage in --stages")
    if "lvs" in wanted and not args.source:
        raise ValueError("LVS needs --source")
    report = dict(identity=args.identity, top=top, library=native.LIB, library_path=native.LIB_PATH,
                  source=dict(view=args.view) if args.view else dict(gds=args.gds), stages=list(wanted),
                  driver_sha256=dict((n, native.sha(native.raw(join(out, n))))
                                     for n in ("cell_physical.py", "run_physical.py", "workspace.py", "cds.lib")),
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

    def edit(work, stage, old, new):
        text = native.read(join(work, stage + ".svrf"))
        if text.count(old) != 1:
            raise ValueError("Expected one deck statement: " + old)
        text = text.replace(old, new)
        native.put(join(work, stage + ".svrf"), text.encode("latin1"))
        report["decks"][stage]["job_sha256"] = native.sha(text.encode("latin1"))

    gds = join(out, "fixture.gds")
    try:
        if args.view:
            if not re.match(r"\Alayout[a-z0-9_]*\Z", args.view):
                raise ValueError("Invalid OA view")
            with open(args.lock, "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                oa = join(native.LIB_PATH, top, args.view, "layout.oa")
                report["source"]["layout_oa_sha256"] = native.sha(native.raw(oa))
                launch("stream", native.CADENCE,
                       ["strmout", "-library", native.LIB, "-topCell", top, "-view", args.view, "-strmFile", gds,
                        "-cdslib", join(out, "cds.lib"), "-layerMap", join(native.PDK, "tsmcN28.layermap"),
                        "-runDir", out, "-logFile", join(out, "stream.log"), "-summaryFile", join(out, "stream.sum"),
                        "-convertPin", "geometry", "-convertPcellPin", "geometry"], out, 1800)
                if native.sha(native.raw(oa)) != report["source"]["layout_oa_sha256"]:
                    raise RuntimeError("layout.oa changed while streaming")
        else:
            if os.path.basename(args.gds) != args.gds or not isfile(join(out, args.gds)):
                raise ValueError("The GDS must be uploaded into the evidence directory")
            if args.gds != "fixture.gds":
                shutil.copyfile(join(out, args.gds), gds)
        identity = native.gds_identity(gds)
        report["gds"] = dict(sha256=identity["sha256"], without_gds_timestamps=identity["without_gds_timestamps"],
                             top_structural_sha256=identity["structural_sha256"].get(top),
                             structures=len(identity["structural_sha256"]),
                             top_labels=sorted(identity["labels"].get(top, [])))
        if top not in identity["structural_sha256"]:
            raise RuntimeError("The stream has no " + top + " structure")
        save()
        for stage in wanted:
            work = join(out, stage)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            if stage == "drc":
                # The same job edits as run_physical.prepare_deck, on the chosen installed deck.
                path = join(native.RULES, DRC_DECKS[args.deck])
                data = native.raw(path)
                text = data.decode("latin1")
                for directive, value in (("LAYOUT PATH", "fixture.gds"), ("LAYOUT PRIMARY", top)):
                    text = native.replace_once(text, r'^' + directive + r'[ \t]+"[^"]*"[^\n]*',
                                               '{} "{}"'.format(directive, value))
                text = native.replace_once(text, r'^DRC RESULTS DATABASE[^\n]*', 'DRC RESULTS DATABASE "DRC_RES.db" ASCII')
                if args.deck == "chip-noseal":
                    text = native.replace_once(text, r'^#DEFINE WITH_SEALRING\b[^\n]*',
                                               "//#DEFINE WITH_SEALRING  // switched off: no seal ring drawn yet")
                selected = []
                prefixes = [s for s in args.select_prefix.split(",") if s]
                if prefixes:
                    names = re.findall(r"(?m)^([A-Za-z][\w.]*)[ \t]*\{", text)
                    selected = sorted(set(n for n in names if any(n.startswith(pre) for pre in prefixes)))
                    if not selected:
                        raise ValueError("No rule check matches " + args.select_prefix)
                # flat Calibre DRC does not take -turbo
                command = ["calibre", "-drc"] + ([] if args.flat else ["-hier", "-turbo", "8"]) + ["-nowait", "drc.svrf"]
                dropped = []
                for attempt in range(6):
                    job = text + ("\nDRC SELECT CHECK " + " ".join(selected) + "\n" if selected else "")
                    native.put(join(work, "drc.svrf"), job.encode("latin1"))
                    report["decks"][stage] = dict(path=path, sha256=native.sha(data), variant=args.deck,
                                                  job_sha256=native.sha(job.encode("latin1")), flat=args.flat,
                                                  selected=selected, dropped_inactive=dropped)
                    phase = stage if attempt == 0 else "%s-retry%d" % (stage, attempt)
                    report["checks"][stage] = dict(status="running", args=command, attempt=attempt)
                    save()
                    rc = native.tool(native.CALIBRE, command, work, join(out, phase + ".console"), 14400)
                    # Rule checks inside inactive #IFDEF blocks are not defined: drop the ones Calibre names and retry.
                    undefined = re.findall(r"SELECT CHECK name is not the name of a RuleCheck statement or RuleCheck "
                                           r"group: (\S+)\.\s*$", native.read(join(out, phase + ".console")), re.M)
                    if rc and selected and undefined:
                        dropped += sorted(set(undefined))
                        selected = [n for n in selected if n not in undefined]
                        continue
                    report["checks"][stage].update(status="exited", returncode=rc)
                    save()
                    if rc:
                        raise RuntimeError("%s exited %d" % (stage, rc))
                    break
                text = native.read(join(work, "DRC.rep"))
                count = re.search(r"TOTAL DRC Results Generated:\s*(\d+)", text, re.I)
                if not count:
                    raise RuntimeError("Missing DRC summary count")
                rules = native.drc_rules(join(work, "DRC_RES.db"))
                checks = re.search(r"TOTAL RuleChecks Executed\s*=\s*(\d+)", text, re.I)
                report["checks"][stage].update(markers=int(count.group(1)), markers_by_rule=rules,
                                               rulechecks_executed=int(checks.group(1)) if checks else None)
                if sum(rules.values()) != int(count.group(1)):
                    raise RuntimeError("DRC marker counts disagree")
            else:
                source_text = native.read(join(out, args.source))
                if args.std_cells:
                    # Standard-cell bodies from the installed foundry SPICE for every master the source uses but
                    # does not define (the SAR macro flow, Layout/tools/physical/sar_se_physical.py, does the same).
                    paths = glob.glob(STD_SPICE)
                    if len(paths) != 1:
                        raise ValueError("Cannot identify the installed T28 standard-cell SPICE")
                    library = native.raw(paths[0]).decode("latin1")
                    defined = set(m.upper() for m in re.findall(r"(?im)^\.subckt[ \t]+(\S+)", source_text))
                    used = set(re.findall(r"(?m)^X\S+[^\n]*[ \t]([A-Z0-9_]+BWP12T30P140)[ \t]*$", source_text))
                    blocks = []
                    for cell in sorted(used - defined):
                        match = re.search(r"(?ims)^\.subckt[ \t]+" + cell + r"\s.*?^\.ends[^\n]*", library)
                        if not match:
                            raise ValueError("Missing transistor definition for " + cell)
                        blocks.append(match.group(0))
                    source_text = "\n".join(blocks) + "\n" + source_text
                    report["std_cells"] = dict(spice=paths[0], sha256=native.sha(native.raw(paths[0])),
                                               cells=sorted(used - defined))
                native.put(join(out, "reference.cdl"), source_text.encode("latin1"))
                report["decks"][stage] = native.prepare_deck(work, "lvs", top)
                if args.hcells:
                    cells = [c.strip() for c in native.read(join(out, args.hcells)).splitlines() if c.strip()]
                    if not cells or not all(re.match(r"\A[A-Za-z0-9_]+\Z", c) for c in cells):
                        raise ValueError("Invalid hcell list")
                    primary = 'LAYOUT PRIMARY "%s"' % top
                    edit(work, stage, primary, primary + "\n" + "\n".join("HCELL %s %s" % (c, c) for c in cells))
                    report["decks"][stage]["hcells"] = cells
                colon = "VIRTUAL CONNECT COLON YES"
                names = [n for n in args.virtual.split(",") if n]
                if args.colon_no or names or args.ring_deck:
                    if not all(re.match(r"\A[A-Za-z0-9_!?]+\Z", n) for n in names):
                        raise ValueError("Invalid virtual connect name")
                    new = "VIRTUAL CONNECT COLON NO" if args.colon_no else colon
                    if names:
                        new += "\nVIRTUAL CONNECT NAME " + " ".join('"%s"' % n for n in names)
                    if args.ring_deck:
                        new += "\n" + "\n".join(RING_DECK_LINES)
                    edit(work, stage, colon, new)
                    report["decks"][stage].update(virtual_connect_name=names, virtual_connect_colon=not args.colon_no,
                                                  ring_deck_lines=RING_DECK_LINES if args.ring_deck else [])
                launch(stage, native.CALIBRE, ["calibre", "-lvs", "-hier", "-turbo", "8", "-nowait", "lvs.svrf"],
                       work, 14400)
                text = native.read(join(work, "lvs.rep"))
                verdicts = re.findall(r"(?m)^[ \t]+(CORRECT|INCORRECT|NOT COMPARED)[ \t]+(\S+)[ \t]+(\S+)[ \t]*$", text)
                verdict = [v for v, a, b in verdicts if a == top and b == top]
                if not verdict:
                    raise RuntimeError("Missing LVS comparison verdict")
                report["checks"][stage].update(verdict=verdict[-1], cells=[dict(verdict=v, layout=a, source=b)
                                                                           for v, a, b in verdicts])
                erc = join(work, "calibre_erc.db")
                report["checks"]["erc"] = dict(status="exited" if isfile(erc) else "missing",
                                               results_by_check=erc_counts(erc) if isfile(erc) else {},
                                               summary_sha256=native.sha(native.raw(join(work, "calibre_erc.sum")))
                                               if isfile(join(work, "calibre_erc.sum")) else None)
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
