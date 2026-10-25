"""Client for home top-level archival, retaining local and remote receipts."""
import argparse,base64,hashlib,json,shlex,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'verification/storage/2026-10-25-home-top-archive'
OUT=ROOT/'output/project_management/home_top_archive'

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def rpc(action):
    OUT.mkdir(parents=True,exist_ok=True);stamp=str(time.time_ns())
    helper=(ROOT/'scripts/management/home_top_archive_remote.py').read_bytes()
    payload=dict(action=action,helper=base64.b64encode(helper).decode())
    source=OUT/(stamp+'.input.json');save(source,payload)
    bootstrap='''import os,sys,json,base64,hashlib,socket,resource
assert os.getuid()==596 and socket.gethostname().split('.')[0]=='thu-wei'
root='/server_local_ssd/chenzc_intern25/sar-adc-t28';assert os.path.realpath(root)==root and os.stat(root).st_uid==596
parent=root+'/maintenance';assert os.path.realpath(parent)==parent and os.stat(parent).st_uid==596
work=parent+'/home-top-20261025'
if not os.path.exists(work):os.mkdir(work,0o700)
assert os.path.realpath(work)==work and os.stat(work).st_uid==596
os.chdir(work);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
request=json.load(sys.stdin);blob=base64.b64decode(request['helper']);path=work+'/helper_'+hashlib.sha256(blob).hexdigest()+'.py'
if not os.path.exists(path):
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(blob)
assert open(path,'rb').read().replace(b'\\r\\n',b'\\n')==blob.replace(b'\\r\\n',b'\\n')
scope={'__name__':'home_archive','__file__':path};exec(compile(blob,path,'exec'),scope)
print(json.dumps(scope['main'](request)))
'''
    command='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(bootstrap.encode()).decode()+"'))")
    output=OUT/(stamp+'.output.json');error=OUT/(stamp+'.stderr')
    with source.open('rb') as inp,output.open('wb') as out,error.open('wb') as err:
        try:rc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',command],stdin=inp,stdout=out,stderr=err,timeout=90).returncode
        except subprocess.TimeoutExpired:rc=124
    if rc:raise RuntimeError('Outcome uncertain; inspect receipt before any retry: '+str(output)+' '+error.read_text(errors='replace')[-1500:])
    result=load(output);result['received_at_utc']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    save(DEST/(action+'.json'),result);return result

def finalize():
    receipt=load(DEST/'archive.json');verification=load(DEST/'verify.json');audit=load(DEST/'audit.json')
    assert receipt['status']=='complete' and verification['status']=='verified'
    assert all(r['status']=='archived_verified' for r in receipt['moved'])
    moved={r['name'] for r in receipt['moved']};before={r['name'] for r in audit['before']};after={r['name'] for r in verification['after']}
    assert after==(before-moved)|{'archive'}
    assert sum(r['bytes'] for r in receipt['moved'])==receipt['archived_bytes']
    visible=[r for r in verification['after'] if not r['hidden']]
    result=dict(status='complete',archive_directory=receipt['archive'],archive_manifest=receipt['archive']+'/manifest.json',
        archived_count=len(moved),archived_bytes=receipt['archived_bytes'],archived_logs=sum('/logs/' in r['destination'] for r in receipt['moved']),
        archived_simulation_artifacts=sum('/simulation/' in r['destination'] for r in receipt['moved']),
        visible_before=sum(not r['hidden'] for r in audit['before']),visible_after=len(visible),hidden_after=verification['hidden_count'],
        protected_metadata_changes=verification['protected_metadata_changes'],no_data_deleted=True,
        space_released_claim=False,remaining_visible=[dict(name=r['name'],type=r['type']) for r in visible],
        verification_received_at_utc=verification['received_at_utc'])
    save(DEST/'summary.json',result)
    lines=['Home top-level remaining list','/home/chenzc_intern25',
        'Visible entries: '+str(len(visible))+'; hidden entries preserved: '+str(verification['hidden_count']),
        'Archive: '+receipt['archive'],'','Visible entries (/ marks a directory):','']
    lines += [r['name']+('/' if r['type']=='directory' else '') for r in visible]
    (DEST/'remaining.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    registry=ROOT/'management/cleanup/2026-10-25/home_archive.json'
    save(registry,dict(status='complete',archive_directory=receipt['archive'],archived_files=len(moved),
        evidence='verification/storage/2026-10-25-home-top-archive/summary.json',
        remaining_list='verification/storage/2026-10-25-home-top-archive/remaining.txt',
        archive_manifest=receipt['archive']+'/manifest.json',no_data_deleted=True))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','archive','verify','receipt','finalize']);a=p.parse_args();r=finalize() if a.action=='finalize' else rpc(a.action)
    if a.action=='audit':
        print(json.dumps(dict(status=r['status'],visible_before=sum(not x['hidden'] for x in r['before']),
            candidates=[{k:v for k,v in x.items() if k not in ['fingerprint','sha256']} for x in r['candidates']]),ensure_ascii=False,indent=2))
    elif a.action=='verify':
        print(json.dumps(dict(status=r['status'],visible_count=r['visible_count'],hidden_count=r['hidden_count'],remaining_visible=[x['name'] for x in r['after'] if not x['hidden']],protected_metadata_changes=r['protected_metadata_changes']),ensure_ascii=False,indent=2))
    else:print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
