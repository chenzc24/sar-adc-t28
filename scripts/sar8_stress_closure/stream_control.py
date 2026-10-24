"""Sequential native-result reduction; no simulator launch or raw modification."""
import argparse,base64,gzip,hashlib,json,shlex,shutil,subprocess,sys,tarfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/sar8_stress_closure'
VERIFY=ROOT/'verification/sar8_stress_closure'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024'
TOOLS=REMOTE+'/stream_v1_tools'
NAMES=json.loads((VERIFY/'setup.json').read_text())['names']
def read(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args,label,timeout=45):
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=OUT/'stream_transport';folder.mkdir(exist_ok=True)
 path=folder/(stamp+'_'+label)
 with path.with_suffix('.out').open('wb') as o,path.with_suffix('.err').open('wb') as e:
  try:rc=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=o,stderr=e,timeout=timeout).returncode
  except subprocess.TimeoutExpired:rc=124
 assert rc==0,(rc,path,path.with_suffix('.err').read_text(errors='replace')[-1500:])
 return path.with_suffix('.out').read_text(errors='replace')
def remote(code):
 enc=base64.b64encode(code.encode()).decode()
 cmd='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+enc+"'))")
 return run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei',cmd],'ssh')
def scp(src,dest,timeout=120):return run(['scp','-B','-o','ConnectTimeout=10',str(src),str(dest)],'scp',timeout)

def prepare():
 folder=OUT/'stream_v1_tools';folder.mkdir(exist_ok=False)
 ctx=read(OUT/NAMES[0]/'context.json')
 selected=set(['vdd!','vrefp','vrefn','vinp','vinn','vinp_src','vinn_src','sample',
  'xdut.topp','xdut.topn','xdut.comp_p','xdut.comp_n','xdut.seq_sample','xdut.sample_int',
  'xdut.cmp_clk','xdut.phi_u','xdut.xctrl.phi_w','xdut.xref.cap_clk','xdut.rst_done',
  'xdut.active','xdut.preset','xdut.sample_match','xdut.xbootp.g','xdut.xbootn.g'])
 for b in range(8):
  selected.add('d'+str(b))
  for k in ['q','h','l','rst']:selected.add('xdut.xref.'+k+str(b))
  for side in ['p','n']:
   selected.add('xdut.xcdac.b'+side+str(b))
   for pol in ['p','n']:selected.add('xdut.g'+side+pol+str(b))
 assert selected<=set(ctx['saved_signals']),selected-set(ctx['saved_signals'])
 selected=sorted(selected);(folder/'selected.txt').write_text('\n'.join(selected)+'\n')
 pairs=[];records=[];pair_index={}
 for d in ctx['stress_devices']:
  for a,b in [('d','s'),('g','s'),('g','d'),('g','b'),('b','d'),('b','s')]:
   nodes=tuple(sorted((d['nodes'][a].lower(),d['nodes'][b].lower())))
   if nodes not in pair_index:pair_index[nodes]=len(pairs);pairs.append(nodes)
   records.append(dict(instance=d['instance'],group=d['group'],model=d['model'],terminal=a+b,
    nodes=list(nodes),limit_v=d['limit_v'],pair_index=pair_index[nodes]))
 assert len(records)==10998
 (folder/'pairs.txt').write_text('\n'.join(' '.join(p) for p in pairs)+'\n')
 dump(folder/'mapping.json',dict(records=records,pairs=pairs,selected=selected))
 cleanup=read(ROOT/'verification/storage/2026-10-24-remote-waveform-cleanup.json')['post_verify']['current_cases']
 cases={}
 for name in NAMES:
  c=read(OUT/name/'context.json');assert c['stress_devices']==ctx['stress_devices']
  cases[name]=dict(deck_sha256=c['deck_sha256'],raw_bytes=next(x['raw_bytes'] for x in cleanup if x['name']==name))
 dump(folder/'cases.json',cases)
 for fn in ['stream_psf.cpp','stream_worker.py']:shutil.copyfile(ROOT/'scripts/sar8_stress_closure'/fn,folder/fn)
 # Sparse sample + GROUP1 alias fixture exercises exact parser invariants.
 (folder/'fixture.psf').write_text('SWEEP\n"time" "time"\nTRACE\n"A" "V"\n"probe" GROUP 1\n"B" "V"\nVALUE\n"time" 0\n"A" 1\n"probe" 0.25\n"time" 1e-9\n"A" -2\n"time" 2e-9\n"probe" -3\nEND\n')
 (folder/'fixture.selected').write_text('a\nb\n');(folder/'fixture.pairs').write_text('a b\n0 a\n')
 archive=OUT/'stream_v1_tools.tar.gz'
 with tarfile.open(archive,'w:gz') as tf:
  for p in folder.iterdir():tf.add(p,arcname=p.name)
 dump(VERIFY/'stream_setup.json',dict(columns=len(selected)+1,unique_pairs=len(pairs),MOS_pairs=len(records),
  memory_limit_mib=512,concurrent_workers=1,raw_kept=True,archive_sha256=sha(archive),
  current_probe_status='Requested wrapper terminal currents absent from native TRACE; no current attribution'))
 print('PREPARED',len(selected),len(pairs))

def deploy():
 archive=OUT/'stream_v1_tools.tar.gz'
 folder=OUT/'stream_v1_tools'
 for fn in ['stream_psf.cpp','stream_worker.py']:shutil.copyfile(ROOT/'scripts/sar8_stress_closure'/fn,folder/fn)
 with tarfile.open(archive,'w:gz') as tf:
  for item in folder.iterdir():tf.add(item,arcname=item.name)
 setup=read(VERIFY/'stream_setup.json');setup['archive_sha256']=sha(archive);dump(VERIFY/'stream_setup.json',setup)
 print(remote("import os\np="+repr(TOOLS)+"\nassert all(not os.path.exists(os.path.dirname(p)+'/'+n+'/stream_v1') for n in "+repr(NAMES)+")\nif not os.path.exists(p):os.mkdir(p)"))
 scp(archive,'thu-wei:'+TOOLS+'/tools.tar.gz')
 code="""import os,tarfile,subprocess,json,struct,hashlib
p=TOOLS
with open(p+'/tools.tar.gz','rb') as f:assert hashlib.sha256(f.read()).hexdigest()==HASH
with tarfile.open(p+'/tools.tar.gz','r:gz') as tf:
 assert all('/' not in x.name and x.isfile() for x in tf.getmembers());tf.extractall(p)
subprocess.check_call(['g++','-std=c++11','-O2',p+'/stream_psf.cpp','-o',p+'/stream_psf'])
subprocess.check_call([p+'/stream_psf',p+'/fixture.psf',p+'/fixture.selected',p+'/fixture.pairs',p+'/fixture'])
with open(p+'/fixture.bin','rb') as f:v=struct.unpack('<9d',f.read())
assert v==(0.,1.,.25,1e-9,-2.,.25,2e-9,-2.,-3.),v
s=[list(map(float,l.split())) for l in open(p+'/fixture.stress.tsv')]
assert s[0][1]==2.25 and s[0][2]==1e-9 and s[1][1]==2
print('FIXTURE_PASS')
""".replace('TOOLS',repr(TOOLS)).replace('HASH',repr(sha(archive)))
 print(remote(code));dump(VERIFY/'stream_parser_validation.json',dict(sparse_and_GROUP1_fixture=True,compiler='remote g++ -std=c++11 -O2'))

def launch(name):
 assert name in NAMES
 dest=OUT/name/'stream_launch.json';assert not dest.exists()
 code="""import os,subprocess,json
tools=TOOLS;name=NAME;p=os.path.dirname(tools)+'/'+name
assert not os.path.exists(p+'/stream_v1')
with open(p+'/stream_v1_worker.log','ab') as log,open('/dev/null','rb') as null:
 child=subprocess.Popen(['python',tools+'/stream_worker.py',name],stdin=null,stdout=log,stderr=log,preexec_fn=os.setsid)
print(json.dumps(dict(pid=child.pid,case=name)))
""".replace('TOOLS',repr(TOOLS)).replace('NAME',repr(name))
 response=json.loads(remote(code));dump(dest,response);print(response)

def status():
 code="""import os,json
root=ROOT;names=NAMES;rows=[]
for n in names:
 p=root+'/'+n;d=p+'/stream_v1';r=dict(name=n,complete=os.path.isfile(d+'/receipt.json'))
 for f,k in [(p+'/stream_v1_worker.log','worker'),(d+'/progress.log','progress')]:
  if os.path.isfile(f):
   with open(f,'rb') as h:h.seek(max(0,os.path.getsize(f)-600));r[k]=h.read().decode()
 if r['complete']:r['receipt']=json.load(open(d+'/receipt.json'))
 rows.append(r)
print(json.dumps(rows))
""".replace('ROOT',repr(REMOTE)).replace('NAMES',repr(NAMES))
 rows=json.loads(remote(code));dump(OUT/'stream_status.json',rows)
 for r in rows:print(r['name'],r['complete'],r.get('progress',''),r.get('worker',''))

def collect(name):
 folder=OUT/name/'stream_v1';folder.mkdir(exist_ok=True)
 rp=REMOTE+'/'+name+'/stream_v1/'
 if not (folder/'receipt.json').exists():scp('thu-wei:'+rp+'receipt.json',folder/'receipt.json')
 receipt=read(folder/'receipt.json')
 for fn,meta in receipt['files'].items():
  target=folder/fn
  if target.exists():assert sha(target)==meta['sha256'];continue
  part=folder/(fn+'.partial');assert not part.exists(),'Inspect partial transfer, do not overwrite'
  scp('thu-wei:'+rp+fn,part,180)
  assert part.stat().st_size==meta['bytes'] and sha(part)==meta['sha256']
  part.rename(target)
 raw=folder/'wave.bin'
 if not raw.exists():
  part=folder/'wave.bin.partial';assert not part.exists()
  with gzip.open(folder/'wave.bin.gz','rb') as src,part.open('xb') as dest:shutil.copyfileobj(src,dest,1024*1024)
  meta=read(folder/'wave.meta.json');assert part.stat().st_size==meta['points']*meta['columns']*8
  part.rename(raw)
 dump(VERIFY/(name+'_stream_receipt.json'),receipt);print('COLLECTED',name,receipt['peak_child_rss_kib'])

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','deploy','launch','status','collect']);p.add_argument('name',nargs='?');a=p.parse_args()
 if a.action in ['launch','collect']:globals()[a.action](a.name)
 else:globals()[a.action]()
