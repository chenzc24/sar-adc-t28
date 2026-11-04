"""Install one finite low-memory coordinator; all simulations use managed API."""
import argparse,base64,hashlib,json,shlex,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
REMOTE=r'''
import os,sys,json,hashlib,base64,subprocess,resource
payload=json.load(sys.stdin)
root='/server_local_ssd/chenzc_intern25/sar-adc-t28'
dest=root+'/campaigns/sar8-noise-20261029-b101'
assert os.getuid()==596 and os.path.realpath(root)==root and os.stat(root).st_uid==596
for folder in [root+'/campaigns',dest]:
 if not os.path.exists(folder):os.mkdir(folder,0o700)
 assert os.path.realpath(folder)==folder and os.stat(folder).st_uid==596
receipt_name='launch.json'
if os.path.exists(dest+'/launch.json'):
 assert payload.get('resume_import_failure'),'Already launched; inspect identity rather than restart'
 old=json.load(open(dest+'/launch.json'));proc='/proc/'+str(old['pid'])+'/stat'
 if os.path.exists(proc):
  fields=open(proc).read().split()
  assert fields[21]!=old['start_ticks'] or fields[2]=='Z','Coordinator still alive'
 assert not os.path.exists(dest+'/status.json'),'This narrow recovery only covers failure before any managed API call'
 assert 'ImportError: libcrypto.so.10' in open(dest+'/console.log').read()
 receipt_name='launch_after_import_fix.json'
 assert not os.path.exists(dest+'/'+receipt_name),'Recovery already attempted; inspect it'
for item in payload['files']:
 assert item['name'] in ['server_flow.py','manifest.json']
 blob=base64.b64decode(item['data']);assert hashlib.sha256(blob).hexdigest()==item['sha256']
 p=dest+'/'+item['name']
 if os.path.exists(p):assert hashlib.sha256(open(p,'rb').read()).hexdigest()==item['sha256']
 else:
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(blob)
 if item['name']=='server_flow.py':compile(blob,p,'exec')
m=json.load(open(dest+'/manifest.json'))
for run,h in m['registered_hashes'].items():
 assert json.load(open(root+'/runs/'+run+'/registered.json'))['recipe_hash']==h
agent=root+'/tools/agent_'+m['agent_sha256']+'.py'
assert hashlib.sha256(open(agent,'rb').read()).hexdigest()==m['agent_sha256']
def setup():
 # No inherited AS cap: managed workers establish their own frozen limits.
 # Coordinator itself only reads bounded metadata, never raw waveform files.
 os.setsid();os.nice(10)
with open('/dev/null','rb') as null,open(dest+'/console.log','ab') as log:
 child=subprocess.Popen([sys.executable,dest+'/server_flow.py'],stdin=null,stdout=log,stderr=log,close_fds=True,preexec_fn=setup)
fields=open('/proc/'+str(child.pid)+'/stat').read().split()
receipt=dict(pid=child.pid,start_ticks=fields[21],path=dest,manifest_sha256=hashlib.sha256(open(dest+'/manifest.json','rb').read()).hexdigest(),server_flow_sha256=hashlib.sha256(open(dest+'/server_flow.py','rb').read()).hexdigest(),managed_work_only=True)
with open(dest+'/'+receipt_name,'w') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt))
'''
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume-import-failure',action='store_true');args=parser.parse_args()
    files=[]
    for p,name in [(R/'scripts/sar8_noise/finish_fft.py','server_flow.py'),(R/'verification/sar8_noise/fft_manifest.json','manifest.json')]:
        b=p.read_bytes();files.append(dict(name=name,sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
    cmd='python -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))')
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei',cmd],input=json.dumps(dict(files=files,resume_import_failure=args.resume_import_failure)),capture_output=True,text=True,timeout=60)
    dest=R/'output/sar8_noise';dest.mkdir(exist_ok=True)
    suffix='_resume' if args.resume_import_failure else ''
    (dest/('deploy'+suffix+'.stdout')).write_text(p.stdout);(dest/('deploy'+suffix+'.stderr')).write_text(p.stderr)
    if p.returncode:raise RuntimeError('Deployment uncertain; inspect retained stdout/stderr and remote launch.json; never automatically redeploy')
    receipt=json.loads(p.stdout);(R/('verification/sar8_noise/fft_launch'+suffix+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
