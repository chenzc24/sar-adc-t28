"""Deploy receipt plus a real Linux flock probe; no simulation or old-run edits."""
import base64,hashlib,json,shlex,subprocess,sys
from pathlib import Path
W=Path(__file__).resolve().parents[1];ROOT=W.parent
sys.path.insert(0,str(ROOT/'scripts/management'))
import execution
h=hashlib.sha256((ROOT/'scripts/management/remote_agent.py').read_bytes()).hexdigest()
code='''import imp,json,tempfile,fcntl,os
a=imp.load_source('slot_probe',%r)
p=a.policy();assert p['max_managed_workloads']==2
folder=tempfile.mkdtemp(prefix='slot_probe_',dir=a.ROOT+'/locks')
legacy=open(folder+'/workload.lock','a');fcntl.flock(legacy,fcntl.LOCK_EX|fcntl.LOCK_NB)
second,n=a.acquire_workload_slot(p,folder);assert n==1
third,k=a.acquire_workload_slot(p,folder);assert third is None and k is None
second.close();legacy.close()
first,n=a.acquire_workload_slot(p,folder);assert n==0;first.close()
print(json.dumps(dict(policy=p,legacy_slot0_plus_new_slot1=True,third_blocked=True,slot_reusable=True,probe_folder=folder,snapshot=a.snapshot())))
'''%(execution.REMOTE_ROOT+'/tools/agent_'+h+'.py')
encoded=base64.b64encode(code.encode()).decode()
cmd='python -c '+shlex.quote("import base64;exec(base64.b64decode('"+encoded+"'))")
r=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',cmd],capture_output=True,text=True,timeout=30)
if r.returncode:raise RuntimeError(r.stderr)
data=json.loads(r.stdout);dest=W/'results/concurrency';dest.mkdir(exist_ok=True)
(dest/'linux_slots.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data,indent=2))
