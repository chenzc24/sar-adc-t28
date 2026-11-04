"""Recognize protected or inline/dot declarations in the two exact PDK files."""
from __future__ import print_function
import hashlib,json,os,re,resource,socket,time
resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
root='/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/models/spectre/'
names=['crn28ull_1d8_elk_v1d8_2p2_shrink0d9_embedded_usage.scs','cln28ull_1d8_elk_v1d8_3.scs']
start=time.time();out=[]
for name in names:
    path=root+name;stat=os.stat(path);h=hashlib.sha256();counts={};samples=[]
    with open(path,'rb') as f:
        line_no=0
        while True:
            raw=f.readline(262145)
            if not raw:break
            if len(raw)>262144:raise ValueError('Source line bound exceeded')
            h.update(raw);line_no+=1;line=raw.decode('ascii','replace').strip()
            for word in ['protect','encrypt','nch_mac','tmibsimbulk','bsimbulk','bsim6']:
                if re.search(r'\b'+word+r'\b',line,re.I):counts[word]=counts.get(word,0)+1
            match=re.match(r'(?i)^(?:inline\s+)?\.?subckt\s+(nch_mac)\s*(.*)',line)
            if match and len(samples)<16:samples.append(dict(kind='macro_declaration',name=match.group(1),ports=match.group(2)[:180],line=line_no))
            match=re.match(r'(?i)^\.?model\s+(nch_mac\S*)\s+(\S+)',line)
            if match and len(samples)<16:samples.append(dict(kind='model_declaration',name=match.group(1),primitive=match.group(2),line=line_no))
            if re.search(r'(?i)(?:^|\s)(?:protect|encrypt)(?:\s|$)',line) and len(samples)<16:
                samples.append(dict(kind='protection_marker',line=line_no,marker_only=line[:100] if len(line)<100 else 'long_marker_content_not_retained'))
    out.append(dict(path=path,bytes=stat.st_size,sha256=h.hexdigest(),token_line_counts=counts,selected_declarations_or_markers=samples))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,CIW_used=False,elapsed_s=time.time()-start,
    files=out,model_parameters_or_encrypted_content_returned=False)))
