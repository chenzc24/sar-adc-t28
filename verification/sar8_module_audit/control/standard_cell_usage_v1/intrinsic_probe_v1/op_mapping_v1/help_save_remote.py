"""Installed exact primitive help only; short wall limit and hard output limit."""
from __future__ import print_function
import hashlib,json,os,re,resource,select,signal,socket,subprocess,time
resource.setrlimit(resource.RLIMIT_CPU,(12,12))
resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2))
exe='/home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre'
args=[exe,'-64','-h','save']
started=time.time();child=subprocess.Popen(args,stdin=open('/dev/null','rb'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=os.setsid)
cap=512*1024;chunks=[];size=0;reason=None
try:
    while True:
        if time.time()-started>8:reason='wall_timeout_8s';break
        ready,_,_=select.select([child.stdout],[],[],.1)
        if ready:
            data=os.read(child.stdout.fileno(),min(8192,cap-size+1))
            if not data:break
            size+=len(data)
            if size>cap:reason='hard_output_limit_512KiB';break
            chunks.append(data)
        elif child.poll() is not None:break
finally:
    if reason or child.poll() is None:
        try:os.killpg(child.pid,signal.SIGKILL)
        except OSError:pass
    rc=child.wait()
blob=b''.join(chunks);text=blob.decode('utf-8','replace');lines=text.splitlines();selected=[]
for i,line in enumerate(lines[:220]):
    selected.append(dict(line=i+1,text=line[:250]))
print(json.dumps(dict(hostname=socket.gethostname(),uid=os.getuid(),read_only=True,CIW_used=False,
    command=args,executable_realpath=os.path.realpath(exe),returncode=rc,stop_reason=reason,elapsed_s=time.time()-started,
    hard_wall_cap_s=8,hard_output_cap_bytes=cap,captured_bytes=len(blob),full_captured_output_sha256=hashlib.sha256(blob).hexdigest(),
    header=[' '.join(x.split())[:240] for x in lines[:10]],selected_semantics=selected,
    tail=[' '.join(x.split())[:240] for x in lines[-4:]],no_simulation_requested=True,no_remote_files_created=True)))
