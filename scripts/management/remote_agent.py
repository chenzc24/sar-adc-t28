"""Project-owned remote worker, Python 2.7/3 stdlib only. No historical writes."""
from __future__ import print_function
import base64, errno, fcntl, hashlib, json, os, re, resource, signal, socket, stat, subprocess, sys, time

ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
UID=596
TERMINAL=set(['complete','failed','rejected','interrupted','limit_exceeded'])

def read(p):
    with open(p) as f:return json.load(f)
def write(p,data):
    tmp=p+'.tmp.'+str(os.getpid())
    with open(tmp,'w') as f:json.dump(data,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.rename(tmp,p)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def identity(pid):
    try:
        with open('/proc/'+str(pid)+'/stat') as f:s=f.read().rsplit(')',1)[1].split()
        return dict(pid=int(pid),start_ticks=s[19],pgid=int(s[2]),state=s[0],boot_id=open('/proc/sys/kernel/random/boot_id').read().strip())
    except (IOError,OSError,IndexError):return None
def same_process(saved):
    current=identity(saved['pid']) if saved else None
    return bool(current and current['start_ticks']==saved.get('start_ticks') and current['boot_id']==saved.get('boot_id')
        and current['pgid']==saved.get('pgid') and current['state']!='Z')
def relative(p):
    assert isinstance(p,str) or isinstance(p,type(u''))
    assert p and not p.startswith('/') and '\\' not in p and re.match(r'^[A-Za-z0-9_.+/-]+\Z',p)
    assert all(x not in ('','.','..') for x in p.split('/'))
    return p
def contained(base,path):
    assert os.path.realpath(base)==base and os.path.realpath(path).startswith(base+'/'),path
    return path
def owned(path):
    assert os.path.realpath(path)==path and os.stat(path).st_uid==UID,path
def mkdir(path):
    if not os.path.exists(path):os.mkdir(path,0o700)
    owned(path)
def runpath(run_id):
    assert re.match(r'^[a-z][a-z0-9_-]{0,63}\Z',run_id),run_id
    return contained(ROOT,ROOT+'/runs/'+run_id)
def policy():return read(ROOT+'/policy.json')
def state(path,phase,**kw):
    p=path+'/'+phase+'.state.json'
    old=read(p) if os.path.isfile(p) else {}
    old.update(kw);old.update(phase=phase,updated_epoch=time.time())
    write(p,old);return old
def snapshot():
    mem={s.split(':')[0]:int(s.split(':')[1].split()[0])*1024 for s in open('/proc/meminfo')}
    cg={};quota=[]
    for line in open('/proc/self/cgroup'):
        _,controllers,p=line.strip().split(':',2)
        if 'memory' in controllers.split(','):
            base='/sys/fs/cgroup/memory';parts=p.strip('/').split('/')
            for i in range(len(parts)+1):
                folder=base+('/'+'/'.join(parts[:i]) if i else '')
                try:
                    limit=int(open(folder+'/memory.limit_in_bytes').read());used=int(open(folder+'/memory.usage_in_bytes').read())
                    if limit<2**60:cg[folder]=dict(limit=limit,used=used,headroom=max(0,limit-used))
                except IOError:pass
        if 'cpu' in controllers.split(','):
            base='/sys/fs/cgroup/cpu';parts=p.strip('/').split('/')
            for i in range(len(parts)+1):
                folder=base+('/'+'/'.join(parts[:i]) if i else '')
                try:
                    q=int(open(folder+'/cpu.cfs_quota_us').read());period=int(open(folder+'/cpu.cfs_period_us').read())
                    if q>0:quota.append(float(q)/period)
                except IOError:pass
    def swap():return {s.split()[0]:int(s.split()[1]) for s in open('/proc/vmstat') if s.startswith(('pswpin ','pswpout '))}
    t=time.time();a=swap();time.sleep(.25);b=swap();dt=max(.001,time.time()-t)
    page=os.sysconf('SC_PAGE_SIZE');rate=sum(max(0,b[k]-a[k]) for k in a)*page/dt
    fs=os.statvfs(ROOT);conflicts=[]
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid)==os.getpid():continue
        try:
            base='/proc/'+pid
            if os.stat(base).st_uid!=UID:continue
            comm=open(base+'/comm').read().strip()
            cmd=open(base+'/cmdline','rb').read().replace(b'\x00',b' ').decode('utf-8','replace')
            if comm.startswith('spectre') or any(x in cmd for x in ['stream_worker.py','reduce_remote.py','stream_reduce.py','/reduce.py']) or ROOT+'/runs/' in cmd:
                conflicts.append(dict(pid=int(pid),comm=comm))
        except (IOError,OSError):pass
    return dict(host=socket.gethostname(),epoch=time.time(),mem_available=mem['MemAvailable'],swap_free=mem['SwapFree'],swap_rate_bytes_s=rate,
        cgroups=cg,cgroup_headroom=min([v['headroom'] for v in cg.values()] or [mem['MemAvailable']]),
        cpu_capacity=min([float(os.sysconf('SC_NPROCESSORS_ONLN'))]+quota),load1=os.getloadavg()[0],
        disk_free=fs.f_bavail*fs.f_frsize,conflicting_processes=conflicts)
def gate(recp,phase,obs,pol):
    budget=recp['resources'];reasons=[]
    rss=budget['simulation_rss_mib'] if phase=='simulation' else budget['analysis_rss_mib']
    need=rss*1024**2;disk=budget['max_output_mib']*1024**2
    if budget['threads']>pol['threads_per_simulation']:reasons.append('threads_exceed_policy')
    if budget['threads']>obs['cpu_capacity']:reasons.append('threads_exceed_cpu_quota')
    if obs['mem_available']<need+pol['host_memory_reserve_mib']*1024**2:reasons.append('host_memory_headroom')
    if obs['cgroup_headroom']<need+pol['user_memory_reserve_mib']*1024**2:reasons.append('user_cgroup_headroom')
    if obs['disk_free']<disk+pol['disk_reserve_mib']*1024**2:reasons.append('disk_headroom')
    if obs['swap_rate_bytes_s']>pol['max_swap_rate_mib_s']*1024**2:reasons.append('active_swapping')
    if obs['load1']>obs['cpu_capacity']*pol['max_load_per_cpu']:reasons.append('cpu_load')
    if obs['conflicting_processes']:reasons.append('existing_simulation_or_analysis')
    if not obs['cgroups']:reasons.append('user_cgroup_observation_missing')
    return dict(pass_gate=not reasons,reasons=reasons,snapshot=obs,phase=phase,policy_sha256=sha(ROOT+'/policy.json') if os.path.exists(ROOT+'/policy.json') else None)
def storage_init(req):
    assert os.getuid()==UID and socket.gethostname().split('.')[0]=='thu-wei'
    parent='/server_local_ssd/chenzc_intern25';owned(parent)
    mounts=[s.split() for s in open('/proc/mounts')]
    mount=next(s for s in mounts if s[1]=='/server_local_ssd')
    assert mount[2] not in ['nfs','nfs4','tmpfs']
    mkdir(ROOT)
    for name in ['runs','tools','locks']:mkdir(ROOT+'/'+name)
    probe=ROOT+'/storage_probe.json'
    if not os.path.exists(probe):write(probe,dict(project='sar-adc-t28',uid=UID,created_epoch=time.time(),purpose='retained_write_read_probe'))
    assert read(probe)['uid']==UID
    write(ROOT+'/policy.json',req['policy'])
    s=os.stat(ROOT);fs=os.statvfs(ROOT)
    return dict(root=ROOT,uid=s.st_uid,mode=oct(s.st_mode & 0o777),mount_device=mount[0],filesystem=mount[2],
        available_bytes=fs.f_bavail*fs.f_frsize,probe_sha256=sha(probe),probe_readback=True,
        retention_policy='scratch; administrator retention/backup guarantees not established',historical_data_changed=False)
def register(req):
    recp=req['recipe'];path=runpath(recp['run_id']);fingerprint=req['recipe_hash']
    if os.path.exists(path):
        assert os.path.isfile(path+'/registered.json'),'Incomplete registration: preserve partial files, reconcile or use a new run ID'
        assert read(path+'/registered.json')['recipe_hash']==fingerprint,'Run ID already has different immutable inputs'
        return dict(existing=True,path=path,recipe_hash=fingerprint)
    os.mkdir(path,0o700);mkdir(path+'/inputs');mkdir(path+'/raw');mkdir(path+'/derived')
    for item in req['files']:
        name=relative(item['name']);dest=contained(path+'/inputs',path+'/inputs/'+name)
        parent=os.path.dirname(dest)
        if not os.path.isdir(parent):os.makedirs(parent,0o700)
        blob=base64.b64decode(item['base64']);assert len(blob)<=32*1024**2
        assert hashlib.sha256(blob).hexdigest()==item['sha256']
        fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(blob)
        os.chmod(dest,0o400)
    for item in recp['files']:assert sha(path+'/inputs/'+relative(item['name']))==item['sha256']
    write(path+'/recipe.json',recp);write(path+'/registered.json',dict(recipe_hash=fingerprint,epoch=time.time(),files_complete=True))
    return dict(existing=False,path=path,recipe_hash=fingerprint)
def inspect(run_id):
    path=runpath(run_id);owned(path);result=dict(run_id=run_id,path=path,registered=read(path+'/registered.json'))
    for phase in ['simulation','analysis']:
        p=path+'/'+phase+'.state.json'
        s=read(p) if os.path.isfile(p) else dict(status='not_started')
        if s.get('status') not in TERMINAL and s.get('worker_identity') and not same_process(s['worker_identity']):
            s=dict(s,observation='worker_not_alive_reconcile_required')
        result[phase]=s
    return result
def spawn(run_id,phase,queue):
    path=runpath(run_id);owned(path);assert read(path+'/registered.json')['files_complete']
    if phase=='analysis':assert inspect(run_id)['simulation'].get('status')=='complete','Native simulation must complete first'
    lock=open(path+'/'+phase+'.launch.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
    try:
        if os.path.exists(path+'/'+phase+'.state.json'):return dict(existing=True,state=inspect(run_id))
        obs=snapshot();recp=read(path+'/recipe.json');g=gate(recp,phase,obs,policy())
        write(path+'/'+phase+'.admission.json',g)
        if not g['pass_gate'] and not queue:return dict(existing=False,admitted=False,gate=g)
        state(path,phase,status='submitted',queued=bool(queue),submitted_epoch=time.time())
        with open(path+'/'+phase+'.worker.log','ab') as log,open('/dev/null','rb') as null:
            child=subprocess.Popen([sys.executable,os.path.abspath(__file__),'worker',run_id,phase],stdin=null,stdout=log,stderr=log,
                preexec_fn=os.setsid,close_fds=True)
        return dict(existing=False,accepted=True,admitted=g['pass_gate'],worker_pid=child.pid,gate=g)
    finally:lock.close()
def group_usage(pgid):
    rss=0;members=[]
    for pid in os.listdir('/proc'):
        if not pid.isdigit():continue
        i=identity(int(pid))
        if not i or i['pgid']!=pgid:continue
        try:
            s={l.split(':')[0]:l.split(':')[1].strip() for l in open('/proc/'+pid+'/status')}
            rss+=int(s.get('VmRSS','0 kB').split()[0])*1024;members.append(int(pid))
        except IOError:pass
    return rss,members
def tree_bytes(path):
    total=0
    for parent,dirs,files in os.walk(path,followlinks=False):
        dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(parent,d))]
        for fn in files:
            try:
                p=os.path.join(parent,fn)
                if not os.path.islink(p):total+=os.path.getsize(p)
            except OSError:pass
    return total
def stop_child(child,saved):
    if same_process(saved) and saved['pgid']==saved['pid']:
        try:os.killpg(saved['pgid'],signal.SIGTERM)
        except OSError as e:
            if e.errno==errno.ESRCH:return
            raise
        for _ in range(20):
            if child.poll() is not None:return
            time.sleep(.1)
        if same_process(saved):
            try:os.killpg(saved['pgid'],signal.SIGKILL)
            except OSError as e:
                if e.errno!=errno.ESRCH:raise

def runtime_reason(rss,elapsed,size,disk,budget,pol,phase):
    if rss>budget[phase+'_rss_mib']*1024**2:return 'aggregate_RSS_limit'
    if elapsed>budget[phase+'_wall_seconds']:return 'wall_time_limit'
    if size is not None and size>budget['max_output_mib']*1024**2:return 'output_size_limit'
    if disk is not None and disk<pol['runtime_disk_floor_mib']*1024**2:return 'runtime_disk_floor'
    return None
def native_summary(path,rc):
    log=path+'/spectre.out';warnings=set();zero=False;version=None;threads=None
    keys=['maxstep','reltol','abstol(V)','abstol(I)','method'];settings=dict((k,None) for k in keys)
    if os.path.isfile(log):
        with open(log) as f:
            for line in f:
                zero=zero or 'spectre completes with 0 errors' in line
                warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
                if line.startswith('Version '):version=line.strip()
                if 'Multithreading' in line or 'threads' in line.lower():threads=line.strip()[:300]
                for k in keys:
                    match=re.match(r'^\s*'+re.escape(k)+r' = (.+)$',line)
                    if match:settings[k]=match.group(1)
    status=path+'/raw/logStatus';passed=os.path.isfile(status) and bool(re.search(r'\bPASS\b',open(status).read()))
    return dict(native_exit=rc,native_analysis_pass=passed,zero_error_footer=zero,version=version,thread_log=threads,
        warning_codes=sorted(warnings),effective_settings=settings,electrical_verdict='not_inferred')
def worker(run_id,phase):
    path=runpath(run_id);owned(path);recp=read(path+'/recipe.json');own=identity(os.getpid())
    state(path,phase,status='queued',worker_identity=own,agent_sha256=sha(os.path.abspath(__file__)))
    budget=recp['resources'];started=time.time();lock=open(ROOT+'/locks/workload.lock','a')
    while True:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);held=True
        except IOError:held=False
        if held:
            g=gate(recp,phase,snapshot(),policy())
            write(path+'/'+phase+'.admission.json',g)
            if g['pass_gate']:break
            fcntl.flock(lock,fcntl.LOCK_UN)
        else:g=dict(pass_gate=False,reasons=['managed_workload_lock'])
        state(path,phase,status='queued',waiting_reasons=g['reasons'])
        if time.time()-started>budget['queue_timeout_seconds']:
            state(path,phase,status='rejected',reason='queue_timeout',gate=g);lock.close();return
        time.sleep(10)
    for item in recp['files']:assert sha(path+'/inputs/'+relative(item['name']))==item['sha256']
    os.nice(10)
    if os.path.exists('/usr/bin/ionice'):subprocess.call(['/usr/bin/ionice','-c','3','-p',str(os.getpid())])
    if phase=='simulation':
        entry=path+'/inputs/'+relative(recp['entry'])
        args=[policy()['spectre_path'],'-64',entry,'+escchars','+log',path+'/spectre.out','-format','psfascii','-raw',path+'/raw']+recp['spectre_args']+['-maxw','5','-maxn','5','+logstatus']
        invocation='source '+policy()['cadence_setup']+'; cd '+path+'/inputs; exec '+' '.join("'"+x.replace("'","'\\''")+"'" for x in args)
        cmd=['/bin/csh','-f','-c',invocation]
        as_limit=budget['simulation_virtual_mib']
    else:
        cmd=[sys.executable,path+'/inputs/'+relative(recp['analyzer']),'--run-dir',path,'--output-dir',path+'/derived']
        as_limit=budget['analysis_virtual_mib']
    def child_setup():
        os.setsid();resource.setrlimit(resource.RLIMIT_AS,(as_limit*1024**2,as_limit*1024**2))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_FSIZE,(budget['max_output_mib']*1024**2,budget['max_output_mib']*1024**2))
    environment=os.environ.copy();environment['HOSTNAME']=socket.gethostname();environment['LD_LIBRARY_PATH']=environment.get('LD_LIBRARY_PATH','')
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:environment[name]='1'
    with open(path+'/'+phase+'.console.log','ab') as console,open('/dev/null','rb') as null:
        child=subprocess.Popen(cmd,cwd=path,stdin=null,stdout=console,stderr=console,preexec_fn=child_setup,close_fds=True,env=environment)
        child_id=identity(child.pid);peak=0;reason=None;t0=time.time();last=-100
        try:
            state(path,phase,status='running',waiting_reasons=[],worker_identity=own,child_identity=child_id,started_epoch=t0,gate=g)
            while child.poll() is None:
                rss,_=group_usage(child.pid);peak=max(peak,rss)
                reason=runtime_reason(rss,time.time()-t0,None,None,budget,policy(),phase)
                if time.time()-last>5:
                    size=tree_bytes(path);last=time.time()
                    disk=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize
                    reason=runtime_reason(rss,time.time()-t0,size,disk,budget,policy(),phase)
                    state(path,phase,status='running',rss_bytes=rss,peak_rss_bytes=peak,output_bytes=size,elapsed_seconds=time.time()-t0)
                if reason:stop_child(child,child_id);break
                time.sleep(.5)
            rc=child.wait()
        except BaseException:
            # A failed receipt write must not leave our newly-created child unbounded.
            stop_child(child,child_id);child.wait();raise
    peak=max(peak,int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)*1024)
    size=tree_bytes(path)
    if size>budget['max_output_mib']*1024**2:reason='output_size_limit'
    result=dict(exit_code=rc,elapsed_seconds=time.time()-t0,peak_rss_bytes=peak,output_bytes=size)
    if phase=='simulation':
        result['native']=native_summary(path,rc)
        ok=rc==0 and result['native']['native_analysis_pass'] and result['native']['zero_error_footer']
    else:ok=rc==0 and os.path.isfile(path+'/derived/result.json')
    result['status']='limit_exceeded' if reason else ('complete' if ok else 'failed')
    if reason:result['reason']=reason
    state(path,phase,**result);lock.close()
def artifacts(run_id):
    path=runpath(run_id);owned(path);out=[]
    candidates=['simulation.state.json','analysis.state.json','simulation.admission.json','analysis.admission.json','spectre.out','raw/logStatus']
    if os.path.isdir(path+'/derived'):
        for parent,dirs,files in os.walk(path+'/derived',followlinks=False):
            dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(parent,d))]
            candidates += [os.path.relpath(os.path.join(parent,f),path) for f in files]
    total=0;limit=policy()['max_collection_mib']*1024**2;skipped=[]
    for name in sorted(set(candidates)):
        p=contained(path,path+'/'+relative(name))
        if not os.path.isfile(p) or os.path.islink(p):continue
        n=os.path.getsize(p)
        if n>limit or total+n>limit:skipped.append(dict(name=name,bytes=n,reason='collection_budget'));continue
        out.append(dict(name=name,bytes=n,sha256=sha(p)));total+=n
    return dict(files=out,skipped=skipped,total_bytes=total,status=inspect(run_id))

LEGACY_PREFIXES=('/home/chenzc_intern25/TSMC28/llm_IO/','/tmp/virtuoso_bridge_chenzc_intern25/90590/')
LEGACY_NAMES=['exit_code','reduce_exit','spectre.out','console.log','reduction.json','reduced_receipt.json',
    'stream_receipt.json','stream_analysis.json','test.raw/logStatus','raw/logStatus']

def legacy_artifacts(path):
    # Read-only small evidence from an exact locally registered historical path.
    assert path.startswith(LEGACY_PREFIXES) and '..' not in path.split('/')
    assert os.path.realpath(path)==path and os.path.isdir(path)
    files=[];skipped=[];total=0;limit=policy()['max_collection_mib']*1024**2
    for name in LEGACY_NAMES:
        p=contained(path,path+'/'+name)
        if not os.path.isfile(p) or os.path.islink(p):continue
        n=os.path.getsize(p)
        if n+total>limit:skipped.append(dict(name=name,bytes=n,reason='collection_budget'));continue
        files.append(dict(name=name,bytes=n,sha256=sha(p)));total+=n
    return dict(remote_path=path,files=files,skipped=skipped,total_bytes=total,read_only=True)
def main(req):
    assert os.getuid()==UID and socket.gethostname().split('.')[0]=='thu-wei','Unexpected execution host/account'
    action=req['action']
    if action=='init':return storage_init(req)
    owned(ROOT);assert os.getuid()==UID
    if action=='register':return register(req)
    if action=='gate':return gate(req['recipe'],req.get('phase','simulation'),snapshot(),policy())
    if action=='status':return inspect(req['run_id'])
    if action in ['submit','analyze']:return spawn(req['run_id'],'simulation' if action=='submit' else 'analysis',req.get('queue',False))
    if action=='artifacts':return artifacts(req['run_id'])
    if action in ['legacy-list','legacy-fetch']:
        listing=legacy_artifacts(req['remote_path'])
        if action=='legacy-list':return listing
        item=next(x for x in listing['files'] if x['name']==req['name'])
        blob=open(req['remote_path']+'/'+item['name'],'rb').read()
        assert hashlib.sha256(blob).hexdigest()==item['sha256']
        return dict(meta=item,base64=base64.b64encode(blob).decode('ascii'))
    if action=='fetch':
        path=runpath(req['run_id']);listing=artifacts(req['run_id'])
        item=next(x for x in listing['files'] if x['name']==req['name'])
        p=path+'/'+relative(req['name']);blob=open(p,'rb').read()
        assert hashlib.sha256(blob).hexdigest()==item['sha256']
        return dict(meta=item,base64=base64.b64encode(blob).decode('ascii'))
    raise ValueError('Unknown action')

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='worker':
        try:worker(sys.argv[2],sys.argv[3])
        except Exception as e:
            state(runpath(sys.argv[2]),sys.argv[3],status='failed',reason=type(e).__name__,message=str(e)[:800]);raise
    else:
        try:print(json.dumps(dict(ok=True,result=main(json.load(sys.stdin)))))
        except Exception as e:print(json.dumps(dict(ok=False,error_type=type(e).__name__,message=str(e))));sys.exit(1)
