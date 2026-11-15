import importlib.util
from pathlib import Path
import sys
import unittest
import re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/saradc/measure'))
spec=importlib.util.spec_from_file_location('short_measure',ROOT/'tools/saradc/measure/reference_short.py')
measure=importlib.util.module_from_spec(spec);spec.loader.exec_module(measure)
from tools.saradc.reference_short import CODES, candidate_source, stimulus


class MinimalReferenceTests(unittest.TestCase):
    def test_input_centers_and_history(self):
        self.assertEqual(len(set(CODES)),12)
        self.assertEqual(CODES[:2],[0,0])
        self.assertEqual(CODES[13:16],[255,0,255])
        for sign in [1,-1]:
            points=list(map(float,stimulus(CODES,sign).split()))
            self.assertTrue(all(0<=v<=.9 for v in points[1::2]))
            self.assertTrue(all(a<b for a,b in zip(points[::2],points[2::2])))

    def test_nominal_and_preset_truth_tables(self):
        source=candidate_source().split('ends sar8i_refword')[0]
        calls=re.findall(r'(?m)^\w+ \(([^)]+)\) (\w+)$',source)
        for word in range(256):
            for preset in [False,True]:
                nodes={'PRESET':preset,'VDD':True,'VSS':False}
                nodes.update({'CODE%d'%i:bool(word & (1<<i)) for i in range(8)})
                for pins,master in calls:
                    n=pins.split()
                    if master=='iprobe':
                        if n[0] in nodes:nodes[n[1]]=nodes[n[0]]
                        else:nodes[n[0]]=nodes[n[1]]
                    elif master=='sar8p_inv':nodes[n[-1]]=not nodes[n[0]]
                    elif master=='sar8p_buf':nodes[n[-1]]=nodes[n[0]]
                    elif master=='sar8p_nand2':nodes[n[-1]]=not(nodes[n[0]] and nodes[n[1]])
                    elif master=='sar8p_or2':nodes[n[-1]]=nodes[n[0]] or nodes[n[1]]
                    else:self.fail(master)
                expected=128 if preset else word
                for bit in range(8):
                    for name in ['GPN','GPP']:self.assertEqual(nodes[name+str(bit)],bool(expected & (1<<bit)))
                    for name in ['GNN','GNP']:self.assertEqual(nodes[name+str(bit)],not bool(expected & (1<<bit)))

    def test_direct_candidate_has_no_second_state_bank(self):
        source=candidate_source().split('ends sar8i_refword')[0]
        for token in ['sar8p_dffr','sar8p_nonoverlap','sar8s_step','CAP_CLK','rupolym']:
            self.assertNotIn(token,source)
        self.assertEqual(len(re.findall(r'(?m)^W\w+ .* iprobe$',source)),17)

    def test_code_threshold_tracks_supply(self):
        values={'vdd!':.81}
        values.update({'d%d'%i:.42 if i in [0,7] else 0 for i in range(8)})
        self.assertEqual(measure.code(values),129)

    def test_bottom_screen_detects_unsettled_bit(self):
        values={'vdd!':.9,'vrefp':.9,'vrefn':0.}
        for side in ['n','p']:
            level=.9 if side=='n' else 0.
            for bit in range(8):
                for gate in ['n','p']:values['xdut.g%s%s%d'%(side,gate,bit)]=level
                values['xdut.xcdac.b%s%d'%(side,bit)]=0. if side=='n' else .9
        self.assertEqual(measure.bottom(values,1.8/256)['weighted_bound_lsb'],0.)
        values['xdut.xcdac.bn7']=.01
        self.assertGreater(measure.bottom(values,1.8/256)['weighted_bound_lsb'],.25)
        values['xdut.gnp7']=0
        self.assertIsNone(measure.bottom(values,1.8/256))

    def test_correct_code_does_not_hide_missing_handshake(self):
        f=measure.frame_new(0);f.update(code_98=0,observer_code=0)
        ctx={'expected_codes':[0],'frame_origin_s':59e-9,'period_s':100e-9,'settling_band_lsb':.25}
        result=measure.finish(f,ctx)
        self.assertTrue(result['code_pass'])
        self.assertFalse(result['timing_pass'])
        self.assertFalse(result['pass_function_timing'])


if __name__=='__main__':unittest.main()
