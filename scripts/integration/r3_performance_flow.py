"""One-shot long-run continuation: validate smoke, run, then analyze locally."""
from __future__ import annotations
from datetime import datetime,timezone
import subprocess
import sys
import time

import r3_performance as run

BRIDGE_PY=run.ROOT.parents[1]/"virtuoso-bridge-lite/.venv/Scripts/python.exe"
PROJECT_PY=run.ROOT/".venv/Scripts/python.exe"
SMOKES=("static_128_129_smoke_v3","sine_4_k1_smoke_v3")
FULL=("sine_1024_k461","static_001_064","static_065_128","static_129_192","static_193_255")


def status(stage,**fields):
    run.dump("flow_status.json",dict(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat(),**fields))
    print(stage,fields,flush=True)


def main():
    assert not (run.OUT/"flow_status.json").exists(),"Existing flow; inspect rather than duplicate"
    try:
        status("waiting_for_measurement_smoke",cases=list(SMOKES))
        started=time.monotonic()
        while not all((run.OUT/f"runs/{n}_waveform.json").exists() for n in SMOKES):
            for name in SMOKES:
                p=run.OUT/f"runs/{name}_result.json"
                if p.exists():
                    r=run.r3.r1.read_json(p)
                    if not r["ok"]:raise RuntimeError(f"Smoke failed: {name}: {r['errors']}")
            if time.monotonic()-started>10800:raise TimeoutError("Smoke wait exceeded three hours")
            time.sleep(10)
        # Parser is a separate project-Python process, not the bridge's NumPy runtime.
        for action in ("pilot","smoke"):
            subprocess.run([str(PROJECT_PY),str(run.ROOT/"scripts/integration/r3_performance_analyze.py"),action],cwd=run.ROOT,check=True)
        subprocess.run([str(PROJECT_PY),"-m","unittest","verification.integration.test_r3_performance","-v"],cwd=run.ROOT,check=True)
        status("running_full_batch",cases=list(FULL),workers=4,threads_each=4,
               note="No performance metrics available until complete; no PVT/mismatch/transient noise")
        run.run(list(FULL),workers=4)
        for n in FULL:
            r=run.r3.r1.read_json(run.OUT/f"runs/{n}_result.json")
            if not r["ok"]:raise RuntimeError(f"Full case failed: {n}: {r['errors']}")
        status("analyzing_full_results")
        subprocess.run([str(PROJECT_PY),str(run.ROOT/"scripts/integration/r3_performance_analyze.py"),"full"],cwd=run.ROOT,check=True)
        status("complete",report="output/sar8_r3_performance/report.md",summary="output/sar8_r3_performance/summary.json")
    except Exception as exc:
        status("failed",error=str(exc))
        raise


if __name__=="__main__":main()
