import json
from pathlib import Path
import unittest
from tools.saradc.pvt_short import matrix
from tools.saradc.reference_short import stimulus

ROOT=Path(__file__).resolve().parents[1]

class PvtMatrixTests(unittest.TestCase):
    def test_exact_45_unique_conditions_and_40_new_points(self):
        cfg=json.loads((ROOT/'specs/pvt_short.json').read_text())
        all_points=matrix(cfg)
        self.assertEqual(len(all_points),45)
        self.assertEqual(len({tuple(sorted(v.items())) for v in all_points.values()}),45)
        self.assertEqual(len(set(all_points)-set(cfg['existing_five'])),40)
        old=json.loads((ROOT/'specs/corners.json').read_text())
        for name,alias in cfg['existing_five'].items():self.assertEqual(all_points[name],old[alias])
        for p in ('fs','sf'):
            self.assertEqual(sum(n.startswith(p+'_') for n in all_points),9)

    def test_ten_differential_centers_and_external_stimulus_timing(self):
        cfg=json.loads((ROOT/'specs/pvt_short.json').read_text());codes=cfg['code_centers_in_order']
        self.assertEqual(len(codes),10);self.assertEqual(len(set(codes)),10)
        self.assertEqual(codes[:4],[0,255,1,254])
        p=list(map(float,stimulus(codes,1).split()));n=list(map(float,stimulus(codes,-1).split()))
        self.assertEqual(p[::2],n[::2]);self.assertAlmostEqual(p[-2],1.059e-6)
        for vp,vn in zip(p[1::2],n[1::2]):
            self.assertAlmostEqual((vp+vn)/2,.45)
        self.assertTrue(all(a<b for a,b in zip(p[::2],p[2::2])))

if __name__=='__main__':unittest.main()
