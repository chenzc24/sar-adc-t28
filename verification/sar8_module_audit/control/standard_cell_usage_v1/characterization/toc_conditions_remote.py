"""Known PDF front-matter section locators and characterization labels only."""
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
def extract(first,last):
    p=subprocess.Popen(['/usr/bin/gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-dFirstPage='+str(first),'-dLastPage='+str(last),'-sDEVICE=txtwrite','-sOutputFile=-',pdf],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    text,error=p.communicate()
    if p.returncode or len(text)>128*1024:raise ValueError('Bounded PDF metadata extraction failed')
    return text.decode('utf-8','replace').splitlines(),hashlib.sha256(text).hexdigest()
lines,h1=extract(1,8)
toc=[dict(line_index=i,text=' '.join(line.split())[:200]) for i,line in enumerate(lines)
     if re.search(r'Chapter|Release Note|Technology|Model|Version|Contents|Characterization',line,re.I)]
lines,h2=extract(14,14)
start=next(i for i,line in enumerate(lines) if '2.2.1' in line)
stop=next(i for i,line in enumerate(lines[start+1:],start+1) if '2.2.2' in line)
labels=[dict(line_index=i,text=' '.join(lines[i].split())[:200]) for i in range(start,stop) if lines[i].strip()]
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,pdf=pdf,
    toc_page_range=[1,8],section_locators=toc[:35],toc_text_sha256=h1,
    characterization_PDF_page=14,characterization_labels=labels,characterization_text_sha256=h2,
    no_document_body_copy=True,archives_opened=False)))
