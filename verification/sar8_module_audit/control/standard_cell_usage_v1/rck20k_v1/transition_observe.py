"""Bounded native extension; frozen10/90 remains, add30/70 and explicit/.50."""
from __future__ import print_function
import gzip
import math
import os
import struct
import full_gate_analyze as native
import usage_gzip as usage


def extended_edges(rows,index,rail,basis=None):
    events=usage.pin_edges(rows,index,rail)
    extra={}
    for fraction in [.3,.7]:
        hits=[]
        for a,b in zip(rows,rows[1:]):
            x=a[index]-fraction*rail;y=b[index]-fraction*rail
            direction=1 if x<0<=y else -1 if x>0>=y else 0
            if direction:
                hits.append(dict(time_s=a[0]-x*(b[0]-a[0])/(y-x),direction=direction,native_bracket_s=[a[0],b[0]]))
                if len(hits)>1024:raise ValueError('Threshold event bound exceeded')
        extra[fraction]=hits
    for event in events:
        for fraction,hits in extra.items():
            found=[h for h in hits if h['direction']==event['direction'] and abs(h['time_s']-event['time_s'])<=.25e-9]
            event['crossings'][str(fraction)]=found[0] if len(found)==1 else None
        lower=event['crossings']['0.3'];upper=event['crossings']['0.7']
        interval=((upper['time_s']-lower['time_s'])*event['direction']) if lower and upper else None
        event['slew_30_70_s']=interval if interval is not None and interval>=0 else None
        event['library_coordinate_s']=None
        event['library_coordinate_status']='internal_node_has_no_input_table_mapping'
        if basis is not None:
            edge='rise' if event['direction']==1 else 'fall';entry=basis[edge]
            factor=entry['slew_derate_from_library']
            if entry['threshold_pct']!=[30.,70.] or factor!=.5:raise ValueError('Frozen explicit threshold/derate basis differs')
            event['library_coordinate_status']='missing_or_ambiguous_threshold_crossing'
            if event['slew_30_70_s'] is not None:
                coordinate=event['slew_30_70_s']/factor;bounds=entry['transition_axis_s']
                event.update(library_coordinate_s=coordinate,library_coordinate_status='explicit_sourced_derate_coordinate',
                    coordinate_within_declared_axis=bounds[0]<=coordinate<=bounds[1])
    return events


def observe(output,cfg,config,result):
    names=native.read(os.path.join(output,'peak.columns.json'))['names'];indices=dict((n,i) for i,n in enumerate(names))
    nodes=config['nodes'];labels=sorted(nodes);columns=[0]+[indices[native.norm(nodes[n])] for n in labels]
    pack=struct.Struct('<'+'d'*len(names));rows=[];previous=None
    with gzip.open(os.path.join(output,'peak.native.bin.gz'),'rb') as handle:
        while True:
            blob=handle.read(pack.size)
            if not blob:break
            if len(blob)!=pack.size:raise ValueError('Incomplete native extension row')
            row=pack.unpack(blob)
            if any(math.isnan(v) or math.isinf(v) for v in row):raise ValueError('Nonfinite native extension row')
            if previous is not None and row[0]<=previous:raise ValueError('Nonincreasing native extension time')
            rows.append(tuple(row[i] for i in columns));previous=row[0]
            if len(rows)>200000:raise ValueError('Native projected-row bound exceeded')
    if len(rows)!=result['diagnostic_points'] or len(rows)<2 or rows[0][0]!=0 or abs(rows[-1][0]-cfg['source_history_stop_s'])>1e-15:
        raise ValueError('Extension full native history/END differs')
    events={};ranges={};focus={}
    for index,label in enumerate(labels,1):
        events[label]=extended_edges(rows,index,cfg['usage']['vdd_v'],config['input_basis'].get(label))
        ranges[label]={}
        for edge,direction in [('rise',1),('fall',-1)]:
            selected=[e for e in events[label] if e['direction']==direction]
            ranges[label][edge]={}
            for key in ['slew_10_90_s','slew_30_70_s','library_coordinate_s']:
                vals=[e[key] for e in selected if e.get(key) is not None]
                ranges[label][edge][key]=[min(vals),max(vals)] if vals else None
            ranges[label][edge]['missing_or_ambiguous_30_70_events']=sum(e['slew_30_70_s'] is None for e in selected)
        if label in config['focus_direction']:
            selected=[e for e in events[label] if e['direction']==config['focus_direction'][label] and config['focus_window_s'][0]<=e['time_s']<=config['focus_window_s'][1]]
            focus[label]=dict(status='one_native_focus_event' if len(selected)==1 else 'missing_or_ambiguous_focus_event',
                event=selected[0] if len(selected)==1 else None,count=len(selected))
    stat=result['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS'];contrasts={}
    for case,ref in config['reference_cases'].items():
        timing={}
        for label,node in config['nodes'].items():
            if label not in focus:continue
            old=ref['falling_event_edges'].get(native.norm(node));new=focus[label]['event']
            timing[label]=dict(actual_event_shift_s=new['time_s']-old['time_s'] if new and old else None,
                actual10_90_change_s=new['slew_10_90_s']-old['slew_10_90_s'] if new and old and new['slew_10_90_s'] is not None and old['slew_10_90_s'] is not None else None,
                waveform_shift_applied=False)
        contrasts[case]=dict(reference_proof=ref['proof'],MM64_peak_delta_v=stat['max_abs_v']-ref['MM64_peak']['max_abs_v'],
            MM64_peak_time_delta_s=stat['max_abs_time_s']-ref['MM64_peak']['max_abs_time_s'],
            strict_failed_pairs_delta=sum(bool(s['over_limit_native_points']) for s in result['full_history_voltage_stress'].values())-ref['strict_failed_pairs'],
            focus_edges=timing,reference_input_ranges=ref['input_ranges'],
            no_automatic_repair_or_reliability_verdict=True)
    cp=focus.get('CP',{}).get('event');target=config['diagnostic_CP_raw30_70_target_s']
    return dict(actual_edges=events,actual_ranges=ranges,focus_edges=focus,reference_contrasts=contrasts,
        native_projected_rows=len(rows),sourced_normalization=config['normalization_source'],
        diagnostic_CP_raw30_70_at_least_target=(cp['slew_30_70_s']>=target if cp and cp['slew_30_70_s'] is not None else None),
        diagnostic_target_s=target,target_is_not_circuit_acceptance=True,
        actual_delays_preserved=True,table_axis_not_a_reliability_limit=True,
        actual_effective_Q_load_F=None,full_conditional_timing_qualified=None,formal_PDK_pairing_proven=False,
        whole_ADC_qualified=None)
