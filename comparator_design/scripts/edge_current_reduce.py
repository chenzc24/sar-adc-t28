"""Bounded stream export of three native current windows; no waveform decimation."""
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
    required=[norm(n) for n in cfg['signals']];optional=[norm(n) for n in cfg['optional_fields']]
    results=[];handles=[];count=0;names=None
    for w in cfg['windows']:
        results.append(dict(tag=w['tag'],window_points=0,peak_V=-1e3,kcl_max_residual_A=0.,largest_branch_abs_A=0.))
        handles.append(gzip.open(os.path.join(a.output_dir,w['tag']+'.csv.gz'),'wb'))
    for t,v in frames(paths[0]):
        count+=1
        if names is None:
            missing=set(required)-set(v)
            if missing:raise ValueError('missing terminal data '+str(sorted(missing)))
            missing_optional=sorted(set(optional)-set(v));names=required+sorted(set(optional)&set(v))
            for f in handles:f.write(('time,'+','.join(names)+'\n').encode('ascii'))
        for w,r,f in zip(cfg['windows'],results,handles):
            if not w['window_s'][0]<=t<=w['window_s'][1]:continue
            r['window_points']+=1
            value=v[norm(w['target'])]
            if value>r['peak_V']:r.update(peak_V=value,peak_time_s=t)
            b=[v[norm(b['signal'])] for b in w['branches']]
            r['kcl_max_residual_A']=max(r['kcl_max_residual_A'],abs(sum(b)))
            r['largest_branch_abs_A']=max([r['largest_branch_abs_A']]+[abs(i) for i in b])
            f.write((','.join(['%.16g'%t]+['%.16g'%v[n] for n in names])+'\n').encode('ascii'))
    for f in handles:f.close()
    if abs(t-cfg['stop_s'])>1e-14:raise ValueError('truncated transient')
    for r in results:
        if r['window_points']<10:raise ValueError('insufficient window')
        if r['kcl_max_residual_A']>max(1e-10,r['largest_branch_abs_A']*.001):raise ValueError('KCL mismatch')
    result=dict(run_id=cfg['run_id'],source_run_id=cfg['source_run_id'],native_state=state['native'],native_points=count,windows=results,missing_optional_fields=missing_optional,sign_convention='Saved terminal current enters device; negate for current injected into node. Includes conduction and displacement.')
    json.dump(result,open(os.path.join(a.output_dir,'result.json'),'w'),indent=2)
    print(json.dumps(results))
if __name__=='__main__':main()
