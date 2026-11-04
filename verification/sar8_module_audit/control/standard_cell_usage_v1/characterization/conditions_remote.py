"""Read only known operating-condition pages, returning parameter metadata."""
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
pattern=re.compile(r'recommended|operating|slew|transition|threshold|capacitan|slope|model|20\s*%|80\s*%|10\s*%|90\s*%|minimum|maximum|typical|voltage|process|temperature',re.I)
pages=[]
for page in [12,13,14,15,16]:
    cmd=['/usr/bin/gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-dFirstPage='+str(page),'-dLastPage='+str(page),'-sDEVICE=txtwrite','-sOutputFile=-',pdf]
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);text,error=p.communicate()
    if p.returncode or len(text)>32768:raise ValueError('Bounded condition-page extraction failed')
    lines=text.decode('utf-8','replace').splitlines();indices=set()
    for i,line in enumerate(lines):
        if pattern.search(line):indices.update(range(max(0,i-1),min(len(lines),i+3)))
    if len(indices)>45:indices=set(sorted(indices)[:45])
    rows=[dict(line_index=i,text=' '.join(lines[i].split())[:220]) for i in sorted(indices) if lines[i].strip()]
    pages.append(dict(PDF_page=page,metadata=rows,extracted_page_text_sha256=hashlib.sha256(text).hexdigest()))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,pdf=pdf,
    pages=pages,document_body_retained_remote=True,archives_opened=False)))
