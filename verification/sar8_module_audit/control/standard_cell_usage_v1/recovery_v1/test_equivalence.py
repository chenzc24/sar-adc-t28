"""Focused lossless writer/observer equivalence and compressed guard tests."""
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
USAGE=HERE.parent
OWN=USAGE.parent
sys.path.insert(0,str(USAGE));sys.path.insert(0,str(OWN));sys.path.insert(0,str(HERE))


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


old=module('immutable_fast',OWN/'standard_cell_storage_fastanalysis_v1/fast_gate_analyze.py')
sys.modules['fast_gate_analyze']=old
import standard_cell_full_analyze as storage
original_usage=module('original_usage',USAGE/'usage_analyze.py')
import fast_gzip_analyze as new
import storage_gzip
import usage_gzip
from stream_gzip import GzipWriter


class Equivalence(unittest.TestCase):
    def test_all_native_statistics_rows_and_observers(self):
        for case in ['baseline','rck2k']:
            cfg=json.loads((USAGE/case/'measurement.json').read_bytes())
            selected=sorted({old.norm(n) for n in cfg['voltage_saves']+cfg['current_saves']})
            currents={old.norm(n) for n in cfg['current_saves']}
            with tempfile.TemporaryDirectory(prefix='_equivalence_',dir=HERE) as temp:
                root=Path(temp);raw=root/'synthetic.tran.tran';a=root/'old';b=root/'gzip';a.mkdir();b.mkdir()
                with raw.open('w',encoding='ascii',newline='\n') as f:
                    f.write('HEADER\nTYPE\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n')
                    for n in selected:f.write('"'+n+'" FLOAT DOUBLE\n')
                    f.write('VALUE\n')
                    for k,at in enumerate([0.,.25e-9,1e-9,2e-9,10e-9,20e-9]):
                        f.write('"time" %.17g\n'%at)
                        for j,n in enumerate(selected):
                            if k==1 and j%2:continue
                            value=.99 if n=='vdd!' else ((j+1)*1e-8*(-1 if k%2 else 1) if n in currents else [.1,.1,1.3,-.05,.6,1.3][k]+(j%3)*.05)
                            f.write('"%s" %.17g\n'%(n,value))
                    f.write('END\n')
                before=hashlib.sha256(raw.read_bytes()).hexdigest()
                lhs=old.summarize(str(raw),cfg,str(a));rhs=new.summarize(str(raw),cfg,str(b))
                stream=rhs.pop('streaming_export')
                self.assertEqual(json.dumps(lhs,sort_keys=True),json.dumps(rhs,sort_keys=True))
                self.assertEqual((a/'peak.columns.json').read_bytes(),(b/'peak.columns.json').read_bytes())
                with gzip.open(b/'peak.native.bin.gz','rb') as f:decoded=f.read()
                self.assertEqual(decoded,(a/'peak.native.bin').read_bytes())
                self.assertFalse((b/'peak.native.bin').exists())
                self.assertEqual(storage.observe_history(str(a),cfg),storage_gzip.observe_history(str(b),cfg))
                self.assertEqual(original_usage.usage_observations(str(a),cfg),usage_gzip.usage_observations(str(b),cfg))
                rhs['streaming_export']=stream
                proof=storage_gzip.verify_compressed(str(b),cfg,rhs)
                self.assertTrue(proof['decompressed_bytes_and_SHA_match'])
                self.assertEqual(len(rhs['full_history_voltage_stress']),348)
                self.assertEqual(len(cfg['current_saves']),73 if case=='baseline' else 75)
                self.assertEqual(before,hashlib.sha256(raw.read_bytes()).hexdigest())
        print('SYNTHETIC_EQUIVALENCE: all348pairs/73or75currents/sparse rows/KCL/slew/state exact; decoded bytes identical')

    def test_compressed_limit_is_strict_without_decoded_truncation(self):
        with tempfile.TemporaryDirectory(prefix='_guard_',dir=HERE) as temp:
            root=Path(temp);path=root/'compressible.gz'
            payload=b'\x00'*200000;writer=GzipWriter(str(path),1024)
            writer.write(payload);writer.close()
            self.assertLessEqual(path.stat().st_size,1024)
            self.assertEqual(writer.proof()['uncompressed']['bytes'],200000)
            with gzip.open(path,'rb') as f:self.assertEqual(f.read(),payload)
            short=root/'strict.gz';writer=GzipWriter(str(short),64)
            with self.assertRaisesRegex(ValueError,'Compressed native export exceeds'):
                try:writer.write(bytes(range(256))*100)
                finally:writer.close()
            self.assertLessEqual(short.stat().st_size,64)
            self.assertTrue(path.exists())


if __name__=='__main__':unittest.main()
