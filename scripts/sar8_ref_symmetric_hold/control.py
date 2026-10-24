"""Reuse audited native transport, rebinding all writable roots to this task."""
from pathlib import Path
import importlib.util
import sys
import contextlib
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('symmetric_transport',ROOT/'scripts/sar8_ref_gate_controls/control.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
OUT=ROOT/'output/sar8_ref_symmetric_hold';VERIFY=ROOT/'verification/sar8_ref_symmetric_hold'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_symmetric_hold_20261024'
OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)
transport.OUT=OUT;transport.VERIFY=VERIFY;transport.REMOTE=REMOTE
wf=transport.wf
wf.OUT=wf.base.OUT=OUT;wf.VERIFY=VERIFY;wf.REMOTE=wf.base.REMOTE=REMOTE
read,dump,sha,remote,reduce=transport.read,transport.dump,transport.sha,transport.remote,transport.reduce

if __name__=='__main__':
    action=sys.argv[1];names=sys.argv[2:]
    if action=='remote':print(remote(names[0]))
    elif action in ['preflight','status']:getattr(wf,action)()
    else:
        with (OUT/(action+'.log')).open('a') as log,contextlib.redirect_stdout(log):
            if action=='reduce':reduce(names)
            else:getattr(wf,action)(names)
        print(action,names)
