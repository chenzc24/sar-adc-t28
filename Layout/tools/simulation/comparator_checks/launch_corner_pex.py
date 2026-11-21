"""Create one comparator corner-extraction evidence identity on the physical host and start it once.

workspace.evidence(create=True) refuses an existing identity, so a retried launch never runs twice.
Usage: launch_corner_pex.py CORNER   (typical | cworst_T | cbest_T)
"""
import base64
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from Layout.project import config  # noqa: E402

corner = sys.argv[1]
ident = 'comp-v8-20261120-pex-%s-supplies' % corner.lower().replace('_', '-')
cfg = config()
here = Path(__file__).resolve().parent
files = {'comp_corner.py': here / 'comp_corner.py', 'sar_rc_corner.py': here / 'sar_rc_corner.py'}
blobs = {n: base64.b64encode(p.read_bytes()).decode() for n, p in files.items()}
code = """import os,sys,subprocess,base64
runtime=RUNTIME
os.chdir(runtime);sys.path.insert(0,runtime)
import workspace
out=workspace.evidence(IDENT,create=True)
for name,value in FILES.items():
    with os.fdopen(os.open(out+'/'+name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(base64.b64decode(value))
compile(open(out+'/comp_corner.py').read(),'comp_corner.py','exec')
log=os.fdopen(os.open(out+'/driver.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb')
print(subprocess.Popen(['python','-u','comp_corner.py',CORNER],cwd=out,stdout=log,stderr=log,stdin=open(os.devnull),preexec_fn=os.setsid,close_fds=True).pid)
""".replace('RUNTIME', repr(cfg['remote_root'] + '/runtime')).replace('IDENT', repr(ident)).replace(
    'FILES', repr(blobs)).replace('CORNER', repr(corner))
for attempt in range(6):
    p = subprocess.run(['ssh', '-o', 'ConnectTimeout=20', cfg['host'], 'python -'], input=code.encode(), capture_output=True)
    if p.returncode == 0:
        print(ident, 'started pid', p.stdout.decode().strip())
        break
    err = p.stderr.decode(errors='replace')
    print('attempt', attempt, err.strip()[-400:])
    if 'already exists' in err or 'exists' in err:
        break
    time.sleep(10)
