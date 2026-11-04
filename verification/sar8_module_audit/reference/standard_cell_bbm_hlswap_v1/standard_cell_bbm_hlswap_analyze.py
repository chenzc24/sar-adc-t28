"""H-only native pin swap on frozen L-swap; full native stress-time measurement."""
from __future__ import print_function
import argparse,gzip,os,struct,sys
sys.dont_write_bytecode=True
import standard_cell_bbm_lswap_analyze as base

BASE_VALIDATE=base.validate
BASE_MEASUREMENTS=base.measurements
VARIANT='original_bit0_BBM_native_stdcell_D1_HL_A1A2_swap_ideal_CODE'
PHASES=[('full',0.,52e-9,True),('CODE_rise',42.995e-9,47.995e-9,False),
        ('CODE_fall',47.995e-9,52e-9,True)]


def validate(cfg):
    if cfg['variant']!=VARIANT:raise ValueError('H-only swap relative to frozen L required')
    q=cfg['single_H_NAND_pin_swap']
    if q['target']!='XDUT.XBBM0.X002.X000.XLIB' or q['old_A1_A2']!=['CODE','HD'] or q['new_A1_A2']!=['HD','CODE'] or not q['L_and_all_other_flat_records_exact']:
        raise ValueError('Exact single H native pin permutation required')
    cat=cfg['terminal_current_catalog']
    for mos,node in [('MM4','XDUT.XBBM0.HD'),('MM1','XDUT.XBBM0.HD'),
                     ('MM9','CODE'),('MM2','CODE')]:
        if cat[q['target']+'.'+mos+':2']['node']!=node:raise ValueError('Actual H native gate mapping differs')
    norm=base.base.cell.base.norm
    if set(map(norm,cfg['diagnostic_voltage_columns']))!=set(map(norm,cfg['voltage_saves'])):
        raise ValueError('Every already-saved voltage needed for full738 duration')
    shadow=dict(cfg);shadow['variant']='original_bit0_BBM_native_stdcell_D1_L_A1A2_swap_ideal_CODE'
    return BASE_VALIDATE(shadow)


def above_duration(t0,y0,t1,y1,limit,start,stop):
    a=max(t0,start);b=min(t1,stop)
    if b<=a:return 0.
    ya=y0+(y1-y0)*(a-t0)/(t1-t0);yb=y0+(y1-y0)*(b-t0)/(t1-t0)
    cuts=[0.,1.]
    if yb!=ya:
        for value in [-limit,limit]:
            f=(value-ya)/(yb-ya)
            if 0<f<1:cuts.append(f)
    cuts.sort();answer=0.
    for x,z in zip(cuts[:-1],cuts[1:]):
        if abs(ya+(yb-ya)*(x+z)*.5)>limit:answer+=(b-a)*(z-x)
    return answer


def full_stress_time(result,cfg,out):
    entry=next(e for e in result['native_exports'] if e['file']=='cell.native.f64le.gz')
    c=dict((n,i) for i,n in enumerate(entry['columns']));fmt=struct.Struct('<'+'d'*len(c))
    norm=base.base.cell.base.norm
    specs=[]
    for p in cfg['selected_mos_pair_screens']:
        nodes=[norm(n) for n in p['nodes']]
        specs.append((p['instance']+':'+p['terminal'],
            None if nodes[0]=='0' else c[nodes[0]],
            None if nodes[1]=='0' else c[nodes[1]],p['screen_v']))
    phases={}
    for name,a,b,closed in PHASES:
        phases[name]=dict(requested_interval_s=[a,b],last_boundary_included=closed,
            pairs=dict((key,dict(limit_V=limit,samples=0,min_V=None,min_time_s=None,
                max_V=None,max_time_s=None,absolute_above_limit_duration_s=0.))
                for key,i,j,limit in specs))
    nand={}
    for leg,cell in [('L','X004'),('H','X002')]:
        inst='XDUT.XBBM0.'+cell+'.X000.XLIB.MM4'
        nodes=[norm(cfg['terminal_current_catalog'][inst+':'+str(j)]['node']) for j in [1,2,3,4]]
        nand[leg]=dict(instance=inst,actual_DGSB_nodes=nodes,
            phases=dict((name,dict(samples=0,stack_min_V=None,stack_max_V=None,
                Vds_max_V=None,Vds_max_native_DGSB=None)) for name,a,b,closed in PHASES))
    previous=None;count=0
    with gzip.open(os.path.join(out,entry['file']),'rb') as f:
        while True:
            raw=f.read(fmt.size)
            if not raw:break
            if len(raw)!=fmt.size:raise ValueError('Partial full-voltage native row')
            row=fmt.unpack(raw);t=row[0];values=[(0. if i is None else row[i])-(0. if j is None else row[j]) for key,i,j,limit in specs]
            for name,a,b,closed in PHASES:
                pairs=phases[name]['pairs']
                inside=a<=t and (t<=b if closed else t<b)
                for (key,i,j,limit),value,k in zip(specs,values,range(len(specs))):
                    q=pairs[key]
                    if inside:
                        q['samples']+=1
                        if q['min_V'] is None or value<q['min_V']:q['min_V']=value;q['min_time_s']=t
                        if q['max_V'] is None or value>q['max_V']:q['max_V']=value;q['max_time_s']=t
                    if previous is not None:
                        pt,pv=previous;q['absolute_above_limit_duration_s']+=above_duration(pt,pv[k],t,value,limit,a,b)
                if inside:
                    for leg,q in nand.items():
                        v=[0. if n=='0' else row[c[n]] for n in q['actual_DGSB_nodes']]
                        s=q['phases'][name];s['samples']+=1
                        s['stack_min_V']=v[2] if s['stack_min_V'] is None else min(s['stack_min_V'],v[2])
                        s['stack_max_V']=v[2] if s['stack_max_V'] is None else max(s['stack_max_V'],v[2])
                        value=v[0]-v[2]
                        if s['Vds_max_V'] is None or value>s['Vds_max_V']:
                            s['Vds_max_V']=value;s['Vds_max_native_DGSB']=dict(time_s=t,D_V=v[0],G_V=v[1],S_V=v[2],B_V=v[3],Vds_V=value)
            previous=(t,values);count+=1
    if count!=entry['rows']:raise ValueError('Native row count mismatch')
    for name,q in phases.items():
        for key,s in q['pairs'].items():
            if s['samples']==0:raise ValueError('Missing physical phase '+name)
            s['strict_native_exceed']=max(abs(s['min_V']),abs(s['max_V']))>s['limit_V']
            if name=='full':
                x=result['selected_mos_pair_extrema'][key]
                if s['min_V']!=x['min'] or s['max_V']!=x['max']:raise ValueError('Independent full terminal extrema mismatch '+key)
        q['strict_native_pair_count']=sum(s['strict_native_exceed'] for s in q['pairs'].values())
    return dict(phases=phases,NAND_native_phase_witnesses=nand,
        interpretation='All738 simultaneous actual terminal pairs; full0..52ns plus two CODE phases. Duration is piecewise-linear interpolation at native points and exact clipped phase boundaries, not lifetime qualification. Frozen per-device screen limits unchanged.',
        raw_all_voltage_native_points=count)


def measurements(original,result,cfg,out):
    m=BASE_MEASUREMENTS(original,result,cfg,out)
    m.update(single_H_NAND_pin_swap=cfg['single_H_NAND_pin_swap'],
        all_terminal_native_phase_time=full_stress_time(result,cfg,out),
        boundary='Only H native A1/A2 swap relative to frozen L-swap; L/RC/clear/IO/Rgate/real load and52ns stimulus exact. Existing L residual and RC issues not declared fixed.')
    return m


def analyze(run,out):
    old_v,old_m=base.validate,base.measurements
    try:
        base.validate=validate;base.measurements=measurements
        return base.analyze(run,out)
    finally:base.validate,base.measurements=old_v,old_m


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if os.name=='posix':
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*base.base.cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*base.base.cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('STDCELL_HL_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')

