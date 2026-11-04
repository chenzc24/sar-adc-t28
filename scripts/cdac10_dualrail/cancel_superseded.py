"""Cancel only this target's pending 10-bit evidence after user corrected to 8 bit."""
import re
from common import OUT,dump
from virtuoso_bridge import VirtuosoClient
c=VirtuosoClient.from_env(profile='t28_io')
log=(OUT/'runs_runner.log').read_text(errors='replace')
paths=list(dict.fromkeys(re.findall(r'\+log (/tmp/virtuoso_bridge_[^ \'\"]+/spectre.out)',log)))
records=[]
for p in paths:
    directory=p.rsplit('/',1)[0]
    cmd=f'''/bin/sh -c 'if [ -r "{directory}/spectre.pid" ]; then adc10_pid=$(cat "{directory}/spectre.pid"); printf "%s\\n" "$adc10_pid"; tr "\\000" " " < "/proc/$adc10_pid/cmdline"; fi' '''
    r=c.ssh_runner.run_command(cmd,timeout=30)
    lines=r.stdout.splitlines()
    if len(lines)>=2 and lines[0].isdigit() and directory+'/' in lines[1] and any(n+'.scs' in lines[1] for n in ['initial_static_all_codes','initial_dynamic_256']):
        done=c.ssh_runner.run_command('kill -TERM '+lines[0],timeout=30)
        records.append({'pid':int(lines[0]),'verified_cmdline':lines[1],'returncode':done.returncode})
dump('diagnostics/cancelled_superseded_10bit.json',records)
print('Cancelled owned superseded processes:',len(records),flush=True)
