"""Issue #2: paired native short runs for minimal reference switching."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from . import candidates, views
from .__main__ import engine

ROOT = Path(__file__).resolve().parents[2]
CODES = [0, 0, 1, 2, 3, 12, 63, 64, 127, 128, 191, 243, 255, 255, 0, 255, 128, 127]
PREFIX = 'sar8-minref'


def text(path):
    return (ROOT / path).read_text(encoding='utf-8')


def read(path):
    return json.loads(text(path))


def candidate_source():
    baseline = candidates.definitions(text('design/xtor/reference/reference.scs'))
    header = baseline['sar8i_refword'].splitlines()[0]
    lines = ['// Minimal reference candidate, Issue #2. No extra state or dead-time.',
             '// D/PHI_U/SAMPLE ports are retained only for interface compatibility.',
             '// iprobe joins are ideal wires between the existing separate gate pins.',
             header, 'XPRESET_N (PRESET VDD VSS RUN) sar8p_inv']
    for bit in range(8):
        # QN is the desired N-side common gate value; PMOS and NMOS share it.
        if bit == 7:
            lines += ['XINITIAL7 (CODE7 PRESET VDD VSS Q7) sar8p_or2',
                      'XINV7 (Q7 VDD VSS QN7) sar8p_inv']
        else:
            lines += ['XINITIAL%d (CODE%d RUN VDD VSS QN%d) sar8p_nand2' % (bit, bit, bit)]
        # Initial polarity logic is lightly loaded; final INV/BUF drives both gates.
        lines += ['XPN%d (QN%d VDD VSS GPN%d) sar8p_inv' % (bit, bit, bit),
                  'XNN%d (QN%d VDD VSS GNN%d) sar8p_buf' % (bit, bit, bit),
                  'WNP%d (GNN%d GNP%d) iprobe' % (bit, bit, bit),
                  'WPP%d (GPN%d GPP%d) iprobe' % (bit, bit, bit)]
    # This output has no consumer in the physical top. No fake completion event.
    lines += ['WUNUSED (RST_DONE VSS) iprobe', 'ends sar8i_refword', '', baseline['sar8i_idle'], '']
    lines = [line for line in '\n'.join(lines).splitlines() if not line.lstrip().startswith('// #')]
    # All drawing annotations are stale after a topology change; retain only electrical idle body.
    from .rnl import strip
    return strip('\n'.join(lines)) + '\n'


def ensure_candidate():
    filename = 'design/xtor/reference/minimal_direct.scs'
    path = ROOT / filename
    source = candidate_source()
    if path.exists() and path.read_text(encoding='utf-8') != source:
        raise ValueError('Candidate source changed; inspect rather than overwrite')
    if not path.exists():
        path.write_text(source, encoding='utf-8', newline='\n')
    row = candidates.read()['modules']['reference']
    if 'minimal_direct' not in row['candidates']:
        candidates.add('reference', 'minimal_direct', filename)
    return filename


def stimulus(codes, sign):
    values = [.45 + sign * (-.9 + (k + .5) * 1.8 / 256) / 2 for k in codes]
    points = ['0 %.17g' % values[0]]
    for i in range(1, len(codes)):
        points += ['%.17g %.17g' % ((59.8 + 100*i)*1e-9, values[i-1]),
                   '%.17g %.17g' % ((59.9 + 100*i)*1e-9, values[i])]
    points += ['%.17g %.17g' % ((59+100*len(codes))*1e-9, values[-1])]
    return ' '.join(points)


def prepare(version, corner, revision='v1', *, condition=None, codes=None, max_output_mib=None):
    if version not in ('b', 'minimal', 'current'):
        raise ValueError('Unknown reference short version')
    ensure_candidate()
    run_id = '%s-%s-%s-%s' % (PREFIX, version, corner, revision)
    engine().valid_id(run_id)
    condition = read('specs/corners.json')[corner] if condition is None else dict(condition)
    codes = list(CODES if codes is None else codes)
    if not codes or any(type(k) is not int or not 0 <= k <= 255 for k in codes):
        raise ValueError('Expected nonempty 8-bit code centers')
    if (set(condition) != {'mos','temperature_c','vdd_v'} or
            condition['mos'] not in ('TT','SS','FF','FS','SF') or
            condition['temperature_c'] not in (-40,27,125) or condition['vdd_v'] not in (.81,.9,.99)):
        raise ValueError('Unsupported PVT condition')
    blobs = views.build('frozen-b' if version == 'b' else 'current', ROOT,
                        {'reference':'minimal_direct'} if version == 'minimal' else None)
    tb = text('tb/top/short/tb.scs')
    for source, node, sign in [('VVINP', 'VINP_SRC', 1), ('VVINN', 'VINN_SRC', -1)]:
        tb = re.sub(r'(?m)^'+source+r' .*$', source+' ('+node+' 0) vsource type=pwl wave=['+stimulus(codes, sign)+']', tb)
    blobs['tb.scs'] = tb.encode()
    deck = text('tb/top/short/test.scs').splitlines()
    deck = [line for line in deck if not line.startswith(('XMEASURE ', 'ahdl_include ', 'tran_ab ', 'save '))]
    section = condition['mos'].lower() + 'macro_mos_moscap'
    deck = '\n'.join(deck).replace('SUP=0.9', 'SUP='+str(condition['vdd_v']))
    deck = deck.replace('section=ttmacro_mos_moscap', 'section='+section)
    deck = deck.replace('temp=27 ', 'temp='+str(condition['temperature_c'])+' ')
    # Keep passive sections identical and explicit, rather than guessing slow/fast MOM.
    signal_names = ['D%d'%i for i in range(8)] + ['SAMPLE','VDD!','VINP_SRC','VINN_SRC','VINP','VINN','VREFP','VREFN']
    signal_names += ['XDUT.'+s for s in ['SAMPLE_INT','SEQ_SAMPLE','CMP_CLK','PHI_U','ACTIVE','PRESET','TOPP','TOPN','COMP_P','COMP_N','XCTRL.PHI_W','XCTRL.XTIM.PR','XCTRL.XTIM.NR','XBOOTP.G','XBOOTN.G','XBOOTP.BTOP','XBOOTP.BBOT','XBOOTN.BTOP','XBOOTN.BBOT']]
    for bit in range(8):
        signal_names += ['XDUT.'+s+str(bit) for s in ['GNN','GNP','GPN','GPP','CODE']]
        signal_names += ['XDUT.XCDAC.B'+side+str(bit) for side in ['N','P']]
    currents = ['XDUT.XCDAC.XS%s%d.%s:1'%(side,bit,mos)
                for side in ['N','P'] for bit in range(8) for mos in ['MN_LOW','MP_HIGH']]
    stop = (59+100*len(codes))*1e-9
    deck += '\nahdl_include "observer.va"\nXPROBE ('+' '.join('D%d'%i for i in range(8))+' SAMPLE VDD! 0) b_behavior_observer\n'
    deck += 'tran_short tran stop=%.17g maxstep=10p errpreset=moderate lteratio=10\n'%stop
    deck += 'save '+' '.join(signal_names+currents)+'\n'
    blobs['test.scs'] = deck.encode()
    blobs['observer.va'] = (ROOT/'tb/behav/observer.va').read_bytes()
    blobs['library_include.scs'] = (ROOT/'tb/common/platform/library_include.scs').read_bytes()
    for filename in ['reference_short.py', 'native_stream.py']:
        blobs[filename] = (ROOT/'tools/saradc/measure'/filename).read_bytes()
    ctx = dict(run_id=run_id, issue=2, version=version, corner=corner, **condition,
               expected_codes=codes, frames=len(codes), period_s=100e-9, frame_origin_s=59e-9,
               expected_stop_s=stop, lsb_v=1.8/256, settling_band_lsb=.25,
               required_signals=[s.lower() for s in signal_names], current_signals=[s.lower() for s in currents],
               noise=False, mismatch=False, pex=False, baseline_frozen_b_sha256=read('specs/arch.json')['frozen_b_sha256'],
               passive_sections=['tt_res_bip_dio_disres','tt_mom','tt_ind_jvar','tt_r_metal'],
               reference_v=[0,.9], first_frame_scored=True, cap_events_required=False,
               source_hashes={n:hashlib.sha256(b).hexdigest() for n,b in blobs.items()})
    blobs['context.json'] = (json.dumps(ctx, indent=2)+'\n').encode()
    dest = ROOT/'work/decks'/run_id
    for name, data in blobs.items():
        p=dest/name
        if p.exists() and p.read_bytes()!=data:
            raise ValueError('Prepared identity differs: '+str(p))
    for name, data in blobs.items():
        p=dest/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
    original=read('specs/tests.json')['tt_short']
    resources=dict(original['resources'])
    # v1 measured 2 GiB by 0.921 us (B) / 1.410 us (minimal).
    # Retain full native precision and currents for the 1.859 us experiment.
    # The managed disk admission and runtime limits enforce this declared budget.
    if max_output_mib is not None and (type(max_output_mib) is not int or max_output_mib<=0):
        raise ValueError('Positive output budget required')
    resources['max_output_mib']=8192 if max_output_mib is None else max_output_mib
    recipe = dict(schema_version=1,run_id=run_id,design_id='sar8_reference_direct_issue2',entry='test.scs',
                  analyzer='reference_short.py', inputs=[dict(name=n,source=(dest/n).relative_to(ROOT).as_posix(),sha256=hashlib.sha256(b).hexdigest()) for n,b in blobs.items()],
                  resources=resources,spectre_args=original['spectre_args'],summary_signals=['sample'],
                  expected_stop_s=stop,qualification_scope='%d-frame native functional/timing comparison; terminal qualification deferred'%len(codes),test_conditions=ctx)
    p=dest/'recipe.yaml'; content=json.dumps(recipe,indent=2)+'\n'
    if p.exists() and p.read_text(encoding='utf-8')!=content:raise ValueError('Recipe identity differs')
    p.write_text(content,encoding='utf-8',newline='\n')
    return p.relative_to(ROOT).as_posix()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','submit','status','analyze','collect'])
    p.add_argument('--version',choices=['b','minimal','current'],required=True)
    p.add_argument('--corner',choices=['tt','ssc','ssh','ffc','ffh'],required=True)
    p.add_argument('--revision',default='v1')
    p.add_argument('--host',choices=['thu-wei','thu-sui','thu-song'],help='Host for a new submission; existing runs retain their host')
    a=p.parse_args(); run_id='%s-%s-%s-%s'%(PREFIX,a.version,a.corner,a.revision)
    if a.action in ['prepare','submit']:
        path=prepare(a.version,a.corner,a.revision);result=dict(recipe=path)
        if a.action=='submit':
            result['registration']=engine().register(path,host=a.host)
            result['submission']=engine().phase('submit',run_id,queue=True)
    elif a.action=='collect':result=engine().collect(run_id)
    else:result=engine().phase(a.action,run_id,queue=a.action=='analyze')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
