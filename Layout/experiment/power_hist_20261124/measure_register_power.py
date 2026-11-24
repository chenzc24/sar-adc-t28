"""Measure the output register at its own supply pin on a native readout replay."""
from __future__ import division

import argparse
import json
import math
import os
from collections import deque

from native_stream import samples


def register_trace(path, plan, stride=1):
    """Keep the eight Q bits, the physical clock and power at the register pin."""
    q = ['xout.q%d' % bit for bit in range(8)]
    previous = None
    edges = []
    for index, (t, row) in enumerate(samples(path)):
        local_supply = row['xout.dvdd_reg'] - row['vss_chip']
        current = (row['xout.dvdd_j'] - row['xout.dvdd_reg']) / plan['register_feed_ohm']
        power = local_supply * current
        tick = row['xout.ck_reg'] - row['vss_chip'] - .5 * local_supply
        if previous is not None and previous[1] <= 0 < tick:
            edges.append(previous[0] - previous[1] * (t-previous[0]) / (tick-previous[1]))
        previous = (t, tick)
        if local_supply <= 0 or any(math.isnan(x) or math.isinf(x) for x in (power, tick)):
            raise ValueError('Invalid register supply trace')
        if index % stride == 0:
            levels = [row[k] - row['vss_chip'] for k in q]
            code = None if any(.3*local_supply < x < .7*local_supply for x in levels) else sum(
                1 << i for i, x in enumerate(levels) if x >= .7*local_supply)
            yield t, power, code, list(edges)


def measure(rows, plan):
    pending = deque()
    for case in plan['cases']:
        for index, word in enumerate(case['codes']):
            t = (case['measure_begin_ns'] + 100*index) * 1e-9
            pending.append(dict(case=case['case'], index=index, code=word, begin_s=t, end_s=t+100e-9,
                                energy_J=0., duration_s=0., sample_s=t+10e-9))
    frames = list(pending)
    previous = None
    edges = []
    for t, power, code, edges in rows:
        if previous is not None:
            t0, p0 = previous
            if t <= t0:
                raise ValueError('Transient times out of order')
            while pending:
                frame = pending[0]
                a, b = max(t0, frame['begin_s']), min(t, frame['end_s'])
                if a < b:
                    u = ((a+b)/2-t0)/(t-t0)
                    frame['energy_J'] += (p0 + u*(power-p0))*(b-a)
                    frame['duration_s'] += b-a
                if 'q_read' not in frame and t >= frame['sample_s'] >= t0:
                    frame['q_read'] = code
                if t < frame['end_s']:
                    break
                pending.popleft()
        previous = (t,power)
    if previous is None or abs(previous[0] - plan['stop_ns']*1e-9) > 12e-12 or pending:
        raise ValueError('Transient does not cover the full measurement')
    for frame in frames:
        if abs(frame['duration_s'] - 100e-9) > 1e-12:
            raise ValueError('Truncated integration period')
        nearby = [e for e in edges if frame['begin_s'] < e < frame['sample_s']]
        frame['capture_edges_s'] = nearby
        frame['passed'] = len(nearby) == 1 and frame.get('q_read') == frame['code']
    out = {}
    for case in plan['cases']:
        key = case['case']
        selected = [f for f in frames if f['case'] == key]
        out[key] = dict(frames=selected, passed=all(f['passed'] for f in selected),
                        register_uW=1e6 * sum(f['energy_J'] for f in selected) / sum(f['duration_s'] for f in selected))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    with open(os.path.join(args.run_dir, 'inputs', 'replay.json')) as stream:
        plan = json.load(stream)
    path = os.path.join(args.run_dir, 'raw', 'tran_short.tran.tran')
    cases = measure(register_trace(path, plan), plan)
    coarse = measure(register_trace(path, plan, stride=2), plan)
    for key, result in cases.items():
        result['alternate_sample_uW'] = coarse[key]['register_uW']
        result['alternate_sample_pass'] = coarse[key]['passed']
    with open(os.path.join(args.output_dir, 'result.json'), 'w') as stream:
        json.dump(dict(plan=plan, cases=cases, passed=all(c['passed'] and c['alternate_sample_pass']
                                                       for c in cases.values())), stream, indent=2)


if __name__ == '__main__':
    main()
