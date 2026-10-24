"""Remote Python2/3 orchestrator: one case, exclusive lock, capped address space."""
from __future__ import print_function
import os,sys,json,subprocess,resource,fcntl,hashlib,gzip,shutil,time

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(1024*1024)
   if not b:break
   h.update(b)
 return h.hexdigest()

def main():
 tools=os.path.dirname(os.path.abspath(__file__))
 cases=json.load(open(tools+'/cases.json'))
 name=sys.argv[1];assert name in cases
 root=os.path.dirname(tools);case=root+'/'+name
 lock=open(tools+'/worker.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(10)
 assert open(case+'/exit_code').read().strip()=='0'
 assert 'PASS' in open(case+'/test.raw/logStatus').read()
 assert 'spectre completes with 0 errors' in open(case+'/spectre.out').read()
 assert sha(case+'/test.scs')==cases[name]['deck_sha256']
 raw=case+'/test.raw/tran_perf.tran.tran';st=os.stat(raw)
 assert st.st_size==cases[name]['raw_bytes']
 dest=case+'/stream_v1';os.mkdir(dest)
 started=time.time()
 with open(dest+'/progress.log','w') as log:
  subprocess.check_call(['ionice','-c','3',tools+'/stream_psf',raw,tools+'/selected.txt',tools+'/pairs.txt',dest+'/wave'],stdout=log,stderr=log)
 meta=json.load(open(dest+'/wave.meta.json'))
 assert abs(meta['last_time_s']-200e-9)<1e-14
 st2=os.stat(raw);assert (st.st_ino,st.st_size,st.st_mtime)==(st2.st_ino,st2.st_size,st2.st_mtime)
 # Compression uses bounded buffers; keep derived binary for interrupted transfer recovery.
 with open(dest+'/wave.bin','rb') as src,gzip.open(dest+'/wave.bin.gz','wb',compresslevel=1) as dst:
  shutil.copyfileobj(src,dst,1024*1024)
 for a,b in [('spectre.out','spectre.out'),('test.raw/logStatus','logStatus')]:shutil.copyfile(case+'/'+a,dest+'/'+b)
 files=['wave.bin.gz','wave.columns','wave.stress.tsv','wave.extrema.tsv','wave.meta.json','spectre.out','logStatus','progress.log']
 receipt=dict(case=name,source=dict(path=raw,bytes=st.st_size,inode=st.st_ino,mtime=st.st_mtime,unchanged=True),
  elapsed_seconds=time.time()-started,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
  memory_limit_bytes=512*1024*1024,files={n:dict(bytes=os.path.getsize(dest+'/'+n),sha256=sha(dest+'/'+n)) for n in files})
 with open(dest+'/receipt.json','w') as f:json.dump(receipt,f,indent=2)
 print('COMPLETE',name,receipt['elapsed_seconds']);sys.stdout.flush()

if __name__=='__main__':main()
