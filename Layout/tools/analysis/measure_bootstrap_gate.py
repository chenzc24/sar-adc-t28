"""Main-switch gate discharge of both Bootstrap channels after every sample close (Python 2.7 on the host).

Analysis-only job on a completed single_edge_lpe run. The Bootstrap clock is SEQ_SAMPLE; its falling 50 %
crossing opens the hold phase, in which the gate G of the main switch discharges through Maux (gate at VDD)
and MRSTG (gate CLKSB) to VSS. The run saves G at one main-switch gate contact (bootstrap_gate_probe for an
extraction). For each frame and channel this analyzer reports, relative to the close edge:
  - the boosted gate before close (g - vin, 0.5 ns before the edge) and G at the edge;
  - the onset of discharge (G 50 mV below its value at the edge) and the fastest fall rate;
  - the overdrive g - min(vin, top), the quantity single_edge_lpe screens at the first comparator clock,
    at that clock and at fixed delays, and the times at which it falls below fixed levels;
  - the overdrive just before the next tracking phase opens (the settled hold level).
gate_excerpt.csv keeps the native points of the first EXCERPT_S after every close, at least EXCERPT_STEP_S apart.
"""
from __future__ import print_function, division
import argparse
import collections
import csv
import json
import os

import native_stream

CLOCK, CMP = 'xdut.seq_sample', 'xdut.cmp_clk'
SIDES = 'pn'
BEFORE_S = .5e-9
ONSET_V = .05
LEVELS_V = (.4, .3, .2, .1, .05, 0.)
DELAYS_S = (.5e-9, 1e-9, 1.3e-9, 2e-9, 3e-9, 5e-9, 8e-9)
EXCERPT_S = 8e-9
EXCERPT_STEP_S = 10e-12


def samples(path, ctx, needed):
    """Native points reduced to the needed signals (aliased to the analyzer names)."""
    alias = ctx.get('signal_aliases', {})
    names = None
    for t, v in native_stream.samples(path):
        if names is None:
            names = dict((k, alias.get(k, k)) for k in v if alias.get(k, k) in needed)
            missing = set(needed) - set(names.values())
            if missing:
                raise ValueError('Missing signals: ' + repr(sorted(missing)))
        yield t, dict((n, v[k]) for k, n in names.items())


def lerp(pt, pv, t, v, when):
    f = (when - pt) / (t - pt)
    return dict((k, pv[k] + f * (v[k] - pv[k])) for k in v)


def overdrive(v, s):
    return v['xdut.xboot%s.g' % s] - min(v['vin' + s], v['xdut.top' + s])


def start(close, v, history):
    """State of one hold phase that opens at `close` (v interpolated at the edge)."""
    before = [h for h in history if h[0] <= close - BEFORE_S]
    ref = before[-1][1] if before else None
    sides = {}
    for s in SIDES:
        g = v['xdut.xboot%s.g' % s]
        sides[s] = dict(vin_v=v['vin' + s], top_v=v['xdut.top' + s], g_at_close_v=g,
                        g_before_close_v=ref['xdut.xboot%s.g' % s] if ref else None,
                        boost_v=ref['xdut.xboot%s.g' % s] - ref['vin' + s] if ref else None,
                        overdrive_at_close_v=overdrive(v, s), onset_ns=None, max_fall_v_per_ns=0.,
                        max_fall_at_ns=None, below_ns=dict(('%g' % x, None) for x in LEVELS_V),
                        overdrive_at_v={}, overdrive_at_first_compare_v=None, settled_overdrive_v=None)
    return dict(close_s=close, first_compare_s=None, sides=sides, last=(close, v), excerpt_t=None)


def advance(h, pt, pv, t, v, rows, frame):
    """Update an open hold phase with the native step (pt, pv) -> (t, v)."""
    close = h['close_s']
    for s in SIDES:
        x = h['sides'][s]
        key = 'xdut.xboot%s.g' % s
        if t > pt:
            rate = -(v[key] - pv[key]) / ((t - pt) * 1e9)
            if rate > x['max_fall_v_per_ns']:
                x['max_fall_v_per_ns'], x['max_fall_at_ns'] = rate, ((pt + t) / 2 - close) * 1e9
        a, b = pv[key] - (x['g_at_close_v'] - ONSET_V), v[key] - (x['g_at_close_v'] - ONSET_V)
        if x['onset_ns'] is None and a > 0 >= b:
            x['onset_ns'] = (pt + (t - pt) * a / (a - b) - close) * 1e9
        for level in LEVELS_V:
            name = '%g' % level
            a, b = overdrive(pv, s) - level, overdrive(v, s) - level
            if x['below_ns'][name] is None and a > 0 >= b:
                x['below_ns'][name] = (pt + (t - pt) * a / (a - b) - close) * 1e9
        for d in DELAYS_S:
            if pt < close + d <= t:
                x['overdrive_at_v']['%g' % (d * 1e9)] = overdrive(lerp(pt, pv, t, v, close + d), s)
    if t - close <= EXCERPT_S and (h['excerpt_t'] is None or t - h['excerpt_t'] >= EXCERPT_STEP_S):
        h['excerpt_t'] = t
        rows.append([frame, '%.6f' % ((t - close) * 1e9)] + ['%.6f' % v[n] for n in (
            CLOCK, CMP, 'xdut.xbootp.g', 'vinp', 'xdut.topp', 'xdut.xbootn.g', 'vinn', 'xdut.topn', 'vdd!')])
    h['last'] = (t, v)


def analyze(root, out):
    with open(root + '/inputs/context.json') as stream:
        ctx = json.load(stream)
    raw = [os.path.join(p, n) for p, _, files in os.walk(root + '/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    origin, period, count = ctx['frame_origin_s'], ctx['period_s'], ctx['frames']
    needed = [CLOCK, CMP, 'vdd!'] + [n % s for s in SIDES for n in ('xdut.xboot%s.g', 'vin%s', 'xdut.top%s')]
    holds, rows, history, prev, h = [], [], collections.deque(), None, None
    for t, v in samples(raw[0], ctx, needed):
        if prev is None:
            prev = t, v
            continue
        pt, pv = prev
        a, b = pv[CLOCK] - .5 * pv['vdd!'], v[CLOCK] - .5 * v['vdd!']
        edge = pt + (t - pt) * a / (a - b) if (a > 0) != (b > 0) else None
        if edge is not None and b < a:
            frame = int((edge - origin) // period)
            if h is not None:
                raise ValueError('Two closes without an opening')
            if 0 <= frame < count:
                at = lerp(pt, pv, t, v, edge)
                h = start(edge, at, history)
                h['frame'] = frame
                advance(h, edge, at, t, v, rows, frame)
        elif h is not None:
            c, d = pv[CMP] - .5 * pv['vdd!'], v[CMP] - .5 * v['vdd!']
            if h['first_compare_s'] is None and c <= 0 < d:
                when = pt + (t - pt) * c / (c - d)
                h['first_compare_s'] = when
                at = lerp(pt, pv, t, v, when)
                for s in SIDES:
                    h['sides'][s]['overdrive_at_first_compare_v'] = overdrive(at, s)
            if edge is not None:
                # Tracking opens: the overdrive just before is the settled hold level.
                for s in SIDES:
                    h['sides'][s]['settled_overdrive_v'] = overdrive(pv, s)
                holds.append(h)
                h = None
            else:
                advance(h, pt, pv, t, v, rows, h['frame'])
        history.append((t, v))
        while history[0][0] < t - 2 * BEFORE_S:
            history.popleft()
        prev = t, v
    if prev is None or prev[0] < ctx['expected_stop_s'] - 1e-12:
        raise ValueError('Incomplete transient')
    if h is not None:
        for s in SIDES:
            h['sides'][s]['settled_overdrive_v'] = overdrive(prev[1], s)
        holds.append(h)
    frames = []
    for h in holds:
        base = origin + h['frame'] * period
        frames.append(dict(frame=h['frame'], close_ns=(h['close_s'] - base) * 1e9,
                           first_compare_after_close_ns=None if h['first_compare_s'] is None
                           else (h['first_compare_s'] - h['close_s']) * 1e9, channels=h['sides']))
    worst = max(((f['frame'], s, f['channels'][s]['overdrive_at_first_compare_v']) for f in frames for s in SIDES
                 if f['channels'][s]['overdrive_at_first_compare_v'] is not None), key=lambda w: w[2])
    result = dict(run_id=ctx['run_id'], corner=ctx['corner'], vdd_v=ctx['vdd_v'], temperature_c=ctx['temperature_c'],
                  bootstrap=ctx.get('bootstrap_physical_evidence') or 'schematic', gate_probe=ctx.get('bootstrap_gate_probe'),
                  gate_limit_v=ctx.get('first_compare_gate_limit_v'), frames=frames,
                  worst=dict(frame=worst[0], channel=worst[1], overdrive_at_first_compare_v=worst[2]),
                  excerpt=dict(file='gate_excerpt.csv', window_ns=EXCERPT_S * 1e9, min_step_ps=EXCERPT_STEP_S * 1e12),
                  method=__doc__.strip())
    with open(out + '/result.json', 'w') as stream:
        json.dump(result, stream, indent=2)
    with open(out + '/gate_excerpt.csv', 'w') as stream:
        w = csv.writer(stream)
        w.writerow(['frame', 'after_close_ns', 'seq_sample', 'cmp_clk', 'g_p', 'vinp', 'topp', 'g_n', 'vinn', 'topn', 'vdd'])
        w.writerows(rows)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir', required=True)
    a = p.parse_args()
    analyze(a.source_run_dir or a.run_dir, a.output_dir)
