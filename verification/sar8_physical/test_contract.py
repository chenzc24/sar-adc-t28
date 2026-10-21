"""Focused candidate graph and testbench-parameter regression checks."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/sar8_physical"))
from circuit import all_objects, reference, bootstrap
from simulate import bind_testbench_parameters


class Contract(unittest.TestCase):
    def test_export_parameter_order(self):
        for text in ("parameters SUP VDIFF\n","parameters VDIFF SUP\r\n"):
            self.assertIn("parameters SUP=0.9 VDIFF=0.123",bind_testbench_parameters(text))

    def test_reject_unknown_parameter(self):
        for text in ("parameters SUP VDIFF EXTRA\n","parameters SUP\n",""):
            with self.assertRaises(AssertionError):bind_testbench_parameters(text)

    def test_no_internal_ideal_devices(self):
        for cell in all_objects():
            if not cell.name.startswith("tb_"):
                self.assertFalse(any(p.lib=="analogLib" for p in cell.parts),cell.name)

    def test_native_reference_word_mapping(self):
        word=reference()[-1]
        stores=[p for p in word.parts if p.master=="sar8p_dffr"]
        self.assertEqual(len(stores),8)
        for bit in range(8):
            store=next(p for p in stores if p.name==f"XSTORE{bit}")
            self.assertEqual(store.terms["RST"],"SAMPLE")
            self.assertEqual(store.terms["D"],"MSB_DN" if bit==7 else f"TARGET{bit}")
            self.assertEqual(store.terms["Q"],"MSB_QN" if bit==7 else f"Q{bit}")
            self.assertEqual(store.terms["CK"],"CAP_CLK")
            mux=next(p for p in word.parts if p.name==f"XMUX{bit}")
            self.assertEqual((mux.terms["D0"],mux.terms["D1"],mux.terms["SEL"]),(f"CODE{bit}",f"D{bit}","PHI_U"))
        trigger=next(p for p in word.parts if p.terms.get("Y")=="CAP_REQ")
        self.assertEqual((trigger.master,trigger.terms["A"],trigger.terms["B"]),("sar8p_or2","FIRST2","LATE_CLK"))
        self.assertEqual(sum(p.master=="sar8p_sr" for p in word.parts),1)

    def test_original_bootstrap_geometry(self):
        mos=[p for p in bootstrap().parts if p.master.endswith("_mac")]
        self.assertEqual(len(mos),12)
        self.assertTrue(all(p.params==dict(Wfg="1u",l="150.0n",fingers="1",simM="1") for p in mos))


if __name__=="__main__":unittest.main()
