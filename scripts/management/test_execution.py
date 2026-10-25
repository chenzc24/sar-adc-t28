"""Focused local fixtures; Linux-only syscalls are mocked on Windows."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import execution
import native_summary
import project
from concurrent.futures import ThreadPoolExecutor

if sys.platform=='win32':
    with mock.patch.dict(sys.modules,{'fcntl':mock.MagicMock(),'resource':mock.MagicMock()}):
        import remote_agent as agent
else:
    import remote_agent as agent


class ExecutionChecks(unittest.TestCase):
    def setUp(self):
        self.policy=execution.POLICY
        self.recipe={'resources':dict(threads=4,simulation_rss_mib=512,analysis_rss_mib=128,
            simulation_wall_seconds=120,analysis_wall_seconds=60,max_output_mib=16)}
        self.obs=dict(cpu_capacity=96,mem_available=16*1024**3,cgroup_headroom=90*1024**3,
            cgroups={'user':{}},disk_free=100*1024**3,swap_rate_bytes_s=0,load1=50,conflicting_processes=[])

    def test_admission_allows_known_safe_observation(self):
        self.assertTrue(agent.gate(self.recipe,'simulation',self.obs,self.policy)['pass_gate'])

    def test_admission_rejects_each_risk(self):
        for key,value,reason in [
            ('mem_available',0,'host_memory_headroom'),('cgroup_headroom',0,'user_cgroup_headroom'),
            ('disk_free',0,'disk_headroom'),('swap_rate_bytes_s',5*1024**2,'active_swapping'),
            ('load1',200,'cpu_load'),('conflicting_processes',[{'pid':123}],'existing_simulation_or_analysis'),
            ('cpu_capacity',2,'threads_exceed_cpu_quota'),('cgroups',{},'user_cgroup_observation_missing')]:
            with self.subTest(reason=reason):
                obs=dict(self.obs,**{key:value})
                self.assertIn(reason,agent.gate(self.recipe,'simulation',obs,self.policy)['reasons'])

    def test_runtime_limits_separate_phases_and_resources(self):
        b=self.recipe['resources'];p=self.policy;g=agent.runtime_reason
        self.assertIsNone(g(1,1,1,100*1024**3,b,p,'analysis'))
        self.assertEqual(g(129*1024**2,1,None,None,b,p,'analysis'),'aggregate_RSS_limit')
        self.assertEqual(g(1,61,None,None,b,p,'analysis'),'wall_time_limit')
        self.assertEqual(g(1,1,17*1024**2,None,b,p,'simulation'),'output_size_limit')
        self.assertEqual(g(1,1,1,0,b,p,'simulation'),'runtime_disk_floor')

    def test_path_traversal_is_not_a_run_or_artifact(self):
        for value in ['../old','/tmp/out','ok/../../out','ok\\out']:
            with self.assertRaises(AssertionError):agent.relative(value)
        for value in ['../old','UPPER','bad/id']:
            with self.assertRaises(ValueError):execution.valid_id(value)
        with self.assertRaises(AssertionError):agent.contained('/tmp/example','/tmp/example-sibling/file')

    def test_pid_reuse_cannot_be_killed(self):
        saved={'pid':123,'pgid':123,'start_ticks':'old','boot_id':'boot'}
        current=dict(saved,start_ticks='new',state='R')
        with mock.patch.object(agent,'identity',return_value=current),mock.patch.object(agent.os,'killpg',create=True) as kill:
            agent.stop_child(mock.Mock(),saved)
            kill.assert_not_called()
        with mock.patch.object(agent,'identity',return_value=dict(saved,state='Z')):
            self.assertFalse(agent.same_process(saved))

    def test_only_matching_owned_child_group_is_stopped(self):
        saved={'pid':123,'pgid':123,'start_ticks':'same','boot_id':'boot'}
        child=mock.Mock();child.poll.return_value=0
        with mock.patch.object(agent,'identity',return_value=dict(saved,state='R')),mock.patch.object(agent.os,'killpg',create=True) as kill:
            agent.stop_child(child,saved)
            kill.assert_called_once_with(123,agent.signal.SIGTERM)
        with mock.patch.object(agent,'identity',return_value=dict(saved,pgid=999,state='R')),mock.patch.object(agent.os,'killpg',create=True) as kill:
            agent.stop_child(child,saved)
            kill.assert_not_called()

    def test_partial_and_changed_registration_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(agent,'runpath',return_value=str(Path(folder,'runs','case'))):
            Path(folder,'runs','case').mkdir(parents=True)
            req={'recipe':{'run_id':'case'},'recipe_hash':'new'}
            with self.assertRaisesRegex(AssertionError,'Incomplete registration'):agent.register(req)
            Path(folder,'runs','case','registered.json').write_text(json.dumps({'recipe_hash':'old'}))
            with self.assertRaisesRegex(AssertionError,'different immutable'):agent.register(req)

    def test_transfer_hash_mismatch_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(execution,'OUT',Path(folder)),mock.patch.object(execution,'rpc',return_value={'base64':'YmFk'}):
            dest=Path(folder)
            listing={'total_bytes':3,'files':[{'name':'result.json','bytes':3,'sha256':'0'*64}]}
            with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):execution.transfer(listing,dest,{'action':'fetch'})
            self.assertFalse((dest/'result.json').exists())

    def test_concurrent_local_snapshots_remain_whole_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,'snapshot.json')
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda i:project.save(path,{'index':i,'body':'x'*1000}),range(16)))
            result=project.load(path)
            self.assertIn(result['index'],range(16))
            self.assertEqual(result['body'],'x'*1000)

    def test_sparse_psf_and_group_alias_are_streamed(self):
        text='''HEADER
SWEEP
"time" FLOAT DOUBLE
TRACE
"group" GROUP 1
"out" FLOAT DOUBLE
"in" FLOAT DOUBLE
VALUE
"time" 0
"group" 0
"in" 1
"time" 1e-9
"group" 0.5
"time" 2e-9
"group" 1
END
'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,'test.tran.tran');path.write_text(text)
            s=native_summary.summarize(str(path),['out','in'])
            self.assertEqual(s['native_points'],3)
            self.assertEqual(s['signals']['out']['sample_mean'],.5)
            self.assertEqual(s['signals']['in']['min'],1)
            path.write_text(text.replace('END',''))
            with self.assertRaises(AssertionError):native_summary.summarize(str(path),['out'])

if __name__=='__main__':unittest.main()
