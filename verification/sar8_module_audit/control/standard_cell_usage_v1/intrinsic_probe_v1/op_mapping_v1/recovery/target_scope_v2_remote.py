"""Verify explicit Instance-scoped MM65 OP block and exact node map; read-only."""
from __future__ import print_function
import hashlib,json,os,re,resource,socket,time
resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/sar8audit-ctrl-mm65-opmapping-ff-v1/raw/'
target='XDUT.XU19.XFF.MM65';out=[];start=time.time()
specs=[('opmap_oppoint.txt',203896,'749067c855c8193da6d3f1b25a9649df56a10c26764146cc1ca68fb9e83230d4'),('opmap_nodes.txt',9797,'ca90a9ba02bdd9a86d22967639d3002c16a10e1fd947db35dfbd60a208212ad4')]
for name,size,want in specs:
    path=root+name;before=os.stat(path);blob=open(path,'rb').read(256*1024+1)
    if len(blob)!=size or hashlib.sha256(blob).hexdigest()!=want:raise ValueError('Completed info identity differs')
    active=False;selected=[];headers=[];fields=[];scope=None;end=None
    for n,line in enumerate(blob.decode('ascii','replace').splitlines(),1):
        if name=='opmap_oppoint.txt':
            header=re.match(r'^Instance:\s+(\S+)\s+of\s+(\S+)\s*$',line)
            if header:
                if active:end=n-1
                active=header.group(1).lower()==target.lower()
                if active:scope=n;headers.append(dict(line=n,text=line))
            if not active:continue
            if line.startswith('Model:'):headers.append(dict(line=n,text=line))
            field=re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$',line)
            if field:
                fields.append(field.group(1))
                if field.group(1).lower() in ['ids','id','vds','vgs','gm','gds','region','igidl','igisl','igs','igd','igb','ibs','ibd']:
                    selected.append(dict(line=n,text=line[:240]))
        else:
            header=re.match(r'^\S+:\s+(\S+)\s+of\s+\S+',line)
            if header:active=header.group(1).lower()==target.lower()
            if active:selected.append(dict(line=n,text=line[:240]))
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):raise ValueError('Source changed')
    out.append(dict(name=name,bytes=size,sha256=want,target_scope_start_line=scope,target_scope_last_line=end,
        explicit_headers=headers,all_target_field_names=fields,selected_actual_format_lines=selected))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,CIW_used=False,
    source_run='sar8audit-ctrl-mm65-opmapping-ff-v1',exact_files=out,elapsed_s=time.time()-start,
    model_or_geometry_parameter_values_returned=False,no_simulation=True)))
