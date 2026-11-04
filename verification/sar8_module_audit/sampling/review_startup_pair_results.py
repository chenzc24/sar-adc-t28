"""Compare only the two collected startup controls, sequentially and locally."""
import json
from pathlib import Path

import numpy as np

import builder as b
from review_startup_dc_results import peak_working_set

HERE = Path(__file__).resolve().parent
OUT = HERE / 'power_on_results/comparison'


def read_curves(case):
    root = HERE / 'power_on_results' / case
    m = json.loads((root / 'measurements.json').read_text())
    e = json.loads((root / 'evidence.json').read_text())
    meta = json.loads((root / 'decoded/wave.meta.json').read_text())
    columns = (root / 'decoded/wave.columns').read_text().splitlines()
    mapping = json.loads((HERE / 'power_on/common/mapping.json').read_text())
    matrix = np.memmap(root / 'decoded/wave.bin', mode='r', dtype='<f8',
                       shape=(meta['points'], len(columns)))
    try:
        indices = {name: i for i, name in enumerate(columns)}
        t = matrix[:, indices['time']]
        x = np.linspace(0, 260, 13001)
        w = dict(time_ns=x)
        for key in ['vdd', 'sample', 'seq_sample', 'top_p', 'top_n',
                    'boot_p_btop', 'boot_p_bbot', 'boot_p_g', 'vin_p']:
            w[key] = np.interp(x * 1e-9, t, matrix[:, indices[mapping['signal_map'][key]]])
        w['m2_p_ua'] = -np.interp(x * 1e-9, t,
            matrix[:, indices[mapping['branch_signal_map']['p_m2_drain']]]) * 1e6
        all_events = {}
        for line in (root / 'decoded/wave.events.tsv').read_text().splitlines():
            name, up, time = line.split()
            if float(time) < 101e-9:
                all_events.setdefault(name, []).append(dict(time_ns=float(time)*1e9, up=int(up)))
        w['pre_formal_all_clock_events'] = all_events
        return m, e, w
    finally:
        matrix._mmap.close()


def plots(cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    styles = [('dc_core', '#b85b45', 'DC core'), ('ramp_core', '#2676a2', '0-to-0.81 V ramp')]
    fig, axes = plt.subplots(5, 2, figsize=(12, 11.5), layout='constrained')
    for name, color, label in styles:
        m, _, w = cases[name]
        x = w['time_ns']
        ys = [w['vdd'], w['seq_sample'], w['boot_p_btop']-w['boot_p_bbot'], w['m2_p_ua']]
        error = np.full(len(x), np.nan)
        for f, target in zip(m['frames'], [-.81, 0]):
            mask = (x >= f['actual_open_ns']) & (x <= f['held_time_ns']+.2)
            error[mask] = (w['top_p'][mask]-w['top_n'][mask]-target)*1000
        ys.append(error)
        for col in range(2):
            for row, y in enumerate(ys):
                axes[row,col].plot(x,y,color=color,lw=1.45,label=label)
    for col,(lo,hi,title,frame) in enumerate([(0,145,'First formal frame: -0.81 V input',0),
                                             (140,245,'Following frame: 0 V input',1)]):
        ref = cases['dc_core'][0]['frames'][frame]
        axes[0,col].set_title(title,fontsize=10)
        for ax in axes[:,col]:
            ax.set_xlim(lo,hi)
            ax.axvline(ref['actual_open_ns'],color='#777',ls=':',lw=.8)
            ax.axvline(ref['actual_close_ns'],color='#777',ls=':',lw=.8)
            ax.grid(alpha=.18)
        axes[4,col].set_yscale('symlog',linthresh=1)
        axes[4,col].axhspan(-1.7578125,1.7578125,color='#88b996',alpha=.18)
        axes[4,col].axhline(0,color='#555',ls='--',lw=.8)
        axes[4,col].set_xlabel('Absolute time (ns)')
    axes[0,0].legend(fontsize=8,loc='lower right')
    for row,label in enumerate(['VDD (V)','SEQ_SAMPLE (V)','P Cboot (V)',
                                 'P M2 into BTOP (uA)','Sample error (mV)']):
        axes[row,0].set_ylabel(label)
    fig.suptitle('SS / 0.81 V / -40 C | same external bias ramp; only core supply prehistory differs\n'
        'Real Bootstrap + full CDAC; fixed Q128, N4 reset; no noise / mismatch / PEX\n'
        'Analog: 20 ps compact estimates; dotted: native DC SEQ edges; green: +/-0.25 LSB screen',fontsize=10.5)
    fig.savefig(OUT/'startup_pair_waveforms.png',dpi=165)
    plt.close(fig)
    peak_working_set()

    fig, axes = plt.subplots(1,2,figsize=(11,3.8),layout='constrained')
    for col,(lo,hi,target) in enumerate([(140.5,142.2,-.81),(240.5,242.2,0)]):
        for name,color,label in styles:
            m,_,w = cases[name]
            f=m['frames'][col];x=w['time_ns'];mask=(x>=lo)&(x<=hi)
            axes[col].plot(x[mask],(w['top_p'][mask]-w['top_n'][mask]-target)*1000,
                           color=color,lw=1.5,label=label)
            axes[col].scatter([f['preclose_time_ns']],[f['preclose_error_mv']],color=color,marker='o',s=28,zorder=5)
            axes[col].scatter([f['held_time_ns']],[f['held_error_at_nominal_edge_mv']],color=color,marker='s',s=28,zorder=5)
        axes[col].axhline(0,color='#555',ls='--',lw=.8,label='Expected zero error' if col==0 else None)
        axes[col].set_xlim(lo,hi);axes[col].grid(alpha=.2)
        axes[col].set_title('First frame: -0.81 V' if col==0 else'Following frame: 0 V',fontsize=10)
        axes[col].set_xlabel('Time (ns); circle: preclose, square: held')
    axes[0].set_ylabel('Differential error (mV)');axes[0].legend(fontsize=8)
    fig.suptitle('Same-frame DC/ramp comparison | close - 0.2 ns versus fixed 141.8 / 241.8 ns\n'
        '20 ps compact estimates; net motion includes continued settling, injection and coupling',fontsize=10)
    fig.savefig(OUT/'startup_pair_endpoints.png',dpi=165);plt.close(fig)
    peak_working_set()

    m,_,w=cases['ramp_core'];x=w['time_ns'];mask=(x>=34.8)&(x<=37.3)
    fig,axes=plt.subplots(2,1,figsize=(9,5.1),sharex=True,layout='constrained')
    axes[0].plot(x[mask],w['vdd'][mask],color='#2676a2',label='VDD ramp')
    axes[0].plot(x[mask],w['sample'][mask],color='#666',ls='--',label='External SAMPLE = 0')
    axes[1].plot(x[mask],w['seq_sample'][mask],color='#2676a2',label='Internal SEQ_SAMPLE')
    axes[1].plot(x[mask],.5*w['vdd'][mask],color='#666',ls='--',label='Instantaneous VDD / 2')
    for event in m['pre_formal_SEQ_events']:
        t=event['time_ns'];level=.5*np.interp(t,x,w['vdd'])
        axes[1].scatter([t],[level],s=23,color='#b85b45',zorder=5)
        for ax in axes:ax.axvline(t,color='#999',ls=':',lw=.8)
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Supply / source (V)');axes[1].set_ylabel('SEQ / threshold (V)')
    axes[1].set_xlabel('Absolute time (ns)')
    fig.suptitle('Power-up transition with external clock held low\n'
        'Native markers: crossings relative to moving half-VDD; not accepted sampling events',fontsize=10.5)
    fig.savefig(OUT/'power_up_clock_detail.png',dpi=165);plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    # Both scalar reviews verified the original collection and frozen inputs.
    cases={case:read_curves(case) for case in ['dc_core','ramp_core']}
    comparisons=[]
    for i,target in enumerate([-.81,0]):
        dc=cases['dc_core'][0]['frames'][i];ramp=cases['ramp_core'][0]['frames'][i]
        comparisons.append(dict(frame=i,source_diff_v=target,
            delta_ramp_minus_DC_preclose_mv=ramp['preclose_error_mv']-dc['preclose_error_mv'],
            delta_ramp_minus_DC_held_mv=ramp['held_error_at_nominal_edge_mv']-dc['held_error_at_nominal_edge_mv'],
            delta_ramp_minus_DC_net_turnoff_mv=ramp['net_turnoff_voltage_change_mv']-dc['net_turnoff_voltage_change_mv'],
            delta_actual_open_ps=(ramp['actual_open_ns']-dc['actual_open_ns'])*1000,
            delta_actual_close_ps=(ramp['actual_close_ns']-dc['actual_close_ns'])*1000))
    m,e,w=cases['ramp_core']
    startup=[]
    for event in m['pre_formal_SEQ_events']:
        startup.append(dict(event,VDD_v=float(np.interp(event['time_ns'],w['time_ns'],w['vdd'])),
            definition='native crossing relative to instantaneous half-VDD, not a qualified clock event'))
    plots(cases)
    result=dict(scope='existing DC versus zero-to-supply pair only',
        cases={name:dict(measurements=m,evidence=e) for name,(m,e,_) in cases.items()},
        same_frame_comparisons=comparisons, ramp_pre_formal_SEQ_crossings=startup,
        local_plot_peak_working_set_mib=peak_working_set(),
        internal_SEQ_low_throughout_ramp=False,
        first_and_second_frames_have_different_input_conditions=True,
        startup_accuracy_pass=None, POR_qualified=False,
        causal_scope='VDD prehistory changes Bootstrap/CDAC initial states and internal power-up transitions together; Cboot contribution is not separately isolated',
        no_new_run_or_package=True, no_remote_operation=True,
        fast_node_snapshot_limit='10ps-before-opening values interpolate20ps exports; use100.99/200.99ns and110/210ns for robust phase comparisons')
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(comparisons=comparisons,ramp_pre_formal_events=startup,
        local_peak_working_set_mib=result['local_plot_peak_working_set_mib']),indent=2))


if __name__=='__main__':main()
