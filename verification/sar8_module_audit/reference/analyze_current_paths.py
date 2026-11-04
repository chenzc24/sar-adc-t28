"""Local branch attribution/figures from immutable completed reduce1 evidence."""
from __future__ import annotations
import gzip
import hashlib
import json
import os
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=ROOT/'output/managed_execution/runs/sar8audit-ref-current-v2-reduce1/collected'
OUT=HERE/'generated/current_branch_review'
P='xdut.xref.xdrv0.'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze():
    OUT.mkdir(parents=True,exist_ok=True)
    r=json.loads((SOURCE/'derived/result.json').read_text())
    cfg=json.loads((HERE/'generated/current_v2/measurement.json').read_text())
    rec=r['native_exports'][1]
    raw=gzip.decompress((SOURCE/'derived'/rec['file']).read_bytes())
    if hashlib.sha256(raw).hexdigest()!=rec['uncompressed_sha256']:
        raise ValueError('Native fault payload changed')
    w=np.frombuffer(raw,dtype='<f8').reshape((-1,len(rec['columns'])))
    c={n:i for i,n in enumerate(rec['columns'])};t=w[:,0];vdd=w[:,c['vdd!']]
    groups={
        'A':[[P+'gnnan:1'],[P+'gnnap:1'],[P+'gnnbn:2',P+'gnnbp:2']],
        'B':[[P+'gnnbn:1'],[P+'gnnbp:1'],[P+'gnncn:2',P+'gnncp:2']],
        'C':[[P+'gnncn:1'],[P+'gnncp:1'],[P+'rgnn0:1']]}
    node_names={'A':P+'gnna','B':P+'gnnb','C':P+'gnndrv'}
    details={}
    for stage,node in node_names.items():
        y=w[:,c[node]];minimum=stage=='B'
        peak=int(np.argmin(y) if minimum else np.argmax(y))
        # Existing native bracket only: no manufactured threshold-time endpoint.
        outside=np.flatnonzero(y[:peak]>=0 if minimum else y[:peak]<=vdd[:peak])
        start=int(outside[-1]);terms=[x for group in groups[stage] for x in group]
        branch={}
        for name in terms:
            values=w[:,c[name]];segment=values[start:peak+1]
            branch[name]=dict(at_peak_A=float(values[peak]),signed_leading_charge_fC=float(np.trapezoid(segment,t[start:peak+1])*1e15),
                positive_charge_fC=float(np.trapezoid(np.maximum(segment,0),t[start:peak+1])*1e15),
                negative_charge_fC=float(np.trapezoid(np.minimum(segment,0),t[start:peak+1])*1e15))
        grouped=[]
        for names in groups[stage]:
            values=sum(w[:,c[x]] for x in names)
            grouped.append(dict(terminals=names,at_peak_A=float(values[peak]),
                signed_leading_charge_fC=float(np.trapezoid(values[start:peak+1],t[start:peak+1])*1e15)))
        kcl=sum(w[:,c[x]] for x in terms)
        peak_snapshot=r['peak_snapshots'][node]
        ports={}
        for suffix in ['n','p']:
            dev='gnn'+stage.lower()+suffix
            ports[dev]={pin:peak_snapshot['all_selected_currents_a'][P+dev+':'+str(k)] for k,pin in enumerate('DGSB',1)}
        details[stage]=dict(node=node,peak_voltage_V=float(y[peak]),peak_time_s=float(t[peak]),
            excursion_mV=float((y[peak]-(0 if minimum else vdd[peak]))*1e3),
            leading_native_interval_s=[float(t[start]),float(t[peak])],leading_native_points=peak-start+1,
            rail_crossing_note='Starts at last native point outside excursion before native extremum; no interpolated charge endpoint',
            branch=branch,groups=grouped,local_max_KCL_A=float(np.max(np.abs(kcl[start:peak+1]))),
            leading_KCL_integral_fC=float(np.trapezoid(kcl[start:peak+1],t[start:peak+1])*1e15),
            MOS_all_four_terminal_currents_at_native_peak_A=ports,
            voltages_at_peak_V={n:float(w[peak,c[n]]) for n in [P+'gnnpre',P+'gnna',P+'gnnb',P+'gnndrv',
                'xdut.gnn0','xdut.xcdac.bn0','xdut.xcdac.bp0','xdut.xref.h0','xdut.xref.l0']},
            start_index=start,peak_index=peak)
    events={n:[x for x in records if 65.15e-9<=x['estimated_time_s']<=65.6e-9]
            for n,records in r['half_vdd_events'].items()}
    max_edge=max(abs(item['error_time_s']) for data in r['source_half_vdd_event_diagnostics']['nodes'].values() for item in data['ordinal_pairs'])
    quiet=(t>=65.17e-9)&(t<=65.18e-9)
    quiet_gate={name:float(np.max(np.abs(w[quiet,c[P+name+':2']]))) for name in ['gnnbn','gnnbp','gnncn','gnncp']}
    measured=dict(source_run=r['measured_source_run_id'],analysis_run='sar8audit-ref-current-v2-reduce1',
        source_result_sha256=sha(SOURCE/'derived/result.json'),source_fault_sha256=rec['sha256'],
        native_points=r['native_points'],native_fault_points=len(w),all275_currents_present=r['all_selected_currents_present_and_initialized'],
        sign='Positive current enters component from its node; negative current injects into the node. Signed terminal charge is NOT an intrinsic Cgd/channel partition.',
        stages=details,events=events,quiet_gate_current_max_abs_A=quiet_gate,
        fidelity=dict(max_peak_voltage_error_V=max(abs(x['error_v']) for x in r['source_peak_reproduction_diagnostic'].values()),
            max_peak_time_error_s=max(abs(x['error_time_s']) for x in r['source_peak_reproduction_diagnostic'].values()),
            max_native_sample_curve_error_V=max(x['max_abs_v'] for x in r['source_wave_reproduction_diagnostic']['voltage_errors'].values()),
            max_half_vdd_edge_error_s=max_edge,max_initial_witness_error_V=max(abs(x) for x in r['initial_witness_error_v'].values()),
            verdict='Diagnostic fidelity numbers only; original acceptance_pass remains null'),
        maximum_full_history_absolute_KCL_A=max(x['max_abs_a'] for x in r['node_kcl'].values()),
        maximum_fault_absolute_KCL_A=max(x['fault_max_abs_a'] for x in r['node_kcl'].values()),
        normalized_KCL_caution='Ratios reaching1 occur at near-zero currents; absolute residual is the meaningful scale here.',
        current_partition_limit='D/G/S/B are total native PDK wrapper currents. Gate-edge timing and signed port flows support dynamic feedthrough, but intrinsic overlap/junction/channel percentages are not identified.',
        original_warnings=r['original_simulator_log'],native_effective_settings=r['native_effective_settings'],
        next_experiment=dict(status='unexecuted single-variable block diagnostic',parameter='R_C_input',value_ohm=1000,
            edit='Insert one ideal1kOhm series resistor from original GNNB to a new GNN_CG node; reconnect BOTH GNNCN/GNNCP gates to GNN_CG in driver0 only. All other devices and geometry unchanged.',
            motivation='Slow the common final-stage input edge and its gate-charge pulse; hold initial rail longer. Test the dynamic feedthrough hypothesis without retiming external clocks.',
            preserve=['Supply0.99V and full supply range','sample window and closing edge','frozen external PWL','all original geometry/models and other drivers','full physical CDAC/reference/source loads'],
            measurements=['GNNB/newGNN_CG/GNNDRV and five baseline KCL nodes','all original275 currents plus both new resistor ports',
                'Update B-node KCL: replace GNNCN/GNNCP gate ports with resistor input port; explicitly close new gate-node KCL with resistor output and both MOS gates',
                'All228 old terminal-pair screens; new gate voltage included','C peak/undershoot, A/B peaks, reference settling and edge delay, added crowbar charge/power'],
            caveat='Ideal resistor is a mechanism experiment, not a qualified PDK resistor implementation. A/B still need repair; replayed D/CODE do not prove closed-loop ADC codes. No success forecast or remote task.'))
    (OUT/'branch_metrics.json').write_text(json.dumps(measured,indent=2)+'\n')
    make_figures(w,c,details,r)
    print(json.dumps(dict(stages={k:{n:v[n] for n in ['peak_time_s','peak_voltage_V','excursion_mV','local_max_KCL_A']}
                                    for k,v in details.items()},fidelity=measured['fidelity']),indent=2))


def make_figures(w,c,details,result):
    os.environ.setdefault('MPLCONFIGDIR',str(HERE/'cache/mpl_current'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#276b9b','#ce5144','#24847c']
    t=w[:,0]
    labels={'A':['D(A_N)','D(A_P)','G(B_N)+G(B_P)'],
            'B':['D(B_N)','D(B_P)','G(C_N)+G(C_P)'],
            'C':['D(C_N)','D(C_P)','Rgate toward load']}
    inputs={'A':P+'gnnpre','B':P+'gnna','C':P+'gnnb'}
    fig,axs=plt.subplots(3,3,figsize=(13.5,8.5),layout='constrained')
    for column,stage in enumerate(['A','B','C']):
        item=details[stage];pk=item['peak_index'];start=item['start_index'];at=t[pk]
        x=(t-at)*1e12;sel=(x>=-4.3)&(x<=.65)
        ax=axs[0,column]
        ax.plot(x[sel],w[sel,c[inputs[stage]]],color='#b27b25',lw=1.2,label='stage input')
        ax.plot(x[sel],w[sel,c[item['node']]],color=colors[0],lw=1.6,label='stage output')
        ax.axhline(.99,color='#777',ls=':',lw=.8);ax.axhline(0,color='#777',ls=':',lw=.8)
        ax.scatter([0],[item['peak_voltage_V']],color=colors[1],s=18,zorder=4)
        ax.set_title('%s: %s | %.6f ns\n%+.3f mV beyond rail'%(stage,item['node'].split('.')[-1].upper(),at*1e9,item['excursion_mV']),fontsize=10)
        ax.set_ylim(-.10,1.13);ax.set_ylabel('Voltage (V)');ax.legend(fontsize=7,loc='lower left')
        ax2=axs[1,column];ax3=axs[2,column]
        for group,label,color in zip(item['groups'],labels[stage],colors):
            i=sum(w[:,c[n]] for n in group['terminals'])
            ax2.plot(x[sel],i[sel]*1e6,label=label,color=color,lw=1.25)
            s=slice(start,pk+1);area=np.r_[0,np.cumsum((i[s][:-1]+i[s][1:])*.5*np.diff(t[s]))]*1e15
            ax3.plot(x[s],area,color=color,lw=1.5)
        ax2.set_ylabel('Port current (uA)');ax2.legend(fontsize=7,loc='best')
        ax3.set_ylabel('Signed port charge (fC)');ax3.set_xlabel('Time relative to this native peak (ps)')
        for row in range(3):
            axis=axs[row,column];axis.axvline(0,color='#777',ls='--',lw=.8)
            axis.axvspan(x[start],0,color='#777',alpha=.07)
            axis.set_xlim(-4.3,.65);axis.grid(alpha=.18)
            if row:axis.axhline(0,color='#555',lw=.7)
    fig.suptitle('Driver0: native current balance and leading-excursion charge',fontsize=14)
    fig.supxlabel('T28 FF / 0.99 V / -40 C | original core driver + IO reference switches + full CDAC | ideal external rails/clocks | no noise, mismatch or PEX\n'
                   'Current positive INTO component. Charge integrates existing native points in the shaded interval; it is not a Cgd/channel partition.',fontsize=8)
    fig.savefig(OUT/'driver0_branch_charge.png',dpi=170);plt.close(fig)

    fig,axs=plt.subplots(4,1,figsize=(12,8.5),sharex=True,layout='constrained')
    ns=t*1e9;sel=(ns>=65.18)&(ns<=65.60)
    for node,label in [('xdut.xref.cap_clk','CAP_CLK'),('xdut.xref.q0','Q0'),('xdut.xref.l0','L0'),('xdut.xref.h0','H0')]:
        axs[0].plot(ns[sel],w[sel,c[node]],label=label,lw=1.2)
    axs[0].set_ylabel('Capture / BBM (V)');axs[0].legend(ncol=4,fontsize=8,loc='upper right')
    for node,label,color in [(P+'gnndrv','GNNDRV - VDD',colors[1]),('xdut.gnn0','GNN0 - VDD',colors[0])]:
        axs[1].plot(ns[sel],(w[sel,c[node]]-w[sel,c['vdd!']])*1e3,label=label,color=color,lw=1.5)
    axs[1].set_ylim(-6,80);axs[1].set_ylabel('Rail excursion (mV)');axs[1].legend(fontsize=8,loc='upper right')
    tp=details['C']['peak_time_s']*1e9
    axs[1].scatter([tp],[details['C']['excursion_mV']],color=colors[1],s=20)
    axs[1].annotate('+67.986 mV',(tp,details['C']['excursion_mV']),xytext=(65.29,50),fontsize=9,
                    arrowprops={'arrowstyle':'->','lw':.9,'color':colors[1]})
    gnn_peak=int(np.argmax(w[:,c['xdut.gnn0']]))
    axs[1].annotate('+1.208 mV',(ns[gnn_peak],(w[gnn_peak,c['xdut.gnn0']]-.99)*1e3),xytext=(65.30,15),fontsize=9,
                    arrowprops={'arrowstyle':'->','lw':.9,'color':colors[0]})
    axs[2].plot(ns[sel],w[sel,c[P+'rgnn0:1']]*1e6,color=colors[2],label='Rgate: driver toward load',lw=1.4)
    axs[2].plot(ns[sel],w[sel,c['xdut.xcdac.xsn0.mn_low:2']]*1e6,color='#555',ls='--',label='MN_LOW gate (same flow)',lw=1)
    axs[2].set_ylabel('Current (uA)');axs[2].legend(fontsize=8,loc='lower right')
    axs[2].annotate('+0.686 uA at driver peak',(tp,details['C']['groups'][2]['at_peak_A']*1e6),
                    xytext=(65.31,2),fontsize=9,arrowprops={'arrowstyle':'->','lw':.8})
    for node,label,color in [('xdut.xcdac.bn0','BN0',colors[0]),('xdut.xcdac.bp0','BP0',colors[1])]:
        axs[3].plot(ns[sel],w[sel,c[node]],label=label,color=color,lw=1.5)
    axs[3].axhline(.9,color='#777',ls=':',lw=.7);axs[3].axhline(0,color='#777',ls=':',lw=.7)
    axs[3].set_ylabel('CDAC bottom (V)');axs[3].set_xlabel('Native simulation time (ns)');axs[3].legend(fontsize=8,loc='upper right')
    for ax in axs:
        ax.axvline(tp,color='#777',ls='--',lw=.9);ax.grid(alpha=.18);ax.set_xlim(65.18,65.60)
    fig.suptitle('Late-CODE capture: internal driver peak precedes bottom-plate handoff',fontsize=13)
    fig.supxlabel('Same FF / 0.99 V / -40 C block reproduction | native waveforms | CMI and CAP_REQ LTE warnings retained\n'
                   'At the driver peak, Rgate removes charge from the driver; this is not net positive-charge backflow from CDAC.',fontsize=8)
    fig.savefig(OUT/'driver0_load_timing.png',dpi=170);plt.close(fig)


if __name__=='__main__':analyze()
