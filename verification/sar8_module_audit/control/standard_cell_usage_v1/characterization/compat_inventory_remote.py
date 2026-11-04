"""Exact known installed directories and small SPICE dependency metadata."""
from __future__ import print_function
import hashlib
import json
import os
import re
import resource
import socket

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
root='/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a'
relative=['TSMCHOME/digital','TSMCHOME/digital/Front_End',
 'TSMCHOME/digital/Front_End/timing_power_noise','TSMCHOME/digital/Front_End/timing_power_noise/CCS',
 'tcbn28hpcplusbwp12t30p140_170a_spi/TSMCHOME/digital/Back_End/spice/tcbn28hpcplusbwp12t30p140_170a']
directories=[]
for rel in relative:
    p=os.path.join(root,rel)
    if not os.path.isdir(p):directories.append(dict(path=p,exists=False));continue
    names=sorted(os.listdir(p))
    if len(names)>250:raise ValueError('Exact-directory metadata budget exceeded')
    directories.append(dict(path=p,exists=True,entries=[dict(name=n,bytes=os.stat(os.path.join(p,n)).st_size,is_directory=os.path.isdir(os.path.join(p,n))) for n in names]))
spi=root+'/'+relative[-1]+'/tcbn28hpcplusbwp12t30p140_170a.spi'
if os.stat(spi).st_size>3*1024**2:raise ValueError('Known SPICE size exceeded')
text=open(spi,'rb').read()
includes=re.findall(r'(?mi)^\s*\.(?:include|inc|lib)\s+([^\r\n]+)',text)
models=sorted(set(re.findall(r'(?mi)^\s*M\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)',text)))
header=text.split('.SUBCKT',1)[0].split('.subckt',1)[0]
header_metadata=[]
for line in header.splitlines():
    if re.search(r'version|release|model|process|technology|corner|date',line,re.I):header_metadata.append(line.strip()[:180])
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,directories=directories,
    spice=dict(path=spi,bytes=len(text),sha256=hashlib.sha256(text).hexdigest(),include_dependencies=includes,
               MOS_model_names=models,header_metadata=header_metadata[:12]),
    archives_opened=False,library_bodies_returned=False)))
