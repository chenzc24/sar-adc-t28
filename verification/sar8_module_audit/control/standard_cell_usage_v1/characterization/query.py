"""Bounded authenticated read-only query runner; outputs stay in this subtree."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import shlex
import subprocess

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('script');p.add_argument('output');a=p.parse_args()
    script=(HERE/a.script).resolve();output=(HERE/a.output).resolve()
    assert script.is_relative_to(HERE) and output.is_relative_to(HERE)
    assert not output.exists(),'Preserve prior query result'
    encoded=base64.b64encode(script.read_bytes()).decode('ascii')
    code="import base64;exec(base64.b64decode('"+encoded+"'))"
    args=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',
          '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','thu-wei','python -c '+shlex.quote(code)]
    try:
        r=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
        result=dict(stage='bounded_readonly_metadata',returncode=r.returncode,query_script_sha256=hashlib.sha256(script.read_bytes()).hexdigest())
        if r.returncode==0:
            assert len(r.stdout)<256*1024,'Metadata output cap exceeded'
            result['metadata']=json.loads(r.stdout.decode('utf-8'))
            assert result['metadata']['uid']==596 and result['metadata']['hostname']=='thu-wei'
        else:
            result['failure_stderr']=r.stderr.decode('utf-8','replace')[-2000:]
    except subprocess.TimeoutExpired:
        result=dict(stage='bounded_readonly_metadata',returncode=124,timeout_seconds=45)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
