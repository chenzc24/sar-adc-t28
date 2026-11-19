"""Prepare one physical single-edge front end for the five project corners and local MC."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from . import reference_short as short

ROOT = short.ROOT
CORNERS = ('tt', 'ssc', 'ssh', 'ffc', 'ffh')
CODES = short.CODES + [0x55, 0xAA, 127, 128]
MC_CODES = [255, 0, 128, 127, 85, 170]
# DFCNQD1BWP12T30P140 databook CP minimum high, scalar reference in ps.
CP_HIGH_PS = dict(tt=19.3214, ssc=30.0598, ssh=26.2451, ffc=15.7166, ffh=15.9454)


def prepare(corner, revision, seed=None, liberty_tables=None, restart=False, cell_lpe=False):
    if corner not in CORNERS or (seed is not None and corner not in ('ssc', 'ffc')):
        raise ValueError('Use a project PVT point or a cold local MC point')
    if restart and (seed is not None or corner != 'tt'):
        raise ValueError('The directed restart case uses nominal TT')
    dut = (ROOT/'design/dut_single_edge.scs').read_bytes()
    sources = {'dut.scs': dut}
    for name in re.findall(r'^include "([^"]+)"', dut.decode(), re.M):
        sources[name] = (ROOT/'design'/name).read_bytes()
    codes = MC_CODES if seed is not None else CODES
    library_corner = {'tt':'typical','ssc':'cworst_t','ssh':'cworst_t','ffc':'cbest_t','ffh':'cbest_t'}[corner]
    library = (ROOT/('tb/common/platform/library_lpe_%s.scs' % library_corner)).read_bytes() if cell_lpe else None
    if cell_lpe:
        revision += '-lpe'
    template = ROOT/short.prepare('single_edge', corner, revision+('-mc-input' if seed is not None else '-input'),
        codes=codes, source_blobs=sources, cell_library=library)
    recipe = json.loads(template.read_text())
    blobs = {row['name']: (ROOT/row['source']).read_bytes() for row in recipe['inputs']}
    rid = 'sar8-single-edge-%s-%s%s' % (corner, revision, '-s%d' % seed if seed is not None else '')
    if restart:
        rid += '-restart'
    folder = ROOT/'work/decks'/rid
    ctx = json.loads(blobs['context.json'])
    ctx.update(run_id=rid, design_id='sar8_single_edge', mismatch=seed is not None,
               min_cp_high_ps=CP_HIGH_PS[corner])
    if cell_lpe:
        ctx.update(cell_lpe=library_corner, pex_modules=[], cdac_model='schematic')
    if seed is None:
        # The first 18 histories match the archived five-point reference.
        points = codes[:-2] + [127.49, 127.51]
        tb = blobs['tb.scs'].decode()
        for source, node, sign in [('VVINP','VINP_SRC',1), ('VVINN','VINN_SRC',-1)]:
            tb, n = re.subn(r'(?m)^'+source+r' .*$', source+' ('+node+' 0) vsource type=pwl wave=['
                            +short.stimulus(points,sign)+']', tb)
            if n != 1:
                raise ValueError('Missing differential input source '+source)
        blobs['tb.scs'] = tb.encode()
        ctx.update(input_code_coordinates=points,
                   accepted_codes={str(i):[127,128] for i in range(len(codes)-2,len(codes))})
    deck = blobs['test.scs'].decode()
    deck, count = re.subn(r'(?m)^(tran_short tran .*)$', r'\1 strobeperiod=5p strobeoutput=strobeonly', deck)
    if count != 1:
        raise ValueError('Missing unique transient')
    if seed is not None:
        mos = ctx['mos']
        deck = deck.replace('section='+mos.lower()+'macro_mos_moscap',
                            'section='+mos+'GlobalCorner_LocalMC_MOS_MOSCAP')
        deck = deck.replace('section=tt_mom', 'section=TTGlobalCorner_LocalMC_MOM')
        mc = ('mc montecarlo numruns=1 seed=%d variations=mismatch dut=[XDUT] sampling=standard '
              'donominal=no savemismatchparams=yes mismatchparamfile="mismatch.params" '
              'mismatchscalarfile="mismatch.values" savefamilyplots=yes savedatainseparatedir=yes {\n')
        deck = re.sub(r'(?m)^(tran_short tran .*)$', lambda m: mc % seed + m[1] + '\n}', deck)
        ctx.update(seed=seed, statistical_mode='fixed process, whole-DUT local mismatch',
                   mos_section=mos+'GlobalCorner_LocalMC_MOS_MOSCAP',
                   passive_sections=['TTGlobalCorner_LocalMC_MOM' if section=='tt_mom' else section
                                     for section in ctx['passive_sections']])
    blobs['test.scs'] = deck.encode()
    for filename in ('mc_short_reduce.py', 'single_edge.py', 'single_edge_audit.py'):
        blobs[filename] = (ROOT/'tools/saradc/measure'/filename).read_bytes()
    blobs['register_constraints.py'] = (ROOT/'Layout/tools/analysis/register_constraints.py').read_bytes()
    tables = Path(liberty_tables) if liberty_tables else (
        ROOT/'work/output/managed_execution/runs/sar-qlpe-dff-ccs-five-20261119a/collected/derived/result.json')
    blobs['dff.json'] = tables.read_bytes()
    if restart:
        tb = blobs['tb.scs'].decode()
        pulse = '0 0 60n 0 60.1n SUP 100n SUP 100.1n 0 105n 0 105.1n SUP 145n SUP 145.1n 0 205n 0 205.1n SUP 245n SUP 245.1n 0'
        tb = re.sub(r'(?m)^VSAMPLE .*$', 'VSAMPLE (SAMPLE 0) vsource type=pwl wave=['+pulse+']', tb)
        for src,node,sign in [('VVINP','VINP_SRC',1),('VVINN','VINN_SRC',-1)]:
            vals = [.45+sign*(-.9+(c+.5)*1.8/256)/2 for c in (255,85,170)]
            wave = '0 %.17g 104.8n %.17g 104.9n %.17g 204.8n %.17g 204.9n %.17g' % (
                vals[0],vals[0],vals[1],vals[1],vals[2])
            tb = re.sub(r'(?m)^'+src+r' .*$', src+' ('+node+' 0) vsource type=pwl wave=['+wave+']', tb)
        blobs['tb.scs'] = tb.encode()
        deck = re.sub(r'(?m)^(?:XPROBE |ahdl_include "observer.va").*\n', '', deck)
        blobs['test.scs'] = re.sub(r'(tran_short tran stop=)\S+', r'\g<1>304n', deck).encode()
        ctx.update(expected_codes=[255,85,170], frames=3, expected_stop_s=304e-9,
                   input_code_coordinates=[255,85,170], accepted_codes={}, aborted_frame=0)
        recipe['expected_stop_s'] = ctx['expected_stop_s']
        blobs['single_edge_restart.py'] = (ROOT/'tools/saradc/measure/single_edge_restart.py').read_bytes()
    ctx['source_hashes'] = {k: hashlib.sha256(v).hexdigest() for k, v in blobs.items() if k != 'context.json'}
    blobs['context.json'] = (json.dumps(ctx, indent=2)+'\n').encode()
    recipe['spectre_args'][recipe['spectre_args'].index('+lqtimeout')+1] = '900'
    recipe.update(run_id=rid, design_id=ctx['design_id'], analyzer='single_edge_restart.py' if restart else 'single_edge.py',
                  qualification_scope='Accepted sample during conversion and restart' if restart else
                  '%d-frame front-end closed-loop transient' % len(codes), test_conditions=ctx,
                  inputs=[dict(name=k, source=(folder/k).relative_to(ROOT).as_posix(),
                               sha256=hashlib.sha256(v).hexdigest()) for k,v in blobs.items()])
    blobs['recipe.yaml'] = (json.dumps(recipe, indent=2)+'\n').encode()
    for name, data in blobs.items():
        path = folder/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Frozen input differs: '+str(path))
    for name, data in blobs.items():
        path = folder/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return (folder/'recipe.yaml').relative_to(ROOT).as_posix()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corner', choices=CORNERS)
    parser.add_argument('revision')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--liberty-tables', type=Path)
    parser.add_argument('--restart', action='store_true')
    parser.add_argument('--cell-lpe',action='store_true',help='Use foundry intra-cell extraction at the project PVT point')
    args = parser.parse_args()
    print(prepare(args.corner, args.revision, args.seed, args.liberty_tables, args.restart, args.cell_lpe))
