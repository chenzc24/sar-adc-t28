import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

PATH=Path(__file__).resolve().parents[1]/'tools/saradc/managed/batch_follow.py'
spec=importlib.util.spec_from_file_location('batch_follow',PATH)
batch=importlib.util.module_from_spec(spec)
with mock.patch.dict(sys.modules,{'fcntl':mock.MagicMock(),'resource':mock.MagicMock()}):
    spec.loader.exec_module(batch)

class BatchTests(unittest.TestCase):
    def exercise(self,fail=None):
        states={str(i):dict(simulation='not_started',analysis='not_started') for i in range(4)};calls=[]
        def main(req):
            action,rid=req['action'],req['run_id'];s=states[rid]
            if action=='status':return dict(registered={'recipe_hash':rid},**{k:{'status':v} for k,v in s.items()})
            calls.append((action,rid))
            if rid==fail:raise RuntimeError('uncertain transport')
            s['simulation' if action=='submit' else 'analysis']='complete'
            return {'accepted':True}
        def write(path,data):Path(path).write_text(json.dumps(data))
        agent=SimpleNamespace(UID=1,socket=SimpleNamespace(gethostname=lambda:'thu-song'),main=main,write=write,
                              TERMINAL={'complete','failed','interrupted','rejected','limit_exceeded'})
        with tempfile.TemporaryDirectory() as f:
            folder=Path(f).resolve();src=folder/'agent.py';src.write_bytes(b'test')
            (folder/'batch.json').write_text(json.dumps(dict(batch_id='test',host='thu-song',agent_path=str(src),agent_sha256=hashlib.sha256(b'test').hexdigest(),max_inflight_runs=2,runs=[dict(run_id=i,recipe_hash=i) for i in states])))
            with mock.patch.object(batch,'load_agent',return_value=agent),mock.patch.object(batch.os,'getuid',return_value=1,create=True),mock.patch.object(batch.os,'stat',return_value=SimpleNamespace(st_uid=1)),mock.patch.object(batch.os.path,'realpath',side_effect=lambda x:x),mock.patch.object(batch.resource,'getrusage',return_value=SimpleNamespace(ru_maxrss=1)),mock.patch.object(batch.resource,'getrlimit',return_value=(-1,-1)),mock.patch.object(batch.resource,'setrlimit') as limits,mock.patch.object(batch.time,'sleep'):
                batch.run(str(folder))
                limits.assert_called_once_with(batch.resource.RLIMIT_AS,(256*1024**2,-1))
            return json.loads((folder/'status.json').read_text()),calls

    def test_two_inflight_runs_analyzed_before_next_wave(self):
        result,calls=self.exercise()
        self.assertEqual(result['status'],'complete')
        self.assertEqual(calls,[('submit','0'),('submit','1'),('analyze','0'),('analyze','1'),('submit','2'),('submit','3'),('analyze','2'),('analyze','3')])

    def test_uncertain_submission_is_not_retried_and_other_runs_continue(self):
        result,calls=self.exercise('0')
        self.assertEqual(result['status'],'finished_with_failures')
        self.assertEqual(calls.count(('submit','0')),1)
        self.assertNotIn(('analyze','0'),calls)
        self.assertIn(('analyze','3'),calls)

if __name__=='__main__':unittest.main()
