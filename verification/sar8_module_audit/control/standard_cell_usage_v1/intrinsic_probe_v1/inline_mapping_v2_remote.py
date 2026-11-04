"""Exact known inline subckt and underlying model type; parameter text omitted."""
from __future__ import print_function
import hashlib,json,os,re,resource,socket,time
resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
path='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/cln28ull_1d8_elk_v1d8_3.scs'
start=time.time();active=False;rows=[];h=hashlib.sha256();blockbytes=0;finished=False
with open(path,'rb') as f:
    line_no=0
    while True:
        raw=f.readline(262145)
        if not raw:break
        line_no+=1
        if len(raw)>262144:raise ValueError('Source line bound exceeded')
        line=raw.decode('ascii','replace');strip=line.strip()
        match=re.match(r'(?i)^inline\s+subckt\s+nch_mac\s+\(([^)]+)\)',strip)
        if match:
            if active or finished:raise ValueError('Duplicate exact inline declaration')
            active=True;rows.append(dict(kind='inline_header',line=line_no,name='nch_mac',ports=match.group(1).split()))
        if active:
            h.update(raw);blockbytes+=len(raw)
            if blockbytes>16*1024**2:raise ValueError('Inline block size bound exceeded')
            match=re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]+)\)\s+(\S+)',line)
            if match:rows.append(dict(kind='inline_child',line=line_no,name=match.group(1),nodes=match.group(2).split(),model=match.group(3)))
            if re.match(r'(?i)^ends(?:\s|$)',strip):active=False;finished=True;rows.append(dict(kind='inline_end',line=line_no))
        if re.search(r'\bbsimbulk\b',strip,re.I):
            match=re.search(r'(?i)\bmodel\s+(\S+)\s+(bsimbulk)\b',strip)
            rows.append(dict(kind='bsimbulk_model_declaration',line=line_no,name=match.group(1),primitive=match.group(2)) if match else dict(kind='bsimbulk_token_not_model_header',line=line_no))
        if len(rows)>40:raise ValueError('Mapping bound exceeded')
if not finished:raise ValueError('Known inline body missing/incomplete')
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,CIW_used=False,
    file=path,inline_block_bytes=blockbytes,inline_block_sha256=h.hexdigest(),mapping=rows,
    elapsed_s=time.time()-start,model_parameters_returned=False)))
