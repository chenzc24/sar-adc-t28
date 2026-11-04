"""One measurement-only package from exact native direct baseline; local only."""
from pathlib import Path
import difflib
import json
import sys

HERE=Path(__file__).resolve().parent
USAGE=HERE.parents[1]
OWN=USAGE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
import prepare_first_event as base
from review_standard_cell_storage_v2 import record,identity


def read(p):return json.loads(p.read_bytes())
def dump(p,obj):base.exact_write(p,json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')
def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Unexpected source transform count:'+old[:60])
    return text.replace(old,new)


def main():
    rec=record('sar8audit-ctrl-usage-baseline-ff-v1')
    assert rec['recipe_hash']=='a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1'
    files={x['name']:ROOT/x['source'] for x in rec['recipe']['files']}
    helps={topic:read(HERE/('installed_'+topic+'_help.json')) for topic in ['info','save']}
    for topic,result in helps.items():
        meta=result['metadata'];assert result['returncode']==0 and meta['returncode']==0 and meta['stop_reason'] is None
        assert meta['command'][-1]==topic and meta['elapsed_s']<8 and meta['captured_bytes']<=524288
    info='\n'.join(x['text'] for x in helps['info']['metadata']['selected_semantics'])
    save='\n'.join(x['text'] for x in helps['save']['metadata']['selected_semantics'])
    assert 'Name info <parameter=value>' in info and 'file="%C:r.info.what"' in info
    assert all(word in info for word in ['primitives','nodes','what=oppoint','descriptions=no','where=logfile','oppoint=all'])
    assert 'save X[:param]' in save and 'operating point parameter name' in save
    old=files['test.scs'].read_text()
    extra='\n// MM65 native field exposure; static info, no transient OP save additions.\n'
    reports=dict(primitives='opmap_primitives.txt',inst='opmap_inst.txt',nodes='opmap_nodes.txt',oppoint='opmap_oppoint.txt')
    for what,name in reports.items():
        tail=' oppoint=dev save=all' if what=='oppoint' else ''
        extra+='opmap_'+what+' info what='+what+' where=file file="../raw/'+name+'" descriptions=yes extremes=no'+tail+'\n'
    new=old+extra
    base.exact_write(HERE/'test.scs',new)
    base.exact_write(HERE/'single_measurement.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen_direct_baseline/test.scs',tofile='op_mapping_v1/test.scs')))
    config=dict(target='XDUT.XU19.XFF.MM65',info_files=reports,per_info_file_cap_bytes=2*1024**2,
        expected_public_ports_from_SPI=dict(D='XDUT.XU19.XFF.net176',G='XDUT.XU19.XFF.mq',S='XDUT.XU19.XFF.net184',B='0'),
        aliases_not_guessed=True,ids_id_named_only=True,transient_OP_waveforms_added=False,
        solution_time_not_assigned=True,help_proof={topic:dict(file=identity(HERE/('installed_'+topic+'_help.json')),
            captured_output_sha256=helps[topic]['metadata']['full_captured_output_sha256']) for topic in helps})
    dump(HERE/'mapping.json',config)
    wrapper=(USAGE/'usage_analyze.py').read_text()
    wrapper=wrapper[:wrapper.index('\ndef pin_edges(')]+wrapper[wrapper.index('\ndef main():'):]
    wrapper=replace(wrapper,'import fast_gate_analyze as native','import fast_gzip_analyze as native')
    wrapper=replace(wrapper,'import standard_cell_full_analyze as storage','import standard_cell_full_analyze as storage\nimport storage_gzip as history\nimport usage_gzip as usage\nimport read_info as opmap')
    wrapper=replace(wrapper,'storage.observe_history(output,cfg)','history.observe_history(output,cfg)')
    wrapper=replace(wrapper,'usage_observations(output,cfg)',"usage.usage_observations(output,cfg)\n    result['native_field_exposure']=opmap.observe(run,native.read(os.path.join(run,'inputs/mapping.json')))")
    wrapper=replace(wrapper,'storage.compress_history(output)','history.verify_compressed(output,cfg,result)')
    wrapper=replace(wrapper,"'NATIVE_DFF_USAGE_DIAGNOSTIC_COMPLETE'","'NATIVE_MM65_FIELD_EXPOSURE_COMPLETE'")
    base.exact_write(HERE/'analyze.py',wrapper)
    inputs=[(n,HERE/n) for n in ['test.scs','mapping.json','analyze.py','read_info.py']]
    inputs += [(n,files[n]) for n in ['dut.scs','measurement.json','external_library.json','full_gate_analyze.py','standard_cell_full_analyze.py']]
    inputs += [(n,USAGE/'recovery_v1'/n) for n in ['fast_gzip_analyze.py','stream_gzip.py','storage_gzip.py','usage_gzip.py']]
    inputs += [(n,p) for n,p in files.items() if n.startswith('pwl/')]
    recipe=read(USAGE/'baseline/recipe.suggested.yaml')
    recipe.update(run_id='sar8audit-ctrl-mm65-opmapping-ff-v1',design_id='native_DFCNQD1_U19_MM65_info_exposure',analyzer='analyze.py',
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=identity(p)['sha256']) for n,p in inputs],
        qualification_scope='One unchanged direct native U19 fixture plus static MM65 native info/OP field exposure; named quantities only, no pure-channel or reliability gate')
    dump(HERE/'recipe.suggested.yaml',recipe)
    frozen=[dict(name=n,source=p.relative_to(ROOT).as_posix(),**identity(p)) for n,p in inputs]
    dump(HERE/'manifest.json',dict(status='prepared_not_registered_not_run',source_run_id=rec['recipe']['run_id'],source_recipe_hash=rec['recipe_hash'],
        inputs=frozen,source_inputs={n:identity(p) for n,p in files.items()},electrical_change=False,
        appended_info_only=True,original_test_prefix_sha256=identity(files['test.scs'])['sha256'],
        original_dut_measurement_PWL_and_saves_unchanged=True,original_tran_statement_unchanged=True,
        MOS=58,pairs=348,voltage_saves=36,current_saves=73,KCL_nodes=6,
        native_info_scope='Small existing circuit info files; only bounded MM65/header/type/port/OP-field metadata returned',
        no_transient_OP_group_addition=True,no_model_parameter_body_returned=True,
        model_current_meaning_unknown=True,ids_id_not_acceptance_gate=True,no_automatic_retry=True,
        helper_syntax_evidence=config['help_proof'],managed_simulation_cwd_evidence='scripts/management/remote_agent.py:279 cd exact run/inputs; raw created at registration',
        owner_no_remote_execution=True,whole_ADC_qualified=None))
    dump(HERE/'freeze.json',dict(status='frozen_for_parent_admission_only',run_id=recipe['run_id'],
        proposed_recipe_file=identity(HERE/'recipe.suggested.yaml'),manifest=identity(HERE/'manifest.json'),
        input_count=len(frozen),input_bytes=sum(x['bytes'] for x in frozen),single_measurement_diff=identity(HERE/'single_measurement.diff')))
    print('LOCAL_MM65_INFO_PACKAGE_PREPARED',identity(HERE/'recipe.suggested.yaml')['sha256'],'inputs',len(frozen),'no_native_run')


if __name__=='__main__':main()
