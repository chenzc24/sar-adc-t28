"""Focused negative tests for bounded replay and local physical-load extraction."""
import json
from pathlib import Path
import unittest
import numpy as np
from prepare_approximate_replay import mandatory_knots,delete_knots,verify_native,crossing_brackets
from build_first_fixture import definitions,instances,ports,closure,TOP

HERE=Path(__file__).resolve().parent


class ReplayTests(unittest.TestCase):
    def test_linear_knots_deleted_without_new_points(self):
        t=np.arange(101,dtype=float)*1e-10;y=t*1e7
        required=mandatory_knots(t,y,.99)
        ids=delete_knots(t,y,required,1e-6)
        report=verify_native(t,y,ids,required,.99,1e-6)
        self.assertLess(len(ids),len(t))
        self.assertLess(report["max_abs_error_v"],1e-6)

    def test_native_narrow_spike_and_fault_window_retained(self):
        t=np.arange(1001,dtype=float)*1e-10;y=np.zeros(1001);y[315]=.001
        required=mandatory_knots(t,y,.99)
        ids=delete_knots(t,y,required,1e-6)
        self.assertIn(315,ids)
        self.assertTrue(np.all(np.isin(np.flatnonzero((t>=64e-9)&(t<=66e-9)),ids)))
        verify_native(t,y,ids,required,.99,1e-6)

    def test_independent_verifier_rejects_lost_spike(self):
        t=np.arange(7,dtype=float);y=np.array([0,0,0,.0001,0,0,0])
        required=np.array([True,False,False,False,False,False,True])
        with self.assertRaisesRegex(ValueError,"error exceeds"):
            verify_native(t,y,np.array([0,6]),required,.99,1e-6)

    def test_crossing_both_sides_exact_equality(self):
        y=np.array([0,.099,.2,.495,.8,.891,.99,.891,.7,.495,0])
        t=np.arange(len(y),dtype=float)
        required=mandatory_knots(t,y,.99)
        ids=delete_knots(t,y,required,1e-6)
        for fraction in [.1,.5,.9]:
            b=crossing_brackets(y,.99*fraction)
            self.assertTrue(np.all(required[b]) and np.all(required[b+1]))
        verify_native(t,y,ids,required,.99,1e-6)

    def test_verifier_rejects_missing_required_witness(self):
        t=np.arange(4,dtype=float);y=np.zeros(4);required=np.ones(4,dtype=bool)
        with self.assertRaisesRegex(ValueError,"required native"):
            verify_native(t,y,np.array([0,3]),required,.99,1e-6)

    def test_unordered_native_input_rejects(self):
        with self.assertRaisesRegex(ValueError,"unordered"):
            delete_knots(np.array([0.,0.,1.]),np.zeros(3),np.ones(3,dtype=bool),1e-6)


class PreparedCircuitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dest=HERE/"generated/first_reproduction"
        cls.defs=definitions((cls.dest/"dut.scs").read_text())
        cls.audit=json.loads((cls.dest/"connection_audit.json").read_text())
        cls.measure=json.loads((cls.dest/"measurement_map.json").read_text())

    def test_no_whole_adc_or_original_async_clock_loop(self):
        names=closure(self.defs,[TOP])
        self.assertNotIn("sar_adc8_join_r4",names)
        self.assertNotIn("sar8p_timing",names)
        self.assertNotIn("sar8i_idle",names)
        self.assertFalse(self.audit["clock_generation_feedback_retained"])

    def test_all_nested_port_arities_match(self):
        for block in self.defs.values():
            for name,args,model,_ in instances(block):
                if model in self.defs:
                    self.assertEqual(len(args),len(ports(self.defs[model])),name)

    def test_protected_direct_fanouts_and_original_devices(self):
        self.assertEqual(len(self.audit["protected_immediate_terminal_fanouts"]),11)
        self.assertTrue(all(x["equal"] for x in self.audit["protected_immediate_terminal_fanouts"].values()))
        self.assertEqual(self.audit["unchanged_source_device_records"],1177)

    def test_kcl_currents_and_all_driver_terminal_screens_present(self):
        currents=set(self.measure["current_saves"])
        for entry in self.measure["KCL"].values():
            self.assertTrue(set(entry["branches_positive_into_component"])<=currents)
        for name in ["XDUT.XCOMP.MNINN","XDUT.XCOMP.MNINP","XDUT.XBOOTN.Mmain","XDUT.XBOOTP.Mmain_U1"]:
            self.assertTrue({name+":"+str(i) for i in range(1,5)}<=currents)
        self.assertTrue(self.measure["not_a_lifetime_signoff"])


if __name__=="__main__":unittest.main()
