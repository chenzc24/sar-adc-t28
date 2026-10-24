"""Focused evidence checks for read-only branch/timing attribution."""
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / 'verification/sar8_bottom_undershoot'
events = json.loads((VERIFY / 'events.json').read_text())
provenance = json.loads((VERIFY / 'provenance.json').read_text())
assert len(events) == 8 and len(provenance) == 4
checks = {}
for key, e in events.items():
    path = ROOT / 'output/sar8_bottom_undershoot' / (key + '.npz')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == e['cache_sha256']
    with np.load(path) as w:
        t = w['time'] * 1e9
        i = int(np.argmin(abs(t - e['bottom_min_ns'])))
        assert abs(t[i] - e['bottom_min_ns']) < 1e-9
        vb = w[e['bottom']][i]
        assert abs(vb * 1000 - e['bottom_min_mv']) < 1e-8
        assert abs(abs(w['vdd!'][i] - vb) - e['body_drain_abs_v']) < 1e-12
        assert abs(e['bottom_min_mv'] - e['reference_n_at_bottom_min_mv']
                   - e['local_bottom_minus_reference_at_min_mv']) < 1e-9
        a, b, p, z = (e[k] for k in ['n_gate_start99_ns', 'p_gate_start99_ns', 'bottom_min_ns', 'bottom_zero_ns'])
        assert a < b < p < z
        assert e['bottom_min_mv'] < e['before_p_bottom_mv'] < -20
        m = (t >= a) & (t <= p)
        assert max(abs(w['xdut.seq_sample'][m])) < .01
        assert e['other_bit_gate_max_range_v'] < .01
        if e['phase'] == 'idle':
            assert max(abs(w['xdut.xref.rst6'][m])) < .01
            assert min(w['xdut.xref.rst7'][m]) > .98
        else:
            assert max(abs(w['xdut.xref.rst7'][m])) < .01
        assert e['devices'][e['branch']+'.MN_LOW']['nodes'] == [e['bottom'], e['gate_n'], 'vrefn', '0']
        assert e['devices'][e['branch']+'.MP_HIGH']['nodes'] == [e['bottom'], e['gate_p'], 'vrefp', 'vdd!']
    checks[key] = dict(cache_hash=True, native_peak=True, terminal_equation=True,
                      voltage_identity=True, gate_order=True, sampling_off=True,
                      other_bits_no_full_transition=True, branch_mapping=True)
assert all(not p['reference_switch_currents_saved'] for p in provenance.values())
result = dict(ok=True, events=checks, source_hash_checks='Performed by analyze.py against context and receipt before extraction',
              reference_switch_currents_saved=False, new_simulations=0, circuit_modified=False,
              limitations=['No current-resolved charge apportionment', 'No accuracy-convergence rerun',
                           'Analysis is not SOA closure or a design fix'])
(VERIFY/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
print('PASS: 8 events, hashes, native peaks, terminal identities, gate order and mapping; no circuit changes.')
