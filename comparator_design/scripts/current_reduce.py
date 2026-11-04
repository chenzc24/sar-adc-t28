"""Stream native terminal-current data; positive terminal current enters the device."""
from __future__ import print_function
import argparse,json,os,gzip
from native_frames import frames,norm

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    cfg=json.load(open(os.path.join(a.run_dir,'inputs','measure.json')))
    state=json.load(open(os.path.join(a.run_dir,'simulation.state.json')))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native simulation incomplete')
    paths=[os.path.join(a.run_dir,'raw',s) for s in os.listdir(os.path.join(a.run_dir,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('ambiguous waveform')
    target=norm(cfg['target']);required=[norm(n) for n in cfg['signals']];optional=[norm(n) for n in cfg['optional_fields']]
    rows=[];count=0;names=None;missing_optional=[]
    for t,v in frames(paths[0]):
        count+=1
        if names is None:
            missing=set(required)-set(v)
            if missing:raise ValueError('missing terminal data '+str(sorted(missing)))
            missing_optional=sorted(set(optional)-set(v));names=required+sorted(set(optional)&set(v))
        if cfg['window_s'][0]<=t<=cfg['window_s'][1]:rows.append(dict(time=t,**{n:v[n] for n in names}))
    if abs(t-cfg['stop_s'])>1e-14:raise ValueError('truncated transient')
    if len(rows)<10:raise ValueError('insufficient window points')
    peak=max(rows,key=lambda r:r[target]);branches=[norm(b['signal']) for b in cfg['branches']]
    # All currents at a floating internal node must sum to numerical residual.
    kcl=max(abs(sum(r[b] for b in branches)) for r in rows)
    branch_peak=max(abs(r[b]) for r in rows for b in branches)
    if kcl>max(1e-9,branch_peak*.001):raise ValueError('node current KCL mismatch '+str(kcl))
    with gzip.open(os.path.join(a.output_dir,'wave.csv.gz'),'wb') as f:
        f.write(('time,'+','.join(names)+'\n').encode('ascii'))
        for r in rows:f.write((','.join(['%.16g'%r[n] for n in ['time']+names])+'\n').encode('ascii'))
    result={'run_id':cfg['run_id'],'source_run_id':cfg['source_run_id'],'native_state':state['native'],'native_points':count,'window_points':len(rows),
            'peak_V':peak[target],'peak_time_s':peak['time'],'peak_difference_from_source_V':peak[target]-cfg['source_peak_V'],
            'kcl_max_residual_A':kcl,'largest_branch_abs_A':branch_peak,'missing_optional_fields':missing_optional,
            'branches':cfg['branches'],'sign_convention':'Positive saved current enters device; negative injects node. Terminal current includes displacement and conduction.',
            'op_fields_scope':'Named raw TMI operating quantities, not assumed intrinsic or multiplicity-normalized without validation.'}
    json.dump(result,open(os.path.join(a.output_dir,'result.json'),'w'),indent=2)
    print('Current window reduced',len(rows),'KCL',kcl,'peak',peak[target])

if __name__=='__main__':main()
