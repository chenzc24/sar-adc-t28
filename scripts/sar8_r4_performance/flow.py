"""One-shot performance job: benchmark gate, bounded batch, then final analysis."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse
import subprocess
import time
from common import ROOT,OUT,read,dump
from run import prepare

WORK_PY=ROOT.parents[1]/".venv/Scripts/python.exe"
ANALYSIS_PY=ROOT/".venv/Scripts/python.exe"
HERE=ROOT/"scripts/sar8_r4_performance"
PILOTS=["pilot_aps","pilot_ax_strict","pilot_cx","pilot_ax","pilot_cx_mt1"]
SMOKES=["smoke_static_cx","smoke_sine_cx"]
RANGES=[(i,min(i+31,255)) for i in range(1,256,32)]
STATIC=[f"static_cx_{a:03d}_{b:03d}" for a,b in RANGES]
SINE="sine_cx_1024_k461"


def status(stage,**kw):
    dump(OUT/"flow_status.json",dict(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat(),**kw))
    print(stage,kw,flush=True)


def command(args,logname):
    with (OUT/logname).open("w",encoding="utf-8") as f:
        subprocess.run([str(x) for x in args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)


def wait_cases(names):
    start=time.monotonic()
    while True:
        pending=[]
        for n in names:
            folder=OUT/"cases"/n
            if (folder/"result.json").exists():
                r=read(folder/"result.json")
                if not r["ok"]:raise RuntimeError(f"{n} failed: {r['errors']}")
            if not (folder/"wave_receipt.json").exists():pending.append(n)
        if not pending:return
        if time.monotonic()-start>14400:raise TimeoutError("Pilot/smoke wait exceeded four hours")
        time.sleep(10)


def run_case(name):
    command([WORK_PY,HERE/"run.py","run",name],f"case_{name}.log")
    return name


def main():
    p=argparse.ArgumentParser();p.add_argument("--resume-preflight",action="store_true");args=p.parse_args()
    if args.resume_preflight:
        previous=read(OUT/"flow_status.json")
        assert previous["stage"] in ("waiting_for_pilots_and_smokes","failed")
        assert not (OUT/"cases"/SINE).exists(),"Production already prepared; inspect exact jobs"
        dump(OUT/("flow_preflight_previous_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")+".json"),previous)
    else:
        assert not (OUT/"flow_status.json").exists(),"Inspect existing flow instead of duplicating it"
    try:
        status("waiting_for_pilots_and_smokes",cases=PILOTS+SMOKES)
        wait_cases(PILOTS+SMOKES)
        command([ANALYSIS_PY,HERE/"analyze.py","pilots",*PILOTS],"pilot_analysis.log")
        comparisons=read(OUT/"pilot_comparison.json")
        chosen=next(r for r in comparisons if r["name"]=="pilot_cx")
        assert chosen["output_codes_match"] and chosen["frame_integrity_pass"]
        assert max(chosen["max_held_delta_v"],chosen["max_final_residual_delta_v"])<.01*(1.8/256),chosen
        assert not chosen["numerical_diagnostics"]
        assert not any(x.startswith("CMI-") for x in chosen["warnings"])
        command([ANALYSIS_PY,HERE/"analyze.py","case",*SMOKES],"smoke_analysis.log")
        for name in SMOKES:
            a=read(OUT/"cases"/name/"analysis.json")
            assert a["frame_integrity_pass"] and not a["numerical_diagnostics"],name
            # A physical SOA warning is a measured design failure, not a reason
            # to discard otherwise valid output-code characterization.
            if a["CMI"]:print("SOA_WARNING_RETAINED",name,"full results will be non-qualified",flush=True)
            if a["context"]["kind"]=="static":assert a["all_brackets_pass"]
        # Every child gets immutable source snapshots and its own native result directory.
        prepare(SINE,"sine",mode="cx")
        for (lo,hi),name in zip(RANGES,STATIC):prepare(name,"static",mode="cx",first=lo,last=hi)
        status("running_full_characterization",cases=[SINE]+STATIC,workers=4,threads_per_job=4,
               solver="Spectre X CX; actual preset tolerances recorded; not equal-tolerance APS speedup")
        completed=[]
        with ThreadPoolExecutor(max_workers=4) as pool:
            fs={pool.submit(run_case,n):n for n in [SINE]+STATIC}
            for f in as_completed(fs):
                completed.append(f.result())
                status("running_full_characterization",completed=completed,total=len(fs),cases=[SINE]+STATIC)
        status("analyzing_full_results",completed=completed)
        if (OUT/"cases/pilot_cx_precision/wave_receipt.json").exists():
            command([ANALYSIS_PY,HERE/"analyze.py","pilots",*PILOTS,"pilot_cx_precision"],"pilot_analysis_with_extra_precision.log")
        command([ANALYSIS_PY,HERE/"report.py","--static",*STATIC,"--sine",SINE],"final_analysis.log")
        summary=read(OUT/"summary.json")
        status("complete",nominal_targets_pass=summary["nominal_targets_pass"],report="docs/sar8_r4_performance.md",
               results="verification/sar8_r4_performance/results.json")
    except Exception as exc:
        status("failed",error=str(exc))
        raise


if __name__=="__main__":main()
