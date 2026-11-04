"""Actual GNN/PRE and reference-port diagnostics. Python2.7/3; no Vth model."""
from __future__ import print_function
import gzip,os,struct


def measure(result,cfg,out):
    e=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz')
    c=dict((n,j) for j,n in enumerate(e['columns']));fmt=struct.Struct('<'+'d'*len(c))
    cat=dict((b.lower(),x) for b,x in cfg['terminal_current_catalog'].items())
    path=cfg['gnn_path_nodes'];stages={}
    for name,a,b in [('turn_low_ref_off',42.995e-9,47.995e-9),('turn_low_ref_on',47.995e-9,52e-9)]:
        events={}
        for n in path:
            q=[x for x in result['half_vdd_events'].get(n,[]) if a<=x['estimated_time_s']<b]
            events[n]=q[0] if len(q)==1 else None
        stages[name]=dict(actual_halfVDD_events=events,missing_or_ambiguous=[n for n,q in events.items() if q is None],
            adjacent_delays_s=dict((u+' -> '+v,None if events[u] is None or events[v] is None else events[v]['estimated_time_s']-events[u]['estimated_time_s']) for u,v in zip(path[:-1],path[1:])),
            diagnostic_not_channel_timing=True)
    pre_load=[b for b,x in cat.items() if x['node']=='XDUT.PRE' and x['port']==2]
    pre_source=[b for b,x in cat.items() if x['node']=='XDUT.PRE' and x['port']==1]
    assert set(pre_load)==set(['xdut.gnncn:2','xdut.gnncp:2'])
    assert set(pre_source)==set(['xdut.x025.xlib.mm1:1','xdut.x025.xlib.mm0:1'])
    phases=[('select_high',42.995e-9,47.995e-9),('select_low',47.995e-9,52e-9)]
    branches=[]
    for side in ['n','p']:
        for device in ['mn_low','mp_high']:
            branches.extend('xdut.xcdac.xs'+side+'0.'+device+':'+str(j) for j in [1,2,3,4])
    phase={name:dict(samples=0,source_exchange={side:dict(peak_A=None,peak=None,native_metric_integral_C=0.) for side in ['N','P']},
        opposed_D={side:dict(peak_A=None,peak=None) for side in ['N','P']},
        signed_terminal_charge_C=dict((b,0.) for b in branches),PRE_load_signed_C=0.,PRE_load_absolute_C=0.) for name,a,b in phases}
    def val(row,node):return 0. if node=='0' else row[c[node.lower()]]
    def snap(row,side):
        devices={}
        for dev in ['mn_low','mp_high']:
            inst='xdut.xcdac.xs'+side.lower()+'0.'+dev
            vs=dict((port,val(row,cat[inst+':'+str(j)]['node'])) for j,port in enumerate('DGSB',1))
            devices[dev]=dict(DGSB_V=vs,DGSB_current_A=dict((port,row[c[inst+':'+str(j)]]) for j,port in enumerate('DGSB',1)),
                declared_Vgs_V=vs['G']-vs['S'],declared_Vsg_V=vs['S']-vs['G'],intrinsic_conduction_current_A=None)
        bot='XDUT.XCDAC.B'+side+'0';terms=cfg['kcl_terms'][bot]
        return dict(time_s=row[0],devices=devices,bottom_V=val(row,bot),
            bottom_actual_port_current_A=dict((b,row[c[b.lower()]]) for b in terms),
            bottom_KCL_A=sum(row[c[b.lower()]] for b in terms))
    targeted={}
    for instance in ['XDUT.GNNCN','XDUT.GNNCP','XDUT.X025.XLIB.MM1','XDUT.X025.XLIB.MM0']:
        options=[(max(abs(x['min']),abs(x['max'])),key,x) for key,x in result['selected_mos_pair_extrema'].items() if key.startswith(instance+':')]
        peak,key,x=max(options,key=lambda z:z[0]);at=x['max_time_s'] if abs(x['max'])>=abs(x['min']) else x['min_time_s']
        targeted[instance]=dict(worst_pair=key,abs_peak_V=peak,time_s=at,coincident=None)
    startup_nodes=['xdut.pre','xdut.gnndrv','xdut.gnn0','xdut.h0','xdut.l0','xdut.xcdac.bn0','xdut.xcdac.bp0']
    startup=dict(interval_s=[0.,42.995e-9],samples=0,node_min_V={},node_max_V={},
        H_L_halfVDD_events=dict((n,[x for x in result['half_vdd_events'].get(n,[]) if x['estimated_time_s']<42.995e-9]) for n in ['xdut.h0','xdut.l0']),
        only_existing_DC_initialized_history=True,physical_supply_ramp_startup_qualified=False)
    pre_ext=dict(min_V=None,max_V=None,min_snapshot=None,max_snapshot=None)
    load=dict(actual_PRE_load_ports=pre_load,actual_X025_output_ports=pre_source,full_load_signed_C=0.,full_load_absolute_C=0.,
        X025_delivered_internal_work_J=0.,PRE_gate_load_internal_work_J=0.,max_PRE_KCL_A=0.,min_load_A=None,max_load_A=None,
        min_load_time_s=None,max_load_time_s=None)
    max_bottom={side:0. for side in ['N','P']};prev=None;prev_metrics=None;count=0
    def metrics(row):
        out={}
        for side in ['N','P']:
            stem='xdut.xcdac.xs'+side.lower()+'0.'
            dn,dp=row[c[stem+'mn_low:1']],row[c[stem+'mp_high:1']]
            sn,sp=row[c[stem+'mn_low:3']],row[c[stem+'mp_high:3']]
            out[side]=(min(max(sp,0.),max(-sn,0.)),min(abs(dn),abs(dp)) if dn*dp<0 else 0.)
        return out
    def integrate_segment(x0,x1,t0,t1,a,b):
        left=max(t0,a);right=min(t1,b)
        if right<=left:return 0.
        u=x0+(x1-x0)*(left-t0)/(t1-t0);v=x0+(x1-x0)*(right-t0)/(t1-t0)
        return (u+v)*(right-left)*.5
    def integrate_abs_segment(x0,x1,t0,t1,a,b):
        left=max(t0,a);right=min(t1,b)
        if right<=left:return 0.
        u=x0+(x1-x0)*(left-t0)/(t1-t0);v=x0+(x1-x0)*(right-t0)/(t1-t0)
        return (abs(u)+abs(v))*(right-left)*.5 if u*v>=0 else (u*u+v*v)/(abs(u)+abs(v))*(right-left)*.5
    with gzip.open(os.path.join(out,e['file']),'rb') as f:
        while True:
            raw=f.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Partial GNN measurement row')
            row=fmt.unpack(raw);t=row[0];count+=1;now=metrics(row)
            li=sum(row[c[b]] for b in pre_load);si=sum(row[c[b]] for b in pre_source);vp=row[c['xdut.pre']]
            load['max_PRE_KCL_A']=max(load['max_PRE_KCL_A'],abs(li+si))
            for kind in ['min','max']:
                if load[kind+'_load_A'] is None or (li<load[kind+'_load_A'] if kind=='min' else li>load[kind+'_load_A']):
                    load[kind+'_load_A']=li;load[kind+'_load_time_s']=t
            for kind in ['min','max']:
                if pre_ext[kind+'_V'] is None or (vp<pre_ext[kind+'_V'] if kind=='min' else vp>pre_ext[kind+'_V']):
                    pre_ext[kind+'_V']=vp;pre_ext[kind+'_snapshot']=dict(time_s=t,PRE_V=vp,
                        actual_X025_output_current_A=dict((b,row[c[b]]) for b in pre_source),
                        actual_GNN_gate_current_A=dict((b,row[c[b]]) for b in pre_load))
            for side in ['N','P']:
                terms=cfg['kcl_terms']['XDUT.XCDAC.B'+side+'0']
                max_bottom[side]=max(max_bottom[side],abs(sum(row[c[b.lower()]] for b in terms)))
            if t<=42.995e-9:
                startup['samples']+=1
                for n in startup_nodes:
                    v=row[c[n]];startup['node_min_V'][n]=v if n not in startup['node_min_V'] else min(v,startup['node_min_V'][n]);startup['node_max_V'][n]=v if n not in startup['node_max_V'] else max(v,startup['node_max_V'][n])
            for instance,q in targeted.items():
                if abs(t-q['time_s'])<1e-18:
                    lo=instance.lower();ports=[cat[lo+':'+str(j)]['node'] for j in [1,2,3,4]]
                    q['coincident']=dict(DGSB_V=dict((p,val(row,n)) for p,n in zip('DGSB',ports)),
                        DGSB_current_A=dict((p,row[c[lo+':'+str(j)]]) for j,p in enumerate('DGSB',1)),PRE_V=vp,GNNDRV_V=row[c['xdut.gnndrv']])
            for name,a,b in phases:
                q=phase[name]
                if a<=t and (t<b if name=='select_high' else t<=b):
                    q['samples']+=1
                    for side in ['N','P']:
                        for index,field in [(0,'source_exchange'),(1,'opposed_D')]:
                            s=q[field][side]
                            if s['peak_A'] is None or now[side][index]>s['peak_A']:s['peak_A']=now[side][index];s['peak']=snap(row,side)
                if prev is not None:
                    pt=prev[0]
                    for side in ['N','P']:q['source_exchange'][side]['native_metric_integral_C']+=integrate_segment(prev_metrics[side][0],now[side][0],pt,t,a,b)
                    for branch in branches:q['signed_terminal_charge_C'][branch]+=integrate_segment(prev[c[branch]],row[c[branch]],pt,t,a,b)
                    old_li=sum(prev[c[x]] for x in pre_load)
                    q['PRE_load_signed_C']+=integrate_segment(old_li,li,pt,t,a,b)
                    q['PRE_load_absolute_C']+=integrate_abs_segment(old_li,li,pt,t,a,b)
            if prev is not None:
                pt=prev[0];dt=t-pt;old_li=sum(prev[c[b]] for b in pre_load);old_si=sum(prev[c[b]] for b in pre_source);old_v=prev[c['xdut.pre']]
                load['full_load_signed_C']+=(old_li+li)*dt*.5;load['full_load_absolute_C']+=integrate_abs_segment(old_li,li,pt,t,pt,t)
                load['X025_delivered_internal_work_J']+=(-old_v*old_si-vp*si)*dt*.5
                load['PRE_gate_load_internal_work_J']+=(old_v*old_li+vp*li)*dt*.5
            prev=row;prev_metrics=now
    if count!=e['rows'] or any(not q['samples'] for q in phase.values()):raise ValueError('Missing full history or handoff phase')
    if any(q['coincident'] is None for q in targeted.values()):raise ValueError('Targeted native peak missing')
    load['internal_work_closure_residual_J']=load['X025_delivered_internal_work_J']-load['PRE_gate_load_internal_work_J']
    return dict(native_points=count,path_diagnostics=stages,PRE_load_and_internal_work=load,PRE_kickback=pre_ext,
        actual_final_IO_and_X025_terminal_peaks=targeted,reference_port_phases=phase,max_bottom_KCL_A=max_bottom,startup_history=startup,
        interpretation='Actual total D/G/S/B include displacement. Source exchange and opposed D are port diagnostics, not pure-channel current or on/off proof. Phase source metric integration is native trapezoid/clipped-boundary diagnostic. No removed-stage aliases or assumed Vth.',
        channel_overlap_duration_s=None,channel_deadtime_s=None)
