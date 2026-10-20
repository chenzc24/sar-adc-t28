"""Read only the explicitly owned batch-netlister logs."""
import re
import shlex
import sys
from virtuoso_bridge import VirtuosoClient
from oa import dump
cell=sys.argv[1];assert re.fullmatch(r"tb_sar8a_[a-z_]+",cell)
c=VirtuosoClient.from_env(profile="t28_io")
base=f"/server_local_ssd/chenzc_intern25/simulation/{cell}/spectre/schematic/netlist"
command="find "+shlex.quote(base)+" -maxdepth 2 -type f -name '*.log' -print -exec tail -n 45 {} \\;"
r=c.ssh_runner.run_command(command,timeout=30)
dump("diagnostic/"+cell+"_netlist.json",dict(stdout=r.stdout,stderr=r.stderr,returncode=r.returncode))
print(r.stdout);print(r.stderr)
