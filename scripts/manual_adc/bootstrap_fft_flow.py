"""Serial durable managed batch; stop on terminal failures, never duplicate."""
import json,subprocess,sys,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2]
O=R/'output/manual_adc/bootstrap_fft_v1'
O.mkdir(parents=True,exist_ok=True)
def call(*args):
    # Retry only read-only status transport failures; never replay mutations.
    for attempt in range(5 if args[0]=='run-status' else 1):
        p=subprocess.run([sys.executable,str(R/'scripts/management/project.py')]+list(args),cwd=str(R),capture_output=True,text=True,timeout=240)
        if not p.returncode:return json.loads(p.stdout)
        error=p.stdout+p.stderr
        transient=('ssh:' in error or 'Connection closed' in error or 'Remote result uncertain' in error)
        if args[0]!='run-status' or not transient or attempt==4:raise RuntimeError(error)
        record(stage='status_transport_retry',run_id=args[1],attempt=attempt+1,error=error)
        time.sleep(30)
def record(**kw):
    kw['epoch']=time.time();(O/'flow_status.json').write_text(json.dumps(kw,indent=2)+'\n');print(json.dumps(kw),flush=True)
def main():
    if (O/'pause.json').exists():
        record(stage='paused_by_user',reason='Unstarted cases stopped; do not resume without user authorization')
        return
    manifest=json.loads((R/'verification/manual_adc/bootstrap_fft_v1/manifest.json').read_text())
    jobs=[x for x in manifest['runs'] if not x['label'].startswith('pilot')]
    for run in jobs:
        name=run['run_id'];record(run_id=name,stage='register')
        call('register','management/recipes/'+name+'.yaml')
        for phase,command in [('simulation','submit'),('analysis','analyze')]:
            s=call('run-status',name)
            if s[phase]['status']=='not_started':call(command,name,'--queue')
            while True:
                s=call('run-status',name);st=s[phase]['status'];record(run_id=name,stage=phase,status=st,detail=s[phase])
                if st=='complete':break
                if st not in ['running','queued','starting','submitted','waiting']:raise RuntimeError('terminal/unknown status '+str(s))
                time.sleep(30)
        call('collect',name);record(run_id=name,stage='collected')
        subprocess.run([sys.executable,str(R/'scripts/manual_adc/bootstrap_fft_review.py')],cwd=str(R),check=True)
    record(stage='complete')
if __name__=='__main__':
    try:main()
    except Exception:
        record(stage='failed',error=traceback.format_exc());raise
