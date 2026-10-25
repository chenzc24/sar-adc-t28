"""Focused guards and reversible exact-file archive checks."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import home_top_archive_remote as remote


class ArchiveChecks(unittest.TestCase):
    def test_only_recognized_visible_logs_and_simulation_files(self):
        for name in ['CDS.log.2','CDS_bridge3.log','libManager.log.4','spectre.out']:
            self.assertEqual(remote.category(name),'logs')
        self.assertEqual(remote.category('clean_va_dynamic_256.scs.tran.srf'),'simulation')
        for name in ['cds.lib','si.env','drc_rule','CDS.log.cdslck','.nfs123','TSMC28','test.ahdlSimDB','../CDS.log','CDS.log\n']:
            self.assertIsNone(remote.category(name))

    def test_symlink_and_unreviewed_name_refused(self):
        with mock.patch.object(remote.os.path,'realpath',return_value='/elsewhere'):
            with self.assertRaises(AssertionError):remote.literal('CDS.log')
        with self.assertRaises(AssertionError):remote.literal('cds.lib')

    def test_changed_source_or_new_lock_refused(self):
        row=dict(name='CDS.log.2',source='/fixture/CDS.log.2',fingerprint={'bytes':1},sha256='known')
        with mock.patch.object(remote,'literal',return_value=(row['source'],{'bytes':2})):
            with self.assertRaises(AssertionError):remote.validate_row(row)
        with mock.patch.object(remote,'literal',return_value=(row['source'],row['fingerprint'])),mock.patch.object(remote,'locks',return_value=['sidecar']):
            with self.assertRaises(AssertionError):remote.validate_row(row)

    def fixture(self,folder):
        home=Path(folder);source=home/'CDS.log.2';source.write_bytes(b'inactive historical log')
        archive=home/'archive/home-top-2026-10-25';(archive/'logs').mkdir(parents=True)
        row=dict(name=source.name,source=source.as_posix(),category='logs',fingerprint=remote.fingerprint(str(source)),sha256=remote.digest(str(source)))
        return home,source,archive,row

    def test_same_filesystem_move_preserves_content_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            home,source,archive,row=self.fixture(folder);target=archive/'logs'/source.name
            sibling=home/'cds.lib';sibling.write_bytes(b'protected configuration')
            with mock.patch.object(remote,'HOME',home.as_posix()),mock.patch.object(remote,'ARCHIVE',archive.as_posix()),mock.patch.object(remote,'UID',source.stat().st_uid),mock.patch.object(remote.os.path,'realpath',side_effect=lambda p:p),mock.patch.object(remote,'process_uses',return_value={'uncertain':[],'uses':{}}):
                remote.hardlink_move(row,target.as_posix())
            self.assertFalse(source.exists());self.assertEqual(target.read_bytes(),b'inactive historical log')
            self.assertEqual(target.stat().st_mtime,row['fingerprint']['mtime']);self.assertEqual(target.stat().st_nlink,1)
            self.assertEqual(sibling.read_bytes(),b'protected configuration')

    def test_destination_collision_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            home,source,archive,row=self.fixture(folder);target=archive/'logs'/source.name;target.write_bytes(b'existing archive')
            with mock.patch.object(remote,'validate_row'):
                with self.assertRaisesRegex(AssertionError,'collision'):remote.hardlink_move(row,target.as_posix())
            self.assertTrue(source.exists());self.assertEqual(target.read_bytes(),b'existing archive')

    def test_new_activity_after_link_keeps_both_names_for_reconciliation(self):
        with tempfile.TemporaryDirectory() as folder:
            home,source,archive,row=self.fixture(folder);target=archive/'logs'/source.name
            with mock.patch.object(remote,'HOME',home.as_posix()),mock.patch.object(remote,'ARCHIVE',archive.as_posix()),mock.patch.object(remote,'UID',source.stat().st_uid),mock.patch.object(remote.os.path,'realpath',side_effect=lambda p:p),mock.patch.object(remote,'process_uses',return_value={'uncertain':[],'uses':{source.name:[{'pid':1}]}}):
                with self.assertRaisesRegex(AssertionError,'became active'):remote.hardlink_move(row,target.as_posix())
            self.assertTrue(source.exists());self.assertEqual(source.read_bytes(),target.read_bytes())

    def test_existing_archive_receipt_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder,mock.patch.dict('sys.modules',{'fcntl':mock.Mock(LOCK_EX=1,LOCK_NB=2)}),mock.patch.object(remote,'WORK',folder),mock.patch.object(remote.os.path,'isfile',return_value=True),mock.patch.object(remote,'read',return_value={'status':'complete','moved':[]}),mock.patch.object(remote,'create_destination') as create:
            self.assertEqual(remote.archive()['status'],'complete');create.assert_not_called()


if __name__=='__main__':unittest.main()
