"""Bounded resume-safe dispatch/reduction/collection; preserve every original run."""
import contextlib
import subprocess
import time
from control import ROOT,OUT,VERIFY,read,wf,reduce

def main():
    names=read(VERIFY/'setup.json')['names'];initial=['null_ff_125','hold100_ff_125']
    for _ in range(90):
        with (OUT/'finish.log').open('a') as log,contextlib.redirect_stdout(log):
            status=wf.status();cases={x['name']:x for x in status['cases']}
            for row in cases.values():
                assert row['exit'] in ['', '0'],row
                assert row['reduce_exit'] in ['', '0'],row
            unlaunched=[n for n in names if not (OUT/n/'launch.json').exists()]
            if unlaunched and all(cases[n]['exit']=='0' for n in initial):wf.launch(unlaunched)
            pending=[n for n,row in cases.items() if (OUT/n/'reduction.json').exists() and row['reduce_exit']=='']
            ready=[n for n,row in cases.items() if row['exit']=='0' and not (OUT/n/'reduction.json').exists()]
            if ready and len(pending)<2:reduce(ready[:2-len(pending)])
            for n,row in cases.items():
                if row['reduce_exit']=='0' and not (OUT/n/'reduced_receipt.json').exists():wf.collect([n])
        for n in names:
            if (OUT/n/'reduced_receipt.json').exists() and not (VERIFY/(n+'_metrics.json')).exists():
                subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'scripts/sar8_ref_gate_controls/analyze.py'),n],check=True)
        done=[n for n in names if (VERIFY/(n+'_metrics.json')).exists()]
        print('Analyzed',len(done),'/',len(names),flush=True)
        if len(done)==len(names):return
        time.sleep(40)
    raise TimeoutError('Bounded wait expired; retain existing native work and resume from receipts')

if __name__=='__main__':main()
