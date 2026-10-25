"""Explicit cleanup phases. Windows deletion is only in the native PowerShell tool."""
import argparse,base64,hashlib,json,os,shlex,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'verification/storage/2026-10-25-approved-cleanup'
OUT=ROOT/'output/project_management/approved_cleanup'
SOURCE='management/cleanup/2026-10-25/review_manifest.json'
WORK='/server_local_ssd/chenzc_intern25/sar-adc-t28/maintenance/cleanup-20261025-c802f73'
IDS=['L-A1','L-B1','L-B2','S-A1','S-A2']

def load(p):
    with Path(p).open(encoding='utf-8-sig') as f:return json.load(f)

def save(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def prepare():
    original=subprocess.check_output(['git','show','c802f73:'+SOURCE],cwd=ROOT)
    d=json.loads(original);assert d==load(ROOT/SOURCE),'Reviewed source modified'
    assert sorted(p['id'] for p in d['proposals'])==IDS
    local=[];remote=[];retained=set()
    for row in d['proposals']:
        assert not row['delete_entire_experiment_directory'] and row['file_count']==len(row['files'])
        for f in row['files']:(local if row['side']=='local' else remote).append(dict(f,proposal=row['id']))
        retained.update(row['required_retained_paths'])
    assert len(local)==21 and len(remote)==15 and len(retained)==10
    assert not {f['path'] for f in remote}&retained
    historical=load(ROOT/'output/sar8_r4_staged/msb_4600/recovery_manifest.json')
    spec=dict(review_sha256=hashlib.sha256(original).hexdigest(),review_source=SOURCE,approved_ids=IDS,
        local_targets=local,remote_targets=remote,retained_paths=sorted(retained),
        historical_parts={r['name']:r['sha256'] for r in historical['parts']},
        historical_compressed_sha256=historical['compressed_sha256'],historical_native_sha256=historical['native_sha256'],
        authorization='User directly approved all five listed duplicate-removal proposals; home inspection only, no home deletion')
    target=DEST/'input.json'
    if target.exists():assert load(target)==spec,'Existing execution input differs'
    else:save(target,spec)
    auth=DEST/'authorization.json'
    if not auth.exists():save(auth,dict(approved_at_utc=now(),user_request='全都处理即可，还有我看到非常多的文件罗列在我的服务器/home,你也查看一下。',
        approved_ids=IDS,review_commit='c802f73',review_sha256=spec['review_sha256'],file_count=36,
        home_scope='read-only metadata, no unknown home file deletion',protected_data_unchanged=True))
    print('AUTHORIZED_INPUT_READY',spec['review_sha256'],len(local),len(remote))

def rpc(request,timeout=45):
    OUT.mkdir(parents=True,exist_ok=True);stamp=str(time.time_ns())
    helper=(ROOT/'scripts/management/cleanup_execute_remote.py').read_bytes()
    policy=(ROOT/'scripts/management/remote_agent.py').read_bytes();spec=(DEST/'input.json').read_bytes()
    files=[dict(name='cleanup_'+hashlib.sha256(helper).hexdigest()+'.py',sha256=hashlib.sha256(helper).hexdigest(),base64=base64.b64encode(helper).decode()),
        dict(name='policy_agent.py',sha256=hashlib.sha256(policy).hexdigest(),base64=base64.b64encode(policy).decode()),
        dict(name='input.json',sha256=hashlib.sha256(spec).hexdigest(),base64=base64.b64encode(spec).decode())]
    inp=OUT/(stamp+'.input.json');save(inp,dict(files=files,request=request))
    bootstrap=r'''import os,sys,json,base64,hashlib,socket
assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
root='/server_local_ssd/chenzc_intern25/sar-adc-t28';assert os.path.realpath(root)==root and os.stat(root).st_uid==596
for p in [root+'/maintenance',root+'/maintenance/cleanup-20261025-c802f73']:
 if not os.path.exists(p):os.mkdir(p,0o700)
 assert os.path.realpath(p)==p and os.stat(p).st_uid==596
work=p;os.chdir(work)
import resource
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
payload=json.load(sys.stdin)
for item in payload['files']:
 blob=base64.b64decode(item['base64']);assert hashlib.sha256(blob).hexdigest()==item['sha256']
 path=work+'/'+item['name']
 if not os.path.exists(path):
  fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
  with os.fdopen(fd,'wb') as f:f.write(blob)
 existing=open(path,'rb').read()
 if item['name']=='input.json':assert json.loads(existing)==json.loads(blob)
 else:assert existing.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n')
path=work+'/'+payload['files'][0]['name'];sys.path.insert(0,work)
scope={'__name__':'cleanup_rpc','__file__':path};exec(compile(base64.b64decode(payload['files'][0]['base64']),path,'exec'),scope)
print(json.dumps(scope['main'](payload['request'])))
'''
    cmd='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(bootstrap.encode()).decode()+"'))")
    out=OUT/(stamp+'.output.json');err=OUT/(stamp+'.stderr')
    with inp.open('rb') as i,out.open('wb') as o,err.open('wb') as e:
        try:rc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',cmd],stdin=i,stdout=o,stderr=e,timeout=timeout).returncode
        except subprocess.TimeoutExpired:rc=124
    if rc:raise RuntimeError(f'Remote outcome uncertain (exit {rc}); inspect {out}; reconcile before retry: '+err.read_text(errors='replace')[-1500:])
    result=load(out)
    if request['action']=='home':save(DEST/'home_inventory.json',dict(result,received_at_utc=now()))
    elif request['action']=='home-cache-sizes':save(DEST/'home_cache_sizes.json',dict(result,received_at_utc=now()))
    elif request['action']=='fetch':save(DEST/request['name'],result)
    elif request['action']=='delete':save(DEST/'remote_receipt.json',result)
    elif request['action']=='verify-retained':save(DEST/'retained_check.json',dict(result,received_at_utc=now()))
    elif request['action']=='final-check':save(DEST/'remote_final_check.json',dict(result,received_at_utc=now()))
    else:save(OUT/(request['action']+'.json'),result)
    return result

def reconcile():
    spec=load(DEST/'input.json');remote=load(DEST/'remote_validation.json');local=load(DEST/'local_validation.json')
    assert remote['status']=='validated' and local['status']=='validated' and remote['review_sha256']==spec['review_sha256']==local['review_sha256']
    local_by={r['path'].replace('\\','/'):r for r in local['files']};pairs=[]
    for row in spec['local_targets']:
        r=local_by[row['path']]
        if row['category']=='native_waveform':
            native=remote['files'][row['remote_counterpart']]
            assert r['sha256']==native['sha256'] and row['bytes']==native['bytes'],'Native content mismatch'
            pairs.append(dict(local_path=row['path'],remote_path=row['remote_counterpart'],local_sha256=r['sha256'],bytes=row['bytes']))
        else:assert r['sha256']==spec['historical_parts'][Path(row['path']).name]
    assert len(pairs)==10
    result=dict(status='reconciled',review_sha256=spec['review_sha256'],pairs=pairs,at_utc=now(),local_file_count=21,remote_file_count=15)
    save(DEST/'reconciliation.json',result);return result

def local_fingerprint(path):
    p=Path(path);allowed=[ROOT/'output/sar8_r4_staged',ROOT/'output/sar8_r4_idle']
    resolved=p.resolve();assert any(resolved.is_relative_to(a.resolve()) and resolved!=a.resolve() for a in allowed)
    assert p.is_file() and not p.is_symlink()
    for parent in [p,*p.parents]:
        if hasattr(parent,'is_junction'):assert not parent.is_junction()
    s=p.stat();assert s.st_nlink==1
    return dict(path=p.as_posix(),bytes=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,inode=s.st_ino,device=s.st_dev,nlink=s.st_nlink)

def summarize():
    spec=load(DEST/'input.json');l=load(DEST/'local_receipt.json');r=load(DEST/'remote_receipt.json')
    final=load(DEST/'remote_final_check.json');home=load(DEST/'home_inventory.json');cache=load(DEST/'home_cache_sizes.json')
    assert l['status']==r['status']=='complete' and final['status']=='verified'
    assert len(l['files'])==21 and len(r['files'])==15 and final['retained_count']==10
    assert all(f['status']=='deleted_verified' for f in l['files']+r['files'])
    assert all(not os.path.lexists(f['path']) for f in spec['local_targets'])
    assert {f['path'] for f in r['files']}==set(final['absent_paths'])
    proposals=[]
    for pid in IDS:
        rows=[f for f in spec['local_targets']+spec['remote_targets'] if f['proposal']==pid]
        proposals.append(dict(id=pid,files=len(rows),bytes=sum(f['bytes'] for f in rows)))
    result=dict(status='complete',checked_at_utc=now(),review_sha256=spec['review_sha256'],proposals=proposals,
        local=dict(deleted_files=21,deleted_bytes=int(l['deleted_bytes']),free_before=l['free_before'],free_after=l['free_after'],free_change=l['free_after']-l['free_before']),
        server=dict(deleted_files=15,deleted_bytes=r['deleted_bytes'],deleted_allocated_bytes=r['deleted_allocated_bytes'],retained_native_count=10,
            free_change=r['free_after'][0]['available_bytes']-r['free_before'][0]['available_bytes']),
        home=dict(entries=len(home['entries']),directories=sum(f['type']=='directory' for f in home['entries']),regular_files=sum(f['type']=='file' for f in home['entries']),
            regular_file_bytes=home['total_regular_file_bytes'],compile_cache_directories=len(cache['cache_directories']),compile_cache_bytes=cache['total_bytes'],deleted_files=0),
        permanent=True,recovery='Download preserved server-native PSFs; regenerate transfer archives/parts if needed',oa_mutations=0)
    save(DEST/'summary.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','home','home-cache-sizes','launch','status','fetch','reconcile','remote-delete','verify-retained','final-check','summarize','local-fingerprint']);p.add_argument('name',nargs='?')
    a=p.parse_args()
    if a.action=='prepare':return prepare()
    if a.action=='local-fingerprint':result=local_fingerprint(a.name)
    elif a.action=='summarize':result=summarize()
    elif a.action=='reconcile':result=reconcile()
    elif a.action=='remote-delete':
        reconciled=load(DEST/'reconciliation.json');result=rpc(dict(action='delete',review_sha256=reconciled['review_sha256'],pairs=reconciled['pairs']))
    else:result=rpc(dict(action=a.action,name=a.name))
    if a.action=='home':print(json.dumps(dict(home=result['home'],entries=len(result['entries']),regular_file_bytes=result['total_regular_file_bytes'],directories_sized=False),indent=2))
    elif a.action=='home-cache-sizes':print(json.dumps(dict(cache_directories=len(result['cache_directories']),bytes=result['total_bytes'],incomplete=sum(not r['complete'] for r in result['cache_directories']),odd_directories=result['odd_literal_directories']),indent=2))
    elif a.action=='fetch':print('FETCHED',a.name)
    else:print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
