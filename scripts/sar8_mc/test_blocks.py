"""Focused physics/measurement checks before native module pilots."""
import importlib.util,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts/sar8_campaign'))
s=importlib.util.spec_from_file_location('block_reduce',Path(__file__).with_name('block_reduce.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestWeights(unittest.TestCase):
    def test_ideal_binary_and_common_scale(self):
        c={side+str(i):4e-15*(2**i if i<8 else 1) for side in 'PN' for i in range(9)}
        for q in [c,{k:3*v for k,v in c.items()}]:
            r=m.weight_metrics(q);self.assertLess(r['dac_dnl_abs_max_lsb'],1e-11);self.assertLess(r['dac_inl_endpoint_abs_max_lsb'],1e-11)
    def test_msb_error_exposes_major_carry(self):
        c={side+str(i):4e-15*(2**i if i<8 else 1) for side in 'PN' for i in range(9)}
        c['P7']*=1.01;r=m.weight_metrics(c)
        self.assertGreater(r['major_carry'][7]['error_lsb'],.5)
    def test_existing_native_ac_parser(self):
        p=R/'output/sar8_pvt_mismatch/activation_9031/native/test.raw/mc_separate/mc-001/mc_ac_probe.ac'
        if not p.exists():self.skipTest('Historical small native fixture absent')
        data=m.cap_values(str(p));self.assertEqual(len(data),3);self.assertLess(data[0][1]['vc0:p'].imag,0)
if __name__=='__main__':unittest.main()
