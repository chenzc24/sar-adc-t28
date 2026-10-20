"""Stop only still-live original smoke jobs after a clock-model defect was found."""
import re
import argparse
from common import OUT,dump
from virtuoso_bridge import VirtuosoClient
parser=argparse.ArgumentParser();parser.add_argument('--stop-original-smoke',action='store_true')
if not parser.parse_args().stop_original_smoke:parser.error('Explicit --stop-original-smoke is required')
c=VirtuosoClient.from_env(profile="t28_io")
text=(OUT/"transient_runner.log").read_text(errors="replace")
paths=list(dict.fromkeys(re.findall(r"\+log (/tmp/virtuoso_bridge_[^ ']+/spectre.out)",text)))
records=[]
for p in paths[-3:]:
    directory=p.rsplit("/",1)[0]
    cmd=f'''/bin/sh -c 'if [ -r "{directory}/spectre.pid" ]; then cdac_pid=$(cat "{directory}/spectre.pid"); printf "%s\\n" "$cdac_pid"; tr "\\000" " " < "/proc/$cdac_pid/cmdline"; fi' '''
    r=c.ssh_runner.run_command(cmd,timeout=30)
    lines=r.stdout.splitlines()
    if len(lines)>=2 and lines[0].isdigit() and directory+"/" in lines[1] and any(n+".scs" in lines[1] for n in ("device_smoke","sar_smoke","caps_smoke")):
        done=c.ssh_runner.run_command("kill -TERM "+lines[0],timeout=30)
        records.append({"pid":int(lines[0]),"verified_cmdline":lines[1],"returncode":done.returncode})
dump("diagnostics/cancelled_clock_smoke.json",records)
print("Cancelled owned original smoke processes:",len(records))
