"""Chip-level objects of the 9 x 9 IO ring plan (Layout/design/io_ring.json) as their own cells in SAR_ADC_T28_LAYOUT,
and their native checks (chenzc24/sar-adc-t28#12, #18).

Every object cell is drawn in die coordinates, so the chip cell places it at the origin, R0.
- `content OBJECT OUT.json` writes the geometry of one object (Layout/design/chip_objects_geometry.py).
- `build-script ID CONTENT.json` writes build.il; `build ID` runs it once on the layout host under the shared layout
  lock. It creates the cell's view, or replaces a view that carries this generator's owner property and nothing
  else, and checks that every guarded cellview's layout.oa is byte-identical afterwards.
- `physical ID --top CELL (--view V | --gds FILE) --stages drc,lvs` uploads Layout/tools/physical/cell_physical.py
  with its helpers into a fresh evidence directory and starts it in the background; `status ID` and
  `fetch ID PATH...` read its results.
Results go to work/layout/chip-objects/<ID>/.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

from Layout.design.toplevel_route import CADENCE, IDENTITY, STANDARD_LIBRARY, num, sk, ssh
from Layout.project import ROOT, config, write_json

WORK = ROOT / "work/layout/chip-objects"
PHYSICAL = ROOT / "Layout/tools/physical"
OWNER = "Layout/design/chip_objects.py"
PDK_LIBRARY = "tsmcN28"
PCELLS = {"nmoscap", "rupolym", "cfmom_2t"}
SHARED_CDS = "/home/dmanager/shared_lib/TSMC28/cds.lib"
PAD_LIBRARY = "PAD"                      # PAD60GU bond pads of the ring (as Layout/design/chip_assembly.py)
SEAL_LIBRARY = "sealring"                # the lab's shared seal-ring kit (shared cds.lib)
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,63}")


def io_library():
    return json.loads((ROOT / "Layout/design/io_ring.json").read_text(encoding="utf-8"))["ring"]["io_library"]


def build_script(identity, content, guarded=()):
    """build.il for one object cell; content: cell, view, instances, pcells, rects, terminals, labels."""
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    cfg = config()
    lib = sk(cfg["library"])
    cell, view = content["cell"], content.get("view", "layout")
    if not (NAME.fullmatch(cell) and re.fullmatch(r"layout[a-z0-9_]*", view)):
        raise ValueError("Invalid cell or view")
    nets = sorted({r["net"] for r in content.get("rects", []) if r.get("net")}
                  | {t["net"] for t in content.get("terminals", [])}
                  | {n for p in content.get("pcells", []) + content.get("instances", [])
                     for n in p.get("nets", {}).values()})
    lines = [
        'procedure(coNeed(ok message) unless(ok error("%s\\n" message)))',
        "procedure(coNet(cv name) or(dbFindNetByName(cv name) dbCreateNet(cv name)))",
        "procedure(coRect(cv layer purpose net box) let((f) f=dbCreateRect(cv list(layer purpose) box)"
        ' coNeed(f sprintf(nil "Cannot draw %s on %s" net layer)) when(net!="" dbAddFigToNet(f coNet(cv net))) f))',
        "procedure(coBind(cv inst term net) let((tm) tm=dbFindTermByName(inst~>master term)"
        ' coNeed(tm sprintf(nil "No terminal %s on %s" term inst~>cellName))'
        ' coNeed(dbCreateInstTerm(coNet(cv net) inst tm) sprintf(nil "Cannot bind %s.%s" inst~>name term))))',
        "procedure(coBuild()",
        " let((dd old cv src)",
        f"  dd=ddGetObj({lib})",
        f"  coNeed(dd && dd~>readPath=={sk(cfg['library_path'])} \"Wrong layout library\")",
        f"  old=ddGetObj({lib} {sk(cell)} {sk(view)})",
        "  when(old",
        f"   cv=dbOpenCellViewByType({lib} {sk(cell)} {sk(view)} \"maskLayout\" \"r\")",
        f"   coNeed(cv && dbGetPropByName(cv \"generatorOwner\")~>value=={sk(OWNER)} \"Existing view is not ours\")",
        "   dbClose(cv))",
    ]
    if content.get("copy_from"):
        # Copy the source view (it stays read-only and guarded) and add to the copy; overwrite in place (g_overwrite)
        # so that a reader's OA cache elsewhere does not block the replacement.
        scell, sview = content["copy_from"]
        lines += [
            f"  src=dbOpenCellViewByType({lib} {sk(scell)} {sk(sview)} \"maskLayout\" \"r\")",
            f"  coNeed(src \"Cannot open {scell}/{sview}\")",
            f"  old=dbCopyCellView(src {lib} {sk(cell)} {sk(view)} nil nil t)",
            f"  coNeed(old \"Cannot copy {scell}/{sview}\")",
            "  when(dbIsId(old) && old!=src dbClose(old))",
            "  dbClose(src)",
            f"  cv=dbOpenCellViewByType({lib} {sk(cell)} {sk(view)} \"maskLayout\" \"a\")",
            f"  coNeed(cv \"Cannot open the copy {cell}/{view}\")",
            '  dbReplaceProp(cv "copiedFrom" "string" ' + sk(scell + "/" + sview) + ")"]
        # Swap the master of a copied instance (same name, origin and orientation); the chip cell binds no instance
        # terminals, so nothing else refers to it.
        swaps = content.get("replace_masters", [])
        if swaps:
            lines[:0] = ["procedure(coSwap(cv name lib cell view) let((inst xy orient)"
                         " inst=car(setof(i cv~>instances i~>name==name))"
                         ' coNeed(inst sprintf(nil "No instance %s" name)) xy=inst~>xy orient=inst~>orient'
                         " dbDeleteObject(inst) inst=dbCreateInstByMasterName(cv lib cell view name xy orient)"
                         ' coNeed(inst sprintf(nil "Cannot place %s/%s/%s" lib cell view))'
                         ' printf("SWAPPED %s %s/%s/%s %L %s\\n" name lib cell view xy orient)))']
        if any("xy" in s for s in swaps):
            # A swap that also moves the instance (a re-tiled seal ring keeps its orientation, not its origin).
            lines[:0] = ["procedure(coSwapAt(cv name lib cell view xy) let((inst orient)"
                         " inst=car(setof(i cv~>instances i~>name==name))"
                         ' coNeed(inst sprintf(nil "No instance %s" name)) orient=inst~>orient'
                         " dbDeleteObject(inst) inst=dbCreateInstByMasterName(cv lib cell view name xy orient)"
                         ' coNeed(inst sprintf(nil "Cannot place %s/%s/%s" lib cell view))'
                         ' printf("SWAPPED %s %s/%s/%s %L %s\\n" name lib cell view xy orient)))']
        for s in swaps:
            if "xy" in s:
                lines.append(f"  coSwapAt(cv {sk(s['inst'])} {sk(s['lib'])} {sk(s['cell'])} {sk(s['view'])} "
                             f"list({num(s['xy'][0])} {num(s['xy'][1])}))")
            else:
                lines.append(f"  coSwap(cv {sk(s['inst'])} {sk(s['lib'])} {sk(s['cell'])} {sk(s['view'])})")
    else:
        lines += [
            f"  cv=dbOpenCellViewByType({lib} {sk(cell)} {sk(view)} \"maskLayout\" \"w\")",
            f"  coNeed(cv \"Cannot open {cell}/{view} for writing\")"]
    lines += [
        '  dbReplaceProp(cv "generatorOwner" "string" ' + sk(OWNER) + ")",
        '  dbReplaceProp(cv "buildIdentity" "string" ' + sk(identity) + ")",
        "  foreach(n '(" + " ".join(sk(n) for n in nets) + ") coNet(cv n))",
    ]
    groups = []
    for p in content.get("instances", []):
        g = [f"  inst=dbCreateInstByMasterName(cv {sk(p['lib'])} {sk(p['cell'])} {sk(p.get('view', 'layout'))} "
             f"{sk(p['name'])} list({num(p['xy'][0])} {num(p['xy'][1])}) {sk(p.get('orient', 'R0'))})",
             f"  coNeed(inst \"Cannot place {p['name']}\")"]
        g += [f"  coBind(cv inst {sk(t)} {sk(n)})" for t, n in p.get("nets", {}).items()]
        groups.append(g)
    for p in content.get("pcells", []):
        if p["cell"] not in PCELLS:
            raise ValueError("Unexpected PCell " + p["cell"])
        params = " ".join(f"list({sk(k)} \"string\" {sk(v)})" for k, v in p["params"].items())
        g = [f"  inst=dbCreateParamInstByMasterName(cv {sk(PDK_LIBRARY)} {sk(p['cell'])} \"layout\" {sk(p['name'])}"
             f" list({num(p['xy'][0])} {num(p['xy'][1])}) {sk(p.get('orient', 'R0'))} 1 list({params}))",
             f"  coNeed(inst \"Cannot place {p['name']}\")"]
        g += [f"  coBind(cv inst {sk(t)} {sk(n)})" for t, n in p.get("nets", {}).items()]
        groups.append(g)
    for r in content.get("rects", []):
        groups.append([f"  coRect(cv {sk(r['layer'])} {sk(r.get('purpose', 'drawing'))} {sk(r.get('net', ''))} "
                       f"list({num(r['box'][0])}:{num(r['box'][1])} {num(r['box'][2])}:{num(r['box'][3])}))"])
    for t in content.get("terminals", []):
        g = [f"  net=coNet(cv {sk(t['net'])}) term=or(dbFindTermByName(cv {sk(t['net'])})"
             f" dbCreateTerm(net {sk(t['net'])} {sk(t.get('direction', 'inputOutput'))}))"]
        for i, pin in enumerate(t["pins"]):
            x0, y0, x1, y1 = pin["box"]
            # The LVS deck connects only drawing metal: every pin figure also gets its drawing rectangle.
            g.append(f"  coRect(cv {sk(pin['layer'])} \"drawing\" {sk(t['net'])} list({num(x0)}:{num(y0)} {num(x1)}:{num(y1)}))")
            g.append(f"  fig=dbCreateRect(cv list({sk(pin['layer'])} \"pin\") list({num(x0)}:{num(y0)} {num(x1)}:{num(y1)}))")
            g.append(f"  coNeed(fig && dbCreatePin(net fig {sk(t['net'] + '_' + str(i))} term) \"Cannot pin {t['net']}\")")
            g.append(f"  dbCreateLabel(cv list({sk(pin['layer'])} \"pin\") {num((x0 + x1) / 2)}:{num((y0 + y1) / 2)} "
                     f"{sk(t['net'])} \"centerCenter\" \"R0\" \"roman\" 0.2)")
        groups.append(g)
    for t in content.get("labels", []):
        groups.append([f"  dbCreateLabel(cv list({sk(t['layer'])} \"pin\") {num(t['xy'][0])}:{num(t['xy'][1])} "
                       f"{sk(t['net'])} \"centerCenter\" \"R0\" \"roman\" 0.2)"])
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
        defs += [f"procedure(coPart{i}(cv)", " let((inst term net fig)"] + body + ["  t))"]
        lines.append(f"  coPart{i}(cv)")
    lines[:0] = defs
    lines += [
        f'  coNeed(dbSave(cv) "Cannot save {cell}/{view}")',
        '  printf("OBJECT_BUILD_OK cell=%s shapes=%d instances=%d nets=%d terminals=%d bBox=%L\\n" cv~>cellName'
        " length(cv~>shapes) length(cv~>instances) length(cv~>nets) length(cv~>terminals) cv~>bBox)",
        "  dbClose(cv) t))",
        "if(errset(coBuild() t) then exit(0) else exit(1))",
    ]
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=False)
    blob = ("\n".join(lines) + "\n").encode("ascii")
    (out / "build.il").write_bytes(blob)
    write_json(out / "content.json", content)
    write_json(out / "intent.json", dict(identity=identity, library=cfg["library"], cell=cell, view=view,
                                         guarded=[list(g) for g in guarded],
                                         build_il_sha256=hashlib.sha256(blob).hexdigest(),
                                         content_sha256=hashlib.sha256((out / "content.json").read_bytes()).hexdigest(),
                                         rects=len(content.get("rects", [])), pcells=len(content.get("pcells", [])),
                                         instances=len(content.get("instances", [])),
                                         terminals=len(content.get("terminals", []))))
    return out


def build_view(identity, timeout=1200):
    out = WORK / identity
    intent = json.loads((out / "intent.json").read_bytes())
    files = {n: (out / n).read_bytes() for n in ("build.il", "intent.json")}
    if hashlib.sha256(files["build.il"]).hexdigest() != intent["build_il_sha256"]:
        raise ValueError("build.il differs from its intent")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    cell_dir = f"{cfg['library_path']}/{intent['cell']}"
    guarded = " ".join(q(f"{cfg['library_path']}/{c}/{v}/layout.oa") for c, v in intent["guarded"])
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}", "flock -w 600 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
              f"if test -d {q(cell_dir)} && find {q(cell_dir)} -name '*.cdslck*' | grep -q .; then echo EDIT_LOCK_PRESENT; exit 4; fi",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script.append(f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib")
    for lib in (STANDARD_LIBRARY, io_library(), PAD_LIBRARY, SEAL_LIBRARY):
        script.append(f"grep -q -E '^DEFINE[[:space:]]+{lib}[[:space:]]' cds.lib || "
                      f"grep -m1 -E '^DEFINE[[:space:]]+{lib}[[:space:]]' {SHARED_CDS} >> cds.lib")
    if guarded:
        script += [f"before=$(sha256sum {guarded} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_BEFORE=$before"]
    script += ["rc=0",
               f"timeout -k 10 {timeout} tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log build.log -restore build.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?"]
    if guarded:
        script += [f"after=$(sha256sum {guarded} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_AFTER=$after",
                   "test \"$before\" = \"$after\" || { echo GUARDED_VIEW_CHANGED; rc=5; }"]
    script += ["sha256sum build.il intent.json cds.lib",
               f"sha256sum {q(cell_dir + '/' + intent['view'] + '/layout.oa')} || true",
               "grep -E '^OBJECT_BUILD_OK|\\*Error\\*|^\\*WARNING\\*' oa.console | head -40 || true",
               "echo EXIT=$rc", "exit $rc"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=timeout + 300)
    text = run.stdout.decode("utf-8", "replace")
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, cell=intent["cell"], view=intent["view"],
                   returncode=run.returncode, stdout=text.splitlines(),
                   stderr=run.stderr.decode("utf-8", "replace").splitlines()[-20:],
                   ok=run.returncode == 0 and "OBJECT_BUILD_OK" in text)
    write_json(out / "build.json", receipt)
    if not receipt["ok"]:
        raise RuntimeError("Build failed; see " + str(out / "build.json"))
    return receipt


IO_SPICE = ("/home/process/tsmc28n/IO/{lib}_170a/0971001_20180621/{lib}_110a_spi/TSMCHOME/digital/Back_End/spice/"
            "{lib}_110a/{lib}.spi")


def lvs_source(content):
    """CDL of one object cell from its content: PDK PCells as their LVS devices, library instances as subcircuit
    calls (the IO library's foundry SPICE is included for its cells), ports = the terminal nets."""
    ports = [t["net"] for t in content.get("terminals", [])]
    lines = [f"* LVS source of {content['cell']}: Layout/design/chip_objects.py"]
    io = io_library()
    if any(i["lib"] == io for i in content.get("instances", [])):
        lines.append(f'.INCLUDE "{IO_SPICE.format(lib=io)}"')
    lines.append(f".SUBCKT {content['cell']} " + " ".join(ports))
    for i in content.get("instances", []):
        if i["lib"] == io:
            order = {"PCLAMPC_H_G": ["VDDESD", "VSSESD"]}[i["cell"]]
            lines.append(f"X{i['name']} " + " ".join(i["nets"][p] for p in order) + f" {i['cell']}")
        else:
            raise ValueError("No LVS source rule for " + i["cell"])
    for p in content.get("pcells", []):
        prm = p["params"]
        if p["cell"] == "nmoscap":
            lines.append(f"X{p['name']} {p['nets']['PLUS']} {p['nets']['MINUS']} nmoscap wr={prm['wr']} lr={prm['lr']}")
        elif p["cell"] == "cfmom_2t":
            lines.append(f"X{p['name']} {p['nets']['PLUS']} {p['nets']['MINUS']} cfmom_2t nr={prm['Nfinger']} "
                         f"lr={prm['Lfinger']} w={prm['Wfinger']} s={prm['Sfinger']} stm={prm['StartMn']} "
                         f"spm={prm['StopMn']} multi=1")
        else:
            raise ValueError("No LVS source rule for " + p["cell"])
    lines.append(f".ENDS {content['cell']}")
    return "\n".join(lines) + "\n"


def query(identity, il, timeout=600):
    """Run a read-only SKILL job (it must not save anything) in a fresh evidence directory; returns its console."""
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    if re.search(r"dbSave|dbCopy|ddDelete|dbOpenCellViewByType\([^)]*\"[aw]\"", il):
        raise ValueError("A query job must not write OA")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    blob = il.encode("ascii")
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}",
              "base64 -d > job.il <<'B64'", base64.b64encode(blob).decode("ascii"), "B64",
              f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib"]
    for lib in (STANDARD_LIBRARY, io_library(), PAD_LIBRARY, SEAL_LIBRARY):
        script.append(f"grep -q -E '^DEFINE[[:space:]]+{lib}[[:space:]]' cds.lib || "
                      f"grep -m1 -E '^DEFINE[[:space:]]+{lib}[[:space:]]' {SHARED_CDS} >> cds.lib")
    script += ["rc=0", f"timeout -k 10 {timeout} tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log job.log -restore job.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?", "cat oa.console", "echo EXIT=$rc", "exit $rc"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=timeout + 120)
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=True)
    (out / "job.il").write_bytes(blob)
    (out / "oa.console").write_bytes(run.stdout)
    if run.returncode:
        raise RuntimeError(f"SKILL query failed ({run.returncode}); see {out / 'oa.console'}")
    return run.stdout.decode("utf-8", "replace")


def physical(identity, top, view=None, gds=None, stages="drc", deck="cell", source=None, hcells=None, virtual=None,
             colon_no=False, std_cells=False, flat=False, select_prefix="", ring_deck=False):
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    if bool(view) == bool(gds):
        raise ValueError("Select exactly one of --view and --gds")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    files = {name: (PHYSICAL / name).read_bytes() for name in ("cell_physical.py", "run_physical.py", "workspace.py")}
    arguments = ["python", "-u", "cell_physical.py", identity, "--top", top, "--lock",
                 cfg["legacy_root"] + "/layout.lock", "--stages", stages, "--deck", deck]
    if view:
        arguments += ["--view", view]
    else:
        files["candidate.gds"] = Path(gds).read_bytes()
        arguments += ["--gds", "candidate.gds"]
    if source:
        files["source.cdl"] = Path(source).read_bytes()
        arguments += ["--source", "source.cdl"]
    if hcells:
        files["hcells.txt"] = ("\n".join(hcells) + "\n").encode("ascii")
        arguments += ["--hcells", "hcells.txt"]
    if virtual:
        arguments += ["--virtual", ",".join(virtual)]
    if colon_no:
        arguments.append("--colon-no")
    if std_cells:
        arguments.append("--std-cells")
    if flat:
        arguments.append("--flat")
    if select_prefix:
        arguments += ["--select-prefix", select_prefix]
    if ring_deck:
        arguments.append("--ring-deck")
    script =["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script.append(f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib")
    for lib in (STANDARD_LIBRARY, io_library(), PAD_LIBRARY, SEAL_LIBRARY):
        script.append(f"grep -q -E '^DEFINE[[:space:]]+{lib}[[:space:]]' cds.lib || "
                      f"grep -m1 -E '^DEFINE[[:space:]]+{lib}[[:space:]]' {SHARED_CDS} >> cds.lib")
    script += ["sha256sum " + " ".join(files) + " cds.lib",
               "nohup " + " ".join(q(a) for a in arguments) + " > driver.log 2>&1 < /dev/null &", "echo PID=$!"]
    text = ssh("\n".join(script), timeout=300).decode("utf-8", "replace")
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, arguments=arguments,
                   uploaded_sha256={n: hashlib.sha256(b).hexdigest() for n, b in files.items()}, stdout=text.splitlines())
    write_json(WORK / identity / "launch.json", receipt)
    return receipt


def status(identity):
    cfg = config()
    path = f"{cfg['remote_root']}/evidence/{identity}"
    raw = ssh(f"cat {shlex.quote(path + '/manifest.json')}; echo; tail -n 5 {shlex.quote(path + '/driver.log')}")
    text = raw.decode("utf-8", "replace")
    manifest, _, tail = text.partition("\n}\n")
    m = json.loads(manifest + "\n}")
    write_json(WORK / identity / "manifest.json", m)
    keys = ("status", "returncode", "markers", "markers_by_rule", "verdict", "results_by_check", "rulechecks_executed")
    return dict(identity=identity, done=m.get("done", False), error=m.get("error"),
                checks={k: {x: v[x] for x in keys if x in v} for k, v in m["checks"].items()},
                driver_tail=tail.strip().splitlines())


def fetch(identity, paths):
    cfg = config()
    base = f"{cfg['remote_root']}/evidence/{identity}"
    dest = WORK / identity
    dest.mkdir(parents=True, exist_ok=True)
    for rel in paths:
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError("Unsafe path " + rel)
        blob = ssh(f"cat {shlex.quote(base + '/' + rel)}", timeout=600)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return [str(dest / p) for p in paths]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("content")
    a.add_argument("object")
    a.add_argument("out")
    a = sub.add_parser("build-script")
    a.add_argument("identity")
    a.add_argument("content")
    a.add_argument("--guard", nargs="*", default=[], help="CELL/VIEW whose layout.oa must not change")
    a = sub.add_parser("build")
    a.add_argument("identity")
    a = sub.add_parser("physical")
    a.add_argument("identity")
    a.add_argument("--top", required=True)
    a.add_argument("--view")
    a.add_argument("--gds")
    a.add_argument("--stages", default="drc")
    a.add_argument("--deck", choices=("cell", "chip", "chip-noseal"), default="cell")
    a.add_argument("--source")
    a.add_argument("--hcells", nargs="*")
    a.add_argument("--virtual", nargs="*")
    a.add_argument("--colon-no", action="store_true")
    a.add_argument("--std-cells", action="store_true")
    a.add_argument("--flat", action="store_true", help="flat DRC (net-based rules such as LUP)")
    a.add_argument("--select-prefix", default="", help="comma-separated rule-name prefixes to select")
    a.add_argument("--ring-deck", action="store_true", help="LVS with the ring deck lines, joining only --virtual")
    a = sub.add_parser("status")
    a.add_argument("identity")
    a = sub.add_parser("fetch")
    a.add_argument("identity")
    a.add_argument("paths", nargs="+")
    args = ap.parse_args()
    if args.action == "content":
        from Layout.design import chip_objects_geometry as geometry
        content, summary = geometry.OBJECTS[args.object]()
        write_json(args.out, content)
        print(json.dumps(summary, indent=1))
    elif args.action == "build-script":
        content = json.loads(Path(args.content).read_text(encoding="utf-8"))
        print(build_script(args.identity, content, [tuple(g.split("/")) for g in args.guard]))
    elif args.action == "build":
        r = build_view(args.identity)
        print(json.dumps({k: r[k] for k in ("identity", "cell", "ok")}, indent=1))
        print("\n".join(r["stdout"][-12:]))
    elif args.action == "physical":
        print(json.dumps(physical(args.identity, args.top, args.view, args.gds, args.stages, args.deck, args.source,
                                  args.hcells, args.virtual, args.colon_no, args.std_cells, args.flat,
                                  args.select_prefix, args.ring_deck)["stdout"], indent=1))
    elif args.action == "status":
        print(json.dumps(status(args.identity), indent=1))
    else:
        print("\n".join(fetch(args.identity, args.paths)))


if __name__ == "__main__":
    main()
