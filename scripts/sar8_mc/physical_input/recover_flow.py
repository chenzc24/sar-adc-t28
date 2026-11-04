"""Register explicit source reanalyses, then resume finite managed experiment."""
import base64,hashlib,json,shlex,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';S=R/'scripts/sar8_mc/physical_input';sys.path.insert(0,str(R/'scripts/management'))
import execution
REMOTE=r'''
import os,sys,json,subprocess,hashlib,base64
p=json.load(sys.stdin);root='/server_local_ssd/chenzc_intern25/sar-adc-t28';dest=root+'/campaigns/sar8-physical-input-20261104/recovery_v2'
assert os.getuid()==596
if not os.path.isdir(dest):os.mkdir(dest,0o700)
assert os.path.realpath(dest)==dest and not os.path.exists(dest+'/launch.json')
for row in p['files']:
 b=base64.b64decode(row['data']);assert hashlib.sha256(b).hexdigest()==row['sha256'];target=dest+'/'+row['name'];assert not os.path.exists(target)
 with open(target,'wb') as f:f.write(b)
 if target.endswith('.py'):compile(b,target,'exec')
def setup():os.setsid();os.nice(10)
# Do not lower a hard virtual-memory limit in the coordinator: managed children
# must set their own separately declared limits. Coordinator never reads raw.
with open('/dev/null','rb') as null,open(dest+'/flow.log','ab') as log:
 q=subprocess.Popen([sys.executable,dest+'/flow.py'],stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
d={'path':dest,'pid':q.pid,'start_ticks':open('/proc/'+str(q.pid)+'/stat').read().split()[21]}
with open(dest+'/launch.json','w') as f:json.dump(d,f,indent=2)
print(json.dumps(d))
'''
def main():
    initial=['sar8phys-nominal-hold-v1','sar8phys-s4124-hold-v1','sar8phys-s4124-stiff-v1'];recover=[]
    for source in initial:
        run=source+'-recover-v2';recover.append(run)
        files=[(S/'reanalyze.py','reanalyze.py'),(S/'reduce.py','reduce_source.py'),(R/'scripts/sar8_campaign/native_stream.py','native_stream.py')]
        spec={'schema_version':1,'run_id':run,'kind':'analysis_only','source_run_id':source,'design_id':'sar8_l90_mmain2_stdcell_v1','entry':'reanalyze.py','analyzer':'reanalyze.py',
          'inputs':[{'source':p.relative_to(R).as_posix(),'name':n,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,n in files],
          'summary_signals':['vinp','vinn','clk'],'expected_stop_s':2259e-9,'qualification_scope':'Recover known completed source; initial analysis never started due inherited coordinator hard limit',
          'spectre_args':['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],
          'resources':{'threads':4,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':32,'simulation_wall_seconds':3600,'analysis_wall_seconds':1200,'queue_timeout_seconds':86400}}
        recipe=R/'management/recipes'/(run+'.yaml');recipe.write_text(json.dumps(spec,indent=2)+'\n');print('REGISTER_BOUND',run,flush=True);print(json.dumps(execution.register(recipe.relative_to(R))),flush=True)
    paired=list(json.loads((V/'manifest_v2.json').read_text())['runs'])
    manifest={'recovery_runs':recover,'paired_runs':paired,'registered_hashes':{run:execution.project.load(R/'management/runs'/(run+'.yaml'))['recipe_hash'] for run in recover+paired},'agent_sha256':hashlib.sha256((R/'scripts/management/remote_agent.py').read_bytes()).hexdigest()}
    (V/'recovery_manifest_v2.json').write_text(json.dumps(manifest,indent=2)+'\n');files=[]
    for p,n in [(R/'scripts/sar8_mc/module_campaign_v2.py','managed_campaign.py'),(S/'recovery_flow.py','flow.py'),(V/'recovery_manifest_v2.json','manifest.json')]:
        b=p.read_bytes();files.append({'name':n,'sha256':hashlib.sha256(b).hexdigest(),'data':base64.b64encode(b).decode()})
    code='import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))'
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],input=json.dumps({'files':files}),text=True,capture_output=True,timeout=30);assert p.returncode==0,p.stderr
    (V/'launch_flow_v2.json').write_text(p.stdout,encoding='utf-8');print(p.stdout)
if __name__=='__main__':main()
