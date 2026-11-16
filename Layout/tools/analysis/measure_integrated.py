"""Current handshake measurement with explicitly unavailable CDAC internals.

The native reference_short companion and inputs are frozen in the run package.
Distributed PEX nodes must not be interpreted as schematic lumped bottom plates.
"""
from __future__ import print_function
import argparse
import json
import os
import reference_short as measurement


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir',required=True)
    p.add_argument('--output-dir',required=True)
    p.add_argument('--source-run-dir')
    a=p.parse_args()
    run=a.source_run_dir or a.run_dir
    ctx=json.load(open(os.path.join(run,'inputs/context.json')))
    if ctx.get('pex_modules')!=['cdac'] or not ctx.get('pex'):
        raise ValueError('Expected current ADC with extracted CDAC')
    # None means unmeasured, never a passing settling bound. Keep real terminal
    # names in current_signals so the companion explicitly reports them missing.
    measurement.bottom=lambda voltages,lsb:None
    result=measurement.analyze(run,a.output_dir)
    for f in result['frames']:
        f['issues']=[x for x in f['issues'] if x['reason']!='bottom_settling_screen']
        for bit in f['bits']:
            bit['bottom_screen_pass']=None
            bit['bottom_stable_margin_ns']=None
        f['switch_port_overlap_peak_a']=None
        f['switch_port_overlap_integral_c']=None
    result['first_issue']=next((dict(frame=f['frame'],**f['issues'][0])
                               for f in result['frames'] if f['issues']),None)
    result['all_screens_pass']=False if result['first_issue'] else None
    result['settling_scope']='Distributed CDAC bottom-plate settling unmeasured; no independent settled TOP target.'
    result['current_scope']='Schematic switch terminal currents unavailable in extracted hierarchy; no overlap-current verdict.'
    result['limitations']=['Only CDAC has PEX; other modules remain pre-layout.',
        'No MC, transient noise, supply ramp or terminal qualification.',
        'No independent settling target or distributed bottom-plate measurement.',
        'Ten TT frames do not establish full-code or corner performance.']
    with open(os.path.join(a.output_dir,'result.json'),'w') as out:
        json.dump(result,out,indent=2);out.write('\n')


if __name__=='__main__':main()
