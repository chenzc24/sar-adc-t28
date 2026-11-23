"""Reduce collected Stage 6 runs (issue #12) to a record under results/integration.

Scores each frame run with the Stage 6 column of #12: codes within the gain-corrected target +/-1 (k from the
standalone XREF/CDAC of the same extraction and MOS corner); acquisition residual at sample close <= 0.25 LSB;
plate settling at each decision <= 0.25 LSB; margin to the 90 ns read > 1 ns at every corner; 8 compares and
updates per frame; restart passes. Plate settling is scored on the signed error against the nominal rails and on
the weighted bound against the instantaneous trunk rails; where an analysis-only split (`-split`) exists, the
static reference-pin offset is reported separately and the settling verdict also uses the error without it.
Attached analysis-only jobs, when collected: `-rails` (Stage 1 rail budget), `-split`, `-gate` (Bootstrap gate).
  python -m Layout.tools.analysis.stage6_summary spec.json --output results/integration/NAME.json
spec.json: {"title": ..., "runs": {"ssc": [RUN_ID, ...], ...}, "notes": {...}}
"""
import argparse
import json

from Layout.project import ROOT
from Layout.tools.analysis import stage2_summary as s2

CLOSE_LIMIT_LSB = .25
SETTLING_LIMIT_LSB = .25
MARGIN_NS = 1.
GATE_SCREEN_V = .1


def attached(run_id, suffix):
    rid = run_id + '-' + suffix
    if not (s2.RUNS / rid / 'collected/derived/result.json').exists():
        return None
    result, recipe, digest = s2.collected(rid)
    return rid, result, recipe, digest


def run_row(run_id):
    row = s2.summarize(run_id)
    recipe = json.loads((s2.RUNS / run_id / 'recipe.json').read_bytes())
    ctx = recipe['test_conditions']
    row.update(stage6=ctx.get('stage6'), bootstrap=(ctx.get('bootstrap_physical_evidence') or '').rsplit('/', 1)[-1])
    if row['kind'] == 'restart':
        row['stage6_pass'] = bool(row['passed'])
        return row
    scored = [f for f in row['frames'] if not f['warmup']]
    settling = row['max_abs_signed_settling_lsb'] <= SETTLING_LIMIT_LSB and row['max_weighted_bound_lsb'] <= SETTLING_LIMIT_LSB
    split = attached(run_id, 'split')
    if split:
        rid, res, rec, digest = split
        row['reference_split'] = dict(run_id=rid, recipe_sha256=rec['recipe_hash'], result_sha256=digest,
                                      quiet_pin_offset_mv={k: max(v, key=abs) for k, v in res['quiet_pin_offset_mv'].items()},
                                      max_abs_lsb=res['max_abs'])
        row['settling_excluding_static_lsb'] = res['max_abs']['excluding_static_lsb']
        settling = settling or (res['max_abs']['excluding_static_lsb'] <= SETTLING_LIMIT_LSB
                                and row['max_weighted_bound_lsb'] <= SETTLING_LIMIT_LSB)
    # The static/switching split with the 88-98 ns quiet window (-rails3) supersedes -rails2 (75-95 ns, which caught
    # the SS-cold conversion tail) and the totals-only rail job (-rails).
    rails = attached(run_id, 'rails3') or attached(run_id, 'rails2') or attached(run_id, 'rails')
    if rails:
        rid, res, rec, digest = rails
        row['rails'] = dict(run_id=rid, recipe_sha256=rec['recipe_hash'], result_sha256=digest, all_pass=res['all_pass'],
                            all_pass_total=res.get('all_pass_total'), static=res.get('static'),
                            verdict_total=res.get('verdict_total'),
                            verdict=res['verdict'], where=res['where'])
    gate = attached(run_id, 'gate')
    if gate:
        rid, res, rec, digest = gate
        row['bootstrap_gate'] = dict(run_id=rid, result_sha256=digest,
                                     summary={k: v for k, v in res.items() if k not in ('frames', 'channels', 'excerpt')})
    row.update(
        stage6_codes=row['codes_within_1'], stage6_events=row['events_8_8'] and all(f['handoff_pass'] for f in scored),
        stage6_close=row['max_abs_close_error_lsb'] <= CLOSE_LIMIT_LSB, stage6_settling=bool(settling),
        stage6_margin=row['min_read_margin_ns'] is not None and row['min_read_margin_ns'] > MARGIN_NS,
        bootstrap_gate_screen_pass=row['max_first_compare_gate_overdrive_v'] <= GATE_SCREEN_V)
    row['stage6_pass'] = bool(row['stage6_codes'] and row['stage6_events'] and row['stage6_close'] and row['stage6_settling']
                              and row['stage6_margin'] and row['pin_pass'])
    return row


def record(spec):
    runs = {corner: [run_row(r) for r in ids] for corner, ids in spec['runs'].items()}
    verdict = {}
    for corner, rows in runs.items():
        frames = [r for r in rows if r['kind'] != 'restart']
        restart = [r for r in rows if r['kind'] == 'restart']
        verdict[corner] = dict(
            runs=len(rows), all_pass=all(r['stage6_pass'] for r in rows),
            restart_pass=all(r['stage6_pass'] for r in restart) if restart else None,
            min_read_margin_ns=min(r['min_read_margin_ns'] for r in frames) if frames else None,
            max_abs_close_error_lsb=max(r['max_abs_close_error_lsb'] for r in frames) if frames else None,
            max_abs_signed_settling_lsb=max(r['max_abs_signed_settling_lsb'] for r in frames) if frames else None,
            max_weighted_bound_lsb=max(r['max_weighted_bound_lsb'] for r in frames) if frames else None,
            max_settling_excluding_static_lsb=max([r['settling_excluding_static_lsb'] for r in frames
                                                   if 'settling_excluding_static_lsb' in r] or [None]),
            max_first_compare_gate_overdrive_v=max(r['max_first_compare_gate_overdrive_v'] for r in frames) if frames else None,
            rails_all_pass=all(r['rails']['all_pass'] for r in frames if 'rails' in r) if any('rails' in r for r in frames) else None,
            # A recorded user disposition (Layout/results/current.json integration.decisions), not a limit change.
            rails_disposition=spec.get('dispositions', {}).get(corner))
    return dict(issue='https://github.com/chenzc24/sar-adc-t28/issues/12', title=spec.get('title'),
                limits=dict(codes='gain-corrected target +/-1', close_error_lsb=CLOSE_LIMIT_LSB,
                            plate_settling_lsb=SETTLING_LIMIT_LSB, read_margin_ns='> %g at every corner' % MARGIN_NS,
                            events='8 compares and updates per frame; restart passes',
                            bootstrap_gate_screen_v=GATE_SCREEN_V),
                notes=spec.get('notes', {}), verdict=verdict, runs=runs)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('--output')
    a = ap.parse_args()
    data = record(json.loads((ROOT / a.spec).read_text(encoding='utf-8')))
    text = json.dumps(data, indent=1) + '\n'
    if a.output:
        (ROOT / a.output).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / a.output).write_text(text, encoding='utf-8', newline='\n')
    else:
        print(text)
