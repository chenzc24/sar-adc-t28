"""Planned OD/PO fill of the Bootstrap core, in the core master's frame (Layout/specs/fill-policy.md).

The 200-unit boot capacitor covers 72 % of the outline, so the OD.DN.3/PO.DN.3 windows (20 um) and the
PO.DN.3.1 windows (10 um, MOMDMY excluded) close inside the array. In-cell utility OD/PO added 36-39 fF to
ground on each plate (fill session, adc-core-diag-noboot-chk against adc-core-fill3-chk), most of it from
dummy poly under the M1 fingers. This plan keeps the dummy poly out from under every finger:
- every gap between two units holds one 0.12 um dummy-poly stripe (DPO.W.1) in the 0.13 um space between the
  units' M1, through all rows where both units exist; this also fills the non-MOMDMY area for PO.DN.3.1;
- dummy OD cannot fit in a gap (DOD.W.1 0.25 um), so each gap carries 0.28 um dummy-OD segments centred under
  its poly stripe (DPO.EX.2 0.075 um), 2.2 um long per unit row: about 22 % OD in the array (OD.DN.3 20 %);
- the notch beside the switch bank continues the column pattern for three columns, clear of OD_18, the
  substrate ring and its PP (DOD.S.2/S.8/S.9);
- ODBLK, POBLK and DM1..DM9EXCL over the whole outline keep every fill utility out of the cell.
Each gap stripe sits under the right finger of one unit and the left finger of the next, so the two plates
see the same fill. The cell is placed with each core instance's transform (XBOOTP R0, XBOOTN MY).
  python -m Layout.design.bootstrap_fill assemble CORE.gds OUT.gds   (fill flattened into the core, for checks)
"""
import argparse
import hashlib
import json

CORE = 'sar_bootstrap_flat_8b_p_core'
FILL = 'sar_bootstrap_flat_8b_p_fill'
# Core geometry of Layout/design/bootstrap.il (bsArray, four-finger main switch).
UNIT_PITCH_X, ROW_PITCH, UNIT_H = .88, 3.14, 2.92
COLUMNS, ROWS = 28, 8
NOTCH = range(6, 18)            # columns absent from rows 0 and 1
GAP_CENTRE = .82                # unit M1 spans 0.005-0.755 um from the unit origin; the next starts at 0.885
OUTLINE = (-11.82, -.045, 12.70, 24.945)
DPO_W, DOD_W = .12, .28
DOD_Y = (.36, 2.56)             # dummy-OD segment within each unit row (centred on the 2.92 um unit)
NOTCH_COLUMNS = (5, 6, 7)       # virtual gaps carried into the notch, left of OD_18 at x -3.76
LAYERS = {('OD', 'dummy'): (6, 1), ('PO', 'dummy'): (17, 1), ('ODBLK', 'dummy'): (150, 20),
          ('POBLK', 'dummy'): (150, 21), **{('DMEXCL', 'dummy%d' % k): (150, k) for k in range(1, 10)}}


def origin(c):
    return (c - 13) * UNIT_PITCH_X - .38


def present(r, c):
    return 0 <= c < COLUMNS and not (r < 2 and c in NOTCH)


def fill_plan():
    """(layer, purpose, x0, y0, x1, y1) in the core master's frame."""
    shapes = []
    for c in range(COLUMNS - 1):
        x = origin(c) + GAP_CENTRE
        rows = [r for r in range(ROWS) if present(r, c) and present(r, c + 1)]
        notch = c in NOTCH_COLUMNS
        if notch:
            rows = sorted(set(rows) | {0, 1})
        if not rows:
            continue
        y0, y1 = min(rows) * ROW_PITCH, max(rows) * ROW_PITCH + UNIT_H
        shapes.append(('PO', 'dummy', x - DPO_W / 2, y0, x + DPO_W / 2, y1))
        for r in rows:
            shapes.append(('OD', 'dummy', x - DOD_W / 2, r * ROW_PITCH + DOD_Y[0], x + DOD_W / 2, r * ROW_PITCH + DOD_Y[1]))
    shapes += [(layer, purpose, *OUTLINE) for layer, purpose in
               [('ODBLK', 'dummy'), ('POBLK', 'dummy')] + [('DMEXCL', 'dummy%d' % k) for k in range(1, 10)]]
    return [(l, p, round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)) for l, p, x0, y0, x1, y1 in shapes]


def summary(shapes=None):
    shapes = shapes or fill_plan()
    area = lambda layer: sum((x1 - x0) * (y1 - y0) for l, p, x0, y0, x1, y1 in shapes if (l, p) == (layer, 'dummy'))  # noqa: E731
    array = (COLUMNS * UNIT_PITCH_X) * (ROWS * ROW_PITCH)
    return dict(dummy_od_um2=round(area('OD'), 3), dummy_po_um2=round(area('PO'), 3),
                array_window_od=round(DOD_W * (DOD_Y[1] - DOD_Y[0]) / (UNIT_PITCH_X * ROW_PITCH), 4),
                array_window_po=round(DPO_W / UNIT_PITCH_X, 4), outline_um2=round(array, 2),
                shapes=len(shapes), sha256=hashlib.sha256(json.dumps(shapes).encode()).hexdigest())


def assemble(core_gds, out_gds, flatten=True):
    """Core stream with the fill: flattened into the core top (extraction and checks keep the core's name,
    ports and probes), or as a FILL child placed R0 in the core (flatten=False)."""
    import gdstk
    lib = gdstk.read_gds(core_gds)
    top = next(c for c in lib.cells if c.name == CORE)
    rects = [gdstk.rectangle((x0, y0), (x1, y1), layer=LAYERS[(l, p)][0], datatype=LAYERS[(l, p)][1])
             for l, p, x0, y0, x1, y1 in fill_plan()]
    if flatten:
        top.add(*rects)
    else:
        fill = gdstk.Cell(FILL)
        fill.add(*rects)
        lib.add(fill)
        top.add(gdstk.Reference(fill))
    lib.write_gds(out_gds)
    digest = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()  # noqa: E731
    return dict(core_gds=core_gds, core_gds_sha256=digest(core_gds), out=out_gds, out_sha256=digest(out_gds),
                flattened=flatten, fill=summary())


WRAPPER = 'sar_bootstrap_flat_8b_p_filled'
OWNER = 'Layout/design/bootstrap_fill.py'
LIBRARY = 'SAR_ADC_T28_LAYOUT'
LIBRARY_PATH = '/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT'


def build_il(core_view, view):
    """SKILL that writes the fill cell FILL/view and the wrapper WRAPPER/view (XCORE + XFILL, the core's ports)."""
    plan = fill_plan()
    rects = '\n'.join('  bfRect(fill "%s" "%s" %.4f %.4f %.4f %.4f)' % s for s in plan)
    return '''; Generated by Layout/design/bootstrap_fill.py (fill plan %(sha)s).
procedure(bfRequire(ok message) unless(ok error("%%s\\n" message)))
procedure(bfRect(cv layer purpose x0 y0 x1 y1)
 bfRequire(dbCreateRect(cv list(layer purpose) list(x0:y0 x1:y1)) "Cannot create fill rectangle"))
procedure(bfOpen(cell)
 let((cv owner)
  cv=dbOpenCellViewByType("%(lib)s" cell "%(view)s" "maskLayout" "a")
  bfRequire(cv strcat("Cannot open " cell))
  owner=dbFindProp(cv "generatorOwner")
  bfRequire((!cv~>instances && !cv~>shapes && !cv~>nets) || (owner && owner~>value=="%(owner)s")
   strcat("Existing view has a different owner: " cell))
  foreach(obj cv~>instances dbDeleteObject(obj))
  foreach(obj cv~>shapes dbDeleteObject(obj))
  foreach(obj cv~>nets dbDeleteObject(obj))
  dbReplaceProp(cv "generatorOwner" "string" "%(owner)s")
  cv))
procedure(bfBuild()
 let((core fill cv inst net term shape)
  bfRequire(equal(ddGetObj("%(lib)s")~>readPath "%(path)s") "Wrong layout library")
  core=dbOpenCellViewByType("%(lib)s" "%(core)s" "%(core_view)s" "" "r")
  bfRequire(core && length(core~>terminals)==5 "Missing core view")
  fill=bfOpen("%(fill)s")
%(rects)s
  bfRequire(dbSave(fill) "Cannot save the fill cell")
  cv=bfOpen("%(wrapper)s")
  inst=dbCreateInst(cv core "XCORE" 0:0 "R0")
  foreach(ct core~>terminals
   net=dbCreateNet(cv ct~>name)
   term=dbCreateTerm(net ct~>name ct~>direction)
   dbCreateInstTerm(net inst ct)
   foreach(pin ct~>pins foreach(fig pin~>figs
    bfRequire(equal(fig~>objType "rect") "Expected a rectangular port")
    shape=dbCreateRect(cv fig~>lpp fig~>bBox)
    dbCreatePin(net shape ct~>name term)
    dbCreateLabel(cv list(fig~>layerName "pin")
     list((caar(fig~>bBox)+caadr(fig~>bBox))/2.0 (cadar(fig~>bBox)+cadadr(fig~>bBox))/2.0)
     ct~>name "centerCenter" "R0" "roman" 0.05))))
  bfRequire(dbCreateInst(cv fill "XFILL" 0:0 "R0") "Cannot place the fill")
  bfRequire(dbSave(cv) "Cannot save the wrapper")
  dbClose(cv) dbClose(fill) dbClose(core)
  fill=dbOpenCellViewByType("%(lib)s" "%(fill)s" "%(view)s" "" "r")
  cv=dbOpenCellViewByType("%(lib)s" "%(wrapper)s" "%(view)s" "" "r")
  bfRequire(length(fill~>shapes)==%(count)d "Fill readback differs")
  bfRequire(length(cv~>instances)==2 && length(cv~>terminals)==5 "Wrapper readback differs")
  printf("BOOTSTRAP_FILL_OK fill_shapes=%%d wrapper_instances=%%d ports=%%d bbox=%%L\\n" length(fill~>shapes)
   length(cv~>instances) length(cv~>terminals) cv~>bBox)
  dbClose(fill) dbClose(cv) t))
if(errset(bfBuild() t) then exit(0) else exit(1))
''' % dict(sha=summary(plan)['sha256'][:16], lib=LIBRARY, path=LIBRARY_PATH, view=view, owner=OWNER, core=CORE,
           core_view=core_view, fill=FILL, wrapper=WRAPPER, rects=rects, count=len(plan))


def _start(identity, driver, arguments, files):
    """Create evidence IDENTITY on the layout host, upload files and start driver once in the background."""
    import base64
    import subprocess
    import tempfile

    from Layout.project import config
    cfg = config()
    blobs = {n: base64.b64encode(b).decode() for n, b in files.items()}
    code = """import os,sys,subprocess,base64
os.chdir(RUNTIME);sys.path.insert(0,RUNTIME)
import workspace
out=workspace.evidence(IDENT,create=True)
for name,value in FILES.items():
    with os.fdopen(os.open(out+'/'+name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(base64.b64decode(value))
compile(open(out+'/'+DRIVER).read(),DRIVER,'exec')
log=os.fdopen(os.open(out+'/driver.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb')
print(subprocess.Popen(['python','-u',DRIVER]+ARGS,cwd=out,stdout=log,stderr=log,stdin=open(os.devnull),preexec_fn=os.setsid,close_fds=True).pid)
""".replace('RUNTIME', repr(cfg['remote_root'] + '/runtime')).replace('IDENT', repr(identity)).replace(
        'DRIVER', repr(driver)).replace('ARGS', repr(list(arguments))).replace('FILES', repr(blobs))
    with tempfile.TemporaryFile() as stream:
        stream.write(code.encode())
        stream.seek(0)
        p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', cfg['host'], 'python -'],
                           stdin=stream, capture_output=True, timeout=300)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-600:])
    return int(p.stdout.decode().strip())


def build(identity, core_view='layout_r2', view='layout_r2'):
    """Write FILL/view and WRAPPER/view in OA once (Layout/tools/physical/bootstrap_fill_build.py)."""
    import re

    from Layout.project import ROOT
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', identity) or not re.fullmatch(r'layout_r\d{1,2}', view):
        raise ValueError('Unsupported identity or view')
    script = build_il(core_view, view).encode('ascii')
    work = ROOT / 'work/layout/bootstrap-fill' / identity
    work.mkdir(parents=True, exist_ok=False)
    (work / 'build.il').write_bytes(script)
    driver = (ROOT / 'Layout/tools/physical/bootstrap_fill_build.py').read_bytes().replace(b'\r\n', b'\n')
    pid = _start(identity, 'bootstrap_fill_build.py', [core_view, FILL, WRAPPER, view],
                 {'bootstrap_fill_build.py': driver, 'build.il': script})
    return dict(identity=identity, pid=pid, fill_cell=FILL + '/' + view, wrapper=WRAPPER + '/' + view,
                core=CORE + '/' + core_view, build_il_sha256=hashlib.sha256(script).hexdigest(), plan=summary())


def launch(identity, source, corner):
    """Assemble the filled stream from SOURCE's verified core stream and start Layout/tools/physical/
    bootstrap_filled.py once in the new evidence directory IDENTITY on the layout host."""
    import re
    import subprocess

    from Layout.project import ROOT, config, evidence
    from Layout.tools.simulation.prepare_full_sim import pull, sha
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', identity) or corner not in ('typical', 'cworst_T', 'cbest_T'):
        raise ValueError('Unsupported identity or corner')
    remote = evidence(source)
    manifest = json.loads(pull(remote + '/manifest.json'))
    work = ROOT / 'work/layout/bootstrap-fill' / identity
    work.mkdir(parents=True, exist_ok=False)
    core = work / 'core.gds'
    out = subprocess.run(['ssh', '-o', 'BatchMode=yes', config()['host'], 'cat ' + remote + '/fixture.gds'],
                         capture_output=True, timeout=300, check=True).stdout
    if sha(out) != manifest['gds']['sha256']:
        raise ValueError('Fetched core stream differs from its manifest')
    core.write_bytes(out)
    plan = assemble(str(core), str(work / 'filled.gds'))
    plan.update(core_gds=source + '/fixture.gds', out=identity + '/filled.gds')
    (work / 'fill.json').write_text(json.dumps(plan, indent=1) + '\n')
    here = ROOT / 'Layout/tools/physical'
    files = {n: (here / n).read_bytes().replace(b'\r\n', b'\n') for n in ('bootstrap_filled.py', 'sar_rc_corner.py')}
    files.update({n: (work / n).read_bytes() for n in ('filled.gds', 'fill.json')})
    pid = _start(identity, 'bootstrap_filled.py', [source, corner], files)
    return dict(identity=identity, source=source, corner=corner, pid=pid,
                filled_sha256=plan['out_sha256'], fill_sha256=plan['fill']['sha256'], work=str(work.relative_to(ROOT)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    sub.add_parser('summary')
    a = sub.add_parser('assemble')
    a.add_argument('core_gds')
    a.add_argument('out_gds')
    s = sub.add_parser('launch', help='DRC, LVS and PEX of SOURCE with the planned fill, in evidence IDENTITY')
    s.add_argument('identity')
    s.add_argument('source')
    s.add_argument('corner', choices=('typical', 'cworst_T', 'cbest_T'))
    b = sub.add_parser('build', help='Write the fill cell and the filled wrapper in OA (evidence IDENTITY)')
    b.add_argument('identity')
    b.add_argument('--core-view', default='layout_r2')
    b.add_argument('--view', default='layout_r2')
    sub.add_parser('il', help='Print the SKILL build script')
    args = ap.parse_args()
    if args.action == 'summary':
        print(json.dumps(summary(), indent=1))
    elif args.action == 'assemble':
        print(json.dumps(assemble(args.core_gds, args.out_gds), indent=1))
    elif args.action == 'build':
        print(json.dumps(build(args.identity, args.core_view, args.view), indent=1))
    elif args.action == 'il':
        print(build_il('layout_r2', 'layout_r2'))
    else:
        print(json.dumps(launch(args.identity, args.source, args.corner), indent=1))
