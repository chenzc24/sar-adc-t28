"""Focused same-shape recovery and ambiguity rejection; no source-library read."""
import hashlib
import unittest
from recover import recover_scalar,RecoveryError


RAW=('0.262900 default_inout_pin_cap : 0.000749449 '
     'default_input_pin_cap : 0.000749449 default_output_pin_cap : 0 '
     'slew_lower_threshold_pct_rise : 30.00 slew_upper_threshold_pct_rise : 70.00 '
     'slew_derate_from_library : 0.50 input_threshold_pct_fall : 50.00 '
     'output_threshold_pct_fall : 50.00 input_threshold_pct_rise : 50.00 '
     'output_threshold_pct_rise : 50.00 slew_lower_threshold_pct_fall : 30.00 '
     'slew_upper_threshold_pct_fall : 70.00 leakage_power_unit : 1nW')
OUTER='default_max_transition'


class ScalarRecoveryTest(unittest.TestCase):
    def test_same_shape_and_full_literal_coverage(self):
        result=recover_scalar(RAW,OUTER,{OUTER:RAW})
        self.assertTrue(result['full_string_coverage'])
        self.assertEqual(result['consumed_characters'],len(RAW))
        self.assertEqual(result['original_scalar_sha256'],hashlib.sha256(RAW.encode()).hexdigest())
        self.assertEqual(len(result['recovered']),14)
        self.assertEqual(result['recovered']['slew_derate_from_library'],.5)
        self.assertEqual(result['recovered']['leakage_power_unit'],'1nW')
        for segment in result['segments']:
            self.assertEqual(RAW[slice(*segment['value_span'])],segment['literal'])

    def test_refuse_ambiguous_or_partially_consumed_input(self):
        mutations=[
            ('duplicate',RAW+' slew_derate_from_library : 0.50',{}),
            ('independent_duplicate',RAW,{'slew_derate_from_library':.5}),
            ('independent_conflict',RAW,{'slew_derate_from_library':.7}),
            ('unknown_field',RAW+' guessed_default : 1',{}),
            ('numeric_suffix',RAW.replace('30.00','30foo',1),{}),
            ('missing_colon',RAW.replace('slew_derate_from_library :','slew_derate_from_library',1),{}),
            ('trailing_punctuation',RAW+' ;',{}),
            ('unsupported_unit',RAW.replace('1nW','1dB'),{}),
            ('nonfinite',RAW.replace('0.50','1e999',1),{}),
            ('invalid_pair',RAW.replace('30.00','80.00',1),{}),
            ('negative_derate',RAW.replace('0.50','-0.5',1),{}),
            ('out_of_range',RAW.replace('30.00','130.00',1),{}),
        ]
        for name,raw,extra in mutations:
            with self.subTest(name=name):
                with self.assertRaises(RecoveryError) as caught:
                    recover_scalar(raw,OUTER,dict({OUTER:raw},**extra))
                self.assertIsInstance(caught.exception.offset,int)
        with self.assertRaises(RecoveryError):
            recover_scalar(RAW,OUTER,{OUTER:RAW+' identity drift'})


if __name__=='__main__':unittest.main()
