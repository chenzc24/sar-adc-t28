"""Deploy an isolated pinned read-only log collector on the authorized server."""
import base64,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
DEST='/server_local_ssd/chenzc_intern25/sar-adc-t28/campaigns/sar8-mc-20261103'
REMOTE=r'''
import os,sys,json,base64,hashlib,tarfile,io,subprocess,resource
p=json.load(sys.stdin);dest=p['dest'];root='/server_local_ssd/chenzc_intern25/sar-adc-t28'
assert os.getuid()==596 and os.path.realpath(root)==root and dest==root+'/campaigns/sar8-mc-20261103'
if not os.path.isdir(dest):os.mkdir(dest,0o700)
assert os.path.realpath(dest)==dest and os.stat(dest).st_uid==596
mon=dest+'/monitor'
if not os.path.isdir(mon):os.mkdir(mon,0o700)
assert not os.path.exists(mon+'/launch.json'),'Collector launch already recorded: inspect instead of restarting'
src=mon+'/inspector-164dbe6'
if not os.path.isdir(src):os.mkdir(src,0o700)
blob=base64.b64decode(p['archive']);assert hashlib.sha256(blob).hexdigest()==p['sha256']
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as tar:
 for member in tar:
  assert member.isfile() or member.isdir()
  assert not member.name.startswith('/') and '..' not in member.name.split('/')
  target=src+'/'+member.name
  if member.isdir():
   if not os.path.isdir(target):os.makedirs(target)
  else:
   data=tar.extractfile(member).read()
   if os.path.exists(target):assert open(target,'rb').read()==data
   else:
    parent=os.path.dirname(target)
    if not os.path.isdir(parent):os.makedirs(parent)
    with open(target,'wb') as f:f.write(data)
with open(mon+'/manifest.json','w') as f:json.dump(p['manifest'],f,indent=2)
py='/home/chenzc_intern25/.local/share/uv/python/cpython-3.11.11-linux-x86_64-gnu/bin/python3.11'
v=subprocess.check_output([py,'-m','simcheck','--version'],cwd=src).strip()
assert v=='0.4.0'
db=mon+'/index.sqlite'
def setup():
 os.setsid();os.nice(10);resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
with open('/dev/null','rb') as null,open(mon+'/collector.log','ab') as log:
 c=subprocess.Popen([py,'-m','simcheck','--db',db,'watch',mon+'/manifest.json','--interval','5'],cwd=src,stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
ticks=open('/proc/'+str(c.pid)+'/stat').read().split()[21]
receipt={'pid':c.pid,'start_ticks':ticks,'python':py,'db':db,'cwd':src,'manifest':mon+'/manifest.json','revision':p['revision'],'archive_sha256':p['sha256']}
with open(mon+'/launch.json','w') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''

def main():
    m=json.loads((R/'verification/sar8_mc/manifest.json').read_text())
    archive=(R/'output/sar8_mc/inspector-164dbe6.tar.gz').read_bytes()
    manifest={'runs':[{'id':x['run_id'],'log':'/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/'+x['run_id']+'/spectre.out',
        'state':'/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/'+x['run_id']+'/simulation.state.json',
        'log_status':'/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/'+x['run_id']+'/raw/logStatus'} for x in m['runs'].values()]}
    payload={'dest':DEST,'archive':base64.b64encode(archive).decode(),'sha256':hashlib.sha256(archive).hexdigest(),
        'revision':m['inspector_commit'],'manifest':manifest}
    code="import base64;exec(base64.b64decode('%s'))"%base64.b64encode(REMOTE.encode()).decode()
    r=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c "'+code+'"'],input=json.dumps(payload),capture_output=True,text=True,timeout=50)
    (R/'output/sar8_mc/monitor_deploy_stdout.txt').write_text(r.stdout)
    (R/'output/sar8_mc/monitor_deploy_stderr.txt').write_text(r.stderr)
    r.check_returncode();receipt=json.loads(r.stdout)
    (R/'verification/sar8_mc/monitor_launch.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
