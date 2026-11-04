import sys,json,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def call(*args):
 r=subprocess.run([sys.executable,str(root/'scripts/management/project.py')]+list(args),cwd=str(root),capture_output=True,text=True,timeout=200)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return json.loads(r.stdout)
for run in sys.argv[1:]:
 s=call('run-status',run)
 if s.get('simulation',{}).get('status')=='not_started':call('submit',run,'--queue')
 while True:
  s=call('run-status',run);st=s['simulation']['status'];print(run,st,flush=True)
  if st=='complete':break
  if st in ['failed','cancelled']:raise RuntimeError(str(s))
  time.sleep(15)
 if s.get('analysis',{}).get('status')=='not_started':call('analyze',run,'--queue')
 while True:
  s=call('run-status',run);st=s['analysis']['status'];print(run,'analysis',st,flush=True)
  if st=='complete':break
  if st in ['failed','cancelled']:raise RuntimeError(str(s))
  time.sleep(10)
 r=call('collect',run);print(run,'collected',r.get('bytes'),flush=True)
