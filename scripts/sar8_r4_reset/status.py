"""Read exact experiment status; no duplicate launching and no CIW execution."""
import argparse
import re
import shlex
from experiment import OUT,read


if __name__=='__main__':
    from virtuoso_bridge import VirtuosoClient
    p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args()
    c=VirtuosoClient.from_env(profile='t28_io',timeout=30,log_to_ciw=False)
    for name in a.names:
        folder=OUT/name
        if (folder/'result.json').exists():
            r=read(folder/'result.json')
            state='COMPLETE' if (folder/'wave_receipt.json').exists() else 'FAILED' if not r['ok'] else 'FINALIZING_WAVE'
            print(name,state,r['ok'],r['errors']);continue
        log=(folder/'runner.log').read_text(errors='replace')
        paths=re.findall(r'\+log (/[^ ]+/spectre\.out)',log)
        if not paths:print(name,'launch',log[-300:]);continue
        path=paths[-1];assert '/virtuoso_bridge_spectre/' in path
        r=c.ssh_runner.run_command('tail -n 15 '+shlex.quote(path),timeout=30)
        print(name,r.stdout[-1500:],r.stderr)
