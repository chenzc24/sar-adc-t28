"""Extract only bounded front-matter metadata remotely through Ghostscript."""
from __future__ import print_function
import hashlib
import json
import os
import re
import resource
import socket
import subprocess

resource.setrlimit(resource.RLIMIT_CPU,(15,15))
resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,384*1024**2))
pdf='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_doc/TSMCHOME/digital/Documentation/documents/tcbn28hpcplusbwp12t30p140_170a/DB_TCBN28HPCPLUSBWP12T30P140_FFG0P99VM40C.pdf'
if os.stat(pdf).st_size>20*1024**2:raise ValueError('Known PDF file-size bound exceeded')
h=hashlib.sha256()
with open(pdf,'rb') as f:
    while True:
        block=f.read(65536)
        if not block:break
        h.update(block)
cmd=['/usr/bin/gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-dFirstPage=1','-dLastPage=8','-sDEVICE=txtwrite','-sOutputFile=-',pdf]
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);text,error=p.communicate()
if len(text)>128*1024:raise ValueError('Front-matter extraction output exceeded128KiB')
if p.returncode:raise ValueError('Ghostscript extraction failed:'+error[-500:])
lines=text.decode('utf-8','replace').splitlines();selected=[]
pattern=re.compile(r'version|release|model|slew|transition|threshold|capacitance|operating|DFCNQ|20\s*%|80\s*%|10\s*%|90\s*%',re.I)
for index,line in enumerate(lines):
    if pattern.search(line):
        selected.append(dict(extracted_line_index=index,text=' '.join(line.split())[:220]))
if len(selected)>40:selected=selected[:40]
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,pdf=pdf,
    bytes=os.stat(pdf).st_size,sha256=h.hexdigest(),PDF_page_range=[1,8],extraction_tool='/usr/bin/gs -sDEVICE=txtwrite',
    relevant_front_matter_metadata=selected,full_document_body_returned=False,archives_opened=False)))
