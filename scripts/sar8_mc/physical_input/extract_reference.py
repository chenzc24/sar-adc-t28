"""Read-only, source-bound compact B clock waveform export; Python2.7/3."""
from __future__ import print_function
import argparse,hashlib,json,os
from native_stream import samples

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--source-run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    paths=[]
    for d,dirs,files in os.walk(a.source_run_dir+'/raw'):
        paths += [d+'/'+n for n in files if n.endswith('.tran.tran')]
    assert len(paths)==1
    names=['sample','xdut.seq_sample','xdut.cmp_clk']
    traces={n:[] for n in names};previous=None;points=0;events={n:[] for n in names}
    end=159e-9;last=None
    for t,v in samples(paths[0]):
        points+=1
        if previous is not None:
            pt,pv=previous
            for n in names:
                if pv[n]<.45<=v[n] or pv[n]>.45>=v[n]:
                    k=(.45-pv[n])/(v[n]-pv[n]);events[n].append([pt+k*(t-pt),1 if v[n]>pv[n] else -1])
        if t<=end:
            for n in names:
                q=traces[n]
                if not q or abs(v[n]-q[-1][1])>=.001:
                    if previous and (not q or previous[0]>q[-1][0]):q.append([previous[0],previous[1][n]])
                    if not q or t>q[-1][0]:q.append([t,v[n]])
            last=(t,dict(v))
        previous=(t,dict(v))
    assert t>=1059e-9-1e-14 and last
    for n in names:
        if traces[n][-1][0]<last[0]:traces[n].append([last[0],last[1][n]])
    cmp=events['xdut.cmp_clk'];assert len(cmp)==160
    r={'analysis_complete':True,'native_data_valid':True,'source_run_dir':a.source_run_dir,'native_points':points,'source_raw':os.path.relpath(paths[0],a.source_run_dir),
       'traces':traces,'events':events,'trace_voltage_filter_v':.001,'initial_interval_s':[0,last[0]],'repeat_template_s':[59e-9,159e-9],
       'scope':'First original B phase60 frame clock waveforms; repeat first-frame comparator burst with static bottom word, not asynchronous feedback reconstruction'}
    with open(a.output_dir+'/result.json','w') as f:json.dump(r,f,indent=2);f.write('\n')
    print('B_CLOCK_EXPORT',points,{n:len(traces[n]) for n in names})
if __name__=='__main__':main()
