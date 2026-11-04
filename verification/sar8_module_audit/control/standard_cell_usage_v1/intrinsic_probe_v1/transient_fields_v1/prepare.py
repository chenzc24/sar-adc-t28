"""One baseline+13 named numeric fields package; no native execution."""
from pathlib import Path
import difflib,json,sys
HERE=Path(__file__).resolve().parent
USAGE=HERE.parents[1]
OWN=USAGE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
import prepare_first_event as base
from review_standard_cell_storage_v2 import record,identity
from review_standard_cell_full_result import receipt_files

FIELDS=['ids','id','vds','vgs','gm','gds','igs','igd','igb','ibs','ibd','igidl','igisl']
TARGET='XDUT.XU19.XFF.MM65'


def dump(p,obj):base.exact_write(p,json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
def replace(s,a,b):
    if s.count(a)!=1:raise ValueError('Exact source transform count differs')
    return s.replace(a,b)


def main():
    source=record('sar8audit-ctrl-usage-baseline-ff-v1')
    assert source['recipe_hash']=='a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1'
    files={x['name']:ROOT/x['source'] for x in source['recipe']['files']}
    recovered_run='sar8audit-ctrl-mm65-opmap-recovery-v1';rec=record(recovered_run)
    assert rec['recipe_hash']=='6dad2f98b9fa87ab178f879416527217301cb1907feb417c96e8b142f1208920'
    folder=ROOT/'output/managed_execution/runs'/recovered_run/'collected';receipt,collected=receipt_files(folder)
    r=json.loads(collected['derived/result.json'].read_bytes());scope=r['recovered_OP']['target_instance_scopes'][TARGET]
    assert scope['field_count']==98 and r['expected_port_mapping_match']
    for name in FIELDS:assert name in scope['fields'] and scope['fields'][name]['explicit_unit']
    old=files['test.scs'].read_text();extra='\n// Actual exposed MM65 numeric fields; meanings remain named-only.\n'+''.join('save '+TARGET+':'+name+'\n' for name in FIELDS)
    base.exact_write(HERE/'test.scs',old+extra)
    base.exact_write(HERE/'single_measurement.diff',''.join(difflib.unified_diff(old.splitlines(True),(old+extra).splitlines(True),fromfile='frozen_direct_baseline/test.scs',tofile='transient_fields_v1/test.scs')))
    fields={name:dict(save=TARGET+':'+name,expected_dimension='V' if name in ['vds','vgs'] else 'S' if name in ['gm','gds'] else 'A',
        static_reported_unit=scope['fields'][name]['explicit_unit'],static_unit_not_used_to_assign_transient_scale=True) for name in FIELDS}
    ref=dict(node_d='XDUT.XU19.XFF.net176',node_g='XDUT.XU19.XFF.mq',node_s='XDUT.XU19.XFF.net184',CP='XDUT.U19_CK',clkbb='XDUT.XU19.XFF.clkbb')
    reference={k:dict(save=v,unit='V') for k,v in ref.items()}
    for j,role in enumerate('dgsb',1):reference['total_'+role]=dict(save=TARGET+':'+str(j),unit='A')
    reference.update(MM64_S=dict(save='XDUT.XU19.XFF.MM64:3',unit='A'),MM66_D=dict(save='XDUT.XU19.XFF.MM66:1',unit='A'))
    config=dict(target=TARGET,field_order=FIELDS,fields=fields,reference_order=sorted(reference),reference_signals=reference,
        ground_B_V=0.,ground_B_is_explicit_source_node=True,stop_s=20e-9,snapshot_times_s=[5e-9,5.03e-9,5.5e-9,5.95e-9],
        compressed_field_cap_bytes=6*1024**2,region_omitted_reason='Only enum text observed; native waveform code format not yet established',
        exposure_evidence=dict(run=recovered_run,managed_recipe_hash=rec['recipe_hash'],result=identity(collected['derived/result.json'])),
        ids_is_not_assigned_pure_channel=True,negative_VDS_convention_not_assigned=True,no_automatic_retry=True)
    dump(HERE/'fields.json',config)
    wrapper=(USAGE/'usage_analyze.py').read_text()
    wrapper=wrapper[:wrapper.index('\ndef pin_edges(')]+wrapper[wrapper.index('\ndef main():'):]
    wrapper=replace(wrapper,'import fast_gate_analyze as native','import base_gzip_analyze as native')
    wrapper=replace(wrapper,'import standard_cell_full_analyze as storage','import standard_cell_full_analyze as storage\nimport storage_gzip as history\nimport usage_gzip as usage\nimport field_capture')
    wrapper=replace(wrapper,'result=native.summarize(raw[0],cfg,output)',
        "field_report=field_capture.capture(raw[0],output,native.read(os.path.join(run,'inputs/fields.json')))\n    native.write_new(os.path.join(output,'field_capture.json'),field_report)\n    result=native.summarize(raw[0],cfg,output)\n    assert field_report['source_raw_sha256']==result['raw_sha256'] and field_report['native_points']==result['native_points']\n    result['MM65_named_field_capture']=field_report")
    wrapper=replace(wrapper,'storage.observe_history(output,cfg)','history.observe_history(output,cfg)')
    wrapper=replace(wrapper,'usage_observations(output,cfg)','usage.usage_observations(output,cfg)')
    wrapper=replace(wrapper,'storage.compress_history(output)','history.verify_compressed(output,cfg,result)')
    wrapper=replace(wrapper,"'NATIVE_DFF_USAGE_DIAGNOSTIC_COMPLETE'","'NATIVE_MM65_NAMED_TRANSIENT_FIELDS_COMPLETE'")
    base.exact_write(HERE/'analyze.py',wrapper)
    original=(USAGE/'recovery_v1/fast_gzip_analyze.py').read_text();derived=(HERE/'base_gzip_analyze.py').read_text()
    base.exact_write(HERE/'reducer_delta.diff',''.join(difflib.unified_diff(original.splitlines(True),derived.splitlines(True),fromfile='frozen_fast_gzip_analyze.py',tofile='base_gzip_analyze.py')))
    inputs=[(n,HERE/n) for n in ['test.scs','fields.json','field_capture.py','base_gzip_analyze.py','analyze.py']]
    inputs +=[(n,files[n]) for n in ['dut.scs','measurement.json','external_library.json','full_gate_analyze.py','standard_cell_full_analyze.py']]
    inputs +=[(n,USAGE/'recovery_v1'/n) for n in ['stream_gzip.py','storage_gzip.py','usage_gzip.py']]
    inputs +=[(n,p) for n,p in files.items() if n.startswith('pwl/')]
    recipe=json.loads((USAGE/'baseline/recipe.suggested.yaml').read_bytes())
    recipe.update(run_id='sar8audit-ctrl-mm65-transient-fields-ff-v1',design_id='native_DFCNQD1_U19_MM65_named_transient_fields',analyzer='analyze.py',
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=identity(p)['sha256']) for n,p in inputs],
        qualification_scope='Original direct fixture plus13exposed numeric MM65 named OP fields; preserve total-port/function/stress, no pure-channel or negative-VDS meaning assumed')
    dump(HERE/'recipe.suggested.yaml',recipe)
    manifest=dict(status='prepared_not_submitted',source_run=source['recipe']['run_id'],source_recipe_hash=source['recipe_hash'],
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),**identity(p)) for n,p in inputs],
        source_inputs={n:identity(p) for n,p in files.items()},electrical_or_timing_change=False,only13numeric_save_additions=True,
        original36V73I_58MOS348pairs_preserved=True,original_measurement_DUT_PWL_identical=True,region_not_saved=True,
        supplemental_units_from_native_header_only=True,missing_or_invalid_values_not_zero=True,model_alias_not_guessed=True,
        exposure_evidence=config['exposure_evidence'],reducer_change='Ignore only known unselected extra OP scalar updates before numerical decoding; original selected arithmetic unchanged',
        original_reducer=identity(USAGE/'recovery_v1/fast_gzip_analyze.py'),whole_ADC_qualified=None,no_remote_execution=True)
    dump(HERE/'manifest.json',manifest)
    print('LOCAL_MM65_TRANSIENT_MEASUREMENT_PREPARED',identity(HERE/'recipe.suggested.yaml')['sha256'],'not_yet_frozen_pending_one_check')


if __name__=='__main__':main()
