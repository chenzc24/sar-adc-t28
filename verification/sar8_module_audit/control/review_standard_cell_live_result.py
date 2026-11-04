"""Compact completed LIVE-stage comparison: one table and one figure."""
import json
import os

import numpy as np

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected,values,duration

OWN,ROOT=base.OWN,base.ROOT
OUT=OWN/'standard_cell_live_v1/results'
P='xdut.xctrl.xtim.'
RUNS={'R0 MN1':('sar8audit-ctrl-stdcell-r0-ff-v1','f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a'),
      'LIVE library':('sar8audit-ctrl-stdcell-live-ff-v1','a99eeaad32f6fb75ac2c548ebf617690091e2175fb022aa43437e522684a9226')}


def main():
    data={tag:read_current_run(*ids) for tag,ids in RUNS.items()}
    reference=json.loads((OWN/'standard_cell_live_v1/source_load_reference.json').read_bytes())
    if (reference['source_run'],reference['source_recipe_sha256'])!=RUNS['R0 MN1']:raise ValueError('Source load reference identity differs')
    report=dict(scope='FF0.99V/-40C first-event whole-X001 stage replacement from R0 MN1',cases={},
        whole_ADC_qualified=False,circuit_repair_claim=False,
        implementation='Old6MOS and explicit MID capacitor removed as one logic-stage implementation; no individual device/cap causality inferred.')
    for tag,(t,n,r,m,proof) in data.items():
        if tag=='R0 MN1' and reference['source_proof']!=proof:raise ValueError('Source loading proof differs from completed run')
        raw=collected(RUNS[tag][0]);sim=json.loads(raw['simulation.state.json'])
        load=reference['input_loads'] if tag=='R0 MN1' else r['LIVE_stage_input_loading']
        quiet=[e['time_s'] for e in r['diagnostic_timing']['signals'][P+'quiet']['threshold_events'] if e['fraction']==.5 and e['direction']==1][0]
        i=int(np.argmin(values(t,n,P+'live')));terms=m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE']
        groups={}
        for instance,item in m['standard_cell_experiment']['observed_mos'].items():
            label='LIVE_stage' if instance.startswith('XDUT.XCTRL.XTIM.X001.') else 'X020_stage' if instance.startswith('XDUT.XCTRL.XTIM.X020.') else 'other_core'
            g=groups.setdefault(label,dict(MOS=0,pairs=0,failed_pairs=0));g['MOS']+=1;g['pairs']+=6
            g['failed_pairs']+=sum(r['full_history_voltage_stress'][key]['over_limit_native_points']>0 for key in item['six_pair_labels'].values())
        case=dict(proof=proof,node_extrema={s:r['voltage_and_current_extrema'][P+s] for s in ['sn','x001.n','live','x020.a1_filter','x020.n','q1','quiet','clock_reset','xclock.rb']},
            QUIET_after_sample_close_s=quiet-r['diagnostic_timing']['sample_close_s'],
            LIVE_below_minus1mV_duration=duration(t[:,0],np.minimum(values(t,n,P+'live'),0),.001),
            input_loads={k:dict(total_peak_a=v['diagnostic_window_extrema']['total_gate']['max'],
                total_trough_a=v['diagnostic_window_extrema']['total_gate']['min'],
                total_gate_exchange_c=v['event_exchange']['total_into_gate_devices_c'],
                first_native_s=v['event_exchange']['first_native_s'],last_native_s=v['event_exchange']['last_native_s'],
                rise_10_90_s=v['rise_10_90_s'],fall_90_10_s=v['fall_90_10_s']) for k,v in load.items()},
            LIVE_minimum_snapshot=dict(time_s=float(t[i,0]),input_N_v=float(values(t,n,P+'x001.n')[i]),
                voltage_v=float(values(t,n,P+'live')[i]),current_positive_out_a={s:float(t[i,n.index(s)]) for s in terms},
                KCL_sum_a=sum(float(t[i,n.index(s)]) for s in terms)),
            groups=groups,KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            five_source_energy_j={k:v['net_delivered_j'] for k,v in r['full_history_source_energy'].items()},
            R0_absorbed_j=r['full_history_resistor_energy']['absorbed_j'],
            native_warning_codes=proof['native_warning_codes'],native_effective_settings=sim['native']['effective_settings'])
        if sum(g['pairs'] for g in groups.values())!=606:raise ValueError('Physical pair grouping differs')
        if tag!='R0 MN1':
            if len(r['standard_cell_native_current_bindings'])!=12:raise ValueError('Twelve library MOS bindings missing')
            case['library_native_current_ports']=sum(len(v['actual']) for v in r['standard_cell_native_current_bindings'].values())
            case['seven_boundary_source_work_j']={k:v['net_delivered_j'] for k,v in r['full_history_boundary_source_energy'].items()}
        report['cases'][tag]=case
    a,b=report['cases'].values()
    if a['native_effective_settings']!=b['native_effective_settings']:raise ValueError('Effective solver differs')
    report['change']=dict(LIVE_negative_peak_reduction_fraction=1-b['node_extrema']['live']['min']/a['node_extrema']['live']['min'],
        QUIET_delay_added_s=b['QUIET_after_sample_close_s']-a['QUIET_after_sample_close_s'],
        VDD_energy_reduction_fraction=1-b['five_source_energy_j']['VDD']/a['five_source_energy_j']['VDD'])
    report['next_repair_recommendation']=dict(target='XCLOCK.X000 reset inverter producing RB',
        action='Propose only one logic-stage substitution with verified INVD1, same CLOCK_RESET input and RB SR fanout; keep reset polarity/priority and all other cells unchanged.',
        reason='RB still reaches about-25.523mV, now larger than LIVE dip and unchanged by this replacement.',
        observe='Keep incident CLOCK_RESET overshoot about+24mV separately visible; one receiver substitution cannot be presumed to remove upstream stress.',
        no_new_circuit_or_remote_job=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    figure(data)
    print(json.dumps(dict(change=report['change'],cases={k:dict(delay_ps=v['QUIET_after_sample_close_s']*1e12,
        LIVE_negative1mV_ps=v['LIVE_below_minus1mV_duration']['total_linear_crossing_s']*1e12,
        total_failed_pairs=sum(g['failed_pairs'] for g in v['groups'].values()),loads=v['input_loads']) for k,v in report['cases'].items()}),indent=2))


def figure(data):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'R0 MN1':'#63778b','LIVE library':'#c76b2b'}
    fig,axes=plt.subplots(5,1,sharex=True,figsize=(10,9.6),layout='constrained')
    for ax,node,title in zip(axes,['sn','x001.n','live','x020.n','quiet'],['SN input','X001.N: stage internal node','LIVE output','X020.N: next NAND output','QUIET output']):
        for tag,(t,n,*_) in data.items():ax.plot(t[:,0]*1e9,values(t,n,P+node),color=colors[tag],ls='--' if tag=='R0 MN1' else '-',lw=1.5,label=tag)
        ax.set(title=title,ylabel='V');ax.axhline(0,color='#888',lw=.7);ax.axhline(.99,color='#888',ls=':',lw=.7);ax.grid(alpha=.18)
        ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    axes[0].legend(ncol=2,fontsize=9);axes[-1].set(xlim=(41.06,41.14),xlabel='Native time (ns)')
    zoom=axes[2].inset_axes([.57,.18,.40,.66])
    for tag,(t,n,*_) in data.items():zoom.plot(t[:,0]*1e9,values(t,n,P+'live')*1e3,color=colors[tag],ls='--' if tag=='R0 MN1' else '-',lw=1.2)
    zoom.set(xlim=(41.078,41.084),ylim=(-33,2),xticks=[41.078,41.081,41.084],yticks=[-30,0]);zoom.tick_params(labelsize=7)
    zoom.set_ylabel('mV',fontsize=8,labelpad=1);zoom.axhline(0,color='#888',lw=.6);zoom.grid(alpha=.15)
    zoom.ticklabel_format(axis='x',style='plain',useOffset=False)
    fig.suptitle('LIVE stage library replacement: smaller dip, similar output timing',fontsize=13)
    fig.supxlabel('FF | 0.99 V | -40 C | whole-stage replacement | same R0, actual loads and PWL\nIdeal external supply/clock | native first event | no noise, mismatch or PEX',fontsize=8)
    fig.savefig(OUT/'parallel_waveforms.png',dpi=165);plt.close(fig)


if __name__=='__main__':main()
