"""Split the signed plate error at each decision of a completed single_edge_lpe run (Python 2.7 on the host).

The frozen analyzer scores the signed TOPP-TOPN error of all 510 plates against the nominal rails, so an
offset of the VREFP/VREFN pins appears as settling error. At every comparator edge this analyzer computes
the same signed sum three ways:
  nominal  - plates against the nominal rails (equals the frozen analyzer's signed_lsb)
  pin      - plates against the instantaneous VREFN/VREFP pins (plate settling)
  static   - the pin offset measured 88 ns into the same frame, after the last update, applied to the
             decision's switch state (static reference-pin offset, e.g. FF-hot switch leakage)
and reports nominal - static, the decision error with the static offset removed (plate settling plus
dynamic reference recovery). Frame timing and the switch state come from the same nets as the analyzer.
"""
from __future__ import print_function, division
import argparse
import json
import math
import os

import native_stream

QUIET_NS = 88.


def samples(path, ctx):
    alias = ctx.get('signal_aliases', {})
    for t, v in native_stream.samples(path):
        yield t, dict((alias.get(k, k), x) for k, x in v.items()) if alias else v


def state(v, groups):
    """Per bit and side: True when the plate is switched to VREFN."""
    return dict(((side, bit), v['xdut.g%sn%d' % (side, bit)] > .5 * v['vdd!']) for side in 'np' for bit in range(8))


def signed(v, groups, weights, lsb, low, rails):
    """Weighted signed differential plate error in volts; rails(on_vrefn) gives the target rail voltage."""
    total = 0.
    for bit in range(8):
        diff = 0.
        for side, sign in (('p', 1.), ('n', -1.)):
            ports = groups[side][bit]
            mean = sum(v[p] for p in ports) / len(ports)
            diff += sign * (mean - rails(low[side, bit]))
        total += weights[bit] * diff
    return total


def analyze(root, out):
    with open(root + '/inputs/context.json') as stream:
        ctx = json.load(stream)
    raw = [os.path.join(p, n) for p, _, files in os.walk(root + '/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    origin, period, lsb = ctx['frame_origin_s'], ctx['period_s'], ctx['lsb_v']
    groups, weights, nominal = ctx['cdac_plate_nodes'], ctx['cdac_weights_v'], ctx['reference_v']
    scale = 1. / (2. * (nominal[1] - nominal[0]) * lsb)
    frames = [dict(frame=i, input_code=c, warmup=i < ctx.get('warmup_frames', 0), decisions=[], quiet=None)
              for i, c in enumerate(ctx.get('input_code_coordinates', ctx['expected_codes']))]
    net = 'xdut.cmp_clk'
    prev = None
    for t, v in samples(raw[0], ctx):
        if prev is None:
            missing = set(['vrefn', 'vrefp', 'vdd!', net]) - set(v)
            if missing:
                raise ValueError('Missing signals: ' + repr(sorted(missing)))
            prev = t, v
            continue
        pt, pv = prev

        def at(frac):
            return dict((k, pv[k] + frac * (v[k] - pv[k])) for k in v)
        a, b = pv[net] - .5 * pv['vdd!'], v[net] - .5 * v['vdd!']
        if (a > 0) != (b > 0) and b > a:
            frac = -a / (b - a)
            when = pt + frac * (t - pt)
            i = int(math.floor((when - origin) / period))
            if 0 <= i < len(frames):
                s = at(frac)
                low = state(s, groups)
                pins = dict(n=s['vrefn'], p=s['vrefp'])
                f = frames[i]
                f['decisions'].append(dict(
                    bit=7 - len(f['decisions']), ns=(when - origin - i * period) * 1e9,
                    low=dict(('%s%d' % k, x) for k, x in low.items()),
                    vrefn_mv=(pins['n'] - nominal[0]) * 1e3, vrefp_mv=(pins['p'] - nominal[1]) * 1e3,
                    nominal_lsb=scale * signed(s, groups, weights, lsb, low, lambda lo: nominal[0] if lo else nominal[1]),
                    pin_lsb=scale * signed(s, groups, weights, lsb, low, lambda lo: pins['n'] if lo else pins['p'])))
        for j in (int(math.floor((t - origin) / period)) - 1, int(math.floor((t - origin) / period))):
            if 0 <= j < len(frames):
                when = origin + j * period + QUIET_NS * 1e-9
                if pt < when <= t:
                    s = at((when - pt) / (t - pt))
                    low = state(s, groups)
                    pins = dict(n=s['vrefn'], p=s['vrefp'])
                    frames[j]['quiet'] = dict(
                        ns=QUIET_NS, vrefn_mv=(pins['n'] - nominal[0]) * 1e3, vrefp_mv=(pins['p'] - nominal[1]) * 1e3,
                        nominal_lsb=scale * signed(s, groups, weights, lsb, low, lambda lo: nominal[0] if lo else nominal[1]),
                        pin_lsb=scale * signed(s, groups, weights, lsb, low, lambda lo: pins['n'] if lo else pins['p']))
        prev = t, v
    if prev is None or prev[0] < ctx['expected_stop_s'] - 1e-12:
        raise ValueError('Incomplete transient')
    for f in frames:
        q = f['quiet']
        if q is None or len(f['decisions']) != 8:
            raise ValueError('Frame %d lacks eight decisions or its quiet sample' % f['frame'])
        offset = dict(n=q['vrefn_mv'] * 1e-3, p=q['vrefp_mv'] * 1e-3)
        for d in f['decisions']:
            # Plates sitting exactly at the quiet pins of the rails this decision's switches select.
            static = 0.
            for bit in range(8):
                for side, sign in (('p', 1.), ('n', -1.)):
                    static += sign * weights[bit] * offset['n' if d['low']['%s%d' % (side, bit)] else 'p']
            d['static_lsb'] = scale * static
            d['rail_lsb'] = d['nominal_lsb'] - d['pin_lsb']
            d['dynamic_rail_lsb'] = d['rail_lsb'] - d['static_lsb']
            d['excluding_static_lsb'] = d['nominal_lsb'] - d['static_lsb']
            del d['low']
    scored = [d for f in frames if not f['warmup'] for d in f['decisions']]

    def worst(key):
        return max(abs(d[key]) for d in scored)
    limit = ctx['settling_limit_lsb']
    result = dict(run_id=ctx['run_id'], corner=ctx['corner'], quiet_ns=QUIET_NS, settling_limit_lsb=limit,
                  frames=frames, max_abs=dict((k, worst(k)) for k in
                                              ('nominal_lsb', 'pin_lsb', 'static_lsb', 'dynamic_rail_lsb',
                                               'excluding_static_lsb')),
                  quiet_pin_offset_mv=dict(vrefn=[f['quiet']['vrefn_mv'] for f in frames],
                                           vrefp=[f['quiet']['vrefp_mv'] for f in frames]),
                  plate_settling_pass=worst('pin_lsb') <= limit,
                  excluding_static_pass=worst('excluding_static_lsb') <= limit,
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
