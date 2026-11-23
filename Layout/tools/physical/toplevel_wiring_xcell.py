"""Top-level wiring extraction of sar8_adc_core with the block masters kept as xcells (remote, Python 2).

Runs from its own new evidence directory, created by launch_toplevel_wiring.py, with the uploaded stream
candidate.gds and the xcell list xcells.txt. It builds the installed typical xRC deck with
run_physical.prepare_deck (the deck of the flat core extraction adc-core-full-p2h-xtr) and runs
  calibre -xrc -phdb -hcell hcells.txt   (block masters kept as hierarchy)
  calibre -xrc -pdb -rcc -xcell xcells.txt
  calibre -xrc -fmt -all
so the netlist holds the top-level nets as RC networks ending on the xcell instance pins, with their mutual
coupling. The xcell bodies are discarded by the Stage 6 deck, which binds the frozen block extractions instead.
No OA access; the layout lock is not taken.
Usage: python toplevel_wiring_xcell.py   (inside the evidence directory)
"""
from __future__ import print_function
import json, os, re, shutil, sys, time, traceback

HERE = os.path.dirname(os.path.realpath(__file__))
IDENT = os.path.basename(HERE)
RUNTIME = os.path.dirname(os.path.dirname(HERE)) + '/runtime'
# The top cell: the routed core, or the filled wrapper sar8_adc_core_filled (top.txt from the launcher).
TOP = open(HERE + '/top.txt').read().strip() if os.path.exists(HERE + '/top.txt') else 'sar8_adc_core'
# Optional foundry interconnect corner (corner.txt: cworst_T | cbest_T): only the xRC rules include changes
# (sar_rc_corner.select, as in bootstrap_rc_corner.py); absent means the installed typical rules.
CORNER = open(HERE + '/corner.txt').read().strip() if os.path.exists(HERE + '/corner.txt') else None
# Optional supply names the deck's PEX EXTRACT EXCLUDE leaves ideal and this run extracts as RC (supplies.txt, one per
# line; the chip periphery extraction, Layout/tools/analysis/chip_periphery.py); absent keeps the installed list.
SUPPLIES = tuple(s.strip() for s in open(HERE + '/supplies.txt').read().splitlines() if s.strip()) \
    if os.path.exists(HERE + '/supplies.txt') else ()


def main(report):
    sys.path.insert(0, RUNTIME)
    import run_physical as rp
    gds = HERE + '/fixture.gds'
    shutil.copyfile(HERE + '/candidate.gds', gds)
    identity = rp.gds_identity(gds)
    cells = [c.strip() for c in rp.read(HERE + '/xcells.txt').splitlines() if c.strip()]
    if not cells or not all(re.match(r'\A[A-Za-z0-9_]+\Z', c) for c in cells):
        raise ValueError('Invalid xcell list')
    if TOP not in identity['structural_sha256'] or not all(c in identity['structural_sha256'] for c in cells):
        raise ValueError('The stream lacks the top cell or an xcell master')
    report.update(gds=dict(sha256=identity['sha256'], top_structural_sha256=identity['structural_sha256'][TOP],
                           top_labels=sorted(identity['labels'].get(TOP, []))), xcells=cells)
    rp.put(HERE + '/reference.cdl', b'* extraction only\n')
    work = HERE + '/pex'
    os.mkdir(work)
    os.symlink('../fixture.gds', work + '/fixture.gds')
    if not all(re.match(r'\A[A-Za-z0-9_]+\Z', s) for s in SUPPLIES):
        raise ValueError('Invalid supply list')
    report['deck'] = rp.prepare_deck(work, 'pex', TOP, SUPPLIES)
    if CORNER:
        assert CORNER in ('cworst_T', 'cbest_T')
        sys.path.insert(0, HERE)
        from sar_rc_corner import select
        import workspace
        os.chdir(RUNTIME)                # workspace.paths() runs only from the owned runtime
        try:
            cfg = workspace.paths()
        finally:
            os.chdir(HERE)
        report['interconnect_rc'] = CORNER
        report['interconnect_rc_rules'] = select(work, cfg, rp.PDK, os.path.join(rp.RULES, 'rcx'), report['deck'], CORNER)
    pairs = ''.join('%s %s\n' % (c, c) for c in cells).encode('ascii')
    rp.put(work + '/hcells.txt', pairs)
    rp.put(work + '/xcells.txt', pairs)
    save(report)
    for phase, args, limit in [('phdb', ['calibre', '-xrc', '-phdb', '-hcell', 'hcells.txt', '-turbo', '8', '-nowait', 'pex.svrf'], 3600),
                               ('rcc', ['calibre', '-xrc', '-pdb', '-rcc', '-xcell', 'xcells.txt', '-turbo', '8', '-nowait', 'pex.svrf'], 3600),
                               ('format', ['calibre', '-xrc', '-fmt', '-all', '-nowait', 'pex.svrf'], 3600)]:
        report['phases'][phase] = dict(started=time.time(), args=args)
        save(report)
        rc = rp.tool(rp.CALIBRE, args, work, HERE + '/' + phase + '.console', limit)
        report['phases'][phase].update(returncode=rc, finished=time.time())
        save(report)
        if rc:
            raise RuntimeError(phase + ' failed: ' + str(rc))
    out = dict((n, rp.sha(rp.raw(work + '/' + n))) for n in sorted(os.listdir(work)) if n.startswith('extracted.scs'))
    if 'extracted.scs' not in out:
        raise RuntimeError('PEX did not write the Spectre netlist')
    report['checks'] = dict(pex=dict(sha256=out.pop('extracted.scs'), companion_sha256=out,
                                     bytes=os.path.getsize(work + '/extracted.scs')))


def save(report):
    with open(HERE + '/manifest.json.next', 'w') as f:
        json.dump(report, f, indent=2, sort_keys=True)
    os.rename(HERE + '/manifest.json.next', HERE + '/manifest.json')


if __name__ == '__main__':
    report = dict(identity=IDENT, top=TOP, case='toplevel-wiring-xcell', started=time.time(), phases={}, done=False,
                  interconnect_rc='typical', driver='toplevel_wiring_xcell.py')
    save(report)
    try:
        main(report)
        report['done'] = True
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['finished'] = time.time()
        save(report)
