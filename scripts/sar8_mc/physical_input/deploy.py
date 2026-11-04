"""Register final six, start finite flow and one read-only pinned monitor."""
import base64,hashlib,json,shlex,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';sys.path.insert(0,str(R/'scripts/management'))
import execution
REMOTE=r'''
import os,sys,json,hashlib,base64,subprocess,resource
p=json.load(sys.stdin);root='/server_local_ssd/chenzc_intern25/sar-adc-t28';dest=root+'/campaigns/sar8-physical-input-20261104'
assert os.getuid()==596
if not os.path.isdir(dest):os.mkdir(dest,0o700)
assert os.path.realpath(dest)==dest and not os.path.exists(dest+'/launch.json')
for row in p['files']:
 b=base64.b64decode(row['data']);assert hashlib.sha256(b).hexdigest()==row['sha256'];target=dest+'/'+row['name'];assert not os.path.exists(target)
 with open(target,'wb') as f:f.write(b)
 if target.endswith('.py'):compile(b,target,'exec')
m=json.load(open(dest+'/manifest.json'))
for run,h in m['registered_hashes'].items():assert json.load(open(root+'/runs/'+run+'/registered.json'))['recipe_hash']==h
def setup():os.setsid();os.nice(10);resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
with open('/dev/null','rb') as null,open(dest+'/flow.log','ab') as log:
 q=subprocess.Popen([sys.executable,dest+'/flow.py'],stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
launch={'path':dest,'pid':q.pid,'start_ticks':open('/proc/'+str(q.pid)+'/stat').read().split()[21]}
old=json.load(open(root+'/campaigns/sar8-mc-20261103/monitor/launch.json'));rows=[]
for run in m['initial_runs']+m['paired_runs']:
 rand='-s' in run;name='mc_phys_tran' if rand else 'phys_tran'
 rows.append({'id':run,'log':root+'/runs/'+run+'/spectre.out','state':root+'/runs/'+run+'/simulation.state.json','log_status':root+'/runs/'+run+'/raw/logStatus',
  'analysis':name,'raw':root+'/runs/'+run+'/raw/'+('mc_separate/mc-001/' if rand else '')+name+'.tran.tran','expected_stop_s':2259e-9})
with open(dest+'/monitor_manifest.json','w') as f:json.dump({'runs':rows},f,indent=2)
with open('/dev/null','rb') as null,open(dest+'/monitor.log','ab') as log:
 q=subprocess.Popen([old['python'],'-m','simcheck','--db',dest+'/monitor.sqlite','watch',dest+'/monitor_manifest.json','--interval','5'],cwd=old['cwd'],stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
launch['monitor']={'pid':q.pid,'start_ticks':open('/proc/'+str(q.pid)+'/stat').read().split()[21],'python':old['python'],'cwd':old['cwd'],'db':dest+'/monitor.sqlite','revision':'164dbe66391b580fe28ff73ad9fd07824644f934'}
with open(dest+'/launch.json','w') as f:json.dump(launch,f,indent=2)
print(json.dumps(launch))
'''
def main():
    m=json.loads((V/'manifest_v2.json').read_text());paired=list(m['runs']);initial=['sar8phys-nominal-hold-v1','sar8phys-s4124-hold-v1','sar8phys-s4124-stiff-v1']
    recovered=R/'output/sar8_mc/physical_input/network_recovered.json'
    observed=json.loads(recovered.read_text())['runs'] if recovered.exists() else {}
    for run in paired:
        registration=observed.get(run,{}).get('registered.json')
        if registration and registration['files_complete']:
            local=execution.project.load(R/'management/runs'/(run+'.yaml'));assert local['recipe_hash']==registration['recipe_hash']
            print('Readback confirmed existing registration',run,flush=True);continue
        print('Register',run,flush=True);print(json.dumps(execution.register('management/recipes/'+run+'.yaml')),flush=True)
    registered={run:json.loads(json.dumps(execution.project.load(R/'management/runs'/(run+'.yaml'))))['recipe_hash'] for run in initial+paired}
    manifest={'initial_runs':initial,'paired_runs':paired,'registered_hashes':registered,'agent_sha256':hashlib.sha256((R/'scripts/management/remote_agent.py').read_bytes()).hexdigest()}
    (V/'server_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');files=[]
    for path,name in [(R/'scripts/sar8_mc/module_campaign_v2.py','managed_campaign.py'),(R/'scripts/sar8_mc/physical_input/flow.py','flow.py'),(V/'server_manifest.json','manifest.json')]:
        b=path.read_bytes();files.append({'name':name,'sha256':hashlib.sha256(b).hexdigest(),'data':base64.b64encode(b).decode()})
    code='import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))'
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],input=json.dumps({'files':files}),text=True,capture_output=True,timeout=40)
    (R/'output/sar8_mc/physical_input/deploy.stdout').write_text(p.stdout);(R/'output/sar8_mc/physical_input/deploy.stderr').write_text(p.stderr)
    assert p.returncode==0,p.stderr
    d=json.loads(p.stdout);(V/'launch.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
if __name__=='__main__':main()
