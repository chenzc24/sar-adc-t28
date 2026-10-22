"""One-shot local collector for an already-dispatched batch; never launches jobs."""
from datetime import datetime, timezone
import argparse
import contextlib
import os
import subprocess
import time
import traceback
from flow import ROOT, OUT, read, dump, status


def main():
    p=argparse.ArgumentParser();p.add_argument('--hours',type=float,default=24);a=p.parse_args()
    assert 0<a.hours<=48
    assert (OUT/'full_launch.json').exists()
    # Exclusive receipt prevents two collectors racing over immutable raw cases.
    with (OUT/'collector_started.json').open('x',encoding='utf-8') as f:
        import json
        json.dump(dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
                       limit_hours=a.hours),f,indent=2)
    with (OUT/'collector.log').open('x',encoding='utf-8') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        deadline=time.monotonic()+a.hours*3600;failures=0
        try:
            while time.monotonic()<deadline:
                try:
                    complete=status('full')
                    failures=0
                except Exception:
                    failures+=1;traceback.print_exc();log.flush()
                    if failures>=3:raise
                    time.sleep(60);continue
                states=read(OUT/'full_status.json')['cases']
                bad=[x for x in states if x['status'].startswith('EXIT ') and not x['completed']]
                if bad:raise RuntimeError(('Native case failed; preserved, no relaunch',bad))
                # Completed cases can be collected while other native jobs continue.
                status('full',collect=True)
                if complete:
                    subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),
                                    str(ROOT/'scripts/sar8_idle_performance/compare.py')],
                                   cwd=ROOT,stdout=log,stderr=log,check=True)
                    dump(OUT/'collector_finished.json',dict(status='complete_pending_visual_review',
                         utc=datetime.now(timezone.utc).isoformat()))
                    return
                log.flush();time.sleep(300)
            raise TimeoutError('Collector time budget expired; remote cases remain untouched')
        except Exception:
            traceback.print_exc()
            dump(OUT/'collector_finished.json',dict(status='needs_attention',utc=datetime.now(timezone.utc).isoformat()))
            dump(OUT/'flow_status.json',dict(stage='collector_needs_attention',log=str(OUT/'collector.log'),
                                           remote_jobs_not_stopped=True,no_relaunch=True))
            raise


if __name__=='__main__':main()
