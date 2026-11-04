"""Independent quantization, timing cancellation and model-parameter checks."""
import math
import json
from pathlib import Path
import re
import unittest

from design.behav.python.sar_adc import AdcSpec,AnalogConfig,SarAdcModel
from tools.saradc.behavioral import check_generated


class BehavioralChecks(unittest.TestCase):
    def setUp(self):
        self.model=SarAdcModel()

    def test_all_256_centers_against_integer_code_oracle(self):
        m=self.model
        for k in range(256):
            vin=-m.spec.vref+(k+0.5)*m.spec.lsb
            r=m.convert(vin)
            self.assertEqual(r.code,k)
            self.assertTrue(r.completed)
            self.assertEqual(r.counts,(8,8,8,16))

    def test_all_transition_flanks_and_ties(self):
        m=self.model
        for k in range(1,256):
            v=-m.spec.vref+k*m.spec.lsb
            self.assertEqual(m.convert(v-1e-6*m.spec.lsb).code,k-1)
            self.assertEqual(m.convert(v).code,k)
            self.assertEqual(m.convert(v+1e-6*m.spec.lsb).code,k)

    def test_saturation_and_offset_direction(self):
        self.assertEqual(self.model.convert(-1.5).code,0)
        self.assertEqual(self.model.convert(1.5).code,255)
        positive=SarAdcModel(analog=AnalogConfig(comparator_offset_v=self.model.spec.lsb))
        self.assertEqual(positive.convert(0).code,127)
        negative=SarAdcModel(analog=AnalogConfig(comparator_offset_v=-self.model.spec.lsb))
        self.assertEqual(negative.convert(0).code,129)

    def test_bit_order_and_async_event_order(self):
        result=self.model.convert(.123,close_s=100e-9)
        self.assertEqual([e['bit'] for e in result.trace if e['event']=='cmp'],list(range(7,-1,-1)))
        for bit in range(8):
            events=[e for e in result.trace if e['bit']==bit]
            self.assertEqual([e['event'] for e in events],['cmp','write','update','cap','cap'])
            self.assertTrue(all(a['time_s']<b['time_s'] for a,b in zip(events,events[1:])))
        self.assertLess(result.finished_s,160e-9)

    def test_stuck_bit_never_publishes_completed_frame(self):
        m=SarAdcModel(analog=AnalogConfig(stuck_bit=3))
        r=m.convert(.123)
        self.assertFalse(r.completed)
        self.assertEqual((r.issue,r.issue_bit),('unresolved_comparator',3))
        self.assertEqual(r.counts,(5,4,4,8))
        # A new conversion resets all word/event state rather than inheriting it.
        self.assertEqual(m.convert(-.4).counts,(5,4,4,8))

    def test_actual_deadline_bit_is_reported(self):
        m=SarAdcModel(timing={'compare_to_write_s':9e-9})
        r=m.convert(.123)
        self.assertFalse(r.completed)
        self.assertEqual(r.issue,'acquisition_deadline')
        self.assertIsNotNone(r.issue_bit)
        self.assertLess(r.counts[1],8)

    def test_weight_errors_are_not_silently_renormalized(self):
        altered=SarAdcModel(analog=AnalogConfig(weight_errors=(0,0,0,0,0,0,0,.01)))
        self.assertGreater(altered.threshold(128),self.model.threshold(128))
        self.assertAlmostEqual(altered.threshold(128)-self.model.threshold(128),.01*128*self.model.spec.lsb)

    def test_disabled_noise_is_exact_and_enabled_noise_is_seeded(self):
        self.assertEqual(self.model.convert(.2).code,self.model.ideal_code(.2))
        a=AnalogConfig(sample_noise_rms_v=.01,comparator_noise_rms_v=.002)
        first=SarAdcModel(analog=a,seed=42)
        second=SarAdcModel(analog=a,seed=42)
        self.assertEqual([first.convert(.1).code for _ in range(30)],
                         [second.convert(.1).code for _ in range(30)])

    def test_invalid_config_cannot_be_used_as_a_different_converter(self):
        with self.assertRaises(ValueError):AdcSpec(10,.9,{})
        with self.assertRaises(ValueError):AnalogConfig(weight_errors=(0,)*7)
        with self.assertRaises(ValueError):self.model.convert(math.nan)
        with self.assertRaises(ValueError):SarAdcModel(timing={'comparator_floor_v':0})

    def test_spec_ports_and_MOM_weights_match_the_physical_B_source(self):
        root=Path(__file__).resolve().parents[1]
        spec=json.loads((root/'specs/arch.json').read_text(encoding='utf-8'))
        source=(root/'design/xtor/cdac/cdac.scs').read_text(encoding='utf-8').replace('\\\n',' ')
        caps={side:{} for side in 'NP'}
        for line in source.splitlines():
            match=re.match(r'\s*CMOM([NP])([0-8])\b.*?\bmulti=(\d+)',line)
            if match:caps[match.group(1)][int(match.group(2))]=int(match.group(3))
        for side in 'NP':
            self.assertEqual([caps[side][b] for b in range(8)],spec['blocks']['cdac']['weights_lsb_first'])
            self.assertEqual(sum(caps[side].values()),spec['blocks']['cdac']['total_units_per_side'])
        va=(root/'design/behav/veriloga/sar_adc_b.va').read_text(encoding='utf-8')
        ports=re.search(r'module sar_adc_b\(([^)]+)\)',va).group(1).split(',')
        physical=[{'VDD!':'VDD','0':'VSS'}.get(p,p) for p in spec['interface']['port_order']]
        self.assertEqual(ports,physical)
        self.assertTrue(check_generated()['physical_ports_match'])


if __name__=='__main__':unittest.main()
