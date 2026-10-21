"""Read the exact owned run log; never alter running processes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shlex
from virtuoso_bridge import VirtuosoClient

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument("name");a=p.parse_args()
folder=ROOT/"output/sar8_physical/runs"/a.name
text=(folder/"runner.log").read_text(encoding="utf-8",errors="replace")
log=re.search(r"\+log (/[^ ]+/spectre\.out)",text).group(1)
assert "/virtuoso_bridge_spectre/" in log
c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
r=c.ssh_runner.run_command("tail -n 65 "+shlex.quote(log),timeout=30)
lines=r.stdout.splitlines()
print(json.dumps(dict(run=a.name,
    warning_codes=sorted(set(re.findall(r"(?:CMI|SPECTRE|SFE)-\d+",r.stdout))),
    footer=re.findall(r"spectre completes with [^\n]+",r.stdout),
    progress_tail=next((s for s in reversed(lines) if re.fullmatch(r"[.\d ]+",s.strip()) and "." in s),None),
    last_warning=next((s.strip() for s in reversed(lines) if "WARNING (" in s),None),
    timing=[s.strip() for s in lines if "elapsed" in s and ("tran" in s or "Time accumulated" in s)],
    read_error=r.stderr),indent=2))
