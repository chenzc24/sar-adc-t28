"""Read-only SSD/runtime/cgroup reconnaissance; local evidence only."""
import base64,json,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/managed_execution';OUT.mkdir(exist_ok=True)
CODE=r'''from __future__ import print_function
import os,json,subprocess,time
rows=[]
for p in ['/server_local_ssd','/server_local_ssd/chenzc_intern25','/server_local_ssd/chenzc_intern25/sar-adc-t28']:
 r=dict(path=p,exists=os.path.exists(p),resolved=os.path.realpath(p))
 if r['exists']:
  s=os.stat(p);r.update(uid=s.st_uid,gid=s.st_gid,mode=oct(s.st_mode & 4095),writable=os.access(p,os.W_OK),listing=sorted(os.listdir(p))[:35])
 rows.append(r)
runtime=[]
for cmd in ['python3','python','spectre','ionice','nice']:
 try:
  out=subprocess.check_output(['sh','-c','command -v '+cmd],stderr=subprocess.STDOUT).decode().strip()
  ver=subprocess.check_output([out,'--version'],stderr=subprocess.STDOUT).decode()[:120] if cmd.startswith('python') else None
  runtime.append(dict(command=cmd,path=out,version=ver))
 except Exception:runtime.append(dict(command=cmd,path=None))
mem={s.split(':')[0]:s.split(':')[1].strip() for s in open('/proc/meminfo')}
print(json.dumps(dict(host=subprocess.check_output(['hostname']).decode().strip(),uid=os.getuid(),paths=rows,runtime=runtime,
 observed_epoch=time.time(),block_devices=subprocess.check_output(['lsblk','-o','NAME,ROTA,TYPE,MOUNTPOINT']).decode('utf-8','replace'),
 cgroup=open('/proc/self/cgroup').read(),mounts=[s.strip() for s in open('/proc/mounts') if s.split()[1] in ['/server_local_ssd','/home/chenzc_intern25','/sys/fs/cgroup/memory']],
 meminfo={k:mem[k] for k in ['MemAvailable','SwapFree','SwapTotal']},
 processes=subprocess.check_output(['ps','-u','chenzc_intern25','-o','pid,ppid,stat,pcpu,rss,comm','--sort=-rss']).decode().splitlines()[:18])))
'''
cmd='python -u -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(CODE.encode()).decode()+"'))")
with (OUT/'probe.stdout').open('wb') as out,(OUT/'probe.stderr').open('wb') as err:
 try:rc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1','thu-wei',cmd],stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=45).returncode
 except subprocess.TimeoutExpired:rc=124
print('EXIT',rc)
print((OUT/('probe.stdout' if rc==0 else 'probe.stderr')).read_text(errors='replace'))
if rc==0:
 import project
 data=project.load(OUT/'probe.stdout')
 project.save(ROOT/'verification/managed_execution/storage_block_devices.json',dict(
  observed_at_utc=project.now(),host=data['host'],block_devices=data['block_devices'],
  limitation='Kernel block-device rotational flags are observations, not administrator retention/backup guarantees'))
