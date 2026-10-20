"""Focused R3 B scope/history/phase contracts; no broad regression suite."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/integration"))
import r3_refgate_events as f


class ReferenceEventContract(unittest.TestCase):
    def test_native_progress_prefix_is_not_a_missing_phase_event(self):
        from r3_refgate_analyze import state_rows
        rows=state_rows("......9.R3PHASE,XDUT.XGP7,8.0105e-7,1,1,0,8.0115e-7\n", "R3PHASE")
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]["time_ns"],801.05)
        self.assertEqual(rows[0]["rising"],rows[0]["sampling"])

    def test_native_circuit_and_original_sources_preserved(self):
        oldctx=json.loads((f.OLD/"context.json").read_text())
        olddeck=(f.OLD/f"decks/{f.OLD_NAME}.scs").read_text()
        for p,h in oldctx["include_sha256"].items():
            self.assertEqual(f.SHA(Path(p)),h)
        for name in ("a","b","b2","b3"):
            ctx=json.loads((f.OUT/name/"context.json").read_text())
            deck=Path(ctx["deck"]).read_text()
            self.assertEqual(f.replay.identity(deck),f.replay.identity(olddeck))
            self.assertEqual(f.replay.parent.r3.r1.blocks(deck),f.replay.parent.r3.r1.blocks(olddeck))
            self.assertIn("stop=51600n maxstep=10p errpreset=conservative strobeperiod=1n",deck)
            for p,h in ctx["include_sha256"].items():
                self.assertEqual(f.SHA(Path(p)),h)
        original=next(Path(p) for p in oldctx["include_files"] if Path(p).name=="sar8j_aligned_refgate.va")
        self.assertEqual(f.instrument_original(original.read_text()),(f.MODEL/"a/sar8j_aligned_refgate.va").read_text())

    def test_input_replay_and_direction_specific_phase(self):
        h=f.history()
        self.assertEqual(len(h),12)
        self.assertAlmostEqual(h[8],-.442529296875,places=15)
        self.assertEqual(h[:5],[h[0]]*5)
        originalctx=json.loads((f.OLD/"context.json").read_text())
        original=next(Path(p) for p in originalctx["include_files"] if Path(p).name=="r3_transition_stim.va")
        stim=(f.MODEL/"r3_transition_stim.va").read_text()
        self.assertEqual(f.frozen_stim(original.read_text()),stim)
        self.assertIn('report_trial=trial;',stim)
        self.assertIn('$strobe("R3SEARCH,%d,%d,%d,%.12g,%d",report_frame,report_k,report_phase,report_trial,code)',stim)
        b=(f.MODEL/"b/sar8j_aligned_refgate.va").read_text()
        directions=re.findall(r"cross\(V\(SAMPLE,VSS\)-0.5\*V\(VDD,VSS\),([+-]?\d)\)",b)
        self.assertEqual(directions,["+1","-1"])
        self.assertNotIn("sample_now=",b)
        self.assertEqual(b.count("V(GP,VSS)<+"),1)
        self.assertEqual(b.count("V(GN,VSS)<+"),1)
        final=(f.MODEL/"b3/sar8j_aligned_refgate.va").read_text()
        self.assertIn("@(timer(restore_at)) begin",final)
        self.assertIn("@(timer(turnon_at)) begin",final)
        self.assertNotIn("$abstime>=restore_at",final)
        self.assertNotIn("$abstime>=turnon_at",final)
        self.assertIn("restore_pending=0; restored=1;",final)


if __name__=="__main__": unittest.main()
