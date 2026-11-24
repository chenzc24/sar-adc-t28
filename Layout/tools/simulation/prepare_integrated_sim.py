"""Bind a verified CDAC xRC view to the current transistor TT design."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from Layout.design.cdac import PORTS
from Layout.tools.physical.run_physical import FULL_CONTEXT_RULES
from Layout.tools.simulation import bootstrap_pex
from Layout.tools.simulation.prepare_full_sim import planned_fill_state, pull, sha
from Layout.project import evidence
from tools.saradc.__main__ import ROOT
from tools.saradc.reference_short import prepare as prepare_current_short


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('evidence')
    parser.add_argument('run_id')
    parser.add_argument('--prefill',action='store_true',help='Use a verified core before density fill')
    parser.add_argument('--planned-fill',action='store_true',
                        help='Use the CDAC with its planned array fill and utility fill outside it')
    parser.add_argument('--rss-mib',type=int,help='Simulation RSS limit; filled extractions need more than prefill')
    parser.add_argument('--corner',choices=['tt','ssc','ssh','ffc','ffh'],default='tt',
                        help='PVT corner of the short ADC fixture (specs/corners.json)')
    parser.add_argument('--acquisition-ns',type=float,
                        help='Diagnostic override of the 40 ns SAMPLE-high time for this run only; '
                             'specs/arch.json and the shared testbenches are unchanged')
    parser.add_argument('--bootstrap',metavar='EVIDENCE',
                        help='Also replace both Bootstrap channels with this verified prefill core extraction')
    args=parser.parse_args()
    assert not (args.prefill and args.planned_fill)
    assert args.acquisition_ns is None or 40<args.acquisition_ns<=55, 'Acquisition override must be in (40, 55] ns'
    for value in [args.evidence,args.run_id]:
        assert re.fullmatch(r'[a-z][a-z0-9-]{1,55}',value)
    # Never alter any previously prepared or registered execution identity.
    dest=ROOT/'work/decks'/args.run_id
    assert not dest.exists(), 'Execution identity already prepared'
    remote=evidence(args.evidence)
    raw=pull(remote+'/manifest.json');manifest=json.loads(raw)
    assert manifest['case']=='full' and not manifest.get('error')
    assert manifest['checks']['lvs']['verdict']=='CORRECT'
    labels=manifest['gds']['labels']
    expected_fill={'sar8_cdac_fill_odpo','sar8_cdac_fill_metal'}
    assert expected_fill.intersection(labels)==(set() if args.prefill else expected_fill)
    drc=manifest['checks']['drc']
    allowed={'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1','DIODMY_L:WARNING'}
    if args.prefill:
        allowed.update(FULL_CONTEXT_RULES)
    if args.planned_fill:
        allowed.update(planned_fill_state(manifest))
    assert set(drc['markers_by_rule']) <= allowed
    assert manifest['decks']['pex']['support']['mom_runset']['mom_device_exclusions']==7
    originals={'extracted.scs':manifest['checks']['pex']['sha256'],
               **manifest['checks']['pex']['companion_sha256']}
    payload={'cdac_physical.json':raw}
    for name,digest in originals.items():
        assert re.fullmatch(r'extracted\.scs(?:\.[A-Za-z0-9_.-]+)?',name)
        blob=pull(remote+'/pex/'+name);assert sha(blob)==digest
        payload[name]=blob
    assert sum(map(len,payload.values()))<32*1024*1024
    pex=payload['extracted.scs'].decode('ascii')
    joined=re.sub(r'\\\s*\n\s*',' ',pex)
    pins=re.search(r'(?mi)^subckt\s+sar8j_r1_cdac\s*\(([^)]+)\)',joined)[1].split()
    assert sorted(pins)==sorted(PORTS) and len(pins)==38
    assert len(re.findall(r'\)\s*cfmom_2t\b',joined))==680
    # Rename only the extracted definition; the physical port names stay intact.
    pex,count=re.subn(r'(?m)^(subckt|ends)\s+sar8j_r1_cdac\b',r'\1 cdac_extracted',pex)
    assert count==2
    payload['extracted.scs']=pex.encode('ascii')
    from tools.saradc.refsel import CDAC_PORTS, shared_pex_wrapper
    wrapper = '\n'.join([
        'simulator lang=spectre','include "extracted.scs"',
        'subckt sar8j_r1_cdac ('+' '.join(PORTS)+')',
        'XPEX ('+' '.join(pins)+') cdac_extracted',
        'ends sar8j_r1_cdac',''])
    payload['cdac_pex_wrapper.scs'] = shared_pex_wrapper(wrapper).encode()
    # Reuse the current handshake stimulus/observer, not the old B CAP_CLK reducer.
    # This staging identity is never registered or submitted.
    codes=json.loads((ROOT/'tb/top/short/context.json').read_text())['expected_codes']
    staging_recipe=ROOT/prepare_current_short('current',args.corner,args.run_id,
                                             codes=codes,max_output_mib=4096)
    recipe=json.loads(staging_recipe.read_text())
    dest.mkdir(parents=True)
    for row in recipe['inputs']:
        target=dest/row['name']; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/row['source']).read_bytes())
        row['source']=target.relative_to(ROOT).as_posix()
    recipe_path=dest/'recipe.json'
    context=json.loads((dest/'context.json').read_text())
    context['run_id']=args.run_id
    recipe['run_id']=args.run_id
    old_cdac=(dest/'xtor/cdac/cdac.scs').read_bytes()
    original_header=re.search(r'(?m)^subckt sar8j_r1_cdac\s+([^\n]+)',
                              re.sub(r'\\\s*\n\s*',' ',old_cdac.decode()))[1].split()
    assert tuple(original_header)==CDAC_PORTS, 'Original positional interface changed'
    original_dut=(dest/'dut.scs').read_bytes()
    # The analyzer's event order depends on the SAR actually included, not the view name.
    if b'include "xtor/sar/single_edge.scs"' in original_dut:
        context['version']='single_edge'
    needle=b'include "xtor/cdac/cdac.scs"'
    assert original_dut.count(needle)==1
    payload['dut.scs']=original_dut.replace(needle,b'include "cdac_pex_wrapper.scs"')
    # The extracted CDAC has distributed nodes and a different device hierarchy.
    # Do not pretend its internal probes are the schematic's lumped Bn nodes.
    tb=(dest/'test.scs').read_text()
    tb=re.sub(r'(?m)^save (.*)$',lambda m:'save '+' '.join(
        token for token in m[1].split() if not token.upper().startswith('XDUT.XCDAC.')),tb)
    payload['test.scs']=tb.encode()
    context['required_signals']=[s for s in context['required_signals'] if not s.startswith('xdut.xcdac.')]
    context['unavailable_pex_diagnostics']=['lumped_bottom_plate_screen','schematic_switch_terminal_currents']
    pex_modules=['cdac']
    if args.bootstrap:
        # One extracted channel serves XBOOTP and XBOOTN; its files carry a boot_ prefix
        # so they cannot collide with the CDAC extraction.
        boot=bootstrap_pex.package(args.bootstrap)
        payload.update(boot['files'])
        payload['dut.scs']=bootstrap_pex.use(payload['dut.scs'])
        # The extracted channel has its own internal node names.
        tb=re.sub(r'(?m)^save (.*)$',lambda m:'save '+' '.join(
            token for token in m[1].split() if not token.upper().startswith(('XDUT.XBOOTP.','XDUT.XBOOTN.'))),tb)
        payload['test.scs']=tb.encode()
        context['required_signals']=[s for s in context['required_signals'] if not s.startswith(('xdut.xbootp.','xdut.xbootn.'))]
        context.update(boot['context'])
        pex_modules.append('bootstrap')
    if args.acquisition_ns is not None:
        # The period stays 100 ns; only the SAMPLE-high time grows and the conversion phase shrinks.
        width=round(args.acquisition_ns-0.1,4)
        bench=(dest/'tb.scs').read_text()
        bench,n=re.subn(r'(?m)^(VSAMPLE \(SAMPLE 0\) .*?\bwidth=)39\.9n\b',lambda m:m[1]+'%gn'%width,bench)
        assert n==1, 'Expected the standard 40 ns SAMPLE source'
        payload['tb.scs']=bench.encode()
        # Keep reading the output pins 5 ns before the next acquisition, as the 55 ns probe does at 40 ns.
        probe=round(95-args.acquisition_ns,4)
        tb,n=re.subn(r'(?m)^(XPROBE \([^)]*\) b_behavior_observer)[ \t]*$',lambda m:m[1]+' probe_delay_s=%gn'%probe,tb)
        assert n==1, 'Expected one pin observer'
        payload['test.scs']=tb.encode()
        context.update(acquisition_s=args.acquisition_ns*1e-9,sample_pulse_width_s=width*1e-9,
                       observer_probe_delay_s=probe*1e-9,
                       acquisition_override='Per-run diagnostic; specs/arch.json and shared testbenches keep 40 ns')
    base_design_id=json.loads((ROOT/'design/manifest.json').read_text())['design_id']
    fill_state='Prefill' if args.prefill else 'Planned-fill' if args.planned_fill else 'Filled'
    corner=json.loads((ROOT/'specs/corners.json').read_text(encoding='utf-8'))[args.corner]
    condition=('TT 0.9V 27C' if args.corner=='tt' else '%s %s %gV %dC (reference 0.9V, TT passive sections, typical-RC extraction)'
               %(args.corner,corner['mos'],corner['vdd_v'],corner['temperature_c']))
    if args.acquisition_ns is not None:
        condition+=', DIAGNOSTIC %g ns acquisition / %g ns conversion phase'%(args.acquisition_ns,100-args.acquisition_ns)
    boot_scope=' and prefill Bootstrap RC extraction (both channels)' if args.bootstrap else ''
    scope=(fill_state+' CDAC native RC extraction'+boot_scope+' inside current transistor ADC '+base_design_id+'; '+condition+', '
           '10 unchanged low/mid/high/startup frames, 60ns low-first clock phase. '
           'Other modules remain pre-layout. No noise/mismatch or whole-chip signoff.')
    view='current_with_'+'_'.join(pex_modules)+'_pex'
    context.update(PEX=True,pex=True,pex_modules=pex_modules,design_view=view,
                   prelayout_design_id=base_design_id,
                   prelayout_dut_sha256=sha(original_dut),dut_sha256=sha(payload['dut.scs']),
                   physical_evidence=remote,gds_sha256=manifest['gds']['sha256'],cdac_fill_state=fill_state.lower(),
                   prelayout_cdac_sha256=sha(old_cdac),
                   extracted_original_sha256=originals,extracted_ports=pins,
                   cdac_wrapper_ports=PORTS,qualification_scope=scope)
    payload['measure_integrated.py']=(ROOT/'Layout/tools/analysis/measure_integrated.py').read_bytes()
    context['source_hashes'].update({n:sha(b) for n,b in payload.items()})
    payload['context.json']=(json.dumps(context,indent=2)+'\n').encode()
    for name,blob in payload.items():
        (dest/name).write_bytes(blob)
    inputs={row['name']:row for row in recipe['inputs']}
    for name,blob in payload.items():
        inputs[name]={'name':name,'source':(dest/name).relative_to(ROOT).as_posix(),'sha256':sha(blob)}
    recipe.update(inputs=list(inputs.values()),design_id=base_design_id+'_'+'_'.join(pex_modules)+'_pex',analyzer='measure_integrated.py',
                  qualification_scope=scope,test_conditions=context)
    if args.rss_mib:
        recipe['resources'].update(simulation_rss_mib=args.rss_mib,
                                   simulation_virtual_mib=max(recipe['resources'].get('simulation_virtual_mib',0),4*args.rss_mib))
    recipe_path.write_text(json.dumps(recipe,indent=2)+'\n')
    print(recipe_path.relative_to(ROOT).as_posix())


if __name__=='__main__':main()
