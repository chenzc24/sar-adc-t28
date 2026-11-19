"""Deploy owned runtime inputs under the existing physical lock; never submit jobs."""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
from Layout.project import ROOT,config

def sar_qualification_files():
    from Layout.design.sar_reference import source_cdl
    files={name:(ROOT/'Layout/tools/physical'/name).read_bytes() for name in ('qualify_sar_timing.py','run_physical.py','sar_rc_corner.py')}
    files['sar_timing.il']=(ROOT/'Layout/design/sar_timing.il').read_bytes()
    sar=json.loads((ROOT/'Layout/design/manifest.json').read_text())['cells']['sar_timing']
    if sar.get('generator')=='Layout/design/sar_standard.py':
        from Layout.design.sar_standard import DECAPS
        files['standard-leaves.cdl']=source_cdl(standard_delays=True,static_latch=True,decaps=DECAPS).encode('ascii')
    else:
        files['sar-leaves.cdl']=source_cdl().encode('ascii')
    return files

def package():
    c=config();files={p.name:p.read_bytes() for p in (ROOT/'Layout/tools/physical').glob('*.py')}
    for p in (ROOT/'Layout/design').glob('*.il'):files[p.name]=p.read_bytes()
    for p in (ROOT/'Layout/tb').glob('*.cdl'):files[p.name]=p.read_bytes()
    for name in ['cdac-full.il','cdac-full-reference.cdl']:
        files[name]=(ROOT/'work/layout/full-cdac'/name).read_bytes()
    paired = ROOT/'work/layout/cdac-paired/paired.il'
    if paired.is_file():
        files['cdac-paired.il'] = paired.read_bytes()
    for comparator in (ROOT/'work/layout/comparator').glob('*-reference.cdl'):
        files[comparator.name] = comparator.read_bytes()
    bootstrap = ROOT/'work/layout/bootstrap/bootstrap-reference.cdl'
    if bootstrap.is_file():
        files[bootstrap.name] = bootstrap.read_bytes()
    files.update(sar_qualification_files())
    if 'sar-leaves.cdl' not in files:
        from Layout.design.sar_reference import source_cdl
        files['sar-leaves.cdl']=source_cdl().encode('ascii')
    files['workspace.json']=(json.dumps(c,indent=2)+'\n').encode()
    return c,files

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true')
    p.add_argument('--sar-only',action='store_true',help='Install the current SAR verifier, OA readback and matching transistor reference in an existing runtime')
    a=p.parse_args()
    c,files=(config(),sar_qualification_files()) if a.sar_only else package()
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
    if not a.apply:print(json.dumps({'host':c['host'],'destination':c['remote_root'],'files_sha256':hashes},indent=2));return
    payload={'config':c,'sar_only':a.sar_only,'files':{k:base64.b64encode(v).decode() for k,v in files.items()},'hashes':hashes}
    encoded=base64.b64encode(json.dumps(payload).encode()).decode()
    program=r'''import base64,json,os,fcntl,hashlib,socket
from os.path import join,realpath,dirname
p=json.loads(base64.b64decode('__PAYLOAD__'));c=p['config'];root=c['remote_root'];legacy=c['legacy_root']
assert socket.gethostname().split('.')[0]==c['host']
assert realpath(root)==root and realpath(legacy)==legacy
assert dirname(root)==dirname(legacy) and os.stat(dirname(root)).st_uid==os.getuid()
assert os.stat(legacy).st_uid==os.getuid()
lock=open(join(legacy,'layout.lock'),'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
os.umask(0o077)
for d in [root,join(root,'runtime'),join(root,'state'),join(root,'evidence')]:
 if not os.path.exists(d):os.mkdir(d)
 assert realpath(d)==d and os.stat(d).st_uid==os.getuid()
runtime=join(root,'runtime');state=join(root,'state')
if p['sar_only']:
 assert os.path.isfile(join(runtime,'cds.lib')) and os.path.isfile(join(runtime,'workspace.json'))
previous={}
for name,b64 in p['files'].items():
 assert name==os.path.basename(name)
 blob=base64.b64decode(b64);assert hashlib.sha256(blob).hexdigest()==p['hashes'][name]
 dest=join(runtime,name)
 if os.path.exists(dest):previous[name]=hashlib.sha256(open(dest,'rb').read()).hexdigest()
 # Deployed files are shared current inputs; each native run copies them first.
 with open(dest+'.next','wb') as f:f.write(blob)
 os.rename(dest+'.next',dest)
if not p['sar_only']:
 for name in ['checkpoint.json','fill_applied.json']:
  dest=join(state,name);src=join(legacy,name)
  if not os.path.exists(dest) and os.path.isfile(src):
   with open(dest,'wb') as f:f.write(open(src,'rb').read())
 with open(join(runtime,'cds.lib'),'wb') as f:f.write(open(join(legacy,'cds.lib'),'rb').read())
receipt={'host':c['host'],'runtime':runtime,'files_sha256':p['hashes'],'previous_sha256':previous,'shared_lock':join(legacy,'layout.lock'),'historical_evidence_unchanged':True}
if p['sar_only']:
 receipt['readback_sha256']={k:hashlib.sha256(open(join(runtime,k),'rb').read()).hexdigest() for k in p['files']}
 assert receipt['readback_sha256']==p['hashes']
record='sar-qualification-deployment.json' if p['sar_only'] else 'deployment.json'
with open(join(state,record),'w') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''.replace('__PAYLOAD__',encoded)
    out=subprocess.check_output(['ssh',c['host'],'python -'],input=program.encode(),timeout=45)
    receipt_name='sar-qualification-deployment.json' if a.sar_only else 'deployment.json'
    dest=ROOT/'work/layout/restructure'/receipt_name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(out)
    print('Deployed verified runtime inputs to '+c['remote_root']+'/runtime')

if __name__=='__main__':main()
