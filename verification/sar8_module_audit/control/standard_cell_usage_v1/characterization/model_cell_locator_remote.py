"""Small PDK header identifiers and bounded known datasheet index pages."""
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
models='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/'
headers=[]
for name in ['crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs','cln28ull_1d8_elk_v1d8_3.scs']:
    path=models+name;text=open(path,'rb').read(4096)
    rows=[]
    for line in text.splitlines():
        if re.search(r'version|release|technology|model\s+name|hpc|ull|28nm',line,re.I):
            if line.lstrip().startswith(('*','//')):rows.append(line.strip()[:180])
    headers.append(dict(path=path,bytes=os.stat(path).st_size,read_prefix_bytes=len(text),prefix_sha256=hashlib.sha256(text).hexdigest(),header_identifiers=rows[:12]))
pdf='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_doc/TSMCHOME/digital/Documentation/documents/tcbn28hpcplusbwp12t30p140_170a/DB_TCBN28HPCPLUSBWP12T30P140_FFG0P99VM40C.pdf'
p=subprocess.Popen(['/usr/bin/gs','-q','-dSAFER','-dBATCH','-dNOPAUSE','-dFirstPage=32','-dLastPage=40','-sDEVICE=txtwrite','-sOutputFile=-',pdf],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
text,error=p.communicate()
if p.returncode or len(text)>128*1024:raise ValueError('Bounded cell-index extraction failed')
lines=text.decode('utf-8','replace').splitlines();cell_rows=[]
for i,line in enumerate(lines):
    if re.search(r'DFCNQ|DFCNQD1',line,re.I):
        cell_rows.append(dict(line_index=i,text=' '.join(line.split())[:220]))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,
    PDK_headers=headers,PDF_cell_index_page_range=[32,40],DFCNQ_locator_rows=cell_rows[:20],
    cell_index_text_sha256=hashlib.sha256(text).hexdigest(),archives_opened=False,library_model_bodies_returned=False)))
