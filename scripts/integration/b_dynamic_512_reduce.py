"""Lossless PSF stream -> bounded full-frame electrical measurements."""
from __future__ import annotations
from array import array
import argparse
import gzip
import hashlib
import io
import itertools
import math
from pathlib import Path
import pickle
import re
import time
import numpy as np

import b_dynamic_512 as flow
from b_short_acceptance_analyze import energy, integral
from r3_anomaly_analyze import edges, monitor, reported_parameters
from r3_refgate_analyze import state_rows

Q = 1.8 / 256


def frame_stream(stream, frame_ns=100):
    """Same TRACE/delta semantics as verified short parser; never hold a run."""
    traces, groups = [], {}
    section, group, depth = None, None, 0
    for line in stream:
        s = line.strip()
        if s in ('HEADER', 'TYPE', 'SWEEP', 'TRACE', 'VALUE'):
            section = s
            if s == 'VALUE': break
            continue
        if section != 'TRACE': continue
        if depth:
            depth += s.count('(') - s.count(')'); continue
        m = re.match(r'"([^"]+)"\s+(.*)', s)
        if not m: continue
        if m[2].startswith('GROUP'): group = m[1]
        elif m[2].startswith('"'):
            traces.append(m[1])
            if group is not None: groups[group] = m[1]
            group = None
        if 'PROP(' in s: depth = s.count('(') - s.count(')')
    assert section == 'VALUE' and traces and len(set(traces)) == len(traces)
    keys = ['time'] + [s.replace('\\', '').lower() for s in traces]
    positions = {k: i for i, k in enumerate(traces)}
    current, values, previous = None, [math.nan] * len(traces), -1.
    buffers = [array('d') for _ in keys]
    frame = 0
    def append_point():
        nonlocal previous
        assert current > previous and all(map(math.isfinite, values))
        previous = current
        buffers[0].append(current)
        for dest, value in zip(buffers[1:], values): dest.append(value)
    def chunk_ready(eof=False):
        if not buffers[0]: return False
        delta_ns = buffers[0][-1] * 1e9 - (frame + 1) * frame_ns
        # Never flush before a boundary during streaming: sub-fs native points
        # can exist just before stop. Only EOF may tolerate roundoff at stop.
        return delta_ns >= 0 or (eof and abs(delta_ns) < 1e-5)
    ended = False
    for line in stream:
        s = line.strip()
        if not s: continue
        if s == 'END':
            append_point(); ended = True
            if chunk_ready(eof=True):
                yield frame, {k: np.asarray(v) for k, v in zip(keys, buffers)}
                frame += 1
            break
        assert s.startswith('"'), s[:80]
        end = s.index('"', 1)
        key, value = s[1:end], float(s[end + 1:])
        if key == 'time':
            if current is not None:
                append_point()
                if chunk_ready():
                    yield frame, {k: np.asarray(v) for k, v in zip(keys, buffers)}
                    buffers = [array('d', v[-2:]) for v in buffers]
                    frame += 1
            current = value
        else: values[positions[groups.get(key, key)]] = value
    assert ended
    for trailing in stream: assert not trailing.strip(), 'Unexpected payload after END'


def measure_frame(f, w, ctx, measurement):
    t = w['time'] * 1e9
    start, end = f * 100, (f + 1) * 100
    assert t[0] <= start + 1e-6 and t[-1] >= end - 1e-6
    node = lambda n: np.zeros_like(t) if n == '0' else w[n.lower()]
    at = lambda n, ns: float(np.interp(ns, t, node(n)))
    word = lambda ns: sum(int(at(f'D{b}', ns) > .45) << b for b in range(8))
    falls = edges(t, node('SAMPLE'), rising=False)
    falls = falls[(falls >= start) & (falls < end)]
    assert len(falls) == 1 and abs(falls[0] - start - 41.05) < 1e-5
    h = float(falls[0])
    source = at('VINP_SRC', h) - at('VINN_SRC', h)
    held = at('TOPP', h + .6) - at('TOPN', h + .6)
    event = {}
    for n in ('cmp_clk', 'xdut.xctrl.phi_w', 'xdut.xctrl.phi_u'):
        es = edges(t, node(n)); event[n] = es[(es >= start) & (es < end)]
    cs, ws, us = event.values()
    count_ok = len(cs) == len(ws) == len(us) == 8
    order_ok = bool(count_ok and np.all(cs < ws) and np.all(ws < us) and np.all(us[:-1] < cs[1:]) and h < cs[0])
    comparisons = []
    for i, c in enumerate(cs):
        ns = c - .02
        token = sum(int(at(f'XDUT.XCTRL.T{b}', ns) > .45) << b for b in range(8))
        trial = word(ns) | token
        actual = at('TOPP', ns) - at('TOPN', ns)
        expected = held + .9 - trial * Q
        comparisons.append(dict(compare_ns=float(c), token=token, trial=trial,
            settling_vs_held_lsb=(actual - expected) / Q))
    bit_ok = len(comparisons) == 8 and all(r['token'] == (128 >> i) for i, r in enumerate(comparisons))
    mid_fail, overlaps = [], []
    mid_error = 0.
    for s in 'PN':
        for b in range(8):
            high = (s == 'P' and b < 7) or (s == 'N' and b == 7)
            rail = 'VREFP' if high else 'VREFN'
            mid_error = max(mid_error, abs(at(f'XDUT.XCDAC.B{s}{b}', h - .1) - at(rail, h - .1)))
            for pol in 'PN':
                key = f'XDUT.G{s}{pol}{b}'
                if abs(at(key, h - .1) - .9 * (1 - high)) > .09: mid_fail.append(key)
            if np.any((node(f'XDUT.G{s}P{b}') < .45) & (node(f'XDUT.G{s}N{b}') > .45)):
                overlaps.append(f'{s}{b}')
    rails = max(min(abs(at(f'D{b}', ns)), abs(at(f'D{b}', ns) - .9))
                for ns in (start + 90, start + 98) for b in range(8))
    completion = float(us[-1] - h) if len(us) else None
    code = word(start + 98)
    ideal = lambda v: max(0, min(255, math.floor((v + .9) / Q)))
    frame = dict(frame=f, observed=f >= 4, sample_ns=h, read_ns=start + 98,
        source_v=source, held_v=held, raw_held_error_mv=(held - source) * 1000,
        code=code, ideal_source_code=ideal(source), ideal_held_code=ideal(held),
        code_minus_held_ideal=code - ideal(held), decoded_midbin_v=(code + .5) * Q - .9,
        counts={n: len(v) for n, v in event.items()}, event_order_pass=order_ok,
        bit_order_pass=bit_ok, events_ns={n: list(map(float, v)) for n, v in event.items()},
        completion_after_hold_ns=completion, held_before_first_compare=bool(len(cs) and h + .6 < cs[0]),
        monitor_valid=measurement['valid'], output_stable=measurement['early'] == code == word(start + 90),
        output_rail_error_v=rails, midpoint_gate_failures=mid_fail,
        midpoint_error_lsb=mid_error / Q, overlap_banks=overlaps, comparisons=comparisons,
        precompare_settling_vs_held_peak_lsb=max((abs(r['settling_vs_held_lsb']) for r in comparisons), default=0))
    assert code == measurement['code']
    frame['functional_pass'] = bool(count_ok and order_ok and bit_ok and completion is not None and completion < 60
        and frame['held_before_first_compare'] and frame['monitor_valid'] and frame['output_stable']
        and rails < .09 and not mid_fail and mid_error < .25 * Q and not overlaps)
    stress = []
    mask = (t >= start) & (t <= end)
    candidates = np.flatnonzero(mask)
    for dev in ctx['analog_devices']:
        terminals = dict(zip('DGSB', dev['nodes']))
        pairs = []
        for a, b in itertools.combinations('DGSB', 2):
            v = node(terminals[a]) - node(terminals[b])
            j = int(candidates[np.argmax(abs(v[mask]))])
            pairs.append(dict(pair=f'V{a}{b}', peak_v=float(abs(v[j])), signed_v=float(v[j]), time_ns=float(t[j])))
        stress.append(dict(path=dev['path'], category=dev['category'], pairs=pairs))
    powers, currents = {}, {}
    def add(group, inst, pin, index, voltage):
        key = next((k.lower() for k in (inst + ':' + pin, inst + ':' + str(index)) if k.lower() in w), None)
        assert key, (inst, pin)
        v = node(voltage); current = w[key]
        powers[group] = powers.get(group, np.zeros_like(t)) - v * current
        currents[key] = dict(peak_abs_a=float(max(abs(current[mask]))), integral_a_ns=integral(t, current, start, end))
    for group, inst, voltage in [('VDD', 'VVDD', 'VDD!'), ('reference', 'VREFHIGH', 'VREFP_SRC'),
        ('reference', 'VREFLOW', 'VREFN_SRC'), ('SAMPLE_ideal_clock', 'VSAMPLE', 'SAMPLE')]:
        add(group, inst, 'p', 1, voltage)
    for s in 'PN':
        add('input_sources', 'VVIN' + s, 'p', 1, 'VIN' + s + '_SRC')
        for b in range(8):
            for pin, index in [('GP', 6), ('GN', 7)]: add('reference_gate_ideal_outputs', f'XDUT.XG{s}{b}', pin, index, f'XDUT.G{s}{pin[1]}{b}')
    p_rows = {}
    for group, p in powers.items():
        full = energy(t, p, start, end)
        acq, conv = energy(t, p, start + 1.05, h), energy(t, p, h, start + 98)
        p_rows[group] = dict(**full, acquisition_net_pj=acq['net_delivered_pj'], conversion_net_pj=conv['net_delivered_pj'],
            other_net_pj=full['net_delivered_pj'] - acq['net_delivered_pj'] - conv['net_delivered_pj'])
    assert len(currents) == 38
    return frame, stress, p_rows, currents


class HashedRaw(io.RawIOBase):
    def __init__(self, source): self.source, self.digest = source, hashlib.sha256()
    def readable(self): return True
    def readinto(self, data):
        count = self.source.readinto(data)
        if count: self.digest.update(memoryview(data)[:count])
        return count


def reduce():
    flow.check()
    ctx = flow.read(flow.OUT / 'context.json')
    result = flow.read(flow.OUT / 'result.json')
    receipt = flow.read(flow.OUT / 'raw_receipt.json')
    log = (flow.OUT / 'spectre/spectre.out').read_text(errors='replace')
    if not result['ok']:
        # Preserve failed execution status; only a complete recovered dataset
        # is eligible for conditional analysis, never a partial gzip.
        from b_dynamic_512_recover import complete_gate
        assert result.get('recovery_capture_complete') and result['metadata']['original_transport_failed']
        assert result['metadata']['native_os_exit_status'] is None
        complete_gate(dict(native_processes=[], clear_anomaly_reasons=[]), log)
    assert flow.sha(receipt['local_gzip']) == receipt['gzip_sha256']
    measurements = monitor(log)
    probes = re.findall(r'BSINE,(\d+),([^\s,]+),([^\s,]+),([^\s,]+)', log)
    assert len(measurements) == len(probes) == 516
    params = reported_parameters(log)
    baseline = flow.read(flow.ROOT / 'verification/integration/b_sine_period_results.json')['reported_solver_parameters']
    assert params == baseline, {k: (v, params.get(k)) for k, v in baseline.items() if params.get(k) != v}
    frames, stress, power, currents = [], {}, {}, {}
    worst_completion, points = -1., 0
    first_time, last_time = None, -1.
    started = time.monotonic()
    with gzip.open(receipt['local_gzip'], 'rb') as compressed:
        hashed = HashedRaw(compressed)
        with io.TextIOWrapper(io.BufferedReader(hashed, buffer_size=2**20), encoding='utf-8', newline='') as stream:
            for f, w in frame_stream(stream):
                assert f == len(frames) and all(np.isfinite(a).all() for a in w.values())
                t = w['time']
                new = t > last_time
                points += int(np.count_nonzero(new)); last_time = float(t[-1])
                if first_time is None: first_time = float(t[0])
                assert np.all(np.diff(t) > 0)
                m = measurements[f]
                assert m['frame'] == f
                row, local_stress, local_power, local_currents = measure_frame(f, w, ctx, m)
                source = ctx['differential_peak_v'] * math.sin(2 * math.pi * ctx['config']['input_frequency_hz'] * row['sample_ns'] * 1e-9 - .4 * math.pi)
                assert abs(source - row['source_v']) < 5e-7
                pp = probes[f]
                assert int(pp[0]) == f and max(abs(float(v) - actual) for v, actual in zip(pp[1:],
                    [row['source_v'], row['held_v'], row['held_v'] - row['source_v']])) < 5e-7
                frames.append(row)
                for item in local_stress:
                    stored = stress.setdefault(item['path'], dict(path=item['path'], category=item['category'], pairs={}))
                    for pair in item['pairs']:
                        if pair['peak_v'] > stored['pairs'].get(pair['pair'], dict(peak_v=-1))['peak_v']:
                            stored['pairs'][pair['pair']] = pair
                for key, values in local_power.items(): power.setdefault(key, []).append(dict(frame=f, **values))
                for key, value in local_currents.items():
                    stored = currents.setdefault(key, dict(peak_abs_a=0., observed_integral_a_ns=0.))
                    stored['peak_abs_a'] = max(stored['peak_abs_a'], value['peak_abs_a'])
                    if f >= 4: stored['observed_integral_a_ns'] += value['integral_a_ns']
                if f == 4:
                    with (flow.OUT / 'detail_first.pickle').open('wb') as dest: pickle.dump(dict(frame=f, wave=w), dest, protocol=5)
                if f >= 4 and row['completion_after_hold_ns'] is not None and row['completion_after_hold_ns'] > worst_completion:
                    with (flow.OUT / 'detail_slowest.pickle').open('wb') as dest: pickle.dump(dict(frame=f, wave=w), dest, protocol=5)
                    worst_completion = row['completion_after_hold_ns']
                flow.dump(flow.OUT / 'reduce_progress.json', dict(frames=f + 1, total_frames=516, points=points,
                    elapsed_s=time.monotonic() - started, functional_failures=[r['frame'] for r in frames if not r['functional_pass']]))
            # frame_stream consumes through EOF; hash is over exact uncompressed bytes.
        digest = hashed.digest.hexdigest()
    assert len(frames) == 516 and first_time == 0 and abs(last_time * 1e9 - 51600) < 1e-5
    assert digest == receipt['raw_sha256'], 'Lossless decompression hash differs'
    for item in stress.values():
        item['pairs'] = list(item['pairs'].values())
        item['worst'] = max(item['pairs'], key=lambda r: r['peak_v'])
        item['screen_v'] = 1.98 if item['category'] == 'bootstrap_io' else .99
        item['screen_pass'] = item['worst']['peak_v'] <= item['screen_v']
    power_summary = {}
    def aggregate(records):
        fields = ['net_delivered_pj', 'positive_delivered_pj', 'recovered_pj', 'acquisition_net_pj', 'conversion_net_pj', 'other_net_pj']
        values = {k: sum(r[k] for r in records) for k in fields}
        values['average_net_mw'] = values['net_delivered_pj'] / (len(records) * 100)
        return values
    for group, rows in power.items():
        power_summary[group] = dict(frames=rows, startup_first_frame=rows[0], warmup=aggregate(rows[:4]), observed=aggregate(rows[4:]))
    for value in currents.values(): value['observed_mean_a'] = value.pop('observed_integral_a_ns') / 51200
    flow.dump(flow.OUT / 'reduced.json', dict(frames=frames, stress=list(stress.values()), power=power_summary,
        current_stats=currents, native_result_ok=result['ok'], execution_provenance=result.get('metadata', {}), reported_solver_parameters=params,
        native_warnings=[s.strip() for s in log.splitlines() if 'WARNING (' in s],
        initial_DC_notices=[s.strip() for s in log.splitlines() if any(k in s for k in ('GminDC =', 'dV(TOP', 'Bad pivoting'))],
        phase_events=len(state_rows(log, 'R3PHASE')), restore_events=len(state_rows(log, 'R3RESTORE')),
        native_footer=next(s for s in log.splitlines() if s.startswith('spectre completes with')),
        has_CMI='CMI-2754' in log, has_LTE='SPECTRE-16780' in log, points=points,
        raw_sha256=digest, gzip_sha256=receipt['gzip_sha256'], full_continuous_data_retained=True,
        reducer_LF_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        reduction_elapsed_s=time.monotonic() - started, logic_all_terminal_coverage=False))
    print('FULL_516_FRAME_LOSSLESS_REDUCTION_PASS', flush=True)


def self_check():
    import b_short_acceptance as old
    import io
    raw = next((old.OUT / 'history12/spectre').rglob('*.tran.tran'))
    prefix, count = [], 0
    with raw.open() as src:
        for line in src:
            if line.startswith('"time" ') and 'VALUE\n' in prefix:
                count += 1
                if count == 2049: break
            prefix.append(line)
    text = ''.join(prefix) + 'END\n'
    expected = old.stream_psf(io.StringIO(text))
    chunks = list(frame_stream(io.StringIO(text), frame_ns=float(expected['time'][-1]) * 1e9))
    assert len(chunks) == 1
    actual = chunks[0][1]
    assert actual.keys() == {k.lower() for k in expected}
    for key, values in expected.items(): np.testing.assert_array_equal(actual[key.lower()], values)
    # Independent numerical cross-check against the already-completed short run.
    ctx = old.read(old.OUT / 'context.json')
    with (old.OUT / 'directed_a16/waveform.pickle').open('rb') as src: w = pickle.load(src)
    w = {k: np.asarray(v) for k, v in w.items()}
    mask = w['time'] * 1e9 <= 100.1
    first = {k: v[mask] for k, v in w.items()}
    m = monitor((old.OUT / 'directed_a16/spectre/spectre.out').read_text())[0]
    frame, stress, power, currents = measure_frame(0, first, ctx, m)
    prior = old.read(old.OUT / 'directed_a16/analysis.json')
    assert frame['functional_pass'] and frame['code'] == prior['all_codes'][0]
    for key, value in power.items():
        for field in ('net_delivered_pj', 'positive_delivered_pj', 'recovered_pj'):
            assert abs(value[field] - prior['power'][key]['frames'][0][field]) < 1e-7
    assert len(stress) == 67 and len(currents) == 38
    for f in (4, 8, 15):
        take = (w['time'] * 1e9 >= f * 100 - .1) & (w['time'] * 1e9 <= (f + 1) * 100 + .1)
        part = {k: v[take] for k, v in w.items()}
        measurement = monitor((old.OUT / 'directed_a16/spectre/spectre.out').read_text())[f]
        new, _, energy_rows, _ = measure_frame(f, part, ctx, measurement)
        previous = prior['frames'][f]
        assert new['functional_pass'] and new['code'] == previous['code']
        assert abs(new['held_v'] - previous['held_v']) < 1e-12
        for key, values in energy_rows.items():
            for field in ('net_delivered_pj', 'positive_delivered_pj', 'recovered_pj'):
                assert abs(values[field] - prior['power'][key]['frames'][f][field]) < 1e-7
        for a, b in zip(new['comparisons'], previous['comparisons']):
            assert abs(a['settling_vs_held_lsb'] - (b['settling_error_lsb'] - previous['held_error_lsb'])) < 1e-10
    # Arbitrary boundary crossing, exact delta carry-forward and trailing hash.
    synthetic = 'SWEEP\n"time" "sweep"\nTRACE\n"v" "V"\nVALUE\n"time" 0\n"v" 1\n"time" 99e-9\n"v" 2\n"time" 101e-9\n"v" 3\n"time" 200e-9\n"v" 4\nEND\n'
    parts = list(frame_stream(io.StringIO(synthetic)))
    assert [i for i, _ in parts] == [0, 1]
    close_boundary = synthetic.replace('99e-9', '99.9999999e-9').replace('101e-9', '100e-9')
    close_boundary = close_boundary.replace('"time" 200e-9', '"time" 199.9999999e-9\n"v" 3.5\n"time" 200e-9')
    parts = list(frame_stream(io.StringIO(close_boundary)))
    unique_times = np.unique(np.concatenate([w['time'] for _, w in parts]))
    assert len(parts) == 2 and len(unique_times) == 5 and abs(unique_times[-1] * 1e9 - 200) < 1e-8
    roundoff_end = close_boundary.replace('"time" 200e-9', '"time" 199.99999999e-9')
    parts = list(frame_stream(io.StringIO(roundoff_end)))
    assert len(parts) == 2 and len(np.unique(np.concatenate([w['time'] for _, w in parts]))) == 5
    packed = gzip.compress(synthetic.encode())
    hashed = HashedRaw(gzip.GzipFile(fileobj=io.BytesIO(packed)))
    with io.TextIOWrapper(io.BufferedReader(hashed)) as src: list(frame_stream(src))
    assert hashed.digest.hexdigest() == hashlib.sha256(synthetic.encode()).hexdigest()
    print('STREAM_CHUNK_BOUNDARY_CURRENT_PROP_RAW_HASH_AND_NATIVE_POWER_EQUIVALENCE_PASS')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--self-check', action='store_true')
    self_check() if ap.parse_args().self_check else reduce()
