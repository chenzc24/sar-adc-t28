"""Focused checks against generated native exports, not a replacement for Spectre."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/cdac8_dualrail'))
from common import OUT,ROOT,load,sha
from run import blocks
from analyze import instances


class TestNativeEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=OUT/'oa_netlists/tb_cdac8_dr_literal/clean_va/input.scs'
        cls.sub=blocks(cls.source.read_text())

    def test_512_independent_mom_units(self):
        def count(master):
            if master=='cfmom_2t':return 1
            return sum(count(target) for _,target in instances(self.sub.get(master,'')).values())
        self.assertEqual(count('cdac8_dr_literal'),512)

    def test_native_switch_count_and_no_vcm_branch(self):
        array=instances(self.sub['cdac8_dr_literal'])
        groups=[m for n,(_,m) in array.items() if n.startswith('XS')]
        self.assertEqual(len(groups),16)
        for master in groups:
            leaf=self.sub[master]
            self.assertNotIn('VCM',leaf)
            mos=[m for _,m in instances(leaf).values() if m in ['nch_mac','pch_mac']]
            self.assertEqual(len(mos),8)
        self.assertNotIn('VCM',self.sub['cdac8_dr_literal'])

    def test_zero_oa_markers_and_dependency_equality(self):
        for p in (OUT/'oa').glob('*_markers.json'):self.assertEqual(load(f'oa/{p.name}'),[],p)
        audit=load('audit/final.json')
        self.assertEqual(len(audit['dependencies_equal']),12)
        self.assertTrue(all(audit['dependencies_equal'].values()))
        self.assertTrue(all(audit['final_exports_equal'].values()))
        for name,proof in audit['va'].items():
            self.assertEqual(proof['local_sha256'],proof['remote_sha256'])
            self.assertEqual(sha(ROOT/'models/veriloga'/name),proof['remote_sha256'])

    def test_canvas_wiring_and_original_preserved(self):
        c=load('canvas_final_v2.json')
        self.assertEqual(c['original']['revision'],266)
        for key in ['top','leaf']:
            self.assertEqual(c[key]['vr']['errors'],0)
            self.assertEqual(c[key]['vr']['warnings'],0)
            self.assertEqual(c[key]['vr']['comparison']['status'],'equal')

    def test_final_deck_duts_identical_to_oa(self):
        for p in (OUT/'cases').glob('*.json'):
            case=load(f'cases/{p.name}')
            if case['oa_tag']!='clean_va':continue
            src=OUT/f"oa_netlists/{case['cell']}/clean_va/input.scs"
            deck=OUT/f'decks/{p.stem}.scs'
            self.assertEqual(sha(src),case['source_sha256'])
            self.assertEqual(sha(deck),case['deck_sha256'])
            self.assertEqual(blocks(src.read_text()),blocks(deck.read_text()),p)


if __name__=='__main__':unittest.main()
