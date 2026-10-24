"""Offline exact duplicate audit; deletion is performed separately via PowerShell."""
import ast
from array import array
import gc
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import re
import shutil
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'output'
MANIFEST = ROOT/'verification/cache_cleanup_20261024.json'
PARSER = ROOT/'scripts/integration/b_short_acceptance.py'

def digest(path, compressed=False):
    h=hashlib.sha256()
    with (gzip.open(path,'rb') if compressed else path.open('rb')) as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

class HashSink:
    def __init__(self): self.h=hashlib.sha256();self.size=0
    def write(self,b):
        view=memoryview(b)
        self.h.update(view);self.size+=view.nbytes

def parser():
    tree=ast.parse(PARSER.read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='stream_psf')
    env=dict(array=array,math=math,re=re)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(PARSER),'exec'),env)
    return env['stream_psf']

def reconstruct(raw,schema):
    with raw.open(encoding='utf-8') as f: parsed=parser()(f)
    parsed={str(k).strip('"').replace('\\','').lower():v for k,v in parsed.items()}
    result={}
    for k,kind in schema:
        v=parsed[k]
        if kind=='list': result[k]=list(v)
        elif kind=='array_d': result[k]=array('d',v)
        elif kind=='numpy_float64': result[k]=np.asarray(v,dtype=np.float64).copy()
        else: raise ValueError(kind)
    return result

def save(r):
    MANIFEST.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    if len(sys.argv)>1 and sys.argv[1]=='restore':
        r=json.loads(MANIFEST.read_text(encoding='utf-8'))
        item=next(x for x in r['verified'] if x['path']==sys.argv[2])
        target=Path(item['path']);raw=Path(item['raw'])
        assert target.resolve().is_relative_to(OUT.resolve()) and not target.exists()
        assert digest(raw)==item['raw_sha256'] and digest(PARSER)==r['parser_sha256']
        wave=reconstruct(raw,item['schema']);sink=HashSink();pickle.dump(wave,sink,protocol=5)
        assert sink.h.hexdigest()==item['sha256']
        with target.open('xb') as f:pickle.dump(wave,f,protocol=5)
        assert digest(target)==item['sha256'];print('RESTORED',target);return
    if len(sys.argv)>1 and sys.argv[1]=='resume':
        r=json.loads(MANIFEST.read_text(encoding='utf-8'))
        assert r['status']=='auditing'
        r['skipped']=[s for s in r['skipped'] if 'PickleBuffer' not in s['reason']]
    else:
        assert not MANIFEST.exists(), 'Do not overwrite audit history'
        r=dict(status='auditing',free_before=shutil.disk_usage(OUT).free,
               parser_sha256=digest(PARSER),verified=[],skipped=[])
    save(r)
    candidates=sorted(OUT.rglob('*.gz'))+sorted(OUT.rglob('waveform.pickle'))
    for p in candidates:
        if any(Path(x['path'])==p for x in r['verified']+r['skipped']):continue
        print('CHECK',p.relative_to(OUT),flush=True)
        try:
            assert not p.is_symlink() and p.resolve().is_relative_to(OUT.resolve())
            if 'cdac10' in str(p):raise ValueError('unrelated experiment')
            item=dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=digest(p))
            if p.suffix=='.gz':
                if p.name not in ('transfer_tran.gz','recovered_transfer.gz'):
                    raise ValueError('test fixture or unknown archive: retain')
                raw=p.parent/'test.raw/tran_perf.tran.tran'
                assert raw.is_file()
                rawhash=digest(raw)
                assert digest(p,True)==rawhash,'decompressed content mismatch'
                item.update(kind='gzip',raw=str(raw.resolve()),raw_sha256=rawhash)
            else:
                receipt=p.parent/'waveform_receipt.json'
                assert json.loads(receipt.read_text())['sha256']==item['sha256']
                raws=list((p.parent/'spectre').rglob('*.tran.tran'))
                assert len(raws)==1,'ambiguous or absent native transient'
                raw=raws[0]
                with p.open('rb') as f: original=pickle.load(f)
                assert original and isinstance(original,dict),'empty or unsupported cache'
                schema=[]
                for k,v in original.items():
                    if isinstance(v,list):kind='list'
                    elif isinstance(v,array) and v.typecode=='d':kind='array_d'
                    elif isinstance(v,np.ndarray) and v.dtype==np.float64 and v.ndim==1:kind='numpy_float64'
                    else:raise ValueError('unsupported cache value type')
                    schema.append((k,kind))
                rebuilt=reconstruct(raw,schema)
                assert all(np.array_equal(original[k],rebuilt[k]) for k in original),'value mismatch'
                sink=HashSink();pickle.dump(rebuilt,sink,protocol=5)
                assert sink.h.hexdigest()==item['sha256'],'exact pickle regeneration differs'
                item.update(kind='pickle',raw=str(raw.resolve()),raw_sha256=digest(raw),schema=schema)
                del original,rebuilt
            r['verified'].append(item);print('VERIFIED',item['bytes'],flush=True)
        except Exception as e:
            r['skipped'].append(dict(path=str(p),reason=str(e)));print('KEEP',str(e),flush=True)
        gc.collect();save(r)
    r.update(status='audited',verified_bytes=sum(x['bytes'] for x in r['verified']))
    save(r);print('AUDIT_COMPLETE',r['verified_bytes'],flush=True)

if __name__=='__main__':main()
