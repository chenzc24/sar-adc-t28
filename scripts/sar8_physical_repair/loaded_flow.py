"""One-shot continuation of named, already-submitted managed runs; no simulations."""
import argparse,json,subprocess,sys,time
from prepare import ROOT

def command(*args):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/management/project.py'),*args],
                          cwd=ROOT,text=True,capture_output=True,check=True)
    return json.loads(result.stdout)

def main():
    p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');a=p.parse_args()
    assert all(r.startswith('sar8fix-loaded-') for r in a.runs)
    done=set();last={}
    while len(done)<len(a.runs):
        for run in a.runs:
            if run in done:continue
            state=command('run-status',run)
            s=state['simulation']['status'];b=state['analysis']['status']
            key=(s,b)
            if last.get(run)!=key:print(run,s,b,flush=True);last[run]=key
            if s in ['failed','blocked','cancelled'] or b in ['failed','blocked','cancelled']:
                raise RuntimeError('Inspect existing run; do not resubmit: '+run+' '+str(key))
            if s=='complete' and b=='not_started':
                print(run,'request managed analysis',command('analyze',run,'--queue').get('accepted'),flush=True)
            elif s=='complete' and b=='complete':
                result=command('collect',run)
                assert not result['skipped'],result
                subprocess.run([sys.executable,str(ROOT/'scripts/sar8_physical_repair/loaded_analyze.py'),run],cwd=ROOT,check=True)
                done.add(run);print(run,'COLLECTED_AND_ANALYZED',flush=True)
        if len(done)<len(a.runs):time.sleep(30)
    print('NAMED_BATCH_COMPLETE',flush=True)

if __name__=='__main__':main()
