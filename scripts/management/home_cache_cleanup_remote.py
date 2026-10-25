"""Python 2/3 exact-tree cleanup for approved obsolete home AHDL caches only."""
from __future__ import print_function
import hashlib,json,os,re,socket,stat,subprocess,sys,time

HOME='/home/chenzc_intern25'
ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
WORK=ROOT+'/maintenance/home-cache-20261025'
GENERIC=set(['input','test','deck','run','small','control'])
UID=596

def read(path):
    with open(path) as f:return json.load(f)

def write(name,value):
    path=WORK+'/'+name;temporary=path+'.tmp.'+str(os.getpid())
    with open(temporary,'w') as f:
        json.dump(value,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    os.rename(temporary,path)

def valid_name(name):
    assert re.match(r'^[A-Za-z0-9_+.-]+\.ahdlSimDB\Z',name),'Invalid cache name'
    assert name not in ['.ahdlSimDB','..ahdlSimDB']
    return name

def cache_path(name):
    valid_name(name);path=HOME+'/'+name
    assert os.path.dirname(path)==HOME and os.path.realpath(path)==path,'Cache containment/symlink guard'
    s=os.lstat(path)
    assert stat.S_ISDIR(s.st_mode) and s.st_uid==UID,'Cache directory ownership/type guard'
    return path

def tree(path):
    assert os.path.dirname(path)==HOME
    cache_path(os.path.basename(path));device=os.lstat(path).st_dev;entries={};total=allocated=0;latest=0
    def item(p):
        s=os.lstat(p)
        assert os.path.realpath(p)==p and s.st_uid==UID and s.st_dev==device,'Tree owner/link/mount guard'
        kind='directory' if stat.S_ISDIR(s.st_mode) else 'file'
        assert kind=='directory' or (stat.S_ISREG(s.st_mode) and s.st_nlink==1),'Special or shared-link file'
        return dict(kind=kind,device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mtime=s.st_mtime,
            ctime=s.st_ctime,nlink=s.st_nlink,mode=s.st_mode,allocated=s.st_blocks*512)
    entries['.']=item(path)
    def fail(error):raise error
    for parent,dirs,files in os.walk(path,topdown=True,onerror=fail,followlinks=False):
        dirs.sort();files.sort()
        for name in dirs+files:entries[os.path.relpath(parent+'/'+name,path)]=item(parent+'/'+name)
        assert len(entries)<=10000,'Cache entry bound'
    for entry in entries.values():
        latest=max(latest,entry['mtime'])
        if entry['kind']=='file':total+=entry['bytes'];allocated+=entry['allocated']
    return dict(entries=entries,bytes=total,allocated_bytes=allocated,latest_mtime=latest,
        file_count=sum(v['kind']=='file' for v in entries.values()))

def references(text):
    return set(re.findall(re.escape(HOME)+r'/([^/\s]+\.ahdlSimDB)(?=/|\s|$)',text))

def process_class(comm,state,cmd):
    if state=='Z':return 'zombie_no_live_descriptors_or_mappings'
    if comm=='sshd' and re.match(r'^sshd: chenzc_intern25(?:@|\s|\[|$)',cmd):
        return 'privilege_separated_ssh_transport_not_simulator'
    return 'inspect'

def processes():
    uses={};spectre=[];uncertain=[];excluded=[]
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid)==os.getpid():continue
        base='/proc/'+pid
        try:
            if os.stat(base).st_uid!=596:continue
            with open(base+'/comm') as f:comm=f.read().strip()
            with open(base+'/stat') as f:process_state=f.read().rsplit(')',1)[1].split()[0]
            with open(base+'/cmdline','rb') as f:cmd=f.read(65536).replace(b'\x00',b' ').decode('utf-8','replace')
            classification=process_class(comm,process_state,cmd)
            if classification!='inspect':
                excluded.append(dict(pid=int(pid),comm=comm,classification=classification));continue
            if comm.startswith('spectre'):spectre.append(dict(pid=int(pid),comm=comm))
            texts=[cmd,os.readlink(base+'/cwd'),os.readlink(base+'/exe')]
            with open(base+'/maps') as f:
                maps=f.read(4*1024**2+1)
                assert len(maps)<=4*1024**2,'Process map bound'
                texts.append(maps)
            descriptors=os.listdir(base+'/fd');assert len(descriptors)<=8192,'Descriptor bound'
            for fd in descriptors:
                try:texts.append(os.readlink(base+'/fd/'+fd))
                except OSError as e:
                    if e.errno!=2:raise
            for name in references('\n'.join(texts)):
                uses.setdefault(name,[]).append(dict(pid=int(pid),comm=comm))
        except (IOError,OSError,AssertionError) as e:
            if not os.path.exists(base):continue
            # A live, unauditable own-user process makes unused status uncertain.
            uncertain.append(dict(pid=int(pid),error=type(e).__name__))
    return dict(cache_uses=uses,spectre=spectre,uncertain=uncertain,non_simulation_exclusions=excluded)

def spec():
    s=read(WORK+'/input.json');assert s['home']==HOME and s['authorization']=='delete_old_unused_home_compile_caches'
    assert len({r['name'] for r in s['caches']})==len(s['caches'])
    for r in s['caches']:valid_name(r['name'])
    return s

def audit():
    if os.path.exists(WORK+'/receipt.json'):return dict(status='receipt_exists_use_verify')
    if os.path.exists(WORK+'/queue.state.json'):return read(WORK+'/audit.json')
    if os.path.exists(WORK+'/audit.json'):
        old=read(WORK+'/audit.json')
        digest=hashlib.sha256(json.dumps(old,sort_keys=True).encode('utf-8')).hexdigest()[:16]
        archive='audit_'+digest+'.json'
        if not os.path.exists(WORK+'/'+archive):write(archive,old)
    s=spec();proc=processes();rows=[];deadline=time.time()+60
    for row in s['caches']:
        assert time.time()<deadline,'Audit time bound'
        name=row['name'];record=dict(name=name,path=HOME+'/'+name,reasons=[])
        if not row['project_sources']:record['reasons'].append('project_origin_unconfirmed')
        if name[:-10] in GENERIC:record['reasons'].append('ambiguous_generic_name')
        if proc['uncertain']:record['reasons'].append('process_audit_uncertain')
        if name in proc['cache_uses']:record['reasons'].append('in_use');record['processes']=proc['cache_uses'][name]
        try:
            record['tree']=tree(cache_path(name))
            if time.time()-record['tree']['latest_mtime']<3600:record['reasons'].append('modified_within_one_hour')
        except (OSError,IOError,AssertionError) as e:record['reasons'].append('unsafe_or_unresolved_tree');record['error']=str(e)[:200]
        record['eligible']=not record['reasons'];rows.append(record)
    result=dict(status='audited',rows=rows,processes=proc,epoch=time.time(),home=HOME)
    write('audit.json',result);return result

def unchanged(row):
    assert tree(cache_path(row['name']))==row['tree'],'Tree changed after audit'

def remove_tree(row):
    path=cache_path(row['name']);unchanged(row)
    entries=row['tree']['entries']
    for relative in sorted(entries,key=lambda r:(r.count('/'),r),reverse=True):
        if relative=='.' or entries[relative]['kind']!='file':continue
        target=path+'/'+relative
        assert os.path.realpath(target)==target and target.startswith(path+'/')
        s=os.lstat(target);expected=entries[relative]
        assert stat.S_ISREG(s.st_mode) and s.st_uid==UID and s.st_nlink==1
        assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime,s.st_ctime)==(expected['device'],expected['inode'],expected['bytes'],expected['mtime'],expected['ctime'])
        os.unlink(target)
    directories=[r for r in entries if entries[r]['kind']=='directory']
    for relative in sorted(directories,key=lambda r:(0 if r=='.' else r.count('/')+1,r),reverse=True):
        target=path if relative=='.' else path+'/'+relative
        assert os.path.realpath(target)==target
        s=os.lstat(target);expected=entries[relative]
        assert stat.S_ISDIR(s.st_mode) and s.st_uid==UID and (s.st_dev,s.st_ino)==(expected['device'],expected['inode'])
        os.rmdir(target)  # Empty exact verified cache directories only.
    assert not os.path.lexists(path)

def free_bytes():
    s=os.statvfs(HOME);return s.f_bavail*s.f_frsize

def delete():
    import fcntl
    if os.path.exists(WORK+'/receipt.json'):
        receipt=read(WORK+'/receipt.json')
        assert receipt['status']=='complete','Partial cleanup: reconcile before any retry'
        return receipt
    lock=open(ROOT+'/locks/workload.lock','r+')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except IOError:
        lock.close();return dict(status='deferred',reason='managed_workload_lock')
    try:
        proc=processes()
        if proc['spectre'] or proc['uncertain']:return dict(status='deferred',reason='active_spectre_or_uncertain_process',processes=proc)
        source=read(WORK+'/audit.json');spec();eligible=[];retained=[]
        for row in source['rows']:
            if not row['eligible']:retained.append(dict(name=row['name'],reasons=row['reasons']));continue
            try:
                assert row['name'] not in proc['cache_uses'],'Currently in use'
                unchanged(row);eligible.append(row)
            except (AssertionError,IOError,OSError):retained.append(dict(name=row['name'],reasons=['changed_or_in_use_after_audit']))
        receipt=dict(status='deleting',deleted=[],retained=retained,free_before=free_bytes(),started_epoch=time.time(),permanent=True)
        write('receipt.json',receipt);deadline=time.time()+90
        for index,row in enumerate(eligible):
            assert time.time()<deadline,'Cleanup time bound'
            if index%20==0:
                live=processes();assert not live['spectre'] and not live['uncertain'],'New process: stop and reconcile'
                assert not any(r['name'] in live['cache_uses'] for r in eligible[index:]),'New live cache reference'
            unchanged(row)
            entry=dict(name=row['name'],path=row['path'],bytes=row['tree']['bytes'],allocated_bytes=row['tree']['allocated_bytes'],files=row['tree']['file_count'],status='intent')
            receipt['deleted'].append(entry);write('receipt.json',receipt)
            remove_tree(row);entry['status']='deleted_verified';write('receipt.json',receipt)
        receipt.update(status='complete',completed_epoch=time.time(),free_after=free_bytes(),
            deleted_bytes=sum(r['bytes'] for r in receipt['deleted']),deleted_allocated_bytes=sum(r['allocated_bytes'] for r in receipt['deleted']))
        write('receipt.json',receipt);return receipt
    finally:lock.close()

def verify():
    receipt=read(WORK+'/receipt.json');assert receipt['status']=='complete'
    assert all(not os.path.lexists(r['path']) for r in receipt['deleted'])
    assert all(os.path.lexists(HOME+'/'+r['name']) for r in receipt['retained'])
    result=dict(status='verified',deleted_count=len(receipt['deleted']),retained_count=len(receipt['retained']),
        remaining_home_cache_names=sorted(n for n in os.listdir(HOME) if n.endswith('.ahdlSimDB')),epoch=time.time())
    write('verification.json',result);return result

def queue():
    import fcntl
    lock=open(WORK+'/queue.launch.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
    try:
        if os.path.exists(WORK+'/queue.state.json'):return read(WORK+'/queue.state.json')
        assert os.path.isfile(WORK+'/audit.json') and not os.path.exists(WORK+'/receipt.json')
        state=dict(status='queued',reason='await_existing_workload',submitted_epoch=time.time())
        write('queue.state.json',state)
        with open(WORK+'/queue.log','ab') as log,open('/dev/null','rb') as null:
            child=subprocess.Popen([sys.executable,os.path.abspath(__file__),'queued-delete'],cwd=WORK,stdin=null,stdout=log,stderr=log,preexec_fn=os.setsid,close_fds=True)
        state['pid']=child.pid;write('queue.state.json',state);return state
    finally:lock.close()

def queued_delete():
    deadline=time.time()+7200
    while time.time()<deadline:
        result=delete()
        if result['status']=='complete':
            verified=verify();write('queue.state.json',dict(status='complete',verification=verified,completed_epoch=time.time()));return
        write('queue.state.json',dict(status='queued',pid=os.getpid(),reason=result.get('reason'),updated_epoch=time.time()))
        time.sleep(5)
    write('queue.state.json',dict(status='rejected',reason='queue_timeout',updated_epoch=time.time()))

def main(request):
    import resource
    assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
    assert os.path.realpath(HOME)==HOME and os.stat(HOME).st_uid==596
    assert os.path.realpath(WORK)==WORK and os.stat(WORK).st_uid==596
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(10)
    action=request['action']
    if action=='audit':return audit()
    if action=='delete':return delete()
    if action=='verify':return verify()
    if action=='queue':return queue()
    if action=='status':return read(WORK+'/queue.state.json') if os.path.exists(WORK+'/queue.state.json') else dict(status='not_queued')
    if action=='receipt':return read(WORK+'/receipt.json') if os.path.exists(WORK+'/receipt.json') else dict(status='not_started')
    raise ValueError(action)

if __name__=='__main__' and sys.argv[1:]==['queued-delete']:
    import resource
    assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
    assert os.path.realpath(WORK)==WORK and os.stat(WORK).st_uid==596
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(10)
    try:queued_delete()
    except Exception as e:
        write('queue.state.json',dict(status='failed',error=type(e).__name__,message=str(e)[:500],epoch=time.time()));raise
