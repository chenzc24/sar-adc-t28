"""Frozen home-cache allowlist and bounded SSH transport; no local deletion."""
import argparse,base64,hashlib,json,shlex,shutil,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'verification/storage/2026-10-25-home-cache-cleanup'
OUT=ROOT/'output/project_management/home_cache_cleanup'
WORK='/server_local_ssd/chenzc_intern25/sar-adc-t28/maintenance/home-cache-20261025'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def prepare():
    previous=ROOT/'verification/storage/2026-10-25-approved-cleanup/home_cache_sizes.json'
    names=sorted(Path(r['path']).name for r in read(previous)['cache_directories'])
    paths=subprocess.check_output(['rg','--files','--hidden','--no-ignore','output','netlist','--glob','*.scs','--glob','!**/.venv/**','--glob','!**/transport/**'],cwd=ROOT).decode('utf-8').splitlines()
    sources={}
    for path in paths:sources.setdefault(Path(path).stem,[]).append(path.replace('\\','/'))
    spec=dict(home='/home/chenzc_intern25',authorization='delete_old_unused_home_compile_caches',
        user_request='看起来差不多管理好了，那我们删一下旧的无用的编译产物，太dirty了',
        source_snapshot_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
        caches=[dict(name=name,project_sources=sorted(sources.get(name[:-10],[]))) for name in names])
    path=DEST/'input.json'
    if path.exists():assert read(path)==spec,'Frozen allowlist already exists; reconcile'
    else:save(path,spec)
    return dict(status='prepared',caches=len(names),project_basename_matches=sum(bool(r['project_sources']) for r in spec['caches']))

def curate_audit(result):
    if 'tree' not in next(iter(result.get('rows',[])),{}):return result
    full=OUT/'audit_full.json';save(full,result)
    concise={k:v for k,v in result.items() if k!='rows'};concise['rows']=[]
    for row in result['rows']:
        item={k:v for k,v in row.items() if k!='tree'}
        if 'tree' in row:
            item['tree_summary']={k:v for k,v in row['tree'].items() if k!='entries'}
            item['tree_summary']['entries']=len(row['tree']['entries'])
        concise['rows'].append(item)
    concise['full_metadata_snapshot']=str(full.relative_to(ROOT)).replace('\\','/')
    concise['full_metadata_sha256']=hashlib.sha256(full.read_bytes()).hexdigest()
    concise['server_authoritative_audit']=WORK+'/audit.json'
    save(DEST/'audit.json',concise);return concise

def rpc(action):
    OUT.mkdir(parents=True,exist_ok=True);stamp=str(time.time_ns())
    helper=(ROOT/'scripts/management/home_cache_cleanup_remote.py').read_bytes()
    payload=dict(action=action,helper=base64.b64encode(helper).decode(),input=base64.b64encode((DEST/'input.json').read_bytes()).decode())
    incoming=OUT/(stamp+'.input.json');save(incoming,payload)
    bootstrap='''import os,sys,json,base64,hashlib,socket,resource
assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
root='/server_local_ssd/chenzc_intern25/sar-adc-t28';assert os.path.realpath(root)==root and os.stat(root).st_uid==596
work=root+'/maintenance/home-cache-20261025'
assert os.path.realpath(root+'/maintenance')==root+'/maintenance' and os.stat(root+'/maintenance').st_uid==596
if not os.path.exists(work):os.mkdir(work,0o700)
assert os.path.realpath(work)==work and os.stat(work).st_uid==596
os.chdir(work);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
request=json.load(sys.stdin);blob=base64.b64decode(request['helper']);source=base64.b64decode(request['input'])
for name,data in [('helper_'+hashlib.sha256(blob).hexdigest()+'.py',blob),('input.json',source)]:
 path=work+'/'+name
 if not os.path.exists(path):
  fd=os.open(path,os.O_WRONLY|os.O_EXCL|os.O_CREAT,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data)
 existing=open(path,'rb').read()
 if name=='input.json':assert json.loads(existing)==json.loads(data)
 else:assert existing.replace(b'\\r\\n',b'\\n')==data.replace(b'\\r\\n',b'\\n')
helper_path=work+'/helper_'+hashlib.sha256(blob).hexdigest()+'.py'
scope={'__name__':'cache_cleanup','__file__':helper_path};exec(compile(blob,helper_path,'exec'),scope)
print(json.dumps(scope['main'](request)))
'''
    command='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(bootstrap.encode()).decode()+"'))")
    output=OUT/(stamp+'.output.json');error=OUT/(stamp+'.stderr')
    with incoming.open('rb') as inp,output.open('wb') as out,error.open('wb') as err:
        try:rc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',command],stdin=inp,stdout=out,stderr=err,timeout=110).returncode
        except subprocess.TimeoutExpired:rc=124
    if rc:raise RuntimeError('Uncertain outcome; inspect receipt before retry: '+str(output)+' '+error.read_text(errors='replace')[-1000:])
    result=read(output);result['received_at_utc']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    # A deferred attempt must not replace the authoritative deletion receipt.
    name='deferred.json' if result['status']=='deferred' else action+'.json'
    if action=='audit' and (DEST/name).exists():
        old=(DEST/name).read_bytes();archive=OUT/('audit_'+hashlib.sha256(old).hexdigest()[:16]+'.json')
        if not archive.exists():shutil.copyfile(DEST/name,archive)
    if action=='audit':curate_audit(result)
    else:save(DEST/name,result)
    return result

def collect():
    state=rpc('status');audit=read(DEST/'audit.json');targets=[r for r in audit['rows'] if r['eligible']]
    result=dict(status=state['status'],observed_at_utc=state['received_at_utc'],
        queued_worker=state,eligible_directories=len(targets),eligible_files=sum(r['tree_summary']['file_count'] for r in targets),
        eligible_bytes=sum(r['tree_summary']['bytes'] for r in targets),
        retained=[dict(name=r['name'],reasons=r['reasons']) for r in audit['rows'] if not r['eligible']],
        server_work_directory=WORK,permanent_removal=True,recovery='Recompile from preserved project sources',
        actual_deletion_verified=False)
    if state['status']=='complete':
        receipt=rpc('receipt');verification=rpc('verify')
        assert receipt['status']=='complete' and verification['status']=='verified'
        result.update(actual_deletion_verified=True,deleted_directories=len(receipt['deleted']),
            deleted_bytes=receipt['deleted_bytes'],deleted_allocated_bytes=receipt['deleted_allocated_bytes'],
            observed_free_change=receipt['free_after']-receipt['free_before'])
    save(DEST/'summary.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','audit','curate-audit','delete','verify','receipt','queue','status','collect']);a=p.parse_args()
    result=(prepare() if a.action=='prepare' else collect() if a.action=='collect' else curate_audit(read(DEST/'audit.json'))
        if a.action=='curate-audit' else rpc(a.action))
    if a.action in ['audit','curate-audit'] and 'rows' in result:
        from collections import Counter
        print(json.dumps(dict(status=result['status'],eligible=sum(r['eligible'] for r in result['rows']),retained_reasons=dict(Counter(s for r in result['rows'] for s in r['reasons'])),processes=result['processes']),indent=2))
    elif result['status']=='complete' and 'deleted' in result:
        print(json.dumps({k:v for k,v in result.items() if k!='deleted'},ensure_ascii=False,indent=2));print('DELETED',len(result['deleted']))
    else:print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
