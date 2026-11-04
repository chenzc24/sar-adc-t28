"""Read verified native exports; compare MP1 floor branch currents and energy."""
import json
import os

import numpy as np
import yaml

import prepare_first_event as base
from review_both_result import read_current_run
from review_first_event_v1 import integrate_native

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN / 'mp1_floor_v1/results'
P = 'xdut.xctrl.xtim.'
SHAPE = ('sar8audit-ctrl-mp1shape-v1', '8dc67ee9a10e3eeb56b27df222a593b475c600bb74ede6cd5496cfc055287d7a')
FLOOR = ('sar8audit-ctrl-mp1floor-v1', '3813f5e217e5d2b360b75fa11d46603b3ca0bbeb8e6e56380f56caa2b0fb529f')


def read_shape_all_time():
    run = 'sar8audit-ctrl-mp1shape-stress-v1'
    expected = 'cba77733017f88e06d61f9d27249c8d1eefa2cea1b40d041fdccfabea02bdbba'
    folder = ROOT / 'output/managed_execution/runs' / run
    receipt = json.loads((folder / 'collected/collection_receipt.json').read_bytes())
    if receipt['skipped']:
        raise ValueError('Incomplete shape reanalysis')
    data = {}
    for item in receipt['files']:
        if item['name'].startswith(('/', '\\')) or '..' in item['name'].split('/'):
            raise ValueError('Unsafe collected path')
        blob = (folder / 'collected' / item['name']).read_bytes()
        if len(blob) != item['bytes'] or base.digest(blob) != item['sha256']:
            raise ValueError('Shape reanalysis receipt differs')
        data[item['name']] = blob
    if sum(map(len, data.values())) != receipt['total_bytes']:
        raise ValueError('Receipt total differs')
    record = yaml.safe_load((ROOT / 'management/runs' / (run + '.yaml')).read_text())
    canonical = json.dumps(record['recipe'], sort_keys=True, separators=(',', ':')).encode()
    if record['recipe_hash'] != expected or base.digest(canonical) != expected:
        raise ValueError('Wrong shape reanalysis recipe')
    for item in record['recipe']['files']:
        if base.digest((ROOT / item['source']).read_bytes()) != item['sha256']:
            raise ValueError('Registered reanalysis input changed')
    state = json.loads(data['analysis.state.json'])
    result = json.loads(data['derived/result.json'])
    if (state['status'] != 'complete' or state['exit_code'] != 0 or not result['analysis_complete']
            or result['source_run_id'] != SHAPE[0] or result['source_recipe_hash'] != SHAPE[1]
            or not result['source_completed_simulation_verified'] or not result['source_END_scanned']):
        raise ValueError('Shape completed-source/native provenance differs')
    return result, dict(run=run, recipe_sha256=expected, receipt_files=len(data),
                       receipt_bytes=receipt['total_bytes'], all_receipt_and_input_hashes_match=True)


def main():
    datasets = {'shape': read_current_run(*SHAPE), 'floor': read_current_run(*FLOOR)}
    shape_all, shape_proof = read_shape_all_time()
    report = dict(scope='FF/0.99V/-40C first-event conditional-load fixture only',
                  source_reanalysis_proof=shape_proof, cases={},
                  current_policy='Native total terminal current; positive leaves its node. '
                      'Charge into N is negative integral. No channel/Cgd decomposition or waveform fitting.',
                  full_ADC_qualified=False)
    traces = [P+'x020.x000.mp1:1', P+'x020.x000.mp0:1', P+'x020.x000.mn0:1',
              P+'x020.x001.mp:2', P+'x020.x001.mn:2']
    for label, (table, names, result, measurement, proof) in datasets.items():
        get = lambda trace: table[:, names.index(trace)]
        n = get(P+'x020.n')
        peak = int(n.argmax())
        currents = table[:, [names.index(trace) for trace in traces]]
        times, charge = integrate_native(table[:, 0], currents, 41.04e-9, table[peak, 0])
        fixed_t, fixed_q = integrate_native(table[:, 0], currents, 41.04e-9, 41.0894e-9)
        all_time = shape_all if label == 'shape' else result
        energy = all_time['full_history_source_energy']
        report['cases'][label] = dict(proof=proof, peak_v=float(n[peak]), peak_time_s=float(table[peak, 0]),
            peak_voltages_v={s: float(get(P+s)[peak]) for s in ['live', 'q1', 'x020.x000.b_pm', 'x020.x000.mid']},
            at_peak_current_a={s: float(get(P+s)[peak]) for s in ['x020.x000.mp1:1', 'x020.x000.mn0:1',
                'x020.x000.cmid:1', 'x020.x000.mn1:1', 'x020.x000.mn0:3', 'x020.x000.mp1:2']},
            prepeak_charge=dict(first_s=float(times[0]), last_s=float(times[-1]),
                into_N_c=dict(zip(traces, map(float, charge[-1])))),
            common_window_charge=dict(requested_last_s=41.0894e-9, first_native_s=float(fixed_t[0]),
                last_native_s=float(fixed_t[-1]), into_N_c=dict(zip(traces, map(float, fixed_q[-1])))),
            node_KCL_max_a=max(v['max_abs_a'] for v in result['node_kcl'].values()),
            full_history_stress=all_time['full_history_voltage_stress'], source_energy=energy,
            VDD_initial_delivered_current_a=-result['initial_values']['vvdd:1'],
            QUIET_rising_s=base.edge_time(table[:, 0], get(P+'quiet'), .99, True),
            QUIET_falling_s=base.edge_time(table[:, 0], get(P+'quiet'), .99, False),
            native_warning_codes=proof['native_warning_codes'])
    se = report['cases']['shape']['source_energy']['VDD']
    fe = report['cases']['floor']['source_energy']['VDD']
    if (se['first_time_s'], se['last_time_s']) != (fe['first_time_s'], fe['last_time_s']):
        raise ValueError('Inconsistent energy observation intervals')
    if shape_all['raw_sha256'] != datasets['shape'][2]['raw_sha256']:
        raise ValueError('Shape full-history observer bound to different raw')
    report['same_interval_VDD_energy_ratio'] = fe['net_delivered_j'] / se['net_delivered_j']
    report['next_single_variable'] = 'Only X020 private CMID multi2->1; preserve floor and all other circuit/stimulus/observer inputs'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR', str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = {'shape': '#266a91', 'floor': '#c25a31'}
    note = 'FF | 0.99 V | -40 C | isolated first-event fixture, original native time\nIdeal external supply/clock, recorded boundaries; no noise, mismatch or PEX'
    fig, axes = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True, layout='constrained')
    for label, (table, names, *_rest) in datasets.items():
        for ax, signal, scale, offset in zip(axes, ['x020.x000.b_pm', 'x020.x000.mid', 'x020.n'], [1, 1, 1000], [0, 0, .99]):
            y = (table[:, names.index(P+signal)] - offset)*scale
            ax.plot(table[:, 0]*1e9, y, color=colors[label], label=label)
    for ax, title, ylabel in zip(axes, ['MP1 gate B_PM', 'NMOS stack MID', 'N rail overshoot'], ['V', 'V', 'mV above 0.99 V']):
        ax.set(title=title, ylabel=ylabel); ax.grid(alpha=.2)
    axes[0].legend(ncol=2, fontsize=9)
    axes[2].axhline(0, color='#555555', lw=.9, ls='--')
    axes[2].set(ylim=(-8, 40), xlabel='Time (ns)', xlim=(41.05, 41.13))
    fig.suptitle('Positive gate floor fixes MP1 stress; N overshoot increases', fontsize=13)
    fig.supxlabel(note, fontsize=8)
    fig.savefig(OUT/'gate_MID_N.png', dpi=160); plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True, layout='constrained')
    for label, (table, names, *_rest) in datasets.items():
        get = lambda trace: table[:, names.index(P+trace)]*1e6
        axes[0].plot(table[:, 0]*1e9, -get('x020.x000.mp1:1'), color=colors[label], label=label)
        axes[1].plot(table[:, 0]*1e9, get('x020.x000.mn0:1'), color=colors[label])
        axes[2].plot(table[:, 0]*1e9, get('x020.x000.mn1:1'), color=colors[label], label=label+' MN1 drain')
        axes[2].plot(table[:, 0]*1e9, -get('x020.x000.cmid:1'), color=colors[label], ls='--', label=label+' CMID release')
    for ax, title in zip(axes, ['MP1 net injection into N: -I(D)', 'Upper MN0 absorption from N: +I(D)', 'MID: lower NMOS current versus explicit capacitor discharge']):
        ax.set(title=title, ylabel='Current (uA)'); ax.grid(alpha=.2)
        ax.axvline(report['cases']['floor']['peak_time_s']*1e9, color='#666666', lw=.8, ls=':')
    axes[0].legend(ncol=2, fontsize=9); axes[2].legend(ncol=2, fontsize=8)
    axes[-1].set(xlim=(41.080, 41.100), xlabel='Time (ns); dotted line: floor N peak')
    fig.suptitle('Terminal-current evidence: most MN1 current releases MID charge', fontsize=12)
    fig.supxlabel(note+'\nTotal native terminal currents; not separated channel/displacement components', fontsize=8)
    fig.savefig(OUT/'injection_absorption.png', dpi=160); plt.close(fig)
    print(json.dumps({k: dict(peak_v=v['peak_v'], KCL_max_a=v['node_KCL_max_a'],
        VDD_j=v['source_energy']['VDD']['net_delivered_j'], QUIET_rising_s=v['QUIET_rising_s'])
        for k, v in report['cases'].items()}, indent=2))


if __name__ == '__main__':
    main()
