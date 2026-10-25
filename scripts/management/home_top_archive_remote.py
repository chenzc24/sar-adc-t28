"""Python2/3 bounded, reversible, no-overwrite archive of inactive home files."""
from __future__ import print_function
import hashlib,json,os,re,socket,stat,time

HOME='/home/chenzc_intern25'
WORK='/server_local_ssd/chenzc_intern25/sar-adc-t28/maintenance/home-top-20261025'
ARCHIVE=HOME+'/archive/home-top-2026-10-25'
UID=596

def read(path):
    with open(path) as f:return json.load(f)

def save(path,value):
    temporary=path+'.tmp.'+str(os.getpid())
    with open(temporary,'w') as f:
        json.dump(value,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    os.rename(temporary,path)

def category(name):
    if re.match(r'^(?:CDS(?:_[A-Za-z0-9_-]+)?\.log|libManager\.log|cdsLibEditor\.log)(?:\.\d+)?\Z',name) or name in ['calibre_drc.log','spectre.out']:return 'logs'
    if re.match(r'^[A-Za-z0-9_+.-]+\.scs\.(?:tran|tran_perf)\.srf\Z',name):return 'simulation'
    return None

def fingerprint(path):
    s=os.lstat(path)
    return dict(device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mtime=s.st_mtime,ctime=s.st_ctime,
        uid=s.st_uid,nlink=s.st_nlink,mode=s.st_mode)

def literal(name):
    assert name and '/' not in name and '\\' not in name and category(name),'Unapproved filename'
    path=HOME+'/'+name;assert os.path.realpath(path)==path,'Symlink path'
    s=fingerprint(path)
    assert stat.S_ISREG(s['mode']) and s['uid']==UID and s['nlink']==1,'Not an exclusive owned regular file'
    return path,s

def locks(path):return [p for p in [path+'.cdslck',path+'.lock'] if os.path.lexists(p)]

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def metadata():
    result=[]
    for name in sorted(os.listdir(HOME)):
        s=fingerprint(HOME+'/'+name)
        kind='directory' if stat.S_ISDIR(s['mode']) else 'file' if stat.S_ISREG(s['mode']) else 'other'
        result.append(dict(name=name,type=kind,hidden=name.startswith('.'),fingerprint=s))
    return result

def process_uses(names):
    paths={name:HOME+'/'+name for name in names};uses={};unknown=[];excluded=[]
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid)==os.getpid():continue
        base='/proc/'+pid
        try:
            if os.stat(base).st_uid!=UID:continue
            with open(base+'/comm') as f:comm=f.read().strip()
            with open(base+'/stat') as f:state=f.read().rsplit(')',1)[1].split()[0]
            with open(base+'/cmdline','rb') as f:cmd=f.read(65536).replace(b'\x00',b' ').decode('utf-8','replace')
            if state=='Z' or (comm=='sshd' and re.match(r'^sshd: chenzc_intern25(?:@|\s|\[|$)',cmd)):
                excluded.append(dict(pid=int(pid),comm=comm));continue
            cwd=os.readlink(base+'/cwd');texts=[cmd,cwd,os.readlink(base+'/exe')]
            with open(base+'/maps') as f:
                maps=f.read(4*1024**2+1);assert len(maps)<=4*1024**2;texts.append(maps)
            fds=os.listdir(base+'/fd');assert len(fds)<=8192
            for fd in fds:
                try:texts.append(os.readlink(base+'/fd/'+fd))
                except OSError as e:
                    if e.errno!=2:raise
            text='\n'.join(texts)
            for name,path in paths.items():
                exact=re.search(re.escape(path)+r'''(?=$|[\s'"\x00])''',text)
                relative=(cwd==HOME and re.search(r'(?<![A-Za-z0-9_.+-])'+re.escape(name)+r'(?![A-Za-z0-9_.+-])',cmd))
                if exact or relative:uses.setdefault(name,[]).append(dict(pid=int(pid),comm=comm))
        except (IOError,OSError,AssertionError) as e:
            if os.path.exists(base):unknown.append(dict(pid=int(pid),error=type(e).__name__))
    return dict(uses=uses,uncertain=unknown,excluded_non_simulation=excluded)

def audit():
    if os.path.exists(WORK+'/audit.json'):return read(WORK+'/audit.json')
    before=metadata();names=[r['name'] for r in before if not r['hidden'] and category(r['name'])]
    proc=process_uses(names);rows=[];total=0
    for name in names:
        row=dict(name=name,source=HOME+'/'+name,category=category(name),reasons=[])
        if name in proc['uses']:row['reasons'].append('active_process_reference');row['open_by']=proc['uses'][name]
        if proc['uncertain']:row['reasons'].append('process_audit_uncertain')
        if locks(row['source']):row['reasons'].append('lock_sidecar_present')
        try:
            path,s=literal(name);row['fingerprint']=s
            if time.time()-s['mtime']<3600:row['reasons'].append('modified_within_one_hour')
        except (IOError,OSError,AssertionError):row['reasons'].append('unsafe_path_type_owner_or_link')
        rows.append(row)
    time.sleep(2)
    again=process_uses(names)
    for row in rows:
        if row['name'] in again['uses']:row['reasons'].append('active_process_reference')
        if again['uncertain']:row['reasons'].append('process_audit_uncertain')
        if 'fingerprint' in row and fingerprint(row['source'])!=row['fingerprint']:row['reasons'].append('changed_during_observation')
        row['reasons']=sorted(set(row['reasons']));row['eligible']=not row['reasons']
        if row['eligible']:
            total+=row['fingerprint']['bytes']
            assert total<=32*1024**2,'Small-file archive budget exceeded before hashing'
            row['sha256']=digest(row['source']);assert fingerprint(row['source'])==row['fingerprint']
    assert total<=32*1024**2,'Small-file archive budget exceeded'
    result=dict(status='audited',home=HOME,destination=ARCHIVE,epoch=time.time(),before=before,candidates=rows,processes=again)
    save(WORK+'/audit.json',result);return result

def owned_directory(path):
    assert path.startswith(HOME+'/archive') and os.path.realpath(path)==path
    s=os.lstat(path);assert stat.S_ISDIR(s.st_mode) and s.st_uid==UID

def create_destination():
    parent=HOME+'/archive'
    if not os.path.exists(parent):os.mkdir(parent,0o700)
    owned_directory(parent)
    assert not os.path.lexists(ARCHIVE),'Dedicated archive batch already exists; reconcile, never merge blindly'
    os.mkdir(ARCHIVE,0o700);owned_directory(ARCHIVE)
    for group in ['logs','simulation']:os.mkdir(ARCHIVE+'/'+group,0o700);owned_directory(ARCHIVE+'/'+group)
    assert os.stat(ARCHIVE).st_dev==os.stat(HOME).st_dev,'Cross-filesystem archive refused'

def validate_row(row):
    path,s=literal(row['name']);assert path==row['source'] and s==row['fingerprint'],'Source changed after audit'
    assert not locks(path),'Lock appeared'
    assert digest(path)==row['sha256'] and fingerprint(path)==s,'Source content changed'

def hardlink_move(row,target):
    validate_row(row);assert not os.path.lexists(target),'Archive destination collision'
    assert os.path.dirname(target)==ARCHIVE+'/'+row['category'] and os.path.realpath(target)==target
    os.link(row['source'],target)  # Atomic fail-if-exists; never overwrite.
    original=row['fingerprint'];current=fingerprint(row['source'])
    assert current['nlink']==2 and fingerprint(target)==current
    for key in ['device','inode','bytes','mtime','uid','mode']:assert current[key]==original[key]
    assert digest(target)==row['sha256'] and not locks(row['source'])
    live=process_uses([row['name']]);assert not live['uncertain'] and row['name'] not in live['uses'],'File became active; preserve both names and reconcile'
    os.unlink(row['source'])  # Verified archived hardlink remains throughout.
    assert not os.path.lexists(row['source']) and fingerprint(target)['nlink']==1
    assert digest(target)==row['sha256']

def archive():
    import fcntl
    lock=open(WORK+'/archive.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        if os.path.isfile(WORK+'/receipt.json'):
            prior=read(WORK+'/receipt.json');assert prior['status']=='complete','Partial prior archive: reconcile journal, never replay'
            return prior
        source=read(WORK+'/audit.json');selected=[];kept=[]
        live=process_uses([r['name'] for r in source['candidates']]);assert not live['uncertain'],'Uncertain process audit'
        for row in source['candidates']:
            if not row['eligible']:kept.append(dict(name=row['name'],reasons=row['reasons']));continue
            try:
                assert row['name'] not in live['uses'];validate_row(row);selected.append(row)
            except (AssertionError,IOError,OSError):kept.append(dict(name=row['name'],reasons=['changed_or_active_after_audit']))
        assert selected,'No confirmed inactive files; no archive created'
        create_destination()
        receipt=dict(status='archiving',archive=ARCHIVE,started_epoch=time.time(),moved=[],retained=kept,no_data_deleted=True)
        save(WORK+'/receipt.json',receipt);deadline=time.time()+60
        for row in selected:
            assert time.time()<deadline,'Archive time bound'
            target=ARCHIVE+'/'+row['category']+'/'+row['name']
            entry=dict(name=row['name'],source=row['source'],destination=target,bytes=row['fingerprint']['bytes'],sha256=row['sha256'],source_fingerprint=row['fingerprint'],status='intent')
            receipt['moved'].append(entry);save(WORK+'/receipt.json',receipt)
            hardlink_move(row,target);entry['status']='archived_verified';entry['archive_fingerprint']=fingerprint(target)
            save(WORK+'/receipt.json',receipt)
        receipt.update(status='complete',completed_epoch=time.time(),archived_bytes=sum(r['bytes'] for r in receipt['moved']))
        save(ARCHIVE+'/manifest.json',receipt);save(WORK+'/receipt.json',receipt);return receipt
    finally:lock.close()

def verify():
    receipt=read(WORK+'/receipt.json');assert receipt['status']=='complete'
    assert read(ARCHIVE+'/manifest.json')==receipt,'Archive manifest does not match operation journal'
    for row in receipt['moved']:
        assert not os.path.lexists(row['source']) and digest(row['destination'])==row['sha256']
        assert fingerprint(row['destination'])==row['archive_fingerprint']
    before=read(WORK+'/audit.json')['before'];moved={r['name'] for r in receipt['moved']};current=metadata();after={r['name']:r for r in current};changes=[]
    for row in before:
        if row['name'] in moved:continue
        assert row['name'] in after,'Protected path disappeared: '+row['name']
        if row['fingerprint']!=after[row['name']]['fingerprint']:changes.append(dict(name=row['name'],reason='metadata_changed_by_concurrent_activity'))
    result=dict(status='verified',epoch=time.time(),home=HOME,archived_count=len(moved),archive=ARCHIVE,
        after=current,protected_metadata_changes=changes,visible_count=sum(not r['hidden'] for r in current),hidden_count=sum(r['hidden'] for r in current))
    save(WORK+'/verification.json',result);return result

def main(request):
    import resource
    assert os.getuid()==UID and socket.gethostname().split('.')[0]=='thu-wei'
    assert os.path.realpath(HOME)==HOME and os.stat(HOME).st_uid==UID
    assert os.path.realpath(WORK)==WORK and os.stat(WORK).st_uid==UID
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(10)
    if request['action']=='audit':return audit()
    if request['action']=='archive':return archive()
    if request['action']=='verify':return verify()
    if request['action']=='receipt':return read(WORK+'/receipt.json') if os.path.isfile(WORK+'/receipt.json') else dict(status='not_started')
    raise ValueError(request['action'])
