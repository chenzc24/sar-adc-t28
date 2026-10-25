"""Small deterministic tests for the explicit cleanup safety boundaries."""
import gzip
import hashlib
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import cleanup_execute as local
import cleanup_execute_remote as remote
import project


class CleanupChecks(unittest.TestCase):
    def test_exact_approved_manifest_and_last_copy_separation(self):
        spec=local.load(local.DEST/'input.json')
        self.assertEqual(spec['approved_ids'],local.IDS)
        self.assertEqual(len(spec['local_targets']),21)
        self.assertEqual(len(spec['remote_targets']),15)
        self.assertEqual(len(set(spec['retained_paths'])),10)
        self.assertFalse(set(spec['retained_paths']) & {r['path'] for r in spec['remote_targets']})

    def test_remote_path_escape_refused_before_file_access(self):
        for path in ['/home/chenzc_intern25/CDS.log',remote.ALLOWED[0]+'2/raw',remote.ALLOWED[0]]:
            with self.assertRaisesRegex(AssertionError,'Outside exact cleanup roots'):
                remote.fingerprint(path)

    def test_remote_traversal_and_symlink_refused(self):
        path=remote.ALLOWED[0]+'/case/../../elsewhere'
        with self.assertRaisesRegex(AssertionError,'Symlink path'):
            remote.fingerprint(path)

    def test_changed_file_refused(self):
        with mock.patch.object(remote,'fingerprint',return_value={'bytes':2}):
            with self.assertRaisesRegex(AssertionError,'Changed after verification'):
                remote.unchanged('/unused',{'bytes':1})

    def test_remote_last_copy_in_targets_refused(self):
        spec=local.load(local.DEST/'input.json')
        spec['retained_paths'][0]=spec['remote_targets'][0]['path']
        with mock.patch.object(remote,'read',return_value=spec):
            with self.assertRaises(AssertionError):remote.verified_spec()

    def test_stream_hash_and_gzip_payload(self):
        payload=b'PSF ASCII\n'+b'sample\n'*100+b'END\n'
        with tempfile.TemporaryDirectory() as folder:
            plain=Path(folder)/'raw';plain.write_bytes(payload)
            archive=Path(folder)/'raw.gz';archive.write_bytes(gzip.compress(payload))
            with mock.patch.object(remote,'fingerprint',return_value={}),mock.patch.object(remote,'unchanged'),mock.patch.object(remote,'status'):
                for path,compressed in [(plain,False),(archive,True)]:
                    result=remote.stream_hash(str(path),time.time()+10,compressed)
                    self.assertEqual(result['sha256'],hashlib.sha256(payload).hexdigest())
                    self.assertEqual(result['bytes'],len(payload))
                    self.assertTrue(result['PSF_END'])

    def test_local_outside_and_hardlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'output/sar8_r4_idle/case/raw'
            target.parent.mkdir(parents=True);target.write_bytes(b'fixture')
            with mock.patch.object(local,'ROOT',root):
                self.assertEqual(local.local_fingerprint(str(target))['nlink'],1)
                with self.assertRaises(AssertionError):local.local_fingerprint(str(root/'outside'))
                other=target.with_name('linked');os.link(target,other)
                with self.assertRaises(AssertionError):local.local_fingerprint(str(target))

    def test_native_powershell_file_only_literal_removal(self):
        source=(local.ROOT/'scripts/management/cleanup_execute_local.ps1').read_text()
        self.assertIn('Remove-Item -LiteralPath $full -Force',source)
        self.assertNotIn('-Recurse',source)
        self.assertIn('Cross-domain approval mismatch',source)
        self.assertIn('Local deletion receipt exists',source)

    def test_completed_cleanup_registry_keeps_exact_retained_paths(self):
        cases,groups=project.completed_cleanup()
        self.assertEqual(len(cases),10)
        self.assertEqual(groups,{'sar8_r4_staged','sar8_r4_idle'})
        self.assertEqual({v['retained_server_native'] for v in cases.values()},
            set(local.load(local.DEST/'input.json')['retained_paths']))
        with mock.patch.object(Path,'exists',return_value=True):
            restored,_=project.completed_cleanup()
        self.assertTrue(all(r['local_state']=='present_after_cleanup_requires_reconcile' for r in restored.values()))


if __name__=='__main__':unittest.main()
