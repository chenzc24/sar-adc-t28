"""Create one corner-extraction evidence identity of a completed stream and start it once.

The identity is SOURCE-CORNER (for example se-xref-peripheral-dense-cworst-t). workspace.evidence(create=True)
refuses an existing identity, so a retried launch never runs twice. The remote driver is xref_rc_corner.py for
a coupled XREF/CDAC stream and bootstrap_rc_corner.py for the Bootstrap core (--case bootstrap).
Usage: python -m Layout.tools.physical.launch_xref_rc_corner SOURCE CORNER [--case bootstrap]   (cworst_T | cbest_T)
"""
import argparse
import base64
import re
import subprocess
from pathlib import Path

from Layout.project import config


DRIVERS = {'xref': 'xref_rc_corner.py', 'bootstrap': 'bootstrap_rc_corner.py'}


def launch(source, corner, case='xref'):
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,40}', source) or corner not in ('cworst_T', 'cbest_T') or case not in DRIVERS:
        raise ValueError('Unsupported source, corner or case')
    driver = DRIVERS[case]
    ident = source + '-' + corner.lower().replace('_', '-')
    cfg = config()
    here = Path(__file__).resolve().parent
    blobs = {n: base64.b64encode((here / n).read_bytes()).decode() for n in (driver, 'sar_rc_corner.py')}
    code = """import os,sys,subprocess,base64
runtime=RUNTIME
os.chdir(runtime);sys.path.insert(0,runtime)
import workspace
out=workspace.evidence(IDENT,create=True)
for name,value in FILES.items():
    with os.fdopen(os.open(out+'/'+name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(base64.b64decode(value))
compile(open(out+'/'+DRIVER).read(),DRIVER,'exec')
log=os.fdopen(os.open(out+'/driver.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb')
print(subprocess.Popen(['python','-u',DRIVER,SOURCE,CORNER],cwd=out,stdout=log,stderr=log,stdin=open(os.devnull),preexec_fn=os.setsid,close_fds=True).pid)
""".replace('RUNTIME', repr(cfg['remote_root'] + '/runtime')).replace('IDENT', repr(ident)).replace(
        'SOURCE', repr(source)).replace('CORNER', repr(corner)).replace('DRIVER', repr(driver)).replace(
        'FILES', repr(blobs))
    p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', cfg['host'], 'python -'],
                       input=code.encode(), capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-600:])
    return ident, int(p.stdout.decode().strip())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source')
    ap.add_argument('corner', choices=('cworst_T', 'cbest_T'))
    ap.add_argument('--case', choices=sorted(DRIVERS), default='xref')
    a = ap.parse_args()
    print('%s started pid %d' % launch(a.source, a.corner, a.case))
