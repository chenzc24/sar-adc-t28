"""Native transport reuse with this task's isolated roots only."""
from pathlib import Path
import contextlib
import shlex
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_main_width'))
import width_flow as wf
OUT=ROOT/'output/sar8_ref_gate_controls';VERIFY=ROOT/'verification/sar8_ref_gate_controls'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_gate_controls_20261024'
wf.OUT=wf.base.OUT=OUT;wf.VERIFY=VERIFY;wf.REMOTE=wf.base.REMOTE=REMOTE
read,dump,sha=wf.read,wf.dump,wf.sha
OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)

def remote(cmd):return wf.base.command(wf.base.client(),cmd,timeout=45)

def reduce(names):
    ssh=wf.base.client()
    for name in names:
        folder=OUT/name;dest=read(folder/'launch.json')['remote'];ctx=read(folder/'context.json')
        assert wf.base.command(ssh,'cat '+shlex.quote(dest+'/exit_code')).strip()=='0'
        assert not (folder/'reduction.json').exists()
        # All original timing signals plus physical gates/bottoms/driver outputs
        # retained at every native point for settling and displaced peak checks.
        ctx['timing_signals']=[s for s in ctx['saved_signals'] if ':' not in s]
        dump(folder/'reduction_context.json',ctx)
        reducer=ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py'
        for src,fn in [(folder/'reduction_context.json','context.json'),(reducer,'reduce.py')]:
            result=ssh.upload(src,dest+'/'+fn,timeout=60);assert result.returncode==0,result.stderr
        cmd='cd '+shlex.quote(dest)+' && python reduce.py > reduce.log 2>&1; echo $? > '+shlex.quote(dest+'/reduce_exit')
        pid=wf.base.command(ssh,'nohup sh -c '+shlex.quote(cmd)+' > /dev/null 2>&1 < /dev/null & echo $!')
        dump(folder/'reduction.json',dict(remote=dest,pid=pid.strip(),reducer_sha256=sha(reducer)))

if __name__=='__main__':
    action=sys.argv[1];names=sys.argv[2:]
    if action=='remote':print(remote(names[0]))
    elif action in ['preflight','status']:getattr(wf,action)()
    else:
        with (OUT/(action+'.log')).open('a') as f,contextlib.redirect_stdout(f):
            if action=='reduce':reduce(names)
            else:getattr(wf,action)(names)
        print(action,names)
