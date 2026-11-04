from __future__ import print_function
import argparse,json,os,gzip
from native_frames import frames,norm

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    cfg=json.load(open(os.path.join(a.run_dir,'inputs','measure.json')))
    state=json.load(open(os.path.join(a.run_dir,'simulation.state.json')))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native incomplete')
    paths=[os.path.join(a.run_dir,'raw',f) for f in os.listdir(os.path.join(a.run_dir,'raw')) if f.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('transient source ambiguous')
    prev=None;charge=[0.]*len(cfg['windows']);names=[norm(n) for n in cfg['signals']]
    f=gzip.open(os.path.join(a.output_dir,'wave.csv.gz'),'wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'))
    for t,v in frames(paths[0]):
        f.write((','.join(['%.12g'%t]+['%.12g'%v[k] for k in names])+'\n').encode('ascii'))
        if prev:
            for i,w in enumerate(cfg['windows']):
                lo=max(prev[0],w['start_s']);hi=min(t,w['end_s'])
                if hi>lo:
                    key=norm(w['source']);dt=t-prev[0];ia=prev[1][key];ib=v[key]
                    a0=ia+(ib-ia)*(lo-prev[0])/dt;b0=ia+(ib-ia)*(hi-prev[0])/dt
                    charge[i]-=(a0+b0)*(hi-lo)/2
        prev=(t,v)
    f.close()
    if abs(t-cfg['stop_s'])>1e-14:raise ValueError('wrong stop')
    rows=[dict(label=w['label'],charge_C=q,effective_C_F=q/w['dv']) for w,q in zip(cfg['windows'],charge)]
    result={'native_complete':True,'rows':rows,'max_effective_C_F':max(r['effective_C_F'] for r in rows),
            'scope':'8 native DFQD1 D inputs + one OR2D4 input per rail; clock low; total dynamic charge incl state-dependent coupling/leakage; not a constant library pin capacitance',
            'native_state':state.get('native')}
    json.dump(result,open(os.path.join(a.output_dir,'result.json'),'w'),indent=2)
    print('Receiver charge measured')

if __name__=='__main__':main()
