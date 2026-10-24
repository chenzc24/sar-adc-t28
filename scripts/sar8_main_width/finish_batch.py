"""Bounded recovery of already-submitted cases; never submits simulations."""
import contextlib
import subprocess
import sys
import time
from width_flow import ROOT,OUT,VERIFY,status,reduce,collect

def main(names):
    deadline=time.monotonic()+3*3600
    while time.monotonic()<deadline:
        with (OUT/('recover_'+names[0]+'.log')).open('a') as f,contextlib.redirect_stdout(f):state=status()
        assert state['remote_bytes']<20*1024**3,'Storage gate: stop further recovery/dispatch; raw data preserved'
        rows={r['name']:r for r in state['cases']};done=0
        for name in names:
            if (VERIFY/(name+'.json')).exists():done+=1;continue
            r=rows[name]
            if r['exit']=='':continue
            assert r['exit']=='0',(name,r)
            if not (OUT/name/'reduction.json').exists():
                with (OUT/('recover_'+names[0]+'.log')).open('a') as f,contextlib.redirect_stdout(f):reduce([name])
                print('REDUCTION',name,flush=True);continue
            if r['reduce_exit']=='':continue
            assert r['reduce_exit']=='0',(name,r)
            if not (OUT/name/'reduced_receipt.json').exists():
                with (OUT/('recover_'+names[0]+'.log')).open('a') as f,contextlib.redirect_stdout(f):collect([name])
            subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'scripts/sar8_main_width/measure.py'),name],check=True,cwd=ROOT)
            done+=1
        print('RECOVERED',done,'/',len(names),'bytes',state['remote_bytes'],flush=True)
        if done==len(names):return
        time.sleep(30)
    print('Recovery wait expired; existing simulations left intact',flush=True)

if __name__=='__main__':main(sys.argv[1:])
