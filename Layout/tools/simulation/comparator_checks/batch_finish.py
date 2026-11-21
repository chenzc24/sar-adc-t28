"""Finish many managed runs in parallel: request analysis only where the simulation is complete and the
analysis never started, then collect completed analyses. Never resubmits a simulation.

Usage: batch_finish.py RUN_ID ...   Loops until every run is collected or terminal.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
import time
from pathlib import Path

EXE = [sys.executable, 'tools/saradc/managed/execution.py']
TERMINAL = {'failed', 'interrupted', 'rejected', 'not_applicable', 'limit_exceeded'}
RUNS = Path('work/output/managed_execution/runs')


def call(*args):
    out = subprocess.run(EXE + list(args), capture_output=True, text=True, timeout=300)
    if out.returncode:
        raise RuntimeError(out.stderr[-300:])
    return json.loads(out.stdout)


def step(run_id):
    """Advance one run by at most one action; return its settled state or None while pending."""
    if (RUNS / run_id / 'collected/derived/result.json').is_file():
        return 'collected'
    try:
        state = call('run-status', run_id)
    except RuntimeError:
        return None
    sim = state.get('simulation', {}).get('status')
    ana = state.get('analysis', {}).get('status', 'not_started')
    if sim in TERMINAL:
        return 'simulation ' + sim
    if sim != 'complete':
        return None
    if ana in (None, 'not_started'):
        try:
            call('analyze', run_id, '--queue')
        except RuntimeError:
            pass
        return None
    if ana in TERMINAL:
        return 'analysis ' + ana
    if ana == 'complete':
        try:
            call('collect', run_id)
        except RuntimeError:
            return None
        return 'collected' if (RUNS / run_id / 'collected/derived/result.json').is_file() else None
    return None


pending = list(sys.argv[1:])
settled = {}
with ThreadPoolExecutor(8) as pool:
    while pending:
        results = dict(zip(pending, pool.map(step, pending)))
        for run_id, result in results.items():
            if result:
                settled[run_id] = result
                print(run_id, result, flush=True)
        pending = [r for r in pending if r not in settled]
        print('PENDING', len(pending), time.strftime('%H:%M:%S'), flush=True)
        if pending:
            time.sleep(60)
print('BATCH_DONE', json.dumps({k: sum(1 for v in settled.values() if v == k) for k in set(settled.values())}), flush=True)
