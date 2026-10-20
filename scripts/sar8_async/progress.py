"""Read only an exact owned Spectre run's remote log."""
from pathlib import Path
import re
import shlex
import sys
from oa import OUT
from virtuoso_bridge import VirtuosoClient

name=sys.argv[1]
assert re.fullmatch(r"[A-Za-z0-9_-]+",name)
text=(OUT/"runner_logs"/(name+".txt")).read_text(encoding="utf-8")
match=re.search(r"\+log (/tmp/virtuoso_bridge_[^ ]+/spectre.out)",text)
assert match
c=VirtuosoClient.from_env(profile="t28_io")
r=c.ssh_runner.run_command("tail -n 24 "+shlex.quote(match.group(1)),timeout=30)
print(r.stdout);print(r.stderr)
if "--wave" in sys.argv:
    raw=re.search(r"-raw (/tmp/virtuoso_bridge_[^ ]+\.raw)",text)
    assert raw
    r=c.ssh_runner.run_command("tail -n 32 "+shlex.quote(raw.group(1)+"/tran_async.tran.tran"),timeout=30)
    print(r.stdout);print(r.stderr)
