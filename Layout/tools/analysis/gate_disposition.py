"""TOP disturbance behind a Bootstrap gate-screen overshoot, from collected runs (no new simulation).

The screen (single_edge_lpe first_compare_gate_limit_v) bounds G - min(VIN, TOP) of the main switch at the first
comparator clock: a switch still on would move TOP while the comparator decides. For the worst frame and channel
of a measure_bootstrap_gate.py job this reports, from its native excerpt:
- the first comparator clock t_cmp and the point t_off where G has finished falling (overdrive within 5 mV of its
  settled hold level), both after the sample close;
- how far TOPP, TOPN and TOPP - TOPN move between t_cmp and t_end = min(t_off, first update - 10 ps), in LSB, and
  the largest excursion from the value at t_cmp in that window;
- the first decision's residue (TOPP - TOPN at the first comparator clock) in LSB.
With --control the same is reported for another gate job (for example the old core in the same deck), and the
codes, sample-close residual and plate settling of both source runs are compared frame by frame.

Most of the TOP movement in that window is comparator kickback at the clock edge and does not depend on the gate.
The score (user decision 2026-11-22) is the switch-attributable part: from the same-deck pair, the sensitivity
k = |change of TOP movement| / |change of overdrive|, and the attributable movement k x overdrive of the run, the
movement a switch with zero overdrive would not have. Taken per quantity (TOPP, TOPN, TOPP - TOPN); the largest
counts against the 0.05 LSB limit.

--pair applies the disposition rule for the routed Bootstrap r2 runs (user decisions 2026-11-22; condition 4
revised 2026-11-23). The 0.1 V screen in the specification is unchanged. The runs pass outright if the worst gate
screen is <= 0.1 V; otherwise they pass with a written disposition only if all hold:
  1. worst gate screen <= 0.111 V;
  2. gate-attributable TOP movement <= 0.05 LSB (slope method above);
  3. codes equal and plate settling within SETTLING_NOISE_LSB of the old-core routed run, on every scored frame;
  4. sample-close residual within the Stage 6 limit, 0.25 LSB (replaces "residual unchanged"; the fill's own
     effect on the residual is recorded separately).
Each pair is (r2 gate job, old-core routed source run, old-core gate job in the same deck). A pair whose old-core
gate job is not available takes the sensitivity of a pair that has one.
  python -m Layout.tools.analysis.gate_disposition GATE_RUN [--control GATE_RUN] [--output PATH]
  python -m Layout.tools.analysis.gate_disposition --pair R2_GATE OLD_RUN [OLD_GATE] [--pair ...] [--output PATH]
"""
import argparse
import csv
import io
import json

from Layout.project import ROOT
from Layout.tools.analysis.stage2_summary import RUNS, collected

SETTLED_BAND_V = .005
UPDATE_GUARD_NS = .01


def gate_job(gate_id):
    result, recipe, digest = collected(gate_id)
    source_id = recipe['test_conditions']['split_source_run_id']
    data = (RUNS / gate_id / 'collected/derived/gate_excerpt.csv').read_bytes()
    receipt = json.loads((RUNS / gate_id / 'collected/collection_receipt.json').read_bytes())
    import hashlib
    excerpt_sha = hashlib.sha256(data).hexdigest()
    if not any(f['name'] == 'derived/gate_excerpt.csv' and f['sha256'] == excerpt_sha for f in receipt['files']):
        raise ValueError('Excerpt does not match its receipt: ' + gate_id)
    rows = list(csv.DictReader(io.StringIO(data.decode())))
    return result, recipe, digest, excerpt_sha, source_id, rows


def disturbance(gate_id, frame=None, channel=None):
    result, recipe, digest, excerpt_sha, source_id, rows = gate_job(gate_id)
    source, source_recipe, source_digest = collected(source_id)
    lsb = source_recipe['test_conditions']['lsb_v']
    frame = result['worst']['frame'] if frame is None else frame
    channel = result['worst']['channel'] if channel is None else channel
    f = next(x for x in result['frames'] if x['frame'] == frame)
    c = f['channels'][channel]
    t_cmp = f['first_compare_after_close_ns']
    run_frame = next(x for x in source['frames'] if x['frame'] == frame)
    t_update = run_frame['writes'][0]['ns'] - f['close_ns'] if run_frame['writes'] else None
    pts = [dict(t=float(r['after_close_ns']), topp=float(r['topp']), topn=float(r['topn']),
                od=float(r['g_' + channel]) - min(float(r['vin' + channel]), float(r['top' + channel])))
           for r in rows if int(r['frame']) == frame]
    settled = c['settled_overdrive_v']
    t_off = next((p['t'] for p in pts if p['t'] > t_cmp and p['od'] <= settled + SETTLED_BAND_V), None)
    t_end = min(x for x in (t_off, None if t_update is None else t_update - UPDATE_GUARD_NS, pts[-1]['t']) if x is not None)

    def value(key, t):
        for a, b in zip(pts, pts[1:]):
            if a['t'] <= t <= b['t']:
                return a[key] + (b[key] - a[key]) * (t - a['t']) / (b['t'] - a['t'])
        raise ValueError('Time outside the excerpt: %g ns' % t)
    window = [p for p in pts if t_cmp <= p['t'] <= t_end]
    out = dict(gate_run=gate_id, gate_result_sha256=digest, excerpt_sha256=excerpt_sha, source_run=source_id,
               bootstrap=result['bootstrap'].rsplit('/', 1)[-1], frame=frame, channel=channel, lsb_v=lsb,
               overdrive_at_first_compare_v=c['overdrive_at_first_compare_v'], first_compare_after_close_ns=t_cmp,
               g_finished_falling_after_close_ns=t_off, first_update_after_close_ns=t_update, window_end_ns=t_end,
               window_cut_by_update=t_off is None or (t_update is not None and t_update - UPDATE_GUARD_NS < t_off),
               first_decision_residue_lsb=next(b for b in run_frame['bits'] if b['bit'] == 7)['top_diff_v'] / lsb)
    for key, name in (('topp', 'topp'), ('topn', 'topn')):
        start = value(key, t_cmp)
        out[name + '_move_lsb'] = (value(key, t_end) - start) / lsb
        out[name + '_max_excursion_lsb'] = max(abs(p[key] - start) for p in window) / lsb if window else 0.
    start = value('topp', t_cmp) - value('topn', t_cmp)
    out['diff_move_lsb'] = (value('topp', t_end) - value('topn', t_end) - start) / lsb
    out['diff_max_excursion_lsb'] = max(abs(p['topp'] - p['topn'] - start) for p in window) / lsb if window else 0.
    return out


ATTRIBUTABLE_LIMIT_LSB = .05


def attributable(run, control):
    """Switch-attributable TOP movement of `run` from a same-deck, same-frame `control` with another overdrive."""
    d_od = run['overdrive_at_first_compare_v'] - control['overdrive_at_first_compare_v']
    if abs(d_od) < 1e-3:
        raise ValueError('The pair needs different overdrives')
    out = dict(delta_overdrive_v=d_od)
    for name in ('topp', 'topn', 'diff'):
        change = run[name + '_move_lsb'] - control[name + '_move_lsb']
        k = abs(change) / abs(d_od)
        out[name] = dict(move_change_lsb=change, sensitivity_lsb_per_v=k,
                         attributable_lsb=k * max(run['overdrive_at_first_compare_v'], 0.))
    out['worst_attributable_lsb'] = max(out[n]['attributable_lsb'] for n in ('topp', 'topn', 'diff'))
    out['limit_lsb'] = ATTRIBUTABLE_LIMIT_LSB
    out['negligible'] = out['worst_attributable_lsb'] <= ATTRIBUTABLE_LIMIT_LSB
    return out


def frames_compare(run_id, control_id):
    """Frame-by-frame codes, residual and settling of two runs of the same stimulus; warm-up frames are listed
    but left out of the summary, as in the Stage 2 scoring."""
    def rows(rid):
        r, recipe, digest = collected(rid)
        return digest, dict((f['frame'], dict(code=f['code90'], close=f['track'][1]['close_error_lsb'] if len(f['track']) == 2 else None,
                                             settle=f['max_abs_signed_settling_lsb'], margin=f['margin_ns'],
                                             gate=f['bits'][0]['first_compare']['gate_overdrive_v'] if f['bits'] else None,
                                             warmup=bool(f.get('warmup'))))
                            for f in r['frames'])
    a_sha, a = rows(run_id)
    b_sha, b = rows(control_id)
    table = [dict(frame=k, warmup=a[k]['warmup'],
                  **{'%s_%s' % (n, side): v[n] for side, v in (('run', a[k]), ('control', b[k])) for n in a[k] if n != 'warmup'})
             for k in sorted(set(a) & set(b))]
    scored = [t for t in table if not t['warmup']]
    return dict(run=run_id, run_result_sha256=a_sha, control=control_id, control_result_sha256=b_sha, frames=table,
                scored_frames=len(scored), codes_equal=all(t['code_run'] == t['code_control'] for t in scored),
                max_close_change_lsb=max(abs((t['close_run'] or 0) - (t['close_control'] or 0)) for t in scored),
                max_settle_change_lsb=max(abs((t['settle_run'] or 0) - (t['settle_control'] or 0)) for t in scored),
                max_abs_close_run_lsb=max(abs(t['close_run'] or 0) for t in scored))


GATE_SCREEN_V = .1
DISPOSITION_MAX_V = .111
STAGE6_CLOSE_LIMIT_LSB = .25
# Same deck and stimulus, only the Bootstrap differs: a settling change above 0.01 LSB is not run-to-run noise.
SETTLING_NOISE_LSB = .01


def verdict(pairs):
    """The disposition rule (module docstring) over (r2 gate job, old-core routed run, old-core gate job or None)."""
    rows = []
    for r2_gate, old_run, old_gate in pairs:
        run = disturbance(r2_gate)
        row = dict(run=run, frames=frames_compare(run['source_run'], old_run))
        if old_gate:
            row['control_same_frame'] = disturbance(old_gate, run['frame'], run['channel'])
            row['attributable'] = dict(attributable(run, row['control_same_frame']), slope_from=r2_gate)
        rows.append(row)
    sources = [r for r in rows if 'attributable' in r]
    if not sources:
        raise ValueError('At least one pair needs its old-core gate job for the sensitivity')
    for r in rows:
        if 'attributable' not in r:
            src = sources[0]['attributable']
            od = max(r['run']['overdrive_at_first_compare_v'], 0.)
            r['attributable'] = dict(slope_from=src['slope_from'], limit_lsb=ATTRIBUTABLE_LIMIT_LSB, **dict(
                (n, dict(sensitivity_lsb_per_v=src[n]['sensitivity_lsb_per_v'],
                         attributable_lsb=src[n]['sensitivity_lsb_per_v'] * od)) for n in ('topp', 'topn', 'diff')))
            r['attributable']['worst_attributable_lsb'] = max(r['attributable'][n]['attributable_lsb']
                                                              for n in ('topp', 'topn', 'diff'))
    worst = max(r['run']['overdrive_at_first_compare_v'] for r in rows)
    conditions = dict(
        screen_within_disposition_max=dict(value_v=worst, limit_v=DISPOSITION_MAX_V, met=worst <= DISPOSITION_MAX_V),
        attributable_top_movement=dict(value_lsb=max(r['attributable']['worst_attributable_lsb'] for r in rows),
                                       limit_lsb=ATTRIBUTABLE_LIMIT_LSB),
        codes_and_settling_unchanged=dict(codes_equal=all(r['frames']['codes_equal'] for r in rows),
                                          max_settle_change_lsb=max(r['frames']['max_settle_change_lsb'] for r in rows),
                                          noise_lsb=SETTLING_NOISE_LSB),
        residual_within_stage6=dict(value_lsb=max(r['frames']['max_abs_close_run_lsb'] for r in rows),
                                    limit_lsb=STAGE6_CLOSE_LIMIT_LSB))
    c = conditions
    c['attributable_top_movement']['met'] = c['attributable_top_movement']['value_lsb'] <= ATTRIBUTABLE_LIMIT_LSB
    c['codes_and_settling_unchanged']['met'] = bool(c['codes_and_settling_unchanged']['codes_equal']
                                                    and c['codes_and_settling_unchanged']['max_settle_change_lsb'] <= SETTLING_NOISE_LSB)
    c['residual_within_stage6']['met'] = c['residual_within_stage6']['value_lsb'] <= STAGE6_CLOSE_LIMIT_LSB
    outright = worst <= GATE_SCREEN_V
    disposition = all(x['met'] for x in conditions.values())
    return dict(rule='Layout/tools/analysis/gate_disposition.py docstring', decisions=['2026-11-22', '2026-11-23'],
                gate_screen_v=GATE_SCREEN_V, worst_gate_screen_v=worst, passed_outright=outright,
                conditions=conditions, passed_with_disposition=bool(not outright and disposition),
                verdict='pass' if outright else 'pass with disposition' if disposition else 'report to the user',
                runs=rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gate_run', nargs='?')
    ap.add_argument('--control')
    ap.add_argument('--pair', action='append', nargs='+', metavar='RUN',
                    help='R2_GATE OLD_RUN [OLD_GATE]: apply the disposition rule (repeat per stimulus)')
    ap.add_argument('--output')
    a = ap.parse_args()
    if bool(a.pair) == bool(a.gate_run):
        ap.error('Give either GATE_RUN or --pair')
    if a.pair:
        if any(len(p) not in (2, 3) for p in a.pair):
            ap.error('--pair takes R2_GATE OLD_RUN [OLD_GATE]')
        data = verdict([(p[0], p[1], p[2] if len(p) == 3 else None) for p in a.pair])
    else:
        data = dict(run=disturbance(a.gate_run))
    if a.gate_run and a.control:
        data['control_same_frame'] = disturbance(a.control, data['run']['frame'], data['run']['channel'])
        data['control_worst'] = disturbance(a.control)
        data['attributable'] = attributable(data['run'], data['control_same_frame'])
        data['frames'] = frames_compare(data['run']['source_run'], data['control_worst']['source_run'])
    text = json.dumps(data, indent=1) + '\n'
    if a.output:
        (ROOT / a.output).write_text(text, encoding='utf-8', newline='\n')
    print(text)
