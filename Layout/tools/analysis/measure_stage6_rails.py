"""Reference and supply rails of a completed Stage 6 run against the Stage 1 budget (Python 2.7 on the host).

The Stage 6 testbench (Layout/tools/simulation/prepare_stage6.py) puts zero-volt ammeters in the system model:
VA_REFP1/2 and VA_REFN1/2 on the two bonds of each reference rail, VA_REFPC/VA_REFNC at the core reference
pins, VA_VDD<b> on each supply bond and VA_VDD<b>_C at each core supply pin. The analyzers read the
reference at the pair's trunk ports (signal names vrefp/vrefn) and the block-side supplies at xdut.vdd<b>_blk
and xdut.vssc. Per scored frame (100 ns from the frame origin) this reports, against
Layout/specs/constraints.json electrical_budgets:
  reference_charge_per_conversion_C  charge into the core VREFP pin (and out of VREFN)
  reference_event_charge_C           largest charge into the VREFP pin within any 1 ns window
  reference_pin_peak_current_A       peak of each rail's summed bond current
  reference_span_droop_V             largest drop of VREFP_TRUNK - VREFN_TRUNK below the nominal span
  supply_charge_per_conversion_C     charge into the three core VDD pins together
  supply_event_charge_C              largest such charge within any 1 ns window
  supply_pin_peak_current_A          peak of the summed VDD bond currents
  supply_droop_V                     largest drop of VDD<b>_BLK - VSSC below the corner supply, per branch

Static current: the mean current of each core pin over the quiet window QUIET_NS of every scored frame (after the
last update and PRESET, before the next track opens), as the reference split reads its quiet pins. The three
charge budgets are scored on the switching part: the frame charge minus that frame's static current times the
period, and the worst 1 ns charge minus the static current of its frame times 1 ns. The totals are kept
(verdict_total). The static VDD current is also given per supply branch (a: comparator and both Bootstraps,
p: XREF/CDAC pair, d: SAR macro; each branch includes the top-level decap on its rail).
"""
from __future__ import print_function, division
import argparse
import json
import os

import native_stream

BRANCHES = ('a', 'p', 'd')
WINDOW_S = 1e-9
# Quiet window within each frame (ns from the frame origin). The last commit is near 59 ns at FF hot but near
# 80 ns at SS cold (75-95 ns caught the SS-cold conversion tail: halves 115 vs 1 uA); the next track opens near
# 101 ns. 88 ns is the quiet point of the reference split. Two halves check that the current is steady.
QUIET_NS = (88., 98.)
QUIET_HALVES_REL = .25     # halves differing by more (above 1 uA) flag the window as not quiet
CHARGE_BUDGETS = ('reference_charge_per_conversion_C', 'reference_event_charge_C', 'supply_charge_per_conversion_C',
                  'supply_event_charge_C')


def samples(path, ctx):
    alias = ctx.get('signal_aliases', {})
    for t, v in native_stream.samples(path):
        yield t, dict((alias.get(k, k), x) for k, x in v.items()) if alias else v


class Integral(object):
    """Running trapezoidal integral with a sliding-window maximum of the charge over WINDOW_S."""

    def __init__(self):
        self.t, self.q = [], []
        self.best = (0., None)

    def add(self, t, i):
        if self.t:
            self.q.append(self.q[-1] + .5 * (self.i + i) * (t - self.t[-1]))
        else:
            self.q.append(0.)
        self.t.append(t)
        self.i = i
        # Window start by linear interpolation of the cumulative charge.
        lo = t - WINDOW_S
        if lo >= self.t[0]:
            k = self.k = getattr(self, 'k', 0)
            while self.t[k + 1] < lo:
                k += 1
            self.k = k
            a = (lo - self.t[k]) / (self.t[k + 1] - self.t[k])
            q0 = self.q[k] + a * (self.q[k + 1] - self.q[k])
            if abs(self.q[-1] - q0) > abs(self.best[0]):
                self.best = (self.q[-1] - q0, t)

    def at(self, t):
        import bisect
        j = bisect.bisect_left(self.t, t)
        if j <= 0:
            return self.q[0]
        if j >= len(self.t):
            return self.q[-1]
        a = (t - self.t[j - 1]) / (self.t[j] - self.t[j - 1])
        return self.q[j - 1] + a * (self.q[j] - self.q[j - 1])


def analyze(root, out, own=None):
    with open(root + '/inputs/context.json') as stream:
        ctx = json.load(stream)
    with open((own or root) + '/inputs/stage6_budget.json') as stream:
        budget = json.load(stream)
    raw = [os.path.join(p, n) for p, _, files in os.walk(root + '/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    origin, period, frames = ctx['frame_origin_s'], ctx['period_s'], ctx['frames']
    warm = ctx.get('warmup_frames', 0)
    span0 = ctx['reference_v'][1] - ctx['reference_v'][0]
    vdd0 = ctx['vdd_v']
    ref_p, ref_n, sup = Integral(), Integral(), Integral()
    branch = dict((b, Integral()) for b in BRANCHES)
    peak = dict(refp=(0., None), refn=(0., None), vdd=(0., None))
    span = (0., None)
    droop = dict((b, (0., None)) for b in BRANCHES)
    begin = origin + warm * period
    end = origin + frames * period
    last = None
    for t, v in samples(raw[0], ctx):
        if last is None:
            need = ['va_refp1:p', 'va_refp2:p', 'va_refn1:p', 'va_refn2:p', 'va_refpc:p', 'va_refnc:p', 'vrefp', 'vrefn',
                    'xdut.vssc'] + ['va_vdd%s:p' % b for b in BRANCHES] + ['va_vdd%s_c:p' % b for b in BRANCHES] + \
                   ['xdut.vdd%s_blk' % b for b in BRANCHES]
            missing = [k for k in need if k not in v]
            if missing:
                raise ValueError('Missing rail signals: ' + repr(missing))
        last = t
        ref_p.add(t, v['va_refpc:p'])
        ref_n.add(t, -v['va_refnc:p'])
        sup.add(t, sum(v['va_vdd%s_c:p' % b] for b in BRANCHES))
        for b in BRANCHES:
            branch[b].add(t, v['va_vdd%s_c:p' % b])
        if not begin <= t <= end:
            continue
        for key, value in (('refp', v['va_refp1:p'] + v['va_refp2:p']), ('refn', v['va_refn1:p'] + v['va_refn2:p']),
                           ('vdd', sum(v['va_vdd%s:p' % b] for b in BRANCHES))):
            if abs(value) > abs(peak[key][0]):
                peak[key] = (value, t)
        drop = span0 - (v['vrefp'] - v['vrefn'])
        if drop > span[0]:
            span = (drop, t)
        for b in BRANCHES:
            d = vdd0 - (v['xdut.vdd%s_blk' % b] - v['xdut.vssc'])
            if d > droop[b][0]:
                droop[b] = (d, t)
    if last is None or last < ctx['expected_stop_s'] - 1e-12:
        raise ValueError('Incomplete transient')
    def mean(integral, a, b):
        return (integral.at(b) - integral.at(a)) / (b - a)

    rails = dict(vrefp=ref_p, vrefn=ref_n, vdd=sup)
    per_frame = []
    for i in range(warm, frames):
        t0, t1 = origin + i * period, origin + (i + 1) * period
        qa, qb = t0 + QUIET_NS[0] * 1e-9, t0 + QUIET_NS[1] * 1e-9
        qm = .5 * (qa + qb)
        row = dict(frame=i)
        for name, integral in rails.items():
            static = mean(integral, qa, qb)
            row[name + '_charge_c'] = integral.at(t1) - integral.at(t0)
            row[name + '_static_a'] = static
            row[name + '_static_halves_a'] = [mean(integral, qa, qm), mean(integral, qm, qb)]
            row[name + '_switching_charge_c'] = row[name + '_charge_c'] - static * period
        row['vdd_static_branch_a'] = dict((b, mean(branch[b], qa, qb)) for b in BRANCHES)
        per_frame.append(row)
    by_frame = dict((f['frame'], f) for f in per_frame)

    def static_at(t, name):
        """Static current of the scored frame holding t (the nearest scored frame for a warm-up event)."""
        i = min(max(int((t - origin) // period), warm), frames - 1)
        return by_frame[i][name + '_static_a']
    # Window maxima cover the whole run; reported with their end time so warm-up events can be recognised.
    rel = lambda t: None if t is None else dict(frame=int((t - origin) // period), ns=((t - origin) % period) * 1e9)
    measured = dict(
        reference_charge_per_conversion_C=max(max(abs(f['vrefp_charge_c']), abs(f['vrefn_charge_c'])) for f in per_frame),
        reference_event_charge_C=max(abs(ref_p.best[0]), abs(ref_n.best[0])),
        reference_pin_peak_current_A=max(abs(peak['refp'][0]), abs(peak['refn'][0])),
        reference_span_droop_V=span[0],
        supply_charge_per_conversion_C=max(abs(f['vdd_charge_c']) for f in per_frame),
        supply_event_charge_C=abs(sup.best[0]),
        supply_pin_peak_current_A=abs(peak['vdd'][0]),
        supply_droop_V=max(d for d, _ in droop.values()))
    event = lambda integral, name: abs(integral.best[0] - static_at(integral.best[1], name) * WINDOW_S) \
        if integral.best[1] is not None else 0.
    switching = dict(
        reference_charge_per_conversion_C=max(max(abs(f['vrefp_switching_charge_c']), abs(f['vrefn_switching_charge_c']))
                                              for f in per_frame),
        reference_event_charge_C=max(event(ref_p, 'vrefp'), event(ref_n, 'vrefn')),
        supply_charge_per_conversion_C=max(abs(f['vdd_switching_charge_c']) for f in per_frame),
        supply_event_charge_C=event(sup, 'vdd'))
    verdict_total = dict((k, dict(measured=v, limit=budget[k], pass_=v <= budget[k])) for k, v in measured.items())
    scored = dict(measured, **switching)
    verdict = dict((k, dict(measured=v, limit=budget[k], pass_=v <= budget[k],
                            basis='switching (static removed)' if k in CHARGE_BUDGETS else 'total'))
                   for k, v in scored.items())
    stat = lambda name: [f[name + '_static_a'] for f in per_frame]
    ref_v = ctx['reference_v']
    static = dict(
        current_a=dict((n, dict(min=min(stat(n)), max=max(stat(n)), mean=sum(stat(n)) / len(per_frame)))
                       for n in rails),
        within_window_halves_max_rel=max(abs(h[0] - h[1]) / max(abs(f[n + '_static_a']), 1e-15)
                                         for f in per_frame for n in rails for h in [f[n + '_static_halves_a']]),
        not_quiet=[dict(frame=f['frame'], rail=n, halves_a=h) for f in per_frame for n in rails
                   for h in [f[n + '_static_halves_a']]
                   if abs(h[0] - h[1]) > max(QUIET_HALVES_REL * abs(f[n + '_static_a']), 1e-6)],
        vdd_branch_a=dict((b, sum(f['vdd_static_branch_a'][b] for f in per_frame) / len(per_frame)) for b in BRANCHES),
        power_w=dict(vdd=vdd0 * sum(stat('vdd')) / len(per_frame),
                     reference=(ref_v[1] * sum(stat('vrefp')) - ref_v[0] * sum(stat('vrefn'))) / len(per_frame)),
        quiet_ns=list(QUIET_NS))
    result = dict(run_id=ctx['run_id'], corner=ctx['corner'], scored_frames=[f['frame'] for f in per_frame],
                  per_frame=per_frame, verdict=verdict, verdict_total=verdict_total, static=static,
                  all_pass=all(x['pass_'] for x in verdict.values()),
                  all_pass_total=all(x['pass_'] for x in verdict_total.values()),
                  where=dict(reference_event=rel(ref_p.best[1]) if abs(ref_p.best[0]) >= abs(ref_n.best[0]) else rel(ref_n.best[1]),
                             supply_event=rel(sup.best[1]), refp_peak=rel(peak['refp'][1]), refn_peak=rel(peak['refn'][1]),
                             vdd_peak=rel(peak['vdd'][1]), span_droop=rel(span[1]),
                             supply_droop=dict((b, dict(v=d, at=rel(t))) for b, (d, t) in droop.items())),
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
    analyze(a.source_run_dir or a.run_dir, a.output_dir, a.run_dir)
