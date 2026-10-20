"""Two-process bounded independent simulation queue, never modifies OA."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse
from suite import build_case,check
from simulate import run,source,deck
from analyze import gates
from oa import OUT
import json
from pathlib import Path
import re


def worker(task):
    kind,tag,mode,prefix=task
    if kind=="strongarm_pos":mode="aps"
    name=prefix+"_"+kind+"_"+mode
    if kind.startswith("gates_"):
        corner=kind.split("_")[1];sup=.99 if corner=="ff" else .81;temp=-40 if corner=="ff" else 125
        sigs=["A","B","CK","RST","Q"]+["Y_"+x for x in ("dac","valid","capture","reset","advance","publish","bbm")]
        text=deck(source("tb_sar8a_gates",tag),{"SUP":sup},"24n",sigs,corner=corner,temp=temp,maxstep="200p")
        result=run(name,text,scope="native_primitive_MOS_corner_ideal_RC",mode=mode)
        if not result["ok"]:return dict(name=name,execution_ok=False)
        g=gates(name,supply=sup)
        log=(Path(result["metadata"]["output_dir"]).parent/"spectre.out").read_text(errors="replace")
        clean="WARNING (CMI-" not in log
        return dict(name=name,functional_pass=True,dac_min_ns=g["delays"]["dac"]["minimum_ns"],soa_clean=clean)
    text,scope,includes=build_case(kind,tag)
    result=run(name,text,scope=scope,includes=includes,mode=mode)
    if not result["ok"]:return dict(name=name,execution_ok=False,errors=result["errors"])
    checked=check(name,kind)
    return {k:v for k,v in checked.items() if k not in ("rows","failures")}


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("kinds",nargs="+");ap.add_argument("--tag",default="recovery")
    ap.add_argument("--prefix",default="recovery")
    ap.add_argument("--mode",choices=["aps","ax"],default="ax");args=ap.parse_args()
    with ProcessPoolExecutor(max_workers=2) as pool:
        jobs={pool.submit(worker,(kind,args.tag,args.mode,args.prefix)):kind for kind in args.kinds}
        failed=False
        for f in as_completed(jobs):
            result=f.result();print("CASE_DONE",jobs[f],result,flush=True)
            failed |= result.get("execution_ok",True) is False or result.get("pass_",True) is False
            failed |= result.get("functional_pass",True) is False or result.get("soa_clean",True) is False
    raise SystemExit(1 if failed else 0)
