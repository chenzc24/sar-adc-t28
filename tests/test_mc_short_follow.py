import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('mc_follow',Path(__file__).resolve().parents[1]/'tools/saradc/managed/mc_short_follow.py')
follow=importlib.util.module_from_spec(spec)
with mock.patch.dict(sys.modules,{'fcntl':mock.MagicMock(),'resource':mock.MagicMock(),'imp':mock.MagicMock()}):spec.loader.exec_module(follow)


class FollowTests(unittest.TestCase):
    def test_two_pilots_require_both_random_vectors_to_change(self):
        rows=[dict(run_id='a'),dict(run_id='b')]
        def r(p,m,ok=True):return dict(pilot_pass=ok,random_evidence=dict(process_values_sha256=p,mismatch_values_sha256=m))
        self.assertFalse(follow.pilot_gate(rows,{'a':r('p','m')}))
        self.assertFalse(follow.pilot_gate(rows,{'a':r('p','m'),'b':r('p','n')}))
        self.assertFalse(follow.pilot_gate(rows,{'a':r('p','m'),'b':r('q','n',False)}))
        self.assertTrue(follow.pilot_gate(rows,{'a':r('p','m'),'b':r('q','n')}))

    def test_analysis_only_pilot_and_automatic_extension_without_resimulation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp).resolve();agentfile=folder/'agent.py';agentfile.write_text('test')
            rows=[dict(run_id='a',source_run_id='original',seed=1,pilot=True,group='nom27',recipe_hash='a'),
                  dict(run_id='b',seed=2,pilot=True,group='nom27',recipe_hash='b'),
                  dict(run_id='c',seed=3,pilot=False,group='nom27',recipe_hash='c')]
            cfg=dict(host='thu-song',agent_path=str(agentfile),agent_sha256=hashlib.sha256(b'test').hexdigest(),batch_id='test',max_inflight_runs=2,runs=rows,groups=['nom27'],protected_fft_run='fft',fft_baseline_seconds_per_frame=64)
            (folder/'batch.json').write_text(json.dumps(cfg));states={r['run_id']:dict(simulation='not_applicable' if r['run_id']=='a' else 'not_started',analysis='not_started') for r in rows};calls=[]
            for row in rows:
                p=folder/row['run_id']/'derived';p.mkdir(parents=True)
                result=dict(context=dict(run_id=row.get('source_run_id',row['run_id']),seed=row['seed']),analysis_complete=True,pilot_pass=True,timing_pass=True,settling_screen_pass=True,first_issue=None,first_settling_review=None,random_evidence=dict(valid=True,process_values_sha256=row['run_id'],mismatch_values_sha256=row['run_id']))
                (p/'result.json').write_text(json.dumps(result))
            def main(req):
                rid=req['run_id'];s=states[rid];act=req['action']
                if act=='status':return dict(registered=dict(recipe_hash=rid),**{k:dict(status=v) for k,v in s.items()})
                calls.append((act,rid));s['simulation' if act=='submit' else 'analysis']='complete';return dict(accepted=True)
            agent=SimpleNamespace(UID=1,socket=SimpleNamespace(gethostname=lambda:'thu-song'),main=main,runpath=lambda rid:str(folder/rid),sha=lambda p:'hash',write=lambda p,d:Path(p).write_text(json.dumps(d)),TERMINAL={'complete','failed','interrupted','rejected','limit_exceeded'})
            with mock.patch.object(follow.imp,'load_source',return_value=agent),mock.patch.object(follow.os,'getuid',return_value=1,create=True),mock.patch.object(follow.os,'stat',return_value=SimpleNamespace(st_uid=1)),mock.patch.object(follow.os.path,'realpath',side_effect=lambda x:x),mock.patch.object(follow.resource,'getrusage',return_value=SimpleNamespace(ru_maxrss=1)),mock.patch.object(follow.resource,'getrlimit',return_value=(-1,-1)),mock.patch.object(follow.time,'sleep'):
                follow.run(str(folder))
            self.assertNotIn(('submit','a'),calls)
            self.assertLess(calls.index(('analyze','b')),calls.index(('submit','c')))
            self.assertEqual(json.loads((folder/'status.json').read_text())['status'],'complete')


if __name__=='__main__':unittest.main()
