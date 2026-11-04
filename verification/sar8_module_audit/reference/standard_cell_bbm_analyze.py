"""Native standard-cell bit0 BBM measurement. Derived from frozen real_bbm analyzer; actual ports and energy groups are explicit config."""
from __future__ import print_function
import argparse,gzip,os,re,struct,sys
sys.dont_write_bytecode=True
import io_cell_analyze as cell


def validate(cfg):
    norm=cell.base.norm;v=[norm(n) for n in cfg['voltage_saves']];i=[norm(n) for n in cfg['current_saves']]
    cat=dict((norm(n),x) for n,x in cfg['terminal_current_catalog'].items());eq=dict((norm(n),[norm(b) for b in q]) for n,q in cfg['kcl_terms'].items())
    if len(set(v))!=len(v) or len(set(i))!=len(i) or set(v)&set(i) or set(cat)!=set(i):raise ValueError('Complete unique save/catalog map required')
    inv=cfg['boundary_inventory']
    if len(v)!=inv['voltage_count'] or len(i)!=inv['mandatory_currents'] or len(eq)!=inv['KCL_nodes'] or set(eq)!=set(norm(n) for n in cfg['required_kcl_nodes']):raise ValueError('Inventory coverage mismatch')
    for n,q in eq.items():
        expected=set(b for b,x in cat.items() if norm(x['node'])==n)
        if not q or len(set(q))!=len(q) or set(q)!=expected:raise ValueError('Incomplete actual incidence '+n)
    need=set(eq)|set(norm(n) for n in cfg['diagnostic_voltage_columns']+cfg['edge_nodes']+list(cfg['initial_witness_v']))
    need|=set(norm(n) for p in cfg['selected_mos_pair_screens'] for n in p['nodes'])-set(['0'])
    if not need<=set(v) or len(cfg['selected_mos_pair_screens'])!=738 or inv['all_actual_MOS']!=123 or inv['BBM_primitive_count']!=38 or inv['native_library_MOS']!=42:raise ValueError('Standard-cell BBM/123MOS738 screens required')
    for p in cfg['selected_mos_pair_screens']:
        if p['screen_v']!=(.99 if p['model'] in ['nch_mac','pch_mac'] else 1.98):raise ValueError('Actual-model screen changed')
    if cfg['variant']!='original_bit0_BBM_native_stdcell_D1_ideal_CODE' or cfg['source_node']!='code' or cfg['source_current']!='vcode:1':raise ValueError('CODE boundary required')
    if any(n.startswith(('vl0:','vl0n:','vgnp:','vgpn:','vpre:','vgpp:')) for n in i):raise ValueError('Ideal internal reference control forbidden')
    if not {'code','xdut.h0','xdut.l0','xdut.gnpdrv','xdut.gpndrv'}<=set(v) or len(eq['xdut.h0'])!=6 or len(eq['xdut.l0'])!=6 or len(eq['code'])!=9:raise ValueError('All H/L/CODE fanout required')
    if cfg['source_peaks'] or cfg['diagnostic_start_s']!=0 or cfg['diagnostic_stop_s']!=52e-9 or cfg['max_total_output_bytes']!=30*cell.MIB:raise ValueError('Full52ns native history/fixed budget required')
    migration=cfg['standard_cell_migration']
    if migration['C0_multi']!=1 or not migration['all_retained_records_exact'] or not migration['external_library_only'] or migration['geometry_copied']:
        raise ValueError('Original C0/retained analog/library boundary required')
    for q in cfg['driver_source_ports'].values():
        if len(q['source_port_branches'])!=2 or not set(q['source_port_branches'])<=set(i):
            raise ValueError('Actual native output MOS currents missing')
    return sorted(v+i),sorted(i),eq


def measurements_core(original,result,cfg,out):
    m=original(result,cfg,out);m['legacy_fixed_window_diagnostic_not_acceptance']=m.pop('load_settling')
    m['GNN_AB_IO_direct_VDD_energy_J']=m.pop('upstream_core_direct_VDD_terminal_energy_J')
    def unique(node,direction,a,b):
        q=[x for x in result['half_vdd_events'].get(node,[]) if x['direction']==direction and a<=x['estimated_time_s']<=b]
        return q[0] if len(q)==1 else None
    def diff(a,b):return None if a is None or b is None else b['estimated_time_s']-a['estimated_time_s']
    events={}
    for p in cfg['logical_event_windows']:
        high=p['name']=='select_high';directions={'code':'rising' if high else 'falling','xdut.h0':'rising' if high else 'falling','xdut.l0':'falling' if high else 'rising',
            'xdut.gnn0':'falling' if high else 'rising','xdut.gpp0':'rising' if high else 'falling',
            'xdut.gnp0':'falling' if high else 'rising','xdut.gpn0':'rising' if high else 'falling'}
        w=dict((n,unique(n,d,p['start_s'],p['stop_s'])) for n,d in directions.items())
        events[p['name']]=dict(native_halfVDD_witnesses=w,missing_or_ambiguous_nodes=[n for n,x in w.items() if x is None],
            CODE_to_H_s=diff(w['code'],w['xdut.h0']),CODE_to_L_s=diff(w['code'],w['xdut.l0']),
            BBM_signed_off_to_on_gap_s=diff(w['xdut.l0'],w['xdut.h0']) if high else diff(w['xdut.h0'],w['xdut.l0']),
            N_signed_off_to_on_gap_s=diff(w['xdut.gnn0'],w['xdut.gnp0']) if high else diff(w['xdut.gnp0'],w['xdut.gnn0']),
            P_signed_off_to_on_gap_s=diff(w['xdut.gpp0'],w['xdut.gpn0']) if high else diff(w['xdut.gpn0'],w['xdut.gpp0']))
    actual_on={}
    off=events['select_low']['native_halfVDD_witnesses'];offs=[off[n]['estimated_time_s'] for n in ['xdut.gnp0','xdut.gpn0'] if off[n] is not None]
    high_stop=min(offs) if len(offs)==2 else 48e-9
    for name in ['select_high','select_low']:
        w=events[name]['native_halfVDD_witnesses'];required=['code','xdut.h0','xdut.l0','xdut.gnn0','xdut.gpp0','xdut.gnp0','xdut.gpn0']
        start=max(w[n]['estimated_time_s'] for n in required) if all(w[n] is not None for n in required) else None
        stop=high_stop if name=='select_high' else 52e-9
        actual_on[name]=dict(start_native_control_estimate_s=start,stop_s=stop,
            status='missing_or_ambiguous_controls' if start is None else 'no_observable_ON_window' if start>=stop else 'observed_window',
            threshold_is_timing_diagnostic_not_MOS_conduction=True,
            nodes=dict((n,dict(samples=0,last_native_s=None,final_error_V=None,last_outside_1mV_s=None,remained_inside_from_native_s=None)) for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0']))
    currents=cfg['terminal_current_catalog'];drivers=dict((n,(q['node'],q['source_port_branches'])) for n,q in cfg['driver_source_ports'].items())
    internals={}
    for name,(node,source) in drivers.items():
        loads=[b.lower() for b,x in currents.items() if x['node'].lower()==node and b.lower() not in source]
        internals[name]=dict(node=node,source_port_branches=source,load_port_branches=loads,
            driver_output_work_J=0.,load_work_J=0.,max_KCL_A=0.,load_min_A=None,load_max_A=None,
            event_charge=dict((n,dict(signed_C=0.,absolute_C=0.,samples=0)) for n in ['select_high','select_low']))
    code_loads=[b.lower() for b,x in currents.items() if x['node']=='CODE' and b!='VCODE:1']
    code=dict(incident_load_branches=code_loads,net_source_J=0.,positive_source_J=0.,returned_J=0.,load_work_J=0.,max_KCL_A=0.,
        input_min_A=None,input_max_A=None,event_charge=dict((n,dict(signed_C=0.,absolute_C=0.,samples=0)) for n in ['select_high','select_low']))
    groups={}
    for n,x in currents.items():
        if x['port'] not in [3,4] or not x['model'].startswith('pch') or x['node']!='VDD!':continue
        inst=x['instance'];group=cfg['source_energy_groups'][inst]
        groups[group]=groups.get(group,0.)+cfg['supply_V']*result['current_charge_trapezoids'][n.lower()]['signed_C']
    body=[]
    for p in cfg['selected_mos_pair_screens']:
        if p['terminal'] not in ['bd','bs']:continue
        key=p['instance']+':'+p['terminal'];x=result['selected_mos_pair_extrema'][key];nt=p['model'].startswith('nch');branch=p['instance'].lower()+':4'
        body.append(dict(pair=key,model=p['model'],forward_definition='Vbody-Vdiffusion' if nt else 'Vdiffusion-Vbody',
            signed_forward_min_V=x['min'] if nt else -x['max'],signed_forward_max_V=x['max'] if nt else -x['min'],
            peak_time_s=x['max_time_s'] if nt else x['min_time_s'],body_current_extrema=result['voltage_and_current_extrema'][branch],
            body_native_charge=result['current_charge_trapezoids'][branch],body_current_at_peak_A=None))
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz');c=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    last=None;last_events={};overlap=dict(HL_both_above_halfVDD_duration_s=0.,maximum_min_HL_V=None,time_s=None)
    opposed=dict((s,dict(peak_min_opposed_abs_A=0.,time_s=None,peak_witness=None,native_opposed_min_abs_charge_C=0.)) for s in ['N','P']);last_opposed=None
    with gzip.open(os.path.join(out,e['file']),'rb') as stream:
        while True:
            raw=stream.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Incomplete native row')
            row=fmt.unpack(raw);t=row[0];cl=sum(row[c[b]] for b in code_loads);power=-row[c['code']]*row[c['vcode:1']];loadwork=row[c['code']]*cl
            code['max_KCL_A']=max(code['max_KCL_A'],abs(cl+row[c['vcode:1']]))
            code['input_min_A']=cl if code['input_min_A'] is None else min(code['input_min_A'],cl);code['input_max_A']=cl if code['input_max_A'] is None else max(code['input_max_A'],cl)
            now={};both=1. if min(row[c['xdut.h0']],row[c['xdut.l0']])>row[c['vdd!']]*.5 else 0.
            low=min(row[c['xdut.h0']],row[c['xdut.l0']])
            if overlap['maximum_min_HL_V'] is None or low>overlap['maximum_min_HL_V']:overlap.update(maximum_min_HL_V=low,time_s=t)
            opposed_now={}
            for side,gn,gp,bot in [('N','xdut.gnn0','xdut.gnp0','xdut.xcdac.bn0'),('P','xdut.gpn0','xdut.gpp0','xdut.xcdac.bp0')]:
                stem='xdut.xcdac.xs'+side.lower()+'0.';lo=row[c[stem+'mn_low:1']];hi=row[c[stem+'mp_high:1']];value=min(abs(lo),abs(hi)) if lo*hi<0 else 0.;opposed_now[side]=value
                if value>opposed[side]['peak_min_opposed_abs_A']:opposed[side].update(peak_min_opposed_abs_A=value,time_s=t,
                    peak_witness=dict(low_D_A=lo,high_D_A=hi,low_gate_V=row[c[gn]],high_gate_V=row[c[gp]],bottom_V=row[c[bot]],VREFN_V=row[c['vrefn']],VREFP_V=row[c['vrefp']]))
            if last_opposed is not None:
                pt,old=last_opposed
                for side in opposed:opposed[side]['native_opposed_min_abs_charge_C']+=(old[side]+opposed_now[side])*(t-pt)*.5
            last_opposed=(t,opposed_now)
            for name,q in internals.items():
                source=sum(row[c[b]] for b in q['source_port_branches']);load=sum(row[c[b]] for b in q['load_port_branches']);voltage=row[c[q['node']]]
                now[name]=(load,-voltage*source,voltage*load);q['max_KCL_A']=max(q['max_KCL_A'],abs(source+load))
                q['load_min_A']=load if q['load_min_A'] is None else min(q['load_min_A'],load);q['load_max_A']=load if q['load_max_A'] is None else max(q['load_max_A'],load)
            if last is not None:
                pt,cp,lp,old_both,old=last;dt=t-pt;code['net_source_J']+=(power+cp)*dt*.5;code['load_work_J']+=(loadwork+lp)*dt*.5
                code['positive_source_J']+=(max(power,0)+max(cp,0))*dt*.5;code['returned_J']+=(max(-power,0)+max(-cp,0))*dt*.5
                overlap['HL_both_above_halfVDD_duration_s']+=(both+old_both)*dt*.5
                for name,q in internals.items():q['driver_output_work_J']+=(now[name][1]+old[name][1])*dt*.5;q['load_work_J']+=(now[name][2]+old[name][2])*dt*.5
            last=(t,power,loadwork,both,now)
            for p in cfg['logical_event_windows']:
                if p['start_s']<=t<=p['stop_s']:
                    for name,q,load in [('CODE',code,cl)]+[(n,q,now[n][0]) for n,q in internals.items()]:
                        key=(name,p['name']);s=q['event_charge'][p['name']];s['samples']+=1
                        if key in last_events:
                            pt,pl=last_events[key];s['signed_C']+=(load+pl)*(t-pt)*.5;s['absolute_C']+=(abs(load)+abs(pl))*(t-pt)*.5
                        last_events[key]=(t,load)
            for name,q in actual_on.items():
                if q['status']!='observed_window' or not(q['start_native_control_estimate_s']<=t<=q['stop_s']):continue
                for n,s in q['nodes'].items():
                    high=name=='select_high';ref=('vrefp' if high else 'vrefn') if n.endswith('bn0') else ('vrefn' if high else 'vrefp');err=row[c[n]]-row[c[ref]]
                    s['samples']+=1;s['last_native_s']=t;s['final_error_V']=err
                    if abs(err)>.001:s['last_outside_1mV_s']=t;s['remained_inside_from_native_s']=None
                    elif s['remained_inside_from_native_s'] is None:s['remained_inside_from_native_s']=t
            for p in body:
                b=p['pair'].split(':')[0].lower()+':4'
                if b in c and abs(t-p['peak_time_s'])<1e-18:p['body_current_at_peak_A']=row[c[b]]
    for q in internals.values():q['work_closure_residual_J']=q['driver_output_work_J']-q['load_work_J']
    code['source_minus_load_work_J']=code['net_source_J']-code['load_work_J']
    for q in actual_on.values():
        for s in q['nodes'].values():s['established_within_window']=None if not s['samples'] else s['remained_inside_from_native_s'] is not None
    rail={}
    for n in cfg['diagnostic_voltage_columns']:
        x=result['voltage_and_current_extrema'][n];rail[n]=dict(x,below_ground_V=max(0.,-x['min']),above_VDD_V=max(0.,x['max']-cfg['supply_V']))
    m.update(actual_control_events=events,actual_correct_ON_settling=actual_on,CODE_source_and_input_load=code,internal_driver_load_work=internals,
        sampled_HL_mutual_exclusion=overlap,opposed_total_reference_terminal_current=opposed,reference_control_direct_VDD_energy_J=groups,body_forward_polarity=body,supply_rail_excursions=rail,
        boundary='Native D1 BBM/core H driver, original RC/clear and tested IO low paths/real loads; ideal CODE/rails, comparator reset; no complete ADC acceptance',
        interpretation='HalfVDD edges/overlap are control diagnostics, not transistor conduction or shoot-through proof. Total D/G/S/B include displacement; positive junction polarity is not a diode-current fraction.',
        body_note='Native total bulk port4 and junction polarity; unavailable coincident bulk samples remain null, never fabricated.',
        work_accounting='CODE ideal source and VDD are external supplies; H/L/PRE/GPNPRE works are internal transfers, never added as external power.',
        missing_edges_or_52ns_nonsettling_not_silently_accepted=True)
    return m


def phase_reset_metrics(result,cfg,out):
    m={}
    physical={}
    for phase,start,stop,high in [('select_high',43.005e-9,47.995e-9,True),('select_low',48.005e-9,52e-9,False)]:
        physical[phase]=dict(requested_interval_s=[start,stop],stop_included=not high,
            nodes=dict((n,dict(samples=0,first_native_s=None,last_native_s=None,final_error_V=None,last_outside_1mV_s=None,remained_inside_from_native_s=None)) for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0']))
    resets={}
    for leg,start,stop,mid,inp in [('HD',48.005e-9,52e-9,48e-9,'code'),('LD',43.005e-9,47.995e-9,43e-9,'xdut.xbbm0.cb')]:
        q=[e for e in result['half_vdd_events'].get(inp,[]) if e['direction']=='falling' and mid-20e-12<=e['estimated_time_s']<=stop]
        resets[leg]=dict(requested_interval_s=[start,stop],CODE_midpoint_s=mid,input_node=inp,
            actual_input_falling_halfVDD_s=q[0]['estimated_time_s'] if len(q)==1 else None,
            nodes=dict((n,dict(target_V=target,samples=0,last_native_s=None,final_error_V=None,last_outside_1percent_s=None,remained_inside_from_native_s=None))
                for n,target in [('xdut.xbbm0.xd_'+leg.lower()+'.rc0',0.),('xdut.xbbm0.xd_'+leg.lower()+'.rc1',cfg['supply_V']),('xdut.xbbm0.'+leg.lower(),0.)]))
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz');c=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    with gzip.open(os.path.join(out,e['file']),'rb') as stream:
        while True:
            raw=stream.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Incomplete native row')
            row=fmt.unpack(raw);t=row[0]
            for phase,q in physical.items():
                a,b=q['requested_interval_s']
                if not(a<=t and (t<=b if q['stop_included'] else t<b)):continue
                for n,s in q['nodes'].items():
                    high=phase=='select_high';ref=('vrefp' if high else 'vrefn') if n.endswith('bn0') else ('vrefn' if high else 'vrefp');err=row[c[n]]-row[c[ref]]
                    if s['first_native_s'] is None:s['first_native_s']=t
                    s['samples']+=1;s['last_native_s']=t;s['final_error_V']=err
                    if abs(err)>.001:s['last_outside_1mV_s']=t;s['remained_inside_from_native_s']=None
                    elif s['remained_inside_from_native_s'] is None:s['remained_inside_from_native_s']=t
            for leg,q in resets.items():
                a,b=q['requested_interval_s']
                if not(a<=t and (t<=b if leg=='HD' else t<b)):continue
                for n,s in q['nodes'].items():
                    err=row[c[n]]-s['target_V'];s['samples']+=1;s['last_native_s']=t;s['final_error_V']=err
                    if abs(err)>cfg['supply_V']*.01:s['last_outside_1percent_s']=t;s['remained_inside_from_native_s']=None
                    elif s['remained_inside_from_native_s'] is None:s['remained_inside_from_native_s']=t
    for q in physical.values():
        for s in q['nodes'].values():s['diagnostic_established']=None if not s['samples'] else s['remained_inside_from_native_s'] is not None
    for q in resets.values():
        for s in q['nodes'].values():
            t=s['remained_inside_from_native_s'];s['diagnostic_reset_complete']=None if not s['samples'] else t is not None
            s['delay_from_CODE_midpoint_s']=None if t is None else t-q['CODE_midpoint_s']
            s['delay_from_actual_input_halfVDD_s']=None if t is None or q['actual_input_falling_halfVDD_s'] is None else t-q['actual_input_falling_halfVDD_s']
    m.update(physical_command_phase_reference_settling=physical,delay_leg_reset_diagnostics=resets,standard_cell_migration=cfg['standard_cell_migration'],
        boundary='Native library ordinary core gates/original C0multi1, RC-clear and IO/real loads; ideal CODE/rails, no ADC or repair qualification',
        phase_window_note='Frozen halfVDD endpoint crosses into turnoff and is retained only as switching diagnostic. Stable-high judgement ends before next CODE edge starts47.995ns.1mV/1percent are diagnostics, not specification changes.')
    return m


def measurements(original,result,cfg,out):
    m=measurements_core(original,result,cfg,out)
    m['legacy_halfVDD_window_switching_diagnostic']=m['actual_correct_ON_settling']
    m.update(phase_reset_metrics(result,cfg,out))
    return m


def analyze(run,out):
    cfg=cell.base.read_json(cell.base.safe_file(os.path.realpath(run),'inputs/measurement.json'));validate(cfg);old_v,old_m,old_b=cell.validate,cell.metrics,cell.base.Budget
    class BBMBudget(old_b):
        def json(self,name,value):
            if name=='result.json':value['waveform_note']='Complete native bench history; actual diagnostic voltages/currents and all%d declared KCL nodes. Lossless timestamps, no internal edge alignment.'%len(cfg['required_kcl_nodes'])
            return old_b.json(self,name,value)
    try:
        cell.validate=validate;cell.metrics=lambda r,c,p:measurements(old_m,r,c,p);cell.base.Budget=BBMBudget
        return cell.analyze(run,out)
    finally:cell.validate,cell.metrics,cell.base.Budget=old_v,old_m,old_b


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('STDCELL_BBM_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
