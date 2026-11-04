"""Small source-only MM64 joint export. Python2.7/3; no simulator."""
from __future__ import print_function
import argparse
import csv
import json
import os
import struct
import sys
sys.dont_write_bytecode=True

import fast_gate_analyze as native
import fast_source_analyze as bound
import standard_cell_full_analyze as tools


def over_segments(t0,t1,a,b,limit):
    """Piecewise-linear estimate between original samples; not an SOA waiver."""
    cuts=[0.,1.]
    if a!=b:cuts += [(v-a)/(b-a) for v in [-limit,limit] if 0<(v-a)/(b-a)<1]
    cuts.sort();out=[]
    for left,right in zip(cuts,cuts[1:]):
        if abs(a+(b-a)*.5*(left+right))>limit:
            out.append((t0+(t1-t0)*left,t0+(t1-t0)*right))
    return out


def export(output,cfg,reference,result):
    columns=native.read(os.path.join(output,'peak.columns.json'))['names']
    index=dict((n,i) for i,n in enumerate(columns));roles=cfg['joint']['roles']
    def v(row,node):return 0. if node=='0' else row[index[native.norm(node)]]
    specs=cfg['stress_voltage_pairs'];phases=cfg['joint']['windows_s']
    pairs=sorted(specs);names=['time']+list(roles)+pairs
    duration=dict((k,dict(linear_duration_estimate_s=0.,native_over_limit_points=0,
                         first_over_native_s=None,last_over_native_s=None,linear_intervals=[])) for k in pairs)
    witnesses={};previous=None;previous_pairs=None;rows=0;exported=0;exact_reference_row=None
    pack=struct.Struct('<'+'d'*len(columns))
    path=os.path.join(output,'joint_native.csv')
    handle=open(path,'wb') if sys.version_info[0]<3 else open(path,'w',newline='')
    try:
        writer=csv.writer(handle);writer.writerow(names)
        with open(os.path.join(output,'peak.native.bin'),'rb') as source:
            while True:
                blob=source.read(pack.size)
                if not blob:break
                if len(blob)!=pack.size:raise ValueError('Incomplete joint native row')
                row=pack.unpack(blob);t=row[0];rows+=1
                state=dict((k,v(row,node)) for k,node in roles.items())
                values=dict((k,v(row,p['positive_node'])-v(row,p['negative_node'])) for k,p in specs.items())
                if t==reference['MM64_VDS_peak_time_s']:exact_reference_row=dict(time_s=t,nodes_v=state,pairs_v=values)
                for key,value in values.items():
                    item=duration[key];limit=specs[key]['limit_abs_v']
                    if key not in witnesses or abs(value)>witnesses[key]['max_abs_v']:
                        witnesses[key]=dict(time_s=t,signed_pair_v=value,max_abs_v=abs(value),nodes_v=dict(state))
                    if abs(value)>limit:
                        item['native_over_limit_points']+=1;item['last_over_native_s']=t
                        if item['first_over_native_s'] is None:item['first_over_native_s']=t
                    if previous is not None:
                        for start,stop in over_segments(previous[0],t,previous_pairs[key],value,limit):
                            item['linear_duration_estimate_s']+=stop-start
                            intervals=item['linear_intervals']
                            if intervals and abs(start-intervals[-1]['stop_s'])<1e-22:
                                intervals[-1]['stop_s']=stop;intervals[-1]['stop_native_bracket_s']=[previous[0],t]
                            else:intervals.append(dict(start_s=start,stop_s=stop,start_native_bracket_s=[previous[0],t],stop_native_bracket_s=[previous[0],t]))
                if any(a<=t<=b for a,b in phases):
                    writer.writerow(['%.17g'%x for x in [t]+[state[k] for k in roles]+[values[k] for k in pairs]]);exported+=1
                previous=row;previous_pairs=values
    finally:handle.close()
    if rows!=reference['native_points'] or exact_reference_row is None:raise ValueError('Exact native point/peak witness missing')
    for key,expected in reference['pair_statistics'].items():
        if result['full_history_voltage_stress'][key]!=expected:raise ValueError('Original full-history joint statistic differs: '+key)
    return dict(full_history_native_points=rows,exported_window_native_points=exported,CSV_columns=names,
        window_policy='Only original points in declared windows exported; all0..20ns points measured for joint extrema and durations. No waveform interpolation or phase alignment.',
        duration_policy='Threshold-crossing duration is piecewise-linear between original endpoint pairs; brackets retained. This is not exact continuous-time lifetime/SOA qualification.',
        all_pair_statistics_match_original_full_run_exactly=True,
        full_history_joint_peak_states=witnesses,full_history_durations=duration,
        exact_original_MM64_VDS_peak=exact_reference_row)


def analyze(run,output,source):
    run,output,source=[os.path.realpath(p) for p in [run,output,source]]
    if bound.inside(run,source) or bound.inside(source,run) or output!=os.path.join(run,'derived'):
        raise ValueError('Fresh disjoint managed output required')
    if os.path.isdir(output) and os.listdir(output):raise ValueError('Preserve previous derived output')
    binding=native.read(bound.safe_file(run,'inputs/source_binding.json'))
    _,proof=bound.verify_source(run,source,binding)
    cfg=native.read(bound.safe_file(run,'inputs/joint_measurement.json'))
    reference=native.read(bound.safe_file(run,'inputs/case_reference.json'))
    for key,rel in [('source_spectre.out','spectre.out'),('source_logStatus','raw/logStatus')]:
        if tools.identity(bound.safe_file(source,rel))!=reference['native_log_identities'][key]:
            raise ValueError('Original source log identity changed')
    raw=[f for f in os.listdir(os.path.join(source,'raw')) if f.endswith('.tran.tran')]
    if len(raw)!=1:raise ValueError('One complete native source required')
    path=bound.safe_file(source,'raw/'+raw[0]);before=os.stat(path)
    if before.st_size!=reference['raw_bytes']:raise ValueError('Wrong original raw size')
    if not os.path.isdir(output):os.makedirs(output)
    result=native.summarize(path,cfg,output)
    if result['raw_sha256']!=reference['raw_sha256']:raise ValueError('Raw SHA differs from completed FFfast source')
    joint=export(output,cfg,reference,result)
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):
        raise ValueError('Source raw changed')
    if bound.verify_source(run,source,binding)[1]!=proof:raise ValueError('Source proof changed')
    # Remove only temporary files created in this fresh analysis directory.
    for name in ['peak.native.bin','peak.columns.json']:os.remove(os.path.join(output,name))
    final=dict(analysis_complete=True,analysis_kind='analysis_only_targeted_joint_voltage_export',simulation_started=False,
        source_run_id=binding['source_run_id'],source_recipe_hash=binding['source_recipe_hash'],source_provenance=proof,
        source_raw_unchanged=True,raw_sha256=result['raw_sha256'],raw_bytes=result['raw_bytes'],native_PSF_END=True,
        source_reference_sha256=tools.identity(os.path.join(run,'inputs/case_reference.json'))['sha256'],
        voltage_roles=cfg['joint']['roles'],full_history_voltage_and_pair_extrema=result['full_history_voltage_stress'],
        full_history_node_extrema=result['voltage_and_current_extrema'],joint=joint,
        csv_identity=tools.identity(os.path.join(output,'joint_native.csv')),
        current_policy='No currents extracted here; MM64 intrinsic currents were not saved in source v2 and remain unknown.',
        source_native_logs_reference=reference['native_log_identities'],
        B_ground_policy='MM64 B is the explicit0 node, emitted as exact ground constant, not an estimated measurement.',
        full_ADC_qualified=None,analysis_peak_rss_bytes=None)
    if sys.platform.startswith('linux'):
        import resource
        final['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if final['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis exceeds256MiB RSS')
    encoded=(json.dumps(final,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    budget=tools.collection_budget(run,output,cfg,len(encoded))
    # The managed framework completion contract requires derived/result.json.
    native.write_new(os.path.join(output,'result.json'),final)
    return final,budget


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for key in ['run-dir','output-dir','source-run-dir']:ap.add_argument('--'+key,required=True)
    args=ap.parse_args();r,b=analyze(args.run_dir,args.output_dir,args.source_run_dir)
    print('MM64_JOINT_NATIVE_EXPORT_COMPLETE',r['joint']['full_history_native_points'],b['projected_bytes'],'simulation_started=False')
