"""Analysis-only terminal-voltage evidence for a completed all-terminal run, Python 2/3, standard library only.

Binds to a completed source run and reads its native waveform once through soa_events.cpp.
Writes over-limit intervals with native sample support, native-time excerpts of planned events,
a time-step review, and a cross-check against the source run's own analysis results.
The source run, its raw waveform and its derived results are never modified.
"""
from __future__ import print_function
import argparse
import gzip
import hashlib
import json
import os
import subprocess
from soa import over_intervals, sliding_max

TOLERANCE_S = 1e-15
TOLERANCE_V = 1e-9


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load(path):
    with open(path) as f:
        return json.load(f)


def build_pairs(topo, rule):
    """Same terminal-pair deduplication and ordering as soa.py, keeping device attribution."""
    thin = set(rule['scope']['thin_oxide_mos_models'] + rule['scope']['thin_oxide_moscap_models'])
    pairs, index, rows = [], {}, []
    for d in topo['devices']:
        pins = dict(zip('pn' if len(d['nodes']) == 2 else 'dgsb', [n.replace('\\', '').lower() for n in d['nodes']]))
        for pair in (['pn'] if len(pins) == 2 else ['gs', 'gd', 'ds', 'gb', 'bs', 'bd']):
            key = tuple(sorted((pins[pair[0]], pins[pair[1]])))
            covered = d['model'] in thin and pair in ('gs', 'gd', 'ds', 'pn')
            if key not in index:
                index[key] = len(pairs)
                pairs.append(dict(nodes=key, covered=False))
            i = index[key]
            pairs[i]['covered'] = pairs[i]['covered'] or covered
            rows.append(dict(instance=d['instance'], model=d['model'], terminal_pair=pair, pair_index=i, in_rule=covered))
    return pairs, rows


def reference_selftest(binary, scratch, limit):
    """Compare the compiled pass with the Python reference on a synthetic two-node waveform."""
    layout = os.path.join(scratch, 'selftest.layout')
    with open(layout, 'w') as f:
        f.write('2 1 %.17g\n0\nv\n1 0 1\n' % limit)
    points = [(0., 1.2), (30e-12, 1.2), (31e-12, 0.), (70e-12, 0.), (71e-12, -1.25),
              (160e-12, 1.25), (161e-12, limit), (300e-12, limit), (310e-12, 0.), (320e-12, 1.3), (330e-12, 0.)]
    wave = os.path.join(scratch, 'selftest.psf')
    with open(wave, 'w') as f:
        f.write('SWEEP\n"time" FLOAT\nTRACE\n"v" FLOAT\nVALUE\n')
        for t, v in points:
            f.write('"time" %.17g\n"v" %.17g\n' % (t, v))
        f.write('END\n')
    plan = os.path.join(scratch, 'selftest.events')
    with open(plan, 'w') as f:
        f.write('1\n0 %.17g %.17g\n' % (60e-12, 165e-12))
    out = os.path.join(scratch, 'selftest.json')
    subprocess.check_call([binary, wave, layout, plan, out])
    seen = load(out)

    def reference(pts):
        result = []
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            for a, b in over_intervals(t0, t1, v0, v1, limit):
                if result and result[-1][1] == a:
                    result[-1][1] = b
                else:
                    result.append([a, b])
        return result

    for observed, expected in ((seen['pairs'][0]['intervals'], reference(points)),
                               (seen['pairs'][0]['coarse_intervals'], reference(points[0::2]))):
        assert len(observed) == len(expected) and expected
        assert all(abs(x - y) < 1e-23 for o, e in zip(observed, expected) for x, y in zip(o[:2], e))
    assert seen['pairs'][0]['peak_abs_V'] == 1.3 and seen['count'] == len(points)
    rows = seen['events'][0]
    expected_rows = [p for p in points if 60e-12 <= p[0] <= 165e-12]
    assert len(rows) == 3 * len(expected_rows)
    assert all(rows[3 * i] == p[0] and rows[3 * i + 1] == p[1] and rows[3 * i + 2] == 0. for i, p in enumerate(expected_rows))
    # First fine interval spans several samples: support count and local step must be reported.
    assert all(len(i) == 4 and i[2] >= 0 and i[3] > 0 for i in seen['pairs'][0]['intervals'])
    return True


def analyze(run_dir, source_dir, output_dir):
    inputs = os.path.join(run_dir, 'inputs')
    src_inputs = os.path.join(source_dir, 'inputs')
    ctx = load(os.path.join(src_inputs, 'soa_context.json'))
    inventory_path = os.path.join(src_inputs, 'terminal_inventory.json')
    topo = load(inventory_path)
    rule = ctx['rule']
    limit, window = rule['limits']['continuous_V'], rule['limits']['window_s']
    peak_limit, over_limit = rule['limits']['peak_V'], rule['limits']['max_over_s']
    plan = load(os.path.join(inputs, 'excerpt_plan.json'))
    assert plan['source_run_id'] == ctx['run_id'] and plan['rule_sha256'] == ctx['rule_sha256'], 'Excerpt plan is for another run or rule'
    source_rows = load(os.path.join(source_dir, 'derived', 'terminal_results.json'))
    source_result = load(os.path.join(source_dir, 'derived', 'result.json'))
    pairs, rows = build_pairs(topo, rule)
    assert len(rows) == len(source_rows), 'Terminal inventory differs from the source analysis'
    for mine, theirs in zip(rows, source_rows):
        assert (mine['instance'], mine['terminal_pair']) == (theirs['instance'], theirs['terminal_pair']), 'Row order differs'
    by_key = dict(((r['instance'], r['terminal_pair']), r) for r in rows)
    events = []
    for e in plan['events']:
        row = by_key[(e['instance'], e['terminal_pair'])]
        events.append(dict(e, pair_index=row['pair_index'], nodes=list(pairs[row['pair_index']]['nodes'])))

    scratch = os.path.join(os.path.dirname(output_dir), 'soa_scratch')
    if not os.path.isdir(scratch):
        os.makedirs(scratch)
    binary = os.path.join(scratch, 'soa_events')
    subprocess.check_call(['g++', '-std=c++11', '-O2', os.path.join(inputs, 'soa_events.cpp'), '-o', binary])
    reference_selftest(binary, scratch, limit)

    nodes = sorted(set(n for p in pairs for n in p['nodes']) | set(['0']))
    index = dict((n, i) for i, n in enumerate(nodes))
    layout = os.path.join(scratch, 'layout.txt')
    with open(layout, 'w') as f:
        f.write('%d %d %.17g\n' % (len(nodes), len(pairs), limit))
        f.write('\n'.join(nodes) + '\n')
        for p in pairs:
            f.write('%d %d %d\n' % (index[p['nodes'][0]], index[p['nodes'][1]], int(p['covered'])))
    event_file = os.path.join(scratch, 'events.txt')
    with open(event_file, 'w') as f:
        f.write('%d\n' % len(events))
        for e in events:
            f.write('%d %.17g %.17g\n' % (e['pair_index'], e['excerpt_s'][0], e['excerpt_s'][1]))
    raw = os.path.join(source_dir, 'raw', 'tran_short.tran.tran')
    raw_stat = os.stat(raw)
    scan_path = os.path.join(scratch, 'scan.json')
    subprocess.check_call([binary, raw, layout, event_file, scan_path])
    scan = load(scan_path)
    stop = scan['stop']
    assert abs(stop - ctx['expected_stop_s']) <= 1e-14, 'Incomplete transient'
    assert scan['count'] == source_result['native_points'], 'Native point count differs from the source analysis'

    # Recompute per-pair statistics and compare with the source run's own results.
    mismatches, detail = [], []
    flips, worst_delta = [], []
    fine_pulses = []
    for i, (p, r) in enumerate(zip(pairs, scan['pairs'])):
        if not p['covered']:
            continue
        fine = [[a, b] for a, b, n, dt in r['intervals']]
        slide, at = sliding_max(fine, window, stop)
        total = sum(b - a for a, b in fine)
        coarse_slide, coarse_at = sliding_max(r['coarse_intervals'], window, stop)
        coarse_total = sum(b - a for a, b in r['coarse_intervals'])
        p.update(peak=r['peak_abs_V'], peak_time=r['peak_time_s'], intervals=r['intervals'], slide=slide,
                 slide_end=at, total=total, count=len(fine))
        numeric = r['peak_abs_V'] <= peak_limit and slide <= over_limit
        coarse_numeric = r['coarse_peak_abs_V'] <= peak_limit and coarse_slide <= over_limit
        if numeric != coarse_numeric:
            flips.append(i)
        worst_delta.append((abs(slide - coarse_slide), abs(r['peak_abs_V'] - r['coarse_peak_abs_V']), abs(total - coarse_total), i))
        for a, b, n, dt in r['intervals']:
            fine_pulses.append((b - a, n, dt, i))
    for mine, theirs in zip(rows, source_rows):
        if not mine['in_rule']:
            continue
        p = pairs[mine['pair_index']]
        bad = []
        if abs(p['peak'] - theirs['peak_abs_V']) > TOLERANCE_V:
            bad.append('peak_abs_V')
        if abs(p['peak_time'] - theirs['peak_time_s']) > TOLERANCE_S:
            bad.append('peak_time_s')
        if p['count'] != theirs['over_pulse_count']:
            bad.append('over_pulse_count')
        if abs(p['total'] - theirs['total_over_s']) > TOLERANCE_S:
            bad.append('total_over_s')
        if abs(p['slide'] - theirs['max_sliding_over_s']) > TOLERANCE_S:
            bad.append('max_sliding_over_s')
        if bad:
            mismatches.append(dict(instance=mine['instance'], terminal_pair=mine['terminal_pair'], fields=bad))
    reproduces = not mismatches

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    files = {}

    def write_gz(name, text):
        path = os.path.join(output_dir, name)
        with gzip.open(path, 'wb') as f:
            f.write(text.encode('utf-8'))
        files[name] = dict(sha256=digest(path), bytes=os.path.getsize(path))

    # Over-limit intervals per physical terminal pair, with every device row that shares the pair.
    members = {}
    for r in rows:
        if r['in_rule']:
            members.setdefault(r['pair_index'], []).append(dict(instance=r['instance'], model=r['model'], terminal_pair=r['terminal_pair']))
    listing = []
    for i, p in enumerate(pairs):
        if p['covered'] and p['intervals']:
            listing.append(dict(nodes=list(p['nodes']), devices=members[i], peak_abs_V=p['peak'], peak_time_s=p['peak_time'],
                                max_sliding_over_s=p['slide'], worst_window_end_s=p['slide_end'], total_over_s=p['total'],
                                fields=['start_s', 'end_s', 'native_samples_inside', 'native_step_s'], intervals=p['intervals']))
    write_gz('over_limit_intervals.json.gz', json.dumps(dict(schema_version=1, run_id=ctx['run_id'], rule_id=rule['rule_id'],
                                                              limit_V=limit, window_s=window, pairs=listing), indent=1) + '\n')

    # Native-time excerpts at full resolution.
    lines = ['event,time_s,v_node_a,v_node_b,v_ab']
    index_rows = []
    for e, data in zip(events, scan['events']):
        samples = [(data[k], data[k + 1], data[k + 2]) for k in range(0, len(data), 3)]
        assert samples, 'Empty excerpt for ' + e['id']
        top = max(samples, key=lambda s: abs(s[1] - s[2]))
        within = [s for s in samples if e['span_s'][0] <= s[0] <= e['span_s'][1]]
        pair_stats = pairs[e['pair_index']]
        for t, a, b in samples:
            lines.append('%s,%.17g,%.17g,%.17g,%.17g' % (e['id'], t, a, b, a - b))
        index_rows.append(dict(id=e['id'], kind=e['kind'], reason=e['reason'], instance=e['instance'], terminal_pair=e['terminal_pair'],
                               nodes=e['nodes'], span_s=e['span_s'], excerpt_s=e['excerpt_s'], samples=len(samples),
                               first_sample_s=samples[0][0], last_sample_s=samples[-1][0],
                               max_native_step_in_excerpt_s=max([y[0] - x[0] for x, y in zip(samples, samples[1:])] or [0.]),
                               excerpt_peak_abs_V=abs(top[1] - top[2]), excerpt_peak_time_s=top[0],
                               pair_peak_abs_V=pair_stats.get('peak'), pair_peak_time_s=pair_stats.get('peak_time'),
                               samples_inside_span=len(within),
                               contains_pair_peak=(pair_stats.get('peak_time') is not None and
                                                   samples[0][0] <= pair_stats['peak_time'] <= samples[-1][0])))
    write_gz('native_excerpts.csv.gz', '\n'.join(lines) + '\n')

    # Time-step review from the native waveform and a 2x decimated screen.
    durations = [d for d, n, dt, i in fine_pulses]
    ratios = [d / dt for d, n, dt, i in fine_pulses]
    top_delta = sorted(worst_delta, reverse=True)[:10]
    review = dict(
        schema_version=1, run_id=ctx['run_id'], method='analysis_only_native_resolution_review',
        native_points=scan['count'], native_end_s=stop, max_native_step_s=scan['max_dt'],
        step_histogram_upper_edges_s=[0.5e-12, 1e-12, 1.5e-12, 2e-12, 3e-12, 5e-12, 10e-12, 20e-12, 50e-12, None],
        step_histogram_counts=scan['dt_hist'],
        over_limit_pulses=len(fine_pulses),
        min_pulse_duration_s=min(durations) if durations else None,
        min_pulse_duration_over_local_step=min(ratios) if ratios else None,
        pulses_with_fewer_than_3_native_samples=sum(1 for d, n, dt, i in fine_pulses if n < 3),
        pulses_with_no_native_sample_inside=sum(1 for d, n, dt, i in fine_pulses if n == 0),
        decimation=dict(
            description='Every second native sample, same piecewise-linear screen; no finer simulator step was run.',
            covered_pairs=sum(1 for p in pairs if p['covered']),
            verdict_flips=len(flips),
            max_abs_delta_peak_V=max([d[1] for d in worst_delta] or [0.]),
            max_abs_delta_sliding_over_s=max([d[0] for d in worst_delta] or [0.]),
            max_abs_delta_total_over_s=max([d[2] for d in worst_delta] or [0.]),
            largest_sliding_changes=[dict(nodes=list(pairs[i]['nodes']), delta_sliding_over_s=d0, delta_peak_V=d1, delta_total_over_s=d2,
                                          devices=members[i][:3]) for d0, d1, d2, i in top_delta]),
        limitation='Piecewise-linear screen of the saved native points. Peaks narrower than the native step cannot be recovered; '
                   'a convergence statement for a finer simulator step needs a new run.')
    path = os.path.join(output_dir, 'time_step_review.json')
    with open(path, 'w') as f:
        json.dump(review, f, indent=2)
        f.write('\n')
    files['time_step_review.json'] = dict(sha256=digest(path), bytes=os.path.getsize(path))

    result = dict(
        analysis_complete=True, run_id=os.path.basename(run_dir), source_run_id=ctx['run_id'], corner=ctx['corner'],
        rule_id=rule['rule_id'], rule_sha256=ctx['rule_sha256'],
        inventory_sha256=digest(inventory_path), source_verdict=source_result['verdict'],
        source_violation_pair_count=source_result['violation_pair_count'],
        reproduces_source_analysis=reproduces, mismatch_count=len(mismatches), mismatches=mismatches[:50],
        compiled_selftest_passed=True,
        native_points=scan['count'], native_end_s=stop, max_native_step_s=scan['max_dt'],
        raw_waveform=dict(path=raw, bytes=raw_stat.st_size, mtime_ns=getattr(raw_stat, 'st_mtime_ns', int(raw_stat.st_mtime * 1e9)),
                          device=raw_stat.st_dev, inode=raw_stat.st_ino),
        pairs_with_over_limit_intervals=len(listing), over_limit_pulses=len(fine_pulses),
        excerpt_count=len(index_rows), excerpts=index_rows, files=files,
        time_step_review=dict((k, review[k]) for k in ('max_native_step_s', 'pulses_with_fewer_than_3_native_samples',
                                                        'pulses_with_no_native_sample_inside', 'min_pulse_duration_over_local_step')),
        decimation_verdict_flips=len(flips),
        limitations=['Reads saved native points only; piecewise-linear between points.',
                     'Same coverage as the source run: stimulus, corner, thin-oxide rule scope. Body pairs and thick-oxide devices are not qualified.',
                     'No finer simulator step was run; the decimation check is a sensitivity estimate, not a convergence proof.'])
    path = os.path.join(output_dir, 'result.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--source-run-dir', required=True)
    args = p.parse_args()
    analyze(args.run_dir, args.source_run_dir, args.output_dir)
