"""One focused GNU/PAX header-identity test; no archive or server access."""
from pathlib import Path
import io
import json
import sys
import tarfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'index_v1'))
import archive_index as archive
import header_reader


def head(name,size,kind=tarfile.REGTYPE):
    item=tarfile.TarInfo(name);item.size=size;item.type=kind
    return item.tobuf(format=tarfile.USTAR_FORMAT)


def padded(blob):return blob+b'\x00'*((-len(blob))%512)
def pax(key,value):
    payload=(' '+key+'='+value+'\n').encode();size=len(payload)+len(str(len(payload)))
    while True:
        blob=str(size).encode()+payload
        if len(blob)==size:return blob
        size=len(blob)


class Stream(object):
    def __init__(self,data):self.source=io.BytesIO(data);self.position=0;self.max_read=0
    def read_exact(self,size):
        if size>65536:raise AssertionError('Unbounded metadata read')
        self.max_read=max(self.max_read,size);blob=self.source.read(size)
        if len(blob)!=size:raise archive.InvalidArchive('Synthetic stream ended')
        self.position+=size;return blob
    def skip(self,size):
        while size:
            amount=min(65536,size);self.read_exact(amount);size-=amount


def fixture(kind):
    name='TSMCHOME/digital/Front_End/timing_power_noise/CCS/tcbn28hpcplusbwp12t30p140_180a/tcbn28hpcplusbwp12t30p140ffg0p99vm40c_ccs.lib'
    old_size=1024*1024;prior=dict(name='previous.db',bytes=old_size,type='0',decoded_header_offset=0,decoded_body_offset=512,link_name=None)
    body=b'library(synthetic) {}\n';size=len(body)
    if kind=='GNU':
        payload=name.encode()+b'\x00';gap=head('././@LongLink',len(payload),tarfile.GNUTYPE_LONGNAME)+padded(payload)
        target_header=head(name[:100],size)
    elif kind=='PAX':
        payload=pax('path',name)+pax('size',str(size));gap=head('PaxHeaders/target',len(payload),tarfile.XHDTYPE)+padded(payload)
        target_header=head('placeholder.lib',0)
    else:gap=b'';target_header=head(name[:100],size)
    offset=512+old_size+len(gap)
    target=dict(name=name,bytes=size,type='0',decoded_header_offset=offset,decoded_body_offset=offset+512,link_name=None)
    data=head('previous.db',old_size)+b'\x00'*old_size+gap+target_header+body
    return data,prior,target


class FocusedReader(unittest.TestCase):
    def test_GNU_PAX_evidence_and_strict_rejection(self):
        cfg=json.loads((HERE/'semantic_config.json').read_text())
        for kind in ['GNU','PAX']:
            data,prior,target=fixture(kind);stream=Stream(data);checkpoint=[]
            result=header_reader.locate(stream,target,prior,cfg,lambda:checkpoint.append(stream.position))
            self.assertTrue(result['all_required_fields_match'])
            self.assertTrue(result['name_check_preserved'])
            self.assertNotEqual(result['raw_header']['name'],target['name'])
            self.assertEqual(result['recovered_fields']['name'],target['name'])
            self.assertEqual(result['comparisons']['name']['source'],'GNU.longname' if kind=='GNU' else 'PAX.path')
            if kind=='PAX':
                self.assertEqual(result['raw_header']['size'],0)
                self.assertEqual(result['comparisons']['bytes']['source'],'PAX.size')
            self.assertEqual(result['body_bytes_read'],0)
            self.assertEqual(stream.position,target['decoded_body_offset'])
            self.assertLessEqual(stream.max_read,65536);self.assertTrue(checkpoint)
            self.assertEqual(set(result['comparisons']),{'name','bytes','type','decoded_header_offset','decoded_body_offset','link_name'})
            for field,value in [('name','wrong/full/path.lib'),('bytes',target['bytes']+1),('type','2'),('decoded_body_offset',target['decoded_body_offset']+512)]:
                wrong=dict(target);wrong[field]=value
                bad=header_reader.locate(Stream(data),wrong,prior,cfg,lambda:None)
                self.assertFalse(bad['all_required_fields_match'])
                self.assertFalse(bad['comparisons'][field]['match'])
        data,prior,target=fixture('no-extension')
        result=header_reader.locate(Stream(data),target,prior,cfg,lambda:None)
        self.assertFalse(result['comparisons']['name']['match'])
        self.assertFalse(result['all_required_fields_match'])
        # A valid full target name cannot compensate for corrupt header checksum.
        data,prior,target=fixture('GNU');damaged=bytearray(data);damaged[target['decoded_header_offset']+1]^=1
        result=header_reader.locate(Stream(bytes(damaged)),target,prior,cfg,lambda:None)
        self.assertFalse(result['raw_header_checksum_valid']);self.assertFalse(result['all_required_fields_match'])
        print('SYNTHETIC_ONLY: GNU/PAX effective identity recovered with every field recorded; unresolved/wrong name,size,type,offset and checksum rejected; no member body read')


if __name__=='__main__':unittest.main()
