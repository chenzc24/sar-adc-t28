"""Focused exact-change/native-accounting test; all waveform rows are synthetic."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import prepare_standard_cell_r0 as prepare
import standard_cell_analyze as standard

OWN, ROOT = prepare.OWN, prepare.ROOT


class StandardCellR0Test(unittest.TestCase):
    def test_two_A1_gates_one_R0_and_strict_native_accounting(self):
        package=OWN/'standard_cell_r0_v1'
        recipe=json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze=json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for item in recipe['inputs']:
            self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        source_recipe=json.loads((prepare.SRC/'recipe.suggested.yaml').read_bytes())
        for item in source_recipe['inputs']:
            self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe_item=next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
        probe=json.loads((ROOT/probe_item['source']).read_bytes())
        source=(prepare.SRC/'dut.scs').read_text()
        text=(package/'dut.scs').read_text()
        self.assertEqual(text,prepare.insert_resistor(source)[0])
        old,_=prepare.standard.expanded_leaves(source,probe)
        new,_=prepare.standard.expanded_leaves(text,probe)
        gates={prepare.P+'X020.X000.MM4',prepare.P+'X020.X000.MM1'}
        self.assertEqual(set(new)-set(old),{prepare.RESISTOR})
        self.assertFalse(set(old)-set(new))
        self.assertEqual({k for k in old if old[k]!=new[k]},gates)
        for k in gates:self.assertEqual(new[k]['nodes'][1],prepare.NEW_NODE)
        self.assertEqual(new[prepare.RESISTOR],dict(model='rupolym',nodes=[prepare.P+'LIVE',prepare.NEW_NODE],parameters='l=17.13u w=1u m=1 multi=(1)'))
        fanout={(k,i+1) for k,v in new.items() for i,n in enumerate(v['nodes']) if n==prepare.NEW_NODE}
        self.assertEqual(fanout,{(prepare.RESISTOR,2)}|{(g,2) for g in gates})
        strip=lambda t:''.join(s for s in t.splitlines(True) if not s.startswith('save '))
        self.assertEqual(strip((package/'test.scs').read_text()),strip((prepare.SRC/'test.scs').read_text()))
        for p in (prepare.SRC/'pwl').glob('*.pwl'):
            self.assertEqual((package/'pwl'/p.name).read_bytes(),p.read_bytes())
        m=json.loads((package/'measurement.json').read_bytes())
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,437,61,609))
        self.assertEqual(m['stress_voltage_pairs']['MP1_VSG']['negative_node'],prepare.NEW_NODE)
        self.assertEqual(m['stress_voltage_pairs']['MP1_VGD']['positive_node'],prepare.NEW_NODE)
        source_m=json.loads((prepare.SRC/'measurement.json').read_bytes())
        self.assertEqual(set(m['stress_voltage_pairs']),set(source_m['stress_voltage_pairs']))
        for k,pair in m['stress_voltage_pairs'].items():
            self.assertEqual(pair['limit_abs_v'],.99)
        a1_terms=m['kcl_terms'][prepare.NEW_NODE]
        self.assertEqual(set(a1_terms),{(prepare.RESISTOR+':2').lower()}|{(g+':2').lower() for g in gates})
        for port,node in [(1,prepare.P+'LIVE'),(2,prepare.NEW_NODE)]:
            self.assertEqual(m['terminal_current_catalog'][prepare.RESISTOR+':'+str(port)]['node'],node)
        with tempfile.TemporaryDirectory(prefix='_stdcell_r0_test_',dir=OWN) as folder:
            root=Path(folder).resolve();self.assertTrue(root.is_relative_to(OWN))
            fake=root/'synthetic.spi';fake.write_bytes(b'* synthetic identity only\n')
            manifest=json.loads((package/'external_library.json').read_bytes())
            manifest.update(file=str(fake),**standard.file_identity(str(fake)))
            for scenario in ['complete','missing_RINPUT_terminal2']:
                run=root/scenario
                for sub in ['inputs','raw','derived']:(run/sub).mkdir(parents=True)
                (run/'inputs/measurement.json').write_text(json.dumps(m))
                (run/'inputs/external_library.json').write_text(json.dumps(manifest))
                for item in recipe['inputs']:
                    if item['name'] in manifest['metadata_inputs']:
                        (run/'inputs'/item['name']).write_bytes((ROOT/item['source']).read_bytes())
                names=sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
                missing=(prepare.RESISTOR+':2').lower()
                if scenario!='complete':names.remove(missing)
                text='HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join('"%s" FLOAT DOUBLE\n'%n for n in names)+'VALUE\n'
                times=[0.,1e-9,40.8e-9,41e-9,41.09e-9,m['source_history_stop_s']]
                left=[0.,0.,0.,.6,.99,.99];right=[0.,0.,0.,.3,.8,.99]
                powers=[]
                for at,l,r in zip(times,left,right):
                    v=dict.fromkeys(names,0.)
                    v.update({k:z for k,z in m['expected_initial_state']['values_v'].items() if k in v})
                    v.update({'vdd!':.99,'vvdd:1':-1e-6})
                    v[(prepare.P+'LIVE').lower()]=l;v[prepare.NEW_NODE.lower()]=r
                    current=(l-r)/10000.
                    v[(prepare.RESISTOR+':1').lower()]=current
                    if missing in v:v[missing]=-current
                    v[(prepare.P+'X001.X001.MN:1').lower()]=-current
                    v[(prepare.P+'X020.X000.MM1:2').lower()]=current
                    powers.append((l-r)*current)
                    if at==1e-9:v[(prepare.P+'X020.N').lower()]=1.05
                    if at>=41.09e-9:v['xdut.sample_int']=0.
                    text+='"time" %.17g\n'%at+''.join('"%s" %.17g\n'%(n,v[n]) for n in names)
                (run/'raw/synthetic.tran.tran').write_text(text+'END\n')
                (run/'raw/logStatus').write_text('tran_first PASS\n')
                (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                    native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2752']))))
                done=subprocess.run([sys.executable,'-B',str(OWN/'standard_cell_r0_analyze.py'),
                    '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
                if scenario!='complete':
                    self.assertNotEqual(done.returncode,0)
                    self.assertIn('Required native TRACE/time sweep missing',done.stderr)
                    self.assertIn(missing,done.stderr)
                    self.assertFalse((run/'derived/result.json').exists());continue
                self.assertEqual(done.returncode,0,done.stderr)
                result=json.loads((run/'derived/result.json').read_bytes())
                self.assertIsNone(result['acceptance_pass']);self.assertFalse(result['circuit_repair_claim'])
                self.assertTrue(result['CMI_warning_present'])
                self.assertEqual(len(result['full_history_voltage_stress']),609)
                self.assertEqual(len(result['standard_cell_native_current_bindings']),6)
                self.assertEqual(len(result['resistor_native_current_bindings']),2)
                self.assertEqual(len(result['full_history_source_energy']),5)
                expected=sum(.5*(a+z)*(t1-t0) for a,z,t0,t1 in zip(powers,powers[1:],times,times[1:]))
                self.assertAlmostEqual(result['full_history_resistor_energy']['absorbed_j'],expected,delta=1e-25)
                self.assertAlmostEqual(result['full_history_source_energy']['VDD']['net_delivered_j'],.99e-6*times[-1],delta=1e-25)
                metrics=result['series_resistor_metrics']
                self.assertAlmostEqual(metrics['apparent_V_over_I_ohm']['min'],10000.)
                self.assertAlmostEqual(metrics['apparent_V_over_I_ohm']['max'],10000.)
                self.assertEqual(metrics['max_two_port_current_sum_a'],0.)
                self.assertGreater(metrics['A1_first_halfrail_relative_LIVE_s'],0.)
                self.assertIsNone(metrics['nodes'][prepare.NEW_NODE.lower()]['full_settling_pass'])
                self.assertEqual(result['node_kcl'][prepare.NEW_NODE.lower()]['max_abs_a'],0.)
                self.assertEqual(result['full_history_voltage_stress']['INV_MN_VGS']['max_abs_time_s'],1e-9)


if __name__=='__main__':
    unittest.main(verbosity=2)
