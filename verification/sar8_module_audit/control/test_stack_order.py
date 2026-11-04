"""Targeted gate-incidence and simultaneous terminal-stress test; no Spectre."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

OWN = Path(__file__).resolve().parent
P = 'xdut.xctrl.xtim.'


class StackOrderMeasurementTest(unittest.TestCase):
    def test_new_gate_incidence_joint_extrema_and_unforced_MID_initial(self):
        m = json.loads((OWN/'stack_order_v1/measurement.json').read_bytes())
        cat = m['terminal_current_catalog']
        upper, lower = 'XDUT.XCTRL.XTIM.X020.X000.MN0:2', 'XDUT.XCTRL.XTIM.X020.X000.MN1:2'
        self.assertEqual(cat[upper]['node'], 'XDUT.XCTRL.XTIM.LIVE')
        self.assertEqual(cat[lower]['node'], 'XDUT.XCTRL.XTIM.Q1')
        self.assertIn(upper.lower(), m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE'])
        self.assertNotIn(lower.lower(), m['kcl_terms']['XDUT.XCTRL.XTIM.LIVE'])
        self.assertIn(lower.lower(), m['kcl_terms']['XDUT.XCTRL.XTIM.Q1'])
        self.assertNotIn(upper.lower(), m['kcl_terms']['XDUT.XCTRL.XTIM.Q1'])
        self.assertNotIn(P+'x020.x000.mid', m['expected_initial_state']['values_v'])
        self.assertFalse(m['proposed_reproduction_contract']['internal_initial_state_equality_required'])
        with tempfile.TemporaryDirectory(prefix='_stack_order_observer_', dir=OWN) as temp:
            run = Path(temp).resolve()
            self.assertTrue(run.is_relative_to(OWN))
            for name in ['inputs', 'raw', 'derived']:
                (run/name).mkdir()
            (run/'inputs/measurement.json').write_text(json.dumps(m))
            names = sorted({x.lower() for x in m['voltage_saves']+m['current_saves']})
            text = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join(
                '"%s" FLOAT DOUBLE\n'%name for name in names)+'VALUE\n'
            # Synthetic voltages are deliberate measurement stimuli, not a circuit result.
            # Independent max(LIVE)-min(MID)=1.0V would falsely exceed0.99V;
            # true simultaneous MN0VGS never exceeds0.5V.
            times = [0., 1e-9, 2e-9, 40.8e-9, m['source_history_stop_s']]
            states = [(0.2, 0., 0.6, 0.9), (0.9, 0.8, 0.7, 0.6),
                      (0.4, -0.1, 0.2, 0.8), (0.2, 0., 0.6, 0.9), (0.2, 0., 0.6, 0.9)]
            for at, (live, mid, node_n, q1) in zip(times, states):
                values = {name: 0. for name in names}
                values.update(m['expected_initial_state']['values_v'])
                values.update({'vdd!': .99, 'vvdd:1': -1e-6, P+'live': live, P+'q1': q1,
                    P+'x020.n': node_n, P+'x020.x000.mid': mid, P+'x020.x000.b_pm': .5})
                text += '"time" %.17g\n'%at
                text += ''.join('"%s" %.17g\n'%(name, values[name]) for name in names)
            (run/'raw/synthetic.tran.tran').write_text(text+'END\n')
            (run/'raw/logStatus').write_text('tran_first PASS\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete', exit_code=0,
                native=dict(native_analysis_pass=True, zero_error_footer=True, warning_codes=[]))))
            done = subprocess.run([sys.executable, '-B', str(OWN/'full_gate_analyze.py'),
                '--run-dir', str(run), '--output-dir', str(run/'derived')], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            result = json.loads((run/'derived/result.json').read_bytes())
            stress = result['full_history_voltage_stress']
            self.assertEqual(len(stress), 15)
            expected = {
                'MN0_VGS': (.1, .5), 'MN0_VGD': (-.4, .2), 'MN0_VDS': (-.1, .6),
                'MN0_VGB': (.2, .9), 'MN0_VDB': (.2, .7), 'MN0_VSB': (-.1, .8),
                'MN1_VGS': (.6, .9), 'MN1_VGD': (-.2, .9), 'MN1_VDS': (-.1, .8),
                'MN1_VGB': (.6, .9), 'MN1_VDB': (-.1, .8), 'MN1_VSB': (0., 0.),
            }
            for label, (minimum, maximum) in expected.items():
                self.assertAlmostEqual(stress[label]['min_v'], minimum, msg=label)
                self.assertAlmostEqual(stress[label]['max_v'], maximum, msg=label)
                self.assertEqual(stress[label]['native_points'], 5)
            self.assertEqual(stress['MN0_VGS']['max_time_s'], 2e-9)
            self.assertEqual(stress['MN0_VGS']['over_limit_native_points'], 0)
            self.assertEqual(stress['MN0_VSB']['min_time_s'], 2e-9)
            self.assertEqual(result['diagnostic_points'], 2)
            self.assertEqual(result['initial_values'][P+'x020.x000.mid'], 0.)
            self.assertEqual(result['max_initial_witness_error_v'], 0.)
            self.assertIsNone(result['acceptance_pass'])
            self.assertAlmostEqual(result['full_history_source_energy']['VDD']['net_delivered_j'],
                                   .99e-6*m['source_history_stop_s'], delta=1e-25)


if __name__ == '__main__':
    unittest.main(verbosity=2)
