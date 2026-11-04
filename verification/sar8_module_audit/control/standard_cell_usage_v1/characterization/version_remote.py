"""Read exact small release notes/header metadata; retain no document bodies."""
from __future__ import print_function
import hashlib
import json
import os
import pkgutil
import re
import resource
import socket
from distutils.spawn import find_executable

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
root='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a'
items=[]
for kind in ['doc','spi']:
    top=root+'/tcbn28hpcplusbwp12t30p140_170a_'+kind+'/TSMCHOME'
    for name in ['IMPORTANT.NOTE','VERSION_NUMBERING_SCHEME.txt']:
        p=top+'/'+name
        if not os.path.isfile(p):items.append(dict(path=p,exists=False));continue
        if os.stat(p).st_size>16384:raise ValueError('Small metadata size bound exceeded')
        text=open(p,'rb').read()
        versions=sorted(set(re.findall(r'\b(?:[vV])?[0-9]+(?:\.[0-9]+){1,3}[a-zA-Z]?\b',text)))
        modelnames=sorted(set(re.findall(r'[A-Za-z0-9_+.-]+\.(?:scs|spi|lib|mdl)\b',text)))
        items.append(dict(path=p,exists=True,bytes=len(text),sha256=hashlib.sha256(text).hexdigest(),
            numeric_version_tokens=versions,referenced_model_filenames=modelnames))
spi=root+'/tcbn28hpcplusbwp12t30p140_170a_spi/TSMCHOME/digital/Back_End/spice/tcbn28hpcplusbwp12t30p140_170a/tcbn28hpcplusbwp12t30p140_170a.spi'
head=open(spi,'rb').read(8192)
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,
    release_note_metadata=items,spice_path=spi,spice_header_prefix_sha256=hashlib.sha256(head).hexdigest(),
    spice_header_version_tokens=sorted(set(re.findall(r'\b(?:[vV])?[0-9]+(?:\.[0-9]+){1,3}[a-zA-Z]?\b',head))),
    available_pdf_modules=dict((name,bool(pkgutil.find_loader(name))) for name in ['PyPDF2','pypdf','pdfminer']),
    available_tools=dict((name,find_executable(name)) for name in ['gs','mutool','python3','lc_shell','dc_shell']),
    proprietary_bodies_returned=False,archives_opened=False)))
