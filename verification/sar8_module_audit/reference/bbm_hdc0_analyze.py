"""HD C0 x4 contrast; reuse frozen BBM measurements and clarify phase endpoints."""
from __future__ import print_function
import argparse,gzip,os,struct
import real_bbm_analyze as base

BASE_VALIDATE=base.validate;BASE_MEASUREMENTS=base.measurements
VARIANT='full_BBM_HD_C0_multi4_ideal_CODE'


def validate(cfg):
    x=cfg['single_component_contrast']
    if cfg['variant']!=VARIANT or x['instance']!='XDUT.XBBM0.XD_HD.C0' or x['old_multi']!=1 or x['new_multi']!=4 or not x['all195_other_flat_records_identical']:raise ValueError('One HD C0 multiplier contrast required')
    shadow=dict(cfg);shadow['variant']='full_original_bit0_BBM_real_H_driver_ideal_CODE'
    return BASE_VALIDATE(shadow)


def measurements(original,result,cfg,out):
    m=BASE_MEASUREMENTS(original,result,cfg,out)
    m['legacy_halfVDD_window_switching_diagnostic']=m['actual_correct_ON_settling']
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
    m.update(physical_command_phase_reference_settling=physical,delay_leg_reset_diagnostics=resets,single_component_contrast=cfg['single_component_contrast'],
        boundary='Complete BBM/real load with only HD C0 multi1->4; ideal CODE/rails, no ADC or RC1 repair qualification',
        phase_window_note='Frozen halfVDD endpoint crosses into turnoff and is retained only as switching diagnostic. Stable-high judgement ends before next CODE edge starts47.995ns.1mV/1percent are diagnostics, not specification changes.')
    return m


def analyze(run,out):
    old_v,old_m=base.validate,base.measurements
    try:
        base.validate=validate;base.measurements=measurements
        return base.analyze(run,out)
    finally:base.validate,base.measurements=old_v,old_m


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    if os.name=='posix':
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*base.cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*base.cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(args.run_dir,args.output_dir);print('BBM_HD_C0X4_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')
