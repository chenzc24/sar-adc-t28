"""Bind filled CDAC xRC to the explicitly recorded current transistor TT design."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from Layout.design.cdac import PORTS
from Layout.tools.simulation.prepare_full_sim import pull, sha
from Layout.project import evidence
from tools.saradc.__main__ import ROOT
from tools.saradc.reference_short import prepare as prepare_current_short


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('evidence')
    parser.add_argument('run_id')
    args=parser.parse_args()
    for value in [args.evidence,args.run_id]:
        assert re.fullmatch(r'[a-z][a-z0-9-]{1,55}',value)
    # Never alter any previously prepared or registered execution identity.
    dest=ROOT/'work/decks'/args.run_id
    assert not dest.exists(), 'Execution identity already prepared'
    remote=evidence(args.evidence)
    raw=pull(remote+'/manifest.json');manifest=json.loads(raw)
    assert manifest['case']=='full' and not manifest.get('error')
    assert manifest['checks']['lvs']['verdict']=='CORRECT'
    assert manifest['checks']['drc']['markers_by_rule'].keys() <= {
        'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1','DIODMY_L:WARNING'}
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
    payload['cdac_pex_wrapper.scs']=('\n'.join([
        'simulator lang=spectre','include "extracted.scs"',
        'subckt sar8j_r1_cdac ('+' '.join(PORTS)+')',
        'XPEX ('+' '.join(pins)+') cdac_extracted',
        'ends sar8j_r1_cdac',''])).encode()
    # Reuse the current handshake stimulus/observer, not the old B CAP_CLK reducer.
    # This staging identity is never registered or submitted.
    codes=json.loads((ROOT/'tb/top/short/context.json').read_text())['expected_codes']
    staging_recipe=ROOT/prepare_current_short('current','tt',args.run_id,
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
    assert original_header==PORTS, 'Original positional interface changed'
    original_dut=(dest/'dut.scs').read_bytes()
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
    base_design_id=json.loads((ROOT/'design/manifest.json').read_text())['design_id']
    scope=('Filled CDAC native RC extraction inside current transistor ADC '+base_design_id+'; TT 0.9V 27C, '
           '10 unchanged low/mid/high/startup frames, 60ns low-first clock phase. '
           'Other modules remain pre-layout. No noise/mismatch or whole-chip signoff.')
    context.update(PEX=True,pex=True,pex_modules=['cdac'],design_view='current_with_cdac_pex',
                   prelayout_design_id=base_design_id,
                   prelayout_dut_sha256=sha(original_dut),dut_sha256=sha(payload['dut.scs']),
                   physical_evidence=remote,gds_sha256=manifest['gds']['sha256'],
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
    recipe.update(inputs=list(inputs.values()),design_id=base_design_id+'_cdac_pex',analyzer='measure_integrated.py',
                  qualification_scope=scope,test_conditions=context)
    recipe_path.write_text(json.dumps(recipe,indent=2)+'\n')
    print(recipe_path.relative_to(ROOT).as_posix())


if __name__=='__main__':main()
