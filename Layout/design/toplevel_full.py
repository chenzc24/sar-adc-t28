"""Stage 4b of chenzc24/sar-adc-t28#12: boundary routes, supply feeds, the reference network, decoupling and grid,
built as sar8_adc_core/layout_route_full on top of layout_route_int.

`build-script ID CONTENT.json` writes build.il from a content file (rects with nets, labels, terminals with their
pin shapes, PDK PCell instances); `build ID` runs it once on the layout host under the shared layout lock. The
script copies layout_route_int with dbCopyCellView, so its routes, nets and labels carry over unchanged, and adds
the content. It replaces an existing layout_route_full only when that view carries this generator's owner
property; layout_place and layout_route_int are opened read-only and their layout.oa files must not change.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

from Layout.design.toplevel_route import CADENCE, IDENTITY, STANDARD_LIBRARY, WORK, num, sk
from Layout.project import config, write_json

CELL = "sar8_adc_core"
VIEW = "layout_route_full"
SOURCE = "layout_route_int"
READ_ONLY = ("layout_place", "layout_route_int")
OWNER = "Layout/design/toplevel_full.py"
PDK_LIBRARY = "tsmcN28"
PCELLS = {"nmoscap", "rupolym"}


def build_script(identity, content):
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    cfg = config()
    lib = sk(cfg["library"])
    nets = sorted({r["net"] for r in content.get("rects", []) if r.get("net")}
                  | {t["net"] for t in content.get("terminals", [])}
                  | {n for p in content.get("pcells", []) for n in p.get("nets", {}).values()})
    lines = [
        'procedure(tfNeed(ok message) unless(ok error("%s\\n" message)))',
        "procedure(tfNet(cv name) or(dbFindNetByName(cv name) dbCreateNet(cv name)))",
        "procedure(tfRect(cv layer purpose net box) let((f) f=dbCreateRect(cv list(layer purpose) box)"
        ' tfNeed(f sprintf(nil "Cannot draw %s on %s" net layer)) when(net!="" dbAddFigToNet(f tfNet(cv net))) f))',
        "procedure(tfBuild()",
        " let((dd src cv old count inst term net fig)",
        f"  dd=ddGetObj({lib})",
        f"  tfNeed(dd && dd~>readPath=={sk(cfg['library_path'])} \"Wrong layout library\")",
        f"  old=ddGetObj({lib} {sk(CELL)} {sk(VIEW)})",
        "  when(old",
        f"   src=dbOpenCellViewByType({lib} {sk(CELL)} {sk(VIEW)} \"maskLayout\" \"r\")",
        f"   tfNeed(src && dbGetPropByName(src \"generatorOwner\")~>value=={sk(OWNER)} \"Existing view is not ours\")",
        "   dbClose(src))",
        f"  src=dbOpenCellViewByType({lib} {sk(CELL)} {sk(SOURCE)} \"maskLayout\" \"r\")",
        '  tfNeed(src && length(src~>instances)==5 && !src~>terminals "Unexpected layout_route_int")',
        # Overwrite in place (g_overwrite) rather than delete: a reader elsewhere keeps its OA cache of the old file,
        # and ddDeleteObj refuses a view with files in use.
        f"  old=dbCopyCellView(src {lib} {sk(CELL)} {sk(VIEW)} nil nil t)",
        '  tfNeed(old "Cannot copy layout_route_int")',
        "  when(dbIsId(old) && old!=src dbClose(old))",
        "  dbClose(src)",
        f"  cv=dbOpenCellViewByType({lib} {sk(CELL)} {sk(VIEW)} \"maskLayout\" \"a\")",
        '  tfNeed(cv && length(cv~>instances)==5 "Cannot open the copy")',
        '  dbReplaceProp(cv "generatorOwner" "string" ' + sk(OWNER) + ")",
        '  dbReplaceProp(cv "copiedFrom" "string" ' + sk(SOURCE) + ")",
    ]
    for a, b in content.get("merge_nets", []):
        lines.append(f"  tfNeed(dbMergeNet(tfNet(cv {sk(b)}) dbFindNetByName(cv {sk(a)})) \"Cannot merge {a}\")")
    lines.append("  foreach(n '(" + " ".join(sk(n) for n in nets) + ") tfNet(cv n))")
    # The content goes into part procedures (statements that share inst/net/term/fig stay in one group): a single
    # function body of some 19000 calls overflows the SKILL value stack.
    groups = []
    for p in content.get("pcells", []):
        if p["cell"] not in PCELLS:
            raise ValueError("Unexpected PCell " + p["cell"])
        params = " ".join(f"list({sk(k)} \"string\" {sk(v)})" for k, v in p["params"].items())
        g = [f"  inst=dbCreateParamInstByMasterName(cv {sk(PDK_LIBRARY)} {sk(p['cell'])} \"layout\" {sk(p['name'])}"
             f" list({num(p['xy'][0])} {num(p['xy'][1])}) {sk(p.get('orient', 'R0'))} 1 list({params}))",
             f"  tfNeed(inst \"Cannot place {p['name']}\")"]
        for term, net in p.get("nets", {}).items():
            g.append(f"  tfNeed(dbCreateInstTerm(tfNet(cv {sk(net)}) inst dbFindTermByName(inst~>master {sk(term)}))"
                     f" \"Cannot bind {p['name']}.{term}\")")
        groups.append(g)
    for r in content.get("rects", []):
        groups.append([f"  tfRect(cv {sk(r['layer'])} {sk(r.get('purpose', 'drawing'))} {sk(r.get('net', ''))} "
                       f"list({num(r['box'][0])}:{num(r['box'][1])} {num(r['box'][2])}:{num(r['box'][3])}))"])
    for t in content.get("terminals", []):
        g = [f"  net=tfNet(cv {sk(t['net'])}) term=or(dbFindTermByName(cv {sk(t['net'])})"
             f" dbCreateTerm(net {sk(t['net'])} {sk(t.get('direction', 'inputOutput'))}))"]
        for i, pin in enumerate(t["pins"]):
            x0, y0, x1, y1 = pin["box"]
            g.append(f"  fig=dbCreateRect(cv list({sk(pin['layer'])} \"pin\") list({num(x0)}:{num(y0)} {num(x1)}:{num(y1)}))")
            g.append(f"  tfNeed(fig && dbCreatePin(net fig {sk(t['net'] + '_' + str(i))} term) \"Cannot pin {t['net']}\")")
            g.append(f"  dbCreateLabel(cv list({sk(pin['layer'])} \"pin\") {num((x0 + x1) / 2)}:{num((y0 + y1) / 2)} "
                     f"{sk(t['net'])} \"centerCenter\" \"R0\" \"roman\" 0.2)")
        groups.append(g)
    for t in content.get("labels", []):
        groups.append([f"  dbCreateLabel(cv list({sk(t['layer'])} \"pin\") {num(t['xy'][0])}:{num(t['xy'][1])} {sk(t['net'])}"
                       ' "centerCenter" "R0" "roman" 0.1)'])
    parts, part = [], []
    for g in groups:
        if part and len(part) + len(g) > 2000:
            parts.append(part)
            part = []
        part += g
    if part:
        parts.append(part)
    defs = []
    for i, body in enumerate(parts):
        defs += [f"procedure(tfPart{i}(cv)", " let((inst term net fig)"] + body + ["  t))"]
        lines.append(f"  tfPart{i}(cv)")
    lines[:0] = defs
    lines += [
        '  tfNeed(dbSave(cv) "Cannot save layout_route_full")',
        '  foreach(i cv~>instances when(i~>libName==' + sk(PDK_LIBRARY) + ' printf("PCELL %s %s bBox=%L\\n" i~>name i~>cellName i~>bBox)'
        '   foreach(tm i~>master~>terminals foreach(p tm~>pins foreach(f list(p~>fig) printf("PIN %s %s %s %L\\n" i~>name tm~>name'
        " f~>layerName dbTransformBBox(f~>bBox i~>transform)))))))",
        '  printf("FULL_BUILD_OK shapes=%d instances=%d nets=%d terminals=%d\\n" length(cv~>shapes) length(cv~>instances)'
        " length(cv~>nets) length(cv~>terminals))",
        "  dbClose(cv) t))",
        "if(errset(tfBuild() t) then exit(0) else exit(1))",
    ]
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=False)
    blob = ("\n".join(lines) + "\n").encode("ascii")
    (out / "build.il").write_bytes(blob)
    write_json(out / "content.json", content)
    write_json(out / "intent.json", dict(identity=identity, library=cfg["library"], cell=CELL, view=VIEW, source=SOURCE,
                                         build_il_sha256=hashlib.sha256(blob).hexdigest(),
                                         content_sha256=hashlib.sha256((out / "content.json").read_bytes()).hexdigest(),
                                         rects=len(content.get("rects", [])), pcells=len(content.get("pcells", [])),
                                         terminals=len(content.get("terminals", []))))
    return out


def build_view(identity):
    out = WORK / identity
    intent = json.loads((out / "intent.json").read_bytes())
    files = {n: (out / n).read_bytes() for n in ("build.il", "intent.json")}
    if hashlib.sha256(files["build.il"]).hexdigest() != intent["build_il_sha256"]:
        raise ValueError("build.il differs from its intent")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    cell_dir = f"{cfg['library_path']}/{CELL}"
    guarded = " ".join(q(f"{cell_dir}/{v}/layout.oa") for v in READ_ONLY)
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}", "flock -w 300 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
              f"if find {q(cell_dir)} -name '*.cdslck*' | grep -q .; then echo EDIT_LOCK_PRESENT; exit 4; fi",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script += [f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
               f"grep -q -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' cds.lib || "
               f"grep -m1 -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' /home/dmanager/shared_lib/TSMC28/cds.lib >> cds.lib",
               f"before=$(sha256sum {guarded} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_BEFORE=$before", "rc=0",
               f"timeout -k 10 600 tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log build.log -restore build.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?",
               f"after=$(sha256sum {guarded} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_AFTER=$after",
               "test \"$before\" = \"$after\" || { echo READ_ONLY_VIEW_CHANGED; rc=5; }",
               "sha256sum build.il intent.json cds.lib", f"sha256sum {q(cell_dir + '/' + VIEW + '/layout.oa')} || true",
               "grep -E '^FULL_BUILD_OK|\\*Error\\*' oa.console || true", "echo PCELLS=$(grep -c '^PCELL' oa.console || true)",
               "echo EXIT=$rc", "exit $rc"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=720)
    text = run.stdout.decode("utf-8", "replace")
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, returncode=run.returncode,
                   stdout=text.splitlines(), stderr=run.stderr.decode("utf-8", "replace").splitlines()[-20:],
                   ok=run.returncode == 0 and "FULL_BUILD_OK" in text)
    write_json(out / "build.json", receipt)
    if not receipt["ok"]:
        raise RuntimeError("Build failed; see " + str(out / "build.json"))
    return receipt


BRANCH_TEXT = {"north": "A", "south": "P", "east": "D"}


def branch_labels(src, out):
    """Copy of a stream for connectivity checks: the VDD!/0 pin texts renamed per supply branch by the edge they
    sit on (north A, south P, east D), so the extraction shows that the branches stay separate inside the core."""
    import gdstk
    lib = gdstk.read_gds(str(src))
    top = next(c for c in lib.cells if c.name == CELL)
    renamed = []
    for lab in list(top.labels):
        if lab.text not in ("VDD!", "0"):
            continue
        x, y = lab.origin
        edge = "north" if y > 110 else "south" if y < 1 else "east" if x > 121 else None
        if edge is None:
            raise ValueError(f"Supply text {lab.text} at {lab.origin} is on no boundary")
        new = ("VDD_" if lab.text == "VDD!" else "VSS_") + BRANCH_TEXT[edge]
        top.remove(lab)
        top.add(gdstk.Label(new, lab.origin, layer=lab.layer, texttype=lab.texttype))
        renamed.append((lab.text, new, [round(x, 3), round(y, 3)]))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    lib.write_gds(str(out))
    return renamed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("build-script")
    a.add_argument("identity")
    a.add_argument("content")
    a = sub.add_parser("build")
    a.add_argument("identity")
    a = sub.add_parser("branch-labels")
    a.add_argument("src")
    a.add_argument("out")
    args = ap.parse_args()
    if args.action == "branch-labels":
        print(json.dumps(branch_labels(args.src, args.out), indent=1))
    elif args.action == "build-script":
        print(build_script(args.identity, json.loads(Path(args.content).read_bytes())))
    else:
        r = build_view(args.identity)
        print(json.dumps(dict(ok=r["ok"], stdout=r["stdout"]), indent=1))


if __name__ == "__main__":
    main()
