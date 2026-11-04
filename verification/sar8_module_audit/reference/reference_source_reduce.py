"""Analysis-only native current recovery from a completed source. Python2.7/3.

No Spectre invocation, source write or current-statistic reduction. Only the
fault waveform columns are narrowed; all selected currents remain mandatory.
"""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import sys
sys.dont_write_bytecode=True
import reference_current_analyze as base

MIB=1024*1024


def inside(path,root):
    path,root=os.path.normcase(os.path.realpath(path)),os.path.normcase(os.path.realpath(root))
    return path==root or path.startswith(root+os.sep)


def paths(run,output,source):
    run,output,source=[os.path.realpath(x) for x in [run,output,source]]
    if inside(run,source) or inside(source,run):
        raise ValueError('New analysis and completed source must be disjoint')
    if os.path.normcase(output)!=os.path.normcase(os.path.join(run,'derived')):
        raise ValueError('Expected fresh managed analysis run/derived')
    if not os.path.isdir(run) or not os.path.isdir(source):
        raise ValueError('Analysis/source run missing')
    if os.path.isdir(output) and os.listdir(output):
        raise ValueError('Preserve previous analysis output')
    return run,output,source


def fault_column_adapter(original, cfg, incident):
    """The tested reducer still computes all275 statistics/integrals/snapshots.

    Adapt only the binary writer, scoped to this single-process reduction; no
    frozen module file is changed. Strict original-column checks prevent drift.
    """
    selected,currents,equations=base.validate_config(cfg)
    expected=['time']+[base.norm(n) for n in cfg['diagnostic_voltage_columns']]+currents+['kcl:'+n for n in sorted(equations)]
    wanted=set(['time']+[base.norm(n) for n in cfg['diagnostic_voltage_columns']]+incident+['kcl:'+n for n in sorted(equations)])
    class NarrowFault(original):
        def __init__(self,budget,name,columns):
            self.input_width=len(columns)
            if name=='fault.native.f64le.gz':
                if columns!=expected:
                    raise ValueError('Frozen reducer fault-column interface changed')
                self.indices=[i for i,n in enumerate(columns) if n in wanted]
                if len(self.indices)!=1+len(cfg['diagnostic_voltage_columns'])+len(incident)+len(equations):
                    raise ValueError('Incomplete incident-current fault export')
            else:
                self.indices=list(range(len(columns)))
            original.__init__(self,budget,name,[columns[i] for i in self.indices])

        def row(self,values):
            if len(values)!=self.input_width:
                raise ValueError('Native measurement row width changed')
            original.row(self,[values[i] for i in self.indices])
    return NarrowFault


def verify_source(run,source,manifest):
    if os.path.basename(source)!=manifest['source_run_id']:
        raise ValueError('Unexpected completed source run')
    recipe_path=base.safe_file(source,'recipe.json')
    recipe=base.read_json(recipe_path)
    canonical=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if (canonical!=manifest['source_recipe_hash'] or recipe.get('run_id')!=manifest['source_run_id'] or
            recipe.get('kind','simulation')!='simulation'):
        raise ValueError('Completed source recipe binding mismatch')
    registration=base.read_json(base.safe_file(source,'registered.json'))
    if not registration.get('files_complete') or registration.get('recipe_hash')!=canonical:
        raise ValueError('Completed source registration mismatch')
    provenance=base.read_json(base.safe_file(run,'source_provenance.json'))
    if (provenance.get('run_id')!=manifest['source_run_id'] or provenance.get('recipe_hash')!=canonical or
            os.path.realpath(provenance.get('path',''))!=source):
        raise ValueError('Managed analysis-only source provenance mismatch')
    state_path=base.safe_file(source,'simulation.state.json')
    state=base.read_json(state_path);native=state.get('native',{})
    if (state.get('status')!='complete' or state.get('exit_code')!=0 or
            not native.get('native_analysis_pass') or not native.get('zero_error_footer')):
        raise ValueError('Completed source native simulation required')
    with open(base.safe_file(source,'raw/logStatus')) as f:
        if not re.search(r'\b'+re.escape(manifest['source_analysis_name'])+r'\s+PASS\b',f.read(65536)):
            raise ValueError('Completed source exact transient PASS missing')
    for relative,expected in manifest['source_input_sha256'].items():
        if base.digest(base.safe_file(source,'inputs/'+relative))!=expected:
            raise ValueError('Completed source input hash changed: '+relative)
    return state,dict(run_id=manifest['source_run_id'],recipe_hash=canonical,
        simulation_state_sha256=base.digest(state_path),recipe_file_sha256=base.digest(recipe_path),
        registration_sha256=base.digest(base.safe_file(source,'registered.json')),source_is_read_only=True)


def analyze(run,output,source):
    run,output,source=paths(run,output,source)
    manifest_path=base.safe_file(run,'inputs/source_binding.json')
    manifest=base.read_json(manifest_path)
    cfg_path=base.safe_file(run,'inputs/measurement.json');cfg=base.read_json(cfg_path)
    base.validate_config(cfg)
    if manifest.get('schema_version')!=1 or manifest['max_derived_bytes']!=30*MIB or cfg['max_total_output_bytes']!=30*MIB:
        raise ValueError('Unchanged30MiB derived cap required')
    if base.digest(cfg_path)!=manifest['measurement_sha256']:
        raise ValueError('Frozen source measurement mismatch')
    reducer=base.safe_file(run,'inputs/reference_current_analyze.py')
    if (base.digest(reducer)!=manifest['frozen_reducer_sha256'] or
            os.path.realpath(base.__file__.replace('.pyc','.py'))!=os.path.realpath(reducer)):
        raise ValueError('Unexpected frozen reducer module')
    incident=sorted(set(base.norm(x) for terms in cfg['kcl_terms'].values() for x in terms))
    if incident!=manifest['fault_current_columns']:
        raise ValueError('All five-node incident currents must remain exported')
    state,source_receipt=verify_source(run,source,manifest)
    raw=base.safe_file(source,manifest['source_raw_relative_path']);raw_before=os.stat(raw)
    if not os.path.isdir(output):os.makedirs(output)
    budget=base.Budget(output,30*MIB)
    log=base.preserve_log(source,budget)
    baseline=base.Baseline(os.path.join(run,'inputs'),cfg['source_diagnostic'])
    original=base.NativeGzip
    try:
        base.NativeGzip=fault_column_adapter(original,cfg,incident)
        result=base.summarize(raw,cfg,budget,baseline)
    finally:
        base.NativeGzip=original
    raw_after=os.stat(raw)
    if (raw_before.st_size,raw_before.st_mtime)!=(raw_after.st_size,raw_after.st_mtime):
        raise ValueError('Completed source raw changed during analysis')
    omitted=sorted(set(base.norm(x) for x in cfg['current_saves'])-set(incident))
    result.update(scope=cfg['scope'],analysis_kind='analysis_only_completed_source_reuse',
        source_run=cfg['source_run'],measured_source_run_id=manifest['source_run_id'],
        completed_source=source_receipt,source_binding_sha256=base.digest(manifest_path),
        measurement_sha256=base.digest(cfg_path),frozen_reducer_sha256=manifest['frozen_reducer_sha256'],
        native_warning_codes=state['native'].get('warning_codes'),
        native_effective_settings=state['native'].get('effective_settings'),
        native_simulator_version=state['native'].get('version'),original_simulator_log=log,
        source_raw_relative_path=manifest['source_raw_relative_path'],source_raw_unchanged=True,
        fault_export_policy=dict(exported_current_columns=incident,omitted_waveform_only_current_columns=omitted,
            all_selected_current_statistics_integrals_and_peak_snapshots_preserved=True,
            selected_current_count=len(cfg['current_saves']),
            native_times_unchanged=True,full_KCL_export_unchanged=True,
            source_raw_retained_for_future_targeted_export=True))
    budget.json('native.columns.json',dict(exports=result['native_exports'],
        waveform_column_reduction_only=True,current_statistics_count=len(cfg['current_saves']),
        units='time seconds, voltages V, terminal currents and KCL A; native times retained'))
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*MIB:raise ValueError('Analysis RSS exceeds256MiB')
    else:result['analysis_peak_rss_bytes']=None
    result['derived_bytes_before_result']=budget.bytes
    budget.json('result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser()
    for name in ['run-dir','output-dir','source-run-dir']:
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS)
        limit=240*MIB if hard==resource.RLIM_INFINITY else min(240*MIB,hard)
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    result=analyze(args.run_dir,args.output_dir,args.source_run_dir)
    print('REFERENCE_SOURCE_NATIVE_REDUCE_OK',result['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
