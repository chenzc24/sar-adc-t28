"""One focused RB mapping/native-measurement check; no simulator or remote call."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_standard_cell_rb as prepare
import standard_cell_rb_analyze as analyze

OWN, ROOT = prepare.OWN, prepare.ROOT


class RBStageTest(unittest.TestCase):
    def test_exact_inverter_mapping_and_measurement_coverage(self):
        package = OWN/'standard_cell_rb_v1'
        recipe = json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze = json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for folder in [package,prepare.SRC]:
            for item in json.loads((folder/'recipe.suggested.yaml').read_bytes())['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe = json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
        oldtext = (prepare.SRC/'dut.scs').read_text(); text = (package/'dut.scs').read_text()
        self.assertEqual(text,prepare.replace_rb(oldtext))
        for master in ['sar8p_sr','sar8p_inv']:
            self.assertEqual(prepare.base.cells(text)[master],prepare.base.cells(oldtext)[master])
        old,_ = prepare.live.expand_twelve(oldtext,probe)
        new,library = prepare.expand_fourteen(text,probe)
        target,p,sr = prepare.TARGET,prepare.P,prepare.SR
        self.assertEqual(set(old)-set(new),{target+'.MP',target+'.MN'})
        self.assertEqual(set(new)-set(old),{target+'.MM0',target+'.MM1'})
        for key in set(old)&set(new):
            self.assertEqual(old[key],new[key])
        self.assertEqual(len(set(old)&set(new)),127)
        self.assertEqual(new[target+'.MM1']['nodes'],[sr+'.RB',p+'CLOCK_RESET','0','0'])
        self.assertEqual(new[target+'.MM0']['nodes'],[sr+'.RB',p+'CLOCK_RESET','VDD!','VDD!'])
        self.assertEqual(prepare.base.parts(prepare.base.cells(text)['sar8audit_sr_rb_tcb'])['X000']['model'],'INVD1BWP12T30P140')
        m = json.loads((package/'measurement.json').read_bytes())
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,436,61,609))
        mos = m['standard_cell_experiment']['observed_mos']
        physical = {label for item in mos.values() for label in item['six_pair_labels'].values()}
        self.assertEqual((len(mos),len(physical),len(library)),(101,606,14))
        self.assertTrue(all(v['limit_abs_v']==.99 for v in m['stress_voltage_pairs'].values()))
        self.assertFalse(any(k.startswith((target+'.MN_',target+'.MP_')) for k in physical))
        for path,item in library.items():
            self.assertEqual(item['nodes'],new[path]['nodes'])
            for port in item['requested_numeric_terminal_currents']:
                self.assertIn(port,m['terminal_current_catalog'])
        for node,terms in m['kcl_terms'].items():
            self.assertEqual(set(terms),{port.lower() for port,item in m['terminal_current_catalog'].items() if item['node']==node})
        self.assertTrue(all(t in m['kcl_terms'][p+'CLOCK_RESET'] for t in [(target+'.MM0:2').lower(),(target+'.MM1:2').lower()]))
        self.assertEqual(m['standard_cell_rb_experiment']['explicit_capacitors_added_or_removed'],[])
        for path in (prepare.SRC/'pwl').glob('*.pwl'):
            self.assertEqual((package/'pwl'/path.name).read_bytes(),path.read_bytes())
        strip = lambda t: ''.join(line for line in t.splitlines(True) if not line.startswith('save '))
        self.assertEqual(strip((package/'test.scs').read_text()),strip((prepare.SRC/'test.scs').read_text()))
        with tempfile.TemporaryDirectory(prefix='_rb_stage_check_',dir=OWN) as folder:
            output = Path(folder).resolve(); self.assertTrue(output.is_relative_to(OWN))
            names = ['time']+sorted({x.lower() for x in m['voltage_saves']+m['current_saves']})
            (output/'peak.columns.json').write_text(json.dumps(dict(names=names)))
            times = [40.8e-9,41e-9,41.1e-9,m['source_history_stop_s']]
            blobs = []
            for i,t in enumerate(times):
                v = dict.fromkeys(names,0.); v['time']=t; v['vdd!']=.99
                v[(p+'CLOCK_RESET').lower()] = [.99,1.01,0.,0.][i]
                v[(sr+'.RB').lower()] = [-.002,-.002,.99,.99][i]
                v[(sr+'.QB').lower()]=.99; v[(sr+'.SN').lower()]=.99
                if i in [1,2]:
                    spec = m['standard_cell_rb_experiment']['load_observers']['CLOCK_RESET']
                    v[spec['ports']['NM_gate'].lower()]=5e-6; v[spec['ports']['PM_gate'].lower()]=3e-6
                    v[(p+'X023.X002.MP1:1').lower()]=-8e-6
                    spec = m['standard_cell_rb_experiment']['load_observers']['RB']
                    for label,amps in [('QB_NM_gate',1e-6),('QB_PM_gate',-.5e-6),('SN_NM_gate',2e-6),('SN_PM_gate',-1e-6)]:
                        v[spec['ports'][label].lower()]=amps
                    v[(target+'.MM1:1').lower()]=-1.5e-6
                blobs.append(struct.pack('<'+'d'*len(names),*(v[n] for n in names)))
            (output/'peak.native.bin').write_bytes(b''.join(blobs))
            observed = analyze.reset_observations(str(output),m)
            self.assertEqual(set(observed['nodes']),{'CLOCK_RESET','RB','SR_QB','SR_SN','CLOCK_Q','CLOCK_SET'})
            self.assertTrue(all(item['native_KCL_max_a']<1e-18 for item in observed['nodes'].values()))
            expected = 5e-6*(times[2]-times[1])+.5*5e-6*(times[3]-times[2])
            self.assertAlmostEqual(observed['nodes']['CLOCK_RESET']['event_exchange']['into_gate_devices_c']['NM_gate'],expected,delta=1e-27)
            width = observed['excursion_widths']['nodes']['RB']['below_minus_1mV']
            self.assertAlmostEqual(width['cumulative_s'],times[1]-times[0]+.001/.992*(times[2]-times[1]),delta=1e-23)
            self.assertTrue(width['episodes'][0]['open_at_window_start'])
            self.assertEqual(len(observed['reset_release_R_fall_to_RB_rise']),1)
            self.assertLess(observed['reset_release_R_fall_to_RB_rise'][0]['delay_s'],0.)
            self.assertEqual(observed['reset_assert_R_rise_to_RB_fall'],[])
            self.assertEqual(observed['nodes']['CLOCK_Q']['rising_halfrail_s'],[])
            self.assertFalse(observed['nodes']['CLOCK_Q']['full_settling_pass'])
            self.assertIsNone(observed['nodes']['CLOCK_Q']['event_exchange']['total_into_gate_devices_c'])
            missing = m['standard_cell_rb_experiment']['load_observers']['CLOCK_RESET']['ports']['NM_gate'].lower()
            (output/'peak.columns.json').write_text(json.dumps(dict(names=[n for n in names if n!=missing])))
            with self.assertRaises(ValueError):
                analyze.reset_observations(str(output),m)
        result = dict(full_history_source_energy={k:dict(net_delivered_j=1e-15) for k in m['source_power_ports']})
        result['full_history_source_energy']['RINPUT_PLUS']['net_delivered_j']=-.3e-15
        result['full_history_source_energy']['RINPUT_MINUS']['net_delivered_j']=.1e-15
        analyze.live.separate_energy(result,m)
        self.assertEqual(len(result['full_history_source_energy']),5)
        self.assertEqual(len(result['full_history_boundary_source_energy']),7)
        self.assertAlmostEqual(result['full_history_resistor_energy']['absorbed_j'],.2e-15,delta=1e-28)
        self.assertAlmostEqual(result['fixture_all_twelve_sources_net_work_j'],12e-15,delta=1e-28)


if __name__ == '__main__':
    unittest.main(verbosity=2)
