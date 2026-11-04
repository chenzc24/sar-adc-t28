"""Analysis-only, all-native metrics plus a bounded native-row figure export."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import struct
import sys
import zlib
sys.dont_write_bytecode=True
import feedback_analyze as base

MIB=1024*1024
s=base.s


def inside(path,root):
    path,root=[os.path.normcase(os.path.realpath(p)) for p in [path,root]]
    return path==root or path.startswith(root+os.sep)


def safe(root,relative):
    p=os.path.realpath(os.path.join(root,relative))
    if not inside(p,root) or p==os.path.realpath(root) or not os.path.isfile(p):raise ValueError('Missing/unsafe source file: '+relative)
    return p


def verify_source(run,source,binding):
    if os.path.basename(source)!=binding['source_run_id']:raise ValueError('Wrong completed source')
    recipe=s.read(safe(source,'recipe.json'))
    canonical=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if canonical!=binding['source_recipe_hash'] or recipe.get('run_id')!=binding['source_run_id'] or recipe.get('kind','simulation')!='simulation':raise ValueError('Source recipe binding differs')
    registered=s.read(safe(source,'registered.json'))
    if not registered.get('files_complete') or registered.get('recipe_hash')!=canonical:raise ValueError('Source registration differs')
    p=s.read(safe(run,'source_provenance.json'))
    if p.get('run_id')!=binding['source_run_id'] or p.get('recipe_hash')!=canonical or os.path.realpath(p.get('path',''))!=source:raise ValueError('Managed source provenance differs')
    for n,h in binding['source_input_sha256'].items():
        if s.digest(safe(source,'inputs/'+n))!=h:raise ValueError('Completed source input differs: '+n)
    state=s.read(safe(source,'simulation.state.json'));native=state.get('native',{})
    if state.get('status')!='complete' or state.get('exit_code')!=0 or not native.get('native_analysis_pass') or not native.get('zero_error_footer'):raise ValueError('Source native success required')
    if s.digest(safe(source,'simulation.state.json'))!=binding['simulation_state_sha256']:raise ValueError('Source simulation state changed')
    with open(safe(source,'raw/logStatus')) as f:
        if not re.search(r'\btran_feedback\s+PASS\b',f.read(65536)):raise ValueError('Source transient PASS missing')
    log=safe(source,'spectre.out')
    if os.path.getsize(log)>2*MIB or s.digest(log)!=binding['native_log_sha256']:raise ValueError('Source log binding differs')
    with open(log,'rb') as f:text=f.read().decode('ascii')
    if 'allpub' in text or not re.search(r'save\s+124\s+\(voltage\)',text) or not re.search(r'save\s+23\s+\(current\)',text):raise ValueError('Native saves differ')
    steps=re.search(r'Number of accepted tran steps\s*=\s*(\d+)',text)
    if not steps or int(steps.group(1))+1!=binding['native_points']:raise ValueError('Source accepted-step count differs')
    return state,log


class EmptyEncoder(object):
    def compress(self,blob):return b''
    def flush(self):return b''


class MetricsOnlyZlib(object):
    DEFLATED=zlib.DEFLATED
    def compressobj(self,*args):return EmptyEncoder()


class MetricsOutput(object):
    def __init__(self,out):self.path=out.path;self.out=out
    def emit(self,handle,blob):
        if blob:raise ValueError('Metrics pass must not serialize waveforms')
    def json(self,name,value):
        if name!='wave.columns.json':raise ValueError('Unexpected first-pass output')


def witnesses(result,cap):
    times={0.,result['last_native_time_s']}
    for e in result['events']:
        times.update([e['before_native_s'],e['after_native_s']])
    for x in result['extrema'].values():times.update([x['min_time_s'],x['max_time_s']])
    for x in result['node_kcl'].values():times.add(x['time_s'])
    for x in result['mos_pair_extrema'].values():times.add(x['time_s'])
    for c in result['cycles']:
        for n in ['pre_compare','after_write_observation','first_reset_ready_native']:
            x=c.get(n)
            if x is not None:times.add(x['time_s'])
        times.update(x['time_s'] for x in c['reset_ready_transitions'])
    if len(times)>cap:raise ValueError('Native witness export budget exceeded; no silent omission')
    return times


def export_native(raw,cfg,result,out,policy):
    needed=witnesses(result,policy['max_witness_times']);found=set()
    count=result['native_points'];stride=max(1,(count+policy['baseline_row_budget']-1)//policy['baseline_row_budget'])
    wave=cfg['wave_voltage_columns']+cfg['wave_current_columns'];nodes=sorted(cfg['kcl_terms'])
    cols=['time']+wave+['kcl:'+n for n in nodes]
    if len(cols)!=60:raise ValueError('History60-column interface differs')
    selected=list(set(wave+list(s.norm(n) for n in cfg['current_saves'])))
    psf=s.PSF(raw,selected);pack=struct.Struct('<'+'d'*len(cols));encoder=zlib.compressobj(6,zlib.DEFLATED,31)
    compressed_sha=hashlib.sha256();plain_sha=hashlib.sha256();rows=0;size=0;first,last=None,None
    filename='wave.export.f64le.gz'
    def write(handle,blob):
        if size+len(blob)>policy['max_wave_bytes']:raise ValueError('Bounded wave export cap exceeded')
        out.emit(handle,blob);compressed_sha.update(blob)
        return len(blob)
    with open(os.path.join(out.path,filename),'wb') as f:
        for t,v in psf.rows():
            index=psf.points-1
            witness=t in needed
            if witness:found.add(t)
            if index%stride and not witness:continue
            if rows>=policy['max_export_rows']:raise ValueError('Native export row cap exceeded')
            kcl=[sum(v[n] for n in cfg['kcl_terms'][node]) for node in nodes]
            blob=pack.pack(*([t]+[v[n] for n in wave]+kcl));plain_sha.update(blob)
            size+=write(f,encoder.compress(blob));rows+=1
            if first is None:first=t
            last=t
        size+=write(f,encoder.flush())
    if psf.sha.hexdigest()!=result['raw_sha256'] or psf.points!=count or psf.last!=result['last_native_time_s']:raise ValueError('Two native passes differ')
    if found!=needed:raise ValueError('A metric/event native witness was not exported')
    descriptor=dict(file=filename,rows=rows,columns=cols,compressed_bytes=size,sha256=compressed_sha.hexdigest(),uncompressed_sha256=plain_sha.hexdigest(),
        export_kind='Subset of original native rows; no interpolation',native_metric_rows=count,
        range_s=[first,last],baseline_native_index_stride=stride,baseline_row_budget=policy['baseline_row_budget'],
        witness_time_count=len(needed),all_requested_witnesses_exported=True,
        mandatory_native_rows='All accepted event brackets, exported-channel extrema,990 selected MOS-pair peak times, KCL extrema, precompare/after-write/reset-recovery witnesses',
        figure_label='Full0--100ns; every%d-th native point plus event/extrema/recovery witness rows. All numerical metrics use every native point.'%stride,
        max_export_rows=policy['max_export_rows'],max_wave_bytes=policy['max_wave_bytes'])
    out.json('wave.columns.json',dict(columns=cols,representation=descriptor['export_kind'],export_policy=descriptor))
    return descriptor


def analyze(run,output,source):
    run,output,source=[os.path.realpath(p) for p in [run,output,source]]
    if inside(run,source) or inside(source,run):raise ValueError('Analysis run and completed source must be disjoint')
    if os.path.normcase(output)!=os.path.normcase(os.path.join(run,'derived')):raise ValueError('Expected fresh managed analysis/derived')
    binding=s.read(safe(run,'inputs/source_binding.json'));cfg=s.read(safe(run,'inputs/measurement.json'))
    if s.digest(safe(run,'inputs/measurement.json'))!=binding['measurement_sha256']:raise ValueError('Frozen measurement differs')
    for n in ['feedback_analyze.py','native_support.py']:
        if s.digest(safe(run,'inputs/'+n))!=binding['frozen_module_sha256'][n]:raise ValueError('Frozen reducer/support differs')
    if os.path.realpath(base.__file__.replace('.pyc','.py'))!=safe(run,'inputs/feedback_analyze.py'):raise ValueError('Reducer must be this analysis run frozen input')
    if cfg['max_output_bytes']!=29*MIB or binding['max_derived_bytes']!=29*MIB:raise ValueError('Unchanged29MiB derived cap required')
    state,log=verify_source(run,source,binding)
    raw=safe(source,binding['source_raw_relative_path']);before=os.stat(raw)
    out=s.Output(output,29*MIB)
    with open(log,'rb') as a,open(os.path.join(output,'spectre.original.log'),'wb') as b:out.emit(b,a.read())
    original=base.zlib
    try:
        base.zlib=MetricsOnlyZlib()
        result=base.reduce(raw,cfg,MetricsOutput(out))
    finally:base.zlib=original
    # The frozen writer's empty placeholder exists only in this fresh derived.
    placeholder=os.path.join(output,'wave.native.f64le.gz')
    if os.path.getsize(placeholder)!=0:raise ValueError('Unexpected first-pass waveform')
    os.remove(placeholder)
    if result['native_points']!=binding['native_points']:raise ValueError('Complete source row count differs')
    native_serial_hash=result['waveform']['uncompressed_sha256']
    result['waveform']=export_native(raw,cfg,result,out,binding['export_policy'])
    after=os.stat(raw)
    if (before.st_size,before.st_mtime)!=(after.st_size,after.st_mtime):raise ValueError('Source raw changed during analysis')
    result.update(analysis_kind='analysis_only_completed_source_reuse',measured_source_run_id=binding['source_run_id'],
        completed_source_recipe_hash=binding['source_recipe_hash'],source_binding_sha256=s.digest(safe(run,'inputs/source_binding.json')),
        measurement_sha256=binding['measurement_sha256'],frozen_module_sha256=binding['frozen_module_sha256'],
        source_raw_relative_path=binding['source_raw_relative_path'],source_raw_unchanged=True,two_full_native_passes_match=True,
        full_native_metric_serialized_sha256=native_serial_hash,all_native_metrics_unchanged=True,
        native_warning_codes=state['native'].get('warning_codes'),native_effective_settings=state['native'].get('effective_settings'),
        simulator_version=state['native'].get('version'),original_simulator_log_sha256=s.digest(log),
        collection_budget=dict(derived_cap_bytes=29*MIB,total_cap_bytes=32*MIB,wave_cap_bytes=binding['export_policy']['max_wave_bytes']))
    result['measurement_methods']['waveform']='Display export is sampled native rows plus all listed witnesses; metrics/990 stress screens remain every native point'
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*MIB:raise ValueError('Analysis RSS exceeds256MiB')
    result['derived_bytes_before_result']=out.bytes;out.json('result.json',result)
    return result


def main():
    p=argparse.ArgumentParser()
    for n in ['run-dir','output-dir','source-run-dir']:p.add_argument('--'+n,required=True)
    a=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*MIB if hard==resource.RLIM_INFINITY else min(240*MIB,hard)
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir,a.source_run_dir)
    print('COMPARATOR_SOURCE_NATIVE_REDUCE_OK',r['native_points'],'export',r['waveform']['rows'],'protocol_eight_pass',r['protocol_eight_pass'])


if __name__=='__main__':main()
