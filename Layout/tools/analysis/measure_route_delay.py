"""Measure every top-level route of a completed route-check run (Python 2.7 on the host).

The route check (Layout/tools/simulation/prepare_all_extracted.py, route_check) places an RC ladder between the
real driver and receiver of each digital top-level net and saves both ends. For each route this analyzer pairs
every 50 % crossing at the driver end with the next same-direction 50 % crossing at the receiver end and reports
the delay, plus the 10-90 % transition at both ends. Supply-relative thresholds use the instantaneous vdd!.
"""
from __future__ import print_function, division
import argparse
import json
import os

import native_stream

LEVELS = (.1, .5, .9)
PAIR_WINDOW_S = 3e-9


def samples(path, ctx):
    alias = ctx.get('signal_aliases', {})
    for t, v in native_stream.samples(path):
        yield t, dict((alias.get(k, k), x) for k, x in v.items()) if alias else v


def transitions(crossings):
    """10-90 % durations: each 50 % crossing bounded by the nearest same-direction 10 % and 90 % crossings."""
    out = []
    for t50, up in crossings[.5]:
        first, last = (.1, .9) if up else (.9, .1)
        before = [t for t, u in crossings[first] if u == up and t <= t50]
        after = [t for t, u in crossings[last] if u == up and t >= t50]
        if before and after:
            out.append(after[0] - before[-1])
    return out


def stats(values):
    values = sorted(values)
    if not values:
        return None
    return dict(count=len(values), min_ps=values[0] * 1e12, median_ps=values[len(values) // 2] * 1e12,
                max_ps=values[-1] * 1e12)


def analyze(root, out):
    with open(root + '/inputs/context.json') as stream:
        ctx = json.load(stream)
    check = ctx['route_check']
    raw = [os.path.join(p, n) for p, _, files in os.walk(root + '/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    nets = {}
    for r in check['routes']:
        for end in ('driver', 'receiver'):
            nets[('xdut.' + r[end]).lower()] = dict((lvl, []) for lvl in LEVELS)
    prev = None
    for t, v in samples(raw[0], ctx):
        if prev is None:
            missing = set(nets) - set(v)
            if missing:
                raise ValueError('Missing route ends: ' + repr(sorted(missing)))
            prev = t, v
            continue
        pt, pv = prev
        for net, crossings in nets.items():
            for lvl in LEVELS:
                a, b = pv[net] - lvl * pv['vdd!'], v[net] - lvl * v['vdd!']
                if (a > 0) != (b > 0):
                    crossings[lvl].append((pt + (t - pt) * a / (a - b), b > a))
        prev = t, v
    if prev is None or prev[0] < ctx['expected_stop_s'] - 1e-12:
        raise ValueError('Incomplete transient')
    routes = []
    for r in check['routes']:
        drv, rcv = nets[('xdut.' + r['driver']).lower()], nets[('xdut.' + r['receiver']).lower()]
        delays, unpaired = {True: [], False: []}, 0
        for t, up in drv[.5]:
            nxt = [s for s, u in rcv[.5] if u == up and t <= s < t + PAIR_WINDOW_S]
            if nxt:
                delays[up].append(nxt[0] - t)
            else:
                unpaired += 1
        routes.append(dict(name=r['name'], driver=r['driver'], receiver=r['receiver'], length_um=r['length_um'],
                           r_ohm=r['r_ohm'], c_F=r['c_F'], driver_edges=len(drv[.5]), receiver_edges=len(rcv[.5]),
                           unpaired_driver_edges=unpaired, rise=stats(delays[True]), fall=stats(delays[False]),
                           max_delay_ps=max([x * 1e12 for x in delays[True] + delays[False]] or [None]),
                           driver_transition=stats(transitions(drv)), receiver_transition=stats(transitions(rcv))))
    group = lambda names: max(x['max_delay_ps'] for x in routes if x['name'] in names)
    result = dict(run_id=ctx['run_id'], corner=ctx['corner'], route_check=dict((k, v) for k, v in check.items()
                                                                                if k != 'routes'),
                  routes=routes, max_handshake_one_way_ps=group(('CMP_CLK', 'COMP_P', 'COMP_N')),
                  max_code_bus_ps=group(['CODE%d' % i for i in range(8)] + ['PRESET']),
                  method=__doc__.strip())
    with open(out + '/result.json', 'w') as stream:
        json.dump(result, stream, indent=2)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    analyze(a.source_run_dir or a.run_dir, a.output_dir)
