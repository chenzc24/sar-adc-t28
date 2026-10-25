"""Python2/3 guarded duplicate cleanup helper. No recursive deletion or home writes."""
from __future__ import print_function
import base64,gzip,hashlib,json,os,re,socket,stat,subprocess,sys,time

ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
WORK=ROOT+'/maintenance/cleanup-20261025-c802f73'
ALLOWED=('/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_r4_staged_20261022',
         '/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_r4_idle_20261022')

def read(p):
    with open(p) as f:return json.load(f)

def write(p,d):
    tmp=p+'.tmp.'+str(os.getpid())
    with open(tmp,'w') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    os.rename(tmp,p)

def fingerprint(p):
    assert any(p.startswith(root+'/') for root in ALLOWED),'Outside exact cleanup roots'
    assert os.path.realpath(p)==p,'Symlink path'
    s=os.lstat(p);assert stat.S_ISREG(s.st_mode) and s.st_uid==596 and s.st_nlink==1,'Owner/type/link guard'
    return dict(bytes=s.st_size,mtime=s.st_mtime,ctime=s.st_ctime,inode=s.st_ino,device=s.st_dev,allocated_bytes=s.st_blocks*512)

def unchanged(p,s):
    assert fingerprint(p)==s,'Changed after verification: '+p

def free_space():
    rows=[]
    for root in ALLOWED:
        s=os.statvfs(root)
        rows.append(dict(path=root,device=os.stat(root).st_dev,available_bytes=s.f_bavail*s.f_frsize))
    return rows

def no_use(paths):
    conflicts=[]
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid)==os.getpid():continue
        try:
            base='/proc/'+pid
            if os.stat(base).st_uid!=596:continue
            cmd=open(base+'/cmdline','rb').read().replace(b'\x00',b' ').decode('utf-8','replace')
            try:cwd=os.readlink(base+'/cwd')
            except OSError:cwd=''
            cases={root+'/'+p[len(root)+1:].split('/')[0] for p in paths for root in ALLOWED if p.startswith(root+'/')}
            hit=[p for p in paths if p in cmd or cwd==os.path.dirname(p)]
            hit += [case for case in cases if case in cmd or cwd==case or cwd.startswith(case+'/')]
            descriptors=os.listdir(base+'/fd')
            assert len(descriptors)<4096,'Descriptor audit exceeds bound'
            for name in descriptors:
                try:
                    target=os.readlink(base+'/fd/'+name)
                    if target in paths:hit.append(target)
                except OSError:pass
            if hit:conflicts.append(dict(pid=int(pid),paths=sorted(set(hit))))
        except (IOError,OSError):pass
    assert not conflicts,'Files in use: '+str(conflicts)

def status(**kw):
    p=WORK+'/validation.state.json';s=read(p) if os.path.isfile(p) else {}
    s.update(kw);s['updated_epoch']=time.time();write(p,s);return s

def stream_hash(path,deadline,compressed=False):
    before=fingerprint(path);h=hashlib.sha256();n=0;tail=b'';last=0
    source=gzip.open(path,'rb') if compressed else open(path,'rb')
    try:
        while True:
            b=source.read(1024*1024)
            if not b:break
            h.update(b);n+=len(b);tail=(tail+b)[-2048:]
            if time.time()>deadline:raise RuntimeError('Integrity wall-time limit')
            if time.time()-last>5:status(status='running',current_path=path,current_bytes=n,payload=compressed);last=time.time()
    finally:source.close()
    unchanged(path,before)
    return dict(path=path,sha256=h.hexdigest(),bytes=n,fingerprint=before,PSF_END=tail.rstrip().endswith(b'END'))

def verified_spec():
    spec=read(WORK+'/input.json')
    assert spec['approved_ids']==['L-A1','L-B1','L-B2','S-A1','S-A2']
    assert len(spec['remote_targets'])==15 and len(spec['local_targets'])==21
    targets={r['path'] for r in spec['remote_targets']};retained=set(spec['retained_paths'])
    assert len(targets)==15 and len(retained)==10 and not targets.intersection(retained)
    for p in targets|retained:assert any(p.startswith(root+'/') for root in ALLOWED)
    for root in ALLOWED:assert os.path.realpath(root)==root and os.stat(root).st_uid==596
    return spec

def validate_worker():
    import fcntl,resource
    import policy_agent as gate
    spec=verified_spec();resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(10)
    subprocess.call(['/usr/bin/ionice','-c','3','-p',str(os.getpid())])
    own=gate.identity(os.getpid());status(status='queued',worker_identity=own)
    lock=open(ROOT+'/locks/workload.lock','a');start=time.time()
    budget=dict(resources=dict(threads=1,analysis_rss_mib=256,max_output_mib=8))
    while True:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);held=True
        except IOError:held=False
        if held:
            admission=gate.gate(budget,'analysis',gate.snapshot(),gate.policy())
            status(status='queued',admission=admission)
            if admission['pass_gate']:break
            fcntl.flock(lock,fcntl.LOCK_UN)
        else:status(status='queued',waiting_reasons=['managed_workload_lock'])
        if time.time()-start>3600:raise RuntimeError('Maintenance admission timeout')
        time.sleep(10)
    deadline=time.time()+7200;checks={};paths=sorted(set(spec['retained_paths'])|{r['path'] for r in spec['remote_targets']})
    no_use(paths)
    for i,p in enumerate(paths):
        s=fingerprint(p)
        expected=next((r for r in spec['remote_targets'] if r['path']==p),None)
        if expected:assert s['bytes']==expected['bytes'] and s['mtime']==expected['mtime'],'Changed since approved review'
        result=stream_hash(p,deadline);checks[p]=result
        if p in spec['retained_paths']:assert result['PSF_END'],'Incomplete native PSF'
        write(WORK+'/hash_progress.json',checks);status(status='running',completed_files=i+1,total_files=len(paths))
    # Compare historical chunk hashes and the compressed aggregate.
    parts=sorted([r for r in spec['remote_targets'] if '/transfer_parts_v1/' in r['path']],key=lambda r:r['path'])
    aggregate=hashlib.sha256()
    for r in parts:
        name=os.path.basename(r['path']);assert checks[r['path']]['sha256']==spec['historical_parts'][name]
        with open(r['path'],'rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):aggregate.update(b)
        unchanged(r['path'],checks[r['path']]['fingerprint'])
    assert aggregate.hexdigest()==spec['historical_compressed_sha256']
    archives=[r for r in spec['remote_targets'] if r['path'].endswith('/transfer_tran.gz')];payloads=[]
    for r in archives:
        native=os.path.dirname(r['path'])+'/test.raw/tran_perf.tran.tran'
        assert native in checks
        payload=stream_hash(r['path'],deadline,compressed=True)
        assert payload['sha256']==checks[native]['sha256'] and payload['bytes']==checks[native]['bytes'] and payload['PSF_END'],'Archive payload mismatch'
        payloads.append(payload)
    msb=ALLOWED[0]+'/msb_4600'
    assert checks[msb+'/transfer_tran.gz']['sha256']==aggregate.hexdigest()
    assert checks[msb+'/test.raw/tran_perf.tran.tran']['sha256']==spec['historical_native_sha256']
    no_use(paths)
    result=dict(status='validated',review_sha256=spec['review_sha256'],files=checks,gzip_payloads=payloads,
        retained_paths=spec['retained_paths'],peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,completed_epoch=time.time())
    write(WORK+'/remote_validation.json',result);status(status='complete',completed_files=len(paths),gzip_payloads_verified=len(payloads),peak_rss_kib=result['peak_rss_kib'])
    lock.close()

def launch():
    import fcntl
    import policy_agent as gate
    lock=open(WORK+'/validation.launch.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
    try:
        if os.path.exists(WORK+'/validation.state.json'):return dict(existing=True,state=read(WORK+'/validation.state.json'))
        status(status='submitted')
        with open(WORK+'/worker.log','ab') as log,open('/dev/null','rb') as null:
            p=subprocess.Popen([sys.executable,os.path.abspath(__file__),'validate-worker'],cwd=WORK,stdin=null,stdout=log,stderr=log,preexec_fn=os.setsid,close_fds=True)
        return dict(existing=False,worker_pid=p.pid)
    finally:lock.close()

def home_inventory():
    import pwd
    home=pwd.getpwuid(596).pw_dir
    assert home=='/home/chenzc_intern25' and os.path.realpath(home)==home
    rows=[]
    for name in sorted(os.listdir(home)):
        p=home+'/'+name
        try:
            s=os.lstat(p);kind='directory' if stat.S_ISDIR(s.st_mode) else ('symlink' if stat.S_ISLNK(s.st_mode) else ('file' if stat.S_ISREG(s.st_mode) else 'special'))
            rows.append(dict(name=name,path=p,type=kind,bytes=s.st_size if kind=='file' else None,uid=s.st_uid,mode=oct(s.st_mode & 0o777),mtime=s.st_mtime,nlink=s.st_nlink))
        except OSError as e:rows.append(dict(name=name,path=p,type='unresolved',error=type(e).__name__))
    # Metadata only: match top-level files to currently open descriptors.
    lookup={r['path']:r for r in rows if r['type']=='file'}
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid)==os.getpid():continue
        try:
            base='/proc/'+pid
            if os.stat(base).st_uid!=596:continue
            comm=open(base+'/comm').read().strip()
            for fd in os.listdir(base+'/fd')[:4096]:
                try:
                    path=os.readlink(base+'/fd/'+fd)
                    if path in lookup:lookup[path].setdefault('open_by',[]).append(dict(pid=int(pid),comm=comm))
                except OSError:pass
        except OSError:pass
    result=dict(home=home,host=socket.gethostname(),observed_epoch=time.time(),entries=rows,read_only=True,contents_read=False,
        recursive_directory_sizes_measured=False,total_regular_file_bytes=sum(r.get('bytes') or 0 for r in rows))
    write(WORK+'/home_inventory.json',result);return result

def home_cache_sizes():
    import resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(10)
    home='/home/chenzc_intern25';deadline=time.time()+45;rows=[];odd=[]
    for name in sorted(os.listdir(home)):
        p=home+'/'+name
        if name in ['$D','$DST'] and os.path.isdir(p):
            odd.append(dict(path=p,immediate_entry_count=len(os.listdir(p)),immediate_names=sorted(os.listdir(p))[:20]));continue
        if not name.endswith('.ahdlSimDB'):continue
        assert os.path.realpath(p)==p and os.stat(p).st_uid==596 and os.path.isdir(p)
        row=dict(path=p,bytes=0,allocated_bytes=0,files=0,complete=True,mtime=os.stat(p).st_mtime)
        def onerror(e):row['complete']=False
        for parent,dirs,files in os.walk(p,followlinks=False,onerror=onerror):
            if time.time()>deadline:row['complete']=False;break
            dirs[:]=[d for d in dirs if not os.path.islink(parent+'/'+d)]
            for filename in files:
                s=os.lstat(parent+'/'+filename)
                if stat.S_ISREG(s.st_mode):row['bytes']+=s.st_size;row['allocated_bytes']+=s.st_blocks*512;row['files']+=1
        rows.append(row)
    result=dict(home=home,observed_epoch=time.time(),cache_directories=rows,odd_literal_directories=odd,
        read_only=True,file_contents_read=False,total_bytes=sum(r['bytes'] for r in rows))
    write(WORK+'/home_cache_sizes.json',result);return result

def deletion(req):
    import fcntl
    spec=verified_spec();validation=read(WORK+'/remote_validation.json')
    assert validation['status']=='validated' and req['review_sha256']==spec['review_sha256']
    pairs=req['pairs'];assert len(pairs)==10 and {r['remote_path'] for r in pairs}==set(spec['retained_paths'])
    for r in pairs:assert r['local_sha256']==validation['files'][r['remote_path']]['sha256']
    p=WORK+'/remote_receipt.json'
    if os.path.exists(p):
        old=read(p)
        if old.get('status')=='complete':return old
        raise RuntimeError('Partial prior deletion: reconcile journal; never repeat blindly')
    lock=open(ROOT+'/locks/workload.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    paths=sorted(validation['files']);no_use(paths)
    for path in paths:unchanged(path,validation['files'][path]['fingerprint'])
    receipt=dict(status='deleting',review_sha256=spec['review_sha256'],files=[],permanent=True,retained_paths=spec['retained_paths'],started_epoch=time.time(),free_before=free_space())
    write(p,receipt)
    for row in spec['remote_targets']:
        path=row['path'];unchanged(path,validation['files'][path]['fingerprint']);no_use([path]+spec['retained_paths'])
        item=dict(path=path,bytes=row['bytes'],sha256=validation['files'][path]['sha256'],fingerprint=validation['files'][path]['fingerprint'],status='intent')
        receipt['files'].append(item);write(p,receipt)
        os.unlink(path)  # Exact allowlisted regular file, never a directory or glob.
        assert not os.path.lexists(path);item['status']='deleted_verified';write(p,receipt)
    for path in spec['retained_paths']:unchanged(path,validation['files'][path]['fingerprint'])
    receipt.update(status='complete',deleted_bytes=sum(r['bytes'] for r in receipt['files']),deleted_allocated_bytes=sum(r['fingerprint']['allocated_bytes'] for r in receipt['files']),completed_epoch=time.time(),free_after=free_space())
    write(p,receipt);lock.close();return receipt

def main(req):
    assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
    assert os.path.realpath(WORK)==WORK and os.stat(WORK).st_uid==596
    action=req['action']
    if action=='home':return home_inventory()
    if action=='home-cache-sizes':return home_cache_sizes()
    if action=='launch':return launch()
    if action=='status':
        return dict(state=read(WORK+'/validation.state.json') if os.path.exists(WORK+'/validation.state.json') else None,
            validated=os.path.exists(WORK+'/remote_validation.json'),receipt=read(WORK+'/remote_receipt.json') if os.path.exists(WORK+'/remote_receipt.json') else None)
    if action=='fetch':
        assert req['name'] in ['remote_validation.json','remote_receipt.json','home_inventory.json','hash_progress.json','validation.state.json']
        return read(WORK+'/'+req['name'])
    if action=='delete':return deletion(req)
    if action=='verify-retained':
        validation=read(WORK+'/remote_validation.json');paths=validation['retained_paths'];no_use(paths)
        for path in paths:unchanged(path,validation['files'][path]['fingerprint'])
        return dict(status='retained_unchanged',review_sha256=validation['review_sha256'],paths=paths,epoch=time.time())
    if action=='final-check':
        spec=verified_spec();validation=read(WORK+'/remote_validation.json')
        for path in spec['retained_paths']:unchanged(path,validation['files'][path]['fingerprint'])
        absent=[r['path'] for r in spec['remote_targets'] if not os.path.lexists(r['path'])]
        assert len(absent)==15,'Some approved transfers still exist'
        return dict(status='verified',absent_paths=absent,retained_count=10,free_space=free_space(),epoch=time.time())
    raise ValueError(action)

if __name__=='__main__' and sys.argv[1:]==['validate-worker']:
    try:validate_worker()
    except Exception as e:status(status='failed',error=type(e).__name__,message=str(e)[:1000]);raise
