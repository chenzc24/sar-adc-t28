"""Start one top-level wiring extraction (toplevel_wiring_xcell.py) under a new evidence identity, once.

The stream is a branch-labelled copy of a verified sar8_adc_core stream: its supply texts are renamed by
position to VDD_A/VSS_A (north, analog), VDD_P/VSS_P (south, pair) and VDD_D/VSS_D (east, SAR), as in the
copy the flat extraction adc-core-full-p2h-xtr used; every shape and reference is unchanged (checked).
workspace.evidence(create=True) refuses an existing identity, so a retried launch never runs twice.
Usage: python -m Layout.tools.physical.launch_toplevel_wiring IDENTITY SOURCE_EVIDENCE LOCAL_SOURCE_GDS
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

from Layout.design.toplevel_route import compare_streams
from Layout.project import ROOT, config

# The XREF/CDAC pair cell is one xcell: its gate trees, reference rails and ties belong to the frozen coupled
# extraction of sar8_cdac_with_xref, so none of them may reappear as top-level wiring.
XCELLS = ['sar8_se_core', 'sar8_cdac_with_xref', 'sar_bootstrap_flat_8b_p_core', 'sar_strongarm_t28_core']
# (text layer, x, y) of each supply text of sar8_adc_core and its branch name.
BRANCH_TEXTS = {(139, 44.115, 110.8): 'VDD_A', (139, 48.115, 110.8): 'VSS_A', (139, 44.0, 0.3): 'VDD_P',
                (138, 48.0, 0.3): 'VSS_P', (139, 121.7, 74.0): 'VDD_D', (138, 121.7, 71.0): 'VSS_D',
                (132, 121.8, 51.5): 'VSS_D'}


def branch_labelled(src, out, top_name='sar8_adc_core', drop=()):
    """Supply texts of top_name renamed by branch; references to the cells in drop removed from every cell."""
    import gdstk
    lib = gdstk.read_gds(str(src))
    top = next(c for c in lib.cells if c.name == top_name)
    dropped = []
    for cell in lib.cells:
        for ref in list(cell.references):
            if ref.cell.name in drop:
                cell.remove(ref)
                dropped.append(dict(parent=cell.name, cell=ref.cell.name))
    if sorted(d['cell'] for d in dropped) != sorted(drop):
        raise ValueError('Expected one reference of each dropped cell: %s' % dropped)
    renamed = []
    for t in top.labels:
        key = (t.layer, round(t.origin[0], 4), round(t.origin[1], 4))
        if key in BRANCH_TEXTS:
            if t.text not in ('VDD!', '0') or (t.text == 'VDD!') != BRANCH_TEXTS[key].startswith('VDD'):
                raise ValueError('Unexpected supply text at %s: %s' % (key, t.text))
            renamed.append(dict(at=key, old=t.text, new=BRANCH_TEXTS[key]))
            t.text = BRANCH_TEXTS[key]
    if any(t.text in ('VDD!', '0') for t in top.labels):
        raise ValueError('A supply text has no branch name')
    lib.write_gds(str(out))
    cmp = compare_streams(src, out)
    if not (cmp['shapes']['equal'] and cmp['references']['equal']):
        raise ValueError('Relabelling changed the core geometry')
    return dict(texts=renamed, dropped=dropped)


def launch(identity, source_evidence, source_gds, top='sar8_adc_core', drop=(), corner=None, bootstrap=None):
    """bootstrap: the Bootstrap master placed in the stream when it is not the bare core, e.g. the filled
    sar_bootstrap_flat_8b_p_filled whose own fill belongs to its block extraction, not to the top-level wiring."""
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', identity):
        raise ValueError('Invalid identity')
    xcells = [bootstrap if bootstrap and c == 'sar_bootstrap_flat_8b_p_core' else c for c in XCELLS]
    dest = ROOT / 'work/layout/toplevel-wiring' / identity
    dest.mkdir(parents=True, exist_ok=False)
    gds = dest / 'candidate.gds'
    renamed = branch_labelled(source_gds, gds, top, drop)
    here = Path(__file__).resolve().parent
    files = {'toplevel_wiring_xcell.py': (here / 'toplevel_wiring_xcell.py').read_bytes(), 'candidate.gds': gds.read_bytes(),
             'xcells.txt': ('\n'.join(xcells) + '\n').encode(), 'top.txt': (top + '\n').encode(),
             'source.json': (json.dumps(dict(source_evidence=source_evidence,
                                             source_gds_sha256=hashlib.sha256(Path(source_gds).read_bytes()).hexdigest(),
                                             branch_texts=renamed), indent=2) + '\n').encode()}
    if corner:
        if corner not in ('cworst_T', 'cbest_T'):
            raise ValueError('Corner must be cworst_T or cbest_T')
        files['corner.txt'] = (corner + '\n').encode()
        files['sar_rc_corner.py'] = (ROOT / 'Layout/tools/simulation/comparator_checks/sar_rc_corner.py').read_bytes()
    cfg = config()
    blobs = {n: base64.b64encode(b).decode() for n, b in files.items()}
    code = """import os,sys,subprocess,base64
runtime=RUNTIME
os.chdir(runtime);sys.path.insert(0,runtime)
import workspace
out=workspace.evidence(IDENT,create=True)
for name,value in FILES.items():
    with os.fdopen(os.open(out+'/'+name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(base64.b64decode(value))
compile(open(out+'/toplevel_wiring_xcell.py').read(),'toplevel_wiring_xcell.py','exec')
log=os.fdopen(os.open(out+'/driver.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb')
print(subprocess.Popen(['python','-u','toplevel_wiring_xcell.py'],cwd=out,stdout=log,stderr=log,stdin=open(os.devnull),preexec_fn=os.setsid,close_fds=True).pid)
""".replace('RUNTIME', repr(cfg['remote_root'] + '/runtime')).replace('IDENT', repr(identity)).replace('FILES', repr(blobs))
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', cfg['host'], 'python -'],
                       input=code.encode(), capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-800:])
    receipt = dict(identity=identity, host=cfg['host'], pid=int(p.stdout.decode().strip()), source_evidence=source_evidence,
                   uploaded_sha256={n: hashlib.sha256(b).hexdigest() for n, b in files.items()}, branch_texts=renamed)
    (dest / 'launch.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('identity')
    ap.add_argument('source_evidence')
    ap.add_argument('source_gds')
    ap.add_argument('--top', default='sar8_adc_core', help='Top cell, e.g. the filled wrapper sar8_adc_core_filled')
    ap.add_argument('--drop', nargs='*', default=[], help='Cells whose references are removed (fill a block extraction carries)')
    ap.add_argument('--corner', choices=['cworst_T', 'cbest_T'], help='Foundry interconnect corner (default typical)')
    ap.add_argument('--bootstrap', help='Bootstrap master in the stream, e.g. sar_bootstrap_flat_8b_p_filled')
    a = ap.parse_args()
    print(json.dumps(launch(a.identity, a.source_evidence, a.source_gds, a.top, tuple(a.drop), a.corner, a.bootstrap),
                     indent=2))
