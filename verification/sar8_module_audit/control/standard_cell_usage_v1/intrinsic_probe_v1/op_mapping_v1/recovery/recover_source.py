"""Completed-source metadata recovery only. Python2.7/3; never runs a simulator."""
from __future__ import print_function
import argparse,hashlib,json,os,re,sys
sys.dont_write_bytecode=True
import read_info_v2 as parser


def read(p):
    with open(p) as f:return json.load(f)


def identity(p):
    h=hashlib.sha256();n=0
    with open(p,'rb') as f:
        while True:
            b=f.read(65536)
            if not b:break
            h.update(b);n+=len(b)
    return dict(bytes=n,sha256=h.hexdigest())


def inside(p,root):return p==root or p.startswith(root+os.sep)


def safe(root,name):
    p=os.path.realpath(os.path.join(root,name))
    if not inside(p,root) or os.path.islink(os.path.join(root,name)) or not os.path.isfile(p):raise ValueError('Unsafe/missing bound source:'+name)
    return p


def verify(run,source,binding):
    if os.path.basename(source)!=binding['source_run_id']:raise ValueError('Wrong completed source directory')
    recipe=read(safe(source,'recipe.json'))
    h=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if h!=binding['source_recipe_hash']:raise ValueError('Canonical source recipe mismatch')
    reg=read(safe(source,'registered.json'))
    if reg.get('recipe_hash')!=h or not reg.get('files_complete'):raise ValueError('Completed source registration differs')
    provenance=read(safe(run,'source_provenance.json'))
    if provenance.get('run_id')!=binding['source_run_id'] or provenance.get('recipe_hash')!=h or os.path.realpath(provenance.get('path',''))!=source:
        raise ValueError('Managed source provenance mismatch')
    for rel,key in [('recipe.json','recipe_file_sha256'),('registered.json','registration_sha256'),('simulation.state.json','simulation_state_sha256')]:
        if provenance.get(key)!=identity(safe(source,rel))['sha256']:raise ValueError('Managed source identity changed:'+rel)
    for rel,want in binding['source_outputs'].items():
        if identity(safe(source,rel))!=want:raise ValueError('Exact completed output changed:'+rel)
    for name,want in binding['source_inputs'].items():
        if identity(safe(source,'inputs/'+name))!=want:raise ValueError('Frozen source input changed:'+name)
    sim=read(safe(source,'simulation.state.json'));analysis=read(safe(source,'analysis.state.json'))
    if sim['status']!='complete' or sim['exit_code']!=0 or not sim['native']['native_analysis_pass'] or not sim['native']['zero_error_footer']:
        raise ValueError('Completed native PASS required')
    if analysis['status']!='complete' or analysis['exit_code']!=0:raise ValueError('Exact completed original analysis required')
    return provenance


def main():
    a=argparse.ArgumentParser()
    for n in ['run-dir','output-dir','source-run-dir']:a.add_argument('--'+n,required=True)
    args=a.parse_args();run,output,source=[os.path.realpath(p) for p in [args.run_dir,args.output_dir,args.source_run_dir]]
    if inside(run,source) or inside(source,run) or output!=os.path.join(run,'derived'):raise ValueError('Disjoint managed recovery output required')
    if os.path.isdir(output) and os.listdir(output):raise ValueError('Preserve existing recovery derived output')
    binding=read(safe(run,'inputs/source_binding.json'));provenance=verify(run,source,binding)
    original=read(safe(source,'derived/result.json'))
    if len(original['native_field_exposure']['reports']['oppoint']['fields'])!=0:raise ValueError('Bound source is not the original empty-field result')
    op=safe(source,'raw/opmap_oppoint.txt');nodes=safe(source,'raw/opmap_nodes.txt')
    for p in [op,nodes]:
        if os.path.getsize(p)>256*1024:raise ValueError('Bound metadata size cap exceeded')
    recovered=parser.read_op(op);ports=parser.read_nodes(nodes)
    root_scope=recovered['target_instance_scopes'].get(parser.TARGET)
    field_count=root_scope['field_count'] if root_scope else 0
    observed=ports['instances'].get(parser.TARGET,{}).get('ports',{})
    actual={k:v['node'] for k,v in observed.items()}
    expected=binding['expected_ports'];match=actual==expected
    verify(run,source,binding)
    result=dict(analysis_complete=True,analysis_kind='completed_native_metadata_recovery_only',source_run_id=binding['source_run_id'],
        source_recipe_hash=binding['source_recipe_hash'],source_provenance=provenance,original_result_identity=binding['source_outputs']['derived/result.json'],
        original_empty_field_result_preserved=True,source_info_identities={os.path.basename(p):identity(p) for p in [op,nodes]},
        recovered_OP=recovered,recovered_ports=ports,expected_port_mapping_match=match,recovered_root_field_count=field_count,
        original_alias_interpretation_superseded='MM65.nch was a truncated Model identifier, not confirmed as an Instance alias',
        source_function_stress_summary=dict(native_points=original['native_points'],pairs=len(original['full_history_voltage_stress']),
            failed_pairs=sum(bool(x['over_limit_native_points']) for x in original['full_history_voltage_stress'].values()),
            stable_hold_pass=original['storage_observations']['stable_hold_observation_pass'],Q_edge_patterns_pass=original['storage_observations']['clean_expected_Q_edge_patterns'],
            MM64_VDS_max_V=original['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS']['max_abs_v'],native_warning_codes=original['native_warning_codes']),
        source_native_waveform_reanalyzed=False,source_PSF_rehashed=False,new_simulation=False,
        actual_TMI_current_definition_verified=False,pure_channel_inference=False,static_OP_time_not_assigned=True,whole_ADC_qualified=None)
    if not os.path.isdir(output):os.makedirs(output)
    blob=(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    if len(blob)>256*1024:raise ValueError('Metadata result cap exceeded')
    with open(os.path.join(output,'result.json'),'wb') as f:f.write(blob)
    print('NATIVE_INFO_METADATA_RECOVERED',field_count,'port_mapping',match,'no_native_rerun')


if __name__=='__main__':main()
