"""Use project managed entry; retain uncertain/failed runs, never relaunch them."""
import json,subprocess,sys,time
from pathlib import Path
W=Path(__file__).resolve().parents[1];ROOT=W.parent
def call(*args):
    p=subprocess.run([sys.executable,str(ROOT/'scripts/management/project.py')]+list(args),cwd=str(ROOT),capture_output=True,text=True,timeout=200)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return json.loads(p.stdout)
for run in sys.argv[1:]:
    cfg=json.loads((W/'recipes'/(run+'.yaml')).read_text())
    analysis_only=cfg.get('kind')=='analysis_only'
    r=call('register',str(W/'recipes'/(run+'.yaml')))
    s=call('run-status',run)
    if not analysis_only and s.get('simulation',{}).get('status')=='not_started':call('submit',run,'--queue')
    for stage in (['analysis'] if analysis_only else ['simulation','analysis']):
        if stage=='analysis' and call('run-status',run).get(stage,{}).get('status')=='not_started':call('analyze',run,'--queue')
        while True:
            s=call('run-status',run);state=s[stage]['status'];print(run,stage,state,flush=True)
            if state=='complete':break
            if state in ['failed','cancelled','rejected','limit_exceeded','expired']:raise RuntimeError(str(s))
            time.sleep(15)
    receipt=call('collect',run)
    col=ROOT/'output/managed_execution/runs'/run/'collected'
    dest=W/'results'/run;dest.mkdir(parents=True,exist_ok=True)
    for src in [col/'derived/result.json',col/'spectre.out',col/'simulation.state.json',col/'analysis.state.json']:
        if src.exists():(dest/src.name).write_bytes(src.read_bytes())
    (dest/'evidence.json').write_text(json.dumps({'run_id':run,'collection':receipt,'source':str(col)},indent=2))
    print(run,'collected',receipt.get('bytes'),flush=True)
