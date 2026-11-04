"""MC recovery using proven optional-signal handling and exact source binding."""
from __future__ import print_function
import argparse,json,os,re,sys
import recover_base as base
from reduce_v2 import evidence

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True);a=p.parse_args()
    ctx=json.load(open(a.source_run_dir+'/inputs/context.json'));raw=[]
    for d,dirs,files in os.walk(a.source_run_dir+'/raw'):
        for n in files:
            if n.endswith('.tran.tran'):raw.append(d+'/'+n)
    assert len(raw)==1
    oldlist=base.os.listdir;oldsample=base.samples
    def files(p):return ['MC_SELECTED.tran.tran'] if p==a.source_run_dir+'/raw' else oldlist(p)
    def samples(p):return oldsample(raw[0] if p.endswith('/MC_SELECTED.tran.tran') else p)
    base.os.listdir=files;base.samples=samples
    sys.argv=[sys.argv[0],'--run-dir',a.run_dir,'--source-run-dir',a.source_run_dir,'--output-dir',a.output_dir]
    try:base.main()
    finally:base.os.listdir=oldlist;base.samples=oldsample
    f=a.output_dir+'/result.json';r=json.load(open(f));e=evidence(a.source_run_dir)
    if ctx['seed'] is not None:assert e['mom_count']==18 and e['mos_count']>=2
    r.update(mismatch_evidence=e,native_data_valid=r['native_event_code_crosscheck'],
        protocol_pass=r['startup_timing_pass'] and r['steady_timing_pass'],
        nominal_center_code_deviations=[{'frame':v['frame'],'reference':v['expected_code'],'actual':v['code_98'],'delta':v['code_98']-v['expected_code']} for v in r['frames'] if not v['code_pass']],
        native_transient_path=os.path.relpath(raw[0],a.source_run_dir),
        statistical_scope='One fixed random circuit, ten key inputs; not full static/yield/FFT; optional unavailable charge measurements remain unknown')
    with open(f,'w') as out:json.dump(r,out,indent=2);out.write('\n')
    print('MC_RECOVERY_COMPLETE',ctx['seed'],r['protocol_pass'],len(r['nominal_center_code_deviations']))
if __name__=='__main__':main()
