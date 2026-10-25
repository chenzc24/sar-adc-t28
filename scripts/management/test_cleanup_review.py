"""Focused read-only review arithmetic, scope and retention checks."""
import unittest
from unittest import mock
import cleanup_review as audit

class ReviewChecks(unittest.TestCase):
    def test_parent_and_child_never_counted_twice(self):
        paths=['/a/case','/a/case/raw','/a/case','/a/case2']
        self.assertEqual(audit.outermost(paths),['/a/case','/a/case2'])

    def test_waveform_summary_gzip_is_not_a_transfer_archive(self):
        self.assertEqual(audit.category('/run/reduced/reduced.json.gz'),'other_preserve')
        self.assertEqual(audit.category('/run/transfer_tran.gz'),'archive')
        self.assertEqual(audit.category('/run/transfer_parts_v1/part_001'),'transfer_parts')
        self.assertEqual(audit.category('/run/test.raw/tran_perf.tran.tran'),'native_waveform')

    def test_current_and_independent_work_is_protected(self):
        for group in ['sar8_stress_closure','sar8_ref_current_probe','sar8_physical_repair',
            'sar8fix-c1r4-ffcold','sar8fix-hyblong-sscold','cdac10_dualrail','sar8_idle_performance']:
            self.assertTrue(audit.protected(group),group)
            self.assertTrue(audit.advice(group,{}).startswith('保留：'))

    def test_review_checks_actual_manifest(self):
        audit.check()
        d=audit.load(audit.DEST/'review_manifest.json')
        ids={p['id'] for p in d['proposals']}
        self.assertEqual(ids,{'L-A1','L-B1','L-B2','S-A1','S-A2'})
        for p in d['proposals']:
            self.assertFalse(p['content_identity_verified_this_audit'])
            self.assertTrue(p['required_retained_paths'])
        self.assertEqual(sum(p['file_count'] for p in d['proposals']),36)

    def test_conflicting_last_copy_is_rejected(self):
        d=audit.load(audit.DEST/'review_manifest.json')
        target=d['proposals'][0]['files'][0]['path']
        d['proposals'][0]['required_retained_paths'].append(target)
        with mock.patch.object(audit,'load',return_value=d):
            with self.assertRaisesRegex(AssertionError,'required retained copy'):audit.check()

if __name__=='__main__':unittest.main()
