"""Read-only local review of collected first-event v1; never mutate frozen inputs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np
import yaml

import prepare_first_event as source_review

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[2]
RUN = 'sar8audit-ctrl-first-event-v1'
OUT = OWN / 'first_event_results_v1'
PREFIX = 'xdut.xctrl.xtim.'
RECIPE_SHA = '587e794d928d6f25fa64ce7749d1d613fd0dd6fe3e1e46b7554b1dd1efb74ae7'


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def collect_readonly():
    folder = ROOT / 'output/managed_execution/runs' / RUN / 'collected'
    receipt_path = folder / 'collection_receipt.json'
    receipt = json.loads(receipt_path.read_bytes())
    if receipt['skipped']:
        raise ValueError('Collection has skipped files')
    members, verified = {}, []
    for item in receipt['files']:
        relative = Path(item['name'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe collected member')
        path = folder / relative
        if not path.exists() or sha(path.read_bytes()) != item['sha256']:
            path = path.with_name(path.stem + '.' + item['sha256'][:12] + path.suffix)
        blob = path.read_bytes()
        if len(blob) != item['bytes'] or sha(blob) != item['sha256']:
            raise ValueError('Collection hash/size mismatch: ' + item['name'])
        members[item['name']] = blob
        verified.append(item)
    if sum(f['bytes'] for f in verified) != receipt['total_bytes']:
        raise ValueError('Receipt total mismatch')
    registration = yaml.safe_load((ROOT / 'management/runs' / (RUN + '.yaml')).read_text())
    recipe = registration['recipe']
    canonical = json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()
    if sha(canonical) != RECIPE_SHA or registration['recipe_hash'] != RECIPE_SHA:
        raise ValueError('Registered recipe mismatch')
    frozen = []
    for item in recipe['files']:
        original = (ROOT / item['source']).read_bytes()
        packed = (folder.parent / 'inputs' / item['name']).read_bytes()
        if sha(original) != item['sha256'] or original != packed:
            raise ValueError('Frozen input changed: ' + item['name'])
        frozen.append(dict(name=item['name'], bytes=len(packed), sha256=item['sha256']))
    states = {name: json.loads(members[name + '.state.json']) for name in ['simulation', 'analysis']}
    for name, state in states.items():
        if state['status'] != 'complete' or state['exit_code'] != 0:
            raise ValueError('Incomplete managed ' + name)
    native = states['simulation']['native']
    if not native['native_analysis_pass'] or not native['zero_error_footer']:
        raise ValueError('Native completion evidence missing')
    result = json.loads(members['derived/result.json'])
    if (not result['analysis_complete'] or not result['native_PSF_END']
            or result['missing_required_signals'] or result['acceptance_pass'] is not None):
        raise ValueError('Frozen reducer contract differs')
    columns = json.loads(members['derived/peak.columns.json'])['names']
    table = np.frombuffer(members['derived/peak.native.bin'], '<f8').reshape((-1, len(columns)))
    if (len(table) != result['diagnostic_points'] or not np.isfinite(table).all()
            or not np.all(np.diff(table[:, 0]) > 0)):
        raise ValueError('Invalid collected native table')
    measure_blob = (folder.parent / 'inputs/measurement.json').read_bytes()
    if sha(measure_blob) != result['measurement_sha256']:
        raise ValueError('Measurement identity mismatch')
    measure = json.loads(measure_blob)
    required = {n.lower() for n in measure['current_saves']}
    if (len(required) != 416 or not required <= set(result['trace_bindings'])
            or not required <= set(result['voltage_and_current_extrema'])):
        raise ValueError('Required native terminal currents incomplete')
    proof = dict(recipe_sha256=RECIPE_SHA, receipt_sha256=sha(receipt_path.read_bytes()),
        receipt_files=verified, receipt_total_bytes=receipt['total_bytes'],
        frozen_input_hashes_verified=frozen, native_points_reported=result['native_points'],
        local_diagnostic_rows=len(table), full_raw_available_locally=False,
        completion_evidence='Frozen checked reducer reports raw END/5917 points and native logStatus PASS; local table has 1836 diagnostic rows only.',
        simulation_peak_rss_bytes=states['simulation']['peak_rss_bytes'],
        analysis_peak_rss_bytes=states['analysis']['peak_rss_bytes'])
    return table, columns, result, measure, proof, members, native


def get(table, names, name):
    return table[:, names.index(name.lower())]


def integrate_native(t, currents, first, last):
    """Trapezoids on actual native rows only; endpoints are existing rows."""
    selection = (t >= first) & (t <= last)
    st, si = t[selection], currents[selection]
    if len(st) < 2:
        raise ValueError('Native integration window too short')
    increments = -.5 * (si[1:] + si[:-1]) * np.diff(st)[:, None]
    cumulative = np.vstack([np.zeros(si.shape[1]), np.cumsum(increments, axis=0)])
    return st, cumulative


def topology_missing_loads():
    source = ROOT / 'output/managed_execution/runs' / source_review.SOURCE_RUN / 'inputs/dut.scs'
    text = source.read_text()
    blocks = source_review.cells(text)
    ports = blocks['sar_adc8_join_r4'].replace('\\\n', ' ').splitlines()[0].split()[2:]
    all_leaves = source_review.flatten(text, 'sar_adc8_join_r4', dict(zip(ports, ports)))
    retained = json.loads((OWN / 'first_event_v1/device_identity.json').read_text())['retained_native_devices']
    cuts = {}
    for local in ['SN', 'LIVE', 'Q1', 'CLOCK_RESET', 'QUIET', 'PR', 'NR', 'WD', 'X020.N']:
        node = 'XDUT.XCTRL.XTIM.' + local
        loads = []
        for name, item in all_leaves.items():
            if name in retained:
                continue
            for port, connected in enumerate(item['nodes'], 1):
                if connected == node:
                    loads.append(dict(instance=name, port=port, model=item['model'], nodes=item['nodes'],
                                      parameters=item['parameters']))
        cuts[node] = loads
    return cuts


def supplementary_saved_signals():
    """Prove proposed follow-up signals were actually requested in native decks."""
    names = [PREFIX + suffix for suffix in ['sn', 'ud', 'write_req', 'x010.n', 'x010.x000.mid',
                                           'x014.n', 'x014.x000.mid', 'x001.n', 'x001.x000.mid']]
    source_test = ROOT / 'output/managed_execution/runs' / source_review.SOURCE_RUN / 'inputs/test.scs'
    fixture_test = OWN / 'first_event_v1/test.scs'
    requested = {}
    for label, path in [('source', source_test), ('fixture', fixture_test)]:
        saves = set(re.findall(r'(?mi)^save\s+(\S+)', path.read_text().lower()))
        requested[label] = {name: name in saves for name in names}
    return dict(proposed_names=names, exact_save_present=requested,
        note='Not in current diagnostic binary. An approved analysis-only supplement can inspect existing raw TRACE; requested save is not proof of resolved TRACE until export.',
        no_remote_export_performed=True)


def perform_review():
    source, snames, sproof = source_review.collected()
    fixture, fnames, result, measure, proof, members, native = collect_readonly()
    t, ts = fixture[:, 0], source[:, 0]
    node = PREFIX + 'x020.n'
    n = get(fixture, fnames, node)
    k = int(n.argmax())
    expected = sproof['native_peak']
    peak = dict(value_v=float(n[k]), time_s=float(t[k]),
                source_value_v=expected['value_v'], source_time_s=expected['time_s'])
    peak['error_v'] = peak['value_v'] - peak['source_value_v']
    peak['error_s'] = peak['time_s'] - peak['source_time_s']
    if peak['value_v'] != result['peak_snapshot']['voltage_v'] or peak['time_s'] != result['peak_snapshot']['time_s']:
        raise ValueError('Independently measured peak differs from reducer')
    edges = {}
    for signal, cfg in measure['expected_edges'].items():
        original = source_review.edge_time(ts, get(source, snames, signal), get(source, snames, 'vdd!'), cfg['direction'] == 1)
        local = source_review.edge_time(t, get(fixture, fnames, signal), get(fixture, fnames, 'vdd!'), cfg['direction'] == 1)
        if original != cfg['time_s'] or local != result['native_edges_s'][signal]:
            raise ValueError('Independent edge calculation differs: ' + signal)
        errors = [b - a for a, b in zip(original, local)]
        edges[signal] = dict(source_s=original, fixture_s=local, error_s=errors,
            counts_equal=len(original) == len(local),
            within_5ps=len(original) == len(local) and all(abs(x) <= 5e-12 for x in errors))
    source_order = sorted(edges, key=lambda name: edges[name]['source_s'][0])
    fixture_order = sorted(edges, key=lambda name: edges[name]['fixture_s'][0])
    live = PREFIX + 'live'
    quiet = PREFIX + 'quiet'
    path_delays = dict(
        source_peak_after_LIVE_s=peak['source_time_s'] - edges[live]['source_s'][0],
        fixture_peak_after_LIVE_s=peak['time_s'] - edges[live]['fixture_s'][0],
        source_QUIET_after_LIVE_s=edges[quiet]['source_s'][0] - edges[live]['source_s'][0],
        fixture_QUIET_after_LIVE_s=edges[quiet]['fixture_s'][0] - edges[live]['fixture_s'][0])
    live_slew = {}
    for label, table, names in [('source', source, snames), ('fixture', fixture, fnames)]:
        rail = get(table, names, 'vdd!')
        crossings = {str(level): source_review.edge_time(table[:, 0],
                     get(table, names, live) + (.5 - level) * rail, rail, True) for level in [.1, .9]}
        live_slew[label] = dict(crossings_s=crossings,
            rise_10_90_s=(crossings['0.9'][0] - crossings['0.1'][0]
                         if len(crossings['0.9']) == len(crossings['0.1']) == 1 else None))
    initial_errors = {name: result['initial_values'][name] - value
                      for name, value in sproof['initial_state_witnesses']['values_v'].items()}
    if max(abs(v) for v in initial_errors.values()) != result['max_initial_witness_error_v']:
        raise ValueError('Initial witness summary differs')
    kcl_check = {}
    for name in measure['critical_kcl_nodes']:
        terms = measure['kcl_terms'][name]
        independent = np.array([sum(row[fnames.index(term)] for term in terms) for row in fixture])
        saved = get(fixture, fnames, 'kcl:' + name)
        if not np.array_equal(independent, saved):
            raise ValueError('Native KCL sum differs from catalog: ' + name)
        kcl_check[name.lower()] = dict(max_abs_a=float(abs(saved).max()),
                                      reducer_all_history_max_abs_a=result['node_kcl'][name.lower()]['max_abs_a'])
    currents = measure['kcl_terms']['XDUT.XCTRL.XTIM.X020.N']
    i = np.column_stack([get(fixture, fnames, name) for name in currents])
    integrals = {}
    for window, stop in [('prepeak', t[k]), ('full_event', 41.12e-9)]:
        it, q = integrate_native(t, i, 41.04e-9, stop)
        selected = (t >= it[0]) & (t <= it[-1])
        integrals[window] = dict(start_s=float(it[0]), stop_s=float(it[-1]), native_points=len(it),
            sign='Q_into_N = -trapezoid(total native terminal current dt); not channel or parasitic decomposition',
            branch_net_q_c=dict(zip(currents, map(float, q[-1]))),
            sum_net_q_c=float(sum(q[-1])), max_abs_summed_current_a=float(abs(i[selected].sum(axis=1)).max()))
    current_review = {}
    sel = (t >= 41.04e-9) & (t <= 41.12e-9)
    for index, name in enumerate(currents):
        samples = i[sel, index]
        current_review[name] = dict(at_n_peak_a=float(i[k, index]),
            event_min_a=float(samples.min()), event_max_a=float(samples.max()))
    replay = {}
    for label, signal in source_review.REPLAYS.items():
        pwl = np.loadtxt(OWN / 'first_event_v1/pwl' / (label + '.pwl'))
        if not np.array_equal(pwl, source[:, [0, snames.index(signal)]]):
            raise ValueError('PWL native knots changed: ' + label)
        error = get(fixture, fnames, signal) - np.interp(t, pwl[:, 0], pwl[:, 1])
        loc = int(abs(error).argmax())
        replay[signal] = dict(max_abs_error_to_declared_linear_pwl_v=float(abs(error[loc])),
                             time_s=float(t[loc]), native_knots=len(pwl))
    warning_t = 41.0608e-9  # Log rounds the timestamp; do not treat it as exact internal breakpoint.
    sample = get(source, snames, 'xdut.sample_int')
    dt = np.diff(ts)
    slopes = np.diff(sample) / dt
    right = int(np.searchsorted(ts, warning_t))
    knot_review = []
    for j in range(right - 4, right + 5):
        knot_review.append(dict(time_s=float(ts[j]), value_v=float(sample[j]),
            previous_gap_s=float(dt[j - 1]), next_gap_s=float(dt[j]),
            incoming_slope_v_s=float(slopes[j - 1]), outgoing_slope_v_s=float(slopes[j]),
            slope_jump_v_s=float(slopes[j] - slopes[j - 1])))
    warning_lines = [line.strip() for line in members['spectre.out'].decode().splitlines()
                     if re.search(r'WARNING \((?:CMI-275[1-5]|SFE-1131|SPECTRE-16780|VACOMP-2435)\)', line)]
    required_codes = {'CMI-2751', 'CMI-2752', 'CMI-2753', 'CMI-2754', 'CMI-2755', 'SFE-1131', 'SPECTRE-16780', 'VACOMP-2435'}
    if not required_codes <= set(native['warning_codes']):
        raise ValueError('Expected warnings lost')
    caps = measure['proposed_reproduction_contract']
    maxkcl = max(v['reducer_all_history_max_abs_a'] for v in kcl_check.values())
    gates = dict(peak_amplitude_within_1mV=abs(peak['error_v']) <= .001,
        peak_time_within_5ps=abs(peak['error_s']) <= 5e-12,
        selected_edges_count_and_time=all(v['within_5ps'] for v in edges.values()),
        selected_edge_order=source_order == fixture_order,
        original_positive_spike_polarity=peak['value_v'] > .99 and peak['source_value_v'] > .99,
        initial_within_1mV=max(abs(v) for v in initial_errors.values()) <= .001,
        critical_kcl_within_1nA=maxkcl <= 1e-9)
    source_state = json.loads((ROOT / 'output/managed_execution/runs' / source_review.SOURCE_RUN / 'collected/simulation.state.json').read_bytes())
    review = dict(schema_version=1, run=RUN, source_run=source_review.SOURCE_RUN,
        provenance=proof, source_native_recovery=sproof, peak=peak, edges=edges,
        path_delays=path_delays, LIVE_slew=live_slew,
        source_event_order=source_order, fixture_event_order=fixture_order,
        initial_witness_errors_v=initial_errors, max_initial_witness_error_v=max(abs(v) for v in initial_errors.values()),
        independent_critical_kcl=kcl_check, max_critical_kcl_a=maxkcl,
        fixed_approved_screens=gates, faithful_reproduction_screen_pass=all(gates.values()),
        frozen_analyzer_acceptance_pass=result['acceptance_pass'], local_fixture_current_evidence_only=True,
        original_whole_ADC_current_attribution=False, currents=current_review, integrated_currents=integrals,
        ideal_input_replay_checks=replay,
        pwl_warning_check=dict(log_timestamp_s_rounded=warning_t, bounding_native_times_s=[float(ts[right-1]), float(ts[right])],
            all_native_times_strictly_increasing=True, native_knot_voltage_continuity=True,
            declared_model='Piecewise linear through original native knots; derivative changes at knots. Warning does not prove a finite voltage jump.',
            local_knots=knot_review, numerical_cause_proven=False),
        omitted_terminal_loads=topology_missing_loads(), proposed_supplementary_native_export=supplementary_saved_signals(),
        native_warning_codes=native['warning_codes'], warning_lines=warning_lines,
        effective_settings=dict(source=source_state['native']['effective_settings'], fixture=native['effective_settings']),
        proposed_contract_in_frozen_measurement=caps,
        interpolation_policy='Original source and fixture traces plotted independently on unshifted native time axes. Piecewise interpolation used only for event times and checking declared PWL at fixture-native times, never for alignment or fitting.',
        integration_policy='Native-grid trapezoids are numerical charge estimates, not exact continuous-time integrals; endpoints are reported original fixture timestamps.')
    OUT.mkdir(exist_ok=True)
    (OUT / 'review.json').write_text(json.dumps(review, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    (OUT / 'warnings.txt').write_text('\n'.join(warning_lines) + '\n', encoding='utf-8')
    plot(source, snames, fixture, fnames, review, currents, i)
    print(json.dumps(dict(receipt_files=len(proof['receipt_files']), receipt_bytes=proof['receipt_total_bytes'],
        fixture_rows=len(fixture), peak=peak, screens=gates, integrals=integrals,
        replay_errors=replay, max_critical_kcl_a=maxkcl, max_initial_error_v=review['max_initial_witness_error_v']), indent=2))


def plot(source, snames, fixture, fnames, review, currents, i):
    os.environ.setdefault('MPLCONFIGDIR', str(OWN / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'legend.fontsize': 8})
    st, ft = source[:, 0] * 1e9, fixture[:, 0] * 1e9
    srcstyle, fixstyle = dict(color='#255d83', lw=1.65), dict(color='#d16b24', lw=1.3, ls='--')
    fig, axes = plt.subplots(5, 1, figsize=(10.6, 10.5), layout='constrained')
    groups = [('xdut.sample_int', 'SAMPLE_INT'), (PREFIX + 'live', 'LIVE'),
              (PREFIX + 'x020.n', 'X020.N'), (PREFIX + 'quiet', 'QUIET')]
    main_axes = [axes[0], axes[1], axes[2], axes[4]]
    for ax, (name, title) in zip(main_axes, groups):
        ax.plot(st, get(source, snames, name), **srcstyle)
        ax.plot(ft, get(fixture, fnames, name), **fixstyle)
        ax.set(ylabel='V', title=title, ylim=(-.06, 1.16), xlim=(41.04, 41.135)); ax.grid(alpha=.2)
        ax.axvline(review['peak']['source_time_s'] * 1e9, color='#255d83', lw=.6, ls=':')
        ax.axvline(review['peak']['time_s'] * 1e9, color='#d16b24', lw=.6, ls=':')
    axes[2].axhline(.99, color='#777', lw=.8, ls=':')
    zoom = axes[3]
    zoom.plot(st, get(source, snames, PREFIX + 'x020.n'), **srcstyle)
    zoom.plot(ft, get(fixture, fnames, PREFIX + 'x020.n'), **fixstyle)
    zoom.set(xlim=(41.080, 41.096), ylim=(1.055, 1.086), ylabel='V', yticks=[1.06, 1.08],
             title='N peak detail on original time axis: +1.248 mV; -3.775 ps')
    zoom.grid(alpha=.2)
    handles = [Line2D([0], [0], **srcstyle, label='Original loaded ADC'),
               Line2D([0], [0], **fixstyle, label='Isolated control v1')]
    axes[0].legend(handles=handles, loc='center right')
    axes[-1].set(xlabel='Original time (ns); no alignment or fitting')
    fig.suptitle('Control reproduction: amplitude screen fails', fontsize=14)
    fig.supxlabel('FF / 0.99 V / -40 C | IO reference + N4 + core control | ideal external supply/clock\n'
                  'v1: 97 MOS / 18 passive; recorded inputs, cut fanout/feedback; no noise, mismatch or PEX', fontsize=8)
    fig.savefig(OUT / 'native_vs_fixture_timing.png', dpi=165); plt.close(fig)

    colors = ['#b8483b', '#d59622', '#296da4', '#7e57a0', '#23906a']
    labels = ['NAND MP1 D (gate LIVE)', 'NAND MP0 D (gate Q1)', 'NAND MN0 D (gate Q1)',
              'Restoring INV MP G', 'Restoring INV MN G']
    fig, axes = plt.subplots(4, 1, figsize=(10.6, 10.5), layout='constrained')
    for name, label, color in [(PREFIX+'x020.n', 'N', '#255d83'),
                               (PREFIX+'x020.x000.mid', 'MID', '#d16b24'),
                               (PREFIX+'live', 'LIVE', '#4b8c4d')]:
        axes[0].plot(ft, get(fixture, fnames, name), label=label, color=color, lw=1.3)
    axes[0].axhline(.99, color='#777', ls=':', lw=.8)
    axes[0].set(ylabel='Voltage (V)', title='Local fixture only: N, internal MID and LIVE')
    axes[0].legend(ncol=3, loc='center right')
    for j, (color, label) in enumerate(zip(colors, labels)):
        axes[1].plot(ft, i[:, j] * 1e6, color=color, label=label, lw=1.15)
    selected = (ft >= 41.04) & (ft <= 41.12)
    extent = i[selected] * 1e6
    axes[1].set(ylabel='Current (uA)', title='All five currents: positive leaves N; negative injects into N',
                ylim=(float(extent.min()) - 8, float(extent.max()) + 12))
    axes[1].legend(ncol=2, loc='upper left')
    before_peak = (ft >= 41.075) & (ft <= review['peak']['time_s'] * 1e9)
    for j, color in enumerate(colors):
        axes[2].plot(ft[before_peak], i[before_peak, j] * 1e6, color=color, lw=1.2)
    axes[2].set(xlim=(41.075, review['peak']['time_s'] * 1e9), ylabel='Current (uA)',
                title='Pre-peak interval detail; same colors and native time axis')
    nt, q = integrate_native(fixture[:, 0], i, 41.04e-9, 41.12e-9)
    for j, color in enumerate(colors):
        axes[3].plot(nt * 1e9, q[:, j] * 1e15, color=color, lw=1.2)
    axes[3].set(ylabel='Net injected charge (fC)', title='Q into N = -integral(I_terminal dt); five-term sum closes',
                xlabel='Original fixture time (ns)', xlim=(41.04, 41.12))
    axes[3].plot(nt * 1e9, q.sum(axis=1) * 1e15, color='#222', lw=1., ls=':', label='Sum of five branches')
    axes[3].legend(loc='best')
    axes[0].set_xlim(41.04, 41.12); axes[1].set_xlim(41.04, 41.12)
    for ax in axes:
        ax.grid(alpha=.2); ax.axvline(review['peak']['time_s'] * 1e9, color='#777', ls=':', lw=.8)
    fig.suptitle('X020.N: measured total terminal-current paths', fontsize=14)
    fig.supxlabel('FF / 0.99 V / -40 C | isolated control v1, recorded boundaries | comparison clock remains low\n'
                  'No transient noise, mismatch or PEX; total currents only; original ADC current attribution remains unqualified', fontsize=8)
    fig.savefig(OUT / 'x020_current_charge.png', dpi=165); plt.close(fig)

    sample = get(source, snames, 'xdut.sample_int')
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10.6, 7.8), layout='constrained')
    axes[0].plot(st, sample, '.-', markersize=3, **srcstyle, label='Source native knots = PWL knots')
    axes[0].plot(ft, get(fixture, fnames, 'xdut.sample_int'), **fixstyle, label='v1 measured SAMPLE_INT')
    axes[0].set(ylabel='SAMPLE_INT (V)', ylim=(.94, .99))
    axes[0].legend(loc='lower left')
    axes[1].step(st[1:], np.diff(source[:, 0])*1e12, where='pre', color='#255d83', label='Source native segment gap')
    axes[1].step(ft[1:], np.diff(fixture[:, 0])*1e12, where='pre', color='#d16b24', label='v1 solver/output gap', ls='--')
    axes[1].set(ylabel='Native gap (ps)', ylim=(0, .4)); axes[1].legend(loc='upper right')
    axes[2].step(st[1:], np.diff(sample)/np.diff(source[:, 0])*1e-9, where='pre', color='#255d83')
    axes[2].set(ylabel='PWL segment slope (V/ns)', xlabel='Original time (ns)',
                xlim=(41.060, 41.062), ylim=(-23, -9))
    for ax in axes:
        ax.axvline(41.0608, ls=':', color='#b8483b', lw=1.1); ax.grid(alpha=.2)
        ax.ticklabel_format(axis='x', style='plain', useOffset=False)
    axes[0].set_title('SPECTRE-16780 at approximately 41.0608 ns (log-rounded time)')
    fig.suptitle('Replay warning: continuous voltage, changes in segment slope', fontsize=13)
    fig.supxlabel('FF / 0.99 V / -40 C | original ADC versus isolated control v1; no noise, mismatch or PEX\n'
                  'Actual declared PWL; no smoothing, new knots or shifted edges\n'
                  'Temporary LTE relaxation is logged; its contribution to the reproduction error is not measured', fontsize=8)
    fig.savefig(OUT / 'pwl_replay_warning.png', dpi=165); plt.close(fig)


if __name__ == '__main__':
    perform_review()
