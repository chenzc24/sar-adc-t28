"""Serial bounded A -> analyze -> inspect function -> B; no retries/adoption."""
import json,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def call(*args):
 r=subprocess.run([sys.executable,str(R/'scripts/management/project.py')]+list(args),cwd=R,capture_output=True,text=True,timeout=200)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return json.loads(r.stdout)
def wait(run,phase):
 previous=None
 while True:
  s=call('run-status',run);v=s.get(phase,{});state=v.get('status')
  if state!=previous:print(run,phase,state,flush=True);previous=state
  if state in ['complete','limit_exceeded']:return s
  if state not in ['running','queued','starting','waiting']:raise RuntimeError(json.dumps(v))
  time.sleep(20)
for mode in ['a','b']:
 run='manual8-sar-%s-tt-v5'%mode
 if mode=='b':
  call('register','management/recipes/'+run+'.yaml');call('submit',run,'--queue')
 s=wait(run,'simulation')
 if s['simulation']['status']=='limit_exceeded' and mode=='a' and s['simulation'].get('reason') in ['output_size_limit','wall_time_limit']:
  print(run,'old budget exhausted; preserve failure and use user-authorized 8 GiB / 1 h identical case',flush=True)
  call('collect',run);run='manual8-sar-a-tt-v6'
  call('register','management/recipes/'+run+'.yaml');call('submit',run,'--queue');s=wait(run,'simulation')
 if s['simulation']['status']!='complete':raise RuntimeError(json.dumps(s['simulation']))
 if s.get('analysis',{}).get('status')=='not_started':call('analyze',run,'--queue')
 s=wait(run,'analysis')
 if s['analysis']['status']!='complete':raise RuntimeError(json.dumps(s['analysis']))
 c=call('collect',run)
 p=R/c['local_path']/'derived/result.json'
 if not p.exists():p=R/c['local_path']/'result.json'
 result=json.loads(p.read_text())
 print(run,'functional_ok',result['functional_ok'],'electrical_screen_ok',result['electrical_screen_ok'],flush=True)
 if not result['functional_ok']:break
