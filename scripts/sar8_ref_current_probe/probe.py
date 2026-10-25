"""Measurement-only native runs on the frozen Rgate baseline; bounded transport."""
import argparse,json,sys,hashlib,re,shlex,shutil,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_stress_closure'))
import stream_control as transport
OUT=ROOT/'output/sar8_ref_current_probe';VERIFY=ROOT/'verification/sar8_ref_current_probe'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_current_probe_20261025'
SPEC='/home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre'
OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True);transport.OUT=OUT
read,dump,sha=transport.read,transport.dump,transport.sha

def preflight():
 deps=read(ROOT/'verification/sar8_stress_closure/preflight.json')['dependencies_sha256']
 code='''import os,json,subprocess,hashlib
deps=__DEPS__
actual={}
for p in deps:
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(1048576)
   if not b:break
   h.update(b)
 actual[p]=h.hexdigest()
mem={k:int(v.split()[0]) for k,v in [l.split(':',1) for l in open('/proc/meminfo')] if k in ['MemAvailable','SwapFree']}
fs=os.statvfs('/home/chenzc_intern25/TSMC28/llm_IO')
ps=subprocess.Popen(['pgrep','-a','-u',str(os.getuid()),'-x','spectre'],stdout=subprocess.PIPE).communicate()[0].decode()
help={}
for topic in ['save','options']:
 p=subprocess.Popen(['timeout','15',__SPEC__,'-h',topic],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 output=p.communicate()[0].decode('utf8','replace');help[topic]=dict(exit=p.returncode,text=output)
version=subprocess.check_output(['timeout','10',__SPEC__,'-W'],stderr=subprocess.STDOUT).decode()
print(json.dumps(dict(hashes=actual,memory_kib=mem,disk_available_bytes=fs.f_bavail*fs.f_frsize,active_spectre=ps,help=help,version=version)))
'''.replace('__DEPS__',repr(deps)).replace('__SPEC__',repr(SPEC))
 r=json.loads(transport.remote(code))
 for topic,v in r.pop('help').items():
  (OUT/('spectre_help_'+topic+'.txt')).write_text(v['text']);assert v['exit']==0
 assert r['hashes']==deps
 assert not r['active_spectre'].strip(),'Existing native simulation; do not add load'
 assert r['memory_kib']['MemAvailable']>8*1024*1024 and r['disk_available_bytes']>8*1024**3
 r.update(profile='t28_io',ok=True,OA_changed=False);dump(VERIFY/'preflight.json',r)
 print({k:v for k,v in r.items() if k!='hashes'})

def prepare(name,source,stop):
 folder=OUT/name;folder.mkdir(exist_ok=False)
 original=ROOT/'output/sar8_stress_closure'/source
 old=(original/'test.scs').read_text()
 # Existing reduced voltage names contain no mixed-case generated suffixes.
 volts=(ROOT/'output/sar8_stress_closure/stream_v1_tools/selected.txt').read_text().splitlines()
 volts=[v.upper() for v in volts]
 currents=[]
 for side in ['P','N']:
  for bit in range(8):
   for dev in ['MN_LOW','MP_HIGH']:
    currents += ['XDUT.XCDAC.XS%s%d.%s:%d'%(side,bit,dev,p) for p in range(1,5)]
   currents += ['XDUT.XCDAC.CMOM%s%d:%d'%(side,bit,p) for p in [1,2]]
 for bit,gate in [(7,'GPN'),(7,'GPP'),(4,'GNN'),(4,'GNP'),(3,'GPN'),(3,'GPP')]:
  prefix='XDUT.XREF.XDRV%d.'%bit
  volts += [prefix+gate+s for s in ['DRV','B','A']]
  currents += [prefix+'R'+gate+'0:1',prefix+'R'+gate+'1_5__dmy0:2']
  for dev in ['CN','CP']:
   currents += [prefix+gate+dev+':'+str(p) for p in range(1,5)]
 for dev in ['RREFP','RREFN','CREFP','CREFN']:
  currents += [dev+':1',dev+':2']
 for side in ['P','N']:
  currents += ['XDUT.XCDAC.CMOM%s8:%d'%(side,p) for p in [1,2]]
 volts=sorted(set(volts));currents=sorted(set(currents));selected=volts+currents
 deck=re.sub(r'^save .*\n','',old,flags=re.M)
 deck=deck.replace('saveOptions options save=selected','saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no')
 assert deck.count('tran_perf tran stop=200n')==1
 deck=deck.replace('tran_perf tran stop=200n','tran_perf tran stop='+stop)
 deck+='\n'+'\n'.join('save '+x for x in selected)+'\n'
 # Exactly reversible measurement-only transform, not an edited DUT.
 restored=re.sub(r'^save .*\n','',deck,flags=re.M).rstrip()
 restored=restored.replace(' currents=selected subcktiprobes=no useprobes=no','').replace('tran_perf tran stop='+stop,'tran_perf tran stop=200n')
 assert restored==re.sub(r'^save .*\n','',old,flags=re.M).rstrip()
 (folder/'test.scs').write_text(deck)
 for fn in ['dut.scs','r4_perf_monitor.va']:shutil.copyfile(original/fn,folder/fn)
 (folder/'selected.txt').write_text('\n'.join(x.lower() for x in selected)+'\n')
 (folder/'pairs.txt').write_text('xdut.gnn4 0\nxdut.xcdac.bp7 0\n')
 manifest=dict(name=name,source=source,stop=stop,remote=REMOTE+'/'+name,voltages=volts,currents=currents,
  source_hashes={f:sha(original/f) for f in ['test.scs','dut.scs','r4_perf_monitor.va']},
  files={f:sha(folder/f) for f in ['test.scs','dut.scs','r4_perf_monitor.va','selected.txt','pairs.txt']},
  circuit_unchanged=True,inserted_probes=False,threads=4,preset='cx')
 dump(folder/'manifest.json',manifest);dump(VERIFY/(name+'_manifest.json'),manifest)
 print(name,len(volts),'voltages',len(currents),'terminal currents')

def launch(name):
 raise RuntimeError('Historical launcher disabled after management commit b6da655. Use scripts/management/project.py register/submit for new runs.')
 # Frozen construction below records the already-completed measurement batch.
 folder=OUT/name;m=read(folder/'manifest.json');assert not (folder/'launch.json').exists()
 if name!='smoke_cold':assert read(VERIFY/'smoke_validation.json')['passed']
 resource_gate(name)
 archive=OUT/(name+'.tar.gz')
 with tarfile.open(archive,'w:gz') as tf:
  for f in list(m['files'])+['manifest.json']:tf.add(folder/f,arcname=f)
 print(transport.remote("import os\np="+repr(REMOTE)+"\nif not os.path.isdir(p):os.mkdir(p)\nassert not os.path.exists(p+'/'+"+repr(name)+")"))
 transport.scp(archive,'thu-wei:'+REMOTE+'/'+name+'.tar.gz')
 cmd='source /home/cshrc/.cshrc.cadence.IC618SP201; cd '+shlex.quote(m['remote'])+'; '+SPEC+' -64 test.scs +escchars +log spectre.out -format psfascii -raw test.raw +preset=cx +mt=4 +lqtimeout 60 -preset_override -maxw 5 -maxn 5 +logstatus'
 worker="""import os,subprocess,json,time,resource,fcntl
p=__PATH__;root=os.path.dirname(p)
lock=open(root+'/native.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
mem={k:int(v.split()[0]) for k,v in [l.split(':',1) for l in open('/proc/meminfo')] if k=='MemAvailable'}
assert mem['MemAvailable']>8*1024*1024
ps=subprocess.Popen(['pgrep','-u',str(os.getuid()),'-x','spectre'],stdout=subprocess.PIPE).communicate()[0]
assert not ps.strip(),'Another Spectre running'
fs=os.statvfs(p);assert fs.f_bavail*fs.f_frsize>8*1024**3
os.nice(5);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
start=time.time()
rc=subprocess.call(['/bin/csh','-fc',__COMMAND__],cwd=p)
json.dump(dict(exit_code=rc,elapsed_s=time.time()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),open(p+'/finished.json','w'))
""".replace('__PATH__',repr(m['remote'])).replace('__COMMAND__',repr(cmd))
 code="""import os,tarfile,hashlib,json,subprocess
p=__PATH__;arc=p+'.tar.gz'
with open(arc,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==__HASH__
os.mkdir(p)
with tarfile.open(arc) as tf:
 assert all('/' not in a.name and a.isfile() for a in tf.getmembers());tf.extractall(p)
m=json.load(open(p+'/manifest.json'))
for fn,h in m['files'].items():
 with open(p+'/'+fn,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==h
open(p+'/worker.py','w').write(__WORKER__)
with open(p+'/worker.log','ab') as log,open('/dev/null','rb') as null:
 child=subprocess.Popen(['python','-u',p+'/worker.py'],stdin=null,stdout=log,stderr=log,preexec_fn=os.setsid)
print(json.dumps(dict(pid=child.pid,remote=p)))
""".replace('__PATH__',repr(m['remote'])).replace('__HASH__',repr(sha(archive))).replace('__WORKER__',repr(worker))
 r=json.loads(transport.remote(code));dump(folder/'launch.json',r);print(r)

def resource_gate(name):
 code="""import os,json,time,subprocess
cgroup='/sys/fs/cgroup/memory/user.slice/user-596.slice/'
mem={k:int(v.split()[0]) for k,v in [l.split(':',1) for l in open('/proc/meminfo')] if k in ['MemAvailable','SwapFree']}
c={f:int(open(cgroup+f).read()) for f in ['memory.usage_in_bytes','memory.limit_in_bytes','memory.memsw.usage_in_bytes']}
def swap():return {k:int(v) for k,v in [l.split() for l in open('/proc/vmstat')] if k in ['pswpin','pswpout']}
a=swap();time.sleep(1);b=swap();delta={k:b[k]-a[k] for k in a}
fs=os.statvfs(__ROOT__);free=fs.f_bavail*fs.f_frsize
ps=subprocess.Popen(['pgrep','-a','-u',str(os.getuid()),'-x','spectre'],stdout=subprocess.PIPE).communicate()[0].decode()
assert not ps.strip()
assert mem['MemAvailable']>8*1024*1024 and c['memory.limit_in_bytes']-c['memory.usage_in_bytes']>4*1024**3 and free>8*1024**3
assert sum(delta.values())<256,'Active host swapping; postpone native job'
print(json.dumps(dict(memory_kib=mem,cgroup=c,swap_pages_per_observed_second=delta,free_disk_bytes=free,active_spectre=ps)))
""".replace('__ROOT__',repr(REMOTE))
 r=json.loads(transport.remote(code));dump(VERIFY/(name+'_resources.json'),r);print('RESOURCE_GATE_PASS',r['memory_kib'],r['swap_pages_per_observed_second'])

def status(name):
 p=REMOTE+'/'+name
 code="""import os,json,re,subprocess
p=__PATH__;r={}
for f in ['finished.json','spectre.out','worker.log','reduce_v2.log','test.raw/tran_perf.tran.tran']:
 q=p+'/'+f
 if not os.path.isfile(q):continue
 if f=='finished.json':r[f]=json.load(open(q));continue
 r[f+'_bytes']=os.path.getsize(q)
 if f.endswith('.tran'):
  with open(q,'rb') as h:
   h.seek(max(0,os.path.getsize(q)-65536));tail=h.read().decode('utf8','replace')
  ts=re.findall(r'^"time" ([^\\n]+)',tail,re.M)
  if ts:r['last_saved_ns']=float(ts[-1])*1e9
 if f.endswith('.log') or f.endswith('.out'):
  with open(q,'rb') as h:h.seek(max(0,os.path.getsize(q)-1800));r[f+'_tail']=h.read().decode('utf8','replace')
ps=subprocess.Popen(['ps','-u',str(os.getuid()),'-o','pid,comm,rss,etime'],stdout=subprocess.PIPE).communicate()[0].decode()
r['spectre_processes']=[l for l in ps.splitlines() if 'spectre' in l]
r['reduction_complete']=os.path.isfile(p+'/reduced_v2/receipt.json')
if 'reduce_v2.log_tail' in r:r['reduction_progress']=r['reduce_v2.log_tail'].splitlines()[-2:]
print(json.dumps(r))
""".replace('__PATH__',repr(p))
 r=json.loads(transport.remote(code));dump(OUT/name/'status.json',r)
 print(json.dumps({k:v for k,v in r.items() if not k.endswith('_tail')},indent=2))
 if r.get('finished.json',{}).get('exit_code',0)!=0:
  for k,v in r.items():
   if k.endswith('_tail'):
    print(k,'\n'.join(l for l in v.splitlines() if re.search(r'error|Error|WARNING|Traceback|Assertion',l)))

def reduce(name):
 raise RuntimeError('Historical remote-analysis launcher disabled after b6da655. Use managed analyze for new heavy work; collect/status remain read-only.')
 # Frozen construction below records the already-completed reductions.
 p=REMOTE+'/'+name
 worker="""import os,json,subprocess,gzip,shutil,hashlib,resource,time,fcntl
p=__PATH__;assert json.load(open(p+'/finished.json'))['exit_code']==0
lock=open(os.path.dirname(p)+'/native.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
active=subprocess.Popen(['pgrep','-u',str(os.getuid()),'-x','spectre'],stdout=subprocess.PIPE).communicate()[0]
assert not active.strip(),'Do not overlap heavy reduction with simulation'
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));os.nice(5)
d=p+'/reduced_v2'
assert not os.path.exists(d+'/receipt.json'),'Already reduced'
if not os.path.isdir(d):os.mkdir(d)
exe=os.path.dirname(p)+'/stream_psf_v2'
with open(exe,'rb') as f:parser_sha=hashlib.sha256(f.read()).hexdigest()
raw=p+'/test.raw/tran_perf.tran.tran'
m=json.load(open(p+'/manifest.json'))
for fn,h in m['files'].items():
 with open(p+'/'+fn,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==h
before=os.stat(raw)
# Preserve the exact native TRACE declarations as probe evidence.
with open(raw) as f,open(d+'/trace.txt','w') as out:
 recording=False
 for line in f:
  if line.strip()=='TRACE':recording=True
  if line.strip()=='VALUE':break
  if recording:out.write(line)
if not os.path.exists(d+'/wave.meta.json'):
 subprocess.check_call([exe,raw,p+'/selected.txt',p+'/pairs.txt',d+'/wave'])
if not os.path.exists(d+'/wave.bin.gz'):
 with open(d+'/wave.bin','rb') as src,gzip.open(d+'/wave.bin.gz','wb',1) as dst:shutil.copyfileobj(src,dst,1048576)
for fn,src in [('spectre.out','spectre.out'),('logStatus','test.raw/logStatus'),('finished.json','finished.json')]:shutil.copyfile(p+'/'+src,d+'/'+fn)
files={}
for fn in ['wave.bin.gz','wave.columns','wave.meta.json','wave.extrema.tsv','wave.stress.tsv','trace.txt','spectre.out','logStatus','finished.json']:
 h=hashlib.sha256()
 with open(d+'/'+fn,'rb') as f:
  while True:
   b=f.read(1048576)
   if not b:break
   h.update(b)
 files[fn]=dict(bytes=os.path.getsize(d+'/'+fn),sha256=h.hexdigest())
after=os.stat(raw);assert (before.st_ino,before.st_size,before.st_mtime)==(after.st_ino,after.st_size,after.st_mtime)
json.dump(dict(files=files,raw_bytes=os.path.getsize(raw),raw_inode=before.st_ino,raw_mtime=before.st_mtime,raw_unchanged=True,
 inputs_rehashed_after_simulation=True,parser_sha256=parser_sha,peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),open(d+'/receipt.json','w'))
print('REDUCTION_COMPLETE')
""".replace('__PATH__',repr(p))
 code="""import os,subprocess,json
p=__PATH__;assert not os.path.exists(p+'/reduced_v2/receipt.json')
open(p+'/reduce_worker_v2.py','w').write(__WORKER__)
with open(p+'/reduce_v2.log','ab') as log,open('/dev/null','rb') as null:
 child=subprocess.Popen(['python','-u',p+'/reduce_worker_v2.py'],stdin=null,stdout=log,stderr=log,preexec_fn=os.setsid)
print(json.dumps(dict(pid=child.pid)))
""".replace('__PATH__',repr(p)).replace('__WORKER__',repr(worker))
 print(transport.remote(code))

def collect(name):
 d=OUT/name/'reduced_v2';d.mkdir(exist_ok=True);rp=REMOTE+'/'+name+'/reduced_v2/'
 if not (d/'receipt.json').exists():transport.scp('thu-wei:'+rp+'receipt.json',d/'receipt.json')
 receipt=read(d/'receipt.json')
 for fn,m in receipt['files'].items():
  target=d/fn
  if target.exists():assert sha(target)==m['sha256'];continue
  part=d/(fn+'.partial');assert not part.exists()
  transport.scp('thu-wei:'+rp+fn,part,180);assert sha(part)==m['sha256'];part.rename(target)
 if not (d/'wave.bin').exists():
  import gzip
  with gzip.open(d/'wave.bin.gz','rb') as src,(d/'wave.bin').open('xb') as dst:shutil.copyfileobj(src,dst,1048576)
 print('COLLECTED',name,read(d/'wave.meta.json'))

def parser():
 source=ROOT/'scripts/sar8_ref_current_probe/stream_psf.cpp'
 transport.scp(source,'thu-wei:'+REMOTE+'/stream_psf_v2.cpp')
 fixture='SWEEP\n"time" "time"\nTRACE\n"A" "V"\n"B" "I" PROP(\n"units" "A"\n)\nVALUE\n"time" 0\n"A" 1\n"B" 2\n"time" 1e-9\n"B" 3\nEND\n'
 code="""import subprocess,struct,json
p=__ROOT__
subprocess.check_call(['g++','-std=c++11','-O2',p+'/stream_psf_v2.cpp','-o',p+'/stream_psf_v2'])
open(p+'/fixture.psf','w').write(__FIXTURE__)
open(p+'/fixture.selected','w').write('a\\nb\\n');open(p+'/fixture.pairs','w').write('a b\\n')
subprocess.check_call([p+'/stream_psf_v2',p+'/fixture.psf',p+'/fixture.selected',p+'/fixture.pairs',p+'/fixture'])
with open(p+'/fixture.bin','rb') as f:assert struct.unpack('<6d',f.read())==(0.,1.,2.,1e-9,1.,3.)
print('CURRENT_PROP_FIXTURE_PASS')
""".replace('__ROOT__',repr(REMOTE)).replace('__FIXTURE__',repr(fixture))
 print(transport.remote(code));dump(VERIFY/'parser_validation.json',dict(source_sha256=sha(source),sparse_current_PROP_fixture=True))

if __name__=='__main__':
 action=sys.argv[1]
 if action=='preflight':preflight()
 elif action=='prepare':prepare(*sys.argv[2:])
 elif action=='launch':launch(sys.argv[2])
 elif action=='status':status(sys.argv[2])
 elif action=='reduce':reduce(sys.argv[2])
 elif action=='collect':collect(sys.argv[2])
 elif action=='parser':parser()
