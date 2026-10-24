"""Independent remote receipts and null-control equivalence to frozen sources."""
import gzip
import json
import shlex
import numpy as np
from control import ROOT,OUT,VERIFY,REMOTE,read,dump,sha,remote

def main():
    names=read(VERIFY/'setup.json')['names']
    program='''import os,json,hashlib
root=%r
rows={}
for name in %r:
 p=os.path.join(root,name);files=['test.scs','r4_perf_monitor.va','spectre.out','reduced.json.gz','reduce.py']
 hashes={}
 for fn in files:
  h=hashlib.sha256()
  with open(os.path.join(p,fn),'rb') as f:
   while True:
    b=f.read(1048576)
    if not b:break
    h.update(b)
  hashes[fn]=h.hexdigest()
 rows[name]=dict(exit=open(os.path.join(p,'exit_code')).read().strip(),reduce_exit=open(os.path.join(p,'reduce_exit')).read().strip(),hashes=hashes)
print(json.dumps(rows))
'''%(REMOTE,names)
    rows=json.loads(remote('python -c '+shlex.quote(program)))
    for name,r in rows.items():
        assert r['exit']==r['reduce_exit']=='0'
        for fn,h in r['hashes'].items():
            if fn=='reduce.py':p=ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py'
            else:p=OUT/name/('reduced' if fn in ['spectre.out','reduced.json.gz'] else '')/fn
            assert sha(p)==h,(name,fn)
    dump(VERIFY/'remote_receipts.json',dict(all_match=True,cases=rows,remote=REMOTE))
    nulls=[]
    for tag in ['125','m40']:
        name='null_ff_'+tag;new=read(VERIFY/(name+'_metrics.json'))
        src='l90_ff_099_'+tag+'_static';old=read(ROOT/'verification/sar8_ref_length'/(src+'.json'))
        path=ROOT/'output/sar8_ref_length'/src/'reduced/reduced.json.gz'
        assert sha(path)==read(path.parent.parent/'reduced_receipt.json')['compressed_sha256']
        with gzip.open(path,'rt') as f:r=json.load(f)
        t=np.array(r['wave']['time'])*1e9;y=np.array(r['wave']['xdut.seq_sample']);delta={}
        for up,key in [(True,'sample_rises_ns'),(False,'sample_falls_ns')]:
            ids=np.flatnonzero((y[:-1]<.495)&(y[1:]>=.495) if up else (y[:-1]>.495)&(y[1:]<=.495))
            ts=t[ids]+(.495-y[ids])*(t[ids+1]-t[ids])/(y[ids+1]-y[ids]);assert len(ts)==len(new[key])
            delta[key+'_max_delta_ps']=float(max(abs(np.array(new[key])-ts)))*1000
        assert new['effective_settings']==old['effective_settings']
        nulls.append(dict(name=name,codes_old=[f['code'] for f in old['frames']],codes_null=new['codes'],
          reference_peak_delta_mv=(new['reference_peak']['peak_v']-old['groups']['reference']['peak_v'])*1000,
          held_error_max_delta_mv=max(abs(a-b['held_error_v']*1000) for a,b in zip(new['held_errors_mv'],old['frames'])),
          timing_deltas=delta,effective_settings_match=True))
        del r
    dump(VERIFY/'null_comparison.json',dict(cases=nulls,scope='Instrumented null vs previous native run; small adaptive-timestep differences measured, not assumed zero'))
    print('Independent remote hashes match; null comparison:',nulls)

if __name__=='__main__':main()
