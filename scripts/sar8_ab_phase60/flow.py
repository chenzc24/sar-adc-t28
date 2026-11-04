"""Finite serial managed A/B flow. Preserve failures; never retry uncertain calls."""
import json,os,subprocess,sys,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2]
O=R/'output/sar8_ab_phase60';V=R/'verification/sar8_ab_phase60'
def state(**d):
    d.update(pid=os.getpid(),epoch=time.time());p=O/'flow_status.json';q=p.with_suffix('.tmp')
    q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p);print(json.dumps(d),flush=True)
def call(*args):
    p=subprocess.run([sys.executable,str(R/'scripts/management/project.py')]+list(args),cwd=str(R),capture_output=True,text=True,timeout=240)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return json.loads(p.stdout)
def main():
    O.mkdir(exist_ok=True,parents=True)
    with (O/'flow.lock').open('x') as f:f.write(str(os.getpid()))
    runs=json.loads((V/'batch.json').read_text())['runs']
    for label,run in zip(['a','b'],runs):
        if not (R/'management/runs'/(run+'.yaml')).exists():call('register','management/recipes/'+run+'.yaml')
        for phase,cmd in [('simulation','submit'),('analysis','analyze')]:
            s=call('run-status',run)
            if s[phase]['status']=='not_started':call(cmd,run,'--queue')
            while True:
                s=call('run-status',run);st=s[phase]['status'];state(run_id=run,stage=phase,status=st,detail=s[phase])
                if st=='complete':break
                if st not in ['running','queued','starting','submitted','waiting']:raise RuntimeError('Terminal/uncertain state: '+str(s))
                time.sleep(30)
        c=call('collect',run);assert not c.get('skipped')
        for name in ['result.json','timeline.csv']:
            dest=V/label/name;data=(R/c['local_path']/'derived'/name).read_bytes()
            if dest.exists():assert dest.read_bytes()==data
            else:dest.write_bytes(data)
        result=json.loads((V/label/'result.json').read_text())
        state(stage='collected',run_id=run,steady_code_pass=result['steady_code_pass'],steady_timing_pass=result['steady_timing_pass'])
    subprocess.run([sys.executable,str(R/'scripts/sar8_ab_phase60/review.py')],cwd=str(R),check=True)
    state(stage='complete_pending_visual_review',result='verification/sar8_ab_phase60/README.md')
if __name__=='__main__':
    try:main()
    except Exception:state(stage='failed',error=traceback.format_exc());raise
