"""Original LIVE NMOS loading measurements with frozen native helpers. Py2.7/3."""
from __future__ import print_function
import argparse
import os
import re
import struct
import sys

import standard_cell_r0_analyze as series

standard,native=series.standard,series.native


def input_loading(output,cfg):
    exp=cfg['standard_cell_r0_mn2_experiment']
    names=native.read(os.path.join(output,'peak.columns.json'))['names']
    node=native.norm(exp['input_loading_node'])
    ports=dict((k,native.norm(v)) for k,v in exp['input_gate_current_ports'].items())
    terms=[native.norm(s) for s in exp['affected_input_KCL_terms']]
    index=dict((s,names.index(s)) for s in [node,'vdd!']+list(ports.values())+terms)
    parser=struct.Struct('<'+'d'*len(names))
    stats={};events=[];previous=None;first_charge=None;last=None;points=0;charge_points=0;KCL=0.
    q=dict((k,0.) for k in ports);work=dict((k,0.) for k in ports)
    start=exp['event_charge_start_s']
    with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
        while True:
            blob=handle.read(parser.size)
            if not blob:break
            if len(blob)!=parser.size:raise ValueError('Incomplete input-loading native row')
            row=parser.unpack(blob);last=row[0];points+=1
            current=dict((k,row[index[s]]) for k,s in ports.items())
            measured=dict(current);measured['total_gate']=sum(current.values());measured['input_voltage']=row[index[node]]
            for key,value in measured.items():
                item=stats.setdefault(key,dict(min=value,max=value,min_time_s=row[0],max_time_s=row[0]))
                if value<item['min']:item.update(min=value,min_time_s=row[0])
                if value>item['max']:item.update(max=value,max_time_s=row[0])
            KCL=max(KCL,abs(sum(row[index[s]] for s in terms)))
            if row[0]>=start:
                if first_charge is None:first_charge=row[0]
                charge_points+=1
                if previous is not None and previous[0]>=start:
                    dt=row[0]-previous[0]
                    for label,trace in ports.items():
                        i0,i1=previous[index[trace]],row[index[trace]]
                        q[label]+=.5*(i0+i1)*dt
                        work[label]+=.5*(previous[index[node]]*i0+row[index[node]]*i1)*dt
            if previous is not None:
                for fraction in [.1,.5,.9]:
                    a=previous[index[node]]-fraction*previous[index['vdd!']]
                    z=row[index[node]]-fraction*row[index['vdd!']]
                    direction=1 if a<0<=z else -1 if a>0>=z else 0
                    if direction:
                        at=previous[0]-a*(row[0]-previous[0])/(z-a)
                        events.append(dict(fraction=fraction,direction=direction,time_s=at))
            previous=row
    if not points or first_charge is None:raise ValueError('Input loading/event window missing')
    pending={1:None,-1:None};slew={1:[],-1:[]}
    events.sort(key=lambda e:e['time_s'])
    for e in events:
        f,d,at=e['fraction'],e['direction'],e['time_s']
        if (f,d)==(.1,1):pending[1]=at
        if (f,d)==(.1,-1):pending[1]=None
        if (f,d)==(.9,-1):pending[-1]=at
        if (f,d)==(.9,1):pending[-1]=None
        if (f,d) in [(.9,1),(.1,-1)] and pending[d] is not None:
            slew[d].append(at-pending[d]);pending[d]=None
    return dict(node=node,native_points=points,diagnostic_window_extrema=stats,
        native_KCL_max_a=KCL,threshold_events=events,rise_10_90_s=slew[1],fall_90_10_s=slew[-1],
        rising_halfrail_s=[e['time_s'] for e in events if e['fraction']==.5 and e['direction']==1],
        falling_halfrail_s=[e['time_s'] for e in events if e['fraction']==.5 and e['direction']==-1],
        event_exchange=dict(requested_start_s=start,first_native_s=first_charge,last_native_s=last,native_points=charge_points,
            into_gate_devices_c=q,total_into_gate_devices_c=sum(q.values()),
            into_gate_terminal_work_j=work,total_into_gate_terminal_work_j=sum(work.values())),
        current_policy='Actual returned native gate terminal currents, already containing model multiplicity; no second factor2. Signed terminal exchange/work, not pure Cgd, fixed input capacitance or dissipation. No waveform endpoint interpolation.',
        full_settling_pass=None)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();run,output=os.path.realpath(args.run_dir),os.path.realpath(args.output_dir)
    if output!=os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):raise ValueError('Expected fresh managed derived directory')
    library=standard.verify_library(os.path.join(run,'inputs','external_library.json'))
    state=native.read(os.path.join(run,'simulation.state.json'))
    if (state['status']!='complete' or state['exit_code']!=0 or not state.get('native',{}).get('native_analysis_pass') or not state.get('native',{}).get('zero_error_footer')):
        raise ValueError('Native simulation not complete')
    with open(os.path.join(run,'raw','logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):raise ValueError('Native PASS missing')
    paths=[os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Expected one native ASCII transient')
    cfg_path=os.path.join(run,'inputs','measurement.json');cfg=native.read(cfg_path)
    result=native.summarize(paths[0],cfg,output)
    result['measurement_sha256']=standard.file_identity(cfg_path)['sha256'];result['external_library_identity']=library
    result['diagnostic_timing']=standard.diagnostic_timing(output,cfg)
    result['series_resistor_metrics']=series.resistor_measurements(output,cfg)
    result['changed_driver_input_loading']=input_loading(output,cfg)
    binding=cfg['standard_cell_experiment']['library_mos']
    result['standard_cell_native_current_bindings']=dict((name,dict(requested=item['requested_numeric_terminal_currents'],
        actual=dict((p,result['trace_bindings'][native.norm(p)]) for p in item['requested_numeric_terminal_currents']),
        nested_inline_primitive_probe_not_used=True)) for name,item in binding.items())
    result['resistor_native_current_bindings']=dict((p,result['trace_bindings'][native.norm(p)]) for p in cfg['standard_cell_r0_experiment']['resistor_current_ports'])
    exp=cfg['standard_cell_r0_mn2_experiment']
    result['changed_MOS_native_terminal_bindings']=dict((p,result['trace_bindings'][native.norm(p)]) for p in exp['changed_MOS_terminal_currents'])
    ports=dict((label,result['full_history_source_energy'].pop(label)) for label in cfg['standard_cell_r0_experiment']['passive_port_energy_labels'])
    result['full_history_resistor_energy']=dict(port_net_delivered_work=ports,absorbed_j=-sum(v['net_delivered_j'] for v in ports.values()),
        policy='Native0..END passive terminal work; separate from five ideal sources and partial gate-terminal work.')
    if set(result['full_history_source_energy'])!={'VDD','BIAS10_N','BIAS10_MID','BIAS14_N','BIAS14_MID'}:raise ValueError('Five-source/passive energy classification differs')
    groups={};stress=result['full_history_voltage_stress']
    for name,item in cfg['standard_cell_experiment']['observed_mos'].items():
        g=groups.setdefault(item['group'],dict(MOS=0,pairs=0,failed_pairs=0,failed_instances=[]))
        g['MOS']+=1;g['pairs']+=len(item['six_pair_labels'])
        failed=sum(stress[label]['over_limit_native_points']>0 for label in item['six_pair_labels'].values());g['failed_pairs']+=failed
        if failed:g['failed_instances'].append(name)
    result['physical_terminal_screen_groups']=groups
    result['comparison_source']=dict(run_id=exp['base_run'],recipe_sha256=exp['base_recipe_sha256'])
    result['native_warning_codes']=state['native'].get('warning_codes');codes=result['native_warning_codes']
    result['CMI_warning_present']=any(s.startswith('CMI') for s in codes) if codes is not None else None
    result['native_effective_settings']=state['native'].get('effective_settings');result['analysis_peak_rss_bytes']=None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis RSS exceeds256 MiB')
    if sum(os.path.getsize(os.path.join(output,s)) for s in os.listdir(output))+1024*1024>=32*1024**2:raise ValueError('Derived output cap exceeded')
    native.write_new(os.path.join(output,'result.json'),result)
    print('CONTROL_STANDARD_CELL_R0_MN2_NATIVE_ANALYSIS_OK',result['native_points'],'no electrical acceptance inferred')


if __name__=='__main__':
    main()
