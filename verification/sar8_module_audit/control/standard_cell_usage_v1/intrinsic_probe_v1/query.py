"""Exact-file/help read-only query; no CIW, model writes or remote scratch."""
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
    assert script.is_relative_to(HERE) and output.is_relative_to(HERE) and not output.exists()
    encoded=base64.b64encode(script.read_bytes()).decode('ascii')
    code="import base64;exec(base64.b64decode('"+encoded+"'))"
    args=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ConnectionAttempts=1',
          '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=1','thu-wei','python -c '+shlex.quote(code)]
    try:
        r=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        result=dict(stage='bounded_readonly_exact_file_or_help',returncode=r.returncode,
            script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),local_wall_cap_s=30)
        if r.returncode==0:
            assert len(r.stdout)<=128*1024
            result['metadata']=json.loads(r.stdout.decode('utf-8'))
            assert result['metadata']['hostname']=='thu-wei' and result['metadata']['uid']==596
        else:result['failure_stderr']=r.stderr.decode('utf-8','replace')[-2000:]
    except subprocess.TimeoutExpired:result=dict(stage='bounded_readonly_exact_file_or_help',returncode=124,timeout_s=30)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(dict(returncode=result['returncode'],output=output.name,metadata_keys=list(result.get('metadata',{}))),sort_keys=True))


if __name__=='__main__':main()
