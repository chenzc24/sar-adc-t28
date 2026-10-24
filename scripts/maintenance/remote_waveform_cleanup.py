"""Bounded remote resource audit and manifest-driven historical wave cleanup."""
import base64
import json
from pathlib import Path
import shlex
import subprocess
import hashlib
import argparse
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/remote_waveform_cleanup'
MANIFEST=ROOT/'verification/storage/2026-10-24-remote-waveform-cleanup.json'
GROUPS=('sar8_ref_gate_controls','sar8_ref_symmetric_hold')

def read(p):return json.loads(p.read_text())

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def remote(code, label, timeout=45):
    OUT.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=OUT/(stamp+'_'+label)
    encoded=base64.b64encode(code.encode()).decode()
    command='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+encoded+"'))")
    args=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',
          '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei',command]
    with target.with_suffix('.stdout').open('wb') as out,target.with_suffix('.stderr').open('wb') as err:
        try:rc=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=timeout).returncode
        except subprocess.TimeoutExpired:rc=124
    target.with_suffix('.json').write_text(json.dumps(dict(utc=stamp,returncode=rc,label=label),indent=2)+'\n')
    print('RESULT',rc,target,flush=True)
    print(target.with_suffix('.stdout').read_text(errors='replace')[-16000:],flush=True)
    if rc:print(target.with_suffix('.stderr').read_text(errors='replace')[-1500:],flush=True)
    return rc,target

DIAG=r'''from __future__ import print_function
import os,subprocess,json
print('HOST',subprocess.check_output(['hostname']).decode().strip())
print('MEMINFO',open('/proc/meminfo').read())
for args in [['df','-Pk','/tmp','/home/chenzc_intern25/TSMC28/llm_IO'],['ps','-u','chenzc_intern25','-o','pid,ppid,stat,etime,pcpu,rss,comm','--sort=-rss']]:
 print('COMMAND',args);print('\n'.join(subprocess.check_output(args).decode().splitlines()[:22]))
print('RELEVANT_MOUNTS','\n'.join(x for x in open('/proc/mounts') if x.split()[1] in ['/','/tmp','/home/chenzc_intern25']))
'''

def candidates():
    rows=[]
    for group in GROUPS:
        for launch in sorted((ROOT/'output'/group).glob('*/launch.json')):
            folder=launch.parent
            receipt=read(folder/'reduced_receipt.json')
            report=read(ROOT/'verification'/group/(folder.name+'.json'))
            ctx=read(folder/'context.json')
            assert receipt['native_exit']==receipt['reduction_exit']==0
            retained=folder/'reduced/reduced.json.gz'
            assert digest(retained)==receipt['compressed_sha256']
            assert 'spectre completes with 0 errors' in (folder/'reduced/spectre.out').read_text()
            assert 'PASS' in (folder/'reduced/logStatus').read_text()
            assert digest(folder/'test.scs')==ctx['deck_sha256']
            dest=read(launch)['remote']
            expected='/home/chenzc_intern25/TSMC28/llm_IO/'+group+'_20261024/'+folder.name
            assert dest==expected
            rows.append(dict(case=folder.name,group=group,remote=dest,
                path=dest+'/test.raw/tran_perf.tran.tran',
                native_bytes=report['native_psf_bytes'],native_sha256_recorded=report['native_psf_sha256'],
                deck_sha256=ctx['deck_sha256'],retained_local=str(retained.relative_to(ROOT)),
                retained_sha256=receipt['compressed_sha256']))
    assert len(rows)==14
    return rows

AUDIT=r'''
from __future__ import print_function
import os,json,stat,hashlib,sys
rows=PAYLOAD
apply=APPLY
assert os.getuid()==596
protected='/home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024'
allowed=['/home/chenzc_intern25/TSMC28/llm_IO/'+g+'_20261024/' for g in ['sar8_ref_gate_controls','sar8_ref_symmetric_hold']]
def smallread(p):
 with open(p) as f:return f.read()
def active_refs():
 refs=[];fail=[];excluded=[]
 for pid in os.listdir('/proc'):
  if not pid.isdigit():continue
  base='/proc/'+pid
  try:
   if os.stat(base).st_uid!=596:continue
   cmd=smallread(base+'/cmdline').replace('\x00',' ')
   status=smallread(base+'/status')
   comm=smallread(base+'/comm').strip()
   state=next(x for x in status.splitlines() if x.startswith('State:'))
   if any(row['remote'] in cmd for row in rows):refs.append(dict(pid=int(pid),reason='case command line'))
   # Zombies have no descriptors; sshd is the privileged session transport,
   # not a simulator or reducer. Record these exclusions without touching them.
   if 'Z (zombie)' in state or comm=='sshd':
    excluded.append(dict(pid=int(pid),comm=comm,state=state));continue
   links=[]
   for n in ['cwd']:
    try:links.append(os.readlink(base+'/'+n))
    except OSError:pass
   for fd in os.listdir(base+'/fd'):
    try:links.append(os.readlink(base+'/fd/'+fd))
    except OSError:pass
   try:maps=smallread(base+'/maps')
   except IOError:maps=''
   for row in rows:
    if row['remote'] in cmd or row['path'] in maps or any(x==row['remote'] or x.startswith(row['remote']+'/') for x in links):
     refs.append(dict(pid=int(pid),case=row['case']))
  except OSError as e:
   if os.path.exists(base) and e.errno not in (2,3):fail.append([pid,str(e)])
 return refs,fail,excluded
refs,fail,excluded=active_refs()
assert not refs and not fail,(refs,fail)
files=[]
for row in rows:
 p=row['path'];root=row['remote']
 assert any(root.startswith(a) and '/' not in root[len(a):] for a in allowed)
 assert p==root+'/test.raw/tran_perf.tran.tran' and not p.startswith(protected)
 assert os.path.realpath(p)==p and not os.path.islink(p)
 s=os.lstat(p)
 assert stat.S_ISREG(s.st_mode) and s.st_uid==596 and s.st_nlink==1
 assert s.st_size==row['native_bytes']
 assert smallread(root+'/exit_code').strip()=='0'
 assert smallread(root+'/reduce_exit').strip()=='0'
 assert 'PASS' in smallread(root+'/test.raw/logStatus')
 with open(root+'/test.scs','rb') as f:h=hashlib.sha256(f.read()).hexdigest()
 assert h==row['deck_sha256']
 files.append(dict(path=p,size=s.st_size,allocated=s.st_blocks*512,inode=s.st_ino,device=s.st_dev,mtime=s.st_mtime))
before=os.statvfs(rows[0]['remote'])
if apply:
 refs,fail,excluded=active_refs();assert not refs and not fail,(refs,fail)
 for item,row in zip(files,rows):
  prior=row['audit'];assert all(item[k]==prior[k] for k in ['path','size','allocated','inode','device','mtime'])
 for item in files:
  s=os.lstat(item['path'])
  assert (s.st_ino,s.st_dev,s.st_size,s.st_mtime)==(item['inode'],item['device'],item['size'],item['mtime'])
  os.unlink(item['path'])
  assert not os.path.lexists(item['path'])
  print('DELETED',json.dumps(item));sys.stdout.flush()
after=os.statvfs(rows[0]['remote'])
print(json.dumps(dict(applied=apply,files=files,allocated_bytes=sum(x['allocated'] for x in files),
 apparent_bytes=sum(x['size'] for x in files),available_before=before.f_bavail*before.f_frsize,
 available_after=after.f_bavail*after.f_frsize,active_refs=refs,active_check_failures=fail,
 transport_or_zombie_exclusions=excluded)))
'''

def inventory():
    assert not MANIFEST.exists(),'Inspect existing manifest; do not overwrite audit'
    rows=candidates()
    payload=[{k:r[k] for k in ['case','remote','path','native_bytes','deck_sha256']} for r in rows]
    code=AUDIT.replace('PAYLOAD',repr(payload)).replace('APPLY','False')
    rc,target=remote(code,'audit')
    assert rc==0
    result=json.loads(target.with_suffix('.stdout').read_text().splitlines()[-1])
    for row,item in zip(rows,result['files']):
        assert row['path']==item['path'];row['audit']=item
    MANIFEST.write_text(json.dumps(dict(status='audited_not_deleted',rows=rows,remote_audit=result,
        recoverability='Native full waveform removed permanently only on apply. Local reduced waveforms/stress summaries and reproducible source decks remain; not a full raw backup.'),indent=2)+'\n')
    print('AUDITED',len(rows),'GiB',result['allocated_bytes']/2**30)

def apply():
    manifest=read(MANIFEST)
    assert manifest['status']=='audited_not_deleted'
    rows=manifest['rows']
    for row in rows:assert digest(ROOT/row['retained_local'])==row['retained_sha256']
    payload=[{k:r[k] for k in ['case','remote','path','native_bytes','deck_sha256','audit']} for r in rows]
    rc,target=remote(AUDIT.replace('PAYLOAD',repr(payload)).replace('APPLY','True'),'delete')
    # Never auto-retry uncertain deletion; preserve every per-file receipt.
    assert rc==0,'Inspect exact per-file DELETED receipts before any retry'
    result=json.loads(target.with_suffix('.stdout').read_text().splitlines()[-1])
    assert result['applied'] and len(result['files'])==len(rows)
    manifest.update(status='deleted_verified',deletion=result,receipt=str(target.relative_to(ROOT))+'.stdout')
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    print('DELETED_GIB',result['allocated_bytes']/2**30)

def verify():
    manifest=read(MANIFEST);assert manifest['status']=='deleted_verified'
    paths=[r['path'] for r in manifest['rows']]
    code='''from __future__ import print_function
import os,json
paths=PATHS
assert all(not os.path.lexists(p) for p in paths)
retained=['test.scs','spectre.out','test.raw/logStatus','reduced.json.gz']
for p in paths:
 root=p.rsplit('/test.raw/',1)[0]
 assert all(os.path.isfile(root+'/'+f) for f in retained)
root='/home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024'
current=[]
for n in ['rg1_strict200_ff_m40','rg4_strict200_ff_m40','rg1_strict200_ff_125','rg4_strict200_ff_125']:
 p=root+'/'+n;raw=p+'/test.raw/tran_perf.tran.tran'
 current.append(dict(name=n,exit=open(p+'/exit_code').read().strip() if os.path.isfile(p+'/exit_code') else None,
 raw_exists=os.path.isfile(raw),raw_bytes=os.path.getsize(raw) if os.path.isfile(raw) else None))
mem={s.split(':')[0]:s.split(':')[1].strip() for s in open('/proc/meminfo')}
st=os.statvfs(root)
print(json.dumps(dict(deleted_paths_absent=True,retained_analysis_files_present=True,current_cases=current,
 meminfo={k:mem[k] for k in ['MemAvailable','SwapFree','Cached','AnonPages']},
 filesystem_available_bytes=st.f_bavail*st.f_frsize)))
'''.replace('PATHS',repr(paths))
    rc,target=remote(code,'verify');assert rc==0
    result=json.loads(target.with_suffix('.stdout').read_text())
    manifest['post_verify']=result
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['resources','audit','apply','verify'],nargs='?',default='resources')
    action=parser.parse_args().action
    if action=='resources':raise SystemExit(remote(DIAG,'resources')[0])
    elif action=='audit':inventory()
    elif action=='apply':apply()
    else:verify()
