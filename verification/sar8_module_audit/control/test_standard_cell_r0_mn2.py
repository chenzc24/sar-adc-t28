"""Focused private-clone and gate-loading accounting test, synthetic rows only."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import prepare_standard_cell_r0_mn2 as prepare
import standard_cell_analyze as standard

OWN,ROOT=prepare.OWN,prepare.ROOT


class StandardCellMN2Test(unittest.TestCase):
    def test_exact_private_multiplicity_and_total_native_gate_loading(self):
        package=OWN/'standard_cell_r0_mn2_v1'
        recipe=json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze=json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for folder in [package,prepare.SRC]:
            r=json.loads((folder/'recipe.suggested.yaml').read_bytes())
            for item in r['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe_item=next(i for i in recipe['inputs'] if i['name']=='probe_metadata.json')
        probe=json.loads((ROOT/probe_item['source']).read_bytes())
        source=(prepare.SRC/'dut.scs').read_text();changed=(package/'dut.scs').read_text()
        generated,clones=prepare.specialize_one(source)
        self.assertEqual(generated,changed);self.assertEqual(len(clones),4)
        old,_=prepare.standard.expanded_leaves(source,probe)
        new,_=prepare.standard.expanded_leaves(changed,probe)
        self.assertEqual(set(old),set(new))
        self.assertEqual({k for k in old if old[k]!=new[k]},{prepare.TARGET})
        self.assertEqual(prepare.base.cells(source)['sar8p_inv'],prepare.base.cells(changed)['sar8p_inv'])
        before=dict(re.findall(r'(\w+)=(\S+)',old[prepare.TARGET]['parameters']))
        after=dict(re.findall(r'(\w+)=(\S+)',new[prepare.TARGET]['parameters']))
        self.assertEqual(before['multi'],'1');self.assertEqual(after['multi'],'2')
        self.assertEqual({k for k in before if before[k]!=after[k]},{'multi'})
        self.assertEqual(new[prepare.TARGET]['nodes'],old[prepare.TARGET]['nodes'])
        for key in [prepare.P+'X019.X001.MN',prepare.P+'X020.RINPUT',prepare.P+'X001.X001.MP']:
            self.assertEqual(old[key],new[key])
        self.assertEqual((package/'test.scs').read_bytes(),(prepare.SRC/'test.scs').read_bytes())
        for p in (prepare.SRC/'pwl').glob('*.pwl'):self.assertEqual((package/'pwl'/p.name).read_bytes(),p.read_bytes())
        m=json.loads((package/'measurement.json').read_bytes());sm=json.loads((prepare.SRC/'measurement.json').read_bytes())
        for key in ['voltage_saves','current_saves','terminal_current_catalog','kcl_terms','critical_kcl_nodes','stress_voltage_pairs','source_power_ports','expected_initial_state']:
            self.assertEqual(m[key],sm[key])
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,437,61,609))
        self.assertEqual(m['standard_cell_experiment']['observed_mos'][prepare.TARGET]['group'],'changed_driver_NM')
        with tempfile.TemporaryDirectory(prefix='_stdcell_mn2_test_',dir=OWN) as folder:
            root=Path(folder).resolve();self.assertTrue(root.is_relative_to(OWN))
            fake=root/'synthetic.spi';fake.write_bytes(b'* synthetic library identity only\n')
            manifest=json.loads((package/'external_library.json').read_bytes())
            manifest.update(file=str(fake),**standard.file_identity(str(fake)))
            for scenario in ['complete','missing_changed_gate_current']:
                run=root/scenario
                for sub in ['inputs','raw','derived']:(run/sub).mkdir(parents=True)
                (run/'inputs/measurement.json').write_text(json.dumps(m));(run/'inputs/external_library.json').write_text(json.dumps(manifest))
                for item in recipe['inputs']:
                    if item['name'] in manifest['metadata_inputs']:(run/'inputs'/item['name']).write_bytes((ROOT/item['source']).read_bytes())
                names=sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
                missing=(prepare.TARGET+':2').lower()
                if scenario!='complete':names.remove(missing)
                text='HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'+''.join('"%s" FLOAT DOUBLE\n'%n for n in names)+'VALUE\n'
                times=[0.,1e-9,40.8e-9,41.075e-9,41.09e-9,m['source_history_stop_s']]
                input_v=[.99,1.04,.99,.9,.3,0.];left=[0.,0.,0.,.6,.99,.99];right=[0.,0.,0.,.3,.8,.99]
                powers=[];gn=[];gp=[]
                for at,x,l,r in zip(times,input_v,left,right):
                    v=dict.fromkeys(names,0.)
                    v.update({k:z for k,z in m['expected_initial_state']['values_v'].items() if k in v})
                    v.update({'vdd!':.99,'vvdd:1':-1e-6})
                    v[prepare.INPUT_NODE.lower()]=x
                    ni=-20e-6 if at in [41.075e-9,41.09e-9] else 0.
                    pi=-10e-6 if at in [41.075e-9,41.09e-9] else 0.
                    if missing in v:v[missing]=ni
                    v[(prepare.PM+':2').lower()]=pi
                    v[(prepare.P+'X001.X000.MN0:1').lower()]=-(ni+pi)
                    gn.append(ni);gp.append(pi)
                    v[(prepare.P+'LIVE').lower()]=l;v[(prepare.P+'X020.A1_FILTER').lower()]=r
                    current=(l-r)/10000.
                    v[(prepare.P+'X020.RINPUT:1').lower()]=current;v[(prepare.P+'X020.RINPUT:2').lower()]=-current
                    v[(prepare.TARGET+':1').lower()]=-current
                    v[(prepare.P+'X020.X000.MM1:2').lower()]=current
                    powers.append((l-r)*current)
                    if at>=41.09e-9:v['xdut.sample_int']=0.
                    text+='"time" %.17g\n'%at+''.join('"%s" %.17g\n'%(s,v[s]) for s in names)
                (run/'raw/synthetic.tran.tran').write_text(text+'END\n');(run/'raw/logStatus').write_text('tran_first PASS\n')
                (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                    native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2752']))))
                done=subprocess.run([sys.executable,'-B',str(OWN/'standard_cell_r0_mn2_analyze.py'),
                    '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
                if scenario!='complete':
                    self.assertNotEqual(done.returncode,0);self.assertIn('Required native TRACE/time sweep missing',done.stderr)
                    self.assertIn(missing,done.stderr);self.assertFalse((run/'derived/result.json').exists());continue
                self.assertEqual(done.returncode,0,done.stderr)
                result=json.loads((run/'derived/result.json').read_bytes());loading=result['changed_driver_input_loading']
                self.assertIsNone(result['acceptance_pass']);self.assertFalse(result['circuit_repair_claim']);self.assertTrue(result['CMI_warning_present'])
                self.assertEqual(result['comparison_source']['recipe_sha256'],prepare.HASH)
                self.assertEqual(len(result['full_history_voltage_stress']),609)
                for group,count in [('standard_cell',6),('changed_driver_NM',1),('retained_core',94)]:
                    self.assertEqual(result['physical_terminal_screen_groups'][group]['MOS'],count)
                self.assertEqual(loading['diagnostic_window_extrema']['changed_NM']['min'],-20e-6)
                expected_nm=sum(.5*(gn[i]+gn[i+1])*(times[i+1]-times[i]) for i in [3,4])
                expected_work=sum(.5*(input_v[i]*gn[i]+input_v[i+1]*gn[i+1])*(times[i+1]-times[i]) for i in [3,4])
                self.assertAlmostEqual(loading['event_exchange']['into_gate_devices_c']['changed_NM'],expected_nm,delta=1e-27)
                self.assertAlmostEqual(loading['event_exchange']['into_gate_terminal_work_j']['changed_NM'],expected_work,delta=1e-27)
                self.assertEqual(loading['event_exchange']['first_native_s'],times[3]);self.assertLess(loading['native_KCL_max_a'],1e-18)
                self.assertEqual(len(loading['falling_halfrail_s']),1);self.assertGreater(loading['fall_90_10_s'][0],0.)
                self.assertIsNone(loading['full_settling_pass'])
                label=m['standard_cell_experiment']['observed_mos'][prepare.TARGET]['six_pair_labels']['VGS']
                self.assertAlmostEqual(result['full_history_voltage_stress'][label]['max_abs_v'],1.04)
                self.assertEqual(result['full_history_voltage_stress'][label]['max_abs_time_s'],1e-9)
                self.assertEqual(len(result['full_history_source_energy']),5)
                expected_res=sum(.5*(a+z)*(t1-t0) for a,z,t0,t1 in zip(powers,powers[1:],times,times[1:]))
                self.assertAlmostEqual(result['full_history_resistor_energy']['absorbed_j'],expected_res,delta=1e-25)


if __name__=='__main__':
    unittest.main(verbosity=2)
