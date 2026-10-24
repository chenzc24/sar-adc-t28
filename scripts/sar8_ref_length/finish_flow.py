"""Bounded recovery-safe collection; never launches a simulation or overwrites a case."""
import contextlib
import time
from control import OUT,VERIFY,read,wf

def main():
    names=read(VERIFY/'integrated_setup.json')['names']
    for _ in range(60):
        with (OUT/'finish_flow.log').open('a') as f,contextlib.redirect_stdout(f):
            status=wf.status();cases={r['name']:r for r in status['cases']}
            for name in names:
                row=cases[name];folder=OUT/name
                assert row['exit'] in ['', '0'],(name,row)
                assert row['reduce_exit'] in ['', '0'],(name,row)
                if row['exit']=='0' and not (folder/'reduction.json').exists():wf.reduce([name])
                if row['reduce_exit']=='0' and not (folder/'reduced_receipt.json').exists():wf.collect([name])
        done=[n for n in names if (OUT/n/'reduced_receipt.json').exists()]
        print('Collected',len(done),'of',len(names),flush=True)
        if len(done)==len(names):return
        time.sleep(45)
    raise TimeoutError('Bounded collection expired; remote jobs left intact')

if __name__=='__main__':main()
