"""Verified HD X005 D1P25 master; complete dynamic native measurement mapping."""
from __future__ import print_function
import argparse,gzip,os,struct
import io_cell_analyze as cell
import standard_cell_bbm_analyze as standard
from standard_cell_bbm_hlswap_analyze import full_stress_time
from rc1_drive_event_measure import measure

VARIANT='HD_X005_verified_native_INVD1P25_with_HD_clear_gate_R_ideal_CODE'


def validate(cfg):
    norm=cell.base.norm
    v=[norm(n) for n in cfg['voltage_saves']];i=[norm(n) for n in cfg['current_saves']]
    cat=dict((norm(n),x) for n,x in cfg['terminal_current_catalog'].items())
    eq=dict((norm(n),[norm(b) for b in terms]) for n,terms in cfg['kcl_terms'].items())
    inv=cfg['boundary_inventory']
    if len(set(v))!=len(v) or len(set(i))!=len(i) or set(v)&set(i) or set(cat)!=set(i):raise ValueError('Unique complete actual save/current catalog required')
    if (len(v),len(i),len(eq))!=(117,662,37) or inv['all_actual_MOS']!=125 or inv['all_primitives']!=197 or inv['BBM_primitive_count']!=41 or inv['native_library_MOS']!=44:raise ValueError('Verified D1P25 actual inventory differs')
    if inv['voltage_count']!=len(v) or inv['mandatory_currents']!=len(i) or inv['KCL_nodes']!=len(eq):raise ValueError('Inventory coverage mismatch')
    for n,terms in eq.items():
        expected=set(b for b,x in cat.items() if norm(x['node'])==n)
        if not terms or len(set(terms))!=len(terms) or set(terms)!=expected:raise ValueError('Complete actual current incidence missing '+n)
    if set(eq)!=set(norm(n) for n in cfg['required_kcl_nodes']):raise ValueError('KCL domain differs')
    need=set(eq)|set(norm(n) for n in cfg['diagnostic_voltage_columns']+cfg['edge_nodes']+list(cfg['initial_witness_v']))
    need|=set(norm(n) for p in cfg['selected_mos_pair_screens'] for n in p['nodes'])-set(['0'])
    if not need<=set(v) or set(map(norm,cfg['diagnostic_voltage_columns']))!=set(v):raise ValueError('Full native voltage coverage required')
    screens=cfg['selected_mos_pair_screens']
    if len(screens)!=750 or len(set(p['instance']+':'+p['terminal'] for p in screens))!=750:raise ValueError('All125 MOS750 physical pairs required')
    for p in screens:
        if p['screen_v']!=(.99 if p['model'] in ['nch_mac','pch_mac'] else 1.98):raise ValueError('Actual model screen changed')
    if cfg['variant']!=VARIANT or cfg['source_node']!='code' or cfg['source_current']!='vcode:1':raise ValueError('Native drive/ideal CODE boundary required')
    if any(n.startswith(('vl0:','vl0n:','vgnp:','vgpn:','vpre:','vgpp:')) for n in i):raise ValueError('Ideal internal force forbidden')
    if any(len(eq[n])!=6 for n in ['xdut.h0','xdut.l0']) or len(eq['code'])!=9 or len(eq['xdut.xbbm0.hd'])!=6:raise ValueError('Actual native loads/source fanout differs')
    if cfg['source_peaks'] or cfg['diagnostic_start_s']!=0 or cfg['diagnostic_stop_s']!=52e-9 or cfg['max_total_output_bytes']!=30*cell.MIB:raise ValueError('Full52ns/fixed byte budget required')
    q=cfg['single_HD_X005_native_drive']
    if q['old_cell']!='INVD1BWP12T30P140' or q['new_cell']!='INVD1P25BWP12T30P140' or q['target']!='XDUT.XBBM0.XD_HD.X005.XLIB' or not q['all193_other_leaf_records_exact']:raise ValueError('Only verified native master replacement permitted')
    stem='XDUT.XBBM0.XD_HD.X005.XLIB.'
    for mos,model in [('MM3_1','nch_mac'),('MM3_2','nch_mac'),('MM2_1','pch_mac'),('MM2_2','pch_mac')]:
        expected=['XDUT.XBBM0.HD','XDUT.XBBM0.XD_HD.RC1','0' if model=='nch_mac' else 'VDD!','0' if model=='nch_mac' else 'VDD!']
        for port,node in enumerate(expected,1):
            c=cat[norm(stem+mos+':'+str(port))]
            if c['node']!=node or c['model']!=model:raise ValueError('Actual D1P25 pin/body map differs')
    for leg,count in [('hd',4),('ld',2)]:
        branches=cfg['receiver_gate_current_branches_by_leg'][leg]
        if len(branches)!=count or not set(branches)<=set(i):raise ValueError('Actual receiver gate current coverage differs')
    if len(eq['xdut.xbbm0.xd_hd.rc1'])!=7:raise ValueError('Actual D1P25 RC1 incidence incomplete')
    for q in cfg['driver_source_ports'].values():
        branches=q['source_port_branches']
        if len(branches)!=2 or not set(branches)<=set(i):raise ValueError('Actual retained driver output currents missing')
        if any(cat[n]['port']!=1 or norm(cat[n]['node'])!=q['node'] for n in branches):raise ValueError('Retained driver output binding differs')
    groups=cfg['HD_actual_port_groups']
    if len(groups['X005_output_D'])!=4 or len(groups['NAND_input_G'])!=2 or set(sum(groups.values(),[]))!=set(eq['xdut.xbbm0.hd']):raise ValueError('Complete actual HD backflow incidence required')
    equivalent=cfg['baseline_equivalent_terminal_groups'];specs=dict((p['instance']+':'+p['terminal'],p) for p in screens)
    flattened=[key for group in equivalent.values() for key in group]
    if len(equivalent)!=738 or len(flattened)!=750 or len(set(flattened))!=750 or set(flattened)!=set(specs):raise ValueError('Complete125-MOS physical/baseline equivalent group coverage required')
    for group in equivalent.values():
        if len(group) not in [1,2]:raise ValueError('Only verified parallel native MOS pairs may be grouped')
        a=specs[group[0]]
        if any((specs[k]['model'],specs[k]['nodes'],specs[k]['screen_v'])!=(a['model'],a['nodes'],a['screen_v']) for k in group):raise ValueError('Parallel voltage-equivalence not established')
    return sorted(v+i),sorted(i),eq


def HD_exchange(result,cfg,out):
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz')
    c=dict((n,i) for i,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    groups=cfg['HD_actual_port_groups'];windows=[('full',0.,52e-9),('CODE_rise',42.995e-9,47.995e-9),('CODE_fall',47.995e-9,52e-9)]
    phases=dict((name,dict(requested_s=[a,b],samples=0,first_native_s=None,last_native_s=None,max_KCL_A=0.,
        signed_charge_C=dict((k,0.) for k in groups),absolute_net_charge_C=dict((k,0.) for k in groups),
        current_min_A=dict((k,None) for k in groups),current_max_A=dict((k,None) for k in groups))) for name,a,b in windows)
    previous=None;count=0
    with gzip.open(os.path.join(out,e['file']),'rb') as f:
        while True:
            raw=f.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Partial native HD row')
            row=fmt.unpack(raw);t=row[0];count+=1
            values=dict((k,sum(row[c[n]] for n in bs)) for k,bs in groups.items())
            for name,a,b in windows:
                q=phases[name]
                if a<=t<=b:
                    q['samples']+=1;q['last_native_s']=t
                    if q['first_native_s'] is None:q['first_native_s']=t
                    q['max_KCL_A']=max(q['max_KCL_A'],abs(sum(values.values())))
                    for k,v in values.items():
                        q['current_min_A'][k]=v if q['current_min_A'][k] is None else min(v,q['current_min_A'][k])
                        q['current_max_A'][k]=v if q['current_max_A'][k] is None else max(v,q['current_max_A'][k])
                if previous is not None:
                    pt,pv=previous;left=max(pt,a);right=min(t,b)
                    if right>left:
                        for k,v in values.items():
                            x=pv[k]+(v-pv[k])*(left-pt)/(t-pt);y=pv[k]+(v-pv[k])*(right-pt)/(t-pt)
                            q['signed_charge_C'][k]+=(x+y)*(right-left)*.5
                            # Integrate |linear current| exactly if it crosses0.
                            integral=(abs(x)+abs(y))*(right-left)*.5 if x*y>=0 else (x*x+y*y)/(abs(x)+abs(y))*(right-left)*.5
                            q['absolute_net_charge_C'][k]+=integral
            previous=(t,values)
    if count!=e['rows']:raise ValueError('HD native row mismatch')
    return dict(actual_port_groups=groups,phases=phases,native_points=count,
        interpretation='Positive into components. Actual four native D1P25 drain ports and two downstream NAND gate ports; signed/absolute total port exchange, no intrinsic fractions. Phase boundaries clipped on native linear segments.')


def measurements(original,result,cfg,out):
    m=standard.measurements(original,result,cfg,out)
    full=full_stress_time(result,cfg,out)
    full['interpretation']=full['interpretation'].replace('All738','All750')
    equivalent={}
    for name,phase in full['phases'].items():
        values={}
        for key,group in cfg['baseline_equivalent_terminal_groups'].items():
            members=[phase['pairs'][p] for p in group]
            if any((q['min_V'],q['max_V'],q['strict_native_exceed'])!=(members[0]['min_V'],members[0]['max_V'],members[0]['strict_native_exceed']) for q in members):raise ValueError('Native parallel voltage grouping differs')
            values[key]=members[0]['strict_native_exceed']
        equivalent[name]=dict(baseline_group_count=738,actual_physical_pair_count=750,
            strict_equivalent_group_count=sum(values.values()),actual_strict_physical_pair_count=phase['strict_native_pair_count'],
            note='Additional fair-count comparison only; all750 physical screens/extrema/durations retained. Parallel D1P25 members share verified endpoint/model/limit tuples.')
    m.update(single_HD_X005_native_drive=cfg['single_HD_X005_native_drive'],
        all_terminal_native_phase_time=full,
        baseline_equivalent_terminal_counts=equivalent,
        RC1_actual_native_event_charge=measure(result,cfg,out),
        HD_actual_native_port_exchange=HD_exchange(result,cfg,out),
        boundary='Only verified native HD.X005 INVD1-to-INVD1P25, gate-R/LD/other193 leaf records and external stimulus exact. Actual125MOS750screens662currents; no ADC or stress pass.')
    return m


def analyze(run,out):
    old_v,old_m,old_b=cell.validate,cell.metrics,cell.base.Budget
    class DriveBudget(old_b):
        def json(self,name,value):
            if name=='result.json':value['waveform_note']='Full117 voltages, actual662 currents/all37 KCL;125 actual MOS750 pairs; verified D1P25 parallel MOS, original native time, no edge alignment.'
            return old_b.json(self,name,value)
    try:
        cell.validate=validate;cell.metrics=lambda r,c,p:measurements(old_m,r,c,p);cell.base.Budget=DriveBudget
        return cell.analyze(run,out)
    finally:cell.validate,cell.metrics,cell.base.Budget=old_v,old_m,old_b


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if os.name=='posix':
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('VERIFIED_HD_NATIVE_DRIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')

