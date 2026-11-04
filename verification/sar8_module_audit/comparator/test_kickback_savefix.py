"""Verify exact Spectre symbol spelling against the actual generated hierarchy."""
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

import kickback_analyze as a
import prepare_kickback_savefix as fix
import test_kickback as synthetic


class SaveCaseTests(unittest.TestCase):
    def test_actual_v2_saves_resolve_and_v1_invalid_case_is_detected(self):
        cfg=json.loads((fix.NEW/'measurement.json').read_bytes())
        check=fix.validate_saves(fix.NEW,cfg)
        self.assertEqual(check['resolved_requests'],81)
        self.assertEqual((check['voltage_requests'],check['current_requests']),(36,45))
        with self.assertRaisesRegex(ValueError,'case-sensitive'):fix.validate_saves(fix.OLD,cfg)
        mapping=fix.expected_saves(fix.NEW,cfg)
        self.assertEqual(mapping['cmp_clk'],'CMP_CLK')
        self.assertEqual(mapping['vsense_ap:1'],'VSENSE_AP:1')
        self.assertEqual(mapping['xactive.xcomp.mninp:2'],'XACTIVE.XCOMP.MNINP:2')

    def test_only_save_spelling_and_corresponding_hash_changed(self):
        old=(fix.OLD/'test.scs').read_bytes().splitlines(keepends=True)
        new=(fix.NEW/'test.scs').read_bytes().splitlines(keepends=True)
        self.assertEqual([s for s in old if not s.startswith(b'save ')],
                         [s for s in new if not s.startswith(b'save ')])
        for name in ['cells.scs','cdac_load.scs','initializer.va','kickback_analyze.py']:
            self.assertEqual((fix.OLD/name).read_bytes(),(fix.NEW/name).read_bytes())
        cfg=json.loads((fix.OLD/'measurement.json').read_bytes())
        cfg['required_input_sha256']['test.scs']=fix.sha((fix.NEW/'test.scs').read_bytes())
        self.assertEqual(cfg,json.loads((fix.NEW/'measurement.json').read_bytes()))
        manifest=json.loads((fix.NEW/'manifest.json').read_bytes())
        for name,h in manifest['parent_input_hashes'].items():self.assertEqual(fix.sha((fix.OLD/name).read_bytes()),h)

    def test_same_two_GiB_and_other_resource_limits_as_registered_parent(self):
        old=json.loads((fix.OLD/'recipe_proposal.json').read_bytes())
        new=json.loads((fix.NEW/'recipe_proposal.json').read_bytes())
        budget=copy.deepcopy(old['resources']);budget['queue_timeout_seconds']=600
        self.assertEqual(new['resources'],budget)
        self.assertEqual(new['resources']['max_output_mib'],2048)
        self.assertEqual(new['spectre_args'],old['spectre_args'])
        self.assertEqual(new['expected_stop_s'],old['expected_stop_s'])

    def test_native_correct_case_and_sparse_group_are_read_as_normalized_measurements(self):
        cfg=json.loads((fix.NEW/'measurement.json').read_bytes())
        mapping=fix.expected_saves(fix.NEW,cfg)
        text=synthetic.psf(cfg,synthetic.samples(cfg),sparse=True,group=True)
        text=re.sub(r'"([^"]+)"',lambda m:'"'+mapping.get(m[1],m[1])+'"',text)
        with tempfile.TemporaryDirectory(prefix='_kb_v2_names_',dir=fix.HERE) as folder:
            root=Path(folder);native=root/'synthetic.tran.tran';native.write_text(text)
            out=a.Output(str(root/'derived'),cfg['max_output_bytes'])
            result=a.reduce(str(native),cfg,out)
            self.assertEqual(len(result['cycles']),6)
            self.assertEqual([len(c['writes']) for c in result['cycles']],[1]*6)
            self.assertTrue(all(c['DATA_matches_nominal_at_each_write']==[True] for c in result['cycles']))
            self.assertIsNone(result['acceptance_pass'])


if __name__=='__main__':unittest.main(verbosity=2)
