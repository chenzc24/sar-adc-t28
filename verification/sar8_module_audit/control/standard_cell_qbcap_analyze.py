"""Native QB-MID charge/recovery observer; frozen source reducers. Python2.7/3."""
from __future__ import print_function
import argparse
import os
import re
import struct
import sys

import standard_cell_resetnand_analyze as source

rb,live,series,standard,native = source.rb,source.live,source.series,source.standard,source.native


def storage_observations(output,cfg,reset):
    exp = cfg['standard_cell_qbcap_experiment']
    names = native.read(os.path.join(output,'peak.columns.json'))['names']
    qb,mid = exp['QB_node'],exp['MID_node']
    catalog = cfg['terminal_current_catalog'];mos = cfg['standard_cell_experiment']['observed_mos']
    required = [qb,mid,'VDD!']+cfg['kcl_terms'][qb]+cfg['kcl_terms'][mid]+list(exp['observed_charge_ports'].values())
    for path in exp['observed_MOS']:
        required += [node for node in mos[path]['nodes'] if node!='0']+[path+':'+str(port) for port in range(1,5)]
    for item in cfg['source_power_ports'].values():
        required += [item['current']]+([item['voltage_node']] if item['voltage_node']!='0' else [])
    index = dict((native.norm(s),names.index(native.norm(s))) for s in required)
    parser = struct.Struct('<'+'d'*len(names))
    def rows():
        with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
            while True:
                blob = handle.read(parser.size)
                if not blob:
                    break
                if len(blob)!=parser.size:
                    raise ValueError('Incomplete native storage row')
                yield parser.unpack(blob)
    def value(row,node):
        return 0. if node=='0' else row[index[native.norm(node)]]
    def phase(row):
        devices = {}
        for path in exp['observed_MOS']:
            d,g,s,b = [value(row,n) for n in mos[path]['nodes']]
            devices[path.rsplit('.',1)[1]] = dict(D_v=d,G_v=g,S_v=s,B_v=b,VGS_v=g-s,VDS_v=d-s,VBS_v=b-s,
                native_total_terminal_currents_a=dict((role,value(row,path+':'+str(port))) for role,port in
                                                     [('D',1),('G',2),('S',3),('B',4)]),
                model_region_vth_and_channel_current_saved=False)
        power=dict((label,-value(row,item['voltage_node'])*value(row,item['current']))
                   for label,item in cfg['source_power_ports'].items())
        boundary=set(cfg['standard_cell_live_experiment']['boundary_source_power_labels'])
        passive=set(cfg['standard_cell_r0_experiment']['passive_port_energy_labels'])
        return dict(time_s=row[0],QB_v=value(row,qb),MID_v=value(row,mid),devices=devices,
            MID_cap_total_port_current_a=value(row,exp['observed_charge_ports']['CMID:1']),
            KCL_sum_a=dict((node,sum(value(row,p) for p in cfg['kcl_terms'][node])) for node in [qb,mid]),
            original_source_port_delivered_power_w=dict((k,v) for k,v in power.items() if k not in boundary|passive),
            boundary_source_port_delivered_power_w=dict((k,v) for k,v in power.items() if k in boundary),
            passive_R0_port_delivered_power_w=dict((k,v) for k,v in power.items() if k in passive))
    minimum = None;last_outside = None;first = None;last = None;count = 0
    for row in rows():
        count+=1;last=row[0]
        if first is None:
            first=row[0]
        q=value(row,qb)
        if minimum is None or q<minimum[1]:
            minimum=(row[0],q)
        if abs(q-exp['recovery_reference_v'])>exp['recovery_band_v']:
            last_outside=row[0]
    if count<2:
        raise ValueError('Missing native QB storage window')
    recovery = None
    for row in rows():
        if row[0]>=minimum[0] and (last_outside is None or row[0]>last_outside):
            recovery=row[0];break
    events = reset['nodes']['RB']['threshold_events']
    t10=next((e['time_s'] for e in events if e['fraction']==.1 and e['direction']==1),None)
    t90=next((e['time_s'] for e in events if e['fraction']==.9 and e['direction']==1),None)
    requested = dict(before_RB_edge=t10-exp['phase_before_RB10_s'] if t10 is not None else None,
        RB_90_percent=t90,QB_minimum=minimum[0],recovery_30ps=minimum[0]+exp['phase_after_minimum_s'],
        within_1mV_until_stop=recovery)
    phases = dict((k,None) for k in requested)
    integral = dict((label,dict(signed_into_device_c=0.,absolute_terminal_exchange_c=0.,into_device_terminal_work_j=0.))
                    for label in exp['observed_charge_ports'])
    integrable = t90 is not None and recovery is not None and recovery>=t90
    charge_first = None;charge_last=None;charge_points=0;previous=None
    for row in rows():
        for label,at in requested.items():
            if at is None:
                continue
            if label=='before_RB_edge':
                if row[0]<=at:
                    phases[label]=phase(row)
            elif phases[label] is None and row[0]>=at:
                phases[label]=phase(row)
        if integrable and t90<=row[0]<=recovery:
            if charge_first is None:
                charge_first=row[0]
            charge_last=row[0];charge_points+=1
            if previous is not None and previous[0]>=t90:
                dt=row[0]-previous[0]
                for label,port in exp['observed_charge_ports'].items():
                    node=catalog[port]['node'];a,z=value(previous,port),value(row,port)
                    item=integral[label]
                    item['signed_into_device_c']+=.5*(a+z)*dt
                    item['absolute_terminal_exchange_c']+=.5*(abs(a)+abs(z))*dt
                    item['into_device_terminal_work_j']+=.5*(value(previous,node)*a+value(row,node)*z)*dt
        previous=row
    exchange = (dict(first_native_s=charge_first,last_native_s=charge_last,native_points=charge_points,ports=integral)
                if integrable and charge_points>=2 else None)
    return dict(actual_native_capacitor_multi=exp['actual_capacitor_multi'],native_points=count,
        diagnostic_first_native_s=first,diagnostic_last_native_s=last,RB_10_s=t10,RB_90_s=t90,phases=phases,
        QB_minimum_to_within_1mV_s=recovery-minimum[0] if recovery is not None else None,
        post_RB90_exchange=exchange,current_multiplicity_rescaling_applied=False,
        evidence_scope='Actual native rows; recovery means stays within band until observed stop, not circuit acceptance. Missing phases/recovery are unavailable. Total terminal currents/work only; no region/Vth/channel/Cgd inference. No interpolated charge endpoints or multiplicity scaling.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();run,output=os.path.realpath(args.run_dir),os.path.realpath(args.output_dir)
    if output!=os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):
        raise ValueError('Expected fresh managed derived directory')
    library_identity=standard.verify_library(os.path.join(run,'inputs','external_library.json'))
    state=native.read(os.path.join(run,'simulation.state.json'))
    if (state['status']!='complete' or state['exit_code']!=0 or not state.get('native',{}).get('native_analysis_pass')
            or not state.get('native',{}).get('zero_error_footer')):
        raise ValueError('Native simulation incomplete')
    with open(os.path.join(run,'raw','logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):
            raise ValueError('Native PASS missing')
    paths=[os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:
        raise ValueError('Expected one native ASCII transient')
    cfg_path=os.path.join(run,'inputs','measurement.json');cfg=native.read(cfg_path)
    result=native.summarize(paths[0],cfg,output)
    result['measurement_sha256']=standard.file_identity(cfg_path)['sha256']
    result['external_library_identity']=library_identity
    result['diagnostic_timing']=standard.diagnostic_timing(output,cfg)
    result['series_resistor_metrics']=series.resistor_measurements(output,cfg)
    result['LIVE_stage_input_loading']=live.load_observations(output,cfg)
    result['reset_stage_observations']=rb.reset_observations(output,cfg)
    result['CLOCK_RESET_NAND_input_loading']=source.nand_input_loading(output,cfg)
    result['QB_storage_observations']=storage_observations(output,cfg,result['reset_stage_observations'])
    result['reset_receiver_initial_native_voltages_v']=dict(
        (label,result['initial_values'][native.norm(item['node'])])
        for label,item in cfg['standard_cell_rb_experiment']['load_observers'].items())
    library=cfg['standard_cell_experiment']['library_mos']
    if len(library)!=18:
        raise ValueError('Expected eighteen actual native library MOS')
    result['standard_cell_native_current_bindings']=dict((name,dict(
        requested=item['requested_numeric_terminal_currents'],
        actual=dict((p,result['trace_bindings'][native.norm(p)]) for p in item['requested_numeric_terminal_currents']),
        nested_primitive_not_assumed=True)) for name,item in library.items())
    result['resistor_native_current_bindings']=dict((p,result['trace_bindings'][native.norm(p)])
        for p in cfg['standard_cell_r0_experiment']['resistor_current_ports'])
    live.separate_energy(result,cfg)
    groups={};stress=result['full_history_voltage_stress']
    for name,item in cfg['standard_cell_experiment']['observed_mos'].items():
        g=groups.setdefault(item['group'],dict(MOS=0,pairs=0,failed_pairs=0,failed_instances=[]))
        g['MOS']+=1;g['pairs']+=len(item['six_pair_labels'])
        failed=sum(stress[s]['over_limit_native_points']>0 for s in item['six_pair_labels'].values())
        g['failed_pairs']+=failed
        if failed:
            g['failed_instances'].append(name)
    result['physical_terminal_screen_groups']=groups
    exp=cfg['standard_cell_qbcap_experiment']
    result['comparison_source']=dict(run_id=exp['base_run'],recipe_sha256=exp['base_recipe_sha256'])
    codes=state['native'].get('warning_codes');result['native_warning_codes']=codes
    result['CMI_warning_present']=any(s.startswith('CMI') for s in codes) if codes is not None else None
    result['native_effective_settings']=state['native'].get('effective_settings');result['analysis_peak_rss_bytes']=None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:
            raise ValueError('Analysis RSS exceeds256 MiB')
    if sum(os.path.getsize(os.path.join(output,s)) for s in os.listdir(output))+1024*1024>=32*1024**2:
        raise ValueError('Derived output cap exceeded')
    native.write_new(os.path.join(output,'result.json'),result)
    print('CONTROL_QB_CAP_NATIVE_ANALYSIS_OK',result['native_points'],'no circuit acceptance')


if __name__=='__main__':
    main()
