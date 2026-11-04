"""Receipt-bound three-case native comparison. Local only; frozen inputs read-only."""
from pathlib import Path
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import re
import struct
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parent
USAGE=CANDIDATE.parent
OWN=USAGE.parent
ROOT=OWN.parents[2]
for p in [OWN,USAGE,USAGE/'recovery_v1',CANDIDATE]:sys.path.insert(0,str(p))
from review_standard_cell_storage_v2 import record,identity
from review_standard_cell_full_result import receipt_files
from transition_observe import extended_edges

spec=importlib.util.spec_from_file_location('frozen_usage_report',USAGE/'results/analyze.py')
frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
COLORS={'baseline':'#2778b5','rck2k':'#a5a5a5','rck20k':'#d2513b'}
STYLES={'baseline':'-','rck2k':':','rck20k':'--'}
LABELS={'baseline':'Direct','rck2k':'2 kOhm','rck20k':'20 kOhm'}


def dump(name,obj):
    (HERE/name).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def read(p):return json.loads(Path(p).read_bytes())


def load(case):
    native_run='sar8audit-ctrl-usage-'+case+'-ff-v1'
    run=native_run if case=='rck20k' else 'sar8audit-ctrl-usage-'+case+'-gzip-v1'
    rec=record(run);src=record(native_run);folder=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==rec['recipe_hash']
    state=read(files['analysis.state.json']);assert state['status']=='complete' and state['exit_code']==0
    r=read(files['derived/result.json']);assert r['native_PSF_END'] and not r['missing_required_signals']
    if case=='rck20k':
        assert rec['recipe_hash']=='c5e24bb1779f7a04a405799aa719a4f4b67047f7d4ac5cf7bd6cb9d563e2fea9'
        sim=read(files['simulation.state.json']);assert sim['status']=='complete' and sim['exit_code']==0
        assert sim['native']['native_analysis_pass'] and sim['native']['zero_error_footer']
        log=files['spectre.out'].read_text();status=files['raw/logStatus'].read_text()
        assert re.search(r'\b0 errors\b',log) and re.search(r'\btran_first\s+PASS\b',status)
        cfg=read(CANDIDATE/'measurement.json')
    else:
        assert r['analysis_kind']=='analysis_only_completed_source_streaming_gzip'
        assert r['source_recipe_hash']==src['recipe_hash']==rec['recipe']['source']['recipe_hash']
        assert r['simulation_started'] is False and r['source_raw_unchanged'] is True
        for name,want in r['original_native_logs'].items():assert identity(files['derived/'+name])==want
        log=files['derived/source_spectre.out'].read_text();status=files['derived/source_logStatus'].read_text()
        assert re.search(r'\b0 errors\b',log) and re.search(r'\btran_first\s+PASS\b',status)
        cfg=read(USAGE/case/'measurement.json')
    assert r['measurement_sha256']==identity(CANDIDATE/'measurement.json' if case=='rck20k' else USAGE/case/'measurement.json')['sha256']
    names=read(files['derived/peak.columns.json'])['names'];idx={n:i for i,n in enumerate(names)}
    n=r['diagnostic_points'];a=np.empty((n,len(names)),dtype=np.float64);pack=struct.Struct('<'+'d'*len(names));h=hashlib.sha256();size=0;rows=0
    with gzip.open(files['derived/peak.native.bin.gz'],'rb') as f:
        while True:
            blob=f.read(pack.size)
            if not blob:break
            assert len(blob)==pack.size and rows<n
            h.update(blob);size+=len(blob);a[rows]=pack.unpack(blob);rows+=1
    assert rows==n==r['native_points']==r['storage_observations']['native_rows']
    assert dict(bytes=size,sha256=h.hexdigest())==r['returned_waveform']['uncompressed']
    assert identity(files['derived/peak.native.bin.gz'])==r['returned_waveform']['compressed']
    assert np.isfinite(a).all() and a[0,0]==0 and a[-1,0]==20e-9 and np.all(np.diff(a[:,0])>0)
    def get(node):return np.zeros(n) if node=='0' else a[:,idx[node.lower()]]
    for node,terms in cfg['kcl_terms'].items():
        total=np.zeros(n)
        for term in terms:total+=get(term)
        assert np.array_equal(total,get('kcl:'+node.lower()))
    for label,pair in cfg['stress_voltage_pairs'].items():
        value=get(pair['positive_node'])-get(pair['negative_node']);stat=r['full_history_voltage_stress'][label]
        assert float(np.max(np.abs(value)))==stat['max_abs_v']
        assert int(np.sum(np.abs(value)>pair['limit_abs_v']))==stat['over_limit_native_points']
    energy_check={}
    for name,ports in cfg['source_power_ports'].items():
        value=float(np.trapezoid(-get(ports['voltage_node'])*get(ports['current']),a[:,0]))
        original=r['full_history_source_energy'][name]['net_delivered_j']
        assert math.isclose(value,original,rel_tol=1e-11,abs_tol=1e-25)
        energy_check[name]=dict(recomputed_J=value,native_reducer_J=original,residual_J=value-original)
    proof=dict(run_id=run,managed_recipe_sha256=rec['recipe_hash'],source_run_id=native_run,source_recipe_sha256=src['recipe_hash'],
        receipt_sha256=identity(folder/'collection_receipt.json')['sha256'],receipt_files=len(receipt['files']),receipt_bytes=receipt['total_bytes'],
        all_receipt_bytes_verified=True,decoded_bytes=size,decoded_sha256=h.hexdigest(),native_rows=n,
        all348_simultaneous_pair_maxima_and_counts_recomputed=True,all_six_KCL_columns_recomputed_exact=True,
        source_energy_recalculation=energy_check,native_logs_PASS_zero_errors=True,
        native_effective_settings=r['native_effective_settings'],native_warning_codes=r['native_warning_codes'],
        original_result_sha256=identity(files['derived/result.json'])['sha256'])
    return dict(cfg=cfg,result=r,a=a,idx=idx,get=get,proof=proof)


def over_intervals(t,v,limit):
    out=[];start=None
    for i in range(len(t)-1):
        x=abs(v[i])-limit;y=abs(v[i+1])-limit
        if i==0 and x>0:start=dict(time_s=float(t[0]),native_bracket_s=[float(t[0]),float(t[0])])
        if x<=0<y:start=dict(time_s=float(t[i]-x*(t[i+1]-t[i])/(y-x)),native_bracket_s=[float(t[i]),float(t[i+1])])
        if x>0>=y and start:
            stop=dict(time_s=float(t[i]-x*(t[i+1]-t[i])/(y-x)),native_bracket_s=[float(t[i]),float(t[i+1])])
            out.append(dict(start=start,stop=stop,duration_s=stop['time_s']-start['time_s']));start=None
    if start:out.append(dict(start=start,stop=dict(time_s=float(t[-1]),native_bracket_s=[float(t[-1]),float(t[-1])]),right_censored=True,duration_s=float(t[-1])-start['time_s']))
    return out


def summarize(case,data):
    cfg=data['cfg'];r=data['result'];a=data['a'];idx=data['idx'];get=data['get'];t=a[:,0]
    config=read(CANDIDATE/'extension_config.json');events={};focus={}
    for label,node in config['nodes'].items():
        rows=[(float(x),float(y)) for x,y in zip(t,get(node))]
        events[label]=extended_edges(rows,1,.99,config['input_basis'].get(label))
        if label in config['focus_direction']:
            selected=[e for e in events[label] if e['direction']==config['focus_direction'][label] and 5e-9<=e['time_s']<=5.06e-9]
            assert len(selected)==1;focus[label]=selected[0]
    vds=get('xdut.xu19.xff.mq_x')-get('xdut.xu19.xff.net176');stat=r['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS']
    peak=int(np.argmax(np.abs(vds)));assert float(t[peak])==stat['max_abs_time_s']
    intervals=over_intervals(t,vds,.99);focus_interval=[v for v in intervals if v['start']['time_s']<=t[peak]<=v['stop']['time_s']];assert len(focus_interval)==1
    front=np.flatnonzero((t>=5e-9)&(t<=5.06e-9));s=get('xdut.xu19.xff.net176');lo=int(front[np.argmin(s[front])])
    roles={'MM'+str(m)+'_'+role:'xdut.xu19.xff.mm'+str(m)+':'+str(j) for m in [64,65,66] for j,role in enumerate('DGSB',1)}
    peaks={}
    for name,node in roles.items():
        value=get(node);minimum=int(front[np.argmin(value[front])]);maximum=int(front[np.argmax(value[front])])
        peaks[name]=dict(min_A=float(value[minimum]),min_time_s=float(t[minimum]),max_A=float(value[maximum]),max_time_s=float(t[maximum]))
    phase_windows=[('phase'+str(p['index']),p['start_s'],p['stop_s'],'original_command_phase') for p in cfg['storage']['DFF_phases']]
    phase_windows += [('front',5e-9,5.06e-9,'absolute_subwindow'),('quiet',5.06e-9,5.95e-9,'absolute_subwindow'),('tail',5.95e-9,6e-9,'absolute_subwindow'),('next_clock',6e-9,6.05e-9,'absolute_subwindow')]
    charges=[]
    for name,start,stop,kind in phase_windows:
        charges.append(dict(name=name,start_s=start,stop_s=stop,kind=kind,start_bracket_s=frozen.boundary(t,start),stop_bracket_s=frozen.boundary(t,stop),
            terminal_charge_C={key:frozen.integrate(t,get(node),start,stop) for key,node in roles.items()},
            KCL_residual_charge_C={node:frozen.integrate(t,get('kcl:'+node.lower()),start,stop) for node in cfg['critical_kcl_nodes']}))
    snapshots={}
    for at in [5.06e-9,5.5e-9,5.95e-9,6e-9]:
        snapshots[str(at)]=dict(absolute_time_s=at,native_bracket_s=frozen.boundary(t,at),method='linear estimate at common absolute time; original brackets retained',
            nodes_V={node:float(np.interp(at,t,get('xdut.xu19.xff.'+node))) for node in ['net176','net184','mq_x','clkbb','mq']},
            currents_A={key:float(np.interp(at,t,get(node))) for key,node in roles.items()})
    failed=sorted(label for label,s in r['full_history_voltage_stress'].items() if s['over_limit_native_points'])
    total_energy=sum(v['net_delivered_j'] for v in r['full_history_source_energy'].values())
    resistor_energy=0. if case=='baseline' else float(np.trapezoid((get('xdut.u19_ck_drv')-get('xdut.u19_ck'))*get('xdut.rck:1'),t))
    holds=r['storage_observations']['contexts']['U19']['phases']
    out=dict(case=case,proof=data['proof'],focus_edges=focus,all_input_and_internal_edges=events,
        MM64_VDS=stat,MM64_focus_over_limit_interval=focus_interval[0],all_MM64_over_limit_intervals=intervals,
        peak_same_native_nodes_V={n:float(get('xdut.xu19.xff.'+n)[peak]) for n in ['mq_x','net176','net184','clkb','clkbb','mq']},
        net176_front_min_V=float(s[lo]),net176_front_min_time_s=float(t[lo]),front_current_extrema=peaks,
        snapshots_at_common_absolute_time=snapshots,phase_charges=charges,failed_pairs=failed,failed_pair_count=len(failed),
        full_history_source_energy=r['full_history_source_energy'],all_source_net_delivered_J=total_energy,
        diagnostic20ns_mean_source_delivery_W=total_energy/20e-9,RCK_absorbed_J=resistor_energy,
        maximum_six_node_KCL_residual_A=max(x['max_abs_a'] for x in r['node_kcl'].values()),
        stable_hold_pass=r['storage_observations']['stable_hold_observation_pass'],Q_edge_patterns_pass=r['storage_observations']['clean_expected_Q_edge_patterns'],
        stable_hold_phase_count=sum(p['stable_hold_observation_pass'] is True for p in holds),
        Q_events_total=sum(len(p['Q_events']) for p in holds),
        actual_functional_delays=[dict(phase=p['index'],delay_s=p['signed_actual_input_to_Q_delay_s'],delay_status=p['delay_status']) for p in holds if p['expected_Q_change']],
        native_warning_codes=r['native_warning_codes'],whole_ADC_qualified=None)
    if case=='rck20k':
        for key,e in focus.items():
            original=r['transition_diagnostic']['focus_edges'][key]['event']
            assert e==original
    return out


def plot(all_data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.20,'legend.frameon':False})
    fig,axes=plt.subplots(6,1,figsize=(10.7,12.0),sharex=True,layout='constrained')
    signals=[('CP (V)','xdut.u19_ck',1.),('clkb (V)','xdut.xu19.xff.clkb',1.),('clkbb (V)','xdut.xu19.xff.clkbb',1.),('mq (V)','xdut.xu19.xff.mq',1.),('net176 (mV)','xdut.xu19.xff.net176',1e3),('MM64 VDS (V)',None,1.)]
    for case,d in all_data.items():
        get=d['get'];t=d['a'][:,0];mask=(t>=4.998e-9)&(t<=5.07e-9)
        for ax,(label,node,scale) in zip(axes,signals):
            value=get(node) if node else get('xdut.xu19.xff.mq_x')-get('xdut.xu19.xff.net176')
            ax.plot(t[mask]*1e9,value[mask]*scale,color=COLORS[case],ls=STYLES[case],lw=1.75 if case!='rck2k' else 1.25,label=LABELS[case])
            ax.set_ylabel(label);ax.set_xlim(4.998,5.07)
    axes[0].legend(ncol=3,loc='upper right');axes[4].axhline(0,color='#777',lw=.9,ls=':')
    axes[5].axhline(.99,color='#555',lw=1.,ls=':');axes[5].text(5.000,.995,'0.99 V screen',fontsize=9,color='#555',va='bottom')
    axes[-1].set_xlabel('Absolute time (ns)')
    fig.suptitle('RCK comparison: original native times\nT28 native DFCNQD1 | FF, 0.99 V, -40 C | same driver and Q loads; ideal external commands',fontsize=12)
    fig.savefig(HERE/'timing_comparison.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12.6,7.7),layout='constrained')
    for case,d in all_data.items():
        t=d['a'][:,0];get=d['get'];hold=(t>=5e-9)&(t<=6.05e-9);front=(t>=4.998e-9)&(t<=5.07e-9)
        values=[get('xdut.xu19.xff.net176')*1e3,get('xdut.xu19.xff.mq_x')-get('xdut.xu19.xff.net176'),get('xdut.xu19.xff.mm64:2')*1e6,get('xdut.xu19.xff.mm65:2')*1e6]
        for i,(ax,v) in enumerate(zip(axes.flat,values)):
            mask=hold if i<2 else front
            ax.plot(t[mask]*1e9,v[mask],color=COLORS[case],ls=STYLES[case],lw=1.7 if case!='rck2k' else 1.2,label=LABELS[case]);ax.set_xlabel('Absolute time (ns)')
    for ax,title in zip(axes.flat,['net176 recovery (mV)','MM64 VDS (V)','MM64 gate total current (uA)','MM65 gate total current (uA)']):ax.set_title(title,fontsize=11)
    axes[0,0].axhline(0,color='#777',lw=1.,ls=':');axes[0,1].axhline(.99,color='#555',lw=1.,ls=':',label='0.99 V screen')
    axes[0,0].legend(ncol=3,loc='upper right',fontsize=9);axes[0,1].legend(loc='lower right',fontsize=9)
    fig.suptitle('Residual voltage and switching currents\nSame FF / 0.99 V / -40 C fixture | total terminal currents; positive into device',fontsize=12)
    fig.savefig(HERE/'recovery_currents.png',dpi=180);plt.close(fig)


def main():
    all_data={};summaries={}
    for case in ['baseline','rck2k','rck20k']:
        all_data[case]=load(case);summaries[case]=summarize(case,all_data[case])
    assert len({json.dumps(x['result']['native_effective_settings'],sort_keys=True) for x in all_data.values()})==1
    baseline=summaries['baseline'];contrast={}
    for case in ['rck2k','rck20k']:
        s=summaries[case];old=set(baseline['failed_pairs']);new=set(s['failed_pairs'])
        contrast[case]=dict(added_failed_pairs=sorted(new-old),removed_failed_pairs=sorted(old-new),
            MM64_peak_change_V=s['MM64_VDS']['max_abs_v']-baseline['MM64_VDS']['max_abs_v'],
            CP_raw30_70_ratio=s['focus_edges']['CP']['slew_30_70_s']/baseline['focus_edges']['CP']['slew_30_70_s'],
            CP_actual10_90_ratio=s['focus_edges']['CP']['slew_10_90_s']/baseline['focus_edges']['CP']['slew_10_90_s'],
            internal_actual10_90_ratios={n:s['focus_edges'][n]['slew_10_90_s']/baseline['focus_edges'][n]['slew_10_90_s'] for n in ['clkb','clkbb','mq']},
            all_source_net_work_change_J=s['all_source_net_delivered_J']-baseline['all_source_net_delivered_J'])
    dump('results.json',dict(cases=summaries,contrast_to_direct=contrast,
        waveform_time_shift_applied=False,CP_series_resistance_repair_direction='stop',
        decision='Strong external CP slew change did not reduce the dominant internal gate slew or MM64 stress; no larger resistance sweep.',
        gate_and_body_terminal_current_is_not_unique_intrinsic_decomposition=True,whole_ADC_qualified=None))
    with (HERE/'terminal_charges.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['case','window','kind','start_ns','stop_ns']+[k+'_fC' for k in summaries['baseline']['phase_charges'][0]['terminal_charge_C']]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for case,s in summaries.items():
            for p in s['phase_charges']:writer.writerow(dict(case=case,window=p['name'],kind=p['kind'],start_ns=p['start_s']*1e9,stop_ns=p['stop_s']*1e9,**{k+'_fC':v*1e15 for k,v in p['terminal_charge_C'].items()}))
    with (HERE/'stress_pairs.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['pair']+[case+suffix for case in all_data for suffix in ['_max_abs_V','_failed']]);writer.writeheader()
        for label in sorted(all_data['baseline']['cfg']['stress_voltage_pairs']):
            row=dict(pair=label)
            for case,d in all_data.items():
                stat=d['result']['full_history_voltage_stress'][label];row[case+'_max_abs_V']=stat['max_abs_v'];row[case+'_failed']=bool(stat['over_limit_native_points'])
            writer.writerow(row)
    plot(all_data)
    print(json.dumps({case:dict(CP30_70ps=s['focus_edges']['CP']['slew_30_70_s']*1e12,CP10_90ps=s['focus_edges']['CP']['slew_10_90_s']*1e12,
        clkb10_90ps=s['focus_edges']['clkb']['slew_10_90_s']*1e12,clkbb10_90ps=s['focus_edges']['clkbb']['slew_10_90_s']*1e12,mq10_90ps=s['focus_edges']['mq']['slew_10_90_s']*1e12,
        maxVDS=s['MM64_VDS']['max_abs_v'],minNet176mV=s['net176_front_min_V']*1e3,
        midNet176mV=s['snapshots_at_common_absolute_time']['5.5e-09']['nodes_V']['net176']*1e3,
        over_duration_ns=s['MM64_focus_over_limit_interval']['duration_s']*1e9,
        failed=s['failed_pair_count'],allSourceEnergy_fJ=s['all_source_net_delivered_J']*1e15,RCKenergy_fJ=s['RCK_absorbed_J']*1e15) for case,s in summaries.items()},sort_keys=True))


if __name__=='__main__':main()
