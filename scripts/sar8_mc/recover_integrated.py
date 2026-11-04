"""Read completed retained whole-chip anchors, with optional-node limits explicit."""
from __future__ import print_function
import argparse,json,os,sys
import recover_base as base
from block_reduce import random_evidence

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True);a=p.parse_args()
    paths=[]
    for d,dirs,files in os.walk(a.source_run_dir+'/raw'):paths += [d+'/'+n for n in files if n.endswith('.tran.tran')]
    assert len(paths)==1
    old_ls=base.os.listdir;old_samples=base.samples
    def ls(p):return ['SELECTED.tran.tran'] if p==a.source_run_dir+'/raw' else old_ls(p)
    def samples(p):return old_samples(paths[0] if p.endswith('/SELECTED.tran.tran') else p)
    base.os.listdir=ls;base.samples=samples
    sys.argv=[sys.argv[0],'--run-dir',a.run_dir,'--source-run-dir',a.source_run_dir,'--output-dir',a.output_dir]
    try:base.main()
    finally:base.os.listdir=old_ls;base.samples=old_samples
    f=a.output_dir+'/result.json';r=json.load(open(f));r['mismatch_evidence']=random_evidence(a.source_run_dir)
    previous=None;events=[]
    for t,v in old_samples(paths[0]):
        x=v['xdut.cmp_clk'];cm=(v['xdut.topp']+v['xdut.topn'])/2
        if previous:
            pt,px,pcm=previous
            if px<.45<=x or px>.45>=x:
                k=(.45-px)/(x-px);events.append({'time_s':pt+k*(t-pt),'direction':1 if x>px else -1,'top_common_mode_v':pcm+k*(cm-pcm)})
        previous=(t,x,cm)
    r['actual_cmp_clock_events']=events;r['native_data_valid']=r['native_event_code_crosscheck']
    r['nominal_code_deviations']=[{'frame':x['frame'],'expected':x['expected_code'],'actual':x['code_98']} for x in r['frames'] if not x['code_pass']]
    with open(f,'w') as out:json.dump(r,out,indent=2);out.write('\n')
if __name__=='__main__':main()
