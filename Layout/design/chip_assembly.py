"""Chip assembly (Stage 5, partial): the ADC core and the IO ring in one chip cell, with the pad-to-core routes that
need no undrawn chip-level object.

`readback ID` reads the saved ring cell SAR_ADC_T28_LAYOUT/sar8_io_ring/layout read-only on the layout host: every
instance with its transform, the pin figures of every IO cell's terminals and the bond-opening shapes of the PAD
cells, all in ring (= die) coordinates. The pad landings and bond centres of the chip routes come from it, not from
cell-centre estimates (chenzc24/sar-adc-t28#18).
"""
import argparse
import base64
import hashlib
import json
import re
import shlex
import subprocess

from Layout.design.toplevel_route import CADENCE, IDENTITY, STANDARD_LIBRARY, sk
from Layout.project import ROOT, config, write_json

WORK = ROOT / "work/layout/chip"
RING = ("sar8_io_ring", "layout")
CORE = ("sar8_adc_core", "layout_route_guard")
IO_LIBRARY = "tphn28hpcpgv18"
PAD_LIBRARY = "PAD"                      # PAD60GU bond pads of the ring
SEAL_LIBRARY = "sealring"                # the lab's shared seal-ring kit (io_ring.json seal_ring)
SHARED_CDS = "/home/dmanager/shared_lib/TSMC28/cds.lib"


def run_skill(identity, il, guarded=(), timeout=900):
    """Run one SKILL file in a fresh evidence directory under the shared layout lock; guarded cellviews' layout.oa
    must not change."""
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    paths = " ".join(q(f"{cfg['library_path']}/{c}/{v}/layout.oa") for c, v in guarded)
    blob = il.encode("ascii")
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}", "flock -w 300 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}",
              "base64 -d > job.il <<'B64'", base64.b64encode(blob).decode("ascii"), "B64",
              f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib"]
    for lib in (STANDARD_LIBRARY, IO_LIBRARY, PAD_LIBRARY, SEAL_LIBRARY):
        script.append(f"grep -q -E '^DEFINE[[:space:]]+{lib}[[:space:]]' cds.lib || "
                      f"grep -m1 -E '^DEFINE[[:space:]]+{lib}[[:space:]]' {SHARED_CDS} >> cds.lib")
    if guarded:
        script += [f"before=$(sha256sum {paths} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_BEFORE=$before"]
    script += ["rc=0",
               f"timeout -k 10 {timeout} tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log job.log -restore job.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?"]
    if guarded:
        script += [f"after=$(sha256sum {paths} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_AFTER=$after",
                   "test \"$before\" = \"$after\" || { echo GUARDED_VIEW_CHANGED; rc=5; }"]
    script += ["sha256sum job.il cds.lib", "echo EXIT=$rc", "exit $rc"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=timeout + 120)
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=True)
    (out / "job.il").write_bytes(blob)
    console = subprocess.run(["ssh", "-o", "BatchMode=yes", cfg["host"], f"cat {q(evidence + '/oa.console')}"],
                             capture_output=True, timeout=300).stdout
    (out / "oa.console").write_bytes(console)
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, returncode=run.returncode,
                   job_il_sha256=hashlib.sha256(blob).hexdigest(), stdout=run.stdout.decode("utf-8", "replace").splitlines(),
                   stderr=run.stderr.decode("utf-8", "replace").splitlines()[-20:])
    write_json(out / "receipt.json", receipt)
    if run.returncode:
        raise RuntimeError(f"SKILL job failed ({run.returncode}); see {out / 'receipt.json'}")
    return receipt, console.decode("utf-8", "replace")


READBACK_IL = """
procedure(rbMain()
 let((cv lib)
  lib=%(lib)s
  cv=dbOpenCellViewByType(lib %(cell)s %(view)s "maskLayout" "r")
  unless(cv error("Cannot open the ring cell"))
  printf("RB_CV %%s %%L\\n" cv~>cellName cv~>bBox)
  foreach(s cv~>shapes when(s~>objType=="label" printf("RB_LABEL %%s %%s %%s %%L\\n" s~>theLabel s~>layerName s~>purpose s~>xy)))
  foreach(tm cv~>terminals foreach(p tm~>pins foreach(f list(p~>fig) when(f
   printf("RB_CVPIN %%s %%s %%s %%L\\n" tm~>name f~>layerName f~>purpose f~>bBox)))))
  foreach(i cv~>instances
   printf("RB_INST %%s %%s %%s %%s %%L %%L\\n" i~>name i~>libName i~>cellName i~>orient i~>xy i~>bBox)
   unless(rexMatchp("^P(FILLER|CORNER|RCUT)" i~>cellName)
    foreach(tm i~>master~>terminals
     foreach(p tm~>pins foreach(f list(p~>fig) when(f
      printf("RB_PIN %%s %%s %%s %%s %%L\\n" i~>name tm~>name f~>layerName f~>purpose dbTransformBBox(f~>bBox i~>transform))))))
    when(i~>cellName=="PAD60GU"
     foreach(s i~>master~>shapes when(member(s~>layerName '("AP" "CB" "CB2" "PM" "RDL"))
      printf("RB_PAD %%s %%s %%s %%L\\n" i~>name s~>layerName s~>purpose dbTransformBBox(s~>bBox i~>transform)))))))
  dbClose(cv)
  printf("RB_DONE\\n") t))
if(errset(rbMain() t) then exit(0) else exit(1))
"""


def parse_box(text):
    v = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", text)]
    return [v[0], v[1], v[2], v[3]]


def readback(identity):
    cfg = config()
    il = READBACK_IL % dict(lib=sk(cfg["library"]), cell=sk(RING[0]), view=sk(RING[1]))
    receipt, console = run_skill(identity, il, guarded=(RING,))
    if "RB_DONE" not in console:
        raise RuntimeError("Readback did not finish")
    data = dict(cell=dict(), labels=[], terminals=[], instances={}, pins=[], pads=[])
    for line in console.splitlines():
        tok = line.split(None, 1)
        if not tok or not tok[0].startswith("RB_"):
            continue
        kind, rest = tok[0], tok[1] if len(tok) > 1 else ""
        if kind == "RB_CV":
            name, box = rest.split(" ", 1)
            data["cell"] = dict(name=name, bbox=parse_box(box))
        elif kind == "RB_LABEL":
            m = re.match(r'(\S+) (\S+) (\S+) \((.*)\)', rest)
            data["labels"].append(dict(text=m.group(1), layer=m.group(2), purpose=m.group(3),
                                       xy=[float(x) for x in m.group(4).split()]))
        elif kind == "RB_CVPIN":
            name, layer, purpose, box = rest.split(" ", 3)
            data["terminals"].append(dict(net=name, layer=layer, purpose=purpose, bbox=parse_box(box)))
        elif kind == "RB_INST":
            name, lib, cell, orient, xy_box = rest.split(" ", 4)
            nums = parse_box(xy_box.replace("(", " ").replace(")", " ") + " 0 0")
            allv = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", xy_box)]
            data["instances"][name] = dict(lib=lib, cell=cell, orient=orient, xy=allv[:2], bbox=allv[2:6])
        elif kind == "RB_PIN":
            inst, term, layer, purpose, box = rest.split(" ", 4)
            data["pins"].append(dict(inst=inst, term=term, layer=layer, purpose=purpose, bbox=parse_box(box)))
        elif kind == "RB_PAD":
            inst, layer, purpose, box = rest.split(" ", 3)
            data["pads"].append(dict(inst=inst, layer=layer, purpose=purpose, bbox=parse_box(box)))
    data["receipt"] = dict(identity=identity, job_il_sha256=receipt["job_il_sha256"],
                           guarded=[l for l in receipt["stdout"] if l.startswith(("GUARDED", "EXIT"))])
    write_json(WORK / identity / "ring_readback.json", data)
    return {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in data.items() if k != "receipt"}


CHIP = ("sar8_adc_chip", "layout")
OWNER = "Layout/design/chip_assembly.py"
SI_ENV = ROOT.parent.parent / "t28-ioring/skills/t28-ioring-generator/calibre/T28/si_T28.env"


def export_ring_cdl(identity):
    """CDL of the ring cell's schematic with si (auCdl), the source the ring's own LVS used."""
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    cfg = config()
    q = shlex.quote
    env = SI_ENV.read_text(encoding="ascii")
    for k, v in {"@SI_RUN_DIR@": ".", "@NETLIST_FILE@": "sar8_io_ring.cdl", "@TOP_CELL@": RING[0],
                 "@LIBRARY@": cfg["library"], "@INC_FILE@": ""}.items():
        env = env.replace(k, v)
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}", f"test ! -e {q(evidence)}",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}",
              "base64 -d > si.env <<'B64'", base64.b64encode(env.encode("ascii")).decode("ascii"), "B64",
              f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
              f"grep -m1 -E '^DEFINE[[:space:]]+{IO_LIBRARY}[[:space:]]' {SHARED_CDS} >> cds.lib",
              f"grep -m1 -E '^DEFINE[[:space:]]+{PAD_LIBRARY}[[:space:]]' {SHARED_CDS} >> cds.lib",
              "echo 'DEFINE basic $CDSHOME/tools/dfII/etc/cdslib/basic' >> cds.lib",
              "rc=0",
              f"timeout -k 10 600 tcsh -fc {q('source ' + CADENCE + '; exec si . -batch -command netlist -cdslib ./cds.lib')}"
              " > si.console 2>&1 < /dev/null || rc=$?",
              "ls -la sar8_io_ring.cdl || true", "sha256sum si.env cds.lib sar8_io_ring.cdl || true", "tail -5 si.console",
              "echo EXIT=$rc", "exit $rc"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=900)
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=True)
    text = run.stdout.decode("utf-8", "replace")
    write_json(out / "receipt.json", dict(identity=identity, returncode=run.returncode, stdout=text.splitlines(),
                                          stderr=run.stderr.decode("utf-8", "replace").splitlines()[-20:]))
    if run.returncode:
        raise RuntimeError("si failed; see " + str(out / "receipt.json"))
    cdl = subprocess.run(["ssh", "-o", "BatchMode=yes", cfg["host"], f"cat {q(evidence + '/sar8_io_ring.cdl')}"],
                         capture_output=True, timeout=300).stdout
    (out / "sar8_io_ring.cdl").write_bytes(cdl)
    return dict(identity=identity, bytes=len(cdl), sha256=hashlib.sha256(cdl).hexdigest())


def build_il(content, labels):
    """SKILL that (re)creates the chip cell: the ring at the origin, the core at its placement, rects with nets, the
    labels as pin-purpose texts. An existing chip view is replaced only when it carries this generator's owner."""
    cfg = config()
    lib = sk(cfg["library"])
    x, y = (round(v, 4) for v in __import__("Layout.design.chip_routes", fromlist=["CORE_ORIGIN"]).CORE_ORIGIN)
    groups = [f"  tfRect(cv {sk(r['layer'])} {sk(r.get('purpose', 'drawing'))} {sk(r['net'])} "
              f"list({r['box'][0]}:{r['box'][1]} {r['box'][2]}:{r['box'][3]}))" for r in content.rects]
    groups += [f"  dbCreateLabel(cv list({sk(l['layer'])} \"pin\") {l['xy'][0]}:{l['xy'][1]} {sk(l['text'])} "
               '"centerCenter" "R0" "roman" 0.5)' for l in labels]
    parts = [groups[i:i + 1500] for i in range(0, len(groups), 1500)]
    lines = ['procedure(tfNeed(ok message) unless(ok error("%s\\n" message)))',
             "procedure(tfNet(cv name) or(dbFindNetByName(cv name) dbCreateNet(cv name)))",
             "procedure(tfRect(cv layer purpose net box) let((f) f=dbCreateRect(cv list(layer purpose) box)"
             ' tfNeed(f sprintf(nil "Cannot draw %s on %s" net layer)) when(net!="" dbAddFigToNet(f tfNet(cv net))) f))']
    for i, body in enumerate(parts):
        lines += [f"procedure(tfPart{i}(cv)", " let(()"] + body + ["  t))"]
    lines += ["procedure(tfBuild()",
              " let((src cv ring adc i)",
              f"  when(ddGetObj({lib} {sk(CHIP[0])} {sk(CHIP[1])})",
              f"   src=dbOpenCellViewByType({lib} {sk(CHIP[0])} {sk(CHIP[1])} \"maskLayout\" \"r\")",
              f"   tfNeed(src && dbGetPropByName(src \"generatorOwner\")~>value=={sk(OWNER)} \"Existing chip view is not ours\")",
              "   dbClose(src))",
              f"  ring=dbOpenCellViewByType({lib} {sk(RING[0])} {sk(RING[1])} \"maskLayout\" \"r\")",
              f"  adc=dbOpenCellViewByType({lib} {sk(CORE[0])} {sk(CORE[1])} \"maskLayout\" \"r\")",
              '  tfNeed(ring && adc "Cannot open the ring or the core")',
              f"  cv=dbOpenCellViewByType({lib} {sk(CHIP[0])} {sk(CHIP[1])} \"maskLayout\" \"w\")",
              '  tfNeed(cv "Cannot create the chip view")',
              '  tfNeed(dbCreateInst(cv ring "XRING" 0:0 "R0") "Cannot place the ring")',
              f'  tfNeed(dbCreateInst(cv adc "XADC" {x}:{y} "R0") "Cannot place the core")',
              '  dbReplaceProp(cv "generatorOwner" "string" ' + sk(OWNER) + ")"]
    lines += [f"  tfPart{i}(cv)" for i in range(len(parts))]
    lines += ['  tfNeed(dbSave(cv) "Cannot save the chip view")',
              '  printf("CHIP_BUILD_OK shapes=%d instances=%d nets=%d\\n" length(cv~>shapes) length(cv~>instances) length(cv~>nets))',
              "  dbClose(cv) dbClose(ring) dbClose(adc) t))",
              "if(errset(tfBuild() t) then exit(0) else exit(1))"]
    return "\n".join(lines) + "\n"


def build(identity, readback_id):
    from Layout.design import chip_routes
    rb = json.loads((WORK / readback_id / "ring_readback.json").read_bytes())
    content, labels, info = chip_routes.build(rb)
    il = build_il(content, labels)
    out = WORK / identity
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "content.json", dict(rects=content.rects, labels=labels, info=info))
    receipt, console = run_skill(identity, il, guarded=(RING, CORE, ("sar8_adc_core", "layout_route_full")))
    ok = "CHIP_BUILD_OK" in console and not any(l.startswith(("GUARDED_VIEW_CHANGED",)) for l in receipt["stdout"])
    summary = dict(ok=ok, rects=len(content.rects), labels=len(labels), readback=readback_id,
                   build=[l for l in console.splitlines() if l.startswith(("CHIP_BUILD_OK", "*Error*"))],
                   guarded=[l for l in receipt["stdout"] if l.startswith(("GUARDED", "EXIT"))])
    write_json(out / "build.json", summary)
    if not ok:
        raise RuntimeError("Chip build failed; see " + str(out / "oa.console"))
    return summary


PHYSICAL = ROOT / "Layout/tools/physical"


def physical(identity, view=CHIP[1], stages="drc,lvs", hcells=None, source=None, top=CHIP[0]):
    """Start Layout/tools/physical/chip_physical.py in a fresh evidence directory (status/fetch: toplevel_route)."""
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    files = {n: (PHYSICAL / n).read_bytes() for n in ("chip_physical.py", "run_physical.py", "workspace.py")}
    args = ["python", "-u", "chip_physical.py", identity, "--top", top, "--view", view,
            "--lock", cfg["legacy_root"] + "/layout.lock", "--stages", stages]
    if hcells:
        files["hcells.txt"] = ("\n".join(hcells) + "\n").encode("ascii")
        args += ["--hcells", "hcells.txt"]
    if source:
        files["source.cdl"] = (ROOT / source).read_bytes()
        args += ["--source", "source.cdl"]
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}", f"test ! -e {q(evidence)}",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script += [f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib"]
    for lib in (STANDARD_LIBRARY, IO_LIBRARY, PAD_LIBRARY, SEAL_LIBRARY):
        script.append(f"grep -q -E '^DEFINE[[:space:]]+{lib}[[:space:]]' cds.lib || "
                      f"grep -m1 -E '^DEFINE[[:space:]]+{lib}[[:space:]]' {SHARED_CDS} >> cds.lib")
    script += ["sha256sum " + " ".join(files) + " cds.lib",
               "nohup " + " ".join(q(a) for a in args) + " > driver.log 2>&1 < /dev/null &", "echo PID=$!"]
    run = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "bash -s"],
                         input="\n".join(script).encode("ascii"), capture_output=True, timeout=180)
    receipt = dict(identity=identity, arguments=args, returncode=run.returncode,
                   uploaded_sha256={n: hashlib.sha256(b).hexdigest() for n, b in files.items()},
                   stdout=run.stdout.decode("utf-8", "replace").splitlines())
    write_json(WORK / identity / "launch.json", receipt)
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("readback")
    a.add_argument("identity")
    a = sub.add_parser("build")
    a.add_argument("identity")
    a.add_argument("--readback", required=True)
    a = sub.add_parser("ring-cdl")
    a.add_argument("identity")
    a = sub.add_parser("physical")
    a.add_argument("identity")
    a.add_argument("--stages", default="drc,lvs")
    a.add_argument("--hcells-from", help="local stream whose block masters stay HCELLs (the core placement stream)")
    a.add_argument("--source", help="chip LVS source (CDL)")
    a.add_argument("--top", default=CHIP[0], help="cell to check (baselines: sar8_io_ring, sar8_adc_core)")
    a.add_argument("--view", default=CHIP[1])
    args = ap.parse_args()
    if args.action == "physical":
        from Layout.design.toplevel_route import block_masters
        hc = block_masters(args.hcells_from) if args.hcells_from else None
        print(json.dumps(physical(args.identity, view=args.view, stages=args.stages, hcells=hc, source=args.source,
                                  top=args.top), indent=1))
        return
    if args.action == "readback":
        print(json.dumps(readback(args.identity), indent=1))
    elif args.action == "ring-cdl":
        print(json.dumps(export_ring_cdl(args.identity), indent=1))
    else:
        print(json.dumps(build(args.identity, args.readback), indent=1))


if __name__ == "__main__":
    main()
