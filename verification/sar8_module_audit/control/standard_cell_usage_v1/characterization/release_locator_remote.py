"""Known documentation directories only; no archive scan or library body."""
from __future__ import print_function
import json
import os
import resource
import socket

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
root='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_doc/TSMCHOME/digital/Documentation'
paths=[root,root+'/documents',root+'/documents/tcbn28hpcplusbwp12t30p140_170a']
rows=[]
for path in paths:
    names=sorted(os.listdir(path))
    if len(names)>200:raise ValueError('Known documentation directory exceeded budget')
    rows.append(dict(path=path,entries=[dict(name=n,is_directory=os.path.isdir(path+'/'+n),bytes=os.stat(path+'/'+n).st_size) for n in names if not n.endswith('.pdf')],PDF_count=sum(n.endswith('.pdf') for n in names)))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,
    exact_directories=rows,archives_opened=False)))
