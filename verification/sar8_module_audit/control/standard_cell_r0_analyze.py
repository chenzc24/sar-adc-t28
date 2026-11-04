"""Native R0 two-side measurements with frozen source helpers. Python2.7/3."""
from __future__ import print_function
import argparse
import os
import re
import struct
import sys

import standard_cell_analyze as standard

native = standard.native


def resistor_measurements(output,cfg):
    exp = cfg['standard_cell_r0_experiment']
    names = native.read(os.path.join(output,'peak.columns.json'))['names']
    live = native.norm(exp['actual_LIVE_node'])
    a1 = native.norm(exp['actual_A1_node'])
    currents = [native.norm(s) for s in exp['resistor_current_ports']]
    nodes = [live,a1]
    index = dict((s,names.index(s)) for s in nodes+currents+['vdd!'])
    record = struct.Struct('<'+'d'*len(names))
    previous = None
    events = dict((s,[]) for s in nodes)
    last_values = {}
    apparent = []
    max_port_sum = 0.
    first,last = None,None
    point_count = 0
    with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
        while True:
            blob = handle.read(record.size)
            if not blob: break
            if len(blob)!=record.size: raise ValueError('Incomplete R0 diagnostic native row')
            row = record.unpack(blob)
            if first is None: first=row[0]
            last=row[0];point_count+=1
            plus,minus = [row[index[s]] for s in currents]
            max_port_sum = max(max_port_sum,abs(plus+minus))
            drop = row[index[live]]-row[index[a1]]
            if abs(plus)>exp['apparent_R_current_floor_a']:
                apparent.append(drop/plus)
            for s in nodes:
                last_values[s]=row[index[s]]
                if previous is None: continue
                for f in [.1,.5,.9]:
                    before=previous[index[s]]-f*previous[index['vdd!']]
                    after=row[index[s]]-f*row[index['vdd!']]
                    direction=1 if before<0<=after else -1 if before>0>=after else 0
                    if direction:
                        at=previous[0]-before*(row[0]-previous[0])/(after-before)
                        events[s].append(dict(fraction=f,direction=direction,time_s=at))
            previous=row
    if previous is None: raise ValueError('No native R0 diagnostic rows')
    timing = {}
    for s in nodes:
        sequence=sorted(events[s],key=lambda e:e['time_s'])
        rises=[e['time_s'] for e in sequence if e['fraction']==.5 and e['direction']==1]
        falls=[e['time_s'] for e in sequence if e['fraction']==.5 and e['direction']==-1]
        pending={1:None,-1:None};slew={1:[],-1:[]}
        for e in sequence:
            f,d,at=e['fraction'],e['direction'],e['time_s']
            if (f,d)==(.1,1):pending[1]=at
            if (f,d)==(.1,-1):pending[1]=None
            if (f,d)==(.9,-1):pending[-1]=at
            if (f,d)==(.9,1):pending[-1]=None
            if (f,d) in [(.9,1),(.1,-1)] and pending[d] is not None:
                slew[d].append(at-pending[d]);pending[d]=None
        timing[s]=dict(threshold_events=sequence,rising_halfrail_s=rises,falling_halfrail_s=falls,
            rise_10_90_s=slew[1],fall_90_10_s=slew[-1],end_voltage_v=last_values[s],
            no_halfrail_edge_observed=not(rises or falls),full_settling_pass=None)
    lhs,rhs=timing[live]['rising_halfrail_s'],timing[a1]['rising_halfrail_s']
    delay=rhs[0]-lhs[0] if len(lhs)==1 and len(rhs)==1 else None
    return dict(observation_start_s=first,observation_stop_s=last,native_points=point_count,
        nodes=timing,A1_first_halfrail_relative_LIVE_s=delay,
        max_two_port_current_sum_a=max_port_sum,
        apparent_V_over_I_ohm=dict(min=min(apparent),max=max(apparent),native_points=len(apparent)) if apparent else None,
        ratio_current_floor_a=exp['apparent_R_current_floor_a'],
        policy='V/I is simultaneous native diagnostic-window ratio when current exceeds measurement floor; no division at zero, inferred fixed R or missing-event zero. Linear threshold interpolation locates events only; no resampled waveform.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    parser.add_argument('--output-dir',required=True)
    args=parser.parse_args()
    run,output=os.path.realpath(args.run_dir),os.path.realpath(args.output_dir)
    if output!=os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):
        raise ValueError('Expected fresh managed derived directory')
    library=standard.verify_library(os.path.join(run,'inputs','external_library.json'))
    state=native.read(os.path.join(run,'simulation.state.json'))
    if (state['status']!='complete' or state['exit_code']!=0
            or not state.get('native',{}).get('native_analysis_pass')
            or not state.get('native',{}).get('zero_error_footer')):
        raise ValueError('Native simulation not complete')
    with open(os.path.join(run,'raw','logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):raise ValueError('Native PASS missing')
    paths=[os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Expected one native ASCII transient')
    cfg_path=os.path.join(run,'inputs','measurement.json');cfg=native.read(cfg_path)
    result=native.summarize(paths[0],cfg,output)
    result['measurement_sha256']=standard.file_identity(cfg_path)['sha256']
    result['external_library_identity']=library
    result['diagnostic_timing']=standard.diagnostic_timing(output,cfg)
    result['series_resistor_metrics']=resistor_measurements(output,cfg)
    binding=cfg['standard_cell_experiment']['library_mos']
    result['standard_cell_native_current_bindings']=dict((name,dict(
        requested=item['requested_numeric_terminal_currents'],
        actual=dict((p,result['trace_bindings'][native.norm(p)]) for p in item['requested_numeric_terminal_currents']),
        nested_inline_primitive_probe_not_used=True)) for name,item in binding.items())
    result['resistor_native_current_bindings']=dict((p,result['trace_bindings'][native.norm(p)])
        for p in cfg['standard_cell_r0_experiment']['resistor_current_ports'])
    ports=dict((label,result['full_history_source_energy'].pop(label))
        for label in cfg['standard_cell_r0_experiment']['passive_port_energy_labels'])
    result['full_history_resistor_energy']=dict(port_net_delivered_work=ports,
        absorbed_j=-sum(v['net_delivered_j'] for v in ports.values()),
        policy='Absorbed passive port work=sum(Vterminal*Iterminal) on same0..END native rows. Separate from the five ideal source contributions and whole-cycle ADC power.')
    if set(result['full_history_source_energy'])!={'VDD','BIAS10_N','BIAS10_MID','BIAS14_N','BIAS14_MID'}:
        raise ValueError('Five-source/passive energy accounting differs')
    groups={}
    stress=result['full_history_voltage_stress']
    for name,item in cfg['standard_cell_experiment']['observed_mos'].items():
        g=groups.setdefault(item['group'],dict(MOS=0,pairs=0,failed_pairs=0,failed_instances=[]))
        g['MOS']+=1;g['pairs']+=len(item['six_pair_labels'])
        failed=sum(stress[label]['over_limit_native_points']>0 for label in item['six_pair_labels'].values())
        g['failed_pairs']+=failed
        if failed:g['failed_instances'].append(name)
    result['physical_terminal_screen_groups']=groups
    result['comparison_source']=dict(run_id=cfg['standard_cell_r0_experiment']['base_run'],
        recipe_sha256=cfg['standard_cell_r0_experiment']['base_recipe_sha256'])
    result['native_warning_codes']=state['native'].get('warning_codes')
    codes=result['native_warning_codes']
    result['CMI_warning_present']=any(s.startswith('CMI') for s in codes) if codes is not None else None
    result['native_effective_settings']=state['native'].get('effective_settings')
    result['analysis_peak_rss_bytes']=None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis RSS exceeds256 MiB')
    if sum(os.path.getsize(os.path.join(output,s)) for s in os.listdir(output))+1024*1024>=32*1024**2:
        raise ValueError('Derived output cap exceeded')
    native.write_new(os.path.join(output,'result.json'),result)
    print('CONTROL_STANDARD_CELL_R0_NATIVE_ANALYSIS_OK',result['native_points'],'no circuit acceptance inferred')


if __name__=='__main__':
    main()
