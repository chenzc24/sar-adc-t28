"""Streaming exact-file metadata after failed bounded query; no parameter text."""
from __future__ import print_function
import hashlib
import json
import os
import re
import resource
import socket
import time

resource.setrlimit(resource.RLIMIT_CPU,(8,8))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
root='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/'
specs=[(root+'crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs','0861d3d08ec8a7884bc1f7c45f72bc9ab3df7c860ff8098f76abf1185fd97b96'),
       (root+'cln28ull_1d8_elk_v1d8_3.scs','f60d75ebcc372dbdf5b66391bfc1ef308a0eeac14188e9ad0c1b1b4c00177af6'),
       ('/home/process/tsmc28n/STD_CELL/tcbn28hpcplusbwp12t30p140_190a/tcbn28hpcplusbwp12t30p140_170a_spi/TSMCHOME/digital/Back_End/spice/tcbn28hpcplusbwp12t30p140_170a/tcbn28hpcplusbwp12t30p140_170a.spi','b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e')]
start=time.time();files=[]
for path,want in specs:
    before=os.stat(path)
    if before.st_size>16*1024**2:raise ValueError('Exact-file size bound exceeded')
    h=hashlib.sha256()
    with open(path,'rb') as source:
        while True:
            chunk=source.read(65536)
            if not chunk:break
            h.update(chunk)
    if h.hexdigest()!=want:raise ValueError('Frozen source identity differs')
    rows=[];active=None;section=None;model_count=0;model_samples=[];types=set();block_hash=None;block_lines=0
    with open(path,'rb') as source:
        line_no=0
        while True:
            raw=source.readline(262145)
            if not raw:break
            line_no+=1
            if len(raw)>262144:raise ValueError('Exact-source line bound exceeded')
            line=raw.decode('ascii','replace');stripped=line.strip()
            match=re.match(r'(?i)^section\s+(\S+)',stripped)
            if match:section=match.group(1)
            match=re.match(r'(?i)^\.?subckt\s+(\S+)\s*(.*)',stripped)
            if match:
                active=match.group(1)
                if active.lower() in ['nch_mac','dfcnqd1bwp12t30p140']:
                    rows.append(dict(kind='subckt_header',name=active,ports=match.group(2).strip(),line=line_no,section=section))
                if active.lower()=='nch_mac':block_hash=hashlib.sha256();block_lines=0
            if active and active.lower()=='nch_mac':
                block_hash.update(raw);block_lines+=1
                part=re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)\s+(\S+)',line)
                if part:rows.append(dict(kind='macro_child',parent=active,instance=part.group(1),nodes=part.group(2).split(),model=part.group(3),line=line_no,section=section))
            if active and active.lower()=='dfcnqd1bwp12t30p140':
                tokens=stripped.split()
                if tokens and tokens[0].upper() in ['MM64','MM65','MM66']:
                    rows.append(dict(kind='native_DFF_instance',instance=tokens[0],nodes=tokens[1:5],model=tokens[5],line=line_no))
            model=re.match(r'(?i)^\s*model\s+(\S+)\s+(\S+)',line)
            if model and model.group(1).lower().startswith(('nch','nmos')):
                model_count+=1;types.add(model.group(2))
                if len(model_samples)<16:model_samples.append(dict(name=model.group(1),primitive=model.group(2),line=line_no,section=section))
            if re.match(r'(?i)^\.?ends(?:\s|$)',stripped):
                if active and active.lower()=='nch_mac':rows.append(dict(kind='macro_block_identity',name=active,sha256=block_hash.hexdigest(),lines=block_lines))
                active=None
            if len(rows)>100:raise ValueError('Macro mapping result bound exceeded')
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):raise ValueError('Source changed during read')
    files.append(dict(path=path,bytes=before.st_size,sha256=h.hexdigest(),mapping=rows,nmos_model_header_count=model_count,
        nmos_primitive_types=sorted(types),nmos_model_header_samples=model_samples,model_samples_truncated=model_count>len(model_samples)))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,elapsed_s=time.time()-start,
    exact_files=files,recursive_scan=False,model_parameter_bodies_returned=False,CIW_used=False,method='64KiB SHA stream plus bounded lines')))
