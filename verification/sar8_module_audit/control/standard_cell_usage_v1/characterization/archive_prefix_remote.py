"""Read at most512KiB of archive prefix, stop before first large member."""
from __future__ import print_function
import hashlib
import json
import os
import resource
import socket
import tarfile

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
path='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_180a_ccs.tar.gz'
class Prefix(object):
    def __init__(self,p):self.f=open(p,'rb');self.count=0;self.h=hashlib.sha256()
    def read(self,n):
        if n<0 or self.count+n>512*1024:raise ValueError('Archive prefix compressed-read bound reached')
        blob=self.f.read(n);self.count+=len(blob);self.h.update(blob);return blob
    def close(self):self.f.close()
before=os.stat(path);stream=Prefix(path);members=[]
tar=tarfile.open(fileobj=stream,mode='r|gz')
try:
    for member in tar:
        if len(members)>=8:break
        item=dict(name=member.name,bytes=member.size,is_file=member.isfile())
        members.append(item)
        if member.size>64*1024:
            item['not_read_large_member']=True;break
        if member.isfile():
            blob=tar.extractfile(member).read(64*1024+1)
            if len(blob)!=member.size:raise ValueError('Small member read mismatch')
            item['sha256']=hashlib.sha256(blob).hexdigest()
finally:tar.close();stream.close()
after=os.stat(path)
if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):raise ValueError('Archive metadata changed')
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,archive=path,
    archive_bytes=before.st_size,archive_mtime_epoch=before.st_mtime,compressed_prefix_read_bytes=stream.count,
    compressed_prefix_sha256=stream.h.hexdigest(),prefix_members=members,
    full_archive_scanned=False,large_member_read=False,files_extracted_to_disk=False)))
