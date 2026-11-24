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
    if ctx.get('pex_modules') not in (['cdac'],['cdac','bootstrap']) or not ctx.get('pex'):
        raise ValueError('Expected current ADC with extracted CDAC')
    # Decks built from the 'current' view carry version 'current'; the SAR they
    # simulate is set by the DUT include, and the single-edge SAR has no PHI_W.
    with open(os.path.join(run,'inputs/dut.scs')) as dut:
        if 'include "xtor/sar/single_edge.scs"' in dut.read() and ctx.get('version')!='single_edge':
            ctx=dict(ctx,version='single_edge',version_source='inputs/dut.scs includes xtor/sar/single_edge.scs')
    reader=None
    boot_nodes=['xdut.xboot%s.%s'%(s,n) for s in 'pn' for n in ('btop','bbot')]
    if 'bootstrap' in ctx['pex_modules']:
        # The extracted Bootstrap has no schematic BTOP/BBOT nodes; report precharge as unmeasured.
        def reader(path):
            for t,v in measurement.samples(path):
                for node in boot_nodes:v.setdefault(node,float('nan'))
                yield t,v
    # None means unmeasured, never a passing settling bound. Keep real terminal
    # names in current_signals so the companion explicitly reports them missing.
    measurement.bottom=lambda voltages,lsb:None
    result=measurement.analyze(run,a.output_dir,sample_reader=reader,context=ctx)
    if reader:
        result['precharge']=None
        result['precharge_scope']='Bootstrap BTOP/BBOT are internal to the extracted core and were not saved.'
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
    result['limitations']=['PEX modules: '+', '.join(ctx['pex_modules'])+'; other modules remain pre-layout.',
        'No MC, transient noise, supply ramp or terminal qualification.',
        'No independent settling target or distributed bottom-plate measurement.',
        'Ten TT frames do not establish full-code or corner performance.']
    with open(os.path.join(a.output_dir,'result.json'),'w') as out:
        json.dump(result,out,indent=2);out.write('\n')


if __name__=='__main__':main()
