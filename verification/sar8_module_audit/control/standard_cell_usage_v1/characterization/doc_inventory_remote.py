"""Bounded doc-only metadata; no archive extraction or document contents."""
from __future__ import print_function
import json
import os
import resource
import socket
import time
from distutils.spawn import find_executable

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
root='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a'
doc=root+'/tcbn28hpcplusbwp12t30p140_170a_doc'
rows=[];visited=0
for parent,dirs,files in os.walk(doc,followlinks=False):
    depth=os.path.relpath(parent,doc).count(os.sep)
    if parent==doc:depth=0
    if depth>=6:dirs[:]=[]
    visited+=1
    if visited>30 or len(rows)>200:raise ValueError('Doc-only metadata budget exceeded')
    for name in sorted(files):
        if name.endswith('.pdf') or name in ['IMPORTANT.NOTE','VERSION_NUMBERING_SCHEME.txt']:
            p=os.path.join(parent,name);s=os.stat(p)
            rows.append(dict(path=p,bytes=s.st_size,mtime_epoch=s.st_mtime))
top=os.path.join(root,'TSMCHOME')
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),observed_epoch=time.time(),
    doc_root=doc,doc_files=rows,visited_doc_directories=visited,
    merged_TSMCHOME_entries=sorted(os.listdir(top)),
    pdfinfo=find_executable('pdfinfo'),pdftotext=find_executable('pdftotext'),
    dc_shell=find_executable('dc_shell'),read_only=True,archives_opened=False,contents_read=False)))
