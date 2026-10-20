"""Audit execution evidence separately from candidate performance acceptance.

Exit zero means evidence is internally consistent, NOT that the design passed.
Use --require-qualified to fail on open performance/implementation gates.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/cdac8_device'))
from common import OUT,LSB,LIMIT,load,dump,sha,cfg
from analyze_system import warning
import yaml

def main(require=False):
    bank=load('banks/summary_200.json');audit=load('audit.json')
    assert bank['numruns']==200 and bank['random_variables']==512
    assert bank['internal_pass_count']==200
    assert len(audit['zero_marker_schematics'])==35
    assert len(audit['readonly_equal'])==6 and len(audit['fresh_exports'])==11
    assert audit['va_source_equal'] and all(r['equal_except_timestamp'] for r in audit['fresh_exports'])
    manifest=yaml.safe_load((ROOT/'virtuoso/cell_manifest.yaml').read_text())
    assert all(n in manifest['cells'] for n in audit['zero_marker_schematics'])
    dynamic=load('transient/summary_dynamic.json')
    for name in ('final_static','final_dac',dynamic['name'],'ideal_dac'):
        result=load(f'transient/{name}_result.json');case=load(f'transient/{name}_case.json')
        assert result['ok'],result['errors']
        source=OUT/'oa_netlists'/case['cell']/case['oa_tag']/'input.scs'
        assert case['oa_sha256']==sha(source)
        for va,digest in case['owned_va_sha256'].items():
            assert sha(ROOT/'models/veriloga'/va)==digest
    dac=load('transient/summary_dac.json');dynamic=load('transient/summary_dynamic.json')
    static=load('transient/summary_static.json');pvt=load('transient/summary_pvt.json')
    trace=load('transient/bit_settling.json');iso=load('transient/input_isolation.json')
    assert len(pvt)==13 and len(trace)==8 and dynamic['samples']==1024 and static['samples']==256
    assert abs(iso['ideal_input_hold_first_mv'])<.01
    gates={
        'cap_local_mc_weight_margin':'pass' if bank['dnl_worst_lsb']<=.5 and bank['inl_worst_lsb']<=.5 else 'fail',
        'nominal_dac_static':'pass' if dac['monotonic'] and max(dac['dnl_abs_max_lsb'],dac['inl_raw_abs_max_lsb'])<=.5 else 'fail',
        'adc_code_center_consistency':'pass' if static['code_center_mismatches']==0 else 'fail',
        'nominal_comparison_residual':'pass' if max(abs(x['raw_error_mv']) for x in trace)<=LIMIT*1000 else 'fail',
        'nominal_dynamic_no_physical_noise':'pass' if dynamic['enob_target_pass'] else 'fail',
        'native_reference_stress':'pass' if warning(load('transient/stress_trace_result.json'))['cmi_printed']==0 else 'fail',
        'first_full_swing_pvt_acquisition':'pass' if all(x['accuracy_pass'] for x in pvt) else 'fail',
        'real_strongarm_interface_stress':'pass' if warning(load('transient/balanced_comparator_result.json'))['cmi_printed']==0 else 'fail',
        'physical_noise_and_mos_mc':'not_run','adc_transition_linearity':'not_run',
        'native_reference_buffer_and_clock_tree':'not_implemented','layout_drc_lvs_pex':'not_run'}
    qualified=all(v=='pass' for v in gates.values())
    assert cfg()['candidate_qualified']==qualified
    result={'execution_evidence_consistent':True,'candidate_qualified':qualified,'gates':gates,
            'note':'A zero exit from this evidence audit is not circuit acceptance.'}
    dump('acceptance.json',result);print(json.dumps(result,indent=2))
    if require and not qualified:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--require-qualified',action='store_true');main(p.parse_args().require_qualified)
