"""Read progress of exact log paths emitted by this target's runner."""
import re
import argparse
from common import OUT
from virtuoso_bridge import VirtuosoClient
c=VirtuosoClient.from_env(profile="t28_io")
text=(OUT/"transient_runner.log").read_text(errors="replace")
parser=argparse.ArgumentParser();parser.add_argument('--stem');args=parser.parse_args()
commands=re.findall(r'(?m)^\[Command\].*? (/tmp/virtuoso_bridge_\S+\.scs) .*?\+log (/tmp/virtuoso_bridge_\S+/spectre.out)',text)
paths=list(dict.fromkeys(p for deck,p in commands if not args.stem or deck.endswith('/'+args.stem+'.scs')))
assert paths,'No observed run path for this selection'
for p in paths[-3:]:
    r=c.ssh_runner.run_command(f"tail -12 '{p}'",timeout=30)
    print(p,r.stdout[-1800:],r.stderr,flush=True)
