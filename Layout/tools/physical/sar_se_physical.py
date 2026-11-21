"""Build the single-edge SAR macro in SAR_ADC_T28_LAYOUT and run the native T28 checks.

The inputs directory holds the build records and the leaf CDL from sar_se_def.py. A
build creates a new view of sar8_se_core in the shared layout library and never replaces
an existing one; later runs verify the saved view. Compatible with Python 2.
"""

from __future__ import print_function

import argparse
import fcntl
import glob
import json
import os
from os.path import isdir, isfile, join
import re
import shutil

import run_physical as native
import workspace

CORE = "sar8_se_core"
STD = "tcbn28hpcplusbwp12t30p140"
SOURCE_LIB = "/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/*_spi/TSMCHOME/digital/Back_End/spice/*/*.spi"
DRC_ADVISORIES = {"DIODMY_L:WARNING", "IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1"}
# Density windows close at the top level with the module fill; see Layout/specs/fill-policy.md.
DENSITY = re.compile(r"\A(OD|PO|M\d|Mx)\.DN\.")


def reference(staging, output):
    paths = glob.glob(SOURCE_LIB)
    if len(paths) != 1:
        raise ValueError("Cannot identify the installed T28 standard-cell SPICE")
    library = native.read(paths[0])
    source = native.read(join(staging, "sar-se-leaves.cdl"))
    blocks = []
    for cell in sorted(set(re.findall(r"(?m)^X\S+[^\n]*[ \t]([A-Z0-9_]+)BWP12T30P140[ \t]*$", source))):
        match = re.search(r"(?ims)^\.subckt[ \t]+" + cell + r"BWP12T30P140\s.*?^\.ends[^\n]*", library)
        if not match:
            raise ValueError("Missing transistor definition for " + cell)
        blocks.append(match.group(0))
    pins = re.search(r"(?im)^\.subckt[ \t]+" + CORE + r"[ \t]+([^\n]+)", source).group(1).split()
    path = join(output, "reference.cdl")
    native.put(path, ("\n".join(blocks) + "\n" + source).encode("ascii"))
    return pins, native.sha(native.raw(path)), native.sha(native.raw(paths[0]))


def cds_lib(cfg, out):
    text = native.read(join(cfg["runtime"], "cds.lib"))
    if not re.search(r"(?m)^DEFINE[ \t]+" + native.LIB + r"[ \t]+" + re.escape(cfg["library_path"]) + r"[ \t]*$", text):
        raise ValueError("The runtime cds.lib must define the shared layout library")
    if not re.search(r"(?m)^DEFINE[ \t]+" + STD + r"[ \t]", text):
        site = native.read("/home/dmanager/shared_lib/TSMC28/cds.lib")
        definition = re.search(r"(?m)^DEFINE[ \t]+" + STD + r"[ \t]+[^\n]+", site)
        if not definition:
            raise ValueError("Cannot resolve the native standard-cell OA library")
        text += "\n" + definition.group(0) + "\n"
    native.put(join(out, "cds.lib"), text.encode("ascii"))


def build(cfg, out, staging, view):
    """Create a new view in the shared library; an existing view or edit lock stops the build."""
    cell = join(cfg["library_path"], CORE)
    if isdir(join(cell, view)):
        raise ValueError("%s/%s/%s already exists; verify it instead of rebuilding" % (native.LIB, CORE, view))
    locks = glob.glob(join(cell, "*", "*.cdslck"))
    if locks:
        raise ValueError("Open edit locks on the macro cell: " + ", ".join(locks))
    script = ('load("sar_single_edge.il")\n'
              'if(errset(seTech("{w}") && seBuild("{w}" "{c}" "{v}" "{r}") && '
              'seAudit("{w}" "{c}" "{v}" "build-readback.txt") t) then exit(0) else exit(1))\n'
              ).format(w=native.LIB, c=CORE, v=view, r=join(staging, "build.txt"))
    native.put(join(out, "build.il"), script.encode("ascii"))
    if native.tool(native.CADENCE, ["virtuoso", "-nograph", "-nocdsinit", "-restore", "build.il", "-log", "build.log"],
                   out, join(out, "build.console"), 600):
        raise RuntimeError("OA build failed; see build.log")


def verify(cfg, out, identity, staging, view, through, built, rc_corner=None):
    pins, source_hash, library_hash = reference(staging, out)
    report = dict(id=identity, case="sar-se", library=native.LIB, library_path=cfg["library_path"], staging=staging,
                  top=CORE, oa_view=view, built_by_this_run=built, interconnect_rc=rc_corner or "typical",
                  reference_sha256=source_hash, standard_library_sha256=library_hash,
                  build_records_sha256=native.sha(native.raw(join(staging, "build.txt"))), checks={}, decks={})

    def save():
        path = join(out, "manifest.json")
        native.put(path + ".new", (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("ascii"))
        os.rename(path + ".new", path)

    def run(label, setup, command, timeout):
        if native.tool(setup, command, out if label in ("oa", "stream") else join(out, label),
                       join(out, label + ".console"), timeout):
            raise RuntimeError("Native tool failed at " + label)

    try:
        audit = ('load("sar_single_edge.il")\nif(errset(seAudit("%s" "%s" "%s" "readback.txt") t) then exit(0) else exit(1))\n'
                 % (native.LIB, CORE, view))
        native.put(join(out, "readback.il"), audit.encode("ascii"))
        run("oa", native.CADENCE, ["virtuoso", "-nograph", "-nocdsinit", "-restore", "readback.il", "-log", "readback.log"], 120)
        run("stream", native.CADENCE, ["strmout", "-library", native.LIB, "-topCell", CORE, "-view", view,
                                       "-strmFile", join(out, "fixture.gds"), "-cdslib", join(out, "cds.lib"),
                                       "-layerMap", join(native.PDK, "tsmcN28.layermap"), "-runDir", out,
                                       "-logFile", join(out, "stream.log"), "-convertPin", "geometry",
                                       "-convertPcellPin", "geometry"], 180)
        gds = native.gds_identity(join(out, "fixture.gds"))
        if sorted(gds["labels"].get(CORE, [])) != sorted(pins):
            raise ValueError("Stream ports differ from the electrical interface")
        report["gds"] = {k: gds[k] for k in ("sha256", "without_gds_timestamps")}
        report["gds"]["structural_sha256"] = gds["structural_sha256"][CORE]
        save()
        for stage in ("drc", "lvs", "pex"):
            if through == "stream":
                break
            work = join(out, stage)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            report["decks"][stage] = native.prepare_deck(work, stage, CORE, distributed_supplies=("VDD", "VSS"))
            if stage == "pex":
                # Name extracted nets after the LVS source so the testbench can probe internal SAR nodes.
                # Source names need the LVS cross-reference (XDB): the first step runs calibre -lvs
                # instead of -phdb, and the SVDB statement also writes the xRC databases.
                deck = native.raw(join(work, "pex.svrf"))
                layout_names = b'PEX NETLIST "extracted.scs" SPECTRE LAYOUTNAMES LOCATION RCNAMED'
                svdb = re.compile(br'(?m)^([ \t]*MASK SVDB DIRECTORY "svdb" QUERY)[ \t]*$')
                if deck.count(layout_names) != 1 or len(svdb.findall(deck)) != 1:
                    raise ValueError("Unexpected PEX netlist or SVDB statement")
                deck = deck.replace(layout_names, layout_names.replace(b"LAYOUTNAMES", b"SOURCENAMES"))
                deck = svdb.sub(lambda m: m.group(1) + b" XRC", deck)
                native.put(join(work, "pex.svrf"), deck)
                report["decks"][stage]["netlist_names"] = "SOURCENAMES"
                report["decks"][stage]["job_sha256"] = native.sha(deck)
                if rc_corner:
                    # Swap the deck's typical interconnect rules for the foundry corner package.
                    from sar_rc_corner import select
                    select(work, cfg, native.PDK, join(native.RULES, "rcx"), report["decks"][stage], rc_corner)
            if stage == "drc":
                run(stage, native.CALIBRE, ["calibre", "-drc", "-hier", "-turbo", "4", "-nowait", "drc.svrf"], 900)
                markers = native.drc_rules(join(work, "DRC_RES.db"))
                count = int(re.search(r"TOTAL DRC Results Generated:\s*(\d+)", native.read(join(work, "DRC.rep")), re.I).group(1))
                if count != sum(markers.values()):
                    raise ValueError("DRC marker counts disagree")
                density = dict((r, n) for r, n in markers.items() if DENSITY.match(r))
                blocking = dict((r, n) for r, n in markers.items() if r not in DRC_ADVISORIES and r not in density)
                report["checks"][stage] = dict(markers=count, markers_by_rule=markers, blocking=blocking,
                                               deferred_density=density)
            elif stage == "lvs":
                run(stage, native.CALIBRE, ["calibre", "-lvs", "-hier", "-turbo", "4", "-nowait", "lvs.svrf"], 900)
                verdict = re.search(r"(?m)^\s+(CORRECT|INCORRECT)[ \t]+" + CORE + r"[ \t]+" + CORE + r"[ \t]*$",
                                    native.read(join(work, "lvs.rep")))
                report["checks"][stage] = {"verdict": verdict.group(1) if verdict else "NO_VERDICT"}
                if not verdict or verdict.group(1) != "CORRECT":
                    save()
                    raise ValueError("Transistor LVS did not match")
            else:
                os.mkdir(join(work, "svdb"))
                for step, command in (
                        ("pex-lvs", ["calibre", "-lvs", "-hier", "-spice", "svdb/" + CORE + ".sp", "-turbo", "4"]),
                        ("rcc", ["calibre", "-xrc", "-pdb", "-rcc", "-turbo", "4"]),
                        ("format", ["calibre", "-xrc", "-fmt", "-all"])):
                    if native.tool(native.CALIBRE, command + ["-nowait", "pex.svrf"], work, join(out, step + ".console"), 1800):
                        raise RuntimeError("Native tool failed at " + step)
                    if step == "pex-lvs":
                        verdict = re.search(r"(?m)^\s+(CORRECT|INCORRECT)[ \t]+" + CORE + r"[ \t]+" + CORE + r"[ \t]*$",
                                            native.read(join(work, "lvs.rep")))
                        if not verdict or verdict.group(1) != "CORRECT":
                            raise ValueError("The LVS comparison inside extraction did not match")
                main = join(work, "extracted.scs")
                parasitics = native.read(main + ".pex")
                rails = {}
                for rail in ("VDD", "VSS"):
                    models = re.findall(r"(?ims)^subckt PM_[^\s]*%" + rail + r"[ \t]+\(.*?^[ \t]*ends\b", parasitics)
                    if len(models) != 1:
                        raise ValueError("Missing or ambiguous distributed supply model for " + rail)
                    rails[rail] = len(re.findall(r"(?im)^r\S+[ \t]+\([^\n]+\)[ \t]+resistor[ \t]+r=", models[0]))
                report["checks"][stage] = dict(distributed_rail_resistors=rails, bytes=os.path.getsize(main),
                                               sha256=native.sha(native.raw(main)),
                                               companion_sha256=dict((f, native.sha(native.raw(join(work, f))))
                                                                     for f in os.listdir(work) if f.startswith("extracted.scs.")))
            save()
            if stage == through:
                break
    except Exception as error:
        report["error"] = str(error)
        save()
        raise
    save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    parser.add_argument("--staging", required=True, help="State directory with build.txt and sar-se-leaves.cdl")
    parser.add_argument("--view", required=True, help="View of sar8_se_core in SAR_ADC_T28_LAYOUT, e.g. layout_r2")
    parser.add_argument("--build", action="store_true", help="Create the view in SAR_ADC_T28_LAYOUT before verification")
    parser.add_argument("--through", choices=("stream", "drc", "lvs", "pex"), default="pex")
    parser.add_argument("--rc-corner", choices=("cworst_T", "cbest_T"), help="Foundry interconnect corner for the extraction")
    args = parser.parse_args()
    if args.rc_corner and args.through != "pex":
        parser.error("--rc-corner requires --through pex")
    if not re.match(r"\Alayout[a-z0-9_]*\Z", args.view):
        raise ValueError("Invalid OA view")
    cfg = workspace.paths()
    staging = workspace.state(args.staging)
    for name in ("build.txt", "sar-se-leaves.cdl"):
        if not isfile(join(staging, name)):
            raise ValueError("Staging input missing: " + name)
    with open(cfg["lock"], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out = workspace.evidence(args.identity, create=True)
        cds_lib(cfg, out)
        shutil.copyfile(join(cfg["runtime"], "sar_single_edge.il"), join(out, "sar_single_edge.il"))
        if args.build:
            build(cfg, out, staging, args.view)
        verify(cfg, out, args.identity, staging, args.view, args.through, args.build, args.rc_corner)


if __name__ == "__main__":
    main()
