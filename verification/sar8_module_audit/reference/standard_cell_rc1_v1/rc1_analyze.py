"""HD analog clear-gate series R only; native library and full stress retained."""
from __future__ import print_function
import argparse,os
import standard_cell_bbm_hlswap_analyze as base
from rc1_event_measure import measure

BASE_VALIDATE=base.validate
BASE_MEASUREMENTS=base.measurements
VARIANT='native_HL_BBM_HD_MP_CLEAR_series_R0_geometry_ideal_CODE'


def validate(cfg):
    q=cfg['single_HD_clear_gate_R']
    if cfg['variant']!=VARIANT or q['target']!='XDUT.XBBM0.XD_HD.MP_CLEAR' or q['new_resistor']!='XDUT.XBBM0.XD_HD.R_CLEAR_GATE' or not q['LD_and_all_other_existing_leaf_records_exact']:
        raise ValueError('Only HD clear-gate resistor insertion permitted')
    inv=cfg['boundary_inventory']
    if inv['all_primitives']!=195 or inv['BBM_primitive_count']!=39 or inv['all_actual_MOS']!=123 or inv['mandatory_currents']!=654 or inv['KCL_nodes']!=37:
        raise ValueError('Actual single-resistor inventory differs')
    cat=cfg['terminal_current_catalog'];st='XDUT.XBBM0.XD_HD.'
    expected={st+'MP_CLEAR:2':st+'CLEAR_G',st+'R_CLEAR_GATE:1':'CODE',st+'R_CLEAR_GATE:2':st+'CLEAR_G'}
    for branch,node in expected.items():
        if cat[branch]['node']!=node:raise ValueError('Actual RC clear-gate incidence differs')
    shadow=dict(cfg);shadow['variant']='original_bit0_BBM_native_stdcell_D1_HL_A1A2_swap_ideal_CODE'
    shadow['boundary_inventory']=dict(inv);shadow['boundary_inventory']['BBM_primitive_count']=38
    # Historical verifier's fixed38 is shadowed only after explicit actual39
    # check above; catalog/count/KCL validation still uses actual654/37/117.
    return BASE_VALIDATE(shadow)


def measurements(original,result,cfg,out):
    m=BASE_MEASUREMENTS(original,result,cfg,out)
    m.update(single_HD_clear_gate_R=cfg['single_HD_clear_gate_R'],
        RC1_actual_native_event_charge=measure(result,cfg,out),
        boundary='One R0-geometry PDK resistor inserted only at HD MP_CLEAR gate; LD and every other existing leaf exact. Native ordinary logic, supply/sample timing retained. No repair or ADC qualification.')
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
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*base.base.base.cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*base.base.base.cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('RC1_HD_GATE_R_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')
