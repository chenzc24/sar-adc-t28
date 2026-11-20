"""Run the single-edge SAR Innovus place and route on the layout host and collect its outputs.

Inputs come from Layout.design.sar_single_edge; the run directory is state/sar-se-REV/route.
An existing route directory is never overwritten.
"""

import argparse
import hashlib
import json
import shlex
import subprocess

from Layout.project import ROOT, config

INNOVUS = "/home/cshrc/.cshrc.cadence.GENUS201"
OUTPUTS = ("routed.def", "overlay.gds", "route.conn", "route.drc", "route.geom", "place.rpt", "innovus.console")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("revision")
    a = ap.parse_args()
    c = config()
    local = ROOT / "work/layout/sar-se" / a.revision
    remote = f"{c['remote_root']}/state/sar-se-{a.revision}/route"
    q = shlex.quote
    subprocess.check_call(["ssh", c["host"], f"test ! -e {q(remote)} && mkdir -p {q(remote)}"], timeout=30)
    subprocess.check_call(["scp", "-q", str(local / "core.v"), str(local / "route.tcl"), f"{c['host']}:{remote}/"], timeout=120)
    command = (f"cd {q(remote)} && tcsh -fc {q('source ' + INNOVUS + ' >& /dev/null; innovus -no_gui -no_logv -overwrite -init route.tcl >& innovus.console')}"
               " ; grep -q SAR_SE_ROUTE_FINISHED innovus.console")
    subprocess.check_call(["ssh", c["host"], command], timeout=1800)
    for name in OUTPUTS:
        subprocess.check_call(["scp", "-q", f"{c['host']}:{remote}/{name}", str(local / name)], timeout=300)
    console = (local / "innovus.console").read_text(errors="replace")
    summary = dict(revision=a.revision, remote=remote,
                   errors=[l for l in console.splitlines() if l.startswith("**ERROR")],
                   drc_clean="No DRC violations were found" in (local / "route.drc").read_text(errors="replace"),
                   geometry=(local / "route.geom").read_text(errors="replace").split("Total Violations :")[-1].strip(),
                   def_sha256=hashlib.sha256((local / "routed.def").read_bytes()).hexdigest())
    (local / "route.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="ascii", newline="\n")
    print(json.dumps(summary, indent=1))
    if summary["errors"] or not summary["drc_clean"]:
        raise SystemExit("Innovus reported errors or DRC violations")


if __name__ == "__main__":
    main()
