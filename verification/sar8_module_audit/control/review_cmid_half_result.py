"""Four frozen cases: native charge/current and CMID-half first-event result."""
import json
import os

import numpy as np
import yaml

import prepare_first_event as base
from review_both_result import read_current_run
from review_first_event_v1 import integrate_native

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN / 'cmid_half_v1/results'
P = 'xdut.xctrl.xtim.'
RUNS = {
    'both': ('sar8audit-ctrl-snload-both-v1', '66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c'),
    'shape': ('sar8audit-ctrl-mp1shape-v1', '8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a'),
    'floor': ('sar8audit-ctrl-mp1floor-v1', '3813f5e217e5d2b360b75fa11d46603b3ca0bbeb8e6e56380f56caa2b0fb529f'),
    'half': ('sar8audit-ctrl-cmidhalf-v1', '4a7e6299c079bec1b798b68ea076c72482005a04c273b39a7824fd039c972069'),
}
REANALYSIS = {
    'both': ('sar8audit-ctrl-both-stress-v1', '21e0940f7afc08f8d054056ca7f3f5eb70e4fdeb054909716780e11e131c82d0'),
    'shape': ('sar8audit-ctrl-mp1shape-stress-v1', 'cba77733017f88e06d61f9d27249c8d1eefa2cea1b40d041fdccfabea02bdbba'),
}
NTRACES = [P+s for s in ['x020.x000.mp1:1', 'x020.x000.mp0:1', 'x020.x000.mn0:1',
                         'x020.x001.mp:2', 'x020.x001.mn:2']]
ITRACES = [P+s for s in ['x020.x000.mp1:1', 'x020.x000.mp0:1', 'x020.x000.mn0:1',
    'x020.x001.mp:2', 'x020.x001.mn:2', 'x020.x000.mn1:1', 'x020.x000.mn0:3',
    'x020.x000.cmid:1']]
COLORS = {'both': '#888888', 'shape': '#276c96', 'floor': '#cc6532', 'half': '#168779'}
LABELS = {'both': 'both: original gates', 'shape': 'shape: gate R',
          'floor': 'floor: + pullup branch', 'half': 'half: CMID 2 -> 1'}


def read_full_history(label, source_result):
    run, expected = REANALYSIS[label]
    folder = ROOT/'output/managed_execution/runs'/run
    receipt = json.loads((folder/'collected/collection_receipt.json').read_bytes())
    if receipt['skipped']:
        raise ValueError('Incomplete reanalysis collection')
    blobs = {}
    for item in receipt['files']:
        name = item['name']
        if name.startswith(('/', '\\')) or '..' in name.replace('\\', '/').split('/'):
            raise ValueError('Unsafe receipt path')
        blob = (folder/'collected'/name).read_bytes()
        if len(blob) != item['bytes'] or base.digest(blob) != item['sha256']:
            raise ValueError('Reanalysis receipt differs')
        blobs[name] = blob
    if sum(map(len, blobs.values())) != receipt['total_bytes']:
        raise ValueError('Reanalysis receipt total differs')
    record = yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
    canonical = json.dumps(record['recipe'], sort_keys=True, separators=(',', ':')).encode()
    if record['recipe_hash'] != expected or base.digest(canonical) != expected:
        raise ValueError('Wrong reanalysis recipe')
    for item in record['recipe']['files']:
        if base.digest((ROOT/item['source']).read_bytes()) != item['sha256']:
            raise ValueError('Registered observer input changed')
    state = json.loads(blobs['analysis.state.json'])
    result = json.loads(blobs['derived/result.json'])
    if (state['status'] != 'complete' or state['exit_code'] != 0
            or not result['analysis_complete'] or not result['source_completed_simulation_verified']
            or not result['source_END_scanned'] or result['source_run_id'] != RUNS[label][0]
            or result['source_recipe_hash'] != RUNS[label][1]
            or result['raw_sha256'] != source_result['raw_sha256']):
        raise ValueError('Wrong completed native source for all-time observations')
    return result, dict(run=run, recipe_sha256=expected, receipt_files=len(blobs),
        receipt_bytes=receipt['total_bytes'], all_receipt_and_input_hashes_match=True,
        same_raw_sha256_as_source=True)


def charges(table, names, first, last):
    times, q = integrate_native(table[:, 0], table[:, [names.index(s) for s in NTRACES]], first, last)
    return dict(requested_first_s=first, requested_last_s=last,
        first_native_s=float(times[0]), last_native_s=float(times[-1]), native_points=len(times),
        into_N_c=dict(zip(NTRACES, map(float, q[-1]))), sum_terminal_charge_c=float(q[-1].sum()))


def main():
    datasets = {label: read_current_run(*identity) for label, identity in RUNS.items()}
    full, reanalysis_proof = {}, {}
    for label, (_, _, r, _, _) in datasets.items():
        if label in REANALYSIS:
            full[label], reanalysis_proof[label] = read_full_history(label, r)
        else:
            full[label] = r
    out = dict(scope='FF/0.99V/-40C isolated conditional-load first-event comparison',
        source_reanalyses=reanalysis_proof, cases={}, full_ADC_qualified=False,
        sign_convention='Native terminal current positive leaving its node. Q_into_N=-integral(I_terminal dt).',
        charge_limit='Total currents include storage/displacement. Five N-terminal charge integrals sum near zero by KCL; '
            'their sum is not extra net node charge or an inferred capacitance. No Cgd/channel separation.',
        common_window_policy='Same requested windows, retaining each actual native endpoint; no waveform resampling or alignment.',
        next_proposal_only='Input-aware NMOS stack ordering at X020; see next_step.md. No new experiment package or remote work.')
    time_probe = datasets['half'][2]['peak_snapshot']['time_s']
    for label, (table, names, r, measurement, proof) in datasets.items():
        get = lambda s: table[:, names.index(P+s)]
        n = get('x020.n')
        peak = int(n.argmax())
        iprobe = int(np.searchsorted(table[:, 0], time_probe, side='right')-1)
        bpm = get('live') if label == 'both' else get('x020.x000.b_pm')
        nterms = set(measurement['kcl_terms']['XDUT.XCTRL.XTIM.X020.N'])
        if nterms != set(NTRACES):
            raise ValueError('N branch incidence changed')
        peak_current = {s: float(table[peak, names.index(s)]) for s in ITRACES}
        ratio = -peak_current[P+'x020.x000.cmid:1']/peak_current[P+'x020.x000.mn1:1']
        edges = dict(MID_half_falling_s=base.edge_time(table[:, 0], get('x020.x000.mid'), .99, False),
            QUIET_rising_s=base.edge_time(table[:, 0], get('quiet'), .99, True),
            QUIET_falling_s=base.edge_time(table[:, 0], get('quiet'), .99, False),
            SAMPLE_falling_s=base.edge_time(table[:, 0], table[:, names.index('xdut.sample_int')], .99, False))
        for threshold in [10, 20, 50]:
            edges['MN0_D_above_'+str(threshold)+'uA_s'] = base.edge_time(table[:, 0],
                get('x020.x000.mn0:1'), 2*threshold*1e-6, True)
        vdd = full[label]['full_history_source_energy']['VDD']
        out['cases'][label] = dict(proof=proof, peak_v=float(n[peak]),
            peak_above_rail_v=float(n[peak]-.99), peak_time_s=float(table[peak, 0]),
            initial_MID_v=r['initial_values'][P+'x020.x000.mid'],
            initial_Q1_v=r['initial_values'][P+'q1'],
            peak_voltages_v=dict(N=float(n[peak]), MID=float(get('x020.x000.mid')[peak]),
                LIVE=float(get('live')[peak]), Q1=float(get('q1')[peak]), B_PM=float(bpm[peak]),
                MN0_VGS=float(get('q1')[peak]-get('x020.x000.mid')[peak])),
            at_peak_current_a=peak_current, at_peak_CMID_release_fraction_of_MN1_D=ratio,
            current_at_same_requested_time=dict(requested_s=float(time_probe), actual_native_s=float(table[iprobe, 0]),
                MN0_D_a=float(get('x020.x000.mn0:1')[iprobe]),
                MP1_into_N_a=float(-get('x020.x000.mp1:1')[iprobe]),
                N_v=float(n[iprobe]), MID_v=float(get('x020.x000.mid')[iprobe])),
            prepeak_charge=charges(table, names, 41.04e-9, float(table[peak, 0])),
            early_common_charge=charges(table, names, 41.04e-9, 41.088e-9),
            later_common_charge=charges(table, names, 41.04e-9, 41.0894e-9),
            end_event_charge=charges(table, names, 41.04e-9, 41.12e-9), edges=edges,
            all_node_KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            critical_KCL_max_a=proof['critical_kcl_max_a'],
            full_history_stress=full[label]['full_history_voltage_stress'],
            source_energy=full[label]['full_history_source_energy'],
            VDD_average_local_power_w=vdd['net_delivered_j']/(vdd['last_time_s']-vdd['first_time_s']),
            initial_VDD_delivered_current_a=-r['initial_values']['vvdd:1'],
            initial_VDD_delivered_power_w=-r['initial_values']['vdd!']*r['initial_values']['vvdd:1'],
            native_warning_codes=proof['native_warning_codes'])
        if label in ['floor', 'half']:
            initial = r['initial_values']
            out['cases'][label]['initial_divider_path'] = dict(
                description='VDD -> RPU0/1/2 -> B_PM -> RSLEW -> LIVE driver -> VSS',
                LIVE_v=initial[P+'live'], B_PM_v=initial[P+'x020.x000.b_pm'],
                current_a=initial[P+'x020.x000.rpu0:1'],
                four_resistor_power_w=(initial['vdd!']-initial[P+'live'])*initial[P+'x020.x000.rpu0:1'])
    intervals = {(v['source_energy']['VDD']['first_time_s'], v['source_energy']['VDD']['last_time_s'])
                 for v in out['cases'].values()}
    if len(intervals) != 1:
        raise ValueError('Energy intervals are not equal')
    floor, half = out['cases']['floor'], out['cases']['half']
    delta = dict(N_overshoot_reduction_v=floor['peak_v']-half['peak_v'],
        N_overshoot_reduction_fraction=(floor['peak_v']-half['peak_v'])/floor['peak_above_rail_v'],
        N_peak_advance_s=floor['peak_time_s']-half['peak_time_s'],
        VDD_energy_change_j=half['source_energy']['VDD']['net_delivered_j']-floor['source_energy']['VDD']['net_delivered_j'],
        initial_static_current_change_a=half['initial_VDD_delivered_current_a']-floor['initial_VDD_delivered_current_a'],
        same_requested_time_MN0_absorption_ratio=half['current_at_same_requested_time']['MN0_D_a']/floor['current_at_same_requested_time']['MN0_D_a'])
    for key in ['MID_half_falling_s', 'MN0_D_above_10uA_s', 'MN0_D_above_20uA_s',
                'MN0_D_above_50uA_s', 'QUIET_rising_s']:
        if len(floor['edges'][key]) != 1 or len(half['edges'][key]) != 1:
            raise ValueError('Expected unique event: '+key)
        delta[key+'_advance'] = floor['edges'][key][0]-half['edges'][key][0]
    out['floor_to_half'] = delta
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    figures(datasets, out)
    print(json.dumps(dict(half_proof=half['proof'], floor_to_half=delta,
        half_peak_current_a=half['at_peak_current_a'], half_prepeak_charge=half['prepeak_charge']), indent=2))


def figures(datasets, report):
    os.environ.setdefault('MPLCONFIGDIR', str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    note = 'FF | 0.99 V | -40 C | isolated first event | original native time\nIdeal external supply/clock; recorded boundaries; no noise, mismatch or PEX'
    plt.rcParams.update({'font.size': 10})
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(10, 9), layout='constrained')
    for label, (table, names, *_rest) in datasets.items():
        get = lambda s: table[:, names.index(P+s)]
        ys = [get('live') if label == 'both' else get('x020.x000.b_pm'),
              get('x020.x000.mid'), (get('x020.n')-.99)*1e3, get('quiet')]
        for ax, y in zip(axes, ys):
            ax.plot(table[:, 0]*1e9, y, label=LABELS[label], color=COLORS[label],
                    ls='--' if label == 'both' else '-', lw=1.5)
    for ax, title, unit in zip(axes, ['MP1 gate', 'NMOS stack MID', 'N overshoot', 'QUIET output'],
                               ['V', 'V', 'mV above 0.99 V', 'V']):
        ax.set(title=title, ylabel=unit); ax.grid(alpha=.2)
    axes[0].legend(ncol=2, loc='upper left', fontsize=8)
    axes[2].axhline(0, color='#555555', ls='--', lw=.8)
    axes[2].set(ylim=(-8, 95))
    axes[-1].set(xlim=(41.05, 41.14), xlabel='Time (ns)')
    fig.suptitle('X020: four frozen circuit versions', fontsize=14)
    fig.supxlabel(note, fontsize=8)
    fig.savefig(OUT/'four_versions.png', dpi=160); plt.close(fig)

    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 7.6), layout='constrained')
    for label in ['floor', 'half']:
        table, names, *_rest = datasets[label]
        get = lambda s: table[:, names.index(P+s)]*1e6
        axes[0].plot(table[:, 0]*1e9, -get('x020.x000.mp1:1'), color=COLORS[label], label=label)
        axes[1].plot(table[:, 0]*1e9, get('x020.x000.mn0:1'), color=COLORS[label])
        axes[2].plot(table[:, 0]*1e9, get('x020.x000.mn1:1'), color=COLORS[label], label=label+' MN1 drain')
        axes[2].plot(table[:, 0]*1e9, -get('x020.x000.cmid:1'), color=COLORS[label], ls='--', label=label+' CMID release')
        for ax in axes:
            ax.axvline(report['cases'][label]['peak_time_s']*1e9, color=COLORS[label], ls=':', lw=.9)
    for ax, title in zip(axes, ['MP1 drain: net injection into N', 'Upper MN0 drain: absorption from N',
                                'MID: lower MN1 drain and explicit capacitor release']):
        ax.set(title=title, ylabel='Current (uA)'); ax.grid(alpha=.2)
    axes[0].legend(ncol=2, fontsize=9)
    axes[2].legend(ncol=2, fontsize=8, loc='lower right')
    axes[-1].set(xlim=(41.080, 41.101), xlabel='Time (ns); dotted lines: respective N peaks')
    fig.suptitle('Half CMID establishes the N sink earlier; MP1 injection remains', fontsize=12)
    fig.supxlabel(note+'\nNative total terminal currents; channel and displacement components not separated', fontsize=8)
    fig.savefig(OUT/'floor_half_currents.png', dpi=160); plt.close(fig)

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10, 6.3), layout='constrained')
    for label, (table, names, *_rest) in datasets.items():
        tt, q = integrate_native(table[:, 0], table[:, [names.index(NTRACES[0]), names.index(NTRACES[2])]],
                                 41.04e-9, 41.091e-9)
        axes[0].plot(tt*1e9, q[:, 0]*1e15, color=COLORS[label], label=LABELS[label], ls='--' if label == 'both' else '-')
        axes[1].plot(tt*1e9, -q[:, 1]*1e15, color=COLORS[label], ls='--' if label == 'both' else '-')
    axes[0].set(title='MP1 drain: cumulative net charge into N', ylabel='Charge (fC)')
    axes[1].set(title='Upper MN0 drain: cumulative charge absorbed from N', ylabel='Charge (fC)',
                xlabel='Time (ns); integration begins at each first native point at or after 41.04 ns', xlim=(41.08, 41.091))
    axes[0].legend(ncol=2, fontsize=8)
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle('Earlier N discharge with continued MP1 terminal injection', fontsize=12)
    fig.supxlabel(note+'\nNative trapezoidal integrals; no common-grid resampling; endpoint times are recorded', fontsize=8)
    fig.savefig(OUT/'charge_flow.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    main()
