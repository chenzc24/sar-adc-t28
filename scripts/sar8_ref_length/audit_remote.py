"""Independent remote exit and source/artifact hash receipts."""
import json
import shlex
from control import ROOT,OUT,VERIFY,REMOTE,read,dump,sha,remote
from prepare import DCNAMES

def main():
    integrated=read(VERIFY/'integrated_setup.json')['names'];names=DCNAMES+integrated
    program='''import os,json,hashlib
root=%r
rows={}
for name in %r:
 p=os.path.join(root,name)
 files=['test.scs','r4_perf_monitor.va','spectre.out']+(['reduced.json.gz','reduce.py'] if name in %r else [])
 hashes={}
 for fn in files:
  h=hashlib.sha256()
  with open(os.path.join(p,fn),'rb') as f:
   while True:
    buf=f.read(1024*1024)
    if not buf:break
    h.update(buf)
  hashes[fn]=h.hexdigest()
 rows[name]=dict(exit=open(os.path.join(p,'exit_code')).read().strip(),hashes=hashes)
print(json.dumps(rows))
'''%(REMOTE,names,integrated)
    data=json.loads(remote('python -c '+shlex.quote(program)))
    for name,row in data.items():
        folder=OUT/name;assert row['exit']=='0'
        for fn,h in row['hashes'].items():
            if fn=='reduce.py':local=ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py'
            elif fn in ['spectre.out','reduced.json.gz']:local=folder/('reduced' if name in integrated else 'native')/fn
            else:local=folder/fn
            assert sha(local)==h,(name,fn)
    dump(VERIFY/'remote_receipts.json',dict(all_match=True,remote=REMOTE,cases=data))
    print('Independent native exits and all remote source/artifact hashes PASS')

if __name__=='__main__':main()
