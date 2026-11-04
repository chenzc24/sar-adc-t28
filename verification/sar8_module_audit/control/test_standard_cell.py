"""One bounded preparation/parser test using synthetic rows, never a circuit result."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import prepare_standard_cell as prepare
import standard_cell_analyze as analyze

OWN, ROOT = prepare.OWN, prepare.ROOT


class StandardCellPackageTest(unittest.TestCase):
    def test_exact_replacement_and_strict_native_binding(self):
        package = OWN/'standard_cell_v1'
        recipe = json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze = json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for item in recipe['inputs']:
            self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe,masters,truth = prepare.metadata()
        nand, inv = [truth['cells'][n] for n in prepare.CELLS]
        self.assertEqual(nand['nmos_input_adjacent_output'],['A1'])
        for row in nand['switch_graph_truth_table']:
            self.assertEqual(row['output'],1-row['inputs']['A1']*row['inputs']['A2'])
        for row in inv['switch_graph_truth_table']:
            self.assertEqual(row['output'],1-row['inputs']['I'])
        text = (prepare.SRC/'dut.scs').read_text()
        changed = (package/'dut.scs').read_text()
        self.assertEqual(changed,prepare.replace_x020(text))
        old = prepare.base.flatten(text,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
        new,library = prepare.expanded_leaves(changed,probe)
        removed = {k for k in old if k.startswith(prepare.TARGET+'.')}
        self.assertEqual(len(removed),7)
        self.assertEqual(set(old)-set(new),removed)
        self.assertEqual(set(new)-set(old),set(library))
        self.assertEqual(len(new),len(old)-1)
        for k in set(old)-removed:
            self.assertEqual(new[k],old[k])
        upper = prepare.TARGET+'.X000.MM4'
        lower = prepare.TARGET+'.X000.MM9'
        self.assertEqual(new[upper]['nodes'],[prepare.TARGET+'.N',prepare.P+'LIVE',prepare.TARGET+'.X000.net10','0'])
        self.assertEqual(new[lower]['nodes'],[prepare.TARGET+'.X000.net10',prepare.P+'Q1','0','0'])
        for path in (prepare.SRC/'pwl').glob('*.pwl'):
            self.assertEqual((package/'pwl'/path.name).read_bytes(),path.read_bytes())
        m = json.loads((package/'measurement.json').read_bytes())
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes'])),(61,435,60))
        self.assertEqual(len(m['stress_voltage_pairs']),609)
        self.assertEqual(len(m['standard_cell_experiment']['observed_mos']),101)
        self.assertNotIn(prepare.TARGET+'.X000.MID',m['voltage_saves'])
        for info in library.values():
            self.assertTrue(set(info['requested_numeric_terminal_currents'])<=set(m['current_saves']))
        with tempfile.TemporaryDirectory(prefix='_stdcell_test_',dir=OWN) as folder:
            root = Path(folder).resolve()
            self.assertTrue(root.is_relative_to(OWN))
            # Non-proprietary synthetic bytes exercise identity checks only.
            fake = root/'synthetic.spi'; fake.write_bytes(b'* synthetic identity fixture\n')
            manifest = json.loads((package/'external_library.json').read_bytes())
            manifest.update(file=str(fake),**analyze.file_identity(str(fake)))
            for scenario in ['complete','missing_library_current']:
                run = root/scenario
                for sub in ['inputs','raw','derived']:
                    (run/sub).mkdir(parents=True)
                (run/'inputs/measurement.json').write_text(json.dumps(m))
                (run/'inputs/external_library.json').write_text(json.dumps(manifest))
                for item in recipe['inputs']:
                    if item['name'] in manifest['metadata_inputs']:
                        (run/'inputs'/item['name']).write_bytes((ROOT/item['source']).read_bytes())
                self.assertEqual(analyze.verify_library(str(run/'inputs/external_library.json'))['sha256'],manifest['sha256'])
                names = sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
                missing = (upper+':2').lower()
                if scenario!='complete': names.remove(missing)
                text = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join('"%s" FLOAT DOUBLE\n'%n for n in names)+'VALUE\n'
                for at in [0.,1e-9,40.8e-9,41.09e-9,m['source_history_stop_s']]:
                    values = dict.fromkeys(names,0.)
                    values.update({k:v for k,v in m['expected_initial_state']['values_v'].items() if k in values})
                    values.update({'vdd!':.99,'vvdd:1':-1e-6})
                    if at==1e-9:
                        values.update({(prepare.TARGET+'.N').lower():1.05,(prepare.P+'X001.N').lower():1.04})
                    if at>=41.09e-9: values['xdut.sample_int']=0.
                    text+='"time" %.17g\n'%at
                    text+=''.join('"%s" %.17g\n'%(n,values[n]) for n in names)
                (run/'raw/synthetic.tran.tran').write_text(text+'END\n')
                (run/'raw/logStatus').write_text('tran_first PASS\n')
                (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                    native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2752']))))
                done = subprocess.run([sys.executable,'-B',str(OWN/'standard_cell_analyze.py'),
                    '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
                if scenario!='complete':
                    self.assertNotEqual(done.returncode,0)
                    self.assertIn('Required native TRACE/time sweep missing',done.stderr)
                    self.assertIn(missing,done.stderr)
                    self.assertFalse((run/'derived/result.json').exists())
                    continue
                self.assertEqual(done.returncode,0,done.stderr)
                result = json.loads((run/'derived/result.json').read_bytes())
                self.assertIsNone(result['acceptance_pass'])
                self.assertFalse(result['circuit_repair_claim'])
                self.assertTrue(result['CMI_warning_present'])
                self.assertEqual(result['diagnostic_points'],3)
                self.assertEqual(len(result['standard_cell_native_current_bindings']),6)
                for group,count in [('standard_cell',6),('retained_core',95)]:
                    self.assertEqual(result['physical_terminal_screen_groups'][group]['MOS'],count)
                label = m['standard_cell_experiment']['observed_mos'][upper]['six_pair_labels']['VDS']
                self.assertEqual(result['full_history_voltage_stress'][label]['max_abs_time_s'],1e-9)
                self.assertAlmostEqual(result['full_history_voltage_stress'][label]['max_abs_v'],1.05)
                self.assertEqual(result['full_history_voltage_stress'][label]['limit_abs_v'],.99)
                self.assertAlmostEqual(result['full_history_source_energy']['VDD']['net_delivered_j'],
                    .99e-6*m['source_history_stop_s'],delta=1e-25)
                timing = result['diagnostic_timing']
                self.assertEqual(timing['signals']['xdut.sample_int']['fall_halfrail_count'],1)
                self.assertTrue(timing['signals'][prepare.P.lower()+'clock_q']['no_halfrail_edge_observed'])
            fake.write_bytes(b'* changed synthetic fixture\n')
            with self.assertRaisesRegex(ValueError,'SPICE SHA/size mismatch'):
                analyze.verify_library(str(root/'complete/inputs/external_library.json'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
