"""Core-internal routing of the ADC core (Stage 4a of chenzc24/sar-adc-t28#12) and its native checks.

The route geometry is Layout/design/toplevel_routes.py. Every result file goes to work/layout/toplevel-route/<ID>/.
- `generate ID --base GDS` merges the routes into a stream of the placement view (candidate.gds, routes.json),
  for checks before any OA write.
- `build-script ID --cell C --view V` writes build.il; `build ID` runs it once on the layout host under the shared
  layout lock. It creates a new view only, copies the placement view's instances and boundary and checks that
  the placement layout.oa is byte-identical afterwards.
- `physical ID (--view V | --gds FILE)` uploads Layout/tools/physical/toplevel_physical.py with its helpers into a
  fresh evidence directory and starts DRC, the HCELL netlist and/or xRC in the background; it reads OA only
  through strmout. `status ID` reads the manifest, `fetch ID PATH...` copies result files.
- `pex-input` adds extraction-only labels to a stream; `compare` checks that two streams have the same top cell.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

from Layout.project import ROOT, config, write_json

WORK = ROOT / "work/layout/toplevel-route"
PHYSICAL = ROOT / "Layout/tools/physical"
STANDARD_LIBRARY = "tcbn28hpcplusbwp12t30p140"
IDENTITY = re.compile(r"[a-z0-9][a-z0-9-]{1,55}")


def ssh(script, timeout=60):
    cfg = config()
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input=script.encode("ascii"), capture_output=True, timeout=timeout)
    if run.returncode:
        raise RuntimeError(run.stderr.decode("utf-8", "replace") + run.stdout.decode("utf-8", "replace"))
    return run.stdout


PAIR = "sar8_cdac_with_xref"


def block_masters(gds):
    """Block masters of the core: the top's children, with the XREF/CDAC pair replaced by its two blocks."""
    import gdstk
    lib = gdstk.read_gds(str(gds))
    cells = {c.name: c for c in lib.cells}
    top = {r.cell.name for r in cells["sar8_adc_core"].references}
    pair = {r.cell.name for r in cells[PAIR].references if "_CDNS_" not in r.cell.name}
    if PAIR not in top or len(pair) != 2:
        raise ValueError("Unexpected block hierarchy")
    return sorted((top - {PAIR}) | pair)


def generate(identity, base):
    """Merge the routes into a placement stream: candidate.gds, routes.json and the block master list."""
    from Layout.design.toplevel_routes import FLOORPLAN, build, overlay
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=False)
    routes = build()
    overlay(routes, base, out / "candidate.gds")
    record = dict(identity=identity, base_gds=str(Path(base).resolve().relative_to(ROOT)),
                  base_gds_sha256=hashlib.sha256(Path(base).read_bytes()).hexdigest(),
                  floorplan_sha256=hashlib.sha256(FLOORPLAN.read_bytes()).hexdigest(),
                  routes_sha256=hashlib.sha256((ROOT / "Layout/design/toplevel_routes.py").read_bytes()).hexdigest(),
                  candidate_sha256=hashlib.sha256((out / "candidate.gds").read_bytes()).hexdigest(),
                  hcells=block_masters(base),
                  rects=[[s.net, s.layer, s.x0, s.y0, s.x1, s.y1, s.role] for s in routes.rects],
                  labels=[[t.net, t.layer, t.x, t.y] for t in routes.labels])
    write_json(out / "routes.json", record)
    return dict(out=str(out), rects=len(record["rects"]), labels=len(record["labels"]), hcells=record["hcells"])


SHIELD_LABEL = ("VSS_SHIELD", "M5", 60.0, 74.1)
CADENCE = "/home/cshrc/.cshrc.cadence.IC618SP201"
PLACEMENT = ("sar8_adc_core", "layout_place")
NAME = re.compile(r"[a-z][a-z0-9_]{1,40}")


def sk(value):
    return '"' + value + '"'


def num(value):
    return format(value, ".3f")


def build_script(identity, cell, view):
    """build.il: a new view with the placement view's instances and boundary, plus the routes and labels.

    The placement view is opened read-only. Shapes are plain rectangles (via cuts included) so that the
    stream is exactly the geometry of toplevel_routes; nets are OA nets on the shapes, named on the wire
    by pin-purpose labels like the block generators do."""
    from Layout.design.toplevel_routes import build
    if not (IDENTITY.fullmatch(identity) and NAME.fullmatch(cell) and NAME.fullmatch(view)):
        raise ValueError("Invalid identity, cell or view")
    if (cell, view) == PLACEMENT:
        raise ValueError("The placement view is read-only")
    cfg = config()
    routes = build()
    nets = sorted({s.net for s in routes.rects})
    lib = sk(cfg["library"])
    lines = [
        'procedure(trNeed(ok message) unless(ok error("%s\\n" message)))',
        "procedure(trRect(cv layer net box) let((f) f=dbCreateRect(cv list(layer \"drawing\") box)"
        ' trNeed(f sprintf(nil "Cannot draw %s on %s" net layer)) dbAddFigToNet(f dbFindNetByName(cv net)) f))',
        "procedure(trBuild()",
        " let((dd src cv count)",
        f"  dd=ddGetObj({lib})",
        f"  trNeed(dd && dd~>readPath=={sk(cfg['library_path'])} \"Wrong layout library\")",
        f"  trNeed(!ddGetObj({lib} {sk(cell)} {sk(view)}) \"Target view already exists\")",
        f"  src=dbOpenCellViewByType({lib} {sk(PLACEMENT[0])} {sk(PLACEMENT[1])} \"maskLayout\" \"r\")",
        '  trNeed(src && length(src~>instances)==5 && length(src~>shapes)==1 && !src~>nets && !src~>terminals'
        ' "Unexpected placement view")',
        f"  cv=dbOpenCellViewByType({lib} {sk(cell)} {sk(view)} \"maskLayout\" \"w\")",
        '  trNeed(cv && !cv~>instances && !cv~>shapes "Cannot create the routed view")',
        "  foreach(i src~>instances trNeed(dbCreateInst(cv i~>master i~>name i~>xy i~>orient)"
        ' sprintf(nil "Cannot place %s" i~>name)))',
        "  foreach(s src~>shapes trNeed(dbCreateRect(cv s~>lpp s~>bBox) \"Cannot copy the boundary\"))",
        "  foreach(i src~>instances let((j) j=dbFindAnyInstByName(cv i~>name)"
        "   trNeed(j && j~>libName==i~>libName && j~>cellName==i~>cellName && j~>viewName==i~>viewName"
        '    && j~>xy==i~>xy && j~>orient==i~>orient sprintf(nil "Instance %s differs from the placement" i~>name))))',
        "  dbClose(src)",
        "  foreach(n '(" + " ".join(sk(n) for n in nets) + ") trNeed(dbCreateNet(cv n) \"Cannot create net\"))",
    ]
    for s in routes.rects:
        lines.append(f"  trRect(cv {sk(s.layer)} {sk(s.net)} list({num(s.x0)}:{num(s.y0)} {num(s.x1)}:{num(s.y1)}))")
    for t in routes.labels:
        lines.append(f"  trNeed(dbCreateLabel(cv list({sk(t.layer)} \"pin\") {num(t.x)}:{num(t.y)} {sk(t.net)}"
                     ' "centerCenter" "R0" "roman" 0.1) "Cannot label")')
    lines += [
        f"  count=length(cv~>shapes)",
        f"  trNeed(count=={len(routes.rects) + len(routes.labels) + 1} && length(cv~>instances)==5"
        f" && length(cv~>nets)=={len(nets)} && !cv~>terminals sprintf(nil \"Unexpected content: %d shapes\" count))",
        '  dbReplaceProp(cv "generatorOwner" "string" "Layout/design/toplevel_route.py")',
        '  trNeed(dbSave(cv) "Cannot save the routed view")',
        '  foreach(i cv~>instances printf("PLACED %s %s/%s/%s xy=%L orient=%s\\n" i~>name i~>libName i~>cellName'
        " i~>viewName i~>xy i~>orient))",
        '  foreach(n cv~>nets printf("NET %s shapes=%d\\n" n~>name length(n~>figs)))',
        '  printf("ROUTE_BUILD_OK shapes=%d instances=%d nets=%d bBox=%L\\n" count length(cv~>instances)'
        " length(cv~>nets) cv~>bBox)",
        "  dbClose(cv) t))",
        "if(errset(trBuild() t) then exit(0) else exit(1))",
    ]
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=False)
    blob = ("\n".join(lines) + "\n").encode("ascii")
    (out / "build.il").write_bytes(blob)
    intent = dict(identity=identity, library=cfg["library"], cell=cell, view=view, placement=list(PLACEMENT),
                  build_il_sha256=hashlib.sha256(blob).hexdigest(),
                  routes_sha256=hashlib.sha256((ROOT / "Layout/design/toplevel_routes.py").read_bytes()).hexdigest(),
                  floorplan_sha256=hashlib.sha256((ROOT / "Layout/design/floorplan.json").read_bytes()).hexdigest(),
                  rects=len(routes.rects), labels=len(routes.labels), nets=nets)
    write_json(out / "intent.json", intent)
    return out, intent


def build_view(identity):
    """Run build.il once on the layout host under the shared lock; the placement view must not change."""
    out = WORK / identity
    intent = json.loads((out / "intent.json").read_bytes())
    files = {name: (out / name).read_bytes() for name in ("build.il", "intent.json")}
    if hashlib.sha256(files["build.il"]).hexdigest() != intent["build_il_sha256"]:
        raise ValueError("build.il differs from its intent")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    place_oa = f"{cfg['library_path']}/{PLACEMENT[0]}/{PLACEMENT[1]}/layout.oa"
    target = f"{cfg['library_path']}/{intent['cell']}/{intent['view']}"
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"test ! -e {q(target)}",
              f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}", "flock -w 300 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
              f"if find {q(cfg['library_path'] + '/' + PLACEMENT[0])} -name '*.cdslck*' | grep -q .; then"
              " echo EDIT_LOCK_PRESENT; exit 4; fi",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script += [f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
               f"grep -q -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' cds.lib || "
               f"grep -m1 -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' /home/dmanager/shared_lib/TSMC28/cds.lib >> cds.lib",
               f"before=$(sha256sum {q(place_oa)} | cut -d' ' -f1)", "echo PLACEMENT_BEFORE=$before", "rc=0",
               f"timeout -k 10 300 tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log build.log -restore build.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?",
               f"after=$(sha256sum {q(place_oa)} | cut -d' ' -f1)", "echo PLACEMENT_AFTER=$after",
               "test \"$before\" = \"$after\" || { echo PLACEMENT_CHANGED; rc=5; }",
               "sha256sum build.il intent.json cds.lib", f"sha256sum {q(target + '/layout.oa')} || true",
               "grep -E '^(PLACED|NET|ROUTE_BUILD_OK)|\\*Error\\*' oa.console || true", "echo EXIT=$rc", "exit $rc"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=420)
    text = run.stdout.decode("utf-8", "replace")
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, returncode=run.returncode,
                   stdout=text.splitlines(), stderr=run.stderr.decode("utf-8", "replace").splitlines()[-20:],
                   ok=run.returncode == 0 and "ROUTE_BUILD_OK" in text)
    write_json(out / "build.json", receipt)
    if not receipt["ok"]:
        raise RuntimeError("Route build failed; see " + str(out / "build.json"))
    return receipt


def pex_input(src, out, kind):
    """Copy of a stream with extraction-only labels: `pins` names every planned landing pin NET__BLOCK on the
    placement view; `routed` names the floating shield of a routed view. Geometry is unchanged."""
    import gdstk
    from Layout.design.toplevel_routes import PIN_TEXT
    from Layout.tools.analysis.toplevel_route_precheck import LANDINGS, READBACK
    lib = gdstk.read_gds(str(src))
    top = next(c for c in lib.cells if c.name == "sar8_adc_core")
    if kind == "pins":
        pins = json.loads(READBACK.read_bytes())["pins"]
        labels = [(f"{net}__{name.split('.')[0]}", pins[name]["lpp"][0], *pins[name]["core_center"])
                  for net, names in LANDINGS.items() for name in names]
    else:
        labels = [SHIELD_LABEL]
    for text, layer, x, y in labels:
        top.add(gdstk.Label(text, (x, y), layer=PIN_TEXT[layer][0], texttype=PIN_TEXT[layer][1]))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    lib.write_gds(str(out))
    return dict(out=str(out), labels=labels)


def top_content(gds):
    """Order-independent content of the sar8_adc_core structure: shapes, texts and block references."""
    import gdstk
    lib = gdstk.read_gds(str(gds))
    top = next(c for c in lib.cells if c.name == "sar8_adc_core")
    shapes = sorted((p.layer, p.datatype, tuple(sorted((round(x, 4), round(y, 4)) for x, y in p.points)))
                    for p in top.polygons)
    texts = sorted((t.text, t.layer, t.texttype, round(t.origin[0], 4), round(t.origin[1], 4)) for t in top.labels)
    refs = sorted((r.cell.name, round(r.origin[0], 4), round(r.origin[1], 4), round(r.rotation or 0.0, 6),
                   bool(r.x_reflection)) for r in top.references)
    return dict(shapes=shapes, texts=texts, references=refs)


def compare_streams(a, b):
    ca, cb = top_content(a), top_content(b)
    return {k: dict(equal=ca[k] == cb[k], count=[len(ca[k]), len(cb[k])],
                    only_first=[list(x) for x in sorted(set(ca[k]) - set(cb[k]))][:10],
                    only_second=[list(x) for x in sorted(set(cb[k]) - set(ca[k]))][:10]) for k in ca}


def physical(identity, view=None, gds=None, through="drc", stages=None, hcells=None, source=None, virtual=None,
             top=None):
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    if bool(view) == bool(gds):
        raise ValueError("Select exactly one of --view and --gds")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    files = {name: (PHYSICAL / name).read_bytes() for name in ("toplevel_physical.py", "run_physical.py", "workspace.py")}
    arguments = ["python", "-u", "toplevel_physical.py", identity, "--lock", cfg["legacy_root"] + "/layout.lock",
                 "--through", through]
    if view:
        arguments += ["--view", view]
    else:
        files["candidate.gds"] = Path(gds).read_bytes()
        arguments += ["--gds", "candidate.gds"]
    if stages:
        arguments += ["--stages", stages]
    if hcells:
        files["hcells.txt"] = ("\n".join(hcells) + "\n").encode("ascii")
        arguments += ["--hcells", "hcells.txt"]
    if source:
        files["source.cdl"] = Path(source).read_bytes()
        arguments += ["--source", "source.cdl"]
    if virtual:
        arguments += ["--virtual", ",".join(virtual)]
    if top:
        arguments += ["--top", top]
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script += [f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
               f"grep -q -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' cds.lib || "
               f"grep -m1 -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' /home/dmanager/shared_lib/TSMC28/cds.lib >> cds.lib",
               "sha256sum " + " ".join(files) + " cds.lib",
               "nohup " + " ".join(q(a) for a in arguments) + " > driver.log 2>&1 < /dev/null &", "echo PID=$!"]
    text = ssh("\n".join(script), timeout=120).decode("utf-8", "replace")
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
    return dict(identity=identity, done=m.get("done", False), error=m.get("error"), gds=m.get("gds"),
                checks={k: {x: v[x] for x in ("status", "returncode", "markers", "markers_by_rule", "bytes") if x in v}
                        for k, v in m["checks"].items()}, driver_tail=tail.strip().splitlines())


def fetch(identity, paths):
    cfg = config()
    base = f"{cfg['remote_root']}/evidence/{identity}"
    dest = WORK / identity
    dest.mkdir(parents=True, exist_ok=True)
    for rel in paths:
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError("Unsafe path " + rel)
        blob = ssh(f"cat {shlex.quote(base + '/' + rel)}", timeout=300)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return [str(dest / p) for p in paths]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("generate")
    a.add_argument("identity")
    a.add_argument("--base", required=True, help="stream of the placement view")
    a = sub.add_parser("compare")
    a.add_argument("first")
    a.add_argument("second")
    a = sub.add_parser("build-script")
    a.add_argument("identity")
    a.add_argument("--cell", required=True)
    a.add_argument("--view", required=True)
    a = sub.add_parser("build")
    a.add_argument("identity")
    a = sub.add_parser("pex-input")
    a.add_argument("src")
    a.add_argument("out")
    a.add_argument("--kind", choices=("pins", "routed"), required=True)
    a = sub.add_parser("physical")
    a.add_argument("identity")
    a.add_argument("--view")
    a.add_argument("--gds")
    a.add_argument("--through", choices=("stream", "drc", "spice", "pex"), default="drc")
    a.add_argument("--stages")
    a.add_argument("--hcells-from", help="local stream whose block masters stay subcircuits in the netlist")
    a.add_argument("--source", help="local LVS source netlist (CDL) for --stages lvs")
    a.add_argument("--virtual", nargs="*", help="net names joined by VIRTUAL CONNECT NAME in the lvs stage")
    a.add_argument("--top", help="top cell when not sar8_adc_core (the fill wrapper sar8_adc_core_filled)")
    a = sub.add_parser("status")
    a.add_argument("identity")
    a = sub.add_parser("fetch")
    a.add_argument("identity")
    a.add_argument("paths", nargs="+")
    args = ap.parse_args()
    if args.action == "generate":
        result = generate(args.identity, args.base)
    elif args.action == "compare":
        result = compare_streams(args.first, args.second)
    elif args.action == "build-script":
        out, intent = build_script(args.identity, args.cell, args.view)
        result = dict(out=str(out), **{k: intent[k] for k in ("cell", "view", "rects", "labels", "nets")})
    elif args.action == "build":
        result = build_view(args.identity)
    elif args.action == "pex-input":
        result = pex_input(args.src, args.out, args.kind)
    elif args.action == "physical":
        hcells = block_masters(args.hcells_from) if args.hcells_from else None
        result = physical(args.identity, args.view, args.gds, args.through, args.stages, hcells, args.source,
                          args.virtual, args.top)
    elif args.action == "status":
        result = status(args.identity)
    else:
        result = fetch(args.identity, args.paths)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
