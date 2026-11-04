"""Synthetic archive tests only; no remote connection or original simulation."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import unittest
import archive_index as parser

HERE=Path(__file__).resolve().parent


def header(name,size,kind=tarfile.REGTYPE,link=''):
    t=tarfile.TarInfo(name);t.size=size;t.type=kind;t.linkname=link
    return t.tobuf(format=tarfile.USTAR_FORMAT)


def compressed(parts):
    stream=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as f:
        for part in parts:f.write(part)
    return stream.getvalue()


class Tracked(io.BytesIO):
    def __init__(self,blob):super().__init__(blob);self.max_read=0
    def read(self,size=-1):
        if size<0 or size>parser.CHUNK:raise AssertionError('Unbounded compressed read')
        self.max_read=max(self.max_read,size);return super().read(size)


def scan(blob,changes=None,clock=None):
    cfg=json.loads((HERE/'index_config.json').read_text());cfg.update(compressed_max_bytes=len(blob),
        decoded_max_bytes=16*1024**2,internal_wall_seconds=10,stop_after_target_and_release=False,
        verified_prefix_bytes=0)
    cfg.update(changes or {});raw=Tracked(blob);r=parser.GzipStream(raw,len(blob),cfg,clock=clock)
    rows=[];checkpoints=[]
    result=parser.scan(r,cfg,rows.append,checkpoints.append)
    return result,rows,checkpoints,raw


class Bounds(unittest.TestCase):
    def test_chunk_skip_pax_links_and_complete_integrity(self):
        size=5*1024**2;path='some/long/metadata/only/file.lib'
        payload=(' path='+path+'\n').encode();n=len(payload)+len(str(len(payload)))
        while True:
            entry=str(n).encode()+payload
            if len(entry)==n:break
            n=len(entry)
        pieces=[header('first.db',size)]+[b'\x00'*65536]*80
        pieces += [header('PaxHeader',len(entry),tarfile.XHDTYPE),entry,b'\x00'*((-len(entry))%512),header('short',0),
                   header('../link',0,tarfile.SYMTYPE,'/never/read/this'),b'\x00'*1024]
        blob=compressed(pieces);result,rows,cp,raw=scan(blob)
        self.assertEqual(result['index_status'],'complete');self.assertTrue(result['gzip_integrity_verified'])
        self.assertEqual(result['full_compressed_sha256'],hashlib.sha256(blob).hexdigest())
        self.assertEqual([r['name'] for r in rows],['first.db',path,'../link'])
        self.assertEqual(rows[0]['bytes'],size);self.assertTrue(rows[-1]['unsafe_path_observed'])
        self.assertLessEqual(raw.max_read,65536);self.assertLessEqual(result['max_decoded_chunk_bytes'],65536)
        self.assertEqual(result['completed_members'],3);self.assertGreater(len(cp),3)

    def test_early_locator_and_incomplete_bounds(self):
        # Header-only267MB declaration: early stop must not request that body.
        target='CCS/tcbn28hpcplusbwp12t30p140ffg0p99vm40c_ccs.db'
        blob=compressed([header('release_note.txt',0),header(target,267632640)])
        result,rows,cp,raw=scan(blob,dict(stop_after_target_and_release=True))
        self.assertEqual(result['index_status'],'early_target_and_release_locator')
        self.assertFalse(result['archive_index_complete']);self.assertEqual(result['completed_members'],1)
        self.assertEqual(rows[-1]['bytes'],267632640)
        valid=compressed([header('file.db',4096),b'\x00'*4096,b'\x00'*1024])
        for change,reason in [(dict(decoded_max_bytes=1024),'decoded_stream_bytes'),(dict(compressed_max_bytes=10),'compressed_input_bytes')]:
            r,_,cp,_=scan(valid,change);self.assertEqual(r['index_status'],'incomplete_bound');self.assertEqual(r['stop_reason'],reason);self.assertTrue(cp)
        counter=[0]
        def clock():counter[0]+=1;return counter[0]
        r,_,cp,_=scan(valid,dict(internal_wall_seconds=2),clock)
        self.assertEqual(r['index_status'],'incomplete_bound');self.assertTrue(cp)
        config=json.loads((HERE/'index_config.json').read_text());config.update(compressed_max_bytes=len(valid),verified_prefix_bytes=0)
        stream=parser.GzipStream(Tracked(valid),len(valid),config);cp=[]
        def reject(_):raise parser.BoundReached('index_metadata_output_bytes')
        r=parser.scan(stream,config,reject,cp.append)
        self.assertEqual(r['stop_reason'],'index_metadata_output_bytes');self.assertTrue(cp)

    def test_truncation_crc_header_and_prefix_identity(self):
        valid=compressed([header('a',0),b'\x00'*1024])
        for blob in [valid[:-4],valid[:-8]+bytes([valid[-8]^1])+valid[-7:],compressed([b'x'*512]),compressed([header('a',0),b'\x00'*1024,b'hidden trailing data'])]:
            r,_,cp,_=scan(blob);self.assertEqual(r['index_status'],'incomplete_read_error');self.assertTrue(cp)
        r,_,cp,_=scan(valid,dict(verified_prefix_bytes=10,verified_prefix_sha256='0'*64))
        self.assertEqual(r['index_status'],'incomplete_read_error');self.assertIn('prefix',r['stop_reason'])


if __name__=='__main__':unittest.main()
