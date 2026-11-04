"""Native B clock/common-mode boundary evidence; source-bound streaming analysis."""
from __future__ import print_function
import argparse,json,os
from native_stream import samples
def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--source-run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args();paths=[]
    for d,dirs,files in os.walk(a.source_run_dir+'/raw'):paths += [d+'/'+n for n in files if n.endswith('.tran.tran')]
    assert len(paths)==1;prev=None;events=[];points=0
    for t,v in samples(paths[0]):
        points+=1;x=v['xdut.cmp_clk'];cm=(v['xdut.topp']+v['xdut.topn'])/2
        if prev:
            pt,px,pcm=prev
            if px<.45<=x or px>.45>=x:
                k=(.45-px)/(x-px);events.append({'time_s':pt+k*(t-pt),'direction':1 if x>px else -1,'top_common_mode_v':pcm+k*(cm-pcm)})
        prev=(t,x,cm)
    assert t>=1059e-9-1e-14
    rises=[x for x in events if x['direction']==1];falls=[x for x in events if x['direction']==-1];assert len(rises)==len(falls)==80
    widths=[(fall['time_s']-rise['time_s'])*1e9 for rise,fall in zip(rises,falls)];cms=[x['top_common_mode_v'] for x in rises]
    r={'analysis_complete':True,'native_data_valid':True,'source_run_dir':a.source_run_dir,'native_points':points,'events':events,'native_cmp_high_ns_range':[min(widths),max(widths)],'top_cm_at_evaluation_v_range':[min(cms),max(cms)],'scope':'Actual retained B ten key-code frames; not all input/PVT common-mode envelope'}
    with open(a.output_dir+'/result.json','w') as f:json.dump(r,f,indent=2);f.write('\n')
if __name__=='__main__':main()
