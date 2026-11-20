"""Prepare a dual-tap SAR with foundry cell LPE and the archived 510-terminal CDAC."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from . import reference_short as short
from .single_edge import CP_HIGH_PS

ROOT = short.ROOT
SOURCE = 'sar-acq-q6-xrc-s10-ssc-20261119c'
COLD = {'ffc': 'cbest_t', 'ssc': 'cworst_t'}
CODES = {'scan': [255, 0, 85, 170], 'verify': [255, 255, 0, 128, 85, 170, 127, 1],
         'boundary':[63,64,63,64], 'reversal': [255, 255, 0, 128]}
CTRL = 'xtor/sar/single_edge.scs'
PHASE = ['XDUT.XCTRL.XTIM.' + s for s in ('PHASE_REQUEST', 'DELIVERED')]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def set_taps(source, high, low):
    if min(high, low) < 1 or max(high, low) > 32:
        raise ValueError('Expected taps between 1 and 32')
    lines = []
    previous = 'PHASE_REQUEST'
    for i in range(1, max(high, low) + 1):
        lines.append('XDEL%d (%s T%d VDD VSS) DEL250D1BWP12T30P140' % (i, previous, i))
        previous = 'T%d' % i
    lines.append('XTAP (T%d T%d' % (high, low))
    source, count = re.subn(rb'(?m)^XDEL1 \(PHASE_REQUEST[^\r\n]*(?:\r?\nXDEL\d+ [^\r\n]*)*\r?\nXTAP \(T\d+ T\d+(?= )',
                            '\n'.join(lines).encode(), source)
    if count != 1:
        raise ValueError('Expected one physical delay chain and one mux')
    return source


def retained_inputs(folder, names):
    files = {f['name']: f['sha256'] for f in json.loads((folder / 'recipe.json').read_bytes())['files']}
    out = {}
    for n in names:
        out[n] = (folder / 'inputs' / n).read_bytes()
        if digest(out[n]) != files[n]:
            raise ValueError('Archived input digest differs for ' + n)
    return out


def prepare(corner, high, low, kind, revision):
    rc = COLD[corner]
    rid = 'sar8-setap-%s-h%dl%d-%s-%s' % (corner, high, low, kind, revision)
    dest = ROOT / 'work/decks' / rid
    runs = ROOT / 'work/output/managed_execution/runs'
    extracted = ['cdac_pex_wrapper.scs', 'cdac_xrc.scs', 'cdac_xrc.scs.pex', 'cdac_xrc.scs.sar8j_r1_cdac.pxi']
    archive = retained_inputs(runs / SOURCE, extracted + ['context.json', 'test.scs', 'xtor/cdac/cdac.scs'])
    control = json.loads(archive['context.json'])
    dut = (ROOT/'design/dut_single_edge.scs').read_bytes()
    sources = {name: (ROOT / 'design' / name).read_bytes()
               for name in re.findall(r'^include "([^"]+)"', dut.decode(), re.M)}
    if sources['xtor/cdac/cdac.scs'] != archive['xtor/cdac/cdac.scs']:
        raise ValueError('Schematic CDAC identity differs from extraction control')
    sources[CTRL] = set_taps(sources[CTRL], high, low)
    sources['dut.scs'] = dut.replace(b'"xtor/cdac/cdac.scs"', b'"cdac_pex_wrapper.scs"')
    sources.update({n: archive[n] for n in extracted})
    library = 'tb/common/platform/library_lpe_%s.scs' % rc
    template_id='tap-h%dl%d-%s-%s' % (high,low,kind,revision)
    template = ROOT / short.prepare('single_edge', corner, template_id, codes=CODES[kind], source_blobs=sources,
                                    cell_library=(ROOT/library).read_bytes())
    recipe = json.loads(template.read_bytes())
    blobs = {f['name']: (ROOT/f['source']).read_bytes() for f in recipe['inputs']}
    ctx = json.loads(blobs['context.json'])
    # Native PSF trace names omit the escape on slash-delimited pin names.
    groups = control['cdac_plate_nodes']
    group_names = [s for side in ('n','p') for group in groups[side] for s in group]
    plate_saves = [line for line in archive['test.scs'].splitlines() if line.startswith(b'save XDUT.XCDAC.XPEX.')]
    actual = [s.decode().replace('\\','').lower() for line in plate_saves for s in line.split()[1:]]
    if sorted(actual) != sorted(group_names) or len(set(actual)) != 510:
        raise ValueError('Expected all 510 physical capacitor terminals')
    weights_id = 'cdac-stacked-mx-%s-20261118' % corner
    weights_root = runs / weights_id
    physical = json.loads(retained_inputs(weights_root, ['physical.json'])['physical.json'])
    if physical['gds']['sha256'] != control['cdac_physical_gds_sha256']:
        raise ValueError('Independent CDAC weights use a different layout')
    wdata = (weights_root/'collected/derived/result.json').read_bytes()
    receipt = json.loads((weights_root/'collected/collection_receipt.json').read_bytes())
    if not any(f['name']=='derived/result.json' and f['sha256']==digest(wdata) for f in receipt['files']):
        raise ValueError('Independent CDAC weights do not match their receipt')
    weights = json.loads(wdata)['post']['metrics']['effective_weights_v']
    ctx.update(run_id=rid, kind=kind, tap_high=high, tap_low=low, pex=True, pex_modules=['cdac'], cell_lpe=rc,
               cdac_source=SOURCE, cdac_physical_gds_sha256=physical['gds']['sha256'], cdac_plate_nodes=groups,
               independent_cdac_gain=sum(weights)/(ctx['lsb_v']*255), weights_source=weights_id,
               weights_result_sha256=digest(wdata), current_signals=[])
    if kind=='boundary':
        gain=ctx['independent_cdac_gain']
        points=[63,64]+[127.5+gain*(x-127.5) for x in (63,64)]
        ctx['input_code_coordinates']=points
        tb=blobs['tb.scs'].decode()
        for node,sign in [('P',1),('N',-1)]:
            line='VVIN'+node+' (VIN'+node+'_SRC 0) vsource type=pwl wave=['+short.stimulus(points,sign)+']'
            tb,count=re.subn(r'(?m)^VVIN'+node+r' .*$',line,tb)
            if count!=1:raise ValueError('Missing differential input')
        blobs['tb.scs']=tb.encode()
    signals = [s for s in ctx['required_signals'] if not s.startswith('xdut.xcdac.')]
    ctrl = 'xdut.xctrl.'
    window = ctrl + 'xtim.xwindow.'
    ctx['selector_probes'] = dict(q=ctrl+'low_q', high=window+'t%d'%high, low=window+'t%d'%low)
    signals += [ctrl+'trial5', ctrl+'xword.low_bits']
    signals += sorted(set(ctx['selector_probes'].values()))
    ctx['required_signals'] = signals + [s.lower() for s in PHASE] + group_names
    deck = re.sub(rb'(?m)^save [^\r\n]+', b'save '+(' '.join([s.upper() for s in signals] + PHASE)).encode(), blobs['test.scs'])
    strobe = 'strobeperiod=5p strobeoutput=strobeonly'
    if kind in ('boundary', 'reversal') and corner == 'ffc':
        # The previous double crossing was shorter than the 5 ps output grid.
        # Keep periodic samples elsewhere, with 0.5 ps samples across the handoff
        # and bit 3 in the last (directed) frame.
        stop_ps = round(ctx['expected_stop_s'] * 1e12)
        last_ps = round((ctx['frame_origin_s'] + (ctx['frames']-1)*ctx['period_s']) * 1e12)
        start, end = last_ps + 45500, last_ps + 52000
        ctx['fine_window_frame_ns'] = [45.5, 52.0]
        ticks = sorted(set(range(10, 2*stop_ps+1, 10)).union(range(2*start, 2*end+1)))
        times = ['%.1fp' % (tick / 2) for tick in ticks]
        rows = [' '.join(times[i:i+32]) for i in range(0,len(times),32)]
        strobe = 'strobetimes=['+' \\\n'.join(rows)+'] strobeoutput=strobeonly'
    deck = re.sub(rb'(?m)^(tran_short tran [^\r\n]+)', lambda m: m[1]+b' '+strobe.encode(), deck)
    blobs['test.scs'] = deck+b'\n'+b'\n'.join(plate_saves)+b'\n'
    blobs['single_edge_lpe.py'] = (ROOT/'tools/saradc/measure/single_edge_lpe.py').read_bytes()
    if kind in ('verify','boundary','reversal'):
        ctx['min_cp_high_ps']=CP_HIGH_PS[corner]
        blobs['single_edge_audit.py']=(ROOT/'tools/saradc/measure/single_edge_audit.py').read_bytes()
        blobs['register_constraints.py']=(ROOT/'Layout/tools/analysis/register_constraints.py').read_bytes()
        dff_tables=runs/'sar-qlpe-dff-ccs-five-20261119a/collected/derived/result.json'
        blobs['dff.json']=dff_tables.read_bytes()
    ctx['source_hashes'] = {k:digest(v) for k,v in blobs.items() if k!='context.json'}
    blobs['context.json'] = (json.dumps(ctx,indent=2)+'\n').encode()
    recipe['resources'].update(simulation_rss_mib=3584,simulation_virtual_mib=16384,analysis_rss_mib=768,
        analysis_wall_seconds=10800,max_output_mib=2048+1200*len(CODES[kind]))
    recipe['spectre_args'][recipe['spectre_args'].index('+lqtimeout')+1] = '900'
    recipe.update(run_id=rid, design_id='sar8_single_edge_cell_lpe_cdac_xrc',analyzer='single_edge_lpe.py',
                  qualification_scope='Cold-cell LPE, extracted nominal-RC CDAC, ideal SAR inter-cell wiring',
                  test_conditions=ctx, inputs=[dict(name=n,source=(dest/n).relative_to(ROOT).as_posix(),
                                                    sha256=digest(b)) for n,b in blobs.items()])
    blobs['recipe.yaml'] = (json.dumps(recipe,indent=2)+'\n').encode()
    for n,b in blobs.items():
        path=dest/n
        if path.exists() and path.read_bytes()!=b:
            raise ValueError('Frozen path differs: '+str(path))
    for n,b in blobs.items():
        path=dest/n
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b)
    return dest/'recipe.yaml'


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('corner',choices=COLD)
    p.add_argument('high',type=int)
    p.add_argument('low',type=int)
    p.add_argument('kind',choices=CODES)
    p.add_argument('revision')
    a=p.parse_args()
    print(prepare(a.corner,a.high,a.low,a.kind,a.revision))
