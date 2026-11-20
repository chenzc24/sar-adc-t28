import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/saradc/measure'))
import mc_short_reduce as mc


class McTests(unittest.TestCase):
    def frame(self,code=12,late=False):
        f=mc.native.frame_new(0)
        f.update(code_90=code,code_98=code,observer_code=code,sample_close_error_lsb=0)
        for name,t,rise in [('sample',1,True),('sample',41,False),('close',41,False),('sample_int',41,False)]:
            f['events'].append(dict(signal=name,time_s=t*1e-9,rising=rise))
        for i in range(8):
            for name,delta in [('cmp',0),('write',1),('update',2)]:
                f['events'].append(dict(signal=name,time_s=(42+i*3+delta+(50 if late else 0))*1e-9,rising=True))
            f['bits'].append(dict(bit=7-i,receiver_valid_at_write=True,bottom=dict(weighted_bound_lsb=.01,max_bottom_error_v=1e-5)))
        return f

    def finish(self,f):
        return mc.finish(f,dict(expected_codes=[12],frame_origin_s=0,period_s=1e-7,lsb_v=1.8/256,settling_band_lsb=.25))

    def test_offset_code_change_is_not_timing_failure(self):
        r=self.finish(self.frame(code=17))
        self.assertFalse(r['code_pass']);self.assertTrue(r['pass_function_timing'])
        self.assertEqual(r['nominal_code_delta'],5);self.assertFalse(r['issues'])

    def test_late_conversion_and_receiver_unresolved_fail(self):
        self.assertFalse(self.finish(self.frame(late=True))['pass_function_timing'])
        f=self.frame();f['bits'][4]['receiver_valid_at_write']=False
        r=self.finish(f);self.assertEqual(r['issues'][0]['bit'],3)
        self.assertFalse(r['pass_function_timing'])

    def test_conservative_bound_exceedance_requires_reference_not_false_timeout(self):
        f=self.frame();f['bits'][2]['bottom']['max_bottom_error_v']=.002
        r=self.finish(f)
        self.assertTrue(r['pass_function_timing'])
        self.assertEqual(r['settling_review'][0]['bit'],5)

    def test_saved_global_and_local_coverage_includes_root_and_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/'raw';out=root/'derived';raw.mkdir();out.mkdir()
            names=['XDUT','XDUT.XCOMP.MNINP','XDUT.XCOMP.MNINN']
            names += ['XDUT.'+x+'.M' for x in ['XCTRL','XREF','XBOOTP','XBOOTN','XSEQ','XSAMPLE','XIDLE']]
            names += ['XDUT.XCDAC.CMOM'+str(i) for i in range(18)]
            (raw/'mismatch.params').write_text('p1 p2\n'+'\n'.join(names)+'\n\n')
            (raw/'mismatch.values').write_text('#1\n'+'\n'.join(str(i+1)+' 1' for i in range(len(names)))+'\n\n')
            (raw/'process.params').write_text('# Temperature = 27\nr1_27 -1e36 1e36 r1\nr2_27 -1e36 1e36 r2\n')
            (raw/'process.values').write_text('0.3 -0.5\n')
            r=mc.random_evidence(str(root),str(out))
            self.assertTrue(r['valid']);self.assertEqual(r['global_numeric_count'],2)
            (raw/'process.values').write_text('0.3\n')
            with self.assertRaisesRegex(ValueError,'Global labels/data'):mc.random_evidence(str(root),str(out))


if __name__=='__main__':unittest.main()
