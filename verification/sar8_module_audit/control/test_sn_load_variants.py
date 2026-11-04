"""Conditional load builder contracts. Synthetic bias is confined to temp cases."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import prepare_first_event as base
import prepare_sn_load_variants as builder
import supplement_native_export as supplement

OWN = Path(__file__).resolve().parent


class LoadBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='_sn_load_test_',dir=OWN)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(OWN))
        self.addCleanup(self.temp.cleanup)
        self.names = ['time'] + supplement.SELECTIONS[builder.SOURCE]
        self.values = np.zeros((5,len(self.names)))
        self.values[:,0] = [0.,40.8e-9,41.08e-9,41.10e-9,supplement.STOP]
        for j in range(1,len(self.names)):
            self.values[:,j] = np.array([.001*j,.001*j,.002*j,.003*j,.003*j])
        self.proof = dict(synthetic_test_only=True,not_actual_collected_bias=True)

    def build(self,branches=('10',),name='case'):
        path = self.root/name
        identity = builder.make_case(branches,self.values,self.names,self.proof,path)
        return path,identity

    def test_native_devices_are_exact_replicas_and_original_v1_unchanged(self):
        baseline = (OWN/'first_event_v1/dut.scs').read_bytes()
        for branches in [('10',),('14',),('10','14')]:
            path,identity = self.build(branches,'case_'+''.join(branches))
            self.assertEqual(identity['native_MOS'],97+2*len(branches))
            self.assertEqual(identity['native_passives'],18)
            original = builder.frozen_base()[3]
            cells = base.cells(original)
            ports = cells['sar_adc8_join_r4'].replace('\\\n',' ').splitlines()[0].split()[2:]
            original_leaves = base.flatten(original,'sar_adc8_join_r4',dict(zip(ports,ports)))
            for item in identity['new_load_device_map'].values():
                source = original_leaves[item['original_instance']]
                self.assertEqual(item['model'],source['model'])
                self.assertEqual(item['parameters'],source['parameters'])
                self.assertEqual(item['conditional_bias_nodes'][1],builder.P+'SN')
            self.assertEqual((OWN/'first_event_v1/dut.scs').read_bytes(),baseline)
            for existing in (OWN/'first_event_v1/pwl').iterdir():
                self.assertEqual((path/'pwl'/existing.name).read_bytes(),existing.read_bytes())

    def test_bias_has_exact_native_rows_and_never_clamps_retained_output(self):
        path,identity = self.build(('10','14'))
        self.assertEqual(identity['retained_active_outputs_forced'],[])
        leaves = base.flatten((path/'dut.scs').read_text(),'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
        old = base.flatten((OWN/'first_event_v1/dut.scs').read_text(),'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
        old_nodes = {n for item in old.values() for n in item['nodes']}
        added = {n:item for n,item in leaves.items() if n not in old}
        for item in added.values():
            if item['model']=='vsource':
                self.assertNotIn(item['nodes'][0],old_nodes)
        for branch in ['10','14']:
            for suffix,signal in [('n','n'),('mid','x000.mid')]:
                actual = np.loadtxt(path/'pwl'/('bias_x0'+branch+'_'+suffix+'.pwl'))
                col = self.names.index('xdut.xctrl.xtim.x0'+branch+'.'+signal)
                np.testing.assert_array_equal(actual,self.values[:,[0,col]])

    def test_measurement_complete_for_SN_and_each_new_bias_node(self):
        for branches in [('10',),('10','14')]:
            path,identity = self.build(branches,'measure_'+''.join(branches))
            measure = json.loads((path/'measurement.json').read_text())
            self.assertEqual(len(measure['current_saves']),416+10*len(branches))
            self.assertEqual(len(measure['voltage_saves']),57+2*len(branches))
            self.assertEqual(len(measure['kcl_terms'][builder.P+'SN']),4+2*len(branches))
            for node in measure['critical_kcl_nodes']:
                self.assertTrue(set(measure['kcl_terms'][node]) <= set(measure['diagnostic_current_columns']))
            self.assertIn((builder.P+'SN').lower(),measure['diagnostic_voltage_columns'])
            self.assertIsNone(measure['acceptance_pass'])
            self.assertIn('conditional',measure['scope'].lower())
            self.assertEqual(identity['source_export_evidence'],self.proof)

    def test_frozen_analyzer_accepts_extended_measurement_synthetically(self):
        path,_ = self.build(('10','14'))
        measure = json.loads((path/'measurement.json').read_text())
        run = self.root/'synthetic_managed'
        for folder in [run/'inputs',run/'raw',run/'derived']:
            folder.mkdir(parents=True,exist_ok=True)
        (run/'inputs/measurement.json').write_text(json.dumps(measure))
        signals = sorted({n.lower() for n in measure['voltage_saves']+measure['current_saves']})
        raw = 'HEADER\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n'
        raw += ''.join('"%s" FLOAT DOUBLE\n'%s for s in signals)+'VALUE\n'
        for at in [0.,40.8e-9,41.08e-9,41.1e-9,measure['source_history_stop_s']]:
            raw += '"time" %.17g\n'%at
            raw += ''.join('"%s" %.17g\n'%(s,.99 if s=='vdd!' else 0.) for s in signals)
        (run/'raw/synthetic.tran.tran').write_text(raw+'END\n')
        (run/'raw/logStatus').write_text('tran_first PASS\n')
        (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
            native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2752']))))
        completed = subprocess.run([sys.executable,'-B',str(OWN/'first_event_analyze.py'),
            '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
        self.assertEqual(completed.returncode,0,completed.stderr)
        result = json.loads((run/'derived/result.json').read_text())
        self.assertEqual(result['missing_required_signals'],[])
        self.assertIsNone(result['acceptance_pass'])
        self.assertFalse(result['circuit_repair_claim'])
        self.assertTrue(result['CMI_warning_present'])

    def test_invalid_or_unavailable_bias_is_never_substituted(self):
        bad = self.values.copy(); bad[2,3] = float('nan')
        with self.assertRaisesRegex(ValueError,'native bias'):
            builder.make_case(('10',),bad,self.names,self.proof,self.root/'bad_nan')
        with self.assertRaisesRegex(ValueError,'native bias'):
            builder.make_case(('10',),self.values[:3],self.names,self.proof,self.root/'bad_short')
        with self.assertRaisesRegex(ValueError,'Only independent'):
            builder.make_case(('11',),self.values,self.names,self.proof,self.root/'bad_branch')
        self.assertFalse((self.root/'bad_nan').exists())
        self.assertFalse((self.root/'bad_short').exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
