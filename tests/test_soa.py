from pathlib import Path
import sys
import unittest
import json
import tempfile

PATH=Path(__file__).resolve().parents[1]/'tools/saradc/measure'
sys.path.insert(0,str(PATH))
from soa import over_intervals,sliding_max,analyze
from soa_topology import definitions,flatten,save_voltage_node


class SoaTests(unittest.TestCase):
    def test_signed_crossing_has_two_separate_overstress_pieces(self):
        pieces=over_intervals(0.,10.,-2.,2.,1.)
        assert pieces==[(0.,2.5),(7.5,10.)]


    def test_exact_threshold_is_not_overstress(self):
        assert over_intervals(0.,1.,1.1,1.1,1.1)==[]


    def test_window_sums_multiple_short_pulses(self):
        duration,end=sliding_max([[1.,1.06],[2.,2.06]],10.,20.)
        self.assertAlmostEqual(duration,.12)
        assert end==2.06


    def test_window_clips_long_pulse_and_includes_startup(self):
        assert sliding_max([[0.,25.]],10.,30.)[0]==10.
        assert sliding_max([[0.,.11]],10.,20.)[0]==.11


    def test_window_finds_maximum_at_shifted_start_not_only_pulse_end(self):
        intervals=[[0.,3.],[5.,9.],[10.,20.]]
        value,end=sliding_max(intervals,10.,20.)
        assert value==10.


    def test_hierarchy_binds_ports_globals_and_library_internal_nodes(self):
        a=definitions('subckt top I O\nX1 (I O VDD! 0) inv\nends top')
        a.update(definitions('.subckt inv A Y VDD VSS\nMM1 net A VSS VSS nch_mac l=30n\nMM2 Y net VDD VDD pch_mac l=30n\n.ends',True))
        result=flatten(a,'top',['vin','vout'])
        assert result['devices'][0]['nodes']==['XDUT.X1.net','vin','0','0']
        assert result['devices'][1]['nodes']==['vout','XDUT.X1.net','VDD!','VDD!']


    def test_unknown_leaf_fails_closed(self):
        a=definitions('subckt top I O\nX1 (I O) missing\nends top')
        with self.assertRaisesRegex(ValueError,'Unresolved'):flatten(a,'top',['i','o'])

    def test_lpe_terminal_net_is_saved_as_a_voltage(self):
        top=definitions('subckt top A Z\nX1 (A Z 0) gate\nends top')
        top.update(definitions('.subckt gate A Z VSS\nR1 A M1:GATE 10\nC1 M1:GATE VSS 1f\n'
                               'MM1 Z M1:GATE VSS VSS nch_mac\n.ends',True))
        circuit=flatten(top,'top',['a','z'])
        self.assertEqual(circuit['other_leaves'],{'resistor':1,'capacitor':1})
        name=circuit['devices'][0]['nodes'][1]
        self.assertEqual(name,'XDUT.X1.M1:GATE')
        saved=save_voltage_node(name)
        self.assertEqual(saved,r'XDUT.X1.M1\:GATE')
        self.assertEqual(save_voltage_node(saved),saved)

    def test_native_analysis_detects_duration_failure_and_body_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'inputs').mkdir();(p/'raw').mkdir()
            rule={'rule_id':'test','scope':{'thin_oxide_mos_models':['nch_mac'],
                  'thin_oxide_moscap_models':[],'thick_oxide_models_outside_this_rule':[]},
                  'limits':{'continuous_V':1.1,'peak_V':1.29,'window_s':1e-8,'max_over_s':1e-10}}
            ctx={'run_id':'test','source_run_id':'source','corner':'tt','rule':rule,
                 'rule_sha256':'test','expected_stop_s':1e-9,'expected_codes':[0]}
            (p/'inputs/soa_context.json').write_text(json.dumps(ctx))
            (p/'inputs/terminal_inventory.json').write_text(json.dumps({'devices':[
                {'instance':'M','model':'nch_mac','nodes':['D','0','0','0']}]}))
            wave='SWEEP\n"time" FLOAT\nTRACE\n"D" FLOAT\nVALUE\n'
            for t,v in [(0,1.2),(2e-10,1.2),(2.01e-10,0),(1e-9,0)]:
                wave+='"time" %.17g\n"D" %.17g\n'%(t,v)
            (p/'raw/tran_short.tran.tran').write_text(wave+'END\n')
            (p/'spectre.out').write_text('BPROBE,0,0,0\n')
            result=analyze(str(p),str(p/'derived'))
            self.assertEqual(result['verdict'],'violation')
            self.assertEqual(result['violation_pair_count'],2)
            self.assertGreater(result['worst_duration']['max_sliding_over_s'],2e-10)
            self.assertTrue(result['observer_codes_pass'])
            rows=json.loads((p/'derived/terminal_results.json').read_text())
            self.assertEqual(next(r for r in rows if r['terminal_pair']=='bd')['verdict'],'outside_rule')

if __name__ == "__main__":unittest.main()
