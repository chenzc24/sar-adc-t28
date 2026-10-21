"""Inspect a live owned run's startup without downloading a waveform file."""
import argparse
import json
from pathlib import Path
import re
import shlex
from virtuoso_bridge import VirtuosoClient

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument("name");a=p.parse_args()
folder=ROOT/"output/sar8_physical/runs"/a.name
log=(folder/"runner.log").read_text(encoding="utf-8",errors="replace")
remote=re.search(r"\+log (/[^ ]+)/spectre\.out",log).group(1)
assert "/virtuoso_bridge_spectre/" in remote
client=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
script=remote+"/physical_probe.py"
r=client.upload_file(Path(__file__).with_name("remote_probe.py"),script);assert r.ok,r.errors
raw=remote+"/"+a.name+".raw/tran_physical.tran.tran"
r=client.ssh_runner.run_command("python "+shlex.quote(script)+" "+shlex.quote(raw),timeout=30)
assert not r.stderr,r.stderr
data=json.loads(r.stdout)
(folder/"startup_probe.json").write_text(json.dumps(data,indent=2)+"\n")
for row in data["rows"]:
    v=row["values"]
    word=sum((1<<i) for i in range(8) if v.get("XDUT.XREF.Q%d"%i,0)>.45)
    print("STARTUP",row["actual_ns"],"Q",word,"TOPP",v.get("XDUT.TOPP"),"TOPN",v.get("XDUT.TOPN"))
