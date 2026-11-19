"""Analysis-only: trace TOP tracking during every sampling window of a short ADC run.

Streams the source run's native waveform (no full arrays). For each frame it keeps the
window from the frame origin to 2 ns after the sample close (falling xdut.seq_sample)
at 50 ps resolution: differential and per-side error of TOP against the ideal source
(LSB), TOP common mode, the input-pin drop across the 50 ohm source, references,
bootstrap gate overdrive, and every crossing of the CDAC gate commands. It reports the
error at fixed times before close and the apparent decay time constant over the last
4 ns. Python 2.7/3.
"""
from __future__ import print_function
import argparse
import glob
import json
import math
import os

from native_stream import samples

STEP = 50e-12


def crossing(prev, cur, key, level):
    a, b = prev[1][key] - level, cur[1][key] - level
    if (a > 0) == (b > 0):
        return None
    return prev[0] - a / (b - a) * (cur[0] - prev[0]), b > 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--source-run-dir', required=True)
    a = p.parse_args()
    run = a.source_run_dir
    ctx = json.load(open(os.path.join(run, 'inputs/context.json')))
    raws = sorted(glob.glob(os.path.join(run, 'raw', '*tran*')))
    assert len(raws) == 1, raws
    lsb, period, origin, nframes = ctx['lsb_v'], ctx['period_s'], ctx['frame_origin_s'], ctx['frames']
    frames = [dict(frame=k, code=ctx['expected_codes'][k], points=[], gate_crossings=[], close_s=None)
              for k in range(nframes)]
    gates = None
    prev = None
    kept = {}
    for t, v in samples(raws[0]):
        if gates is None:
            gates = sorted(n for n in v if n.startswith('xdut.g') and n[6:8] in ('nn', 'np', 'pn', 'pp'))
        k = int(math.floor((t - origin) / period))
        if 0 <= k < nframes:
            f = frames[k]
            half = .5 * v['vdd!']
            if prev is not None:
                c = crossing(prev, (t, v), 'xdut.seq_sample', half)
                if c and not c[1] and f['close_s'] is None:
                    f['close_s'] = c[0]
                    frac = (c[0] - prev[0]) / (t - prev[0])
                    at = dict((n, prev[1][n] + frac * (v[n] - prev[1][n])) for n in v)
                    f['at_close'] = dict(
                        err_lsb=(at['xdut.topp'] - at['xdut.topn'] - at['vinp_src'] + at['vinn_src']) / lsb,
                        err_p_lsb=(at['xdut.topp'] - at['vinp_src']) / lsb,
                        err_n_lsb=(at['xdut.topn'] - at['vinn_src']) / lsb,
                        vin_diff_v=at['vinp_src'] - at['vinn_src'])
                for g in gates:
                    c = crossing(prev, (t, v), g, half)
                    if c:
                        f['gate_crossings'].append([g[5:], round(c[0] - origin - k * period, 13), c[1]])
            limit = f['close_s'] + 2e-9 if f['close_s'] else None
            if (limit is None or t <= limit) and t - kept.get(k, -1) >= STEP:
                kept[k] = t
                f['points'].append([
                    round(t - origin - k * period, 13),
                    (v['xdut.topp'] - v['xdut.topn'] - v['vinp_src'] + v['vinn_src']) / lsb,
                    (v['xdut.topp'] - v['vinp_src']) / lsb,
                    (v['xdut.topn'] - v['vinn_src']) / lsb,
                    .5 * (v['xdut.topp'] + v['xdut.topn']),
                    v['vinp'] - v['vinp_src'], v['vinn'] - v['vinn_src'],
                    v['vrefp'], v['vrefn'],
                    v['xdut.xbootp.g'] - v['vinp'], v['xdut.xbootn.g'] - v['vinn'],
                    v['xdut.seq_sample'], v['vdd!']])
        prev = (t, v)
    columns = ['t_rel_s', 'err_lsb', 'err_p_lsb', 'err_n_lsb', 'top_cm_v', 'vinp_drop_v', 'vinn_drop_v',
               'vrefp_v', 'vrefn_v', 'bootp_overdrive_v', 'bootn_overdrive_v', 'seq_sample_v', 'vdd_v']
    for f in frames:
        close = f['close_s'] - origin - f['frame'] * period if f['close_s'] else None
        f['close_rel_s'] = close
        if close is None:
            continue
        pts = f['points']

        def at(dt, col):
            # Last kept point at or before the requested time; the close value itself is interpolated.
            target = close - dt
            return max((r for r in pts if r[0] <= target + 1e-15), key=lambda r: r[0])[col]
        f['err_before_close_lsb'] = dict(('%gns' % (dt * 1e9), at(dt, 1)) for dt in (1e-9, 2e-9, 4e-9, 8e-9, 16e-9, 30e-9))
        f['err_before_close_lsb']['0ns'] = f['at_close']['err_lsb']
        # Fit only points before close, so the switch-off edge cannot bias the decay.
        p0 = max((r for r in pts if r[0] < close), key=lambda r: r[0])
        p4 = max((r for r in pts if r[0] <= p0[0] - 4e-9 + 1e-15), key=lambda r: r[0])
        e0, e4 = p0[1], p4[1]
        f['apparent_tau_last_4ns_s'] = ((p0[0] - p4[0]) / math.log(e4 / e0)) if e0 * e4 > 0 and abs(e4) > abs(e0) else None
        opened = [r for r in pts if r[0] < close and r[11] > .5 * r[12]]
        f['sample_open_rel_s'] = opened[0][0] if opened else None
        f['bootstrap_overdrive_at_close_v'] = [at(0, 9), at(0, 10)]
        f['min_bootstrap_overdrive_in_window_v'] = [min(r[9] for r in opened) if opened else None,
                                                    min(r[10] for r in opened) if opened else None]
    result = dict(source_run=os.path.basename(run.rstrip('/')), corner=ctx.get('corner'),
                  mos=ctx.get('mos'), vdd_v=ctx.get('vdd_v'), temperature_c=ctx.get('temperature_c'),
                  lsb_v=lsb, columns=columns, frames=frames, analysis_complete=True)
    with open(os.path.join(a.output_dir, 'result.json'), 'w') as out:
        json.dump(result, out)
    for f in frames:
        print(f['frame'], f['code'], f.get('at_close'), f.get('apparent_tau_last_4ns_s'))


if __name__ == '__main__':
    main()
