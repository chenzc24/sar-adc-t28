"""Scope, provenance and completed-experiment assertions."""
import json
import re
import sys
from control import ROOT,OUT,VERIFY,SOURCE,read,dump,sha
from prepare import DCNAMES,resized

def sources():
    old=(SOURCE/'dut.scs').read_text()
    assert sha(SOURCE/'dut.scs')=='839596a5b493e9868a53fea451ef98b4e051484dca5d8e3d21d5dd151bf01695'
    for length,name in zip([30,60,90],DCNAMES):
        folder=OUT/name;ctx=read(folder/'context.json');text=(folder/'test.scs').read_text()
        assert ctx['deck_sha256']==sha(folder/'test.scs')
        # All two Ron devices preserve the exact multline parameter body of the pair.
        cell=re.search(r'(?ms)^subckt sar8j_r1_sw_b7 .*?^ends sar8j_r1_sw_b7',resized(old,length))[0]
        assert cell in text
        for dev,tag,ports in [('MN_LOW','N','DN VB VN 0'),('MP_HIGH','P','DP 0 VP VB')]:
            lines=cell.splitlines();i=next(i for i,x in enumerate(lines) if x.strip().startswith(dev+' '));j=i
            while lines[j].rstrip().endswith('\\'):j+=1
            line='\n'.join(lines[i:j+1]).strip()
            expect=re.sub(dev+r' \([^)]*\)',f'MRon{tag} ({ports})',line,count=1)
            assert expect in text
    for name in read(VERIFY/'integrated_setup.json')['names']:
        folder=OUT/name;ctx=read(folder/'context.json');src=ROOT/'output/sar8_main_width'/ctx['source_case']
        original=(src/'dut.scs').read_text();candidate=(folder/'dut.scs').read_text()
        assert candidate==resized(original,90)
        assert (folder/'test.scs').read_text()==(src/'test.scs').read_text().replace(original,candidate,1)
        assert sha(folder/'test.scs')==ctx['deck_sha256'] and sha(folder/'dut.scs')==ctx['DUT_sha256']
        assert sha(folder/'r4_perf_monitor.va')==sha(src/'r4_perf_monitor.va')==ctx['monitor_sha256']
    result=dict(source_inverse_check=True,DC_full_parameter_copy_check=True,
       monitor_unchanged=True,W_nf_multi_timing_unchanged=True,OA_changed=False,PDK_changed=False)
    if '--final' in sys.argv:
        comp=read(VERIFY/'integrated_comparison.json');assert comp['complete'] and len(comp['points'])==5
        for p in comp['points']:
            c=p['candidate'];assert len(c['codes'])==6
            assert c['effective_settings']==p['baseline']['effective_settings']
            assert abs(p['sample_close_change_ps'])<10
            assert abs(p['acquisition_change_ps'])<10
        result.update(complete_native_cases=8,failed_setup_cases_retained=3,
            all_static_codes_pass=all(p['candidate']['static_code_pass'] for p in comp['points']),
            post_startup_all_static_codes_pass=all(p['candidate']['post_startup_static_code_pass'] for p in comp['points']),
            all_timing_idle_pass=all(p['candidate']['timing_pass'] and p['candidate']['idle_pass'] for p in comp['points']),
            CMI_any=any(p['candidate']['CMI'] for p in comp['points']),
            not_signoff=True)
    dump(VERIFY/'validation.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':sources()
