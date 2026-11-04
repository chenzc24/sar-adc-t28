"""Focused physical mapping, stage boundaries and signed-stress report controls."""
import copy
import unittest
from analyze_standard_cell_bbm import device_mapping, function_group, phase, terminal_rows


class ComparisonTest(unittest.TestCase):
    def test_actual_pair_mapping_and_signed_extrema(self):
        mapping=device_mapping()
        self.assertEqual(len(mapping),123)
        self.assertEqual(sum(x['candidate_implementation']=='standard_gate_internal' for x in mapping.values()),42)
        self.assertEqual(sum(x['candidate_implementation']=='retained_RC_clear' for x in mapping.values()),4)
        self.assertEqual(sum(x['candidate_implementation']=='retained_IO' for x in mapping.values()),8)
        self.assertEqual(mapping['XDUT.XBBM0.X002.X000.MN0']['candidate'],'XDUT.XBBM0.X002.X000.XLIB.MM4')
        self.assertEqual(mapping['XDUT.XBBM0.X002.X000.MN1']['candidate'],'XDUT.XBBM0.X002.X000.XLIB.MM9')
        self.assertEqual(mapping['XDUT.GNPAN']['candidate'],'XDUT.XSTD_GNPAN.MM1')
        self.assertEqual(function_group('XDUT.XBBM0.XD_HD.MP_CLEAR'),'RC_clear')
        with self.assertRaises(ValueError):function_group('unknown_unmeasured')
        self.assertEqual(phase(42.995e-9),'CODE_rise')
        self.assertEqual(phase(47.995e-9),'CODE_fall')
        self.assertEqual(phase(48.005e-9),'low_select_and_HD_reset')
        screens=[];extrema={}
        for old,x in mapping.items():
            for suffix in ['ds','gs','gd','gb','bd','bs']:
                screens.append(dict(instance=x['candidate'],terminal=suffix,model=x['model'],
                    nodes=[x['candidate_nodes']['dgsb'.index(n)] for n in suffix],
                    screen_v=.99 if x['model'] in ['nch_mac','pch_mac'] else 1.98))
                extrema[x['candidate']+':'+suffix]=dict(min=-1.07,max=.99,
                    min_time_s=48.1e-9,max_time_s=43.2e-9)
        d=dict(cfg=dict(selected_mos_pair_screens=screens),result=dict(selected_mos_pair_extrema=extrema))
        rows=terminal_rows(d,'ffcold','std',mapping)
        self.assertEqual(len(rows),738)
        self.assertEqual(len({x['mapped_pair'] for x in rows}),738)
        self.assertTrue(all(x['signed_peak_V']==-1.07 and x['peak_phase']=='low_select_and_HD_reset' for x in rows))
        self.assertTrue(any(x['excess_V']<0 for x in rows))
        bad=copy.deepcopy(d);bad['cfg']['selected_mos_pair_screens'][0]['screen_v']=9
        with self.assertRaises(AssertionError):terminal_rows(bad,'ffcold','std',mapping)


if __name__=='__main__':
    unittest.main()
