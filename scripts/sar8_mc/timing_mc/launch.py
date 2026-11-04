"""One durable queue and one independent pinned collector per campaign DB."""
import base64
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'verification/sar8_mc/timing_mc'
REMOTE=r'''
import os,sys,json,base64,hashlib,subprocess
p=json.load(sys.stdin)
root='/server_local_ssd/chenzc_intern25/sar-adc-t28'
group=p['group']
assert group in ('modules','cold','refs') and os.getuid()==596
d=root+'/campaigns/sar8-timing-mc-20261104-'+group
assert os.path.realpath(d)==d
if not os.path.isdir(d):os.mkdir(d,0o700)
assert not any(os.path.exists(d+'/'+n) for n in ['launch.json','flow.log','monitor.log'])
for name,encoded in p['files'].items():
 data=base64.b64decode(encoded)
 if name.endswith('.py'):compile(data,name,'exec')
 with open(d+'/'+name,'wb') as f:f.write(data)
m=json.load(open(d+'/manifest.json'))
for run,h in m['registered_hashes'].items():
 assert json.load(open(root+'/runs/'+run+'/registered.json'))['recipe_hash']==h
rows=[]
for run in m['jobs']:
 path=root+'/runs/'+run
 family=run.split('-')[1]
 analysis={'cdac':'cap_ac','comp':'comp_tran'}.get(family,'tran_ab')
 raw=path+'/raw/mc_separate/mc-001/mc_'+analysis+('.ac' if family=='cdac' else '.tran.tran')
 row=dict(id=run,analysis=analysis,log=path+'/spectre.out',state=path+'/simulation.state.json',log_status=path+'/raw/logStatus',raw=raw)
 if family!='cdac':row['expected_stop_s']=109e-9 if family=='comp' else 1059e-9
 rows.append(row)
with open(d+'/monitor.json','w') as f:json.dump({'runs':rows},f)
def launch(args,filename,cwd):
 def setup():os.setsid();os.nice(10)
 with open('/dev/null','rb') as i,open(d+'/'+filename,'ab') as o:
  return subprocess.Popen(args,cwd=cwd,stdin=i,stdout=o,stderr=o,close_fds=True,preexec_fn=setup).pid
mon=p['monitor']
db=d+'/index.sqlite'
watch=launch([mon['python'],'-m','simcheck','--db',db,'watch',d+'/monitor.json','--interval','15'],'monitor.log',mon['cwd'])
flow=launch([sys.executable,d+'/flow.py'],'flow.log',d)
r=dict(path=d,monitor_pid=watch,flow_pid=flow,db=db,revision=mon['revision'],python=mon['python'],cwd=mon['cwd'])
with open(d+'/launch.json','w') as f:json.dump(r,f)
print(json.dumps(r))
'''
if __name__=='__main__':
    group=sys.argv[1]
    files={'manifest.json':OUT/(group+'.json'),'managed_campaign.py':ROOT/'scripts/sar8_mc/module_campaign_v2.py','flow.py':Path(__file__).with_name('review_flow.py' if group=='refs' else 'flow.py')}
    if group=='refs':files['cold_queue.py']=Path(__file__).with_name('cold_queue.py')
    bundle={name:base64.b64encode(path.read_bytes()).decode() for name,path in files.items()}
    mon=json.loads((ROOT/'verification/sar8_mc/physical_input/regen_monitor.json').read_text())
    assert mon['revision']=='164dbe66391b580fe28ff73ad9fd07824644f934'
    cmd='python -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(REMOTE.encode()).decode()+"'))")
    r=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',cmd],input=json.dumps(dict(group=group,files=bundle,monitor=mon)),capture_output=True,text=True,timeout=60)
    if r.returncode:raise RuntimeError(r.stderr)
    (OUT/(group+'_launch.json')).write_text(r.stdout)
    print(r.stdout)
