"""Only the approved acquisition-history variable; local synthetic checks."""
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

import kickback_analyze as a
import prepare_kickback_hold2 as h
import test_kickback as synthetic


def source_points(text):
    match=re.search(r'(?m)^VINIT \(CINIT 0\) vsource type=pwl wave=\[([^\]]+)\]$',text)
    tokens=match[1].split()
    return [(float(tokens[i][:-1]),tokens[i+1] if tokens[i+1]=='SUP' else float(tokens[i+1]))
            for i in range(0,len(tokens),2)]


class HoldHistory(unittest.TestCase):
    def test_only_CINIT_second_acquisition_changes(self):
        old=(h.SOURCE/'test.scs').read_text();new=(h.DEST/'test.scs').read_text()
        self.assertEqual([s for s in old.splitlines() if not s.startswith('VINIT ')],
                         [s for s in new.splitlines() if not s.startswith('VINIT ')])
        self.assertEqual(new,h.remove_second_pulse(old))
        op,np=source_points(old),source_points(new)
        times=sorted({t for t,v in op}|{t for t,v in np}|{44.05,50.,58.05,60.})
        times+= [(x+y)*.5 for x,y in zip(times,times[1:])]
        for t in times:
            before,after=synthetic.interp(op,t),synthetic.interp(np,t)
            if not 44<t<58.1:self.assertAlmostEqual(before,after,places=12)
            if 18.1<=t<=84:self.assertAlmostEqual(after,0.,places=12)
        self.assertEqual(synthetic.interp(op,50.),.9)
        self.assertEqual(synthetic.interp(np,50.),0.)

    def test_frozen_hardware_analyzer_clocks_targets_and_budgets(self):
        for name in ['cells.scs','cdac_load.scs','initializer.va','kickback_analyze.py']:
            self.assertEqual((h.SOURCE/name).read_bytes(),(h.DEST/name).read_bytes())
        old=json.loads((h.SOURCE/'measurement.json').read_bytes());new=json.loads((h.DEST/'measurement.json').read_bytes())
        for a0,a1 in zip(old['cycles'],new['cycles']):
            for key in ['index','start_s','clock_fall_end_s','target_diff_v','target_cm_v','expected_DATA']:
                self.assertEqual(a0[key],a1[key])
        self.assertEqual(new['cycles'][1]['release_end_s'],new['cycles'][0]['release_end_s'])
        self.assertAlmostEqual(new['cycles'][0]['next_acquire_s'],84e-9,delta=1e-20)
        for name,hsh in json.loads((h.DEST/'manifest.json').read_bytes())['parent_input_hashes'].items():
            self.assertEqual(h.sha((h.SOURCE/name).read_bytes()),hsh)
        for name in new['required_input_sha256']:
            self.assertEqual(h.sha((h.DEST/name).read_bytes()),new['required_input_sha256'][name])
        oldr=json.loads((h.SOURCE/'recipe_proposal.json').read_bytes());newr=json.loads((h.DEST/'recipe_proposal.json').read_bytes())
        self.assertEqual(newr['resources'],oldr['resources']);self.assertEqual(newr['spectre_args'],oldr['spectre_args'])
        self.assertEqual(newr['expected_stop_s'],oldr['expected_stop_s'])

    def test_generated_config_measures_residual_before_second_compare(self):
        cfg=json.loads((h.DEST/'measurement.json').read_bytes());rows=copy.deepcopy(synthetic.samples(cfg))
        points=source_points((h.DEST/'test.scs').read_text());arm=cfg['arms']['evaluate']
        for t,v in rows:
            v['cinit']=synthetic.interp(points,t*1e9)
            # Deliberately supplied synthetic charge residue; not simulated data.
            if 44e-9<=t<84e-9:
                v[arm['topp']]+=-.0003+.0001/2
                v[arm['topn']]+=-.0003-.0001/2
        with tempfile.TemporaryDirectory(prefix='_hold2_probe_',dir=h.HERE) as folder:
            root=Path(folder);self.assertTrue(root.resolve().is_relative_to(h.HERE.resolve()))
            path=root/'synthetic.tran.tran';path.write_text(synthetic.psf(cfg,rows,sparse=True,group=True))
            result=a.reduce(str(path),cfg,a.Output(str(root/'derived'),cfg['max_output_bytes']))
            second=result['cycles'][1]
            self.assertLess(second['after_release']['time_s'],20e-9)
            self.assertAlmostEqual(second['pre_compare_target_error_v'],.0001,places=12)
            self.assertAlmostEqual(second['pre_compare']['arms']['evaluate']['cm_v'],.4497,places=12)
            self.assertEqual(second['DATA_matches_nominal_at_each_write'],[True])
            self.assertEqual(len(second['writes']),1)
            self.assertIsNone(result['acceptance_pass'])


if __name__=='__main__':unittest.main(verbosity=2)
