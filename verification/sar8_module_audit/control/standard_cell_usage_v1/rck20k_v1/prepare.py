"""One exact electrical change; local preparation only; frozen sources read-only."""
from pathlib import Path
import copy
import difflib
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
USAGE=HERE.parent
OWN=USAGE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
import prepare_first_event as base
from review_standard_cell_storage_v2 import record,identity


def read(p):return json.loads(p.read_bytes())
def dump(p,o):base.exact_write(p,json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n')
def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Expected exactly one frozen transform:'+old[:60])
    return text.replace(old,new)


def main():
    source=record('sar8audit-ctrl-usage-rck2k-ff-v1')
    assert source['recipe_hash']=='997693935954ebbce4f0d4191e0a55ac1e1f391d7502bd5f5005c92c39876b3a'
    source_files={x['name']:ROOT/x['source'] for x in source['recipe']['files']}
    old=source_files['dut.scs'].read_text();new=replace(old,'resistor r=2000\n','resistor r=20000\n')
    base.exact_write(HERE/'dut.scs',new)
    base.exact_write(HERE/'test.scs',source_files['test.scs'].read_text())
    cfg=read(source_files['measurement.json']);cfg['usage']['case']='rck20k_v1';dump(HERE/'measurement.json',cfg)
    spec=importlib.util.spec_from_file_location('frozen_usage_prepare',USAGE/'prepare.py')
    prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
    _,flat=prep.measurement(new)
    previous=read(USAGE/'manifest.json')['cases']['rck2k']['physical_leaves']
    changed=[k for k in flat if flat[k]!=previous[k]]
    assert set(flat)==set(previous) and changed==['XDUT.RCK']
    assert flat['XDUT.RCK']==dict(previous['XDUT.RCK'],parameters='r=20000')
    assert len(cfg['observed_mos'])==58 and len(cfg['stress_voltage_pairs'])==348
    assert len(cfg['voltage_saves'])==37 and len(cfg['current_saves'])==75 and len(cfg['kcl_terms'])==6
    diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen_rck2k/dut.scs',tofile='rck20k_v1/dut.scs'))
    base.exact_write(HERE/'single_variable.diff',diff)
    recovery=USAGE/'characterization/liberty_v2/attribute_recovery';normalized=read(recovery/'normalized_coordinate.json')
    assert normalized['all_sampled_normalized_input_coordinates_within_axes']
    old_compare=read(USAGE/'results/comparison.json')
    reference=copy.deepcopy(old_compare['cases'])
    for case,entry in reference.items():
        rec=record(entry['proof']['source_run_id']);assert rec['recipe_hash']==entry['proof']['source_recipe_sha256']
        entry['input_ranges']=normalized['edge_ranges'][case]
    config=dict(nodes=dict(CP='XDUT.U19_CK',D='XDUT.U19_D',CDN='XDUT.XU19.RN',
        clkb='XDUT.XU19.XFF.clkb',clkbb='XDUT.XU19.XFF.clkbb',mq='XDUT.XU19.XFF.mq'),
        input_basis={p:{edge:dict(threshold_pct=[30.,70.],slew_derate_from_library=.5,
                transition_axis_s=[1.5e-12,262.9e-12]) for edge in ['rise','fall']} for p in ['CP','D','CDN']},
        normalization_source=normalized['normalization_source'],normalization_evidence=identity(recovery/'normalized_coordinate.json'),
        reference_comparison_evidence=identity(USAGE/'results/comparison.json'),reference_cases=reference,
        focus_direction=dict(CP=-1,clkb=1,clkbb=-1,mq=-1),focus_window_s=[5e-9,5.06e-9],
        diagnostic_CP_raw30_70_target_s=5e-12,no_timing_recenter=True)
    dump(HERE/'extension_config.json',config)
    wrapper=(USAGE/'usage_analyze.py').read_text()
    wrapper=wrapper[:wrapper.index('\ndef pin_edges(')]+wrapper[wrapper.index('\ndef main():'):]
    wrapper=replace(wrapper,'import fast_gate_analyze as native','import fast_gzip_analyze as native')
    wrapper=replace(wrapper,'import standard_cell_full_analyze as storage','import standard_cell_full_analyze as storage\nimport storage_gzip as history\nimport usage_gzip as usage\nimport transition_observe as extension')
    wrapper=replace(wrapper,"storage.observe_history(output,cfg)","history.observe_history(output,cfg)")
    wrapper=replace(wrapper,"usage_observations(output,cfg)","usage.usage_observations(output,cfg)\n    result['transition_diagnostic']=extension.observe(output,cfg,native.read(os.path.join(run,'inputs/extension_config.json')),result)")
    wrapper=replace(wrapper,"storage.compress_history(output)","history.verify_compressed(output,cfg,result)")
    wrapper=replace(wrapper,"'NATIVE_DFF_USAGE_DIAGNOSTIC_COMPLETE'","'NATIVE_DFF_RCK20K_GZIP_DIAGNOSTIC_COMPLETE'")
    base.exact_write(HERE/'analyze.py',wrapper)
    recovery_gzip=USAGE/'recovery_v1'
    inputs=[(name,HERE/name) for name in ['test.scs','dut.scs','measurement.json','extension_config.json','analyze.py','transition_observe.py']]
    inputs += [(name,recovery_gzip/name) for name in ['fast_gzip_analyze.py','stream_gzip.py','storage_gzip.py','usage_gzip.py']]
    inputs += [(name,source_files[name]) for name in ['external_library.json','full_gate_analyze.py','standard_cell_full_analyze.py']]
    inputs += [(name,source_files[name]) for name in source_files if name.startswith('pwl/')]
    recipe=read(USAGE/'rck2k/recipe.suggested.yaml')
    recipe.update(run_id='sar8audit-ctrl-usage-rck20k-ff-v1',design_id='native_DFCNQD1_U19_slew_diagnostic_rck20k',
        analyzer='analyze.py',inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=identity(p)['sha256']) for n,p in inputs])
    dump(HERE/'recipe.suggested.yaml',recipe)
    frozen=[dict(name=n,source=p.relative_to(ROOT).as_posix(),**identity(p)) for n,p in inputs]
    dump(HERE/'manifest.json',dict(status='local_prepared_not_registered_not_run',source_run_id=source['recipe']['run_id'],
        source_recipe_hash=source['recipe_hash'],source_inputs={n:identity(p) for n,p in source_files.items()},
        sole_electrical_change=dict(instance='XDUT.RCK',old_ohm=2000,new_ohm=20000),
        identical_test_scs=identity(HERE/'test.scs')==identity(source_files['test.scs']),
        measurement_metadata_change_only='usage.case:rck2k->rck20k_v1',MOS=58,voltage_saves=37,current_saves=75,terminal_pairs=348,KCL_nodes=6,
        changed_physical_leaves=changed,physical_leaves=flat,inputs=frozen,library_internals_unchanged=True,
        direct_gzip_no_uncompressed_scratch=True,actual_delayed_clock_preserved=True,no_remote_actions=True,
        physical_RCK_implementation=False,formal_PDK_pairing_proven=False,whole_ADC_qualified=None))
    dump(HERE/'freeze.json',dict(status='frozen_for_parent_managed_admission_only',run_id=recipe['run_id'],
        proposed_recipe_file=identity(HERE/'recipe.suggested.yaml'),manifest=identity(HERE/'manifest.json'),
        input_count=len(frozen),input_bytes=sum(x['bytes'] for x in frozen),single_variable_diff=identity(HERE/'single_variable.diff')))
    print('RCK20K_LOCAL_PACKAGE_PREPARED',identity(HERE/'recipe.suggested.yaml')['sha256'],'inputs',len(frozen),'no_remote')


if __name__=='__main__':main()
