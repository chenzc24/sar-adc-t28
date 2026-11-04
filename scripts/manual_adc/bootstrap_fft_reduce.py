"""Python2.7 streaming log + strobe verification; no full waveform recovery."""
from __future__ import print_function
import argparse,json,os,re
from reduce import frames

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir');a=p.parse_args()
    if a.source_run_dir:a.run_dir=a.source_run_dir
    cfg=json.load(open(a.run_dir+'/inputs/measure.json'))
    state=json.load(open(a.run_dir+'/simulation.state.json'))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native incomplete')
    rows={0:[],1:[]};logs=[a.run_dir+'/spectre.out']
    # Native file is unwrapped; console copy can wrap records at80 columns.
    with open(logs[0]) as f:
        for line in f:
            if 'BOOTFFT ' not in line:continue
            z=line[line.index('BOOTFFT '):].split();tag=int(z[1]);idx=int(z[2])
            if len(z)!=10:raise ValueError('malformed observer record '+line)
            rows[tag].append(dict(frame=idx,time_s=float(z[3]),code=int(z[4]),comparisons=int(z[5]),completed=int(z[6]),faults=int(z[7]),held_diff_V=float(z[8]),close_s=float(z[9])))
    for tag in [0,1]:
        if len(rows[tag])!=cfg['frames'] or [x['frame'] for x in rows[tag]]!=list(range(cfg['frames'])):raise ValueError('missing/duplicate frames')
    raw=[a.run_dir+'/raw/'+x for x in os.listdir(a.run_dir+'/raw') if x.endswith('.tran.tran')]
    if len(raw)!=1:raise ValueError('raw count')
    verified=[0,0];bad=[];points=0;faultmax=0.;snippets=[]
    for t,v in frames(raw[0]):
        points+=1;faultmax=max(faultmax,v['fault'],v['ifault'])
        idx=int(round((t-211e-9)/1e-7))
        if 0<=idx<cfg['frames'] and abs(t-(211e-9+idx*1e-7))<1e-14:
            for tag,pref in [(0,'do_'),(1,'ido_')]:
                code=sum(1<<i for i in range(8) if v[pref+str(i)]>cfg['vdd_V']/2)
                verified[tag]+=1
                if code!=rows[tag][idx]['code']:bad.append([tag,idx,code,rows[tag][idx]['code']])
        if t>cfg['stop_s']-300e-9:snippets.append([t,v['vinp']-v['vinn'],v['xadc.topp']-v['xadc.topn']])
    if verified!=[cfg['frames']]*2 or bad or abs(t-cfg['stop_s'])>1e-14:raise ValueError('strobe/observer mismatch '+str([verified,bad,t]))
    timing=all(x['comparisons']==8 and x['completed']==1 and x['faults']==0 and abs(x['close_s']-(149.975e-9+x['frame']*1e-7))<2e-12 for rr in rows.values() for x in rr)
    result=dict(config=cfg,rows=rows,checks=dict(frame_timing=timing,strobe_code_agreement=True,no_fault=faultmax<cfg['vdd_V']/2,
                 zero_native_CMI=not any('CMI-' in x for x in state['native'].get('warning_codes',[]))),native_state=state['native'],
                 native_strobe_points=points,verified_code_count=verified,observer_log=os.path.relpath(logs[0],a.run_dir),last_wave=snippets,
                 limitation='1ns saved strobes are not full peak/terminal stress measurements; retain native CMI warnings')
    json.dump(result,open(a.output_dir+'/result.json','w'),indent=2,sort_keys=True)
    print('BOOTFFT frames',cfg['frames'],'checks',result['checks'])

if __name__=='__main__':main()
