"""One focused measurement-delta/unknown-coverage/native-trace check."""
import copy
from pathlib import Path
import tempfile
import unittest

import prepare_standard_cell_storage_v2 as prepare
import standard_cell_storage_v2_analyze as adapter


class StorageMeasureV2Test(unittest.TestCase):
    def test_only_measurement_changes_and_unmeasured_is_not_zero(self):
        boundaries=prepare.read(prepare.V1/'load_boundaries.json')
        for tag in ['ff','ss']:
            old=prepare.read(prepare.V1/tag/'measurement.json')
            new=prepare.measurement(old,boundaries)
            allowed={'scope','current_saves','terminal_current_catalog','kcl_terms','critical_kcl_nodes','storage','selected_current_coverage'}
            self.assertEqual({k:v for k,v in old.items() if k not in allowed},
                             {k:v for k,v in new.items() if k not in allowed})
            s=copy.deepcopy(old['storage']);s.update(raw_all_actual_MOS_ports=False,full_history_all_KCL=False)
            self.assertEqual(s,new['storage'])
            self.assertEqual(len(new['voltage_saves']),980)
            self.assertEqual(len(new['stress_voltage_pairs']),11220)
            self.assertEqual(len(new['storage']['observers']),26)
            self.assertEqual(len(new['current_saves']),89)
            coverage=new['selected_current_coverage']
            self.assertEqual({k:len(v) for k,v in coverage['groups'].items()},dict(external_sources=7,SR=34,RC=48))
            self.assertEqual(coverage['unsaved_current_count'],7466)
            self.assertFalse(new['kcl_terms'])
            before=(prepare.V1/tag/'test.scs').read_text();after=prepare.save_only_deck(before,new)
            nonsave=lambda t:''.join(l for l in t.splitlines(True) if not l.startswith('save '))
            self.assertEqual(nonsave(before),nonsave(after))
            saves={l[5:] for l in after.splitlines() if l.startswith('save ')}
            self.assertEqual(saves,set(new['voltage_saves']+new['current_saves']))
            result=adapter.add_coverage(dict(node_kcl={}),new)
            self.assertIsNone(result['KCL_coverage']['whole_fixture_KCL_pass'])
            self.assertEqual(result['KCL_coverage']['status'],'unmeasured')
            self.assertFalse(result['terminal_current_coverage']['all_actual_MOS_terminal_currents_measured'])
            self.assertTrue(result['voltage_terminal_screen_coverage']['all_original_voltage_and_physical_pairs_preserved'])
            with self.assertRaisesRegex(ValueError,'no complete KCL'):
                adapter.add_coverage(dict(node_kcl={'fabricated':0}),new)
            broken=copy.deepcopy(new);broken['current_saves'].pop()
            with self.assertRaisesRegex(ValueError,'saved set'):
                adapter.add_coverage(dict(node_kcl={}),broken)
        # Missing a deliberately selected native current still hard-fails.
        with tempfile.TemporaryDirectory(prefix='_std_v2_trace_',dir=prepare.OWN) as t:
            root=Path(t);raw=root/'incomplete.tran.tran';out=root/'derived';out.mkdir()
            raw.write_text('SWEEP\n"time" FLOAT DOUBLE\nTRACE\n"vdd!" FLOAT DOUBLE\n"q" FLOAT DOUBLE\nVALUE\n"time" 0\n"vdd!" 0.99\n"q" 0\nEND\n')
            cfg=dict(voltage_saves=['VDD!','Q'],current_saves=['MISSING:1'],kcl_terms={},critical_kcl_nodes=[],
                     diagnostic_current_columns=[],diagnostic_voltage_columns=['Q'],diagnostic_start_s=0.,diagnostic_stop_s=1e-9,
                     source_history_stop_s=1e-9,stress_voltage_pairs={},source_power_ports={},expected_edges={},
                     max_derived_binary_bytes=1024,expected_native_peak=dict(node='Q',value_v=0.,time_s=0.),
                     expected_initial_state=dict(values_v={'VDD!':.99}),scope='synthetic missing selected trace',
                     proposed_reproduction_contract={})
            with self.assertRaisesRegex(ValueError,'TRACE/time sweep missing'):
                adapter.frozen.native.summarize(str(raw),cfg,str(out))


if __name__=='__main__':unittest.main()
