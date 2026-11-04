"""Exact known library root metadata only; Python2.7/3; no filesystem writes."""
from __future__ import print_function
import json
import os
import resource
import socket
import time

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
root='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a'
names=sorted(os.listdir(root))
if len(names)>200:raise ValueError('Unexpected root inventory size')
rows=[]
for name in names:
    path=os.path.join(root,name);s=os.stat(path)
    rows.append(dict(name=name,is_directory=os.path.isdir(path),bytes=s.st_size,mtime_epoch=s.st_mtime))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),observed_epoch=time.time(),
    root=root,entries=rows,read_only=True,recursive_scan=False,contents_read=False)))
