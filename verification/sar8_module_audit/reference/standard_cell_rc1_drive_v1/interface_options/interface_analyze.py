"""Loaded analog RC interface experiment; actual ports, no automatic qualification."""
from __future__ import print_function
import argparse,gzip,os,struct
import io_cell_analyze as cell
import standard_cell_bbm_analyze as standard
from standard_cell_bbm_hlswap_analyze import full_stress_time
VARIANT='HD_RC1_IO_clear_receiver_passive_guard_topology_v1'


def validate(cfg):
    norm=cell.base.norm
    v=list(map(norm,cfg['voltage_saves']));i=list(map(norm,cfg['current_saves']))
    cat=dict((norm(n),x) for n,x in cfg['terminal_current_catalog'].items())
    eq=dict((norm(n),list(map(norm,q))) for n,q in cfg['kcl_terms'].items())
    if len(set(v))!=len(v) or len(set(i))!=len(i) or set(v)&set(i) or set(cat)!=set(i):raise ValueError('Unique actual save/catalog required')
    inv=cfg['boundary_inventory']
    if (len(v),len(i),len(eq))!=(inv['voltage_count'],inv['mandatory_currents'],inv['KCL_nodes']):raise ValueError('Inventory mismatch')
    if (inv['all_actual_MOS'],inv['all_primitives'],inv['native_library_MOS'],inv['BBM_primitive_count'])!=(123,201,40,45):raise ValueError('Exact interface inventory required')
    for n,terms in eq.items():
        if not terms or len(set(terms))!=len(terms) or set(terms)!=set(b for b,x in cat.items() if norm(x['node'])==n):raise ValueError('Incomplete incidence '+n)
    if set(eq)!=set(map(norm,cfg['required_kcl_nodes'])):raise ValueError('KCL domain mismatch')
    need=set(eq)|set(map(norm,cfg['diagnostic_voltage_columns']+cfg['edge_nodes']+list(cfg['initial_witness_v'])))
    pairs=cfg['selected_mos_pair_screens'];keys=set()
    for p in pairs:
        key=p['instance']+':'+p['terminal'];keys.add(key)
        if p['screen_v']!=(.99 if p['model'] in ['nch_mac','pch_mac'] else 1.98):raise ValueError('Actual-model screen changed')
        a,b=p['terminal'];ports=dict((z,cat[norm(p['instance']+':'+str(j))]['node']) for j,z in enumerate('dgsb',1))
        if p['nodes']!=[ports[a],ports[b]]:raise ValueError('Actual terminal pair map differs')
        need.update(norm(n) for n in p['nodes'] if n!='0')
    if len(pairs)!=738 or len(keys)!=738 or not need<=set(v) or set(map(norm,cfg['diagnostic_voltage_columns']))!=set(v):raise ValueError('Complete voltage/738 actual pair coverage required')
    if cfg['variant']!=VARIANT or cfg['source_node']!='code' or cfg['source_current']!='vcode:1':raise ValueError('One topology/CODE fixture required')
    if cfg['source_peaks'] or cfg['diagnostic_start_s']!=0 or cfg['diagnostic_stop_s']!=52e-9 or cfg['max_total_output_bytes']!=30*cell.MIB:raise ValueError('Full52ns/fixed budget required')
    if any(n.startswith(('vl0:','vl0n:','vgnp:','vgpn:','vpre:','vgpp:')) for n in i):raise ValueError('Ideal internal force forbidden')
    delta=cfg['interface_delta']
    if not delta['all192_other_leaf_records_exact'] or not delta['all_outside_HD_exact'] or not delta['all_pure_digital_masters_exact']:raise ValueError('Frozen exterior changed')
    stem='XDUT.XBBM0.XD_HD.'
    for name,model,nodes in [('MP_CLEAR','pch_18_mac',[stem+'RC1',stem+'CLEAR_G','VDD!','VDD!']),
            ('X005.MN_IO','nch_18_mac',[stem+'HD_RAW',stem+'RC1','0','0']),
            ('X005.MP_IO','pch_18_mac',[stem+'HD_RAW',stem+'RC1','VDD!','VDD!'])]:
        for j,node in enumerate(nodes,1):
            q=cat[norm(stem+name+':'+str(j))]
            if q['model']!=model or q['node']!=node:raise ValueError('Actual IO template/body mapping differs')
    for node in cfg['interface_nodes']:
        if node not in eq or not set(eq[node])<=set(cfg['diagnostic_current_columns']):raise ValueError('Interface actual native currents absent')
    return sorted(v+i),sorted(i),eq


def interface_metrics(result,cfg,out):
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz')
    cols=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(cols))
    eq=dict((n.lower(),[b.lower() for b in q]) for n,q in cfg['kcl_terms'].items())
    phases=[('full',0.,52e-9),('CODE_rise',42.995e-9,47.995e-9),('CODE_fall',47.995e-9,52e-9)]
    nodes={}
    for n in cfg['interface_nodes']:
        nodes[n]=dict(actual_incident_ports=eq[n],phases=dict((name,dict(samples=0,max_KCL_A=0.,
            signed_charge_C=dict((b,0.) for b in eq[n]),absolute_charge_C=dict((b,0.) for b in eq[n]))) for name,a,b in phases),
            min_V=None,max_V=None,min_snapshot=None,max_snapshot=None)
    resets={}
    for name,target in [('xdut.xbbm0.xd_hd.rc0',0.),('xdut.xbbm0.xd_hd.rc1',cfg['supply_V'])]:
        resets[name]=dict(target_V=target,samples=0,last_native_s=None,final_error_V=None,last_outside_1percent_s=None,remained_inside_from_native_s=None)
    static={p['name']:dict(samples=0,first_s=None,last_s=None,total_VDD_work_J=0.,native_NAND_VDD_work_J=0.,HD_interface_VDD_work_J=0.,
        guard_resistor_dissipation_J=0.,HD_min_V=None,HD_max_V=None,HD_RAW_min_V=None,HD_RAW_max_V=None) for p in cfg['static_windows']}
    nand=[b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['instance'].startswith('XDUT.XBBM0.X002.X000.XLIB.') and x['node']=='VDD!']
    interface_VDD=[b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node']=='VDD!' and
        x['instance'] in ['XDUT.XBBM0.XD_HD.MP_CLEAR','XDUT.XBBM0.XD_HD.X005.MP_IO','XDUT.XBBM0.XD_HD.R_GUP1']]
    resistor_ports=[]
    for n in cfg['interface_passive_resistors']:
        ports=[cfg['terminal_current_catalog'][next(k for k in cfg['terminal_current_catalog'] if k.lower()==n+':'+str(j))]['node'].lower() for j in [1,2]]
        resistor_ports.append((n+':1',ports))
    def val(row,n):return 0. if n=='0' else row[cols[n]]
    def power(row):
        supply=row[cols['vdd!']]
        diss=sum(row[cols[b]]*(val(row,ns[0])-val(row,ns[1])) for b,ns in resistor_ports)
        return [-supply*row[cols['vvdd:1']],supply*sum(row[cols[b]] for b in nand),diss,
            supply*sum(row[cols[b]] for b in interface_VDD)]
    prev=None;count=0
    with gzip.open(os.path.join(out,e['file']),'rb') as f:
        while True:
            raw=f.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Partial interface row')
            row=fmt.unpack(raw);t=row[0];count+=1
            for n,q in nodes.items():
                value=row[cols[n]]
                witness=dict(time_s=t,voltage_V=value,concurrent_V=dict((x,row[cols[x]]) for x in cfg['interface_nodes']),
                    actual_port_current_A=dict((b,row[cols[b]]) for b in eq[n]))
                for extreme in ['min','max']:
                    if q[extreme+'_V'] is None or (value<q[extreme+'_V'] if extreme=='min' else value>q[extreme+'_V']):q[extreme+'_V']=value;q[extreme+'_snapshot']=witness
                for name,a,b in phases:
                    s=q['phases'][name]
                    if a<=t<=b:s['samples']+=1;s['max_KCL_A']=max(s['max_KCL_A'],abs(sum(row[cols[x]] for x in eq[n])))
                    if prev is not None:
                        left=max(prev[0],a);right=min(t,b)
                        if right>left:
                            for branch in eq[n]:
                                x0=prev[cols[branch]];x1=row[cols[branch]]
                                x=x0+(x1-x0)*(left-prev[0])/(t-prev[0]);y=x0+(x1-x0)*(right-prev[0])/(t-prev[0])
                                s['signed_charge_C'][branch]+=(x+y)*(right-left)*.5
                                s['absolute_charge_C'][branch]+=(abs(x)+abs(y))*(right-left)*.5 if x*y>=0 else (x*x+y*y)/(abs(x)+abs(y))*(right-left)*.5
            if 48.005e-9<=t<=52e-9:
                for n,q in resets.items():
                    err=row[cols[n]]-q['target_V'];q['samples']+=1;q['last_native_s']=t;q['final_error_V']=err
                    if abs(err)>cfg['supply_V']*.01:q['last_outside_1percent_s']=t;q['remained_inside_from_native_s']=None
                    elif q['remained_inside_from_native_s'] is None:q['remained_inside_from_native_s']=t
            for p in cfg['static_windows']:
                q=static[p['name']];a,b=p['start_s'],p['stop_s']
                if a<=t<=b:
                    q['samples']+=1;q['last_s']=t
                    if q['first_s'] is None:q['first_s']=t
                    for label,node in [('HD','xdut.xbbm0.hd'),('HD_RAW','xdut.xbbm0.xd_hd.hd_raw'),
                            ('NAND_N','xdut.xbbm0.x002.n'),('H0','xdut.h0'),('L0','xdut.l0')]:
                        value=row[cols[node]]
                        for extreme in ['min','max']:
                            k=label+'_'+extreme+'_V'
                            q[k]=value if q.get(k) is None else (min(q[k],value) if extreme=='min' else max(q[k],value))
                if prev is not None:
                    left=max(prev[0],a);right=min(t,b)
                    if right>left:
                        pv=power(prev);rv=power(row)
                        for j,k in enumerate(['total_VDD_work_J','native_NAND_VDD_work_J','guard_resistor_dissipation_J','HD_interface_VDD_work_J']):
                            x=pv[j]+(rv[j]-pv[j])*(left-prev[0])/(t-prev[0]);y=pv[j]+(rv[j]-pv[j])*(right-prev[0])/(t-prev[0])
                            q[k]+=(x+y)*(right-left)*.5
            prev=row
    if count!=e['rows']:raise ValueError('Native row count mismatch')
    for q in resets.values():
        t=q['remained_inside_from_native_s'];q['diagnostic_reset_complete']=None if not q['samples'] else t is not None
        q['delay_from_CODE_midpoint_s']=None if t is None else t-48e-9
    for p in cfg['static_windows']:
        q=static[p['name']];span=p['stop_s']-p['start_s']
        for k in ['total_VDD_work_J','native_NAND_VDD_work_J','guard_resistor_dissipation_J','HD_interface_VDD_work_J']:q[k.replace('work_J','mean_power_W').replace('dissipation_J','mean_dissipation_W')]=q[k]/span
        for label in ['total','native_NAND','HD_interface']:q[label+'_mean_VDD_current_A']=q[label+'_VDD_mean_power_W']/cfg['supply_V']
        q['native_NAND_required_output_logic']=0 if p['name']=='high' else 1
        q['H0_required_output_logic']=1 if p['name']=='high' else 0
        target=cfg['supply_V'] if p['name']=='high' else 0.
        q['original_full_swing_HD_target_V']=target
        q['original_full_swing_HD_max_error_V']=None if not q['samples'] else max(abs(q['HD_min_V']-target),abs(q['HD_max_V']-target))
        q['original_full_swing_HD_1percent_met']=None if not q['samples'] else q['original_full_swing_HD_max_error_V']<=cfg['supply_V']*.01
        q['library_VIH_VIL_qualification']='unknown; no verified library DC input/noise-margin condition supplied'
    return dict(nodes=nodes,HD_RC_reset_nodes=resets,static_windows=static,native_points=count,
        HD_interface_actual_VDD_ports=interface_VDD,native_NAND_actual_VDD_ports=nand,
        HD_interface_direct_VDD_energy_J=cfg['supply_V']*sum(result['current_charge_trapezoids'][b]['signed_C'] for b in interface_VDD),
        native_NAND_direct_VDD_energy_J=cfg['supply_V']*sum(result['current_charge_trapezoids'][b]['signed_C'] for b in nand),
        HD_guard_reset_note='HD is now a loaded analog input. Original zero-rail reset contract is retained separately, not satisfied by renaming its target. Judge actual H/L logic, edge uniqueness, non-overlap and reference settling separately. Quarter/threequarter levels are stiff-source estimates only; VIH/VIL remains unknown.',
        interpretation='Actual total ports including displacement. Charges clipped on native linear segments; no intrinsic fractions. Static bias and native NAND current explicitly included; no stress or logic acceptance inferred.')


def measurements(original,result,cfg,out):
    m=standard.measurements(original,result,cfg,out)
    # Retain the original independent target, distinguish it from RC-node reset,
    # and never substitute the measured DC endpoint as a functional target.
    m['original_full_swing_HD_reset_contract']=m['delay_leg_reset_diagnostics']['HD']['nodes'].pop('xdut.xbbm0.hd')
    m['interface_measurements']=interface_metrics(result,cfg,out)
    m['all_terminal_native_phase_time']=full_stress_time(result,cfg,out)
    m['all_terminal_native_phase_time']['interpretation']=m['all_terminal_native_phase_time']['interpretation'].replace('All738','All738 actual current-topology')
    m['boundary']=cfg['scope']
    m['interface_factor']=cfg['interface_delta']['factor']
    return m


def analyze(run,out):
    old_v,old_m=cell.validate,cell.metrics
    try:
        cell.validate=validate;cell.metrics=lambda r,c,p:measurements(old_m,r,c,p)
        return cell.analyze(run,out)
    finally:cell.validate,cell.metrics=old_v,old_m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if os.name=='posix':
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('HD_INTERFACE_DIAGNOSTIC_READY',r['native_points'],'acceptance_pass=null')
