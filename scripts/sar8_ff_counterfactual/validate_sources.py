"""Validate isolated controls locally and exact dispatched bytes over SSH."""
import contextlib
import re
import shlex
from control import OUT, VERIFY, SOURCE, NAMES, read, dump, sha, wf

original = (SOURCE/'test.scs').read_text()
dut = (SOURCE/'dut.scs').read_text()
baseline = read(SOURCE/'context.json')
assert sha(SOURCE/'test.scs') == baseline['deck_sha256']
assert sha(SOURCE/'dut.scs') == baseline['DUT_sha256']
assert sha(SOURCE/'r4_perf_monitor.va') == baseline['monitor_sha256']
expected = {}
for name in NAMES:
    folder = OUT/name; ctx = read(folder/'context.json')
    text = (folder/'test.scs').read_text()
    newdut = (folder/'dut.scs').read_text()
    if name == 'ffhot_rref1':
        for side in ['P', 'N']:
            a = f'RREF{side} (VREF{side}_SRC VREF{side}) resistor r=1'
            assert text.count(a) == 1
            text = text.replace(a, a.replace('r=1', 'r=50'), 1)
        assert newdut == dut
    else:
        cell = re.search(r'(?ms)^subckt sar8p_delay_quiet .*?^ends sar8p_delay_quiet', dut)[0]
        changed = cell.replace('multi=30', 'multi=60')
        assert text.count(changed) == newdut.count(changed) == 1
        text = text.replace(changed, cell, 1)
        assert newdut.replace(changed, cell, 1) == dut
    assert text == original
    assert sha(folder/'test.scs') == ctx['deck_sha256']
    assert sha(folder/'dut.scs') == ctx['DUT_sha256']
    remote = read(folder/'launch.json')['remote']
    for file in ['test.scs', 'r4_perf_monitor.va']:
        expected[remote+'/'+file] = sha(folder/file)
    assert sha(folder/'r4_perf_monitor.va') == baseline['monitor_sha256']
with (OUT/'source_validation.log').open('w') as log, contextlib.redirect_stdout(log):
    ssh = wf.base.client()
    hashes = wf.base.command(ssh, 'sha256sum '+' '.join(shlex.quote(p) for p in expected))
actual = {s.split(None, 1)[1].strip(): s.split()[0] for s in hashes.splitlines()}
assert actual == expected
dump(VERIFY/'source_validation.json', dict(exact_inverse_controls=True,
     original_unchanged=True, monitor_unchanged=True, remote_decks_match=True,
     dispatched_sha256=actual, OA_changed=False))
print('SOURCE VALIDATION PASS')
