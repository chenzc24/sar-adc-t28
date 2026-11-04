"""One focused native-history stress/energy observer test; no Spectre run."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

OWN=Path(__file__).resolve().parent


class FullHistoryObserverTest(unittest.TestCase):
    def test_stress_before_diagnostic_window_and_constant_source_energy(self):
        m=json.loads((OWN/'mp1_floor_v1/measurement.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='_full_gate_observer_',dir=OWN) as temp:
            run=Path(temp).resolve()
            self.assertTrue(run.is_relative_to(OWN))
            for path in [run/'inputs',run/'raw',run/'derived']:path.mkdir()
            (run/'inputs/measurement.json').write_text(json.dumps(m))
            names=sorted({x.lower() for x in m['voltage_saves']+m['current_saves']})
            text='HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join('"%s" FLOAT DOUBLE\n'%n for n in names)+'VALUE\n'
            for at in [0.,1e-9,40.8e-9,41.09e-9,m['source_history_stop_s']]:
                text+='"time" %.17g\n'%at
                for n in names:
                    v=.99 if n=='vdd!' else -1e-6 if n=='vvdd:1' else 0.
                    if at==1e-9 and n=='xdut.xctrl.xtim.x020.x000.b_pm':v=-.02
                    if at==1e-9 and n=='xdut.xctrl.xtim.x020.n':v=1.02
                    text+='"%s" %.17g\n'%(n,v)
            (run/'raw/synthetic.tran.tran').write_text(text+'END\n')
            (run/'raw/logStatus').write_text('tran_first PASS\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2752']))))
            completed=subprocess.run([sys.executable,'-B',str(OWN/'full_gate_analyze.py'),'--run-dir',str(run),
                '--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            r=json.loads((run/'derived/result.json').read_bytes())
            stress=r['full_history_voltage_stress']
            self.assertEqual(stress['MP1_VGD']['max_abs_time_s'],1e-9)
            self.assertAlmostEqual(stress['MP1_VGD']['max_abs_v'],1.04)
            self.assertAlmostEqual(stress['MP1_VSG']['max_abs_v'],1.01)
            self.assertEqual(stress['MP1_VGD']['native_points'],5)
            self.assertEqual(r['diagnostic_points'],3)
            measured=r['full_history_source_energy']['VDD']['net_delivered_j']
            expected=.99*1e-6*m['source_history_stop_s']
            self.assertLess(abs(measured-expected),1e-25)
            self.assertIsNone(r['acceptance_pass'])


if __name__=='__main__':unittest.main(verbosity=2)
