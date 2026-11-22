"""Record of the Bootstrap boosted-gate margin at SS cold and the Bootstrap core corner extractions (issue #12).

Reads only digest-verified collected results: the analysis-only gate jobs (measure_bootstrap_gate.py) on the
SS-cold ADC runs with each Bootstrap variant, the SS-cold Stage 2 stimuli rerun with the CWORST_T Bootstrap
(run family allxc) and their Stage 2 counterparts, and the parasitic summary of the three extractions.
  python -m Layout.tools.analysis.bootstrap_corner_summary --output results/integration/NAME.json
      [--excerpt results/integration/NAME.csv] [--figure results/integration/NAME.png]
"""
import argparse
import csv
import hashlib
import io
import json

from Layout.project import ROOT, evidence
from Layout.tools.analysis import bootstrap_parasitics, stage2_summary
from Layout.tools.simulation.prepare_full_sim import pull

RUNS = stage2_summary.RUNS
GATE_LIMIT_V = .1
# SS-cold gate jobs, from the two-finger schematic control to the CWORST_T extraction.
GATE = [
    dict(key='sch2', label='2-finger schematic', run='sar8-sebit-ssc-cw-verify-b-gate'),
    dict(key='sch4', label='4-finger schematic', run='sar8-sepl-ssc-cw-verify-r3cw-gate'),
    dict(key='ext4_sebit', label='4-finger extracted, typical RC (cell-LPE deck)', run='sar8-sebit-ssc-cw-verify-bootx-a-gate'),
    dict(key='ext4_typ', label='4-finger extracted, typical RC (Stage 2)', run='sar8-allx-ssc-verify-a-gate'),
    dict(key='ext4_cw', label='4-finger extracted, CWORST_T', run='sar8-allxc-ssc-verify-a-gate'),
    dict(key='ext4_cw_extreme', label='4-finger extracted, CWORST_T, extreme stimulus', run='sar8-allxc-ssc-extreme-a-gate'),
]
# Corner-Bootstrap rerun and the Stage 2 run of the same stimulus.
PAIRS = [('sar8-allxc-ssc-verify-a', 'sar8-allx-ssc-verify-a'), ('sar8-allxc-ssc-extreme-a', 'sar8-allx-ssc-extreme-b'),
         ('sar8-allxc-ssc-carry-a', 'sar8-allx-ssc-carry-a'), ('sar8-allxc-ssc-restart-a', 'sar8-allx-ssc-restart-a')]
EXTRACTIONS = ['boot-core-20261121', 'boot-core-20261121-cworst-t', 'boot-core-20261121-cbest-t']
LEVELS_V = (.5, .4, .3, .2)
WORST = dict(frame=1, channel='n')


def collected_file(run_id, name):
    root = RUNS / run_id
    data = (root / 'collected' / name).read_bytes()
    receipt = json.loads((root / 'collected/collection_receipt.json').read_bytes())
    digest = hashlib.sha256(data).hexdigest()
    if not any(f['name'] == name and f['sha256'] == digest for f in receipt['files']):
        raise ValueError('Collected %s does not match its receipt: %s' % (name, run_id))
    return data, digest


def excerpt(run_id, frame, side):
    data, digest = collected_file(run_id, 'derived/gate_excerpt.csv')
    rows = [r for r in csv.DictReader(io.StringIO(data.decode())) if int(r['frame']) == frame]
    return [(float(r['after_close_ns']), float(r['g_' + side]) - min(float(r['vin' + side]), float(r['top' + side])),
             float(r['g_' + side])) for r in rows], digest


def fall_rates(points):
    """dG/dt (V/ns) where G first falls through each level, over +/-2 native excerpt points."""
    t, g = [p[0] for p in points], [p[2] for p in points]
    out = {}
    for level in LEVELS_V:
        i = next((k for k in range(1, len(g)) if g[k - 1] > level >= g[k]), None)
        if i is not None:
            lo, hi = max(i - 3, 0), min(i + 2, len(t) - 1)
            out['%g' % level] = (g[lo] - g[hi]) / (t[hi] - t[lo])
    return out


def gate_row(spec):
    data, digest = collected_file(spec['run'], 'derived/result.json')
    result = json.loads(data)
    recipe = json.loads((RUNS / spec['run'] / 'recipe.json').read_bytes())
    source = recipe['test_conditions']['split_source_run_id']
    src = json.loads((RUNS / source / 'recipe.json').read_bytes())
    frames = []
    for f in result['frames']:
        for s in 'pn':
            c = f['channels'][s]
            frames.append(dict(frame=f['frame'], channel=s, vin_v=c['vin_v'], boost_v=c['boost_v'],
                               onset_ns=c['onset_ns'], max_fall_v_per_ns=c['max_fall_v_per_ns'],
                               below_0p1_v_ns=c['below_ns']['0.1'], below_0_v_ns=c['below_ns']['0'],
                               first_compare_after_close_ns=f['first_compare_after_close_ns'],
                               overdrive_at_first_compare_v=c['overdrive_at_first_compare_v'],
                               overdrive_at_1p3_ns_v=c['overdrive_at_v'].get('1.3'),
                               settled_overdrive_v=c['settled_overdrive_v']))
    worst = next(x for x in frames if x['frame'] == WORST['frame'] and x['channel'] == WORST['channel'])
    points, excerpt_sha = excerpt(spec['run'], WORST['frame'], WORST['channel'])
    return dict(spec, source_run_id=source, result_sha256=digest, excerpt_sha256=excerpt_sha,
                recipe_sha256=json.loads((RUNS / spec['run'] / 'registration.json').read_bytes())['recipe_hash'],
                bootstrap=result['bootstrap'].rsplit('/', 1)[-1], gate_probe=result['gate_probe'],
                source_scope=src['qualification_scope'], worst=result['worst'],
                worst_channel_frame_1=dict(worst, fall_rate_v_per_ns_at_g=fall_rates(points)), frames=frames), points


def extraction(identity):
    manifest = json.loads(pull(evidence(identity) + '/manifest.json'))
    para = bootstrap_parasitics.summarize(identity)
    para.pop('method')
    info = manifest['decks']['pex']['support'].get('interconnect_rc', {})
    return dict(identity=identity, interconnect_rc=manifest.get('interconnect_rc', 'typical'),
                gds_sha256=manifest['gds']['sha256'], pex_sha256=manifest['checks']['pex']['sha256'],
                pex_companion_sha256=manifest['checks']['pex']['companion_sha256'],
                job_deck_sha256=manifest['decks']['pex']['job_sha256'],
                derived_from=manifest.get('derived_from'), drc_lvs_inherited_from=manifest.get('drc_lvs_inherited_from'),
                lvs=manifest['checks']['lvs']['verdict'], drc_markers=manifest['checks']['drc']['markers_by_rule'],
                foundry_rules=dict((k, info[k]) for k in ('archive', 'archive_sha256', 'effective_rules_sha256') if k in info),
                parasitics=para)


def compare(new_id, old_id):
    new, old = stage2_summary.summarize(new_id), stage2_summary.summarize(old_id)
    keep = ('run_id', 'recipe_sha256', 'result_sha256', 'kind', 'bootstrap', 'codes_within_1', 'events_8_8', 'pin_pass',
            'max_abs_close_error_lsb', 'close_pass', 'max_abs_signed_settling_lsb', 'max_weighted_bound_lsb',
            'settling_pass', 'min_read_margin_ns', 'margin_pass', 'max_first_compare_gate_overdrive_v',
            'setup_hold_slack_ps', 'warnings', 'passed', 'comparisons', 'updates', 'public_read_codes')
    row = dict((k, new[k]) for k in keep if k in new)
    row['stage2'] = dict((k, old[k]) for k in keep if k in old)
    if new['kind'] != 'restart':
        row['frames'] = [dict((k, f[k]) for k in ('frame', 'warmup', 'input_code', 'code', 'target', 'code_error',
                                                   'close_error_lsb', 'max_abs_signed_settling_lsb', 'read_margin_ns',
                                                   'first_compare_gate_overdrive_v')) for f in new['frames']]
        row['gate_pass'] = new['max_first_compare_gate_overdrive_v'] <= GATE_LIMIT_V
        row['all_pass'] = bool(new['codes_within_1'] and new['events_8_8'] and new['pin_pass'] and new['close_pass']
                               and new['settling_pass'] and new['margin_pass'] and row['gate_pass'])
    else:
        row['all_pass'] = bool(new['passed'])
    return row


def figure(path, series):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']
    ink, muted, surface = '#0b0b0b', '#52514e', '#fcfcfb'
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=surface)
    for ax in (a, b):
        ax.set_facecolor(surface)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        for side in ('left', 'bottom'):
            ax.spines[side].set_color(muted)
        ax.tick_params(colors=muted, labelsize=8)
        ax.grid(True, color='#e4e3df', linewidth=.6)
    a.axhline(GATE_LIMIT_V, color=muted, linewidth=1, linestyle=(0, (4, 3)))
    a.text(2.95, GATE_LIMIT_V + .012, '0.1 V screen', color=muted, fontsize=8, ha='right')
    ends = []
    for (row, points), color in zip(series, colors):
        t = [p[0] for p in points if p[0] <= 3]
        w = row['worst_channel_frame_1']
        a.plot(t, [p[1] for p in points if p[0] <= 3], color=color, linewidth=2,
               label='%s: %+.3f V' % (row['label'], w['overdrive_at_first_compare_v']))
        a.plot([w['first_compare_after_close_ns']], [w['overdrive_at_first_compare_v']], 'o', color=color, markersize=8,
               markeredgecolor=surface, markeredgewidth=2)
        rates = w['fall_rate_v_per_ns_at_g']
        levels = sorted(rates, key=float, reverse=True)
        b.plot([float(x) for x in levels], [rates[x] for x in levels], color=color, linewidth=2, marker='o', markersize=8,
               markeredgecolor=surface, markeredgewidth=2, label=row['label'])
        ends.append([rates[levels[-1]], float(levels[-1]), row['label']])
    # Direct labels at the last point, spaced so that neighbouring series do not overlap.
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + .13)
    for y, x, label in ends:
        b.annotate(label, (x, y), xytext=(8, 0), textcoords='offset points', color=ink, fontsize=7.5, va='center')
    a.set_xlim(0, 3)
    a.set_ylim(-.05, .85)
    a.set_xlabel('Time after SEQ_SAMPLE falls (ns)', color=ink, fontsize=9)
    a.set_ylabel('G - min(VIN, TOP) (V)', color=ink, fontsize=9)
    a.set_title('Main-switch gate, frame 1, VINN = 0 V; dot = first comparator clock', color=ink, fontsize=9, loc='left')
    b.set_xlim(.55, .1)
    b.set_xlabel('G (V)', color=ink, fontsize=9)
    b.set_ylabel('Fall rate of G (V/ns)', color=ink, fontsize=9)
    b.set_title('Discharge rate at matched gate voltage', color=ink, fontsize=9, loc='left')
    a.legend(loc='upper right', fontsize=7.5, frameon=False, labelcolor=ink, title='At the first comparator clock',
             title_fontsize=7.5, alignment='left')
    fig.suptitle('Bootstrap hold-phase gate discharge, SS 0.81 V -40 C', color=ink, fontsize=10, x=.01, ha='left')
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=surface)


def record():
    gates, series = [], []
    for spec in GATE:
        row, points = gate_row(spec)
        gates.append(row)
        if spec['key'] in ('sch2', 'sch4', 'ext4_typ', 'ext4_cw'):
            series.append((row, points))
    by = dict((g['key'], g['worst_channel_frame_1']) for g in gates)

    def ratio(a, b):
        return dict((k, by[a]['fall_rate_v_per_ns_at_g'][k] / by[b]['fall_rate_v_per_ns_at_g'][k])
                    for k in by[a]['fall_rate_v_per_ns_at_g'] if k in by[b]['fall_rate_v_per_ns_at_g'])
    decomposition = dict(
        below_0p1_v_ns=dict((k, by[k]['below_0p1_v_ns']) for k in by),
        added_by_four_fingers_ns=by['sch4']['below_0p1_v_ns'] - by['sch2']['below_0p1_v_ns'],
        added_by_extraction_ns=by['ext4_typ']['below_0p1_v_ns'] - by['sch4']['below_0p1_v_ns'],
        added_by_cworst_ns=by['ext4_cw']['below_0p1_v_ns'] - by['ext4_typ']['below_0p1_v_ns'],
        fall_rate_ratio_four_fingers=ratio('sch2', 'sch4'), fall_rate_ratio_extraction=ratio('sch4', 'ext4_typ'),
        fall_rate_ratio_extraction_cell_lpe_deck=ratio('sch4', 'ext4_sebit'), fall_rate_ratio_cworst=ratio('ext4_typ', 'ext4_cw'))
    runs = [compare(n, o) for n, o in PAIRS]
    return dict(issue='https://github.com/chenzc24/sar-adc-t28/issues/12', date='2026-11-22',
                subject='Bootstrap boosted-gate margin at SS 0.81 V -40 C and Bootstrap core corner extractions',
                limits=dict(gate_screen_v=GATE_LIMIT_V,
                            close_error_lsb=stage2_summary.CLOSE_LIMIT_LSB, plate_settling_lsb=stage2_summary.SETTLING_LIMIT_LSB,
                            ssc_read_margin_ns=stage2_summary.SSC_MARGIN_NS, codes='gain-corrected target +/-1 code',
                            events='8 compares and 8 updates per frame; restart passes'),
                extractions=[extraction(i) for i in EXTRACTIONS], gate=gates, decomposition=decomposition,
                ssc_cworst_bootstrap=runs, ssc_cworst_bootstrap_all_pass=all(r['all_pass'] for r in runs),
                entry='Layout/tools/simulation/prepare_all_extracted.py'), series


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', required=True)
    ap.add_argument('--excerpt', help='CSV of the worst-channel gate traces of the plotted runs')
    ap.add_argument('--figure')
    a = ap.parse_args()
    data, series = record()
    (ROOT / a.output).write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8', newline='\n')
    if a.excerpt:
        with open(ROOT / a.excerpt, 'w', newline='\n', encoding='utf-8') as stream:
            w = csv.writer(stream, lineterminator='\n')
            w.writerow(['run_id', 'frame', 'channel', 'after_close_ns', 'g_v', 'overdrive_v'])
            for row, points in series:
                w.writerows([row['run'], WORST['frame'], WORST['channel'], '%.4f' % t, '%.5f' % g, '%.5f' % od]
                            for t, od, g in points)
    if a.figure:
        figure(ROOT / a.figure, series)
