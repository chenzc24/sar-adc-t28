"""Receipt-bound MN1/MN2 comparison; preserve refused admission, no remote work."""
import json
import os
import re

import numpy as np
import yaml

import prepare_first_event as base
from review_both_result import read_current_run
from review_standard_cell_result import collected,values,duration,charge
from standard_cell_r0_mn2_analyze import input_loading

OWN,ROOT=base.OWN,base.ROOT
OUT=OWN/'standard_cell_r0_mn2_v1/results'
P='xdut.xctrl.xtim.'
TARGET='XDUT.XCTRL.XTIM.X001.X001.MN'
RUNS={'MN1':('sar8audit-ctrl-stdcell-r0-ff-v1','f182531c14a57e1a6aabb8a38fb532c17b7ae56b8889ec504e8fadc8244f990a'),
      'MN2':('sar8audit-ctrl-stdcell-r0-mn2-ff-q2','3b0e98474b6d0dc6e6a11484382c79e06d762e3a4d070c8134536097cedff31c')}
REJECTED='sar8audit-ctrl-stdcell-r0-mn2-ff-v1'
REJECTED_HASH='a262cf7214baa45720243b0252a0988d6c2ddcfcd391b9f1aebf571853927629'
COLORS={'MN1':'#63778b','MN2':'#c76b2b'}


def record(run,expected):
    r=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
    if r['recipe_hash']!=expected or base.digest(json.dumps(r['recipe'],sort_keys=True,separators=(',',':')).encode())!=expected:
        raise ValueError('Managed recipe identity differs')
    return r['recipe']


def admissions():
    old=record(REJECTED,REJECTED_HASH);new=record(*RUNS['MN2'])
    old_files={i['name']:(i['source'],i['bytes'],i['sha256']) for i in old['files']}
    new_files={i['name']:(i['source'],i['bytes'],i['sha256']) for i in new['files']}
    freeze=json.loads((OWN/'standard_cell_r0_mn2_v1/freeze.json').read_bytes())
    declared={i['name']:(i['bytes'],i['sha256']) for i in freeze['inputs']}
    if old_files!=new_files or len(declared)!=21:raise ValueError('q2 did not preserve refused input identities')
    if any(name not in new_files or new_files[name][1:]!=identity for name,identity in declared.items()):
        raise ValueError('Managed input identity differs from declared21-file freeze')
    added={name:v for name,v in new_files.items() if name not in declared}
    if set(added)!={'native_summary.py'} or added['native_summary.py'][0]!='scripts/management/native_summary.py':
        raise ValueError('Unexpected management-added helper')
    files=collected(REJECTED);state=json.loads(files['simulation.state.json'])
    if (set(files)!={'simulation.admission.json','simulation.state.json'} or state['status']!='rejected'
            or state['reason']!='queue_timeout' or state.get('child_identity') or state.get('started_epoch') or state.get('native')
            or 'host_memory_headroom' not in state['waiting_reasons']):
        raise ValueError('Refused first admission is not verified as never started')
    return dict(rejected_run=REJECTED,rejected_recipe_sha256=REJECTED_HASH,
        status=state['status'],reason=state['reason'],waiting_reasons=state['waiting_reasons'],
        receipt_files=len(files),receipt_bytes=sum(len(b) for b in files.values()),
        native_simulation_started=False,has_no_child_or_start_or_native=True,
        actual_run=RUNS['MN2'][0],actual_recipe_sha256=RUNS['MN2'][1],identical_declared_input_files=21,
        identical_managed_files=len(new_files),unchanged_management_added_helper=added,
        recipe_keys_differ=[k for k in sorted(set(old)|set(new)) if old.get(k)!=new.get(k)],
        policy='Original admission retained, not a circuit simulation failure. q2 has independent identity and actual result; no uncertain execution was rerun under another ID.')


def source_loading(tag,cfg,raw):
    folder=ROOT/'output/managed_execution/runs'/RUNS[tag][0]/'collected'
    for name in ['derived/peak.native.bin','derived/peak.columns.json']:
        if (folder/name).read_bytes()!=raw[name]:raise ValueError('Canonical waveform differs from receipt-verified member')
    observed=input_loading(str(folder/'derived'),cfg)
    if tag=='MN1':
        reference=json.loads((OWN/'standard_cell_r0_mn2_v1/source_input_loading_reference.json').read_bytes())
        if (reference['source_run'],reference['source_recipe_sha256'],reference['actual_source_multiplicity'])!=(*RUNS['MN1'],1):
            raise ValueError('Ancillary one-unit loading reference source differs')
        expected=reference['loading_observation']
    else:expected=json.loads(raw['derived/result.json'])['changed_driver_input_loading']
    for k in ['native_points','event_exchange','diagnostic_window_extrema','threshold_events','fall_90_10_s']:
        if observed[k]!=expected[k]:raise ValueError('Identical native loading reduction differs: '+k)
    return observed


def snap(table,names,m,node,at):
    i=int(np.flatnonzero(table[:,0]==at)[0]);terms=m['kcl_terms'][node]
    return dict(time_s=float(at),node=node,
        voltages_v={n:float(values(table,names,n)[i]) for n in [P+'x001.n',P+'live',P+'x020.a1_filter',P+'x020.n',P+'quiet']},
        current_out_a={s:float(table[i,names.index(s)]) for s in terms},
        KCL_sum_a=sum(float(table[i,names.index(s)]) for s in terms))


def main():
    report=dict(scope='FF0.99V/-40C one original LIVE NMOS multi1->2, same unit and native R0/library; first event only',
        admission_history=admissions(),cases={},whole_ADC_qualified=False,circuit_repair_claim=False,
        evidence_policy='Original native rows. No alignment, forced waveform points, zero-filled traces or artificial current multiplicity.',
        duration_policy='Linear threshold-crossing estimates retain native brackets. Exact0.99V screens unchanged; compare duration, not mesh-dependent sample counts.')
    data={tag:read_current_run(*identity) for tag,identity in RUNS.items()}
    load_cfg=json.loads((OWN/'standard_cell_r0_mn2_v1/measurement.json').read_bytes())
    reference_stop=data['MN1'][2]['voltage_and_current_extrema'][P+'live']['min_time_s']
    for tag,(table,names,r,m,proof) in data.items():
        raw=collected(RUNS[tag][0]);sim=json.loads(raw['simulation.state.json']);analysis=json.loads(raw['analysis.state.json'])
        log=raw['spectre.out'].decode('utf-8',errors='replace')
        loading=source_loading(tag,load_cfg,raw)
        case=dict(proof=proof,input_loading=loading,node_metrics={},snapshots={},
            simulation_seconds=sim['elapsed_seconds'],simulation_peak_rss_bytes=sim['peak_rss_bytes'],
            analysis_seconds=analysis['elapsed_seconds'],analysis_peak_rss_bytes=analysis['peak_rss_bytes'],
            native_effective_settings=sim['native']['effective_settings'],KCL_max_a=max(v['max_abs_a'] for v in r['node_kcl'].values()),
            source_energy=r['full_history_source_energy'],five_source_net_work_j=sum(v['net_delivered_j'] for v in r['full_history_source_energy'].values()),
            resistor_energy=r['full_history_resistor_energy'],resistor_metrics=r['series_resistor_metrics'],
            native_warning_codes=proof['native_warning_codes'],displayed_CMI_lines=[s.strip() for s in log.splitlines() if 'WARNING (CMI-' in s],
            suppressed_warning_count=int(re.search(r'(\d+) warnings suppressed',log)[1]))
        for label,node in {'X001.N':P+'x001.n','LIVE':P+'live','A1':P+'x020.a1_filter','N':P+'x020.n',
            'Q1':P+'q1','QUIET':P+'quiet','RC1':P+'xd_quiet_d.rc1','RESET':P+'clock_reset','RB':P+'xclock.rb'}.items():
            v=values(table,names,node);full=r['voltage_and_current_extrema'][node]
            above=duration(table[:,0],v,.99)
            case['node_metrics'][label]=dict(node=node,full_history_extrema=full,end_voltage_v=float(v[-1]),
                above_rail=above,above_rail_plus1mV=duration(table[:,0],v,.991),below_ground_1mV=duration(table[:,0],np.minimum(v,0),.001),
                peak_rail_episode=next((d for d in above['intervals'] if d['start_s']<=full['max_time_s']<=d['stop_s']),None))
        timing=r['diagnostic_timing'];series=r['series_resistor_metrics'];close=timing['sample_close_s']
        quiet=[e['time_s'] for e in timing['signals'][P+'quiet']['threshold_events'] if e['fraction']==.5 and e['direction']==1]
        case['timing']=dict(sample_close_s=close,X001N_fall_90_10_s=loading['fall_90_10_s'],X001N_falling_halfrail_s=loading['falling_halfrail_s'],
            LIVE_rise_10_90_s=series['nodes'][P+'live']['rise_10_90_s'],A1_rise_10_90_s=series['nodes'][P+'x020.a1_filter']['rise_10_90_s'],
            A1_relative_LIVE_s=series['A1_first_halfrail_relative_LIVE_s'],QUIET_after_close_s=quiet[0]-close,
            N_fall_90_10_s=timing['signals'][P+'x020.n']['fall_90_10_s'],
            later_clock_observations={s:timing['signals'][s] for s in [P+'quiet_d',P+'clock_set',P+'clock_q','xdut.cmp_clk']})
        for event,node,minimum in [('LIVE_min','LIVE',True),('input_peak','X001.N',False),('N_peak','X020.N',False)]:
            v=values(table,names,P+node.lower());i=int(v.argmin() if minimum else v.argmax())
            case['snapshots'][event]=snap(table,names,m,'XDUT.XCTRL.XTIM.'+node,table[i,0])
        terms=m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE']
        case['LIVE_exchange_common_stop']=charge(table,names,terms,41.075e-9,reference_stop)
        case['LIVE_exchange_to_own_min']=charge(table,names,terms,41.075e-9,case['snapshots']['LIVE_min']['time_s'])
        groups={};all_stress=r['full_history_voltage_stress'];watched=m['standard_cell_experiment']['observed_mos']
        for group in ['changed_driver_NM','standard_cell','other_core']:
            rows=[]
            for instance,item in watched.items():
                actual='changed_driver_NM' if instance==TARGET else 'standard_cell' if instance.startswith('XDUT.XCTRL.XTIM.X020.') else 'other_core'
                if actual!=group:continue
                for pair,label in item['six_pair_labels'].items():
                    x=all_stress[label];binding=m['stress_voltage_pairs'][label]
                    rows.append(dict(instance=instance,pair=pair,label=label,full_history=x,
                        positive_node=binding['positive_node'],negative_node=binding['negative_node'],excess_v=max(0.,x['max_abs_v']-.99)))
            rows.sort(key=lambda v:v['excess_v'],reverse=True)
            selected=rows if group!='other_core' else rows[:12]
            for item in selected:
                v=values(table,names,item['positive_node'])-values(table,names,item['negative_node'])
                item['window_duration']=duration(table[:,0],v,.99)
                x=item['full_history'];covered=bool(not x['over_limit_native_points'] or (x['first_over_limit_s']>=table[0,0] and x['last_over_limit_s']<=table[-1,0]))
                if covered and item['window_duration']['native_over_limit_points']!=x['over_limit_native_points']:raise ValueError('Duration/witness count differs')
                item['all_over_limit_witnesses_inside_window']=covered
            bounds=[0.,1.1e-7,1e-6,1e-3,1e-2,float('inf')]
            groups[group]=dict(MOS=len({v['instance'] for v in rows}),pairs=len(rows),failed_pairs=sum(v['excess_v']>0 for v in rows),
                bands=dict(zip(['0..0.11uV','0.11..1uV','1uV..1mV','1..10mV','above10mV'],[sum(a<v['excess_v']<=z for v in rows) for a,z in zip(bounds,bounds[1:])])),
                worst_pair=rows[0],selected_pair_details=selected)
        if sum(g['MOS'] for g in groups.values())!=101 or sum(g['pairs'] for g in groups.values())!=606:raise ValueError('Physical screen regrouping lost devices')
        case['harmonized_groups']=groups
        for energy in case['source_energy'].values():
            if energy['first_time_s']!=0 or energy['last_time_s']!=m['source_history_stop_s']:raise ValueError('Energy interval differs')
        report['cases'][tag]=case
    a,b=report['cases']['MN1'],report['cases']['MN2']
    if a['native_effective_settings']!=b['native_effective_settings']:raise ValueError('Effective solver differs')
    report['change']=dict(LIVE_negative_peak_reduction_fraction=1-b['node_metrics']['LIVE']['full_history_extrema']['min']/a['node_metrics']['LIVE']['full_history_extrema']['min'],
        input_fall_delay_added_s=b['timing']['X001N_fall_90_10_s'][0]-a['timing']['X001N_fall_90_10_s'][0],
        QUIET_delay_added_s=b['timing']['QUIET_after_close_s']-a['timing']['QUIET_after_close_s'],
        input_NM_net_gate_exchange_ratio=b['input_loading']['event_exchange']['into_gate_devices_c']['changed_NM']/a['input_loading']['event_exchange']['into_gate_devices_c']['changed_NM'],
        total_input_gate_exchange_ratio=b['input_loading']['event_exchange']['total_into_gate_devices_c']/a['input_loading']['event_exchange']['total_into_gate_devices_c'],
        VDD_net_energy_increase_fraction=b['source_energy']['VDD']['net_delivered_j']/a['source_energy']['VDD']['net_delivered_j']-1)
    report['next_discriminating_single_variable']=dict(
        experiment='Common-input isolated LIVE inverter: compare only NM multi1 versus2 at identical measured input.',
        fixed='Use one complete source R0 X001.N native0..END history for both units. Preserve original PM, same-unit NM, R0 and real standard NAND/INV and identified downstream loads/boundaries. Do not replace loads with one guessed C.',
        cut='Cut at inverter gate input; never attach ideal replay to a still-connected original NAND output. This is a driver-level conditional mechanism bench, not a new adopted controller.',
        missing_data='Current local voltage export begins40.81ns. Export complete recorded input and any required boundaries first; never fabricate early constant history.',
        inference='Persistence of benefit at common input supports output-unit restoration/parasitic contribution; loss of benefit shows input slowing made a major contribution. This still does not separate channel current from capacitance.',
        validation='First check multi1 reproduces its source local wave/current behavior under declared loads; measure LIVE/A1/N, input ideal-source work separately, VDD work and all interface screens.',
        proposal_only=True,no_new_circuit_or_remote_job=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    (OUT/'native_CMI_excerpt.txt').write_text('\n\n'.join(tag+'\n'+'\n'.join(c['displayed_CMI_lines']) for tag,c in report['cases'].items())+'\n',encoding='utf-8')
    figures(data,report)
    print(json.dumps(dict(admissions=report['admission_history'],change=report['change'],
        timing={k:{n:v['timing'][n] for n in ['X001N_fall_90_10_s','QUIET_after_close_s']} for k,v in report['cases'].items()},
        screens={tag:{g:(v['MOS'],v['pairs'],v['failed_pairs']) for g,v in c['harmonized_groups'].items()} for tag,c in report['cases'].items()}),indent=2))


def figures(data,report):
    os.environ.setdefault('MPLCONFIGDIR',str(OWN/'.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.titlesize':11})
    note=('FF | 0.99 V | -40 C | native first event | unchanged R0, library and RC loads\n'
          'Same PWL/sample close | ideal external supply/clock | no noise, mismatch or PEX')
    def line(ax,tag,node,scale=1.,offset=0.):
        table,names,*_=data[tag]
        ax.plot(table[:,0]*1e9,(values(table,names,node)-offset)*scale,color=COLORS[tag],ls='--' if tag=='MN1' else '-',lw=1.5,label=tag)
    def finish(fig,name,title):
        for ax in fig.axes:ax.grid(alpha=.18);ax.ticklabel_format(axis='x',style='plain',useOffset=False)
        fig.suptitle(title,fontsize=13);fig.supxlabel(note,fontsize=8);fig.savefig(OUT/name,dpi=165);plt.close(fig)
    fig,axes=plt.subplots(5,1,sharex=True,figsize=(10,9.6),layout='constrained')
    for ax,label in zip(axes,['X001.N','LIVE','A1','N','QUIET']):
        for tag,c in report['cases'].items():line(ax,tag,c['node_metrics'][label]['node'])
        ax.set(title={'X001.N':'X001.N: loaded inverter input','LIVE':'LIVE: upstream driver output','A1':'Filtered standard NAND A1','N':'Standard NAND output N','QUIET':'Loaded inverter output QUIET'}[label],ylabel='V')
        ax.axhline(0,color='#888',lw=.7);ax.axhline(.99,color='#888',lw=.7,ls=':')
        ax.axvline(report['cases']['MN2']['timing']['sample_close_s']*1e9,color='#888',lw=.7,ls=':')
    axes[0].legend(ncol=2);axes[-1].set(xlim=(41.06,41.14),xlabel='Time (ns)')
    finish(fig,'timing_comparison.png','NM multi1 to2: input slows, LIVE dip shrinks, output shifts later')

    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8),layout='constrained')
    for tag,(table,names,*_) in data.items():
        line(axes[0],tag,P+'x001.n',1e3,.99)
        line(axes[1],tag,P+'x001.x001.mn:2',1e6)
        total=values(table,names,P+'x001.x001.mn:2')+values(table,names,P+'x001.x001.mp:2')
        axes[2].plot(table[:,0]*1e9,total*1e6,color=COLORS[tag],ls='--' if tag=='MN1' else '-',lw=1.5,label=tag)
    axes[0].set(title='X001.N: positive-rail detail',ylabel='X001.N - VDD (mV)',ylim=(-1,18));axes[0].legend(ncol=2)
    axes[1].set(title='Changed NM gate: actual total native current',ylabel='Into gate (uA)')
    axes[2].set(title='NM + PM gate load at X001.N',ylabel='Into gates (uA)',xlim=(41.07,41.1),xlabel='Time (ns)')
    for ax in axes:ax.axhline(0,color='#888',lw=.7)
    finish(fig,'input_loading.png','NM input charge nearly doubles; total load also increases')

    fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8),layout='constrained')
    for tag in data:
        line(axes[0],tag,P+'live',1e3)
        line(axes[1],tag,P+'x001.x001.mp:1',-1e6)
        line(axes[2],tag,P+'x001.x001.mn:1',-1e6)
    axes[0].set(title='LIVE low-level detail',ylabel='LIVE (mV)',ylim=(-33,4));axes[0].legend(ncol=2)
    axes[1].set(title='Original PM total drain: low-level interval',ylabel='Into LIVE (uA)',ylim=(-20,6))
    axes[2].set(title='Changed NM total drain: dynamic and conductive current combined',ylabel='Into LIVE (uA)',ylim=(-10,18),xlim=(41.075,41.084),xlabel='Time (ns)')
    for ax in axes:ax.axhline(0,color='#888',lw=.7)
    finish(fig,'LIVE_current_exchange.png','Smaller LIVE dip includes both changed input slew and output-unit effects')


if __name__=='__main__':
    main()
