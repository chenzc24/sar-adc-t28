"""Bounded SFTP/SCP read of one immutable native file, no remote shell writes."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/sar8_stress_closure'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024'
p=argparse.ArgumentParser()
p.add_argument('case',choices=json.loads((ROOT/'verification/sar8_stress_closure/setup.json').read_text())['names'])
p.add_argument('file',choices=['spectre.out','exit_code','test.raw/logStatus','reduce.log','reduce_exit','reduced.json.gz'])
p.add_argument('--timeout',type=int,default=90)
a=p.parse_args()
assert 1<=a.timeout<=180
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
folder=OUT/'recovery_reads'/stamp/a.case
folder.mkdir(parents=True,exist_ok=False)
dest=folder/Path(a.file).name
command=['scp','-v','-B','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',
         '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2',
         'thu-wei:'+REMOTE+'/'+a.case+'/'+a.file,str(dest)]
with (folder/'transport.stdout').open('wb') as out,(folder/'transport.stderr').open('wb') as err:
    try:rc=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=a.timeout).returncode
    except subprocess.TimeoutExpired:rc=124
(folder/'attempt.json').write_text(json.dumps(dict(case=a.case,file=a.file,returncode=rc,utc=stamp,timeout=a.timeout),indent=2)+'\n')
print('FETCH',rc,str(dest),'bytes',dest.stat().st_size if dest.exists() else None,flush=True)
raise SystemExit(rc)
