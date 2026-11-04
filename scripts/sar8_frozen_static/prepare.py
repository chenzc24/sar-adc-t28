"""Freeze historical bytes and prepare immutable TT static characterization cases."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / 'netlist/sar8_l90_mmain2_frozen'
VERIFY = ROOT / 'verification/sar8_frozen_static'
SHA = '41d5444c4fcc3f26b097cca609474804afde2e61616c424c8a0cb8a5b2f298c4'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def freeze():
    sources = sorted((ROOT / 'output/sar8_ref_length').glob('l90_*_static/dut.scs'))
    assert len(sources) == 5 and all(digest(p) == SHA for p in sources)
    text = sources[0].read_text()
    count = [0]
    def inverse(m):
        s, n = re.subn(r'\bl=90n\b', 'l=30n', m[0])
        assert n == 2
        count[0] += 1
        return s
    parent = re.sub(r'(?ms)^subckt sar8j_r1_sw_b[0-7] .*?^ends sar8j_r1_sw_b[0-7]', inverse, text)
    assert count[0] == 8
    assert parent == (ROOT / 'output/sar8_main_width/w2_tt_090_27_static/dut.scs').read_text()
    FROZEN.mkdir(parents=True, exist_ok=True)
    target = FROZEN / 'dut.scs'
    if target.exists():
        assert digest(target) == SHA
    else:
        target.write_bytes(sources[0].read_bytes())
    manifest = dict(design_id='sar8_l90_mmain2_frozen', source_commit='e94e8028e6dcc9aa843116a7d0c46c865df5f7b7',
        dut_sha256=SHA, historical_duts=[str(p.relative_to(ROOT)).replace('\\','/') for p in sources],
        identical_five_historical_duts=True, inverse_to_mmain2_l30_exact=True,
        only_reference_length_parameters_changed=16,
        mmain='two explicit 1um/150nm devices per side', reference_switch_length_nm=90,
        base_idle_reset_commit='027b951', OA_changed=False, adopted_baseline=False,
        qualification='Functional characterization snapshot; startup and stress remain open',
        source_evidence=['verification/sar8_ref_length/integrated_comparison.json', 'verification/sar8_ref_length/validation.json'])
    dump(FROZEN / 'manifest.json', manifest)


def prepare(first, last):
    assert 1 <= first <= last <= 255
    assert digest(FROZEN / 'dut.scs') == SHA
    run_id = 'sar8frozen-tt-%03d-%03d-v1' % (first,last)
    folder = VERIFY / run_id
    assert not folder.exists(), 'Immutable case already exists'
    frames = 4 + (last-first+1)*10 + 1
    header = (ROOT / 'netlist/sar8_physical/tt_nominal.scs').read_text().split('\ntran_physical')[0]
    header = header.replace('    sensfile="../psf/sens.output" checklimitdest=psf', '    checklimitdest=psf')
    tb = (ROOT / 'netlist/sar8_physical/tb.scs').read_text()
    tb = '\n'.join(s for s in tb.splitlines() if not s.startswith(('VVINN ', 'VVINP '))) + '\n'
    # Keep reference independent of VDD for future PVT; identical at this TT point.
    tb = tb.replace('VREFHIGH (VREFP_SRC 0) vsource dc=SUP', 'VREFHIGH (VREFP_SRC 0) vsource dc=0.9')
    text = header + '\nXSTIM (VINP_SRC VINN_SRC D0 D1 D2 D3 D4 D5 D6 D7) r4_transition_stim first_k=%d last_k=%d warmup=4 refine=7 half_span_lsb=0.5\n' % (first,last)
    text += 'XMEASURE (XDUT.SAMPLE_INT XDUT.CMP_CLK XDUT.XCTRL.PHI_W XDUT.PHI_U XDUT.XREF.CAP_CLK VDD! VINP_SRC VINN_SRC XDUT.TOPP XDUT.TOPN D0 D1 D2 D3 D4 D5 D6 D7) r4_perf_monitor\n'
    saves = ['D%d'%b for b in range(8)] + ['SAMPLE','VDD!','XDUT.SAMPLE_INT','XDUT.CMP_CLK','XDUT.TOPP','XDUT.TOPN','VINP_SRC','VINN_SRC']
    text += 'tran_perf tran stop=%dn maxstep=10p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=strobeonly\nsave %s\n' % (frames*100,' '.join(saves))
    folder.mkdir(parents=True)
    for name in ['r4_transition_stim.va','r4_perf_monitor.va']:
        text += 'ahdl_include "%s"\n' % name
        (folder/name).write_bytes((ROOT/'models/veriloga/sar8_r4_performance'/name).read_bytes())
    (folder/'test.scs').write_text(text, encoding='utf-8')
    (folder/'tb.scs').write_text(tb, encoding='utf-8')
    context = dict(run_id=run_id, first=first, last=last, warmup=4, refine=7, frames=frames,
        dut_sha256=SHA, stop_s=frames*100e-9, code_read_ns=98, sampled_range_v=[-.9,.9],
        fullscale_v=1.8, corner='tt',vdd=.9,reference_v=.9,temperature_c=27,
        requested_reltol=1e-6,requested_maxstep_s=1e-11,noise=False,mismatch=False,PEX=False,
        startup_separate=True,stress_deferred_not_qualified=True)
    dump(folder/'context.json',context)
    paths = [folder/n for n in ['test.scs','tb.scs','r4_transition_stim.va','r4_perf_monitor.va','context.json']]
    paths += [FROZEN/'dut.scs', ROOT/'scripts/sar8_frozen_static/reduce.py']
    recipe = dict(schema_version=1,run_id=run_id,design_id='sar8_l90_mmain2_frozen',entry='test.scs',analyzer='reduce.py',
        inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=p.name,sha256=digest(p)) for p in paths],
        expected_stop_s=context['stop_s'], summary_signals=[s.lower() for s in saves],
        test_conditions=context, qualification_scope='Steady-state static function only; retained startup/stress limitations',
        oa_parity='Netlist-only frozen historical candidate; OA unchanged',
        spectre_args=['+preset=cx','+mt=4','-preset_override','+lqtimeout','60'],
        resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,
            analysis_virtual_mib=1024,max_output_mib=2048,simulation_wall_seconds=43200,
            analysis_wall_seconds=1200,queue_timeout_seconds=7200))
    dump(ROOT/'management/recipes'/('%s.yaml'%run_id),recipe)
    print(json.dumps(dict(run_id=run_id,frames=frames,dut_sha256=SHA)))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--first',type=int);p.add_argument('--last',type=int)
    a=p.parse_args()
    if a.freeze:freeze()
    if a.first is not None:prepare(a.first,a.last)
