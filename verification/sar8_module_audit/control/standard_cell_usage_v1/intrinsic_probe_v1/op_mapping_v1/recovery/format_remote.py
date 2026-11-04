"""Exactly two completed-run files; selected MM65 OP/port format, no geometry."""
from __future__ import print_function
import hashlib,json,os,re,resource,socket,time
resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8audit-ctrl-mm65-opmapping-ff-v1/raw/'
specs=[('opmap_oppoint.txt',203896,'749067c855c8193da6d3f1b25a9649df56a10c26764146cc1ca68fb9e83230d4'),
       ('opmap_nodes.txt',9797,'ca90a9ba02bdd9a86d22967639d3002c16a10e1fd947db35dfbd60a208212ad4')]
target='XDUT.XU19.XFF.MM65';start=time.time();out=[]
for name,size,want in specs:
    path=root+name;before=os.stat(path)
    if before.st_size!=size or size>256*1024:raise ValueError('Exact completed-file size differs')
    blob=open(path,'rb').read();sha=hashlib.sha256(blob).hexdigest()
    if sha!=want:raise ValueError('Completed native info SHA differs')
    lines=blob.decode('ascii','replace').splitlines();selected=[]
    if name=='opmap_oppoint.txt':
        for index in range(4896,min(5109,len(lines))):
            line=lines[index]
            if target.lower() in line.lower() or re.search(r'(?i)\b(?:ids|id|vds|vgs|gm|gds|region|igidl|igisl|igb|igd|igs|ibd|ibs)\b',line):
                selected.append(dict(line=index+1,text=line[:300]))
    else:
        active=False
        for index,line in enumerate(lines):
            if target.lower() in line.lower():active=True
            elif active and re.search(r'(?i)\bXDUT\.',line) and re.search(r'(?i)\b(?:tmibsimbulk|subckt|instance|device)\b',line):break
            if active:
                selected.append(dict(line=index+1,text=line[:300]))
                if len(selected)>=8:break
    if len(selected)>64:raise ValueError('MM65 format-return bound exceeded')
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):raise ValueError('Source changed during format query')
    out.append(dict(name=name,bytes=size,sha256=sha,selected_format_lines=selected))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,CIW_used=False,
    elapsed_s=time.time()-start,source_run='sar8audit-ctrl-mm65-opmapping-ff-v1',exact_files=out,
    model_or_geometry_bodies_returned=False,no_simulation=True)))
