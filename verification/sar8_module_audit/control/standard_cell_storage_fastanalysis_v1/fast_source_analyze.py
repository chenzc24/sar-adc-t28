"""Source-bound analysis only. Python2.7/3, no simulator or remote commands."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
sys.dont_write_bytecode=True

import fast_gate_analyze as fast
import standard_cell_full_analyze as frozen
import standard_cell_storage_v2_analyze as coverage


def inside(path,root):
    return path==root or path.startswith(root+os.sep)


def safe_file(root,relative):
    p=os.path.realpath(os.path.join(root,relative))
    if not inside(p,root) or os.path.islink(os.path.join(root,relative)) or not os.path.isfile(p):
        raise ValueError('Unsafe/missing source file: '+relative)
    return p


def activation(state,allow_not_started=False):
    if state is None and allow_not_started:
        return 'source_analysis_not_started_explicit_binding'
    if state is None:raise ValueError('Source analysis not started but this exact source binding forbids that activation')
    if state.get('status')=='limit_exceeded' and state.get('reason')=='wall_time_limit':
        return 'actual_source_analysis_wall_timeout'
    if state.get('status') in ['failed','interrupted'] and state.get('exit_code') not in [None,0]:
        return 'source_analysis_terminal_failure_or_parent_verified_targeted_stop'
    raise ValueError('Source analysis still running, already complete, or no authorized terminal failure')


def verify_source(run,source,binding):
    if os.path.basename(source)!=binding['source_run_id']:raise ValueError('Wrong source run directory')
    recipe=fast.read(safe_file(source,'recipe.json'))
    h=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if h!=binding['source_recipe_hash'] or recipe.get('kind','simulation')!='simulation':
        raise ValueError('Completed simulation recipe binding mismatch')
    reg=fast.read(safe_file(source,'registered.json'))
    if reg.get('recipe_hash')!=h or not reg.get('files_complete'):raise ValueError('Source registration mismatch')
    provenance=fast.read(safe_file(run,'source_provenance.json'))
    if (provenance.get('run_id')!=binding['source_run_id'] or provenance.get('recipe_hash')!=h
            or os.path.realpath(provenance.get('path',''))!=source):
        raise ValueError('Managed analysis-only source provenance mismatch')
    state_path=safe_file(source,'simulation.state.json');state=fast.read(state_path);native=state.get('native',{})
    for relative,key in [('recipe.json','recipe_file_sha256'),('registered.json','registration_sha256'),
                         ('simulation.state.json','simulation_state_sha256')]:
        if provenance.get(key)!=frozen.identity(safe_file(source,relative))['sha256']:
            raise ValueError('Managed source metadata digest differs: '+relative)
    if (state.get('status')!='complete' or state.get('exit_code')!=0 or
            not native.get('native_analysis_pass') or not native.get('zero_error_footer')):
        raise ValueError('Completed native simulation/PASS/footer required')
    if os.path.lexists(os.path.join(source,'analysis.state.json')):
        analysis_path=safe_file(source,'analysis.state.json');old_analysis=fast.read(analysis_path)
        analysis_sha=frozen.identity(analysis_path)['sha256']
    else:
        old_analysis=None;analysis_sha=None
    why=activation(old_analysis,binding.get('allow_analysis_not_started',False))
    for name,expected in binding['source_inputs'].items():
        if frozen.identity(safe_file(source,'inputs/'+name))!=expected:raise ValueError('Frozen source input changed: '+name)
    log=safe_file(source,'raw/logStatus')
    with open(log) as f:
        if not re.search(r'\btran_first\s+PASS\b',f.read()):raise ValueError('Source exact transient PASS missing')
    cfg_path=safe_file(run,'inputs/measurement.json')
    if frozen.identity(cfg_path)!=binding['source_inputs']['measurement.json']:
        raise ValueError('Analysis configuration differs from source')
    if frozen.identity(safe_file(run,'inputs/fast_gate_analyze.py'))['sha256']!=binding['fast_reducer_sha256']:
        raise ValueError('Unexpected fast reducer')
    for name in ['full_gate_analyze.py','standard_cell_full_analyze.py','standard_cell_storage_v2_analyze.py']:
        if frozen.identity(safe_file(run,'inputs/'+name))!=binding['source_inputs'][name]:
            raise ValueError('Frozen observation/coverage helper differs: '+name)
    return state,dict(run_id=binding['source_run_id'],recipe_hash=h,
        simulation_state_sha256=frozen.identity(state_path)['sha256'],
        source_analysis_state_sha256=analysis_sha,
        source_analysis_terminal_status=old_analysis['status'] if old_analysis is not None else 'not_started',
        source_analysis_not_started_is_not_a_failure=old_analysis is None,activation=why,
        native_simulation_started=False,source_read_only=True)


def analyze(run,output,source):
    run,output,source=[os.path.realpath(p) for p in [run,output,source]]
    if inside(run,source) or inside(source,run) or output!=os.path.join(run,'derived'):
        raise ValueError('Analysis output must be fresh and disjoint from source')
    if os.path.isdir(output) and os.listdir(output):raise ValueError('Preserve existing derived output')
    binding=fast.read(safe_file(run,'inputs/source_binding.json'))
    state,provenance=verify_source(run,source,binding)
    cfg_path=safe_file(run,'inputs/measurement.json');cfg=fast.read(cfg_path)
    external=frozen.verify_external(safe_file(run,'inputs/external_library.json'))
    raw=[p for p in os.listdir(os.path.join(source,'raw')) if p.endswith('.tran.tran')]
    if len(raw)!=1:raise ValueError('Exactly one source native transient required')
    path=safe_file(source,'raw/'+raw[0]);before=os.stat(path)
    if not os.path.isdir(output):os.makedirs(output)
    # Copy original native logs under derived, never synthesize simulation.state
    # or a new raw/logStatus. Their original bytes are retained, not truncated.
    log_proof={}
    for rel,name in [('spectre.out','source_spectre.out'),('raw/logStatus','source_logStatus')]:
        p=safe_file(source,rel)
        if os.path.getsize(p)>1024**2:raise ValueError('Source log exceeds declared1MiB copy allowance')
        shutil.copyfile(p,os.path.join(output,name));log_proof[name]=frozen.identity(p)
    result=coverage.add_coverage(fast.summarize(path,cfg,output),cfg)
    result['storage_observations']=frozen.observe_history(output,cfg)
    for key in ['peak_error_v','peak_time_error_s']:result.pop(key,None)
    result['peak_snapshot_role']='Diagnostic first-SR maximum, not source-fit acceptance'
    result['measurement_sha256']=frozen.identity(cfg_path)['sha256'];result['external_identity']=external
    result['physical_terminal_screen_pass']=not any(v['over_limit_native_points'] for v in result['full_history_voltage_stress'].values())
    native=state['native'];codes=native.get('warning_codes')
    result['native_warning_codes']=codes;result['native_CMI_present']=any(c.startswith('CMI') for c in codes) if codes is not None else None
    result['native_effective_settings']=native.get('effective_settings');result['whole_ADC_qualified']=None
    result['returned_waveform']=frozen.compress_history(output)
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):
        raise ValueError('Source raw metadata changed during analysis')
    if verify_source(run,source,binding)[1]!=provenance:raise ValueError('Source binding/state changed during analysis')
    result.update(analysis_kind='analysis_only_exact_completed_source_reuse',source_run_id=binding['source_run_id'],
        source_recipe_hash=binding['source_recipe_hash'],source_provenance=provenance,
        original_native_logs=log_proof,source_raw_unchanged=True,simulation_started=False,
        fast_reducer_sha256=binding['fast_reducer_sha256'],source_binding_sha256=frozen.identity(os.path.join(run,'inputs/source_binding.json'))['sha256'],
        analysis_peak_rss_bytes=None)
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis exceeds256MiB RSS')
    result['collection_budget_policy']=dict(derived_guard_bytes=cfg['storage']['collection_cap_bytes'],
        user_cap_bytes=cfg['storage']['user_collection_cap_bytes'],final_state_reserve_bytes=cfg['storage']['final_state_reserve_bytes'],
        full_PSF_retained_remote=True,no_time_or_extrema_decimation=True)
    encoded=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    budget=frozen.collection_budget(run,output,cfg,len(encoded))
    fast.write_new(os.path.join(output,'result.json'),result)
    return result,budget


def main():
    ap=argparse.ArgumentParser()
    for key in ['run-dir','output-dir','source-run-dir']:ap.add_argument('--'+key,required=True)
    a=ap.parse_args();r,b=analyze(a.run_dir,a.output_dir,a.source_run_dir)
    print('FAST_STORAGE_SOURCE_ANALYSIS_COMPLETE',r['native_points'],b['projected_bytes'],'simulation_started=False')


if __name__=='__main__':main()
