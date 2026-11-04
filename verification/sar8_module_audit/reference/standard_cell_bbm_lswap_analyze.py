"""Single L native NAND A1/A2 swap; frozen standard-cell measurements reused."""
from __future__ import print_function
import argparse
import os
import standard_cell_bbm_analyze as base

BASE_VALIDATE=base.validate
BASE_MEASUREMENTS=base.measurements
VARIANT='original_bit0_BBM_native_stdcell_D1_L_A1A2_swap_ideal_CODE'


def validate(cfg):
    if cfg['variant']!=VARIANT:raise ValueError('Single L native pin-swap required')
    x=cfg['single_L_NAND_pin_swap']
    if x['target']!='XDUT.XBBM0.X004.X000.XLIB' or x['old_A1_A2']!=['CB','LD'] or x['new_A1_A2']!=['LD','CB'] or not x['H_and_all_other_flat_records_exact']:
        raise ValueError('Only L native A1/A2 permutation permitted')
    expected={'MM4':'XDUT.XBBM0.LD','MM9':'XDUT.XBBM0.CB',
              'MM1':'XDUT.XBBM0.LD','MM2':'XDUT.XBBM0.CB'}
    cat=cfg['terminal_current_catalog']
    for mos,node in expected.items():
        q=cat[x['target']+'.'+mos+':2']
        if q['node']!=node or q['port']!=2:raise ValueError('Actual swapped native gate binding differs')
    shadow=dict(cfg);shadow['variant']='original_bit0_BBM_native_stdcell_D1_ideal_CODE'
    return BASE_VALIDATE(shadow)


def measurements(original,result,cfg,out):
    m=BASE_MEASUREMENTS(original,result,cfg,out)
    m.update(single_L_NAND_pin_swap=cfg['single_L_NAND_pin_swap'],
        boundary='Only L native NAND A1/A2 permutation on frozen standard-cell bit0; H/RC/clear/IO/Rgate/real load and all external timing exact. No ADC or repair qualification.')
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
        _,hard=resource.getrlimit(resource.RLIMIT_AS);limit=240*base.cell.MIB if hard==resource.RLIM_INFINITY else min(hard,240*base.cell.MIB);resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    r=analyze(a.run_dir,a.output_dir);print('STDCELL_LSWAP_NATIVE_DIAGNOSTIC_OK',r['native_points'],'acceptance_pass=null')
