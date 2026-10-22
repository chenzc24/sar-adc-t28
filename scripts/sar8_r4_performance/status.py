"""Read exact owned remote simulation logs without CIW shell execution."""
import argparse
import contextlib
import io
import json
import re
import shlex
from common import OUT, read


def main():
    from virtuoso_bridge import VirtuosoClient
    p=argparse.ArgumentParser();p.add_argument("names",nargs="+");a=p.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    for name in a.names:
        folder=OUT/"cases"/name
        if (folder/"recovered_result.json").exists():
            r=read(folder/"recovered_result.json")
            print(json.dumps(dict(name=name,complete=True,native_analysis_pass=r["ok"],recovery=r["recovery"])))
            continue
        if (folder/"result.json").exists():
            r=read(folder/"result.json")
            print(json.dumps(dict(name=name,complete=True,ok=r["ok"],errors=r["errors"],elapsed=r["elapsed_wall_s"])))
            continue
        state=read(OUT/"flow_status.json")
        from pathlib import Path
        manifest=Path(state.get("recovery_manifest",str(OUT/"recovery_20261022_r2.json")))
        jobs=read(manifest)["jobs"] if manifest.exists() else []
        job=next((j for j in jobs if j["name"]==name),None)
        text=(folder/"runner.log").read_text(errors="replace") if (folder/"runner.log").exists() else ""
        paths=[job["remote"]+"/spectre.out"] if job else re.findall(r"\+log (/[^ ]+/spectre\.out)",text)
        if not paths:
            print(json.dumps(dict(name=name,stage="launch",tail=text[-600:])));continue
        log=paths[-1]
        assert "/virtuoso_bridge_spectre/" in log
        with contextlib.redirect_stdout(io.StringIO()):
            command="tail -n 24 "+shlex.quote(log)
            if job:
                command="if test -f "+shlex.quote(log)+"; then "+command+"; else printf 'queued'; fi; if test -f "+shlex.quote(job["remote"]+"/exit_code")+"; then printf '\\nexit_code='; cat "+shlex.quote(job["remote"]+"/exit_code")+"; fi"
            r=c.ssh_runner.run_command(command,timeout=30)
        measured=re.findall(r"R4MEAS,[^\r\n]+",r.stdout)
        print(json.dumps(dict(name=name,last_frame=measured[-1] if measured else None,
            progress_tail=r.stdout[-150:],warning_codes=sorted(set(re.findall(r"(?:CMI|SPECTRE|SFE)-\d+",r.stdout))),error=r.stderr)))


if __name__=="__main__":main()
