"""User-authorized scoped clean file-cache release; never removes waveforms."""
import base64,json,shlex,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
REMOTE=r'''
import os,json,ctypes,stat,time
root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs'
cg='/sys/fs/cgroup/memory/user.slice/user-596.slice'
assert os.getuid()==596
def snapshot():
    v=dict(line.split() for line in open(cg+'/memory.stat'))
    return {'used':int(open(cg+'/memory.usage_in_bytes').read()),'limit':int(open(cg+'/memory.limit_in_bytes').read()),'stat':{k:int(v[k]) for k in ['total_cache','total_rss','total_active_file','total_inactive_file','total_dirty','total_writeback'] if k in v}}
out={'before':snapshot(),'files':[],'processes':[]}
for p in os.listdir('/proc'):
    if not p.isdigit():continue
    try:
        d=dict(line.split(':',1) for line in open('/proc/'+p+'/status') if ':' in line)
        if int(d['Uid'].split()[0])==596:out['processes'].append({'pid':int(p),'name':d['Name'].strip(),'rss_kb':int(d.get('VmRSS','0').split()[0])})
    except (IOError,OSError,KeyError):pass
out['processes']=sorted(out['processes'],key=lambda x:x['rss_kb'],reverse=True)[:15]
ids=['manual8-cdac-l60-ss090cold-v1','manual8-cdac-l60-ff099cold-v1','manual8-cdac-l60-ss081cold-v1','manual8-cdac-nl60-ffhot-v1','manual8-cdac-nl90-ffhot-v1']
lib=ctypes.CDLL(None,use_errno=True)
lib.posix_fadvise.argtypes=[ctypes.c_int,ctypes.c_longlong,ctypes.c_longlong,ctypes.c_int]
for run in ids:
    folder=root+'/'+run
    sim=json.load(open(folder+'/simulation.state.json'))
    assert sim['status'] in ['complete','failed']
    ap=folder+'/analysis.state.json'
    assert not os.path.exists(ap) or json.load(open(ap))['status'] in ['complete','failed','not_started']
    for name in os.listdir(folder+'/raw'):
        p=folder+'/raw/'+name
        if not name.endswith('.tran.tran'):continue
        st=os.lstat(p)
        assert stat.S_ISREG(st.st_mode) and st.st_uid==596 and os.path.realpath(p)==p and p.startswith(root+'/')
        row={'path':p,'size':st.st_size,'mtime':st.st_mtime}
        if RELEASE:
            fd=os.open(p,os.O_RDONLY)
            try:row['fadvise_return']=lib.posix_fadvise(fd,0,0,4)
            finally:os.close(fd)
            after=os.stat(p);assert after.st_size==st.st_size and after.st_mtime==st.st_mtime
        out['files'].append(row)
out['after']=snapshot();out['release_requested']=RELEASE;out['epoch']=time.time()
print(json.dumps(out))
'''
release='--release' in sys.argv
code='RELEASE='+str(release)+'\n'+REMOTE
encoded=base64.b64encode(code.encode()).decode()
cmd='python -c '+shlex.quote("import base64;exec(base64.b64decode('"+encoded+"'))")
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei',cmd],capture_output=True,text=True,timeout=30)
assert p.returncode==0,p.stderr
data=json.loads(p.stdout)
dest=R/'verification/manual_adc/cdac_l60pvt_v1'/('memory_release.json' if release else 'memory_before.json')
assert not dest.exists(),'Preserve earlier observation'
dest.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
