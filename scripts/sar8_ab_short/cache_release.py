"""User-authorized completed-file cache advice, never deletes data. Remote Py2/3."""
import argparse,base64,json,shlex,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
O=R/'verification/sar8_ab_short/memory_cleanup'
REMOTE=r'''
import os,json,stat,time,ctypes
root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs'
cg='/sys/fs/cgroup/memory/user.slice/user-596.slice'
assert os.getuid()==596 and os.path.realpath(root)==root
def read(p):
    try:return json.load(open(p))
    except (IOError,OSError,ValueError):return {}
def snapshot():
    stats=dict((k,int(v)) for k,v in (x.split() for x in open(cg+'/memory.stat')))
    used=int(open(cg+'/memory.usage_in_bytes').read());limit=int(open(cg+'/memory.limit_in_bytes').read())
    disk=os.statvfs(root)
    return dict(used=used,limit=limit,headroom=limit-used,stat=stats,disk_free=disk.f_bavail*disk.f_frsize)
def processes():
    rows=[];refs=set()
    for pid in os.listdir('/proc'):
        if not pid.isdigit():continue
        d='/proc/'+pid
        try:
            s=dict(x.split(':',1) for x in open(d+'/status') if ':' in x)
            if int(s['Uid'].split()[0])!=596:continue
            rows.append(dict(pid=int(pid),name=s['Name'].strip(),rss_kb=int(s.get('VmRSS','0').split()[0])))
            for fd in os.listdir(d+'/fd'):
                try:refs.add(os.path.realpath(d+'/fd/'+fd))
                except OSError:pass
            for line in open(d+'/maps'):
                parts=line.split(None,5)
                if len(parts)==6 and parts[5].startswith('/'):refs.add(parts[5].strip())
        except (IOError,OSError,KeyError):continue
    return sorted(rows,key=lambda x:x['rss_kb'],reverse=True),refs
def states():
    safe={};protected=set();status_rows=[]
    for run in os.listdir(root):
        d=root+'/'+run
        if not os.path.isdir(d) or os.path.realpath(d)!=d:continue
        sim=read(d+'/simulation.state.json').get('status','unknown')
        ana=read(d+'/analysis.state.json').get('status','not_started')
        recipe=read(d+'/recipe.json');kind=recipe.get('kind','simulation')
        # Exact terminal enum from managed remote_agent.py, including retained failures.
        terminal_states=['complete','failed','rejected','interrupted','limit_exceeded']
        terminal=(sim in terminal_states and ana in terminal_states+['not_started'])
        if kind=='analysis_only':terminal=ana in terminal_states
        if not terminal:
            protected.add(run)
            source=recipe.get('source',{}).get('run_id')
            if source:protected.add(source)
        else:safe[run]=dict(simulation=sim,analysis=ana,kind=kind)
        status_rows.append(dict(run_id=run,simulation=sim,analysis=ana))
    for k in protected:safe.pop(k,None)
    return safe,protected,status_rows
before=snapshot();procs,refs=processes();safe,protected,state_rows=states()
out=dict(before=before,processes=procs[:25],protected_run_ids=sorted(protected),run_states=state_rows,files=[],skipped=[],epoch=time.time(),mode=MODE)
if MODE=='inspect':
    for run in sorted(safe):
        for leaf in ['raw','derived']:
            d=root+'/'+run+'/'+leaf
            if not os.path.isdir(d) or os.path.realpath(d)!=d:continue
            for folder,dirs,names in os.walk(d,followlinks=False):
                dirs[:]=[n for n in dirs if not os.path.islink(folder+'/'+n)]
                for name in names:
                    p=folder+'/'+name
                    try:s=os.lstat(p)
                    except OSError:continue
                    if not stat.S_ISREG(s.st_mode) or s.st_uid!=596 or os.path.realpath(p)!=p or p in refs:continue
                    if s.st_size<1048576:continue
                    out['files'].append(dict(path=p,run_id=run,size=s.st_size,mtime=s.st_mtime,inode=s.st_ino,device=s.st_dev,state=safe[run]))
    out['files'].sort(key=lambda x:x['size'],reverse=True)
else:
    lib=ctypes.CDLL(None,use_errno=True)
    lib.posix_fadvise.argtypes=[ctypes.c_int,ctypes.c_longlong,ctypes.c_longlong,ctypes.c_int]
    lib.posix_fadvise.restype=ctypes.c_int
    for item in CANDIDATES:
        p=item['path'];run=item['run_id']
        if run not in safe or p in refs:out['skipped'].append(dict(path=p,reason='active_or_referenced'));continue
        assert p.startswith(root+'/'+run+'/raw/') or p.startswith(root+'/'+run+'/derived/')
        assert os.path.realpath(p)==p
        s=os.lstat(p)
        assert stat.S_ISREG(s.st_mode) and s.st_uid==596
        assert [s.st_size,s.st_mtime,s.st_ino,s.st_dev]==[item['size'],item['mtime'],item['inode'],item['device']]
        # Recheck state and actual open files immediately before touching this inode.
        live,openrefs=processes();now,blocked,unused=states()
        if run not in now or p in openrefs:out['skipped'].append(dict(path=p,reason='became_active'));continue
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            fs=os.fstat(fd);assert fs.st_ino==s.st_ino and fs.st_dev==s.st_dev
            code=lib.posix_fadvise(fd,0,0,4)
            after=os.fstat(fd)
            assert after.st_size==s.st_size and after.st_mtime==s.st_mtime
        finally:os.close(fd)
        out['files'].append(dict(item,fadvise_return=code))
out['after']=snapshot();out['candidate_bytes']=sum(x['size'] for x in out['files'])
out['used_reduction_bytes']=before['used']-out['after']['used']
out['cache_reduction_bytes']=before['stat'].get('total_cache',0)-out['after']['stat'].get('total_cache',0)
print(json.dumps(out))
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['inspect','release']);p.add_argument('--inventory');p.add_argument('--name',required=True);a=p.parse_args()
    O.mkdir(parents=True,exist_ok=True);dest=O/(a.name+'.json');assert not dest.exists()
    items=json.loads(Path(a.inventory).read_text())['files'] if a.inventory else []
    assert a.mode=='inspect' or items
    code='import sys,json\nrequest=json.load(sys.stdin)\nMODE=request["mode"]\nCANDIDATES=request["items"]\n'+REMOTE
    encoded=base64.b64encode(code.encode()).decode()
    cmd='python -c '+shlex.quote("import base64;exec(base64.b64decode('"+encoded+"'))")
    proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei',cmd],input=json.dumps(dict(mode=a.mode,items=items)),capture_output=True,text=True,timeout=180)
    assert proc.returncode==0,proc.stderr
    data=json.loads(proc.stdout);dest.write_text(json.dumps(data,indent=2)+'\n')
    short={k:data[k] for k in ['mode','candidate_bytes','used_reduction_bytes','cache_reduction_bytes']}
    short.update(file_count=len(data['files']),skipped=len(data['skipped']),before=data['before'],after=data['after'],processes=data['processes'][:8],protected_run_ids=data['protected_run_ids'])
    print(json.dumps(short,indent=2))
if __name__=='__main__':main()
