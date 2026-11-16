"""Deploy owned runtime inputs under the existing physical lock; never submit jobs."""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
from Layout.project import ROOT,config

def package():
    c=config();files={p.name:p.read_bytes() for p in (ROOT/'Layout/tools/physical').glob('*.py')}
    for p in (ROOT/'Layout/design').glob('*.il'):files[p.name]=p.read_bytes()
    for p in (ROOT/'Layout/tb').glob('*.cdl'):files[p.name]=p.read_bytes()
    for name in ['cdac-full.il','cdac-full-reference.cdl']:
        files[name]=(ROOT/'work/layout/full-cdac'/name).read_bytes()
    files['workspace.json']=(json.dumps(c,indent=2)+'\n').encode()
    return c,files

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
    c,files=package();hashes={k:hashlib.sha256(v).hexdigest() for k,v in files.items()}
    if not a.apply:print(json.dumps({'host':c['host'],'destination':c['remote_root'],'files_sha256':hashes},indent=2));return
    payload={'config':c,'files':{k:base64.b64encode(v).decode() for k,v in files.items()},'hashes':hashes}
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
previous={}
for name,b64 in p['files'].items():
 assert name==os.path.basename(name)
 blob=base64.b64decode(b64);assert hashlib.sha256(blob).hexdigest()==p['hashes'][name]
 dest=join(runtime,name)
 if os.path.exists(dest):previous[name]=hashlib.sha256(open(dest,'rb').read()).hexdigest()
 # Deployed files are shared current inputs; each native run copies them first.
 with open(dest+'.next','wb') as f:f.write(blob)
 os.rename(dest+'.next',dest)
for name in ['checkpoint.json','fill_applied.json']:
 dest=join(state,name);src=join(legacy,name)
 if not os.path.exists(dest) and os.path.isfile(src):
  with open(dest,'wb') as f:f.write(open(src,'rb').read())
with open(join(runtime,'cds.lib'),'wb') as f:f.write(open(join(legacy,'cds.lib'),'rb').read())
receipt={'host':c['host'],'runtime':runtime,'files_sha256':p['hashes'],'previous_sha256':previous,'shared_lock':join(legacy,'layout.lock'),'historical_evidence_unchanged':True}
with open(join(state,'deployment.json'),'w') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''.replace('__PAYLOAD__',encoded)
    out=subprocess.check_output(['ssh',c['host'],'python -'],input=program.encode(),timeout=45)
    dest=ROOT/'work/layout/restructure/deployment.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(out)
    print('Deployed verified runtime inputs to '+c['remote_root']+'/runtime')

if __name__=='__main__':main()
