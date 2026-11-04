"""Strict compressed-byte guard and full decoded-byte proof. Python2.7/3."""
from __future__ import print_function
import gzip
import hashlib
import os


class BoundedSink(object):
    def __init__(self,path,cap):
        self.handle=open(path,'wb');self.cap=cap
    def write(self,data):
        if self.handle.tell()+len(data)>self.cap:
            raise ValueError('Compressed native export exceeds declared byte cap: '+str(self.cap))
        return self.handle.write(data)
    def flush(self):self.handle.flush()
    def tell(self):return self.handle.tell()
    def close(self):self.handle.close()


class GzipWriter(object):
    def __init__(self,path,cap):
        self.path=path;self.sink=BoundedSink(path,cap)
        self.stream=gzip.GzipFile(filename='',mode='wb',compresslevel=6,fileobj=self.sink,mtime=0)
        self.digest=hashlib.sha256();self.decoded_bytes=0
    def write(self,blob):
        self.stream.write(blob);self.digest.update(blob);self.decoded_bytes+=len(blob)
    def close(self):
        try:self.stream.close()
        finally:self.sink.close()
    def proof(self):
        return dict(file=os.path.basename(self.path),direct_streaming_gzip=True,
            uncompressed=dict(bytes=self.decoded_bytes,sha256=self.digest.hexdigest()),
            compressed_cap_bytes=self.sink.cap,compressed_bytes=os.path.getsize(self.path))
