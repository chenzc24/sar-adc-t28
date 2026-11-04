"""Native RC1 event currents with verified actual receiver gate lists. Python2.7/3."""
from __future__ import print_function
import gzip,os,struct

EVENTS=[('HD_positive','hd',True,43e-9),('LD_negative','ld',False,43e-9),
        ('LD_positive','ld',True,48e-9),('HD_negative','hd',False,48e-9)]


def measure(result,cfg,out):
    e=next(q for q in result['native_exports'] if q['file']=='cell.native.f64le.gz')
    columns=e['columns'];ids=dict((n,i) for i,n in enumerate(columns))
    wanted=set(['time','vdd!'])
    for leg in ['hd','ld']:
        stem='xdut.xbbm0.xd_'+leg+'.'
        wanted.update([stem+'rc1',stem+'b','xdut.xbbm0.'+leg,
                       stem+'c1:1',stem+'r1:1',stem+'r1:2'])
        wanted.update(cfg['receiver_gate_current_branches_by_leg'][leg])
        wanted.update(stem+'mp_clear:'+str(j) for j in [1,2,3,4])
        gate=cfg['terminal_current_catalog']['XDUT.XBBM0.XD_'+leg.upper()+'.MP_CLEAR:2']['node'].lower()
        wanted.add(gate)
        incident=set(b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node'].lower()==stem+'rc1')
        expected=set([stem+'mp_clear:1',stem+'c1:1',stem+'r1:2']+cfg['receiver_gate_current_branches_by_leg'][leg])
        if incident!=expected:raise ValueError('Actual RC1 incidence differs '+leg)
    if not wanted<=set(ids):raise ValueError('RC1 native port/voltage absent')
    chosen=[(n,ids[n]) for n in sorted(wanted)]
    fmt=struct.Struct('<'+'d'*len(columns));samples=[];count=0
    with gzip.open(os.path.join(out,e['file']),'rb') as stream:
        while True:
            b=stream.read(fmt.size)
            if not b:break
            if len(b)!=fmt.size:raise ValueError('Incomplete native row')
            row=fmt.unpack(b);count+=1;t=row[0]
            if any(edge-20e-12<=t<=edge+400e-12 for name,leg,pos,edge in EVENTS):
                samples.append(dict((n,row[i]) for n,i in chosen))
    if count!=e['rows']:raise ValueError('Native count mismatch')
    def integrate(rows,field):
        return sum((rows[j]['time']-rows[j-1]['time'])*(field(rows[j])+field(rows[j-1]))*.5 for j in range(1,len(rows)))
    events={}
    for name,leg,pos,edge in EVENTS:
        stem='xdut.xbbm0.xd_'+leg+'.';rc=stem+'rc1'
        rows=[q for q in samples if edge-20e-12<=q['time']<=edge+400e-12]
        peak=max(range(len(rows)),key=lambda j:rows[j][rc]) if pos else min(range(len(rows)),key=lambda j:rows[j][rc])
        target=cfg['supply_V'] if pos else 0.
        before=[j for j in range(peak+1) if rows[j][rc]<=target] if pos else [j for j in range(peak+1) if rows[j][rc]>=target]
        after=[j for j in range(peak+1,len(rows)) if rows[j][rc]<=target] if pos else [j for j in range(peak+1,len(rows)) if rows[j][rc]>=target]
        start=before[-1] if before else None;end=after[0] if after else None
        groups={'MP_CLEAR_D':[stem+'mp_clear:1'],'C1':[stem+'c1:1'],
                'R1':[stem+'r1:2'],'X005_native_gates':cfg['receiver_gate_current_branches_by_leg'][leg]}
        def value(row,keys):return sum(row[k] for k in keys)
        def interval(first,last):
            if first is None or last is None:return dict(status='unobserved_rail_crossing',charge_C=None)
            q=rows[first:last+1]
            charges=dict((n,integrate(q,lambda row,ks=ks:value(row,ks))) for n,ks in groups.items())
            return dict(status='observed',native_interval_s=[q[0]['time'],q[-1]['time']],
                RC1_start_V=q[0][rc],RC1_stop_V=q[-1][rc],charge_C=charges,
                signed_charge_sum_C=sum(charges.values()),
                max_KCL_A=max(abs(sum(value(row,ks) for ks in groups.values())) for row in q),
                MP_CLEAR_DGSB_charge_C=dict((str(j),integrate(q,lambda row,j=j:row[stem+'mp_clear:'+str(j)])) for j in [1,2,3,4]))
        p=rows[peak]
        gate=cfg['terminal_current_catalog']['XDUT.XBBM0.XD_'+leg.upper()+'.MP_CLEAR:2']['node'].lower()
        vd,vg,vs,vb=p[rc],p[gate],p['vdd!'],p['vdd!']
        rvalues=[]
        for row in rows:
            current=row[stem+'r1:1']
            if abs(current)>1e-6:rvalues.append((row[stem+'b']-row[rc])/current)
        gate_rows=[q for q in rows if edge-5e-12<=q['time']<=edge+(20e-12 if leg=='hd' else 40e-12)]
        gateQ=integrate(gate_rows,lambda q:q[stem+'mp_clear:2']) if len(gate_rows)>1 else None
        events[name]=dict(leg=leg.upper(),polarity='positive' if pos else 'negative',nominal_edge_s=edge,
            excursion_detected=(vd>target if pos else vd<target),
            peak_time_s=p['time'],RC1_peak_V=vd,gate_node=gate,
            MP_CLEAR_peak_DGSB_V=dict(D=vd,G=vg,S=vs,B=vb,Vds=vd-vs,Vgs=vg-vs,Vgd=vg-vd,Vbd=vb-vd),
            receiver_X005_peak_V=dict(gate_RC1=vd,output_Y=p['xdut.xbbm0.'+leg],NMOS_Vgs=vd,NMOS_Vgd=vd-p['xdut.xbbm0.'+leg]),
            peak_group_current_A=dict((n,value(p,ks)) for n,ks in groups.items()),
            MP_CLEAR_peak_DGSB_A=dict((str(j),p[stem+'mp_clear:'+str(j)]) for j in [1,2,3,4]),
            leading=interval(start,peak),whole_excursion=interval(start,end),
            observed_return_within400ps=end is not None,
            gate_charge_probe=dict(native_interval_s=[gate_rows[0]['time'],gate_rows[-1]['time']] if gate_rows else None,
                signed_C=gateQ,scope='Actual total gate current over stated native interval; not a constant intrinsic capacitance'),
            observed_R1_ohm_range=[min(rvalues),max(rvalues)] if rvalues else None,
            current_groups=groups)
    return dict(events=events,native_points=count,source_native_columns=len(columns),
        signs='Currents positive into named component port. Negative MP_CLEAR D charge delivers charge into RC1; C1/R1/native receiver gates take the balancing charge.',
        interpretation='Actual native total D/G/S/B currents including displacement; closed incidence budget identifies branch exchange, not a unique intrinsic Cgd/channel/diode decomposition. Only actual verified native X005 gate lists used; HD D1P25 four MOS/LD D1 two MOS; no fabricated legacy MM1/MM0 aliases.',
        missing_crossing_is_not_accepted=True)

