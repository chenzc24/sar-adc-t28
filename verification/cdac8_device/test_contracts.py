"""Small offline regressions; these do not replace Spectre circuit evidence."""
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/cdac8_device'))
from common import LSB,LIMIT,cfg
from run import variables,parameter_names

class Contracts(unittest.TestCase):
    def test_flat_weights_and_budget(self):
        self.assertEqual(sum(1<<b for b in range(8))+1,256)
        self.assertAlmostEqual(LSB,7.03125e-3)
        self.assertAlmostEqual(LIMIT,1.7578125e-3)
        c=cfg()
        self.assertEqual(c['resolution_bits'],8)
        self.assertAlmostEqual(c['selected_side_capacitance_pf'],256*c['selected_unit_measured_ff']/1000)

    def test_multiline_parameters(self):
        source='header\nparameters A \\\n B C\nDUT untouched\n'
        self.assertEqual(parameter_names(source),['A','B','C'])
        result=variables(source,{'A':.9,'B':2e-12,'C':100})
        self.assertIn('DUT untouched',result)
        self.assertIn('parameters A=0.9 B=2e-12 C=100\n',result)
        with self.assertRaises(AssertionError):variables(source,{'A':1})

    def test_thermal_lower_bound_is_not_physical_noise_closure(self):
        cap=cfg()['selected_side_capacitance_pf']*1e-12
        sigma=math.sqrt(2*1.380649e-23*300.15/cap)
        self.assertLess(sigma,.1e-3)
        self.assertGreater(sigma,.08e-3)

    def test_va_ports_are_scalar_and_phase_is_separate(self):
        source=(ROOT/'models/veriloga/cdac8_controller.va').read_text()
        for bit in range(8):
            self.assertIn(f'output electrical SEL0_{bit}',source)
            self.assertIn(f'output electrical SEL1_{bit}',source)
        self.assertIn('input electrical PREPARE',source)
        self.assertIn('@(timer(ready_time[k]))',source)
        self.assertNotIn('white_noise',source)  # No duplicated synthetic device noise.

if __name__=='__main__':unittest.main()
