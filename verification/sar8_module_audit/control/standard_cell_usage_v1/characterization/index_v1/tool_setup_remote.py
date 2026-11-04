"""Known setup-directory metadata only; never runs compilers or prints env."""
from __future__ import print_function
import hashlib
import json
import os
import re
import resource
import socket

resource.setrlimit(resource.RLIMIT_CPU,(5,5))
resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2))
root='/home/cshrc';files=[];paths=set();checked=0;truncated=False
if os.path.isdir(root):
    names=sorted(os.listdir(root))
    if len(names)>300:raise ValueError('Known setup directory size bound exceeded')
    selected=[n for n in names if re.search(r'synopsys|(?:^|[._-])dc(?:[._-]|$)|liberty|library.?compiler',n,re.I)][:12]
    for name in selected:
        path=root+'/'+name
        if not os.path.isfile(path):continue
        size=os.stat(path).st_size
        if size>65536:files.append(dict(name=name,bytes=size,contents_not_read='size_bound'));continue
        text=open(path,'rb').read();checked+=1
        files.append(dict(name=name,bytes=size,sha256=hashlib.sha256(text).hexdigest()))
        for line in text.splitlines():
            if re.search(r'license|password|passwd|token|secret|credential|(?:^|_)key',line,re.I):continue
            for value in re.findall(r'/[A-Za-z0-9_.+/-]+',line):
                if re.search(r'synopsys|design.?compiler|library.?compiler|lc_shell|dc_shell',value,re.I) and len(value)<250:
                    if value.rstrip('/') not in paths and len(paths)==30:truncated=True;break
                    paths.add(value.rstrip('/'))
            if truncated:break
        if truncated:break
executables=[]
for path in sorted(paths):
    candidates=[path] if path.endswith(('lc_shell','dc_shell')) else [path+'/lc_shell',path+'/dc_shell',path+'/bin/lc_shell',path+'/bin/dc_shell']
    for candidate in candidates:
        if os.path.isfile(candidate):executables.append(dict(path=candidate,realpath=os.path.realpath(candidate),executable=os.access(candidate,os.X_OK)))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,
    known_setup_root=root,setup_files=files,small_setup_files_read=checked,
    executable_metadata=executables,tool_started=False,environment_or_license_values_returned=False,
    candidate_paths_retained=len(paths),candidate_path_limit=30,partial_tool_setup_inventory=truncated,
    no_tool_installation=True)))
