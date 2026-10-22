"""Bounded standalone help query; never runs a shell command through CIW."""
import contextlib
import io
from common import OUT
from virtuoso_bridge import VirtuosoClient

with contextlib.redirect_stdout(io.StringIO()):
    c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    r=c.ssh_runner.run_command("timeout 20 /home/cadence/spectre/SPECTRE211Hotfix/tools/bin/spectre -h 2>&1",timeout=30)
(OUT/"spectre_help.txt").write_text(r.stdout+"\n"+r.stderr,encoding="utf-8")
lines=r.stdout.splitlines()
indices=set()
for i,line in enumerate(lines):
    if any(s in line.lower() for s in ("preset", "override", "spectre x", "+x", "maxstep")):
        indices.update(range(max(0,i-2),min(len(lines),i+9)))
print("\n".join(lines[i] for i in sorted(indices)) or r.stdout[-4000:])
