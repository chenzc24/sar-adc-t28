"""Bounded recovery of the two already submitted cases; never launches cases."""
import contextlib
import time
from control import OUT, NAMES, wf, dump, VERIFY

deadline = time.monotonic() + 1200
while time.monotonic() < deadline:
    with (OUT/'recovery_status.log').open('a') as log, contextlib.redirect_stdout(log):
        state = wf.status()
    rows = {x['name']: x for x in state['cases']}
    assert set(rows) == set(NAMES)
    assert state['remote_bytes'] < 5 * 1024**3
    for name, row in rows.items():
        assert row['exit'] in ['', '0'], (name, row)
        assert row['reduce_exit'] in ['', '0'], (name, row)
    if all(x['exit'] == '0' for x in rows.values()):
        pending = [n for n in NAMES if not (OUT/n/'reduction.json').exists()]
        if pending:
            with (OUT/'reduce.log').open('a') as log, contextlib.redirect_stdout(log):
                wf.reduce(pending)
            print('Native complete; reduction started', pending, flush=True)
    if all(x['reduce_exit'] == '0' for x in rows.values()):
        pending = [n for n in NAMES if not (OUT/n/'reduced_receipt.json').exists()]
        if pending:
            with (OUT/'collect.log').open('a') as log, contextlib.redirect_stdout(log):
                wf.collect(pending)
        dump(VERIFY/'recovery.json', dict(complete=True, cases=NAMES, raw_deleted=False))
        print('RECOVERED', NAMES, flush=True)
        break
    time.sleep(30)
else:
    raise TimeoutError('Bounded recovery ended; native background cases preserved')
