"""Small deterministic R1 construction checks, not substitutes for Spectre."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
from join_r1 import top,array,switches,VA


class R1(unittest.TestCase):
    def test_three_x_only_pass_MOS(self):
        for bit,leaf in enumerate(switches()):
            self.assertEqual(len(leaf.parts),2)
            self.assertEqual({p.params["simM"] for p in leaf.parts},{str(3*(1<<bit))})
        for side in "PN":
            caps=[p for p in array().parts if p.name.startswith("CMOM"+side)]
            self.assertEqual(sum(int(p.params["m"]) for p in caps),256)

    def test_native_mapping_and_midpoint(self):
        parts={p.name:p for p in top().parts}
        self.assertEqual(parts["XCTRL"].master,"sar_logic_8b_async_simple")
        self.assertEqual(parts["XCOMP"].master,"sar_strongarm_t28")
        for s,bank,mid in (("P","N",127),("N","P",128)):
            for b in range(8):
                gate=parts[f"XG{s}{b}"]
                self.assertEqual(gate.terms["EH"],f"B{bank}_H{b}")
                self.assertEqual(gate.params["initial_high"],str((mid>>b)&1))
            self.assertEqual(parts["XBOOT"+s].terms["VOUT"],"TOP"+s)

    def test_no_ideal_analog_plant(self):
        masters={p.master for p in top().parts}
        self.assertNotIn("sar8a_plant",masters)
        self.assertNotIn("cdac8_dualrail_comparator",masters)
        text=VA.read_text()
        self.assertNotIn("V(TOP",text)
        self.assertNotIn("V(VIN",text)
        self.assertIn("off_at+dead_time_s",text)


if __name__=="__main__":unittest.main()
