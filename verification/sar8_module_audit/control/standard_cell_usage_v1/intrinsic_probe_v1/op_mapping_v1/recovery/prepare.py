"""Bind one metadata-only recovery to the exact completed OP run; local only."""
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent
OWN=HERE.parents[3]
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
import prepare_first_event as base
from review_standard_cell_storage_v2 import record,identity
from review_standard_cell_full_result import receipt_files


def dump(path,obj):base.exact_write(path,json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')


def main():
    run='sar8audit-ctrl-mm65-opmapping-ff-v1';rec=record(run)
    assert rec['recipe_hash']=='d6ea28629d09a0b808c2392767688153b3b8c72ac68e2ab3847a3826ab3006a8'
    folder=ROOT/'output/managed_execution/runs'/run/'collected';receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==rec['recipe_hash'] and not receipt.get('skipped')
    original=json.loads(files['derived/result.json'].read_bytes());assert not original['native_field_exposure']['reports']['oppoint']['fields']
    outputs={n:identity(files[n]) for n in ['simulation.state.json','analysis.state.json','derived/result.json','spectre.out','raw/logStatus']}
    for name,kind in [('opmap_oppoint.txt','oppoint'),('opmap_nodes.txt','nodes')]:
        outputs['raw/'+name]=original['native_field_exposure']['reports'][kind]['identity']
    binding=dict(source_run_id=run,source_recipe_hash=rec['recipe_hash'],
        source_inputs={x['name']:dict(bytes=x['bytes'],sha256=x['sha256']) for x in rec['recipe']['files']},
        source_outputs=outputs,expected_ports=dict(d='XDUT.XU19.XFF.net176',g='XDUT.XU19.XFF.mq',s='XDUT.XU19.XFF.net184',b='0'),
        original_result_empty_fields_preserved=True,original_raw_PSF_read_required=False,
        source_qualification='Completed native simulation and original full function/stress analysis retained unchanged; metadata-only recovery')
    dump(HERE/'source_binding.json',binding)
    inputs=[(n,HERE/n) for n in ['recover_source.py','read_info_v2.py','source_binding.json']]
    recipe=dict(schema_version=1,kind='analysis_only',source_run_id=run,
        run_id='sar8audit-ctrl-mm65-opmap-recovery-v1',design_id='native_DFCNQD1_U19_MM65_info_parser_recovery',
        entry='recover_source.py',analyzer='recover_source.py',
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=identity(p)['sha256']) for n,p in inputs],
        expected_stop_s=20e-9,summary_signals=rec['recipe']['summary_signals'],oa_parity='netlist_only',test_conditions=rec['recipe']['test_conditions'],
        qualification_scope='Exact completed source metadata only; explicit Instance scopes and full Model identifiers, no waveform reanalysis, native rerun or pure-channel claim',
        resources=dict(threads=1,analysis_rss_mib=256,analysis_virtual_mib=1024,analysis_wall_seconds=60,max_output_mib=8,queue_timeout_seconds=600))
    dump(HERE/'recipe.suggested.yaml',recipe)
    manifest=dict(status='prepared_not_submitted',source_run_id=run,source_recipe_hash=rec['recipe_hash'],
        source_collection_receipt=identity(folder/'collection_receipt.json'),source_original_result=identity(files['derived/result.json']),
        exact_metadata_files={n:outputs['raw/'+n] for n in ['opmap_oppoint.txt','opmap_nodes.txt']},
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),**identity(p)) for n,p in inputs],
        original_empty_fields_and_inputs_unchanged=True,scope_boundary='Explicit Instance header only; never Model or terminal node names',
        no_native_PSF_read=True,no_waveform_reanalysis=True,no_new_simulation=True,model_parameters_returned=False,
        original_alias_model_name_confusion_corrected=True,pure_channel_inference=False)
    dump(HERE/'manifest.json',manifest)
    dump(HERE/'freeze.json',dict(status='frozen_for_parent_analysis_only_admission',run_id=recipe['run_id'],
        recipe_file=identity(HERE/'recipe.suggested.yaml'),manifest=identity(HERE/'manifest.json'),
        input_count=len(inputs),input_bytes=sum(identity(p)['bytes'] for _,p in inputs)))
    print('LOCAL_METADATA_RECOVERY_PREPARED',identity(HERE/'recipe.suggested.yaml')['sha256'],'no_native_rerun')


if __name__=='__main__':main()
