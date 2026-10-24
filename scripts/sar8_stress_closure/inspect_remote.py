"""Read-only direct SSH inspection, avoiding a slow login shell and pipe hangs."""
from pathlib import Path
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/sar8_stress_closure'
VERIFY=ROOT/'verification/sar8_stress_closure'
REMOTE='/home/chenzc_intern25/TSMC28/llm_IO/sar8_stress_closure_20261024'
names=json.loads((VERIFY/'setup.json').read_text())['names']
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
# Direct, single-line remote program; native files are strictly read-only.
code='import os,json;root='+repr(REMOTE)+';names='+repr(names)+';'+\
     "read=lambda p:open(p).read() if os.path.isfile(p) else '';"+\
     "print(json.dumps([dict(name=n,exit=read(root+'/'+n+'/exit_code').strip(),"+\
     "reduce_exit=read(root+'/'+n+'/reduce_exit').strip(),"+\
     "log_tail=read(root+'/'+n+'/spectre.out')[-3000:]) for n in names]))"
simple='--simple' in sys.argv
host='thu-han' if '--jump' in sys.argv else 'thu-wei'
remote_command=('/bin/cat '+shlex.quote(REMOTE+'/'+names[0]+'/exit_code')) if simple else 'python -c '+shlex.quote(code)
command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',
         '-o','ControlMaster=no','-o','ControlPath=none','-o','ServerAliveInterval=10',
         '-o','ServerAliveCountMax=2',host,remote_command]
output=OUT/('direct_status_'+stamp+'.json')
error=OUT/('direct_status_'+stamp+'.stderr')
with output.open('wb') as out,error.open('wb') as err:
    try:
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=90)
        rc=result.returncode
    except subprocess.TimeoutExpired:
        rc=124
print('DIRECT_STATUS_EXIT',rc,'files',output,error,flush=True)
(OUT/('direct_attempt_'+stamp+'.json')).write_text(json.dumps(dict(
    utc=stamp,host=host,simple_exit_read=simple,returncode=rc,timeout_seconds=90,
    stdout_path=str(output.relative_to(ROOT)),stderr_path=str(error.relative_to(ROOT)),
    native_files_modified=False),indent=2)+'\n')
if rc==0:
    if simple:
        print('First case native exit:',output.read_text())
        raise SystemExit(0)
    rows=json.loads(output.read_text())
    for row in rows:print(row['name'],'exit=',row['exit'],'reduce_exit=',row['reduce_exit'],row['log_tail'][-500:])
    (VERIFY/'recovery_status.json').write_text(json.dumps(dict(utc=stamp,cases=rows),indent=2)+'\n')
else:
    print(error.read_text(errors='replace')[-2000:])
    raise SystemExit(rc)
