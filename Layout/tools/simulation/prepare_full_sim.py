"""Bind full-CDAC xRC to the existing independent TT CDAC fixture."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from Layout.design.cdac import PORTS
from Layout.project import config,evidence
ROOT=Path(__file__).resolve().parents[3]


def sha(data):return hashlib.sha256(data).hexdigest()
def pull(path):
    assert re.fullmatch(r'/[A-Za-z0-9_./-]+',path) and '..' not in path.split('/')
    cmd="test $(stat -c %s '"+path+"') -le 16777216 && cat '"+path+"'"
    return subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',config()['host'],'bash -s'],input=(cmd+'\n').encode(),timeout=40)


def main():
    p=argparse.ArgumentParser();p.add_argument('evidence');p.add_argument('run_id');a=p.parse_args()
    for x in [a.evidence,a.run_id]:assert re.fullmatch(r'[a-z][a-z0-9-]{1,55}',x)
    path=evidence(a.evidence)
    raw=pull(path+'/manifest.json');manifest=json.loads(raw)
    assert manifest['case']=='full' and not manifest.get('error')
    assert manifest['checks']['lvs']['verdict']=='CORRECT'
    assert manifest['decks']['pex']['support']['mom_runset']['mom_device_exclusions']==7
    filled='sar8_cdac_fill_odpo' in manifest['gds']['labels']
    if filled:
        assert manifest['checks']['drc']['markers_by_rule'].keys() <= {
            'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1','DIODMY_L:WARNING'}
    payload={'physical.json':raw}
    names={'extracted.scs':manifest['checks']['pex']['sha256'],**manifest['checks']['pex']['companion_sha256']}
    for name,digest in names.items():
        assert re.fullmatch(r'extracted\.scs(?:\.[A-Za-z0-9_.-]+)?',name)
        blob=pull(path+'/pex/'+name);assert sha(blob)==digest
        payload[name]=blob
    assert sum(map(len,payload.values()))<32*1024*1024
    pex=payload['extracted.scs'].decode('ascii')
    joined=re.sub(r'\\\s*\n\s*',' ',pex)
    pins=re.search(r'(?mi)^subckt\s+sar8j_r1_cdac\s*\(([^)]+)\)',joined)[1].split()
    assert sorted(pins)==sorted(PORTS)
    assert len(re.findall(r'\)\s*cfmom_2t\b',joined))==680
    original=(ROOT/'design/xtor/cdac/cdac.scs').read_text()
    source='\n'.join(l for l in original.splitlines() if not l.lstrip().startswith('//'))
    payload['schematic.scs']=re.sub(r'\bsar8j_r1_cdac\b','schematic_cdac',source).encode()
    fixture=(ROOT/'tb/blocks/cdac/acceptance.scs').read_text()
    for prefix in ['pre','post']:
        inst=re.search(r'^XDAC \(([^)]+)\) @CDAC@',fixture,re.M)
        pinmap=dict(zip(PORTS,inst[1].split()));assert len(pinmap)==38
        if prefix=='post':
            text=fixture[:inst.start()]+'XDAC ('+' '.join(pinmap[n] for n in pins)+') sar8j_r1_cdac'+fixture[inst.end():]
        else:text=fixture.replace('@CDAC@','schematic_cdac')
        text=re.sub(r'\bd_\w+\b',lambda m:prefix+'_'+m[0],text)
        # Prefix every fixture instance, not the shared native/VA masters.
        text=re.sub(r'(?m)^([A-Za-z]\w*)\s+\(',lambda m:prefix+'_'+m[1]+' (',text)
        payload[prefix+'_fixture.scs']=text.encode()
    platform='\n'.join(l for l in (ROOT/'tb/top/short/test.scs').read_text().splitlines() if l.startswith('include "/home/process/'))
    signals=[prefix+'_'+node for prefix in ['pre','post'] for node in ['d_pre','d_n','d_p','d_rn','d_rp']]
    deck=['simulator lang=spectre','global 0 VDD!',platform,'include "schematic.scs"','include "extracted.scs"',
          'ahdl_include "block_switch.va"','VVDD (VDD! 0) vsource dc=0.9','include "pre_fixture.scs"','include "post_fixture.scs"',
          'simulatorOptions options temp=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13',
          'saveOptions options save=selected','tran_cdac tran stop=260n maxstep=5p errpreset=conservative','save '+' '.join(signals)]
    payload['test.scs']=('\n'.join(deck)+'\n').encode()
    payload['block_switch.va']=(ROOT/'tb/common/veriloga/block_switch.va').read_bytes()
    scope=('TT 0.9V 27C filled full-CDAC; original 100ps ideal gate commands, 50ohm/4pF references; '
           '19ns hold comparison to separate settled weight amplitude from speed; no active comparator or SAR timing qualification'
           if filled else
           'TT 0.9V 27C pre-fill full-CDAC; original 100ps ideal gate commands, 50ohm/4pF references; no active comparator or SAR timing; density/antenna/fill and integrated signoff remain open')
    context={'modules':['cdac'],'required_signals':['d_pre','d_n','d_p','d_rn','d_rp'],
             'contracts':{'cdac':json.loads((ROOT/'specs/block_tests.json').read_text())['tests']['cdac']},
             'physical_evidence':path,'gds_sha256':manifest['gds']['sha256'],
             'scope':scope,'filled':filled,
             'native_pins':pins,'extracted_original_sha256':names}
    payload['context.json']=(json.dumps(context,indent=2)+'\n').encode()
    payload['measure_full.py']=(ROOT/'Layout/tools/analysis/measure_full.py').read_bytes()
    for name in ['analyze_blocks.py','native_stream.py']:
        payload[name]=(ROOT/'tools/saradc/measure'/name).read_bytes()
    dest=ROOT/'work/layout'/a.run_id;dest.mkdir(exist_ok=False)
    for name,blob in payload.items():(dest/name).write_bytes(blob)
    recipe={'run_id':a.run_id,'design_id':'sar8_b_full_cdac_'+('filled' if filled else 'prefill'),'entry':'test.scs','analyzer':'measure_full.py',
            'inputs':[{'name':n,'source':(dest/n).relative_to(ROOT).as_posix(),'sha256':sha(b)} for n,b in payload.items()],
            'resources':dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=128,simulation_wall_seconds=1800,analysis_wall_seconds=600,queue_timeout_seconds=3600),
            'spectre_args':['+preset=cx','+mt=4','-preset_override','+lqtimeout','60'],
            'summary_signals':signals,'expected_stop_s':260e-9,'qualification_scope':context['scope'],'test_conditions':context}
    (dest/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print((dest/'recipe.json').relative_to(ROOT).as_posix())


if __name__=='__main__':main()
