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


DECK_NOTES={'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1','DIODMY_L:WARNING'}


def planned_fill_state(manifest):
    """Planned array fill plus utility fill outside it (Layout/specs/fill-policy.md).

    The module must close OD/PO density and the 30 um Mx.DN.7 windows itself; only the
    125 um metal density and gradient windows (Mn.DN.1, Mn.DN.3) are larger than the CDAC
    and close at the top level.
    """
    labels=manifest['gds']['labels']
    assert {'sar8_cdac_fill_plan','sar8_cdac_fill_odpo','sar8_cdac_fill_metal'} <= set(labels)
    rules=set(manifest['checks']['drc']['markers_by_rule'])
    deferred={r for r in rules if re.fullmatch(r'M\d\.DN\.[13]',r)}
    assert rules <= DECK_NOTES|deferred, rules-DECK_NOTES-deferred
    return sorted(deferred)


def corner_fixture(fixture, vdd):
    """Gate and precharge commands swing to VDD; references stay at 0.9 V (specs/arch.json reference)."""
    out=[]
    for line in fixture.splitlines(keepends=True):
        if line.startswith(('VDg','VDPRE ')):
            line,n=re.subn(r'\b0\.9(?:0000000000000002)?\b',repr(vdd),line)
            assert n and not re.search(r'\b0\.9\b',line)
        out.append(line)
    return ''.join(out)


def main():
    p=argparse.ArgumentParser();p.add_argument('evidence');p.add_argument('run_id')
    p.add_argument('--adc-solver',action='store_true',help='Use the integration options and Spectre X preset of the current transistor ADC')
    p.add_argument('--planned-fill',action='store_true',help='CDAC with its planned array fill and utility fill outside it')
    p.add_argument('--rss-mib',type=int,default=1024,help='Simulation RSS limit; filled extractions need more than prefill')
    p.add_argument('--corner',choices=['tt','ssc','ssh','ffc','ffh'],default='tt',
                   help='PVT corner (specs/corners.json): MOS section, temperature and VDD; passive sections stay TT')
    p.add_argument('--queue-timeout-s',type=int,default=3600,help='Managed admission wait before the run gives up')
    a=p.parse_args()
    condition=json.loads((ROOT/'specs/corners.json').read_text(encoding='utf-8'))[a.corner]
    for x in [a.evidence,a.run_id]:assert re.fullmatch(r'[a-z][a-z0-9-]{1,55}',x)
    path=evidence(a.evidence)
    raw=pull(path+'/manifest.json');manifest=json.loads(raw)
    assert manifest['case']=='full' and not manifest.get('error')
    assert manifest['checks']['lvs']['verdict']=='CORRECT'
    assert manifest['decks']['pex']['support']['mom_runset']['mom_device_exclusions']==7
    filled='sar8_cdac_fill_odpo' in manifest['gds']['labels']
    deferred=planned_fill_state(manifest) if a.planned_fill else None
    if filled and not a.planned_fill:
        assert manifest['checks']['drc']['markers_by_rule'].keys() <= DECK_NOTES
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
    from tools.saradc.refsel import split_cdac
    source=split_cdac((ROOT/'design/xtor/cdac/cdac.scs').read_text())
    payload['schematic.scs']=re.sub(r'\bsar8j_r1_cdac\b','schematic_cdac',source).encode()
    fixture=(ROOT/'tb/blocks/cdac/acceptance.scs').read_text()
    if a.corner!='tt':
        fixture=corner_fixture(fixture,condition['vdd_v'])
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
    adc_fixture=(ROOT/'tb/top/short/test.scs').read_text()
    platform='\n'.join(l for l in adc_fixture.splitlines() if l.startswith('include "/home/process/'))
    signals=[prefix+'_'+node for prefix in ['pre','post'] for node in ['d_pre','d_n','d_p','d_rn','d_rp']]
    options='simulatorOptions options temp=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13'
    transient_options='errpreset=conservative'
    preset='cx'
    if a.adc_solver:
        flat_fixture=re.sub(r'\\\s*\n\s*',' ',adc_fixture)
        options=re.search(r'(?m)^simulatorOptions options .+$',flat_fixture)[0]
        transient_options=re.search(r'(?m)^\w+ tran .*? (errpreset=\S+ lteratio=\S+)',flat_fixture)[1]
        preset='mx'
    vdd='0.9'
    if a.corner!='tt':
        section=condition['mos'].lower()+'macro_mos_moscap'
        platform,n=re.subn(r'section=ttmacro_mos_moscap\b','section='+section,platform);assert n==1
        options,n=re.subn(r'\btemp=27 ','temp=%d '%condition['temperature_c'],options);assert n==1
        vdd=repr(condition['vdd_v'])
    deck=['simulator lang=spectre','global 0 VDD!',platform,'include "schematic.scs"','include "extracted.scs"',
          'ahdl_include "block_switch.va"','VVDD (VDD! 0) vsource dc='+vdd,'include "pre_fixture.scs"','include "post_fixture.scs"',
          options,'saveOptions options save=selected','tran_cdac tran stop=260n maxstep=5p '+transient_options,'save '+' '.join(signals)]
    payload['test.scs']=('\n'.join(deck)+'\n').encode()
    payload['block_switch.va']=(ROOT/'tb/common/veriloga/block_switch.va').read_bytes()
    scope=('TT 0.9V 27C filled full-CDAC; original 100ps ideal gate commands, 50ohm/4pF references; '
           '19ns hold comparison to separate settled weight amplitude from speed; no active comparator or SAR timing qualification'
           if filled else
           'TT 0.9V 27C pre-fill full-CDAC; original 100ps ideal gate commands, 50ohm/4pF references; no active comparator or SAR timing; density/antenna/fill and integrated signoff remain open')
    fill_state='filled' if filled else 'prefill'
    if a.planned_fill:
        fill_state='planned'
        scope=('TT 0.9V 27C full-CDAC with its planned array fill and foundry utility fill outside the blocked array; '
               'original 100ps ideal gate commands, 50ohm/4pF references; module metal density ('+', '.join(deferred)+
               ') closes at top level; no active comparator or SAR timing qualification')
    if a.corner!='tt':
        scope=scope.replace('TT 0.9V 27C','%s %s %gV %dC (gate commands at VDD, references 0.9V, TT MOM/passive sections, typical-RC extraction)'
                            %(a.corner,condition['mos'],condition['vdd_v'],condition['temperature_c']),1)
    context={'modules':['cdac'],'required_signals':['d_pre','d_n','d_p','d_rn','d_rp'],
             'contracts':{'cdac':json.loads((ROOT/'specs/block_tests.json').read_text())['tests']['cdac']},
             'physical_evidence':path,'gds_sha256':manifest['gds']['sha256'],
             'scope':scope,'filled':filled,'fill_state':fill_state,
             'native_pins':pins,'extracted_original_sha256':names}
    if a.corner!='tt':
        context.update(corner=a.corner,**condition,reference_v=[0,.9],
                       passive_sections=['tt_res_bip_dio_disres','tt_mom','tt_ind_jvar','tt_r_metal'])
    if a.adc_solver:
        context['solver']={'preset':preset,'options':options,'transient':transient_options,'maxstep_s':5e-12}
    payload['context.json']=(json.dumps(context,indent=2)+'\n').encode()
    payload['measure_full.py']=(ROOT/'Layout/tools/analysis/measure_full.py').read_bytes()
    for name in ['analyze_blocks.py','native_stream.py']:
        payload[name]=(ROOT/'tools/saradc/measure'/name).read_bytes()
    dest=ROOT/'work/layout'/a.run_id;dest.mkdir(exist_ok=False)
    for name,blob in payload.items():(dest/name).write_bytes(blob)
    recipe={'run_id':a.run_id,'design_id':'sar8_b_full_cdac_'+fill_state,'entry':'test.scs','analyzer':'measure_full.py',
            'inputs':[{'name':n,'source':(dest/n).relative_to(ROOT).as_posix(),'sha256':sha(b)} for n,b in payload.items()],
            'resources':dict(threads=4,simulation_rss_mib=a.rss_mib,simulation_virtual_mib=max(8192,4*a.rss_mib),analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=128,simulation_wall_seconds=1800,analysis_wall_seconds=600,queue_timeout_seconds=a.queue_timeout_s),
            'spectre_args':['+preset='+preset,'+mt=4','-preset_override','+lqtimeout','60'],
            'summary_signals':signals,'expected_stop_s':260e-9,'qualification_scope':context['scope'],'test_conditions':context}
    (dest/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print((dest/'recipe.json').relative_to(ROOT).as_posix())


if __name__=='__main__':main()
