"""Compare actual old/new gate assignments and native current exchange."""
import json
import os

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run
from review_first_event_v1 import integrate_native

OWN, ROOT = base.OWN, base.ROOT
OUT = OWN/'stack_order_v1/results'
P = 'xdut.xctrl.xtim.'
RUNS = {
    'half': ('sar8audit-ctrl-cmidhalf-v1', '4a7e6299c079bec1b798b68ea076c72482005a04c273b39a7824fd039c972069'),
    'stack': ('sar8audit-ctrl-stackorder-v1', 'f7fdea18a1eb32890b5dd3688952ac6e14e91d8d05106bc8dfcd3d85305a82e3'),
}
PACKAGES = {'half': 'cmid_half_v1', 'stack': 'stack_order_v1'}
COLORS = {'half': '#168779', 'stack': '#8053a2'}


def extrema(t, v):
    lo, hi, absolute = int(v.argmin()), int(v.argmax()), int(np.abs(v).argmax())
    over = np.flatnonzero(np.abs(v) > .99)
    return dict(min_v=float(v[lo]), max_v=float(v[hi]), min_time_s=float(t[lo]), max_time_s=float(t[hi]),
        max_abs_v=float(abs(v[absolute])), max_abs_time_s=float(t[absolute]),
        native_points=len(t), over_limit_native_points=len(over),
        first_over_limit_s=float(t[over[0]]) if len(over) else None,
        last_over_limit_s=float(t[over[-1]]) if len(over) else None, limit_abs_v=.99)


def integrate_terms(table, names, terms, stop):
    tt, q = integrate_native(table[:, 0], table[:, [names.index(s) for s in terms]], 41.04e-9, stop)
    return dict(requested_start_s=41.04e-9, requested_stop_s=float(stop),
        first_native_s=float(tt[0]), last_native_s=float(tt[-1]),
        into_node_c=dict(zip(terms, map(float, q[-1]))), sum_terminal_charge_c=float(q[-1].sum()))


def main():
    data = {label: read_current_run(*identity) for label, identity in RUNS.items()}
    common_start = max(item[0][0, 0] for item in data.values())
    common_stop = min(item[0][-1, 0] for item in data.values())
    report = dict(scope='FF/0.99V/-40C isolated first-event fixture only', cases={},
        comparable_stress_scope=dict(first_s=float(common_start), last_s=float(common_stop),
            policy='Actual terminal bindings in each frozen netlist, simultaneous native voltages in the overlapping diagnostic window. Half added pairs are NOT full-history observations.'),
        current_policy='Total terminal current positive leaves node; into-node charge is negative native-grid integral. No channel/Cgd separation. KCL sums do not infer extra node charge.',
        qualification_pass=False, next_proposal='Local rated CMOS drive/gate/receiver boundary and remove DC divider; see next_step.md')
    curves = {}
    nterms = [P+s for s in ['x020.x000.mp1:1', 'x020.x000.mp0:1', 'x020.x000.mn0:1',
                           'x020.x001.mp:2', 'x020.x001.mn:2']]
    for label, (table, names, r, m, proof) in data.items():
        mask = (table[:, 0] >= common_start) & (table[:, 0] <= common_stop)
        native = table[mask]
        get = lambda node: np.zeros(len(native)) if node == '0' else native[:, names.index(node.lower())]
        t = native[:, 0]
        leaves = base.flatten((OWN/PACKAGES[label]/'dut.scs').read_text(),
                              'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
        pairs = {}
        for device in ['MN0', 'MN1']:
            d, g, s, b = leaves['XDUT.XCTRL.XTIM.X020.X000.'+device]['nodes']
            for suffix, (a, z) in dict(VGS=(g, s), VGD=(g, d), VDS=(d, s),
                                       VGB=(g, b), VDB=(d, b), VSB=(s, b)).items():
                value = get(a)-get(z)
                pairs[device+'_'+suffix] = dict(extrema(t, value), positive_node=a, negative_node=z)
                curves[label, device+'_'+suffix] = (t, value)
        if label == 'stack':
            for key, item in pairs.items():
                all_time = r['full_history_voltage_stress'][key]
                for field in ['min_v', 'max_v', 'max_abs_v']:
                    if abs(item[field]-all_time[field]) > 1e-12:
                        raise ValueError('Stack full-history extreme outside comparable window: '+key+' '+field)
        n, q1 = get(P+'x020.n'), get(P+'q1')
        npk, qpk = int(n.argmax()), int(q1.argmax())
        pk_time, q_time = float(t[npk]), float(t[qpk])
        current = lambda name, i: float(native[i, names.index(name)])
        case = dict(proof=proof, initial_MID_v=r['initial_values'][P+'x020.x000.mid'],
            N_peak_v=float(n[npk]), N_peak_time_s=pk_time,
            Q1_peak_v=float(q1[qpk]), Q1_peak_time_s=q_time,
            LIVE_min=extrema(t, get(P+'live')), MID_window=extrema(t, get(P+'x020.x000.mid')),
            actual_MN0_nodes=leaves['XDUT.XCTRL.XTIM.X020.X000.MN0']['nodes'],
            actual_MN1_nodes=leaves['XDUT.XCTRL.XTIM.X020.X000.MN1']['nodes'],
            simultaneous_voltage_stress_common_window=pairs,
            full_history_configured_stress=r['full_history_voltage_stress'],
            N_peak_branch_current_a={s: current(s, npk) for s in nterms},
            N_charge_to_own_peak=integrate_terms(table, names, nterms, pk_time),
            N_charge_common_early=integrate_terms(table, names, nterms, 41.08465e-9),
            N_charge_common_late=integrate_terms(table, names, nterms, 41.0881e-9),
            Q1_branch_currents_scope='Only columns genuinely present in compact export; missing half currents never filled with zero',
            Q1_branch_terms=m['kcl_terms']['XDUT.XCTRL.XTIM.Q1'],
            source_energy=r['full_history_source_energy'],
            initial_VDD_delivered_current_a=-r['initial_values']['vvdd:1'],
            initial_VDD_delivered_power_w=-r['initial_values']['vdd!']*r['initial_values']['vvdd:1'],
            QUIET_rising_s=base.edge_time(table[:, 0], table[:, names.index(P+'quiet')], .99, True),
            QUIET_falling_s=base.edge_time(table[:, 0], table[:, names.index(P+'quiet')], .99, False),
            all_node_KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            native_warning_codes=proof['native_warning_codes'])
        qterms = case['Q1_branch_terms']
        missing = [s for s in qterms if s not in names]
        case['Q1_missing_compact_current_columns'] = missing
        if not missing:
            case['Q1_charge_to_own_peak'] = integrate_terms(table, names, qterms, q_time)
            case['Q1_peak_branch_current_a'] = {s: current(s, qpk) for s in qterms}
        if label == 'stack':
            snapshots = {}
            for key, at in [('LIVE_minimum', float(t[get(P+'live').argmin()])),
                             ('N_peak', pk_time), ('Q1_peak', q_time)]:
                i = int(np.flatnonzero(t == at)[0])
                snapshots[key] = dict(time_s=at,
                    voltage_v={s: float(get(P+s)[i]) for s in ['live', 'q1', 'x020.n', 'x020.x000.mid', 'x020.x000.b_pm']},
                    N_branch_current_a={s: current(s, i) for s in nterms},
                    Q1_branch_current_a={s: current(s, i) for s in qterms})
            case['causal_snapshots'] = snapshots
        report['cases'][label] = case
    half, stack = report['cases']['half'], report['cases']['stack']
    for label in RUNS:
        vdd = report['cases'][label]['source_energy']['VDD']
        if vdd['first_time_s'] != 0 or vdd['last_time_s'] != common_stop:
            raise ValueError('Different full-history energy observation interval')
    report['change'] = dict(N_overshoot_reduction_v=half['N_peak_v']-stack['N_peak_v'],
        N_overshoot_reduction_fraction=(half['N_peak_v']-stack['N_peak_v'])/(half['N_peak_v']-.99),
        N_peak_advance_s=half['N_peak_time_s']-stack['N_peak_time_s'],
        Q1_positive_peak_increase_v=stack['Q1_peak_v']-half['Q1_peak_v'],
        QUIET_advance_s=half['QUIET_rising_s'][0]-stack['QUIET_rising_s'][0])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    figures(data, curves, report)
    print(json.dumps(dict(stack_proof=stack['proof'], change=report['change'],
        stack_N_charge=stack['N_charge_to_own_peak'], stack_Q1_charge=stack.get('Q1_charge_to_own_peak'),
        half_missing_Q1_currents=half['Q1_missing_compact_current_columns']), indent=2))


def figures(data, curves, report):
    os.environ.setdefault('MPLCONFIGDIR', str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    note = 'FF | 0.99 V | -40 C | isolated first event | original native time\nIdeal external supply/clock; recorded boundaries; no noise, mismatch or PEX'
    plt.rcParams.update({'font.size': 10})
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 7.4), layout='constrained')
    for label, (table, names, *_rest) in data.items():
        for ax, signal, scale, offset in zip(axes, ['x020.x000.mid', 'x020.n', 'q1'], [1, 1000, 1000], [0, .99, .99]):
            ax.plot(table[:, 0]*1e9, (table[:, names.index(P+signal)]-offset)*scale,
                    color=COLORS[label], label=label)
    for ax, title, unit in zip(axes, ['MID pre-discharge', 'N positive-rail detail', 'Q1 positive-rail detail'],
                               ['V', 'mV above 0.99 V', 'mV above 0.99 V']):
        ax.set(title=title, ylabel=unit); ax.grid(alpha=.2)
    axes[0].legend(ncol=2, fontsize=9)
    for ax in axes[1:]: ax.axhline(0, color='#555555', lw=.8, ls='--')
    axes[1].set(ylim=(-2, 25)); axes[2].set(ylim=(-2, 2))
    axes[-1].set(xlim=(41.078, 41.103), xlabel='Time (ns)')
    fig.suptitle('Pre-discharging MID reduces N overshoot; Q1 ripple remains', fontsize=13)
    fig.supxlabel(note+'\nRail-detail panels zoom the positive excursion; larger negative movement lies below the displayed range', fontsize=8)
    fig.savefig(OUT/'response.png', dpi=160); plt.close(fig)

    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 7.5), layout='constrained')
    for label, (table, names, *_rest) in data.items():
        visible = (table[:, 0] >= 41.081e-9) & (table[:, 0] <= 41.08505e-9)
        for trace, style, branch in [('x020.x000.mp1:1', '-', 'MP1 drain'), ('x020.x000.mn0:1', '--', 'MN0 drain')]:
            current = table[:, names.index(P+trace)]
            axes[0].plot(table[visible, 0]*1e9, -current[visible]*1e6, color=COLORS[label], ls=style, label=label+' '+branch)
            tt, charge = integrate_native(table[:, 0], current[:, None], 41.04e-9, 41.08505e-9)
            qvisible = tt >= 41.081e-9
            axes[1].plot(tt[qvisible]*1e9, charge[qvisible, 0]*1e15, color=COLORS[label], ls=style)
        axes[2].plot(table[visible, 0]*1e9, (table[visible, names.index(P+'x020.n')]-.99)*1e3, color=COLORS[label])
    for ax in axes:
        ax.axhline(0, color='#555555', ls=':', lw=.8); ax.grid(alpha=.2)
    axes[0].set(title='MP1 and upper MN0: net current into N', ylabel='Current (uA)')
    axes[1].set(title='Native cumulative terminal charge into N', ylabel='Charge (fC)')
    axes[2].set(title='N in the same early interval', ylabel='mV above 0.99 V', xlabel='Time (ns)', xlim=(41.081, 41.08505))
    axes[0].legend(ncol=2, fontsize=8)
    for ax in axes: ax.ticklabel_format(axis='x', style='plain', useOffset=False)
    fig.suptitle('Stack ordering shifts early net injection from MP1 to MN0', fontsize=13)
    fig.supxlabel(note+'\nStack-peak interval; the later half peak is shown in response.png. Total currents, no Cgd decomposition.', fontsize=8)
    fig.savefig(OUT/'N_exchange.png', dpi=160); plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout='constrained')
    for label, (table, names, *_rest) in data.items():
        top_visible = (table[:, 0] >= 41.080e-9) & (table[:, 0] <= 41.0832e-9)
        axes[0, 0].plot(table[top_visible, 0]*1e9, table[top_visible, names.index(P+'live')]*1e3,
                        color=COLORS[label], label=label+' LIVE')
        t, value = curves[label, 'MN0_VDS']
        visible = (t >= 41.079e-9) & (t <= 41.089e-9)
        axes[0, 1].plot(t[visible]*1e9, value[visible], color=COLORS[label], label=label)
        axes[1, 0].plot(table[:, 0]*1e9, (table[:, names.index(P+'q1')]-.99)*1e3, color=COLORS[label])
    t, value = curves['stack', 'MN0_VGD']
    visible = (t >= 41.080e-9) & (t <= 41.0832e-9)
    axes[0, 0].plot(t[visible]*1e9, (-value[visible]-.99)*1e3, color='#8d5331', ls='--', label='stack VDG - 0.99 V')
    axes[0, 0].axhline(0, color='#ad4747', ls=':', lw=.9)
    axes[0, 1].axhline(.99, color='#ad4747', ls='--', lw=.9)
    axes[1, 0].axhline(0, color='#ad4747', ls='--', lw=.9)
    axes[0, 0].set(title='LIVE dip and stack MN0 VDG excess', ylabel='mV',
                    xlim=(41.080, 41.0832), ylim=(-15, 15))
    axes[0, 1].set(title='Upper MN0 VDS: MID near ground', ylabel='V', xlim=(41.079, 41.089))
    axes[1, 0].set(title='Q1 was already above the rail in half', ylabel='mV above 0.99 V',
                    ylim=(-2, 2), xlim=(41.079, 41.089), xlabel='Time (ns)')
    table, names, *_rest = data['stack']
    qterms = report['cases']['stack']['Q1_branch_terms']
    branch_names = ['MP0 gate', 'lower MN1 gate', 'Q1 driver PMOS drain', 'Q1 driver NMOS drain']
    visible = (table[:, 0] >= 41.083e-9) & (table[:, 0] <= 41.087e-9)
    for trace, label in zip(qterms, branch_names):
        axes[1, 1].plot(table[visible, 0]*1e9, -table[visible, names.index(trace)]*1e6, label=label)
    axes[1, 1].set(title='Stack only: terminal currents into Q1', ylabel='Current (uA)',
                    xlim=(41.083, 41.087), xlabel='Time (ns)')
    axes[0, 0].legend(ncol=1, fontsize=7, loc='upper right')
    axes[0, 1].legend(ncol=2, fontsize=8)
    axes[1, 1].legend(ncol=1, fontsize=7, loc='lower left')
    for ax in axes.flat:
        ax.grid(alpha=.2); ax.ticklabel_format(axis='x', style='plain', useOffset=False)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    fig.suptitle('LIVE undershoot and Q1 coupling: simultaneous terminal differences', fontsize=12)
    fig.supxlabel(note+'\nStress comparison uses matching diagnostic windows; no new half full-history claim. Q1 currents shown only where saved.', fontsize=8)
    fig.savefig(OUT/'terminal_paths.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    main()
