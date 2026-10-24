"""Isolated native reference-length experiment; no OA or baseline writes."""
from pathlib import Path
import contextlib
import re
import shlex
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_main_width'))
import width_flow as wf
OUT=ROOT/'output/sar8_ref_length';VERIFY=ROOT/'verification/sar8_ref_length'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_length_20261024'
SOURCE=ROOT/'output/sar8_main_width/w2_ff_099_125_static'
PDK='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531'
wf.OUT=wf.base.OUT=OUT;wf.VERIFY=VERIFY;wf.REMOTE=wf.base.REMOTE=REMOTE
read,dump,sha=wf.read,wf.dump,wf.sha
OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)

def remote(command):
    return wf.base.command(wf.base.client(),command,timeout=45)

def native_collect(names):
    ssh=wf.base.client()
    for name in names:
        folder=OUT/name;dest=read(folder/'launch.json')['remote']
        assert wf.base.command(ssh,'cat '+shlex.quote(dest+'/exit_code')).strip()=='0'
        target=folder/'native';assert not target.exists();target.mkdir()
        for fn,rec in [('spectre.out',False),('test.raw',True)]:
            r=ssh.download(dest+'/'+fn,target/fn,recursive=rec,timeout=120);assert r.returncode==0,r.stderr
        h=wf.base.command(ssh,'sha256sum '+shlex.quote(dest+'/test.scs')).split()[0]
        assert h==sha(folder/'test.scs')
        dump(folder/'receipt.json',dict(native_exit=0,remote_deck_sha256=h,
            native_files={p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file()}))

if __name__=='__main__':
    action=sys.argv[1];names=sys.argv[2:]
    if action=='remote':print(remote(names[0]))
    elif action in ['status','preflight']:getattr(wf,action)()
    else:
        with (OUT/(action+'.log')).open('a') as f,contextlib.redirect_stdout(f):
            if action=='native_collect':native_collect(names)
            else:getattr(wf,action)(names)
        print(action,names)
