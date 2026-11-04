"""One focused local-package/typed-stress test; no native simulation claim."""
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


class LocalIOTest(unittest.TestCase):
    def test_exact_local_change_and_core_IO_screens_stay_distinct(self):
        folder = OWN/'io_local_v1'
        m = json.loads((folder/'measurement.json').read_bytes())
        old = base.flatten((OWN/'stack_order_v1/dut.scs').read_text(), 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
        new = base.flatten((folder/'dut.scs').read_text(), 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
        changed = {k for k in new if new[k] != old[k]}
        self.assertEqual(len(changed), 15)
        self.assertEqual(set(old)-set(new), {P+'X020.X000.RPU'+str(i) for i in range(3)})
        for k in changed:
            self.assertEqual(new[k]['nodes'], old[k]['nodes'])
            self.assertIn(new[k]['model'], ['nch_18_mac', 'pch_18_mac'])
            pars = dict(re.findall(r'(\w+)=(\S+)', new[k]['parameters']))
            self.assertEqual((pars['l'], pars['w'], pars['nf']), ('150n', '320n', '1'))
        self.assertEqual(new[P+'X020.X000.MN0']['nodes'][1], P+'LIVE')
        self.assertEqual(new[P+'X020.X000.MN1']['nodes'][1], P+'Q1')
        self.assertEqual(new[P+'X020.X000.CMID'], old[P+'X020.X000.CMID'])
        self.assertEqual(new[P+'X020.X000.RSLEW'], old[P+'X020.X000.RSLEW'])
        boundary = m['io_local_experiment']['observed_mos']
        self.assertEqual(len(boundary), 32)
        self.assertEqual(sum(x['changed'] for x in boundary.values()), 15)
        for item in boundary.values():
            self.assertEqual(set(item['six_pair_labels']), {'VGS', 'VGD', 'VDS', 'VGB', 'VDB', 'VSB'})
        with tempfile.TemporaryDirectory(prefix='_io_local_observer_', dir=OWN) as temp:
            run = Path(temp).resolve()
            self.assertTrue(run.is_relative_to(OWN))
            for name in ['inputs', 'raw', 'derived']:
                (run/name).mkdir()
            (run/'inputs/measurement.json').write_text(json.dumps(m))
            names = sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
            text = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join(
                '"%s" FLOAT DOUBLE\n'%s for s in names)+'VALUE\n'
            # Synthetic test voltages exercise separate family screens; not a circuit result.
            for at in [0., 1e-9, 2e-9, 40.8e-9, m['source_history_stop_s']]:
                values = dict.fromkeys(names, 0.)
                values.update(m['expected_initial_state']['values_v'])
                values.update({'vdd!': .99, 'vvdd:1': -1e-6})
                if at == 1e-9:
                    values.update({(P+'X020.N').lower(): 1.05,
                        (P+'X020.X000.B_PM').lower(): -.02, (P+'X001.N').lower(): 1.04})
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
            self.assertEqual(len(stress), 196)
            core_label = boundary[P+'X001.X000.MP0']['six_pair_labels']['VGD']
            io_label = boundary[P+'X001.X001.MN']['six_pair_labels']['VGS']
            self.assertAlmostEqual(stress[core_label]['max_abs_v'], 1.04)
            self.assertEqual(stress[core_label]['limit_abs_v'], .99)
            self.assertEqual(stress[core_label]['over_limit_native_points'], 1)
            self.assertAlmostEqual(stress[io_label]['max_abs_v'], 1.04)
            self.assertEqual(stress[io_label]['limit_abs_v'], 1.98)
            self.assertEqual(stress[io_label]['over_limit_native_points'], 0)
            self.assertEqual(stress['MP1_VSG']['max_abs_time_s'], 1e-9)
            self.assertAlmostEqual(stress['MP1_VSG']['max_abs_v'], 1.01)
            self.assertEqual(stress['N_versus_old_core_rail_DIAGNOSTIC']['over_limit_native_points'], 1)
            self.assertTrue(result['CMI_warning_present'])
            self.assertEqual(result['diagnostic_points'], 2)
            self.assertIsNone(result['acceptance_pass'])
            self.assertAlmostEqual(result['full_history_source_energy']['VDD']['net_delivered_j'],
                                   .99e-6*m['source_history_stop_s'], delta=1e-25)


if __name__ == '__main__':
    unittest.main(verbosity=2)
