"""Focused checks for identity, precision preservation and outlier detection."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/integration"))
import r3_anomaly_replay as replay
from r3_anomaly_analyze import monitor, searches, outliers


class ReplayContract(unittest.TestCase):
    def test_parent_and_replay_identity(self):
        source = (replay.parent.OUT/f"decks/{replay.PARENT}.scs").read_text()
        derived = (replay.OUT/f"decks/{replay.NAME}.scs").read_text()
        self.assertEqual(replay.identity(source), replay.identity(derived))
        self.assertEqual(replay.parent.r3.r1.blocks(source), replay.parent.r3.r1.blocks(derived))
        for parameter in ("maxstep=10p", "errpreset=conservative", "step=51.6n", "istep=51.6n",
                          "transres=51.6f", "strobeperiod=1n", "stop=1200n", "outputstart=800n"):
            self.assertIn(parameter, derived)
        ctx = replay.parent.r3.r1.read_json(replay.OUT/"context.json")
        for p, h in ctx["include_sha256"].items():
            self.assertEqual(replay.parent.r3.r1.sha(Path(p)), h)
        originalstop = (replay.OUT/"original_stop/decks/static065_originalstop_first12.scs").read_text()
        self.assertEqual(replay.identity(source), replay.identity(originalstop))
        self.assertEqual(replay.parent.r3.r1.blocks(source), replay.parent.r3.r1.blocks(originalstop))
        self.assertIn("tran_perf tran stop=51600n maxstep=10p errpreset=conservative strobeperiod=1n", originalstop)
        self.assertIn("XSTOP (SAMPLE) r3_replay_stop stop_s=1200n", originalstop)

    def test_stable_complete_code_can_still_be_wrong(self):
        text = "R3MEAS,8,1,8,1,1,7e-6\nR3SEARCH,8,65,4,-0.442529296875,1\n"
        self.assertTrue(monitor(text)[0]["valid"])
        self.assertEqual(len(outliers(searches(text))), 1)
        self.assertEqual(outliers([dict(k=65, code=64), dict(k=65, code=65)]), [])


if __name__ == "__main__":
    unittest.main()
