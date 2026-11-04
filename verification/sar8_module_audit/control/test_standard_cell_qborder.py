"""One focused two-gate/source-identity/KCL/native observation test; no simulator."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_standard_cell_qborder as prepare
import standard_cell_qborder_analyze as analyze

OWN, ROOT = prepare.OWN,prepare.ROOT


class QBOrderTest(unittest.TestCase):
    def test_only_gate_order_and_native_gate_load_mapping(self):
        package=OWN/'standard_cell_qborder_v1';recipe=json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze=json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for folder in [package,prepare.SRC]:
            for item in json.loads((folder/'recipe.suggested.yaml').read_bytes())['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe=json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
        oldtext=(prepare.SRC/'dut.scs').read_text();text=(package/'dut.scs').read_text()
        self.assertEqual(text,prepare.replace_qborder(oldtext))
        for master in ['sar8p_nand2','sar8p_inv','sar8audit_sr_rb_qbcap','sar8audit_nand_qbcap1','sar8audit_or_resetnand_tcb']:
            self.assertEqual(prepare.base.cells(text)[master],prepare.base.cells(oldtext)[master])
        old,oldlib=prepare.mapping.expand_eighteen(oldtext,probe);new,lib=prepare.mapping.expand_eighteen(text,probe)
        self.assertEqual(old.keys(),new.keys());self.assertEqual(oldlib,lib)
        self.assertEqual({k for k in old if old[k]!=new[k]},{prepare.NAND+'.MN0',prepare.NAND+'.MN1'})
        for name,gate in [('MN0',prepare.Q),('MN1',prepare.RB)]:
            key=prepare.NAND+'.'+name;expected=dict(old[key]);expected['nodes']=list(old[key]['nodes']);expected['nodes'][1]=gate
            self.assertEqual(new[key],expected)
        self.assertEqual(old[prepare.NAND+'.CMID'],new[prepare.NAND+'.CMID'])
        m=json.loads((package/'measurement.json').read_bytes());om=json.loads((prepare.SRC/'measurement.json').read_bytes())
        for key in ['voltage_saves','current_saves','source_power_ports','expected_initial_state']:
            self.assertEqual(m[key],om[key])
        changed=[p for p in m['terminal_current_catalog'] if m['terminal_current_catalog'][p]!=om['terminal_current_catalog'][p]]
        self.assertEqual(set(changed),{prepare.NAND+'.MN0:2',prepare.NAND+'.MN1:2'})
        for node,terms in m['kcl_terms'].items():
            self.assertEqual(set(terms),{p.lower() for p,item in m['terminal_current_catalog'].items() if item['node']==node})
        obs=m['standard_cell_rb_experiment']['load_observers']
        self.assertEqual(obs['RB']['ports']['QB_NM_gate'],prepare.NAND+'.MN1:2')
        self.assertEqual(set(obs['RB']['ports'].values()),set(prepare.complete_gate_ports(m,prepare.RB).values()))
        self.assertEqual(set(obs['CLOCK_Q']['ports'].values()),set(prepare.complete_gate_ports(m,prepare.Q).values()))
        self.assertIn(prepare.NAND+'.MN0:2',obs['CLOCK_Q']['ports'].values())
        self.assertNotIn(prepare.NAND+'.MN1:2',obs['CLOCK_Q']['ports'].values())
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,435,61,609))
        mos=m['standard_cell_experiment']['observed_mos']
        self.assertEqual(len({s for item in mos.values() for s in item['six_pair_labels'].values()}),606)
        for name,gate in [('MN0',prepare.Q),('MN1',prepare.RB)]:
            node=mos[prepare.NAND+'.'+name]['nodes'];d,g,s,b=node
            for suffix,endpoints in dict(VGS=(g,s),VGD=(g,d),VDS=(d,s),VGB=(g,b),VDB=(d,b),VSB=(s,b)).items():
                actual=m['stress_voltage_pairs'][mos[prepare.NAND+'.'+name]['six_pair_labels'][suffix]]
                self.assertEqual((actual['positive_node'],actual['negative_node'],actual['limit_abs_v']),(*endpoints,.99))
        self.assertFalse({prepare.RB.lower(),prepare.Q.lower(),(prepare.NAND+'.MID').lower()}.intersection(m['expected_initial_state']['values_v']))
        self.assertEqual(len(m['standard_cell_qborder_experiment']['acceptance_gaps']),2)
        self.assertEqual((package/'test.scs').read_bytes(),(prepare.SRC/'test.scs').read_bytes())
        for p in (prepare.SRC/'pwl').glob('*.pwl'):
            self.assertEqual((package/'pwl'/p.name).read_bytes(),p.read_bytes())
        with tempfile.TemporaryDirectory(prefix='_qborder_check_',dir=OWN) as temp:
            output=Path(temp).resolve();self.assertTrue(output.is_relative_to(OWN))
            names=['time']+sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
            (output/'peak.columns.json').write_text(json.dumps(dict(names=names)))
            times=[40.8e-9,41e-9,41.1e-9,41.2e-9,m['source_history_stop_s']];data=[]
            p,nand=prepare.P.lower(),prepare.NAND.lower()
            for i,t in enumerate(times):
                v=dict.fromkeys(names,0.);v['time']=t;v['vdd!']=.99
                v[p+'xclock.qb']=[.99,.99,.98,.9895,.99][i]
                v[nand+'.mid']=[.08,.08,.02,.001,0.][i]
                v[p+'xclock.rb']=0. if i<2 else .99;v[p+'clock_reset']=.99 if i<2 else 0.
                if i in [1,2,3]:
                    factor=1. if i in [1,2] else .1
                    ports={nand+'.mn0:2':5e-6,nand+'.mp1:2':2e-6,
                        p+'x025.x000.mn:2':1e-6,p+'x025.x000.mp:2':-.5e-6,
                        nand+'.mn1:2':3e-6,nand+'.mp0:2':1e-6,
                        p+'xclock.x002.mp1:1':-7.5e-6,p+'xclock.x000.mm0:1':-4e-6,
                        nand+'.mn0:1':1e-6,nand+'.mn0:3':-1e-6,
                        nand+'.mn1:1':9e-6,nand+'.mp1:1':-1e-6,nand+'.cmid:1':-8e-6}
                    for port,amps in ports.items():
                        v[port]=amps*factor
                data.append(v)
            (output/'peak.native.bin').write_bytes(b''.join(struct.pack('<'+'d'*len(names),*(v[n] for n in names)) for v in data))
            reset=analyze.rb.reset_observations(str(output),m)
            interval=times[2]-times[1]+.5*(1.+.1)*(times[3]-times[2])+.5*.1*(times[4]-times[3])
            self.assertAlmostEqual(reset['nodes']['RB']['event_exchange']['into_gate_devices_c']['QB_NM_gate'],3e-6*interval,delta=1e-27)
            self.assertAlmostEqual(reset['nodes']['CLOCK_Q']['event_exchange']['total_into_gate_devices_c'],7.5e-6*interval,delta=1e-27)
            self.assertTrue(all(reset['nodes'][n]['native_KCL_max_a']<1e-18 for n in ['RB','CLOCK_Q']))
            storage=analyze.source.storage_observations(str(output),m,reset)
            minimum=storage['phases']['QB_minimum']
            self.assertAlmostEqual(minimum['devices']['MN0']['VGS_v'],-.02)
            self.assertAlmostEqual(minimum['devices']['MN1']['VGS_v'],.99)
            self.assertLess(storage['post_RB90_exchange']['ports']['CMID:1']['signed_into_device_c'],0.)
            coverage=analyze.coverage(reset,m)
            self.assertFalse(coverage['full_set_operation_qualified']);self.assertFalse(coverage['full_reset_from_Qhigh_qualified'])
            self.assertEqual(coverage['set_input_rises'],[]);self.assertEqual(coverage['reset_input_rises'],[])
            missing=(prepare.NAND+'.MN0:2').lower()
            (output/'peak.columns.json').write_text(json.dumps(dict(names=[n for n in names if n!=missing])))
            with self.assertRaises(ValueError):
                analyze.rb.reset_observations(str(output),m)


if __name__=='__main__':
    unittest.main(verbosity=2)
