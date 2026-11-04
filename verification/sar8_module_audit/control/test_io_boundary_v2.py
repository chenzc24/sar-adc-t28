"""Exact targeted boundary and all-fixture observation test; no Spectre."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import prepare_first_event as base

OWN = Path(__file__).resolve().parent
P = 'XDUT.XCTRL.XTIM.'


class BoundaryV2Test(unittest.TestCase):
    def test_targeted_nodes_and_unconverted_core_screen(self):
        folder = OWN/'io_boundary_v2'
        m = json.loads((folder/'measurement.json').read_bytes())
        old = base.flatten((OWN/'io_local_v1/dut.scs').read_text(), 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
        new = base.flatten((folder/'dut.scs').read_text(), 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
        self.assertEqual(set(new), set(old))
        changed = {k for k in new if new[k] != old[k]}
        self.assertEqual(changed, set(m['boundary_correction_v2']['changed_this_candidate']))
        self.assertEqual(len(changed), 15)
        for name in new:
            self.assertEqual(new[name]['nodes'], old[name]['nodes'])
            if name in changed:
                pars = dict(re.findall(r'(\w+)=(\S+)', new[name]['parameters']))
                self.assertEqual((pars['l'], pars['w'], pars['nf']), ('150n', '320n', '1'))
                self.assertIn(new[name]['model'], ['nch_18_mac', 'pch_18_mac'])
        clear_pars = dict(re.findall(r'(\w+)=(\S+)', new[P+'XD_QUIET_D.MN_CLEAR']['parameters']))
        self.assertEqual(clear_pars['multi'], '7')
        self.assertEqual(new[P+'X001.X000.MP1']['model'], 'pch_mac')
        self.assertEqual(new[P+'X022.X000.MN1']['model'], 'nch_mac')
        watched = m['boundary_correction_v2']['watched_mos']
        self.assertEqual(len(watched), 101)
        self.assertEqual(len(m['stress_voltage_pairs']), 610)
        self.assertEqual(len(m['diagnostic_current_columns']), 438)
        self.assertEqual(len(m['critical_kcl_nodes']), 61)
        for item in watched.values():
            self.assertEqual(set(item['six_pair_labels']), {'VGS', 'VGD', 'VDS', 'VGB', 'VDB', 'VSB'})
        with tempfile.TemporaryDirectory(prefix='_io_boundary_v2_', dir=OWN) as temp:
            run = Path(temp).resolve()
            self.assertTrue(run.is_relative_to(OWN))
            for name in ['inputs', 'raw', 'derived']:
                (run/name).mkdir()
            (run/'inputs/measurement.json').write_text(json.dumps(m))
            names = sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
            text = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join(
                '"%s" FLOAT DOUBLE\n'%s for s in names)+'VALUE\n'
            for at in [0., 1e-9, 2e-9, 40.8e-9, m['source_history_stop_s']]:
                values = dict.fromkeys(names, 0.)
                values.update(m['expected_initial_state']['values_v'])
                values.update({'vdd!': .99, 'vvdd:1': -1e-6})
                if at == 1e-9:
                    # Deliberate synthetic values, not claimed as a physical circuit result.
                    values.update({'xdut.active': 0., (P+'X001.N').lower(): 1.04,
                                   (P+'XD_QUIET_D.AB').lower(): 1.05})
                text += '"time" %.17g\n'%at
                text += ''.join('"%s" %.17g\n'%(s, values[s]) for s in names)
            (run/'raw/synthetic.tran.tran').write_text(text+'END\n')
            (run/'raw/logStatus').write_text('tran_first PASS\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete', exit_code=0,
                native=dict(native_analysis_pass=True, zero_error_footer=True, warning_codes=['CMI-2752']))))
            done = subprocess.run([sys.executable, '-B', str(OWN/'full_gate_analyze.py'),
                '--run-dir', str(run), '--output-dir', str(run/'derived')], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            result = json.loads((run/'derived/result.json').read_bytes())
            stress = result['full_history_voltage_stress']
            self.assertEqual(len(stress), 610)
            core_key = watched[P+'X001.X000.MP1']['six_pair_labels']['VGD']
            io_key = watched[P+'X001.X000.MN0']['six_pair_labels']['VDB']
            clear_key = watched[P+'XD_QUIET_D.MN_CLEAR']['six_pair_labels']['VGS']
            self.assertAlmostEqual(stress[core_key]['max_abs_v'], 1.04)
            self.assertEqual(stress[core_key]['limit_abs_v'], .99)
            self.assertEqual(stress[core_key]['over_limit_native_points'], 1)
            self.assertAlmostEqual(stress[io_key]['max_abs_v'], 1.04)
            self.assertEqual(stress[io_key]['limit_abs_v'], 1.98)
            self.assertEqual(stress[io_key]['over_limit_native_points'], 0)
            self.assertAlmostEqual(stress[clear_key]['max_abs_v'], 1.05)
            self.assertEqual(stress[clear_key]['over_limit_native_points'], 0)
            self.assertEqual(stress[clear_key]['max_abs_time_s'], 1e-9)
            self.assertTrue(result['CMI_warning_present'])
            self.assertIsNone(result['acceptance_pass'])
            self.assertEqual(result['diagnostic_points'], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
