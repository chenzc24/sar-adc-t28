"""Retain every native sample around one identified peak, bound to a completed source."""
from __future__ import print_function
import argparse,json,os,gzip
from native_frames import frames,norm

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True);a=p.parse_args()
    cfg=json.load(open(os.path.join(a.run_dir,'inputs','zoom.json')))
    state=json.load(open(os.path.join(a.source_run_dir,'simulation.state.json')))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('source not complete')
    paths=[os.path.join(a.source_run_dir,'raw',s) for s in os.listdir(os.path.join(a.source_run_dir,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('ambiguous source')
    names=[norm(n) for n in cfg['signals']];count=0;peak=0.
    with gzip.open(os.path.join(a.output_dir,'wave.csv.gz'),'wb') as f:
        f.write(('time,'+','.join(names)+'\n').encode('ascii'))
        for t,v in frames(paths[0]):
            if t<cfg['start_s']:continue
            if t>cfg['end_s']:break
            v['0']=0.
            if set(names)-set(v):raise ValueError('missing node')
            count+=1;peak=max(peak,abs(v[norm(cfg['pair_nodes'][0])]-v[norm(cfg['pair_nodes'][1])]))
            f.write((','.join(['%.16g'%t]+['%.16g'%v[n] for n in names])+'\n').encode('ascii'))
    if count<3 or abs(peak-cfg['expected_peak_V'])>1e-9:raise ValueError('zoom peak does not match native full scan')
    json.dump({'source_run_id':cfg['source_run_id'],'native_points':count,'peak_V':peak,'peak_verified':True,'decimation':False},open(os.path.join(a.output_dir,'result.json'),'w'),indent=2)
    print('Native zoom verified',count,peak)

if __name__=='__main__':main()
