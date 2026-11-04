"""Freeze and start one finite managed module coordinator and read-only monitor."""
import base64,hashlib,json,shlex,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
REMOTE=r'''
import os,sys,json,base64,hashlib,subprocess,resource
p=json.load(sys.stdin);root='/server_local_ssd/chenzc_intern25/sar-adc-t28';parent=root+'/campaigns/sar8-mc-20261103';dest=parent+'/modules'
assert os.getuid()==596 and os.path.realpath(parent)==parent
if not os.path.isdir(dest):os.mkdir(dest,0o700)
assert os.path.realpath(dest)==dest and os.stat(dest).st_uid==596
assert not os.path.exists(dest+'/launch.json'),'Already deployed; inspect existing checkpoint'
for item in p['files']:
 assert item['name'] in ['server_flow.py','manifest.json']
 data=base64.b64decode(item['data']);assert hashlib.sha256(data).hexdigest()==item['sha256']
 target=dest+'/'+item['name'];assert not os.path.exists(target)
 with open(target,'wb') as f:f.write(data)
 if item['name'].endswith('.py'):compile(data,target,'exec')
m=json.load(open(dest+'/manifest.json'))
for run,h in m['registered_hashes'].items():assert json.load(open(root+'/runs/'+run+'/registered.json'))['recipe_hash']==h
def setup():os.setsid();os.nice(10)
with open('/dev/null','rb') as null,open(dest+'/coordinator.log','ab') as log:
 c=subprocess.Popen([sys.executable,dest+'/server_flow.py'],stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
receipt={'pid':c.pid,'start_ticks':open('/proc/'+str(c.pid)+'/stat').read().split()[21],'path':dest,'manifest_sha256':hashlib.sha256(open(dest+'/manifest.json','rb').read()).hexdigest()}
with open(dest+'/launch.json','w') as f:json.dump(receipt,f,indent=2)
mon=json.load(open(parent+'/monitor/launch.json'));py=mon['python'];src=mon['cwd'];db=dest+'/monitor.sqlite'
manifest={'runs':[{'id':x['run_id'],'log':root+'/runs/'+x['run_id']+'/spectre.out','state':root+'/runs/'+x['run_id']+'/simulation.state.json','log_status':root+'/runs/'+x['run_id']+'/raw/logStatus'} for x in m['runs'].values()]}
with open(dest+'/monitor_manifest.json','w') as f:json.dump(manifest,f,indent=2)
def monsetup():os.setsid();os.nice(10);resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
with open('/dev/null','rb') as null,open(dest+'/monitor.log','ab') as log:
 q=subprocess.Popen([py,'-m','simcheck','--db',db,'watch',dest+'/monitor_manifest.json','--interval','5'],cwd=src,stdin=null,stdout=log,stderr=log,preexec_fn=monsetup,close_fds=True)
receipt['monitor']={'pid':q.pid,'start_ticks':open('/proc/'+str(q.pid)+'/stat').read().split()[21],'python':py,'cwd':src,'db':db,'revision':'164dbe66391b580fe28ff73ad9fd07824644f934'}
with open(dest+'/monitor_launch.json','w') as f:json.dump(receipt['monitor'],f,indent=2)
print(json.dumps(receipt))
'''
def main():
    files=[]
    for path,name in [(R/'scripts/sar8_mc/module_campaign.py','server_flow.py'),(R/'verification/sar8_mc/blocks/server_manifest.json','manifest.json')]:
        b=path.read_bytes();files.append({'name':name,'sha256':hashlib.sha256(b).hexdigest(),'data':base64.b64encode(b).decode()})
    code='import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))'
    r=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],input=json.dumps({'files':files}),capture_output=True,text=True,timeout=40)
    (R/'output/sar8_mc/module_deploy.stdout').write_text(r.stdout);(R/'output/sar8_mc/module_deploy.stderr').write_text(r.stderr)
    r.check_returncode();d=json.loads(r.stdout);(R/'verification/sar8_mc/blocks/launch.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
if __name__=='__main__':main()
