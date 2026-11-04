"""One focused CLOCK_RESET NAND mapping/coverage check; no Spectre invocation."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_standard_cell_resetnand as prepare
import standard_cell_resetnand_analyze as analyze

OWN, ROOT = prepare.OWN, prepare.ROOT


class ResetNANDTest(unittest.TestCase):
    def test_exact_nand_mapping_and_native_measurement_coverage(self):
        folder = OWN/'standard_cell_resetnand_v1'
        recipe = json.loads((folder/'recipe.suggested.yaml').read_bytes())
        freeze = json.loads((folder/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((folder/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for package in [folder,prepare.SRC]:
            for item in json.loads((package/'recipe.suggested.yaml').read_bytes())['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe = json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
        oldtext = (prepare.SRC/'dut.scs').read_text(); text = (folder/'dut.scs').read_text()
        self.assertEqual(text,prepare.replace_resetnand(oldtext))
        for master in ['sar8p_or2','sar8p_nand2','sar8p_inv','sar8audit_sr_rb_tcb']:
            self.assertEqual(prepare.base.cells(text)[master],prepare.base.cells(oldtext)[master])
        old,_ = prepare.rb.expand_fourteen(oldtext,probe)
        new,library = prepare.expand_eighteen(text,probe)
        s,p,o = prepare.TARGET,prepare.P,prepare.OR
        self.assertEqual(set(old)-set(new),{s+'.'+x for x in ['MP0','MP1','MN0','MN1','CMID']})
        self.assertEqual(set(new)-set(old),{s+'.'+x for x in ['MM4','MM9','MM1','MM2']})
        self.assertEqual(len(set(old)&set(new)),124)
        for key in set(old)&set(new):
            self.assertEqual(old[key],new[key])
        self.assertEqual(new[s+'.MM4']['nodes'],[p+'CLOCK_RESET',o+'.AB',s+'.net10','0'])
        self.assertEqual(new[s+'.MM9']['nodes'],[s+'.net10',o+'.BB','0','0'])
        self.assertEqual(new[s+'.MM1']['nodes'],[p+'CLOCK_RESET',o+'.AB','VDD!','VDD!'])
        self.assertEqual(new[s+'.MM2']['nodes'],[p+'CLOCK_RESET',o+'.BB','VDD!','VDD!'])
        m = json.loads((folder/'measurement.json').read_bytes())
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,435,61,609))
        self.assertNotIn(s+'.MID',m['voltage_saves']);self.assertIn(s+'.net10',m['voltage_saves'])
        self.assertNotIn(s+'.CMID:1',m['current_saves'])
        self.assertEqual(m['standard_cell_resetnand_experiment']['removed_explicit_capacitor'],old[s+'.CMID'])
        self.assertEqual(m['standard_cell_resetnand_experiment']['added_explicit_capacitors'],[])
        mos = m['standard_cell_experiment']['observed_mos']
        self.assertEqual((len(mos),len({label for item in mos.values() for label in item['six_pair_labels'].values()}),len(library)),(101,606,18))
        self.assertTrue(all(item['limit_abs_v']==.99 for item in m['stress_voltage_pairs'].values()))
        for item in library.values():
            for port in item['requested_numeric_terminal_currents']:
                self.assertIn(port,m['terminal_current_catalog'])
        for node,terms in m['kcl_terms'].items():
            self.assertEqual(set(terms),{port.lower() for port,item in m['terminal_current_catalog'].items() if item['node']==node})
        for path in (prepare.SRC/'pwl').glob('*.pwl'):
            self.assertEqual((folder/'pwl'/path.name).read_bytes(),path.read_bytes())
        strip = lambda t: ''.join(line for line in t.splitlines(True) if not line.startswith('save '))
        self.assertEqual(strip((folder/'test.scs').read_text()),strip((prepare.SRC/'test.scs').read_text()))
        with tempfile.TemporaryDirectory(prefix='_resetnand_stage_check_',dir=OWN) as temp:
            output = Path(temp).resolve();self.assertTrue(output.is_relative_to(OWN))
            names = ['time']+sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
            (output/'peak.columns.json').write_text(json.dumps(dict(names=names)))
            times = [40.8e-9,41e-9,41.1e-9,m['source_history_stop_s']];blobs=[]
            for i,t in enumerate(times):
                v = dict.fromkeys(names,0.);v['time']=t;v['vdd!']=.99
                v[(o+'.AB').lower()] = 0. if i<2 else .99
                v[(o+'.BB').lower()] = .99
                v[(p+'CLOCK_RESET').lower()] = .99 if i<2 else 0.
                v[(p+'XCLOCK.RB').lower()] = 0. if i<2 else .99
                v[(p+'XCLOCK.QB').lower()]=.99;v[(p+'XCLOCK.SN').lower()]=.99
                if i in [1,2]:
                    spec = m['standard_cell_resetnand_experiment']['load_observers']['AB']['ports']
                    v[spec['NM_gate'].lower()]=5e-6;v[spec['PM_gate'].lower()]=3e-6
                    v[(o+'.X000.MP:1').lower()]=-8e-6
                    spec = m['standard_cell_resetnand_experiment']['load_observers']['BB']['ports']
                    v[spec['NM_gate'].lower()]=-2e-6;v[spec['PM_gate'].lower()]=1e-6
                    v[(o+'.X001.MP:1').lower()]=1e-6
                blobs.append(struct.pack('<'+'d'*len(names),*(v[n] for n in names)))
            (output/'peak.native.bin').write_bytes(b''.join(blobs))
            observed = analyze.nand_input_loading(str(output),m)
            self.assertEqual(set(observed),{'AB','BB'})
            self.assertTrue(all(item['native_KCL_max_a']<1e-18 for item in observed.values()))
            interval = times[2]-times[1]+.5*(times[3]-times[2])
            self.assertAlmostEqual(observed['AB']['event_exchange']['into_gate_devices_c']['NM_gate'],5e-6*interval,delta=1e-27)
            self.assertAlmostEqual(observed['BB']['event_exchange']['total_into_gate_devices_c'],-1e-6*interval,delta=1e-27)
            self.assertEqual(len(observed['AB']['rising_halfrail_s']),1)
            self.assertEqual(observed['BB']['rising_halfrail_s'],[])
            reset = analyze.rb.reset_observations(str(output),m)
            self.assertEqual(len(reset['reset_release_R_fall_to_RB_rise']),1)
            self.assertEqual(reset['reset_assert_R_rise_to_RB_fall'],[])
            self.assertIsNone(reset['nodes']['CLOCK_Q']['event_exchange']['total_into_gate_devices_c'])
            self.assertIn('RB',reset['excursion_widths']['nodes'])
            missing = m['standard_cell_resetnand_experiment']['load_observers']['AB']['ports']['NM_gate'].lower()
            (output/'peak.columns.json').write_text(json.dumps(dict(names=[n for n in names if n!=missing])))
            with self.assertRaises(ValueError):
                analyze.nand_input_loading(str(output),m)
        result = dict(full_history_source_energy={k:dict(net_delivered_j=1e-15) for k in m['source_power_ports']})
        result['full_history_source_energy']['RINPUT_PLUS']['net_delivered_j']=-.3e-15
        result['full_history_source_energy']['RINPUT_MINUS']['net_delivered_j']=.1e-15
        analyze.live.separate_energy(result,m)
        self.assertEqual(len(result['full_history_source_energy']),5)
        self.assertEqual(len(result['full_history_boundary_source_energy']),7)
        self.assertAlmostEqual(result['full_history_resistor_energy']['absorbed_j'],.2e-15,delta=1e-28)
        self.assertAlmostEqual(result['fixture_all_twelve_sources_net_work_j'],12e-15,delta=1e-28)


if __name__=='__main__':
    unittest.main(verbosity=2)
