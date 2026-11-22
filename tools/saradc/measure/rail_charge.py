"""Per-frame charge and peak current of the ADC supply and reference rails; Python 2.7/3.

Binds to a completed short ADC run that saved VDD!, VREFP, VREFN, SAMPLE and the VVDD terminal
current. Reference source current is read across the fixture's series resistor, so the source
charge per frame is exact; the die charge removes the change of the fixture bypass charge.
The source run, its raw waveform and its derived results are never modified."""
from __future__ import print_function
import argparse
import bisect
import json
import os

from native_stream import samples


def interp(xs, ys, x):
    i = bisect.bisect_left(xs, x)
    if i <= 0:
        return ys[0]
    if i >= len(xs):
        return ys[-1]
    a = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
    return ys[i - 1] + a * (ys[i] - ys[i - 1])


def window_charge(trace, windows, cbyp):
    """Largest charge into the die within any window of each width, with its window end time.

    Reference die charge removes the fixture bypass charge change, so no derivative is needed."""
    out = {}
    ts = trace['t']
    for w in windows:
        best = dict(vdd=(0., None), vrefp=(0., None), vrefn=(0., None))
        for j, t2 in enumerate(ts):
            t1 = t2 - w
            if t1 < ts[0]:
                continue
            q = dict(vdd=trace['vdd'][j] - interp(ts, trace['vdd'], t1))
            for rail in ('vrefp', 'vrefn'):
                src = trace[rail + '_source'][j] - interp(ts, trace[rail + '_source'], t1)
                q[rail] = src - cbyp * (trace[rail][j] - interp(ts, trace[rail], t1))
            for rail, value in q.items():
                if abs(value) > abs(best[rail][0]):
                    best[rail] = (value, t2)
        out['%g' % w] = dict((rail, dict(charge_c=value, end_s=end)) for rail, (value, end) in best.items())
    return out


def measure(run_dir, source_dir, out_dir):
    with open(os.path.join(run_dir, 'inputs/rail_charge_context.json')) as f:
        cfg = json.load(f)
    with open(os.path.join(source_dir, 'inputs/context.json')) as f:
        ctx = json.load(f)
    assert ctx['run_id'] == cfg['source_run_id'], 'Context belongs to another run'
    paths = [os.path.join(p, n) for p, _, names in os.walk(os.path.join(source_dir, 'raw'))
             for n in names if n.endswith('.tran.tran')]
    assert len(paths) == 1, 'Expected one native transient'
    r, cbyp = cfg['reference_series_ohm'], cfg['reference_bypass_f']
    vp0, vn0 = cfg['vrefp_v'], cfg['vrefn_v']
    origin, period, count = ctx['frame_origin_s'], ctx['period_s'], ctx['frames']
    frames = [dict(frame=k, start_s=origin + k * period, end_s=origin + (k + 1) * period,
                   code=ctx['expected_codes'][k],
                   charge_c=dict(vdd=0., vrefp_source=0., vrefn_source=0.),
                   sampling_charge_c=dict(vdd=0., vrefp_source=0., vrefn_source=0.),
                   peak_a=dict(vdd=0., vrefp_source=0., vrefn_source=0.),
                   peak_time_s=dict(vdd=None, vrefp_source=None, vrefn_source=None),
                   min_vrefp_v=None, max_vrefn_v=None, min_reference_span_v=None,
                   boundary_v=dict()) for k in range(count)]
    traces = [dict(t=[], vrefp=[], vrefn=[], vdd=[], vrefp_source=[], vrefn_source=[]) for _ in range(count)]
    prev, points = None, 0
    for t, v in samples(paths[0]):
        points += 1
        cur = dict(vdd=-v['vvdd:p'], vrefp_source=(vp0 - v['vrefp']) / r, vrefn_source=(vn0 - v['vrefn']) / r)
        high = v['sample'] > .5 * v['vdd!']
        k = int((t - origin) // period)
        if 0 <= k < count:
            f = frames[k]
            if 'start' not in f['boundary_v']:
                f['boundary_v']['start'] = dict(vrefp=v['vrefp'], vrefn=v['vrefn'], t=t)
            f['boundary_v']['end'] = dict(vrefp=v['vrefp'], vrefn=v['vrefn'], t=t)
            for rail, i in cur.items():
                if abs(i) > abs(f['peak_a'][rail]):
                    f['peak_a'][rail], f['peak_time_s'][rail] = i, t
            span = v['vrefp'] - v['vrefn']
            f['min_vrefp_v'] = v['vrefp'] if f['min_vrefp_v'] is None else min(f['min_vrefp_v'], v['vrefp'])
            f['max_vrefn_v'] = v['vrefn'] if f['max_vrefn_v'] is None else max(f['max_vrefn_v'], v['vrefn'])
            f['min_reference_span_v'] = span if f['min_reference_span_v'] is None else min(f['min_reference_span_v'], span)
        # Each trapezoid belongs to the frame that holds its midpoint, so no step is lost at a boundary.
        m = None if prev is None else int((.5 * (t + prev[0]) - origin) // period)
        if m is not None and 0 <= m < count:
            dt = t - prev[0]
            for rail in cur:
                q = .5 * (cur[rail] + prev[1][rail]) * dt
                frames[m]['charge_c'][rail] += q
                if high and prev[2]:
                    frames[m]['sampling_charge_c'][rail] += q
        if 0 <= k < count:
            trace = traces[k]
            trace['t'].append(t)
            trace['vrefp'].append(v['vrefp'])
            trace['vrefn'].append(v['vrefn'])
            for rail in cur:
                trace[rail].append(frames[k]['charge_c'][rail])
        prev = (t, cur, high)
    for f, trace in zip(frames, traces):
        f['window_charge_c'] = window_charge(trace, cfg['windows_s'], cbyp)
        b = f.pop('boundary_v')
        f['die_charge_c'] = dict(
            vdd=f['charge_c']['vdd'],
            vrefp=f['charge_c']['vrefp_source'] - cbyp * (b['end']['vrefp'] - b['start']['vrefp']),
            vrefn=f['charge_c']['vrefn_source'] - cbyp * (b['end']['vrefn'] - b['start']['vrefn']))
        f['conversion_charge_c'] = dict((k, f['charge_c'][k] - f['sampling_charge_c'][k]) for k in f['charge_c'])
        f['reference_bypass_delta_v'] = dict(vrefp=b['end']['vrefp'] - b['start']['vrefp'],
                                             vrefn=b['end']['vrefn'] - b['start']['vrefn'])
        f['vrefp_droop_max_v'] = vp0 - f.pop('min_vrefp_v')
        f['vrefn_rise_max_v'] = f.pop('max_vrefn_v') - vn0
        f['reference_span_droop_max_v'] = (vp0 - vn0) - f.pop('min_reference_span_v')
    scored = [f for f in frames if f['frame'] >= cfg['first_steady_frame']]
    summary = dict((key, dict((rail, max(abs(f[key][rail]) for f in scored)) for rail in scored[0][key]))
                   for key in ('peak_a', 'die_charge_c', 'charge_c'))
    result = dict(analysis_complete=True, run_id=cfg['run_id'], source_run_id=cfg['source_run_id'],
                  native_points=points, frames=frames, steady_frames=[f['frame'] for f in scored],
                  worst_steady=summary, context=cfg,
                  scope=('Charge per 100 ns frame and peak source current of the ideal VDD source and the two '
                         'reference sources behind the fixture resistors. Positive charge flows from the source '
                         'into the ADC. The first frame starts from the DC solution and is reported, not scored.'))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(os.path.join(out_dir, 'result.json'), 'w') as f:
        json.dump(result, f, indent=2)
        f.write('\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--source-run-dir', required=True)
    a = p.parse_args()
    measure(a.run_dir, a.source_run_dir, a.output_dir)
