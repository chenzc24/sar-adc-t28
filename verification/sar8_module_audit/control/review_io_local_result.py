"""IO-local result: retained interfaces, real edges and signed source energy."""
import json
import os

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run

OWN = base.OWN
OUT = OWN/'io_local_v1/results'
P = 'xdut.xctrl.xtim.'
RUNS = {
    'stack': ('sar8audit-ctrl-stackorder-v1', 'f7fdea18a1eb32890b5dd3688952ac6e14e91d8d05106bc8dfcd3d85305a82e3'),
    'io': ('sar8audit-ctrl-iolocal-v1', 'aa418b9919dce4576fe5013f09e6d1721c63df76b856e20e205a682d570682a7'),
}
COLORS = {'stack': '#8053a2', 'io': '#c76b2b'}


def pair_comparison(table, names, result, a, z):
    a, z = a.lower(), z.lower()
    constants = {'0': 0., 'vdd!': .99}
    # A measured scalar relative to an ideal constant has exact full-history extrema.
    if a in constants or z in constants:
        if a in constants and z in constants:
            return dict(method='exact_constant_identity', min_v=constants[a]-constants[z],
                        max_v=constants[a]-constants[z], max_abs_v=abs(constants[a]-constants[z]))
        variable = z if a in constants else a
        if variable in result['voltage_and_current_extrema']:
            v = result['voltage_and_current_extrema'][variable]
            if a in constants:
                low, high = constants[a]-v['max'], constants[a]-v['min']
            else:
                low, high = v['min']-constants[z], v['max']-constants[z]
            return dict(method='full_history_single_scalar_plus_ideal_constant', min_v=low, max_v=high,
                max_abs_v=max(abs(low), abs(high)), variable_node=variable,
                scope='Exact constant-reference identity, not subtraction of independent varying extrema')
    if a in names and z in names:
        value = table[:, names.index(a)]-table[:, names.index(z)]
        return dict(method='simultaneous_diagnostic_window', min_v=float(value.min()), max_v=float(value.max()),
            max_abs_v=float(np.abs(value).max()), first_s=float(table[0, 0]), last_s=float(table[-1, 0]))
    return dict(method='not_available', missing_waveforms=[node for node in [a, z] if node not in names])


def main():
    data = {label: read_current_run(*identity) for label, identity in RUNS.items()}
    report = dict(scope='FF/0.99V/-40C first-event conditional fixture; no full-cycle/PVT/ADC qualification',
        cases={}, core_failures=[], full_ADC_qualified=False,
        evidence_policy='Native rows or exact one-variable versus ideal-constant identities only. Missing old waveforms never reconstructed from scalar extrema.',
        power_policy='Signed net delivered source work over0..END, not complete-cycle dissipation or whole-ADC power')
    nodes = ['live', 'q1', 'x020.n', 'quiet', 'xd_quiet_d.ab', 'xd_quiet_d.rc0',
             'xd_quiet_d.rc1', 'x001.n', 'x019.n', 'quiet_d', 'clock_set', 'clock_q']
    for label, (table, names, result, measure, proof) in data.items():
        stat = result['voltage_and_current_extrema']
        if stat['vdd!']['min'] != .99 or stat['vdd!']['max'] != .99:
            raise ValueError('Ideal constant-reference assumption invalid')
        edges = {}
        for node in ['xdut.sample_int', P+'live', P+'quiet', P+'quiet_d', P+'clock_set', P+'clock_q', 'xdut.cmp_clk']:
            if node in names:
                edges[node] = dict(method='native_waveform_halfrail',
                    rising_s=base.edge_time(table[:, 0], table[:, names.index(node)], .99, True),
                    falling_s=base.edge_time(table[:, 0], table[:, names.index(node)], .99, False))
            elif stat[node]['max'] < .495:
                edges[node] = dict(method='full_history_scalar_max_below_halfrail_proves_no_crossing', rising_s=[], falling_s=[])
            else:
                edges[node] = dict(method='unavailable')
        energies = result['full_history_source_energy']
        case = dict(proof=proof, node_extrema={P+n: stat[P+n] for n in nodes}, edges=edges,
            node_end_voltages={node: float(table[-1, names.index(node)]) for node in [P+'quiet', P+'xd_quiet_d.rc0', P+'xd_quiet_d.rc1']},
            source_energy=energies, total_five_source_work_j=sum(v['net_delivered_j'] for v in energies.values()),
            initial_VDD_power_w=-result['initial_values']['vdd!']*result['initial_values']['vvdd:1'],
            all_node_KCL_max_a=max(v['max_abs_a'] for v in result['node_kcl'].values()),
            native_warning_codes=proof['native_warning_codes'])
        close = edges['xdut.sample_int']['falling_s'][0]
        case['QUIET_after_sample_close_s'] = edges[P+'quiet']['rising_s'][0]-close
        case['LIVE_after_sample_close_s'] = edges[P+'live']['rising_s'][0]-close
        report['cases'][label] = case
    io_t, io_n, io_r, io_m, _ = data['io']
    watched = io_m['io_local_experiment']['observed_mos']
    all_pairs = io_r['full_history_voltage_stress']
    io_bad = core_bad = 0
    for instance, item in watched.items():
        old_pairs = {}
        bad = {}
        d, g, s, b = item['nodes']
        endpoints = dict(VGS=(g, s), VGD=(g, d), VDS=(d, s), VGB=(g, b), VDB=(d, b), VSB=(s, b))
        for suffix, key in item['six_pair_labels'].items():
            if all_pairs[key]['over_limit_native_points']:
                bad[suffix] = all_pairs[key]
                if item['changed']:
                    io_bad += 1
                else:
                    core_bad += 1
            a, z = endpoints[suffix]
            old_pairs[suffix] = pair_comparison(*data['stack'][:3], a, z)
        if bad:
            report['core_failures'].append(dict(instance=instance, model=item['model'], failures=bad,
                old_stack_comparable_pairs=old_pairs, changed_in_io_local=item['changed']))
    report['screen_counts'] = dict(changed_IO_instances=15, changed_IO_pairs=90, changed_IO_failed_pairs=io_bad,
        retained_core_instances=17, retained_core_pairs=102, retained_core_failed_pairs=core_bad,
        retained_failed_instances=sum(not x['changed_in_io_local'] for x in report['core_failures']))
    worst = max((all_pairs[key]['max_abs_v'], name, suffix, key)
                for name, item in watched.items() if item['changed']
                for suffix, key in item['six_pair_labels'].items())
    report['worst_IO_absolute_screen_pair'] = dict(value_v=worst[0], instance=worst[1],
        terminal_pair=worst[2], provisional_limit_v=all_pairs[worst[3]]['limit_abs_v'])
    index = int(io_t[:, io_n.index(P+'live')].argmin())
    report['io_LIVE_minimum_junction_observation'] = dict(time_s=float(io_t[index, 0]),
        NMOS_VDB_v=float(io_t[index, io_n.index(P+'live')]),
        NMOS_body_total_current_a=float(io_t[index, io_n.index(P+'x001.x001.mn:4')]),
        PMOS_body_total_current_a=float(io_t[index, io_n.index(P+'x001.x001.mp:4')]),
        qualification='Signed NMOS junction forward polarity is observed; absolute1.98V screen does not qualify forward junctions. Total body port currents are not isolated DC diode current.')
    snapshots = {}
    for node, minimum in [(P+'xd_quiet_d.ab', False), (P+'xd_quiet_d.rc0', True),
                           (P+'xd_quiet_d.rc1', False), (P+'x001.n', False), (P+'quiet', False)]:
        wave = io_t[:, io_n.index(node)]
        index = int(wave.argmin() if minimum else wave.argmax())
        terms = io_m['kcl_terms'][next(key for key in io_m['kcl_terms'] if key.lower() == node)]
        if not all(term in io_n for term in terms):
            raise ValueError('Missing IO causal KCL terminal')
        snapshots[node] = dict(time_s=float(io_t[index, 0]), voltage_v=float(wave[index]),
            terminal_current_a={term: float(io_t[index, io_n.index(term)]) for term in terms},
            KCL_sum_a=sum(float(io_t[index, io_n.index(term)]) for term in terms))
    report['io_causal_snapshots'] = snapshots
    old, new = report['cases']['stack'], report['cases']['io']
    for key in old['source_energy']:
        a, z = old['source_energy'][key], new['source_energy'][key]
        if (a['first_time_s'], a['last_time_s']) != (z['first_time_s'], z['last_time_s']):
            raise ValueError('Energy observation intervals differ')
    report['change'] = dict(
        VDD_net_energy_reduction_fraction=1-new['source_energy']['VDD']['net_delivered_j']/old['source_energy']['VDD']['net_delivered_j'],
        QUIET_delay_increase_s=new['QUIET_after_sample_close_s']-old['QUIET_after_sample_close_s'],
        N_peak_above_rail_old_v=old['node_extrema'][P+'x020.n']['max']-.99,
        N_peak_above_rail_new_v=new['node_extrema'][P+'x020.n']['max']-.99)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    figures(data, report)
    print(json.dumps(dict(screen_counts=report['screen_counts'], change=report['change'],
        failed_core_instances=[x['instance'] for x in report['core_failures']]), indent=2))


def figures(data, report):
    os.environ.setdefault('MPLCONFIGDIR', str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    note = 'FF | 0.99 V | -40 C | conditioned first event, original native time\nIdeal sources; recorded FF boundaries; no noise, mismatch or PEX'
    fig, axes = plt.subplots(3, 2, figsize=(11, 10), layout='constrained')
    for label, (table, names, *_rest) in data.items():
        for ax, signal in [(axes[0, 0], 'live'), (axes[0, 1], 'quiet')]:
            mask = (table[:, 0] >= 41.05e-9) & (table[:, 0] <= 41.59e-9)
            ax.plot(table[mask, 0]*1e9, table[mask, names.index(P+signal)], color=COLORS[label], label=label)
        mask = table[:, 0] <= 41.06e-9
        axes[2, 0].plot(table[mask, 0]*1e9, -table[mask, names.index('vvdd:1')]*.99*1e6,
                        color=COLORS[label], label=label)
        mask = (table[:, 0] >= 41.05e-9) & (table[:, 0] <= 41.25e-9)
        axes[1, 0].plot(table[mask, 0]*1e9, table[mask, names.index(P+'x020.n')], color=COLORS[label])
        axes[1, 1].plot(table[mask, 0]*1e9, (table[mask, names.index(P+'q1')]-.99)*1e3, color=COLORS[label])
    for ax in axes[0]:
        ax.axhline(.495, ls='--', lw=.8, color='#777777'); ax.set(ylabel='V')
    axes[0, 0].set(title='LIVE'); axes[0, 1].set(title='QUIET: halfrail crossings')
    axes[1, 0].set(title='X020 N: overshoot remains', ylabel='V')
    axes[1, 0].axhline(.99, ls='--', lw=.8, color='#777777')
    axes[1, 1].set(title='Q1 rail excursion', ylabel='mV above0.99V')
    axes[1, 1].axhline(0, ls='--', lw=.8, color='#777777')
    axes[2, 0].set(title='VDD delivered power before sampling closes', ylabel='uW', xlabel='Time (ns)')
    axes[2, 1].bar(['stack', 'io'], [report['cases'][label]['source_energy']['VDD']['net_delivered_j']*1e12
                                  for label in ['stack', 'io']], color=[COLORS['stack'], COLORS['io']])
    axes[2, 1].set(title='VDD net energy, same0..41.5908ns interval', ylabel='pJ')
    axes[0, 0].legend(ncol=2, fontsize=9)
    for ax in [axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1], axes[2, 0]]:
        ax.grid(alpha=.2); ax.ticklabel_format(axis='x', useOffset=False); ax.xaxis.set_major_locator(MaxNLocator(4))
    fig.suptitle('Removing the divider reduces idle work; local IO adds delay', fontsize=13)
    fig.supxlabel(note, fontsize=8)
    fig.savefig(OUT/'delay_energy.png', dpi=155); plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout='constrained')
    specs = [(axes[0, 0], 'xd_quiet_d.ab', (41.07, 41.24), (-2, 45), 'AB: MN_CLEAR VGS/VGB'),
             (axes[0, 1], 'xd_quiet_d.rc1', (41.07, 41.59), (-1, 9), 'RC1: X005 NMOS gate'),
             (axes[1, 0], 'xd_quiet_d.rc0', (41.07, 41.18), (-.2, .1), 'RC0: negative-rail detail'),
             (axes[1, 1], 'x001.n', (41.073, 41.08), (-1, 18), 'X001.N: retained NAND drain')]
    for ax, signal, window, ylim, title in specs:
        node = P+signal
        for label, (table, names, result, *_rest) in data.items():
            offset = 0 if signal.endswith('rc0') else .99
            if node in names:
                mask = (table[:, 0]*1e9 >= window[0]) & (table[:, 0]*1e9 <= window[1])
                ax.plot(table[mask, 0]*1e9, (table[mask, names.index(node)]-offset)*1e3,
                        color=COLORS[label], label=label)
            else:
                stat = result['voltage_and_current_extrema'][node]
                ax.plot(stat['max_time_s']*1e9, (stat['max']-offset)*1e3, 'o', color=COLORS[label],
                        label=label+' peak only')
        ax.set(title=title, ylabel='mV' if signal.endswith('rc0') else 'mV above0.99V',
               xlim=window, ylim=ylim, xlabel='Time (ns)')
        ax.axhline(0, color='#777777', lw=.8, ls='--'); ax.grid(alpha=.2)
        ax.ticklabel_format(axis='x', useOffset=False); ax.xaxis.set_major_locator(MaxNLocator(4))
    axes[0, 0].legend(fontsize=8); axes[0, 1].legend(fontsize=8)
    fig.suptitle('Retained core interfaces: old faults and changed amplitudes', fontsize=13)
    fig.supxlabel(note+'\nOld AB/X001.N scalar peaks are points; missing old waveforms are not reconstructed.', fontsize=8)
    fig.savefig(OUT/'retained_interfaces.png', dpi=160); plt.close(fig)

    table, names, *_rest = data['io']
    specs = [
        ('xd_quiet_d.ab', [('xd_quiet_d.x006.mp:1', 'X006 PMOS drain'), ('xd_quiet_d.x006.mn:1', 'X006 NMOS drain'),
                          ('xd_quiet_d.mn_clear:2', 'MN_CLEAR gate')], 2e-12),
        ('xd_quiet_d.rc0', [('xd_quiet_d.r0:2', 'R0'), ('xd_quiet_d.mn_clear:1', 'MN_CLEAR drain'),
                           ('xd_quiet_d.c0:1', 'C0')], 12e-12),
        ('xd_quiet_d.rc1', [('xd_quiet_d.mp_clear:1', 'MP_CLEAR drain'), ('xd_quiet_d.r1:2', 'R1'),
                           ('xd_quiet_d.c1:1', 'C1')], 40e-12)]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), layout='constrained')
    for ax, (signal, terms, span) in zip(axes, specs):
        at = report['io_causal_snapshots'][P+signal]['time_s']
        mask = (table[:, 0] >= at-span) & (table[:, 0] <= at+span*.25)
        for trace, label in terms:
            ax.plot(table[mask, 0]*1e9, -table[mask, names.index(P+trace)]*1e6, label=label)
        ax.axvline(at*1e9, color='#777777', lw=.8, ls=':')
        ax.set(title=signal.upper()+': net terminal current into node', ylabel='uA', xlabel='Time (ns)')
        ax.grid(alpha=.2); ax.legend(fontsize=8, ncol=3)
        ax.ticklabel_format(axis='x', useOffset=False); ax.xaxis.set_major_locator(MaxNLocator(4))
    fig.suptitle('IO-local only: actual charge-transfer branches at interface extrema', fontsize=12)
    fig.supxlabel(note+'\nNative total terminal currents; all KCL terms retained in comparison.json; no Cgd/channel split.', fontsize=8)
    fig.savefig(OUT/'interface_currents.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    main()
