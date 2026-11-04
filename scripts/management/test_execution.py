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

    def test_two_managed_slots_keep_unknown_and_resource_gates(self):
        self.policy=dict(self.policy,max_managed_workloads=2)
        one={'pid':12,'managed':dict(run_id='one',phase='simulation',reserved_rss_mib=512,threads=4)}
        two={'pid':13,'managed':dict(one['managed'],run_id='two')}
        def verdict(items,**kw):
            return agent.gate(self.recipe,'simulation',dict(self.obs,conflicting_processes=items,**kw),self.policy)
        self.assertTrue(verdict([one])['pass_gate'])
        self.assertTrue(verdict([one,dict(one,pid=14)])['pass_gate'])
        self.assertIn('managed_workload_capacity',verdict([one,two])['reasons'])
        self.assertIn('existing_simulation_or_analysis',verdict([one,{'pid':99}])['reasons'])
        reserve=self.policy['host_memory_reserve_mib']*1024**2
        self.assertIn('host_memory_headroom',verdict([one],mem_available=reserve+700*1024**2)['reasons'])
        self.assertIn('aggregate_threads_exceed_cpu_quota',verdict([one],cpu_capacity=6)['reasons'])

    def test_legacy_lock_uses_slot_zero_and_second_slot_is_bounded(self):
        self.policy=dict(self.policy,max_managed_workloads=2)
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(agent.fcntl,'flock',side_effect=[IOError(),None]):
                handle,slot=agent.acquire_workload_slot(self.policy,folder)
                self.assertEqual(slot,1);self.assertTrue(handle.name.endswith('workload.1.lock'));handle.close()
            with mock.patch.object(agent.fcntl,'flock',side_effect=IOError()):
                self.assertEqual(agent.acquire_workload_slot(self.policy,folder),(None,None))

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
        with tempfile.TemporaryDirectory() as folder,mock.patch.object(execution,'OUT',Path(folder)),mock.patch.object(execution,'rpc',return_value={'base64':'YmFk'}) as rpc:
            dest=Path(folder)
            listing={'total_bytes':3,'files':[{'name':'result.json','bytes':3,'sha256':'0'*64}]}
            with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):execution.transfer(listing,dest,{'action':'fetch'})
            self.assertFalse((dest/'result.json').exists())
            rpc.assert_called_once_with({'action':'fetch','name':'result.json'},timeout=180)

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


class AnalysisOnlyChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        self.original={'run_id':'source-case','schema_version':1,'entry':'test.scs'}
        self.hash=execution.recipe_hash(self.original)
        self.recipe={'run_id':'new-export','kind':'analysis_only','analyzer':'export.py',
                     'source':{'run_id':'source-case','recipe_hash':self.hash}}
        self.state={'status':'complete','exit_code':0,'native':{'native_analysis_pass':True,'zero_error_footer':True}}
        (self.path/'raw').mkdir()
        self.save('recipe.json',self.original)
        self.save('registered.json',{'files_complete':True,'recipe_hash':self.hash})
        self.save('simulation.state.json',self.state)
        patch=mock.patch.object(agent,'runpath',return_value=str(self.path));patch.start();self.addCleanup(patch.stop)
        patch=mock.patch.object(agent,'owned');patch.start();self.addCleanup(patch.stop)

    def save(self,name,value):
        (self.path/name).write_text(json.dumps(value))

    def test_completed_source_provenance_and_read_only_command(self):
        before={p.name:p.read_bytes() for p in self.path.iterdir() if p.is_file()}
        proof=agent.validate_phase(self.recipe,'analysis')
        self.assertEqual(proof['recipe_hash'],self.hash)
        cmd=agent.analysis_command('/new-run',self.recipe,proof)
        self.assertEqual(cmd[1:],['/new-run/inputs/export.py','--run-dir','/new-run',
            '--output-dir','/new-run/derived','--source-run-dir',str(self.path)])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.path.iterdir() if p.is_file()})

    def test_incomplete_or_failed_native_source_rejected(self):
        for update in [{'status':'running'},{'exit_code':1},{'native':{}}]:
            self.save('simulation.state.json',dict(self.state,**update))
            with self.assertRaises(AssertionError):agent.validate_phase(self.recipe,'analysis')

    def test_changed_recipe_and_registration_rejected(self):
        self.save('recipe.json',dict(self.original,entry='other.scs'))
        with self.assertRaisesRegex(AssertionError,'recipe hash'):agent.source_provenance(self.recipe)
        self.save('recipe.json',self.original)
        self.save('registered.json',{'files_complete':True,'recipe_hash':'0'*64})
        with self.assertRaisesRegex(AssertionError,'registration'):agent.source_provenance(self.recipe)

    def test_self_and_nested_analysis_sources_rejected(self):
        bad=dict(self.recipe,run_id='source-case')
        with self.assertRaisesRegex(AssertionError,'itself'):agent.source_provenance(bad)
        nested=dict(self.original,kind='analysis_only');h=execution.recipe_hash(nested)
        self.save('recipe.json',nested);self.save('registered.json',{'files_complete':True,'recipe_hash':h})
        bad=dict(self.recipe,source={'run_id':'source-case','recipe_hash':h})
        with self.assertRaisesRegex(AssertionError,'must be a simulation'):agent.source_provenance(bad)

    def test_simulation_refused_local_and_remote_before_launch(self):
        with self.assertRaisesRegex(AssertionError,'cannot execute'):agent.validate_phase(self.recipe,'simulation')
        with mock.patch.object(execution,'recipe',return_value=self.recipe),mock.patch.object(execution,'rpc') as rpc:
            with self.assertRaisesRegex(ValueError,'cannot submit'):execution.phase('submit','new-export')
            rpc.assert_not_called()

    def test_existing_analysis_interface_and_completion_gate_unchanged(self):
        legacy=dict(self.recipe);legacy.pop('kind');legacy.pop('source')
        with mock.patch.object(agent,'inspect',return_value={'simulation':{'status':'complete'}}):
            self.assertIsNone(agent.validate_phase(legacy,'analysis'))
        with mock.patch.object(agent,'inspect',return_value={'simulation':{'status':'failed'}}):
            with self.assertRaisesRegex(AssertionError,'complete first'):agent.validate_phase(legacy,'analysis')
        self.assertNotIn('--source-run-dir',agent.analysis_command('/old-run',legacy))

    def test_analysis_memory_gate_is_still_enforced(self):
        checks=ExecutionChecks();checks.setUp()
        obs=dict(checks.obs,cgroup_headroom=1024**3)
        self.assertIn('user_cgroup_headroom',agent.gate(checks.recipe,'analysis',obs,checks.policy)['reasons'])

    def test_registration_is_hash_stable_for_legacy_and_freezes_analysis_source(self):
        # Build both recipe kinds through real local registration, mocking only RPC/Git.
        root=self.path/'project';root.mkdir();(root/'scripts/management').mkdir(parents=True)
        (root/'scripts/management/native_summary.py').write_text('# default')
        (root/'export.py').write_text('# dedicated')
        (root/'test.scs').write_text('simulator lang=spectre\n')
        registry=root/'management/runs';registry.mkdir(parents=True)
        project.save(registry/'source-case.yaml',{'managed':True,'recipe_hash':self.hash,'recipe':self.original})
        spec={'run_id':'legacy-case','design_id':'test','entry':'test.scs','inputs':[
            {'source':'test.scs','name':'test.scs'}], 'summary_signals':['OUT'],'expected_stop_s':1e-9}
        project.save(root/'spec.yaml',spec)
        with mock.patch.object(execution,'ROOT',root),mock.patch.object(execution,'OUT',root/'output'),\
             mock.patch.object(execution,'SPEC_ROOT',registry),mock.patch.object(project,'git',return_value='commit'),\
             mock.patch.object(execution,'rpc',return_value={'existing':False}) as rpc:
            execution.register('spec.yaml');old=project.load(registry/'legacy-case.yaml')
            self.assertEqual(rpc.call_args.kwargs,{'timeout':180})
            self.assertEqual(rpc.call_args.args[0]['action'],'register')
            self.assertNotIn('kind',old['recipe']);self.assertEqual(old['recipe']['schema_version'],1)
            execution.register('spec.yaml')
            self.assertEqual(old,project.load(registry/'legacy-case.yaml'))
            spec.update(run_id='new-export',kind='analysis_only',source_run_id='source-case',analyzer='export.py',
                        inputs=[{'source':'export.py','name':'export.py'}])
            spec.pop('entry');project.save(root/'spec.yaml',spec)
            execution.register('spec.yaml');new=project.load(registry/'new-export.yaml')['recipe']
            self.assertEqual(new['source'],self.recipe['source']);self.assertEqual(new['entry'],'export.py')
            self.assertEqual(new['schema_version'],2)
            # Changed source metadata cannot be silently rebound under the same export ID.
            project.save(registry/'source-case.yaml',{'managed':True,'recipe_hash':'bad','recipe':self.original})
            with self.assertRaisesRegex(ValueError,'hash mismatch'):execution.register('spec.yaml')

if __name__=='__main__':unittest.main()
