"""Placement-only ADC core: the frozen block views at their floorplan transforms, with no routing and no fill.

`generate` writes build.il and intent.json under work/layout/toplevel-placement/<id>. `--build` runs that
SKILL once in a fresh native workspace on the layout host, under the shared layout lock. It creates a new cell
and view only; the block views are opened read-only.
"""
import argparse
import base64
import hashlib
import json
import re
import shlex
import subprocess

from Layout.project import ROOT, config, write_json
from Layout.tools.analysis.toplevel_pin_readback import CELLVIEWS, FLOORPLAN

CELL = "sar8_adc_core"
VIEW = "layout_place"
CADENCE = "/home/cshrc/.cshrc.cadence.IC618SP201"
STANDARD_LIBRARY = "tcbn28hpcplusbwp12t30p140"
# Top-level instance of each floorplan block, and the occurrence that covers the block. The pair keeps the
# name its extracted netlist already has in the ADC (XCDAC); the SAR macro keeps XSAR from prepare_sar_se.
INSTANCES = {"cdac": ("XCDAC", "XCDAC/XCDAC"), "reference": ("XCDAC", "XCDAC/XREF"), "comparator": ("XCOMP", "XCOMP"),
             "bootstrap_n": ("XBOOTN", "XBOOTN"), "bootstrap_p": ("XBOOTP", "XBOOTP"), "sar": ("XSAR", "XSAR")}
# pins_um prefix -> top-level instance whose master carries the terminal.
PIN_OWNER = {"XCDAC": "XCDAC", "XREF": "XCDAC", "XCOMP": "XCOMP", "XBOOTN": "XBOOTN", "XBOOTP": "XBOOTP", "SAR": "XSAR"}


def sk(value):
    return '"' + value + '"'


def num(value):
    return format(value, ".3f")


def placements(plan):
    blocks = {b["id"]: b for b in plan["blocks"]}
    if set(blocks) != set(INSTANCES):
        raise ValueError("Floorplan blocks differ from the placement map")
    out = {}
    for block_id, (name, _) in INSTANCES.items():
        b = blocks[block_id]
        row = dict(name=name, cell=CELLVIEWS[block_id][0], view=CELLVIEWS[block_id][1],
                   xy=b["native_origin_translation"], orient=b.get("instance_orientation", "R0"))
        if any(abs(v * 200 - round(v * 200)) > 1e-6 for v in row["xy"]):
            raise ValueError(f"{name} origin is off the 5 nm grid")
        if out.setdefault(name, row) != row:
            raise ValueError(f"Blocks sharing {name} disagree on its master or transform")
    return list(out.values())


def generate(identity):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,55}", identity):
        raise ValueError("Invalid identity")
    plan_bytes = FLOORPLAN.read_bytes()
    plan = json.loads(plan_bytes)
    rows = placements(plan)
    cfg = config()
    x0, y0, x1, y1 = plan["core_bbox"]
    lines = [
        'procedure(tpNeed(ok message) unless(ok error("%s\\n" message)))',
        "procedure(tpBuild()",
        " let((lib cv master inst)",
        f"  lib=ddGetObj({sk(cfg['library'])})",
        f"  tpNeed(lib && lib~>readPath=={sk(cfg['library_path'])} \"Wrong layout library\")",
        f"  tpNeed(!ddGetObj({sk(cfg['library'])} {sk(CELL)}) \"Target cell already exists\")",
        f"  cv=dbOpenCellViewByType({sk(cfg['library'])} {sk(CELL)} {sk(VIEW)} \"maskLayout\" \"w\")",
        '  tpNeed(cv && !cv~>instances && !cv~>shapes "Cannot create the placement view")',
    ]
    for r in rows:
        lines += [
            f"  master=dbOpenCellViewByType({sk(cfg['library'])} {sk(r['cell'])} {sk(r['view'])} \"\" \"r\")",
            f"  tpNeed(master \"Missing master {r['cell']}/{r['view']}\")",
            f'  printf("MASTER {r["name"]} %s/%s/%s mode=%s bBox=%L terminals=%L\\n" master~>libName master~>cellName '
            "master~>viewName master~>mode master~>bBox sort(master~>terminals~>name 'alphalessp))",
            f"  inst=dbCreateInst(cv master {sk(r['name'])} list({num(r['xy'][0])} {num(r['xy'][1])}) {sk(r['orient'])})",
            f"  tpNeed(inst \"Cannot place {r['name']}\")",
        ]
    lines += [
        f"  tpNeed(dbCreateRect(cv list(\"prBoundary\" \"drawing\") list(list({num(x0)} {num(y0)}) list({num(x1)} {num(y1)}))) "
        '"Cannot draw the core boundary")',
        f"  tpNeed(length(cv~>instances)=={len(rows)} && length(cv~>shapes)==1 && !cv~>nets && !cv~>terminals "
        '"Unexpected placement content")',
        '  tpNeed(dbSave(cv) "Cannot save the placement view")',
        '  foreach(i cv~>instances printf("PLACED %s %s/%s/%s xy=%L orient=%s bBox=%L\\n" i~>name i~>libName '
        "i~>cellName i~>viewName i~>xy i~>orient i~>bBox))",
        '  printf("PLACEMENT_BUILD_OK instances=%d bBox=%L\\n" length(cv~>instances) cv~>bBox)',
        "  dbClose(cv) t))",
        "if(errset(tpBuild() t) then exit(0) else exit(1))",
    ]
    out = ROOT / "work/layout/toplevel-placement" / identity
    out.mkdir(parents=True, exist_ok=False)
    build = ("\n".join(lines) + "\n").encode("ascii")
    (out / "build.il").write_bytes(build)
    intent = dict(identity=identity, library=cfg["library"], cell=CELL, view=VIEW, instances=rows,
                  blocks={k: dict(instance=v[0], occurrence=v[1]) for k, v in INSTANCES.items()},
                  prboundary=[[x0, y0], [x1, y1]], floorplan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
                  build_il_sha256=hashlib.sha256(build).hexdigest(),
                  scope="placement only: no nets, terminals, routing or fill; block views are opened read-only")
    write_json(out / "intent.json", intent)
    return out, intent


def build(identity):
    out = ROOT / "work/layout/toplevel-placement" / identity
    intent = json.loads((out / "intent.json").read_bytes())
    files = {name: (out / name).read_bytes() for name in ("build.il", "intent.json")}
    if hashlib.sha256(files["build.il"]).hexdigest() != intent["build_il_sha256"]:
        raise ValueError("build.il differs from its intent")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    script = [
        "set -eu", "umask 077",
        f"test \"$(hostname -s)\" = {q(cfg['host'])}",
        f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
        f"test ! -e {q(cfg['library_path'] + '/' + CELL)}",
        f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}",
        "flock -w 300 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
        f"mkdir {q(evidence)}", f"cd {q(evidence)}",
    ]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script += [
        f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
        f"grep -q -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' cds.lib || "
        f"grep -m1 -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' /home/dmanager/shared_lib/TSMC28/cds.lib >> cds.lib",
        "rc=0",
        f"timeout -k 10 300 tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log build.log -restore build.il')}"
        " > oa.console 2>&1 < /dev/null || rc=$?",
        "sha256sum build.il intent.json cds.lib",
        f"sha256sum {q(cfg['library_path'] + '/' + CELL + '/' + VIEW + '/layout.oa')} || true",
        "grep -E '^(MASTER|PLACED|PLACEMENT_BUILD_OK)|\\*Error\\*' oa.console || true",
        "echo EXIT=$rc", "exit $rc",
    ]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=420)
    text = run.stdout.decode("utf-8", "replace")
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, returncode=run.returncode,
                   stdout=text.splitlines(), stderr=run.stderr.decode("utf-8", "replace").splitlines()[-20:],
                   ok=run.returncode == 0 and "PLACEMENT_BUILD_OK" in text)
    write_json(out / "build.json", receipt)
    if not receipt["ok"]:
        raise RuntimeError("Placement build failed; see " + str(out / "build.json"))
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    ap.add_argument("--build", action="store_true", help="run the generated build.il on the layout host")
    args = ap.parse_args()
    if args.build:
        print(json.dumps(build(args.identity), indent=1))
    else:
        out, intent = generate(args.identity)
        print(json.dumps(dict(out=str(out), instances=intent["instances"]), indent=1))


if __name__ == "__main__":
    main()
