"""One focused single-capacitor/source-identity/native-storage measurement test."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_standard_cell_qbcap as prepare
import standard_cell_qbcap_analyze as analyze

OWN, ROOT = prepare.OWN, prepare.ROOT


class QBCapTest(unittest.TestCase):
    def test_only_cap_multi_and_native_charge_recovery_coverage(self):
        package=OWN/'standard_cell_qbcap_v1';recipe=json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze=json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for folder in [package,prepare.SRC]:
            for item in json.loads((folder/'recipe.suggested.yaml').read_bytes())['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe=json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
        oldtext=(prepare.SRC/'dut.scs').read_text();text=(package/'dut.scs').read_text()
        self.assertEqual(text,prepare.replace_qbcap(oldtext))
        for master in ['sar8p_nand2','sar8p_inv','sar8audit_sr_rb_tcb','sar8audit_or_resetnand_tcb']:
            self.assertEqual(prepare.base.cells(text)[master],prepare.base.cells(oldtext)[master])
        old,oldlib=prepare.source.expand_eighteen(oldtext,probe);new,lib=prepare.source.expand_eighteen(text,probe)
        self.assertEqual(old.keys(),new.keys());self.assertEqual(oldlib,lib)
        self.assertEqual([k for k in old if old[k]!=new[k]],[prepare.TARGET])
        expected=dict(old[prepare.TARGET]);expected['parameters']=expected['parameters'].replace('multi=2','multi=1')
        self.assertEqual(expected,new[prepare.TARGET]);self.assertEqual(len(old)-1,127)
        m=json.loads((package/'measurement.json').read_bytes());om=json.loads((prepare.SRC/'measurement.json').read_bytes())
        for key in ['voltage_saves','current_saves','terminal_current_catalog','critical_kcl_nodes','kcl_terms',
                    'stress_voltage_pairs','source_power_ports','standard_cell_experiment']:
            self.assertEqual(m[key],om[key])
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,435,61,609))
        self.assertEqual(len(lib),18)
        for item in lib.values():
            for port in item['requested_numeric_terminal_currents']:
                self.assertIn(port,m['terminal_current_catalog'])
        self.assertEqual((package/'test.scs').read_bytes(),(prepare.SRC/'test.scs').read_bytes())
        for path in (prepare.SRC/'pwl').glob('*.pwl'):
            self.assertEqual((package/'pwl'/path.name).read_bytes(),path.read_bytes())
        with tempfile.TemporaryDirectory(prefix='_qbcap_check_',dir=OWN) as temp:
            output=Path(temp).resolve();self.assertTrue(output.is_relative_to(OWN))
            names=['time']+sorted({s.lower() for s in m['voltage_saves']+m['current_saves']})
            (output/'peak.columns.json').write_text(json.dumps(dict(names=names)))
            times=[40.8e-9,41e-9,41.1e-9,41.2e-9,m['source_history_stop_s']]
            data=[];p=prepare.P.lower();nand=prepare.NAND.lower()
            for i,t in enumerate(times):
                v=dict.fromkeys(names,0.);v['time']=t;v['vdd!']=.99
                v[prepare.QB.lower()]=[.99,.99,.88,.9895,.99][i]
                v[prepare.MID.lower()]=[.08,.08,.33,.64,.65][i]
                v[p+'xclock.rb']=0. if i<2 else .99
                v[p+'clock_reset']=.99 if i<2 else 0.
                if i in [1,2,3]:
                    scale=1. if i in [1,2] else .1
                    for port,amps in [('mn0:1',10e-6),('mn0:2',-.5e-6),('mn0:3',-9e-6),('mn0:4',-.5e-6),
                                      ('mn1:1',1e-6),('mn1:3',-1e-6),('mp1:1',-10e-6),('mp1:3',10e-6),('cmid:1',8e-6)]:
                        v[nand+'.'+port]=amps*scale
                    v['vvdd:1']=-10e-6*scale
                data.append(v)
            def save():
                (output/'peak.native.bin').write_bytes(b''.join(struct.pack('<'+'d'*len(names),*(v[n] for n in names)) for v in data))
            save();reset=analyze.rb.reset_observations(str(output),m)
            got=analyze.storage_observations(str(output),m,reset)
            self.assertEqual(got['actual_native_capacitor_multi'],1)
            self.assertFalse(got['current_multiplicity_rescaling_applied'])
            self.assertAlmostEqual(got['QB_minimum_to_within_1mV_s'],times[3]-times[2],delta=1e-24)
            exchange=got['post_RB90_exchange'];self.assertEqual(exchange['first_native_s'],times[2])
            cap=exchange['ports']['CMID:1']
            self.assertAlmostEqual(cap['signed_into_device_c'],.5*(8e-6+.8e-6)*(times[3]-times[2]),delta=1e-28)
            self.assertAlmostEqual(cap['into_device_terminal_work_j'],.5*(.33*8e-6+.64*.8e-6)*(times[3]-times[2]),delta=1e-28)
            balance=sum(exchange['ports'][s]['signed_into_device_c'] for s in ['MN0:3','MN1:1','CMID:1'])
            self.assertLess(abs(balance),1e-28)
            phase=got['phases']['QB_minimum'];self.assertAlmostEqual(phase['devices']['MN0']['VGS_v'],.66)
            self.assertAlmostEqual(phase['devices']['MN0']['VDS_v'],.55)
            self.assertTrue(all(abs(v)<1e-18 for v in phase['KCL_sum_a'].values()))
            self.assertEqual((len(phase['original_source_port_delivered_power_w']),len(phase['boundary_source_port_delivered_power_w']),len(phase['passive_R0_port_delivered_power_w'])),(5,7,2))
            self.assertAlmostEqual(phase['original_source_port_delivered_power_w']['VDD'],.99*10e-6,delta=1e-20)
            self.assertIsNone(got['phases']['QB_minimum']['devices']['MN0'].get('region'))
            data[-1][prepare.QB.lower()]=.98;save()
            unknown=analyze.storage_observations(str(output),m,reset)
            self.assertIsNone(unknown['QB_minimum_to_within_1mV_s'])
            self.assertIsNone(unknown['phases']['within_1mV_until_stop'])
            self.assertIsNone(unknown['post_RB90_exchange'])
            missing=(prepare.NAND+'.CMID:1').lower()
            (output/'peak.columns.json').write_text(json.dumps(dict(names=[n for n in names if n!=missing])))
            with self.assertRaises(ValueError):
                analyze.storage_observations(str(output),m,reset)


if __name__=='__main__':
    unittest.main(verbosity=2)
