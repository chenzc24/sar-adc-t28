"""Launch a finite managed queue and the project's pinned read-only inspector."""
import base64
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

R=Path(__file__).resolve().parents[3]
V=R/'verification/sar8_mc/regen30'
REMOTE=r'''
import os,json,base64,hashlib,subprocess,sys
p=json.load(sys.stdin);root='/server_local_ssd/chenzc_intern25/sar-adc-t28'
d=root+'/campaigns/sar8-regen30-20261104'
assert os.getuid()==596 and os.path.realpath(d)==d
if not os.path.isdir(d):os.mkdir(d,0o700)
assert not os.path.exists(d+'/launch.json') and not os.path.exists(d+'/flow.log')
for row in p['files']:
 b=base64.b64decode(row['data']);assert hashlib.sha256(b).hexdigest()==row['sha256']
 with open(d+'/'+row['name'],'wb') as f:f.write(b)
 if row['name'].endswith('.py'):compile(b,row['name'],'exec')
m=json.load(open(d+'/manifest.json'))
for run,h in m['registered_hashes'].items():assert json.load(open(root+'/runs/'+run+'/registered.json'))['recipe_hash']==h
def setup():os.setsid();os.nice(10)
def launch(args,log,cwd):
 with open('/dev/null','rb') as i,open(d+'/'+log,'ab') as o:
  return subprocess.Popen(args,stdin=i,stdout=o,stderr=o,cwd=cwd,close_fds=True,preexec_fn=setup).pid
rows=[]
for run in m['paired_runs']:
 path=root+'/runs/'+run
 rows.append(dict(id=run,log=path+'/spectre.out',state=path+'/simulation.state.json',log_status=path+'/raw/logStatus',analysis='phys_tran',raw=path+'/raw/mc_separate/mc-001/mc_phys_tran.tran.tran',expected_stop_s=1.259e-6))
with open(d+'/monitor.json','w') as f:json.dump({'runs':rows},f)
c=p['monitor'];db=d+'/monitor.sqlite'
pid=launch([sys.executable,d+'/flow.py'],'flow.log',d)
watch=launch([c['python'],'-m','simcheck','--db',db,'watch',d+'/monitor.json','--interval','10'],'monitor.log',c['cwd'])
rec=dict(path=d,pid=pid,watch_pid=watch,db=db,revision=c['revision'])
with open(d+'/launch.json','w') as f:json.dump(rec,f)
print(json.dumps(rec))
'''
if __name__=='__main__':
    hashes=json.loads((V/'registered.json').read_text())
    jobs=json.loads((V/'jobs.json').read_text())
    assert set(hashes)==set(jobs) and len(jobs)==84
    manifest={'registered_hashes':hashes,'initial_runs':[],'paired_runs':jobs,'agent_sha256':hashlib.sha256((R/'scripts/management/remote_agent.py').read_bytes()).hexdigest()}
    (V/'manifest.json').write_text(json.dumps(manifest,indent=2))
    files=[]
    for path,name in [(V/'manifest.json','manifest.json'),(R/'scripts/sar8_mc/module_campaign_v2.py','managed_campaign.py'),(R/'scripts/sar8_mc/physical_input/flow.py','flow.py')]:
        data=path.read_bytes()
        files.append({'name':name,'sha256':hashlib.sha256(data).hexdigest(),'data':base64.b64encode(data).decode()})
    monitor=json.loads((R/'verification/sar8_mc/physical_input/regen_monitor.json').read_text())
    cmd='python -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))')
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',cmd],input=json.dumps({'files':files,'monitor':monitor}),capture_output=True,text=True,timeout=40,check=True)
    (V/'launch.json').write_text(p.stdout);print(p.stdout)
