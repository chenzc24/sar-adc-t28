"""Bounded gzip/tar metadata index. Python2.7/3; never extracts a library."""
from __future__ import print_function
import fnmatch
import hashlib
import json
import os
import time
import zlib

CHUNK=65536


class BoundReached(Exception):pass
class InvalidArchive(Exception):pass


class GzipStream(object):
    def __init__(self,raw,raw_size,limits,clock=None):
        self.raw=raw;self.raw_size=raw_size;self.limits=limits;self.clock=clock or time.time
        self.started=self.clock();self.decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
        self.pending=b'';self.buffer=b'';self.compressed=0;self.decoded=0;self.position=0
        self.digest=hashlib.sha256();self.gzip_end=False;self.done=False;self.max_output_chunk=0
        self.prefix_digest=hashlib.sha256();self.prefix_bytes=0;self.prefix_verified=None
    def guard(self):
        if self.clock()-self.started>=self.limits['internal_wall_seconds']:raise BoundReached('internal_wall_time')
    def raw_block(self):
        self.guard()
        if self.compressed==self.raw_size:return b''
        remaining=self.limits['compressed_max_bytes']-self.compressed
        if remaining<=0:raise BoundReached('compressed_input_bytes')
        size=min(CHUNK,self.raw_size-self.compressed,remaining)
        block=self.raw.read(size)
        if not block:raise InvalidArchive('Compressed file ended before recorded size')
        if len(block)>size:raise InvalidArchive('Raw reader returned more than requested')
        self.compressed+=len(block);self.digest.update(block)
        count=min(len(block),max(0,self.limits.get('verified_prefix_bytes',0)-self.prefix_bytes))
        if count:self.prefix_digest.update(block[:count]);self.prefix_bytes+=count
        if self.limits.get('verified_prefix_bytes') and self.prefix_bytes==self.limits['verified_prefix_bytes']:
            if self.prefix_digest.hexdigest()!=self.limits['verified_prefix_sha256']:raise InvalidArchive('Known compressed archive prefix changed')
            self.prefix_verified=True
        return block
    def fill(self):
        while not self.buffer and not self.done:
            self.guard()
            if self.gzip_end:
                trailing=self.pending or self.raw_block();self.pending=b''
                if trailing:
                    if trailing.strip(b'\x00'):raise InvalidArchive('Trailing data or concatenated gzip unsupported; index not complete')
                    continue
                self.done=True;return
            if not self.pending:self.pending=self.raw_block()
            if not self.pending:
                # Python2 zlib lacks eof: a sentinel must be unused by a fully
                # CRC-validated gzip stream. It is never included in source SHA.
                extra=self.decoder.decompress(b'\x00',1)
                if extra or self.decoder.unused_data!=b'\x00':raise InvalidArchive('Truncated gzip trailer')
                self.gzip_end=True;continue
            remaining=self.limits['decoded_max_bytes']-self.decoded
            if remaining<=0:raise BoundReached('decoded_stream_bytes')
            data=self.decoder.decompress(self.pending,min(CHUNK,remaining))
            self.pending=self.decoder.unconsumed_tail
            if self.decoder.unused_data:
                self.pending=self.decoder.unused_data;self.gzip_end=True
            self.decoded+=len(data);self.max_output_chunk=max(self.max_output_chunk,len(data));self.buffer=data
    def read_some(self,size):
        if not 0<size<=CHUNK:raise ValueError('Only bounded positive reads are permitted')
        self.fill()
        blob=self.buffer[:size];self.buffer=self.buffer[len(blob):];self.position+=len(blob)
        return blob
    def read_exact(self,size):
        if not 0<=size<=CHUNK:raise ValueError('Metadata read exceeds64KiB')
        pieces=[];left=size
        while left:
            blob=self.read_some(left)
            if not blob:raise InvalidArchive('Incomplete tar header or bounded metadata')
            pieces.append(blob);left-=len(blob)
        return b''.join(pieces)
    def skip(self,size):
        while size:
            blob=self.read_some(min(CHUNK,size))
            if not blob:raise InvalidArchive('Truncated tar member body')
            size-=len(blob)
    def drain(self):
        while True:
            blob=self.read_some(CHUNK)
            if not blob:break
            if blob.strip(b'\x00'):raise InvalidArchive('Nonzero decoded data after tar end')


def octal(field):
    if field and bytearray(field)[0]&128:raise InvalidArchive('Unsupported base256 tar number')
    token=field.strip(b'\x00 ')
    if not token:return 0
    if any(x<48 or x>55 for x in bytearray(token)):raise InvalidArchive('Invalid octal tar field')
    return int(token,8)


def text(field):return field.split(b'\x00',1)[0].decode('utf-8','replace')


def header(block):
    if len(block)!=512:raise InvalidArchive('Tar header must be512bytes')
    expected=octal(block[148:156]);actual=sum(bytearray(block[:148]+b'        '+block[156:]))
    if expected!=actual:raise InvalidArchive('Tar header checksum mismatch')
    name=text(block[:100]);prefix=text(block[345:500]) if block[257:262]==b'ustar' else ''
    if prefix:name=prefix+'/'+name
    kind=block[156:157] or b'\x00'
    return dict(name=name,size=octal(block[124:136]),type=kind.decode('ascii','replace'),link_name=text(block[157:257]))


def pax_fields(blob):
    result={};at=0
    while at<len(blob):
        space=blob.find(b' ',at)
        if space<0:raise InvalidArchive('Malformed PAX length')
        try:count=int(blob[at:space])
        except ValueError:raise InvalidArchive('Malformed PAX length integer')
        if count<=space-at+1 or at+count>len(blob):raise InvalidArchive('PAX record crosses metadata bound')
        record=blob[space+1:at+count]
        if not record.endswith(b'\n') or b'=' not in record:raise InvalidArchive('Malformed PAX record')
        key,value=record[:-1].split(b'=',1)
        if key in [b'path',b'linkpath',b'size']:result[key.decode('ascii')]=value.decode('utf-8','replace')
        at+=count
    return result


def scan(stream,cfg,emit,checkpoint):
    state=dict(indexed_headers=0,completed_members=0,last_header_offset=None,last_member=None,
               next_decoded_offset=0,target_FF_members=[],release_metadata_members=[],text_Liberty_members=[])
    local={};global_fields={};long_name=None;long_link=None
    def snapshot():
        value=dict(state,compressed_bytes_read=stream.compressed,decoded_bytes_produced=stream.decoded,
            decoded_bytes_consumed=stream.position,compressed_prefix_sha256=stream.digest.hexdigest(),
            max_decoded_chunk_bytes=stream.max_output_chunk,elapsed_seconds=stream.clock()-stream.started)
        value['known_compressed_prefix_verified']=stream.prefix_verified
        checkpoint(value);return value
    snapshot()
    try:
        while True:
            stream.guard();offset=stream.position;block=stream.read_exact(512)
            if block==b'\x00'*512:
                if stream.read_exact(512)!=b'\x00'*512:raise InvalidArchive('Single tar zero block followed by data')
                stream.drain()
                return dict(snapshot(),index_status='complete',archive_index_complete=True,
                    gzip_integrity_verified=stream.done and stream.gzip_end,full_compressed_sha256=stream.digest.hexdigest())
            item=header(block);state['last_header_offset']=offset
            if item['type'] in ['x','g','L','K']:
                if item['size']>cfg['extended_metadata_max_bytes']:raise BoundReached('extended_tar_metadata_bytes')
                blob=stream.read_exact(item['size']);stream.skip((-item['size'])%512)
                if item['type'] in ['x','g']:
                    fields=pax_fields(blob)
                    if item['type']=='g':global_fields.update(fields)
                    else:local=fields
                elif item['type']=='L':long_name=text(blob)
                else:long_link=text(blob)
                state['next_decoded_offset']=stream.position;snapshot();continue
            fields=dict(global_fields);fields.update(local);local={}
            item['name']=fields.get('path',long_name or item['name']);long_name=None
            item['link_name']=fields.get('linkpath',long_link or item['link_name']);long_link=None
            if 'size' in fields:
                try:item['size']=int(fields['size'])
                except ValueError:raise InvalidArchive('Invalid PAX member size')
            if item['size']<0:raise InvalidArchive('Negative tar member size')
            name=item['name'];lower=name.lower();base=lower.rsplit('/',1)[-1]
            if max(len(json.dumps(x,ensure_ascii=True)) for x in [name,item['link_name']])>cfg['member_path_max_chars']:raise BoundReached('member_path_JSON_length')
            row=dict(name=name,bytes=item['size'],type=item['type'],decoded_header_offset=offset,
                decoded_body_offset=stream.position,link_name=item['link_name'] or None,
                metadata_only=True,body_not_retained=True,unsafe_path_observed=name.startswith('/') or '..' in name.split('/'))
            emit(row);state['indexed_headers']+=1;state['last_member']=name
            compact={k:row[k] for k in ['name','bytes','type','decoded_header_offset','decoded_body_offset']}
            if len(state['target_FF_members'])<8 and any(fnmatch.fnmatch(lower,p) for p in cfg['target_FF_patterns']):state['target_FF_members'].append(compact)
            if len(state['text_Liberty_members'])<8 and (base.endswith('.lib') or base.endswith('.lib.gz')):state['text_Liberty_members'].append(compact)
            related=any(word in base for word in ['release','relnotes','readme','manifest']) and base not in ['important.note','version_numbering_scheme.txt']
            if related and len(state['release_metadata_members'])<16:state['release_metadata_members'].append(compact)
            if cfg['stop_after_target_and_release'] and state['target_FF_members'] and state['release_metadata_members']:
                state['next_decoded_offset']=stream.position
                return dict(snapshot(),index_status='early_target_and_release_locator',archive_index_complete=False,
                    gzip_integrity_verified=False,large_current_member_skipped=False)
            # All library bodies, including267MB db, are discarded64KiB at a time.
            stream.skip(item['size']);stream.skip((-item['size'])%512)
            state['completed_members']+=1;state['next_decoded_offset']=stream.position;snapshot()
    except BoundReached as error:
        return dict(snapshot(),index_status='incomplete_bound',archive_index_complete=False,
            gzip_integrity_verified=False,stop_reason=str(error))
    except (InvalidArchive,zlib.error) as error:
        return dict(snapshot(),index_status='incomplete_read_error',archive_index_complete=False,
            gzip_integrity_verified=False,stop_reason=str(error))
