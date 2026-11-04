"""Compare completed direct-A1 and one-R0 cases; local native exports only."""
import json
import os
import re

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected,values,duration,charge

OWN, ROOT = base.OWN,base.ROOT
OUT = OWN/'standard_cell_r0_v1/results'
P = 'xdut.xctrl.xtim.'
RUNS = {'direct':('sar8audit-ctrl-stdcell-ff-v1','593b9ea2d3d261345eb16a21037346df3717a6c7b0781342ea09de606a611d20'),
        'R0':('sar8audit-ctrl-stdcell-r0-ff-v1','f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a')}
COLORS = {'direct':'#63778b','R0':'#c76b2b'}


def extrema(t,v):
    i,j=int(v.argmin()),int(v.argmax())
    return dict(min_v=float(v[i]),min_time_s=float(t[i]),max_v=float(v[j]),max_time_s=float(t[j]))


def snap(table,names,m,node,at,a1):
    i=int(np.flatnonzero(table[:,0]==at)[0]);terms=m['kcl_terms'][node]
    return dict(time_s=float(at),node=node,
        voltages_v={n:float(values(table,names,n)[i]) for n in
            [P+'live',a1,P+'q1',P+'x020.n',P+'x020.x000.net10',P+'quiet',P+'x001.n']},
        currents_out_of_node_a={n:float(table[i,names.index(n)]) for n in terms},
        KCL_sum_a=sum(float(table[i,names.index(n)]) for n in terms))


def main():
    data={tag:read_current_run(*identity) for tag,identity in RUNS.items()}
    report=dict(scope='FF0.99V/-40C unchanged library with one external native R0; first-event only',
        cases={},full_ADC_qualified=False,circuit_repair_claim=False,
        evidence_policy='Original native clocks, nodes and current ports. No time alignment, synthetic endpoints, zero-filled traces or channel/Cgd decomposition.',
        duration_policy='Native exported-window linear-crossing estimates with native brackets; exact0.99V screen retained. A +1mV display threshold is not acceptance.',
        integration_policy='Native terminal exchange uses existing samples only, actual boundaries returned. KCL sum is not extra stored node charge.')
    npeak_stop={tag:item[2]['peak_snapshot']['time_s'] for tag,item in data.items()}
    for tag,(table,names,r,m,proof) in data.items():
        a1=P+'live' if tag=='direct' else P+'x020.a1_filter'
        raw=collected(RUNS[tag][0]);sim=json.loads(raw['simulation.state.json'])
        log=raw['spectre.out'].decode('utf-8',errors='replace')
        case=dict(proof=proof,A1_node=a1,simulation_seconds=sim['elapsed_seconds'],simulation_peak_rss_bytes=sim['peak_rss_bytes'],
            native_effective_settings=sim['native']['effective_settings'],
            KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            node_metrics={},snapshots={},current_metrics={},
            source_energy=r['full_history_source_energy'],
            five_source_net_work_j=sum(v['net_delivered_j'] for v in r['full_history_source_energy'].values()),
            resistor_energy=r.get('full_history_resistor_energy'),resistor_metrics=r.get('series_resistor_metrics'),
            native_warning_codes=proof['native_warning_codes'],
            displayed_CMI_lines=[s.strip() for s in log.splitlines() if 'WARNING (CMI-' in s],
            suppressed_warning_count=int(re.search(r'(\d+) warnings suppressed',log)[1]))
        mapping={'LIVE':P+'live','A1':a1,'N':P+'x020.n','Q1':P+'q1','QUIET':P+'quiet',
            'RC1':P+'xd_quiet_d.rc1','RESET':P+'clock_reset','RB':P+'xclock.rb'}
        for label,node in mapping.items():
            v=values(table,names,node)
            metric=dict(node=node,full_history_extrema=r['voltage_and_current_extrema'][node],
                window_extrema=extrema(table[:,0],v),end_voltage_v=float(v[-1]),
                above_rail=duration(table[:,0],v,.99),above_rail_plus1mV=duration(table[:,0],v,.991),
                below_ground_plus1mV=duration(table[:,0],np.minimum(v,0),.001))
            at=metric['full_history_extrema']['max_time_s']
            metric['peak_rail_episode']=next((d for d in metric['above_rail']['intervals'] if d['start_s']<=at<=d['stop_s']),None)
            case['node_metrics'][label]=metric
        common_timing=r['diagnostic_timing'];close=common_timing['sample_close_s']
        source_side=common_timing['signals'][P+'live']
        receiver=source_side if tag=='direct' else r['series_resistor_metrics']['nodes'][a1]
        def first_half(item):
            if 'rising_halfrail_s' in item:return item['rising_halfrail_s'][0] if len(item['rising_halfrail_s'])==1 else None
            at=[e['time_s'] for e in item['threshold_events'] if e['fraction']==.5 and e['direction']==1]
            return at[0] if len(at)==1 else None
        case['timing']=dict(sample_close_s=close,LIVE_rise_10_90_s=source_side['rise_10_90_s'],
            A1_rise_10_90_s=receiver['rise_10_90_s'],LIVE_halfrail_s=first_half(source_side),
            A1_halfrail_s=first_half(receiver),A1_relative_LIVE_halfrail_s=0. if tag=='direct' else r['series_resistor_metrics']['A1_first_halfrail_relative_LIVE_s'],
            N_fall_90_10_s=common_timing['signals'][P+'x020.n']['fall_90_10_s'],
            QUIET_rise_10_90_s=common_timing['signals'][P+'quiet']['rise_10_90_s'],
            QUIET_after_sample_close_s=first_half(common_timing['signals'][P+'quiet'])-close,
            clock_chain_observations={s:common_timing['signals'][s] for s in [P+'quiet_d',P+'clock_set',P+'clock_q','xdut.cmp_clk']})
        for event,label,minimum in [('LIVE_min','LIVE',True),('A1_min','A1',True),('N_peak','N',False),('QUIET_min','QUIET',True)]:
            node=mapping[label];v=values(table,names,node);i=int(v.argmin() if minimum else v.argmax())
            canonical=next(n for n in m['kcl_terms'] if n.lower()==node)
            case['snapshots'][event]=snap(table,names,m,canonical,table[i,0],a1)
        nterms=m['kcl_terms']['XDUT.XCTRL.XTIM.X020.N']
        case['N_terminal_exchange']={key:charge(table,names,nterms,41.079e-9,stop) for key,stop in
            [('own_peak',npeak_stop[tag]),('common_direct_peak',npeak_stop['direct']),('common_R0_peak',npeak_stop['R0'])]}
        gate_exchange=charge(table,names,[P+'x020.x000.mm1:2',P+'x020.x000.mm4:2'],41.075e-9,table[-1,0])
        case['A1_gate_exchange']=dict(first_native_s=gate_exchange['first_native_s'],last_native_s=gate_exchange['last_native_s'],
            into_gate_devices_c={s:-v for s,v in gate_exchange['into_node_c'].items()},
            total_into_gate_devices_c=-sum(gate_exchange['into_node_c'].values()),
            interpretation='Integral of native total gate terminal currents into the two devices; not isolated Cgd or inferred node charge.')
        case['LIVE_exchange_to_minimum']=charge(table,names,m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE'],41.075e-9,case['snapshots']['LIVE_min']['time_s'])
        direct_live_minimum=data['direct'][2]['voltage_and_current_extrema'][P+'live']['min_time_s']
        case['LIVE_exchange_common_stop']=charge(table,names,m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE'],41.075e-9,direct_live_minimum)
        channels={'A1_total_gate_current':[P+'x020.x000.mm1:2',P+'x020.x000.mm4:2'],
            'A1_PM_total_drain_into_N':[P+'x020.x000.mm1:1'],
            'A1_NM_total_drain_into_N':[P+'x020.x000.mm4:1']}
        for key,terms in channels.items():
            v=sum(values(table,names,n) for n in terms)
            if 'into_N' in key:v=-v
            case['current_metrics'][key]=dict(window_extrema=extrema(table[:,0],v),
                convention='positive input current into gate devices' if 'gate' in key else 'positive total terminal current into N')
        groups={}
        stress=r['full_history_voltage_stress'];watched=m['standard_cell_experiment']['observed_mos']
        for group in ['standard_cell','retained_core']:
            rows=[]
            for instance,item in watched.items():
                if item['group']!=group:continue
                for pair,key in item['six_pair_labels'].items():
                    x=stress[key];binding=m['stress_voltage_pairs'][key]
                    rows.append(dict(instance=instance,pair=pair,label=key,full_history=x,positive_node=binding['positive_node'],
                        negative_node=binding['negative_node'],excess_v=max(0.,x['max_abs_v']-.99)))
            rows.sort(key=lambda v:v['excess_v'],reverse=True)
            selected=rows if group=='standard_cell' else rows[:15]
            for item in selected:
                v=values(table,names,item['positive_node'])-values(table,names,item['negative_node'])
                d=duration(table[:,0],v,.99);f=item['full_history'];covered=bool(not f['over_limit_native_points'] or (f['first_over_limit_s']>=table[0,0] and f['last_over_limit_s']<=table[-1,0]))
                if covered and d['native_over_limit_points']!=f['over_limit_native_points']:
                    raise ValueError('Exported-window duration native count differs from full-history witness')
                item.update(window_duration=d,all_over_limit_witnesses_in_window=covered)
            bounds=[0.,1.1e-7,1e-6,1e-3,1e-2,float('inf')]
            groups[group]=dict(MOS=len({v['instance'] for v in rows}),pairs=len(rows),failed_pairs=sum(v['excess_v']>0 for v in rows),
                excess_amplitude_bands=dict(zip(['0..0.11uV','0.11..1uV','1uV..1mV','1..10mV','above10mV'],
                    [sum(a<v['excess_v']<=z for v in rows) for a,z in zip(bounds,bounds[1:])])),
                worst_pair=rows[0],selected_pair_details=selected)
        case['screen_groups']=groups
        for item in case['source_energy'].values():
            if item['first_time_s']!=0 or item['last_time_s']!=m['source_history_stop_s']:raise ValueError('Different energy interval')
        report['cases'][tag]=case
    a,b=report['cases']['direct'],report['cases']['R0']
    if a['native_effective_settings']!=b['native_effective_settings']:raise ValueError('Different native solver settings')
    report['change']=dict(N_overshoot_reduction_fraction=1-(b['node_metrics']['N']['full_history_extrema']['max']-.99)/(a['node_metrics']['N']['full_history_extrema']['max']-.99),
        LIVE_negative_peak_increase_v=a['node_metrics']['LIVE']['full_history_extrema']['min']-b['node_metrics']['LIVE']['full_history_extrema']['min'],
        QUIET_halfrail_delay_added_s=b['timing']['QUIET_after_sample_close_s']-a['timing']['QUIET_after_sample_close_s'],
        VDD_net_energy_change_j=b['source_energy']['VDD']['net_delivered_j']-a['source_energy']['VDD']['net_delivered_j'],
        VDD_net_energy_reduction_fraction=1-b['source_energy']['VDD']['net_delivered_j']/a['source_energy']['VDD']['net_delivered_j'])
    report['next_single_variable']=dict(
        target='Original LIVE inverter NMOS XDUT.XCTRL.XTIM.X001.X001.MN',
        proposed_change='Keep W500nm/L30nm/nf1 unit and all per-unit parameters; only multi1->2 on that original NMOS. Keep current one-R0, library, PMOS, histories/window/closing edge unchanged.',
        question='Does stronger low-state restoration reduce the now-worst incident LIVE negative excursion while preserving filtered-A1/N benefits?',
        observe='Upstream X001.N extra input loading, LIVE/A1 negative minima, all606 physical pairs, N/Q1/QUIET and native delay/energy/KCL. Added unit also adds parasitics; outcome is not guaranteed.',
        scope='Proposal only; no generated candidate, remote job or full-controller expansion.')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    (OUT/'native_CMI_excerpt.txt').write_text('\n\n'.join(tag+'\n'+'\n'.join(c['displayed_CMI_lines']) for tag,c in report['cases'].items())+'\n',encoding='utf-8')
    figures(data,report)
    print(json.dumps(dict(change=report['change'],timing={k:v['timing'] for k,v in report['cases'].items()},
        screens={tag:{g:{k:v[k] for k in ['pairs','failed_pairs','excess_amplitude_bands']} for g,v in c['screen_groups'].items()} for tag,c in report['cases'].items()}),indent=2))


def figures(data,report):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.titlesize':11})
    note='FF | 0.99 V | -40 C | native first event | same PWL and sample close | no noise, mismatch or PEX'
    def finish(fig,name,title):
        for ax in fig.axes:
            ax.grid(alpha=.18);ax.ticklabel_format(axis='x',style='plain',useOffset=False)
        fig.suptitle(title,fontsize=13);fig.supxlabel(note,fontsize=8)
        fig.savefig(OUT/name,dpi=165);plt.close(fig)
    def line(ax,tag,node,scale=1.,offset=0.,label=None):
        t,n,*_=data[tag]
        ax.plot(t[:,0]*1e9,(values(t,n,node)-offset)*scale,color=COLORS[tag],
            ls='--' if tag=='direct' else '-',lw=1.5,label=label or tag)
    fig,axes=plt.subplots(5,1,sharex=True,figsize=(10,9.8),layout='constrained')
    for ax,label in zip(axes,['LIVE','A1','N','Q1','QUIET']):
        for tag,c in report['cases'].items():
            node=c['node_metrics'][label]['node']
            line(ax,tag,node,1e3 if label=='Q1' else 1.,.99 if label=='Q1' else 0.)
        ax.set(title={'LIVE':'Upstream LIVE','A1':'Receiver A1: direct wire versus R0 output','N':'NAND output N','Q1':'Retained Q1: positive-rail detail','QUIET':'Loaded inverter output QUIET'}[label],ylabel='Q1 - VDD (mV)' if label=='Q1' else 'V')
        ax.axhline(0,color='#888',lw=.7)
        if label!='Q1':ax.axhline(.99,color='#888',lw=.7,ls=':')
        ax.axvline(report['cases']['R0']['timing']['sample_close_s']*1e9,color='#888',lw=.7,ls=':')
    axes[0].legend(ncol=2,loc='upper right');axes[2].set_ylim(-.02,1.08);axes[3].set_ylim(-6,4)
    for tag,c in report['cases'].items():
        v=c['node_metrics']['N']['full_history_extrema']
        axes[2].plot(v['max_time_s']*1e9,v['max'],'o',ms=4,color=COLORS[tag])
        axes[2].annotate('%.2f mV above VDD'%((v['max']-.99)*1e3),(v['max_time_s']*1e9,v['max']),
            xytext=(65,-8 if tag=='direct' else -30),textcoords='offset points',fontsize=9,color=COLORS[tag],
            arrowprops=dict(arrowstyle='-',lw=.7,color=COLORS[tag]))
    axes[-1].set(xlim=(41.06,41.14),xlabel='Time (ns)')
    finish(fig,'timing_comparison.png','A1 series R0: slower input, smaller N peak, later QUIET')

    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8.0),layout='constrained')
    for tag,(t,n,*_) in data.items():
        gate=values(t,n,P+'x020.x000.mm1:2')+values(t,n,P+'x020.x000.mm4:2')
        axes[0].plot(t[:,0]*1e9,gate*1e6,color=COLORS[tag],ls='--' if tag=='direct' else '-',lw=1.5,label=tag)
        for ax,node in zip(axes[1:],[P+'x020.x000.mm1:1',P+'x020.x000.mm4:1']):
            line(ax,tag,node,-1e6)
    axes[0].set(title='A1 PM + NM total gate current',ylabel='Into gate devices (uA)');axes[0].legend(ncol=2)
    axes[1].set(title='A1 PM total drain current',ylabel='Into N (uA)')
    axes[2].set(title='Upper A1 NM total drain current',ylabel='Into N (uA)',xlim=(41.079,41.107),xlabel='Time (ns)')
    for ax in axes:ax.axhline(0,color='#888',lw=.7)
    finish(fig,'N_current_exchange.png','Less rapid terminal exchange; pull-down is delayed, not strengthened')

    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8.0),layout='constrained')
    for tag,c in report['cases'].items():line(axes[0],tag,P+'live',1e3)
    t,n,*_=data['R0']
    axes[0].plot(t[:,0]*1e9,values(t,n,P+'x020.a1_filter')*1e3,color='#3a9479',lw=1.4,label='R0 A1_FILTER')
    axes[0].set(title='Negative input detail: upstream versus receiver',ylabel='Voltage (mV)',ylim=(-33,4));axes[0].legend(ncol=3,fontsize=9)
    for tag in data:line(axes[1],tag,P+'x001.x001.mp:1',-1e6)
    axes[1].set(title='Original upstream PM total drain current',ylabel='Into LIVE (uA)',ylim=(-45,15))
    for tag in data:line(axes[2],tag,P+'x001.x001.mn:1',-1e6)
    axes[2].plot(t[:,0]*1e9,-values(t,n,P+'x020.rinput:1')*1e6,color='#3a9479',lw=1.4,label='R0 port1 into LIVE')
    axes[2].set(title='Restoration: original NM drain and new resistor port',ylabel='Into LIVE (uA)',ylim=(-8,35),xlim=(41.075,41.083),xlabel='Time (ns)');axes[2].legend(ncol=3,fontsize=8)
    for ax in axes:ax.axhline(0,color='#888',lw=.7)
    finish(fig,'upstream_exchange.png','Filtered A1 improves while upstream LIVE undershoot remains')


if __name__=='__main__':
    main()
