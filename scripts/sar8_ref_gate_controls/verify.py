"""Exact native-device and single-variable source audit."""
import sys
import re
from control import ROOT,OUT,VERIFY,read,dump,sha
from prepare import design,VARIANTS
sys.path.insert(0,str(ROOT/'scripts/sar8_ff_overvoltage'))
from localize import mapping

def main():
    rows=[]
    for name in read(VERIFY/'setup.json')['names']:
        p=OUT/name;ctx=read(p/'context.json');src=ROOT/'output/sar8_ref_length'/ctx['source_case']
        original=(src/'dut.scs').read_text();new=(p/'dut.scs').read_text();g,r=VARIANTS[ctx['variant']]
        assert new==design(original,g,r)
        origmos={k:v for k,v in mapping(original).items() if v['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']}
        newmos={k:v for k,v in mapping(new).items() if v['model'] in ['nch_mac','pch_mac','nch_18_mac','pch_18_mac']}
        assert origmos==newmos and len(newmos)==1833
        d0=(src/'test.scs').read_text();d1=(p/'test.scs').read_text()
        for tag in ['VSAMPLE','VVDD','VVINP','VVINN','RREFP','RREFN','CREFP','CREFN','tran_perf']:
            pattern=r'(?m)^'+tag+r' .*'
            assert re.findall(pattern,d0)==re.findall(pattern,d1)
        assert sha(p/'test.scs')==ctx['deck_sha256'] and sha(p/'dut.scs')==ctx['DUT_sha256']
        assert (p/'r4_perf_monitor.va').read_bytes()==(src/'r4_perf_monitor.va').read_bytes()+b'\n'+(ROOT/'scripts/sar8_ref_gate_controls/diagnostic.va').read_bytes()
        assert ctx['spectre_args']==read(src/'context.json')['spectre_args']
        rows.append(dict(name=name,native_MOS_identical=1833,source_timing_and_supplies_identical=True,
            helper_parameters=[g,r],inverse_reconstruction=True))
    dump(VERIFY/'source_validation.json',dict(status='PASS',cases=rows,scope='Sources, not simulation pass'))
    print('Source audit PASS:1833 native MOS unchanged per case, one control parameter varied')

if __name__=='__main__':main()
