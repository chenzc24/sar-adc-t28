"""Focused exact-cache path, dependency and removal safety tests."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock
import home_cache_cleanup_remote as remote


class CacheChecks(unittest.TestCase):
    def test_exact_immediate_cache_names_only(self):
        for name in ['../test.ahdlSimDB','test.ahdlSimDB/child','TSMC28','.ahdlSimDB','test.ahdlSimDB\n']:
            with self.assertRaises(AssertionError):remote.valid_name(name)
        self.assertEqual(remote.valid_name('sine_1024_k461.ahdlSimDB'),'sine_1024_k461.ahdlSimDB')

    def test_open_and_mapped_cache_recognition(self):
        text=remote.HOME+'/pilot_aps.ahdlSimDB/a.so (deleted)\n'+remote.HOME+'/test.ahdlSimDB\n/other/test.ahdlSimDB/a.so'
        self.assertEqual(remote.references(text),{'pilot_aps.ahdlSimDB','test.ahdlSimDB'})

    def test_only_specific_non_simulation_roles_excluded(self):
        self.assertNotEqual(remote.process_class('cdsServIpc','Z',''),'inspect')
        self.assertNotEqual(remote.process_class('sshd','S','sshd: chenzc_intern25@pts/0'),'inspect')
        self.assertNotEqual(remote.process_class('sshd','S','sshd: chenzc_intern25'),'inspect')
        for comm,cmd in [('spectre','spectre test.scs'),('sshd','unknown'),('python','sshd: chenzc_intern25@notty')]:
            self.assertEqual(remote.process_class(comm,'S',cmd),'inspect')

    def fixture(self,folder):
        home=Path(folder);cache=home/'known.ahdlSimDB';(cache/'nested').mkdir(parents=True)
        (cache/'nested/library.so').write_bytes(b'regenerable compiled fixture')
        return home,cache

    def test_exact_tree_removal_keeps_siblings(self):
        with tempfile.TemporaryDirectory() as folder:
            home,cache=self.fixture(folder);sibling=home/'keep.scs';sibling.write_bytes(b'source')
            # Use real temporary-file identities; only adapt the Windows uid
            # and path separator differences for this Linux-only operation.
            entries={'.':dict(kind='directory'), 'nested':dict(kind='directory'), 'nested/library.so':dict(kind='file')}
            for relative,row in entries.items():
                path=cache if relative=='.' else cache/relative;s=path.stat()
                row.update(device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mtime=s.st_mtime,ctime=s.st_ctime)
            with mock.patch.object(remote,'HOME',str(home)),mock.patch.object(remote,'UID',cache.stat().st_uid),mock.patch.object(remote,'cache_path',return_value=str(cache)),mock.patch.object(remote,'unchanged'),mock.patch.object(remote.os.path,'realpath',side_effect=lambda p:p):
                remote.remove_tree(dict(name=cache.name,tree=dict(entries=entries)))
            self.assertFalse(cache.exists());self.assertEqual(sibling.read_bytes(),b'source')

    def test_changed_tree_refused(self):
        with mock.patch.object(remote,'cache_path',return_value='/fixture'),mock.patch.object(remote,'tree',return_value={'changed':True}):
            with self.assertRaisesRegex(AssertionError,'Tree changed'):
                remote.unchanged(dict(name='known.ahdlSimDB',tree={'changed':False}))

    def test_generic_recent_and_unknown_origins_retained(self):
        caches=[dict(name=n+'.ahdlSimDB',project_sources=[] if n=='unknown' else ['project.scs'])
            for n in ['input','recent','unknown','known']]
        def metadata(path):
            return dict(latest_mtime=time.time() if 'recent' in path else time.time()-7200)
        proc=dict(uncertain=[],cache_uses={})
        with mock.patch.object(remote,'spec',return_value={'caches':caches}),mock.patch.object(remote,'processes',return_value=proc),mock.patch.object(remote.os.path,'exists',return_value=False),mock.patch.object(remote,'cache_path',side_effect=lambda n:remote.HOME+'/'+n),mock.patch.object(remote,'tree',side_effect=metadata),mock.patch.object(remote,'write'):
            result=remote.audit()
        self.assertEqual([r['name'] for r in result['rows'] if r['eligible']],['known.ahdlSimDB'])

    def test_symlink_and_wrong_owner_refused(self):
        name='known.ahdlSimDB'
        with mock.patch.object(remote.os.path,'realpath',return_value='/elsewhere'):
            with self.assertRaises(AssertionError):remote.cache_path(name)
        bad=mock.Mock(st_uid=597,st_mode=0o40700)
        with mock.patch.object(remote.os.path,'realpath',side_effect=lambda p:p),mock.patch.object(remote.os,'lstat',return_value=bad):
            with self.assertRaises(AssertionError):remote.cache_path(name)

    def test_duplicate_queue_does_not_start_another_worker(self):
        fake_lock=mock.Mock()
        with mock.patch.dict('sys.modules',{'fcntl':mock.Mock(LOCK_EX=1)}),mock.patch('builtins.open',return_value=fake_lock),mock.patch.object(remote.os.path,'exists',return_value=True),mock.patch.object(remote,'read',return_value={'status':'queued','pid':123}),mock.patch.object(remote.subprocess,'Popen') as start:
            self.assertEqual(remote.queue()['pid'],123);start.assert_not_called()

    def test_no_broad_recursive_shell_delete(self):
        source=Path(remote.__file__).read_text(encoding='utf-8')
        self.assertNotIn('rmtree',source);self.assertNotIn('rm -rf',source)
        self.assertIn('os.unlink(target)',source);self.assertIn('os.rmdir(target)',source)


if __name__=='__main__':unittest.main()
