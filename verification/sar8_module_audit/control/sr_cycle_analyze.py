"""Streamed full SR cycle observations; Python2.7/3, no simulator launch."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import struct
import sys

import full_gate_analyze as native
import standard_cell_analyze as standard

P='XDUT.XCTRL.XTIM.'


def project_native_wave(output,cfg):
    """Project columns only AFTER all full-history/phase observations finish."""
    header_path=os.path.join(output,'peak.columns.json');path=os.path.join(output,'peak.native.bin')
    header=native.read(header_path);old=header['names']
    kept=['time']+[native.norm(n) for n in cfg['voltage_saves']]
    kept += [native.norm(n) for n in cfg['cycle']['final_wave_current_columns']]
    kept += ['kcl:'+native.norm(n) for n in cfg['cycle']['final_wave_KCL_nodes']]
    if len(kept)!=len(set(kept)):raise ValueError('Duplicate final wave column')
    indices=[old.index(n) for n in kept];reader=struct.Struct('<'+'d'*len(old));writer=struct.Struct('<'+'d'*len(kept))
    temp=path+'.projecting';header_temp=header_path+'.projecting'
    if os.path.exists(temp) or os.path.exists(header_temp):raise ValueError('Preserve existing incomplete projection')
    count=0;time_hash=hashlib.sha256();first=None;last=None
    with open(path,'rb') as source,open(temp,'wb') as target:
        while True:
            blob=source.read(reader.size)
            if not blob:break
            if len(blob)!=reader.size:raise ValueError('Incomplete analysis wave row')
            row=reader.unpack(blob);target.write(writer.pack(*[row[j] for j in indices]));count+=1
            time_hash.update(struct.pack('<d',row[0]));last=row[0]
            if first is None:first=row[0]
    if not count:raise ValueError('Empty native wave projection')
    new=dict(names=kept,units=[header['units'][j] for j in indices],
        native_rows=count,all_native_timestamps_preserved=True,all_voltage_columns_preserved=True,
        time_sha256=time_hash.hexdigest(),first_native_s=first,last_native_s=last,
        KCL_fields='Six core fields projected from the full65-node native reduction; all65-node statistics remain in result.',
        export_policy=cfg['cycle']['export_policy'])
    with open(header_temp,'w') as handle:json.dump(new,handle,sort_keys=True,indent=2);handle.write('\n')
    replace=getattr(os,'replace',os.rename)
    replace(temp,path);replace(header_temp,header_path)
    return dict(analysis_columns=len(old),exported_columns=len(kept),native_rows=count,
        all_native_timestamps_preserved=True,all66_voltage_traces_preserved=True,
        analysis_bytes=count*reader.size,exported_bytes=count*writer.size,
        analysis_current_columns=len(cfg['diagnostic_current_columns']),exported_current_columns=len(cfg['cycle']['final_wave_current_columns']),
        time_sha256=time_hash.hexdigest(),raw_PSF_modified=False)


def collection_budget(run,output,cfg,pending_result_bytes=0):
    """Mirror managed artifact membership, including logs/states outside derived."""
    known=['simulation.state.json','analysis.state.json','simulation.admission.json','analysis.admission.json',
           'spectre.out','raw/logStatus','source_provenance.json']
    paths=[os.path.join(run,n) for n in known]
    for parent,dirs,files in os.walk(output,followlinks=False):
        dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(parent,d))]
        paths += [os.path.join(parent,f) for f in files]
    sizes=dict((os.path.relpath(p,run),os.path.getsize(p)) for p in paths if os.path.isfile(p) and not os.path.islink(p))
    size=sum(sizes.values())+pending_result_bytes
    reserve=cfg['cycle']['final_analysis_state_reserve_bytes'];projected=size+reserve
    limit=cfg['cycle']['output_budget_bytes']
    if projected>limit:raise ValueError('Final SR collection exceeds30MiB including logs/states and final-state reserve')
    return dict(existing_members=sizes,existing_plus_pending_result_bytes=size,final_state_growth_reserve_bytes=reserve,
                projected_collection_bytes=projected,collection_limit_bytes=limit,user_limit_bytes=cfg['cycle']['collection_user_limit_bytes'])


def inspect_cycle(output,cfg):
    names=native.read(os.path.join(output,'peak.columns.json'))['names']
    required=cfg['diagnostic_voltage_columns']+cfg['diagnostic_current_columns']
    required+=['kcl:'+n for n in cfg['critical_kcl_nodes']]
    index=dict((native.norm(n),names.index(native.norm(n))) for n in required)
    def value(row,n):return 0. if n=='0' else row[index[native.norm(n)]]
    cyc=cfg['cycle'];phases=cyc['phases'];parser=struct.Struct('<'+'d'*len(names))
    observed=[];saved={};events={}
    signals=[P+'CLOCK_RESET',P+'CLOCK_SET',P+'CLOCK_Q',P+'XCLOCK.QB',P+'XCLOCK.RB','XDUT.CMP_CLK']
    signals += [P+'CYCLE_'+c for c in ['RESET_A','RESET_B','SET_A','SET_B']]
    for ph in phases:
        observed.append(dict(name=ph['name'],native_points=0,first_native_s=None,last_native_s=None,
            hold_points=0,hold_input_mismatches=0,hold_Q_mismatches=0,hold_QB_mismatches=0,
            voltages={},current_extrema={},physical_pairs={},KCL_max_a={},
            source_port_work_j=dict((k,0.) for k in cfg['source_power_ports']),MID_charge_c=0.,
            gate_loading=dict((k,dict(min_a=None,max_a=None,signed_into_gates_c=0.,terminal_work_j=0.))
                              for k in cyc['input_gate_ports'])))
    previous=None;previous_phase=None
    with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
        while True:
            blob=handle.read(parser.size)
            if not blob:break
            if len(blob)!=parser.size:raise ValueError('Incomplete SR native table row')
            row=parser.unpack(blob);at=row[0];i=min(len(phases)-1,int(at/cyc['period_s']));ph=phases[i];out=observed[i]
            if i<0:raise ValueError('Negative native time')
            out['native_points']+=1;out['last_native_s']=at
            if out['first_native_s'] is None:out['first_native_s']=at
            rail=value(row,'VDD!')
            for n in cfg['voltage_saves']:
                z=value(row,n);v=out['voltages'].setdefault(n,dict(min_v=z,max_v=z,min_time_s=at,max_time_s=at))
                if z<v['min_v']:v.update(min_v=z,min_time_s=at)
                if z>v['max_v']:v.update(max_v=z,max_time_s=at)
            for n in cfg['diagnostic_current_columns']:
                z=value(row,n);v=out['current_extrema'].setdefault(n,dict(min_a=z,max_a=z))
                v['min_a']=min(v['min_a'],z);v['max_a']=max(v['max_a'],z)
            for label,pair in cfg['stress_voltage_pairs'].items():
                z=value(row,pair['positive_node'])-value(row,pair['negative_node'])
                v=out['physical_pairs'].setdefault(label,dict(max_abs_v=abs(z),max_abs_time_s=at,over_limit_native_points=0))
                if abs(z)>v['max_abs_v']:v.update(max_abs_v=abs(z),max_abs_time_s=at)
                v['over_limit_native_points']+=int(abs(z)>pair['limit_abs_v'])
            for n in cfg['critical_kcl_nodes']:
                out['KCL_max_a'][n]=max(out['KCL_max_a'].get(n,0.),abs(value(row,'kcl:'+n)))
            qb=value(row,P+'XCLOCK.QB')
            for role,old in [('QB_min',out['voltages'][P+'XCLOCK.QB']['min_v']),('QB_max',out['voltages'][P+'XCLOCK.QB']['max_v'])]:
                key=(i,role)
                if key not in saved or (role=='QB_min' and qb<value(saved[key],P+'XCLOCK.QB')) or (role=='QB_max' and qb>value(saved[key],P+'XCLOCK.QB')):
                    saved[key]=row
            def logic_matches(node,bit):
                z=value(row,node);return z>=cyc['high_fraction']*rail if bit else z<=cyc['low_fraction']*rail
            if ph['hold_start_s']<=at<=ph['hold_stop_s']:
                out['hold_points']+=1
                out['hold_input_mismatches']+=int(not(logic_matches(P+'CLOCK_RESET',ph['R']) and logic_matches(P+'CLOCK_SET',ph['S'])))
                out['hold_Q_mismatches']+=int(not logic_matches(P+'CLOCK_Q',ph['Q']))
                out['hold_QB_mismatches']+=int(not logic_matches(P+'XCLOCK.QB',ph['QB']))
            for n,ports in cyc['input_gate_ports'].items():
                amps=sum(value(row,p) for p in ports);v=out['gate_loading'][n]
                v['min_a']=amps if v['min_a'] is None else min(v['min_a'],amps)
                v['max_a']=amps if v['max_a'] is None else max(v['max_a'],amps)
                if previous is not None and previous_phase==i:
                    dt=at-previous[0];oldamps=sum(value(previous,p) for p in ports)
                    v['signed_into_gates_c']+=.5*(oldamps+amps)*dt
                    v['terminal_work_j']+=.5*(value(previous,n)*oldamps+value(row,n)*amps)*dt
            if previous is not None:
                for n in signals:
                    a=value(previous,n)-.5*value(previous,'VDD!');z=value(row,n)-.5*rail
                    direction=1 if a<0<=z else -1 if a>0>=z else 0
                    if direction:events.setdefault(n,[]).append(dict(time_s=previous[0]-a*(at-previous[0])/(z-a),direction=direction))
                if previous_phase==i:
                    dt=at-previous[0]
                    out['MID_charge_c']+=.5*(value(previous,cyc['MID_current'])+value(row,cyc['MID_current']))*dt
                    for label,power in cfg['source_power_ports'].items():
                        a=-value(previous,power['voltage_node'])*value(previous,power['current'])
                        z=-value(row,power['voltage_node'])*value(row,power['current'])
                        out['source_port_work_j'][label]+=.5*(a+z)*dt
            previous=row;previous_phase=i
    if previous is None:raise ValueError('No native SR cycle rows')
    for i,(ph,out) in enumerate(zip(phases,observed)):
        def window_events(node,direction=None):
            return [e for e in events.get(node,[]) if ph['start_s']-.1e-9<=e['time_s']<ph['stop_s']-.1e-9
                    and (direction is None or e['direction']==direction)]
        out['events']={n:window_events(n) for n in signals}
        changed=ph['previous_Q'] is not None and ph['Q']!=ph['previous_Q']
        required_direction=1 if ph['Q'] else -1
        qedges=window_events(P+'CLOCK_Q');qbedges=window_events(P+'XCLOCK.QB')
        wanted=(len(qedges)==1 and qedges[0]['direction']==required_direction and len(qbedges)==1
                and qbedges[0]['direction']==-required_direction) if changed else not(qedges or qbedges)
        out['expected_output_transition']=changed;out['expected_edge_pattern_observed']=wanted
        out['delays_s']=None;out['delay_status']='not_applicable' if not changed else 'unobserved_or_ambiguous'
        if changed:
            causes=window_events(P+ph['cause_node'],ph['cause_direction'])
            command=window_events(P+'CYCLE_'+ph['changed_command'],ph['cause_direction'])
            if len(causes)==len(command)==len(qedges)==len(qbedges)==1:
                out['delays_s']=dict(command_to_actual_input=causes[0]['time_s']-command[0]['time_s'],
                    actual_input_to_Q=qedges[0]['time_s']-causes[0]['time_s'],
                    actual_input_to_QB=qbedges[0]['time_s']-causes[0]['time_s'])
                out['delay_status']='signed_native_halfrail_events'
        if out['hold_points']<2:verdict=None
        elif out['hold_input_mismatches'] or out['hold_Q_mismatches'] or out['hold_QB_mismatches'] or not wanted:verdict=False
        elif changed and out['delays_s'] is None:verdict=None
        else:verdict=True
        out['functional_observation_pass']=verdict
        out['source_work_groups_j']={g:{label:out['source_port_work_j'][label] for label in labels}
                                     for g,labels in cyc['energy_groups'].items()}
        out['bias_snapshots']={}
        for role in ['QB_min','QB_max']:
            row=saved.get((i,role))
            if row is None:out['bias_snapshots'][role]=None;continue
            devices={}
            for path in cyc['core_bias_mos']:
                d,g,s,b=[value(row,n) for n in cfg['observed_mos'][path]['nodes']]
                devices[path]=dict(D_v=d,G_v=g,S_v=s,B_v=b,VGS_v=g-s,VDS_v=d-s,VBS_v=b-s,
                    native_total_terminal_currents_a={str(p):value(row,path+':'+str(p)) for p in range(1,5)})
            out['bias_snapshots'][role]=dict(time_s=row[0],devices=devices,region_Vth_channel_components_saved=False)
    flags=[p['functional_observation_pass'] for p in observed]
    suite=False if False in flags else None if None in flags else True
    return dict(phases=observed,events=events,functional_observation_pass=suite,
        logic_policy='10/90 percent-VDD hold bands and raw halfrail events are bench criteria, not foundry noise-margin signoff. Missing/ambiguous observations stay unknown.',
        integration_policy='Native endpoints within each phase only; no current interpolation/rescaling or implied phase-boundary energy. Work is per terminal, not unique device dissipation.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    a=parser.parse_args();run,output=os.path.realpath(a.run_dir),os.path.realpath(a.output_dir)
    if output!=os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):raise ValueError('Fresh managed derived directory required')
    library=standard.verify_library(os.path.join(run,'inputs','external_library.json'));state=native.read(os.path.join(run,'simulation.state.json'))
    if state['status']!='complete' or state['exit_code']!=0 or not state.get('native',{}).get('native_analysis_pass') or not state.get('native',{}).get('zero_error_footer'):
        raise ValueError('Native simulation incomplete')
    with open(os.path.join(run,'raw','logStatus')) as h:
        if not re.search(r'tran_first\s+PASS',h.read()):raise ValueError('Native transient PASS missing')
    paths=[os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Exactly one native transient required')
    cfg_path=os.path.join(run,'inputs','measurement.json');cfg=native.read(cfg_path)
    try:result=native.summarize(paths[0],cfg,output)
    except ValueError as exc:
        if 'export exceeds 30 MiB cap' in str(exc):raise ValueError('SR temporary full-analysis table exceeds64MiB limit; final collection limit is30MiB')
        raise
    result['measurement_sha256']=standard.file_identity(cfg_path)['sha256'];result['external_library_identity']=library
    result['SR_cycle_observations']=inspect_cycle(output,cfg)
    result['native_library_current_bindings']={p:{s:result['trace_bindings'][native.norm(s)] for s in item['requested_numeric_terminal_currents']}
                                             for p,item in cfg['library_mos'].items()}
    work=result.pop('full_history_source_energy');result['full_history_observed_port_work']=work
    result['full_history_work_groups']={g:{label:work[label] for label in labels} for g,labels in cfg['cycle']['energy_groups'].items()}
    if set(work)!=set(label for labels in cfg['cycle']['energy_groups'].values() for label in labels):raise ValueError('Work classification incomplete')
    result['physical_terminal_screen_pass']=not any(v['over_limit_native_points'] for v in result['full_history_voltage_stress'].values())
    result['native_warning_codes']=state['native'].get('warning_codes');codes=result['native_warning_codes']
    result['CMI_warning_present']=any(s.startswith('CMI') for s in codes) if codes is not None else None
    result['native_effective_settings']=state['native'].get('effective_settings');result['circuit_qualified']=None
    result['export_policy']=cfg['cycle']['export_policy'];result['analysis_peak_rss_bytes']=None
    # All per-phase logic, current, work and606 stress calculations above used
    # the complete analysis table; only the final return waveform is narrowed.
    result['wave_projection']=project_native_wave(output,cfg)
    result['collection_budget_policy']=dict(limit_bytes=cfg['cycle']['output_budget_bytes'],
        user_limit_bytes=cfg['cycle']['collection_user_limit_bytes'],
        final_state_growth_reserve_bytes=cfg['cycle']['final_analysis_state_reserve_bytes'],
        membership='Same seven managed log/state paths plus every derived file; full raw PSF stays remote.')
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:raise ValueError('Analysis RSS exceeds256MiB')
    encoded=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    collection=collection_budget(run,output,cfg,len(encoded))
    native.write_new(os.path.join(output,'result.json'),result)
    print('SR_CYCLE_NATIVE_OBSERVATIONS_COMPLETE',result['native_points'],
          'functional',result['SR_cycle_observations']['functional_observation_pass'],'physical',result['physical_terminal_screen_pass'],
          'projected_collection_bytes',collection['projected_collection_bytes'],'not full ADC qualification')


if __name__=='__main__':main()
