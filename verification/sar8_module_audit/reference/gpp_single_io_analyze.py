"""Single IO GPP implementation; frozen native parser/writer reused."""
from __future__ import print_function
import argparse,gzip,os,struct,sys
sys.dont_write_bytecode=True
import io_cell_analyze as cell


def validate(cfg):
    norm=cell.base.norm;v=[norm(n) for n in cfg['voltage_saves']];i=[norm(n) for n in cfg['current_saves']]
    if len(set(v))!=len(v) or len(set(i))!=len(i) or set(v)&set(i):raise ValueError('Unique saves required')
    cat=dict((norm(n),d) for n,d in cfg['terminal_current_catalog'].items());eq=dict((norm(n),[norm(t) for t in ts]) for n,ts in cfg['kcl_terms'].items())
    if set(cat)!=set(i) or set(eq)!=set(norm(n) for n in cfg['required_kcl_nodes']) or len(eq)!=12:raise ValueError('Full current/12-node KCL map required')
    for n,terms in eq.items():
        expected=set(b for b,d in cat.items() if norm(d['node'])==n)
        if not terms or len(set(terms))!=len(terms) or set(terms)!=expected:raise ValueError('KCL incidence mismatch '+n)
    need=set(eq)|set(norm(n) for n in cfg['diagnostic_voltage_columns']+cfg['edge_nodes']+list(cfg['initial_witness_v']))
    need|=set(norm(n) for p in cfg['selected_mos_pair_screens'] for n in p['nodes'])-set(['0'])
    if not need<=set(v) or len(cfg['selected_mos_pair_screens'])!=474:raise ValueError('All79 MOS/474 terminal screens required')
    for p in cfg['selected_mos_pair_screens']:
        limit=.99 if p['model'] in ['nch_mac','pch_mac'] else 1.98
        if p['screen_v']!=limit:raise ValueError('Actual-model screen mismatch')
    if cfg['variant']!='real_X025_GPP_single_IO_ideal_L0' or cfg['pre_node']!='xdut.pre' or cfg['source_current']!='vl0:1':raise ValueError('Explicit real PRE / ideal L0 boundary required')
    if any(x.startswith(('vpre:','vgpp:')) for x in i) or not {'vl0:1','xdut.x025.mn:1','xdut.x025.mp:1','xdut.gppin:2','xdut.gppip:2'}<=set(i):raise ValueError('Shared-load/source-conflict mapping invalid')
    if cfg['source_peaks'] or cfg['diagnostic_start_s']!=0 or cfg['diagnostic_stop_s']!=cfg['source_history_stop_s'] or cfg['max_total_output_bytes']!=30*cell.MIB:raise ValueError('Full native history/fixed budget required')
    return sorted(v+i),sorted(i),eq


def measurements(original,result,cfg,out):
    m=original(result,cfg,out);m['GNN_AB_IO_direct_VDD_energy_J']=m.pop('upstream_core_direct_VDD_terminal_energy_J')
    m['test_cell_role']='Legacy test_cell energy refers to GNN_C; restored_stage_direct_VDD_energy_J identifies X025, single IO GPP and ABC.'
    energies={}
    for name,p in [('GNN_A','xdut.gnnap'),('GNN_B','xdut.gnnbp'),('GNN_C','xdut.gnncp'),
                   ('GPP_single_IO','xdut.gppip'),('X025','xdut.x025.mp')]:
        energies[name]=cfg['supply_V']*sum(result['current_charge_trapezoids'][p+':'+str(pin)]['signed_C'] for pin in [3,4])
    body=[]
    for p in cfg['selected_mos_pair_screens']:
        if p['terminal'] not in ['bd','bs']:continue
        key=p['instance']+':'+p['terminal'];x=result['selected_mos_pair_extrema'][key];n_type=p['model'].startswith('nch');branch=p['instance'].lower()+':4'
        body.append(dict(pair=key,model=p['model'],forward_definition='Vbody-Vdiffusion' if n_type else 'Vdiffusion-Vbody',
            signed_forward_min_V=x['min'] if n_type else -x['max'],signed_forward_max_V=x['max'] if n_type else -x['min'],
            peak_time_s=x['max_time_s'] if n_type else x['min_time_s'],body_current_extrema=result['voltage_and_current_extrema'][branch],
            body_native_charge=result['current_charge_trapezoids'][branch],body_current_at_forward_peak_A=None))
    trace=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz');c=dict((n,j) for j,n in enumerate(trace['columns']));fmt=struct.Struct('<'+'d'*len(c))
    loads={name:dict(min_A=None,max_A=None,min_time_s=None,max_time_s=None,full_signed_charge_C=0.,event_charge={p['name']:dict(samples=0,first_s=None,last_s=None,signed_C=0.,absolute_C=0.) for p in cfg['logical_event_windows']}) for name in ['L0_shared','PRE_A_gates']}
    last_events={};last=None;work=dict(L0_net_delivered_J=0.,L0_positive_delivered_J=0.,L0_returned_J=0.,L0_gate_port_work_J=0.,PRE_A_gate_internal_work_J=0.,X025_to_PRE_internal_work_J=0.,max_L0_KCL_A=0.)
    on={p['name']:dict((n,dict(samples=0,last_outside_1mV_s=None,remained_inside_from_native_s=None,last_native_s=None,final_error_V=None)) for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0']) for p in cfg['correct_on_windows']}
    opposed={side:dict(peak_min_opposed_abs_A=0.,time_s=None,peak_witness=None,native_opposed_min_abs_charge_C=0.) for side in ['N','P']}
    l0_branches=['xdut.x025.mn:2','xdut.x025.mp:2','xdut.gppin:2','xdut.gppip:2']
    with gzip.open(os.path.join(out,trace['file']),'rb') as stream:
        while True:
            raw=stream.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Incomplete native row')
            row=fmt.unpack(raw);t=row[0];l0=sum(row[c[b]] for b in l0_branches);pre=row[c['xdut.gnnan:2']]+row[c['xdut.gnnap:2']]
            source=row[c['vl0:1']];vl0=row[c['l0']];vp=row[c['xdut.pre']];pd=-vl0*source;pg=vl0*l0;pp=vp*pre;px=-vp*(row[c['xdut.x025.mn:1']]+row[c['xdut.x025.mp:1']])
            work['max_L0_KCL_A']=max(work['max_L0_KCL_A'],abs(source+l0));current={'L0_shared':l0,'PRE_A_gates':pre};co={}
            for side,gateN,gateP,bot in [('N','xdut.gnn0','xdut.gnp0','xdut.xcdac.bn0'),('P','xdut.gpn0','xdut.gpp0','xdut.xcdac.bp0')]:
                stem='xdut.xcdac.xs'+side.lower()+'0.';low=row[c[stem+'mn_low:1']];high=row[c[stem+'mp_high:1']];co[side]=min(abs(low),abs(high)) if low*high<0 else 0.
                if co[side]>opposed[side]['peak_min_opposed_abs_A']:
                    opposed[side].update(peak_min_opposed_abs_A=co[side],time_s=t,peak_witness=dict(low_D_A=low,high_D_A=high,
                        low_gate_V=row[c[gateN]],high_gate_V=row[c[gateP]],bottom_V=row[c[bot]],VREFN_V=row[c['vrefn']],VREFP_V=row[c['vrefp']]))
            if last is not None:
                pt,old_i,old_p,old_co=last;dt=t-pt
                for name in loads:loads[name]['full_signed_charge_C']+=(current[name]+old_i[name])*dt*.5
                for name,value,old_value in [('L0_net_delivered_J',pd,old_p[0]),('L0_gate_port_work_J',pg,old_p[1]),
                    ('PRE_A_gate_internal_work_J',pp,old_p[2]),('X025_to_PRE_internal_work_J',px,old_p[3])]:work[name]+=(value+old_value)*dt*.5
                work['L0_positive_delivered_J']+=(max(pd,0)+max(old_p[0],0))*dt*.5;work['L0_returned_J']+=(max(-pd,0)+max(-old_p[0],0))*dt*.5
                for side in opposed:opposed[side]['native_opposed_min_abs_charge_C']+=(co[side]+old_co[side])*dt*.5
            last=(t,current,(pd,pg,pp,px),co)
            for name,i in current.items():
                for kind,less in [('min',True),('max',False)]:
                    if loads[name][kind+'_A'] is None or (i<loads[name][kind+'_A'] if less else i>loads[name][kind+'_A']):loads[name][kind+'_A']=i;loads[name][kind+'_time_s']=t
                for p in cfg['logical_event_windows']:
                    if p['start_s']<=t<=p['stop_s']:
                        key=(name,p['name']);s=loads[name]['event_charge'][p['name']]
                        if s['first_s'] is None:s['first_s']=t
                        if key in last_events:
                            pt,pi=last_events[key];s['signed_C']+=(i+pi)*(t-pt)*.5;s['absolute_C']+=(abs(i)+abs(pi))*(t-pt)*.5
                        last_events[key]=(t,i);s['last_s']=t;s['samples']+=1
            for p in cfg['correct_on_windows']:
                if p['start_s']<=t and (t<p['stop_s'] if p['stop_exclusive'] else t<=p['stop_s']):
                    for node in on[p['name']]:
                        ref=('vrefp' if p['select_high'] else 'vrefn') if node.endswith('bn0') else ('vrefn' if p['select_high'] else 'vrefp')
                        err=row[c[node]]-row[c[ref]];s=on[p['name']][node];s['samples']+=1;s['last_native_s']=t;s['final_error_V']=err
                        if abs(err)>.001:s['last_outside_1mV_s']=t;s['remained_inside_from_native_s']=None
                        elif s['remained_inside_from_native_s'] is None:s['remained_inside_from_native_s']=t
            for p in body:
                branch=p['pair'].split(':')[0].lower()+':4'
                if branch in c and abs(t-p['peak_time_s'])<1e-18:p['body_current_at_forward_peak_A']=row[c[branch]]
    if any(s['samples']<2 for d in loads.values() for s in d['event_charge'].values()) or any(s['samples']==0 for phase in on.values() for s in phase.values()):raise ValueError('Measurement window absent')
    def edge(node,direction,start,stop):
        q=[e for e in result['half_vdd_events'].get(node,[]) if e['direction']==direction and start<=e['estimated_time_s']<=stop]
        return q[0] if len(q)==1 else None
    def difference(a,b):return None if a is None or b is None else b['estimated_time_s']-a['estimated_time_s']
    timing={}
    for p in cfg['logical_event_windows']:
        disable=p['name']=='disable_low';a,b=p['start_s'],p['stop_s'];w={}
        dirs={'l0':'falling' if disable else 'rising','xdut.pre':'rising' if disable else 'falling',
              'xdut.gnna':'falling' if disable else 'rising','xdut.gnnb':'rising' if disable else 'falling',
              'xdut.gnndrv':'falling' if disable else 'rising','xdut.gnn0':'falling' if disable else 'rising',
              'xdut.gppdrv':'rising' if disable else 'falling','xdut.gpp0':'rising' if disable else 'falling'}
        for n,d in dirs.items():w[n]=edge(n,d,a,b)
        timing[p['name']]=dict(native_edge_witnesses=w,L0_to_PRE_s=difference(w['l0'],w['xdut.pre']),
            PRE_to_GNN0_s=difference(w['xdut.pre'],w['xdut.gnn0']),L0_to_GNN0_s=difference(w['l0'],w['xdut.gnn0']),
            L0_to_GPP0_s=difference(w['l0'],w['xdut.gpp0']),GNN_after_GPP_control_skew_s=difference(w['xdut.gpp0'],w['xdut.gnn0']))
    gaps={}
    for name,first,fd,second,sd,a,b in [
        ('N_high_transition','xdut.gnn0','falling','xdut.gnp0','falling',42.98e-9,45e-9),
        ('P_high_transition','xdut.gpp0','rising','xdut.gpn0','rising',42.98e-9,45e-9),
        ('N_low_transition','xdut.gnp0','rising','xdut.gnn0','rising',46.98e-9,51e-9),
        ('P_low_transition','xdut.gpn0','falling','xdut.gpp0','falling',46.98e-9,51e-9)]:
        x,y=edge(first,fd,a,b),edge(second,sd,a,b);gaps[name]=dict(first_off_witness=x,second_on_witness=y,signed_halfVDD_control_gap_s=difference(x,y))
    rail={}
    for n in ['l0','xdut.pre','xdut.gnna','xdut.gnnb','xdut.gnndrv','xdut.gnn0','xdut.gppdrv','xdut.gpp0','xdut.xcdac.bn0','xdut.xcdac.bp0']:
        x=result['voltage_and_current_extrema'][n];rail[n]=dict(x,below_ground_V=max(0.,-x['min']),above_VDD_V=max(0.,x['max']-cfg['supply_V']))
    work.update(source_minus_L0_load_work_J=work['L0_net_delivered_J']-work['L0_gate_port_work_J'],
        X025_to_A_internal_work_residual_J=work['X025_to_PRE_internal_work_J']-work['PRE_A_gate_internal_work_J'],
        accounting='L0 ideal source work, internal PRE transfer and VDD supply energy are separate, never summed. Internal PRE work is not another external supply.')
    loads['L0_shared']['gate_port_branches']=l0_branches
    loads['PRE_A_gates']['gate_port_branches']=['xdut.gnnan:2','xdut.gnnap:2']
    m.update(restored_stage_direct_VDD_energy_J=energies,real_PRE_and_L0_loads=loads,source_and_internal_work=work,
        actual_stage_timing=timing,actual_same_side_control_gaps=gaps,opposed_reference_terminal_current=opposed,correct_ON_settling=on,
        body_forward_polarity=body,supply_rail_excursions=rail,
        control_overlap_note='VDD/2 control gaps/skew are timing diagnostics, not MOS conduction thresholds. Opposed total drain currents include displacement and do not prove shoot-through.',
        body_note='Positive signed junction voltage is forward polarity; no threshold/current-fraction claim. Body port current is total native port4; unavailable coincident samples stay null.',
        boundary='Physical core X025 plus one IO GPP inverter/shared L0 load; true BBM source omitted. Driver implementation changes count/parasitics together, no full chain acceptance.')
    return m


def analyze(run,out):
    cfg=cell.base.read_json(cell.base.safe_file(os.path.realpath(run),'inputs/measurement.json'));validate(cfg);old_v,old_m=cell.validate,cell.metrics
    try:
        cell.validate=validate;cell.metrics=lambda r,c,p:measurements(old_m,r,c,p)
        return cell.analyze(run,out)
    finally:cell.validate,cell.metrics=old_v,old_m


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('GPP_SINGLE_IO_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')


if __name__=='__main__':main()
