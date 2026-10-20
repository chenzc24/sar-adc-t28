from dataclasses import replace
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from models.behavioral.sar_async import AsyncSAR,AsyncConfig


class AsyncModelTest(unittest.TestCase):
    def test_all_codes_and_separate_capture_advance(self):
        adc=AsyncSAR()
        for code in range(256):
            r=adc.convert(-.9+(code+.5)*1.8/256,duplicate_ready=True,stale_ready=True)
            self.assertTrue(r.valid);self.assertEqual(r.code,code);self.assertEqual(r.captures,8)
            caps=[x for x in r.trace if x["event"]=="capture"]
            rst=[x for x in r.trace if x["event"]=="reset"]
            adv=[x for x in r.trace if x["event"]=="advance"]
            self.assertEqual([x["bit"] for x in caps],list(range(7,-1,-1)))
            self.assertTrue(all(a["t_ns"]<b["t_ns"]<d["t_ns"] for a,b,d in zip(caps,rst,adv)))

    def test_delay_and_timeout_are_real_events(self):
        a=AsyncSAR();fast=a.convert(.123,delays_ns=[.2]*8)
        slow=a.convert(.123,delays_ns=[1.5]*8)
        self.assertAlmostEqual(slow.completion_ns-fast.completion_ns,10.4)
        self.assertEqual(fast.code,slow.code)
        for bit in range(8):
            bad=a.convert(-.3,stuck_bit=bit)
            self.assertFalse(bad.valid);self.assertEqual(bad.code,slow.code)
            self.assertEqual(bad.fault,"deadline")

    def test_abort_illegal_reset_and_recovery(self):
        a=AsyncSAR();old=a.convert(.2).code
        for bit in range(8):
            r=a.convert(-.2,illegal_bit=bit);self.assertFalse(r.valid);self.assertEqual(r.code,old)
        self.assertEqual(a.convert(-.2,abort_ns=60).fault,"abort")
        self.assertFalse(a.convert(-.2,reset_ns=100).valid)
        self.assertTrue(a.convert(-.2).valid)
        a.reset();self.assertEqual(a.output,0)

    def test_deadline_wins_exact_completion_tie(self):
        a=AsyncSAR();r=a.convert(.1,delays_ns=[1.5]*8)
        b=AsyncSAR(replace(a.cfg,deadline_ns=r.commit_ns))
        self.assertFalse(b.convert(.1,delays_ns=[1.5]*8).valid)
        b=AsyncSAR(replace(a.cfg,deadline_ns=r.commit_ns+.05))
        self.assertTrue(b.convert(.1,delays_ns=[1.5]*8).valid)

    def test_disabled_error_controls_and_sensitivity(self):
        ideal=AsyncSAR();bias=AsyncSAR(replace(ideal.cfg,comparator_offset_v=.02))
        self.assertGreater(bias.convert(0).code,ideal.convert(0).code)
        self.assertEqual(AsyncSAR().convert(0).code,128)


if __name__=="__main__":unittest.main()
