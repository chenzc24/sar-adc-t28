"""Submit frozen gate-driver physical inputs to the owned layout workspace."""

import argparse
import base64
import hashlib
import json
import re
import subprocess

from Layout.project import ROOT, config, write_json


def submit(identity, from_stream=None, default_supplies=False):
    if not all(re.fullmatch(r"[a-z][a-z0-9-]{1,55}", n) for n in (identity, from_stream or identity)):
        raise ValueError("Invalid physical identity")
    cfg = config()
    source = ROOT / "work/layout/reference-driver" / identity
    inputs = source.parent / from_stream if from_stream else source
    paths = [inputs / n for n in ("build.il", "intent.json", "driver-leaves.cdl")]
    paths += [ROOT / "Layout/design" / name for name in ("reference_driver.il", "sar_timing.il")]
    paths += [ROOT / "work/layout/full-cdac/cdac-full-reference.cdl"]
    paths += [ROOT / "Layout/tools/physical" / name for name in ("run_reference_driver.py", "run_physical.py")]
    blobs = {p.name: p.read_bytes() for p in paths}
    payload = {
        "identity": identity,
        "from_stream": from_stream,
        "default_supplies": default_supplies,
        "config": cfg,
        "files": {name: base64.b64encode(blob).decode("ascii") for name, blob in blobs.items()},
        "sha256": {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()},
    }
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    script = """
import base64, hashlib, json, os, socket, subprocess
from os.path import join, isdir, lexists, realpath
p=json.loads(base64.b64decode(%r))
cfg=p['config']
assert socket.gethostname().split('.')[0]==cfg['host']
root=cfg['remote_root']
runtime=join(root,'runtime')
state=join(root,'state')
for directory in (root,runtime,state,cfg['legacy_root']):
    assert realpath(directory)==directory and isdir(directory) and os.stat(directory).st_uid==os.getuid()
assert json.load(open(join(runtime,'workspace.json')))==cfg
ident=p['identity']
for owner in (root,cfg['legacy_root']):
    if lexists(join(owner,'evidence',ident)):
        raise ValueError('Evidence already exists; check its status')
os.umask(0o077)
marker=join(state,ident+'.reference-submitted')
os.close(os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600))
staging=join(state,ident+'.reference-inputs')
os.mkdir(staging)
for name,data in p['files'].items():
    assert name==os.path.basename(name)
    blob=base64.b64decode(data)
    assert hashlib.sha256(blob).hexdigest()==p['sha256'][name]
    with open(join(staging,name),'wb') as f: f.write(blob)
env=os.environ.copy()
env['PYTHONPATH']=runtime
with open(os.devnull,'rb') as devnull, open(join(state,ident+'.driver'),'wb') as log:
    command=['nohup','python',join(staging,'run_reference_driver.py'),ident]
    if p['from_stream']: command.extend(['--from-stream',p['from_stream']])
    if p['default_supplies']: command.append('--default-supplies')
    runner=subprocess.Popen(command,
        cwd=runtime,env=env,stdin=devnull,stdout=log,stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,close_fds=True)
print(json.dumps(dict(identity=ident,pid=runner.pid,host=cfg['host'],staging=staging,sha256=p['sha256'])))
""" % data
    answer = subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["host"], "python -"],
        input=script.encode("ascii"), timeout=45,
    )
    receipt = json.loads(answer)
    write_json(source / "submission.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    parser.add_argument("--from-stream")
    parser.add_argument("--default-supplies", action="store_true",
                        help="Use the foundry deck's default supply extraction, as in the CDAC control")
    args = parser.parse_args()
    print(json.dumps(submit(args.identity, args.from_stream, args.default_supplies)))
