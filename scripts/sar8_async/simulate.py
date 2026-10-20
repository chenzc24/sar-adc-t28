"""Run immutable generated decks; preserve exact OA-exported DUT hierarchy."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
import re
from pathlib import Path
from concurrent.futures import as_completed
import numpy as np
from oa import OUT,ROOT,dump
from virtuoso_bridge.spectre.runner import SpectreSimulator,spectre_mode_args

os.environ.setdefault("VB_DISABLE_CONTROL_MASTER","1")


def source(cell,tag="recovery"):
    path=OUT/"exports"/cell/tag/"input.scs"
    return path.read_text(encoding="utf-8")


def deck(text,params,stop,save,*,supply=.9,corner="tt",temp=27,maxstep="5p",extra=""):
    def resolve(m):
        names=m.group(1).replace("\\","").split()
        assert all(n in params for n in names),names
        return "parameters "+" ".join(f"{n}={params[n]}" for n in names)
    text=re.sub(r"(?m)^parameters (.*(?:\n[ \t]+.*)*)",resolve,text)
    text=text.replace("temp=27 tnom=27",f"temp={temp} tnom=27")
    text=text.replace("section=ttmacro_mos_moscap",f"section={corner}macro_mos_moscap")
    text=text.replace("reltol=1e-4","reltol=1e-5").replace("vabstol=1e-6","vabstol=1e-8")
    text=text.replace("save=allpub","save=selected")
    text=re.sub(r"(?m)^\w+ info [^\n]*\n","",text)
    return text+f"\n{extra}\ntran_async tran stop={stop} maxstep={maxstep} errpreset=conservative\nsave {' '.join(save)}\n"


def run(name,text,*,scope,includes=(),mode="aps"):
    if (OUT/"results"/(name+".json")).exists():
        raise RuntimeError("Preserve completed evidence; use a new case name: "+name)
    path=OUT/"decks"/(name+".scs");path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8")!=text:raise RuntimeError("Use a new case identity: "+name)
    path.write_text(text,encoding="utf-8");digest=hashlib.sha256(text.encode()).hexdigest()
    sim=SpectreSimulator.from_env(profile="t28_io",work_dir=OUT/"spectre"/name,timeout=1800,
        spectre_args=[*spectre_mode_args(mode),"+lqtimeout","5"])
    log=OUT/"runner_logs"/(name+".txt");log.parent.mkdir(parents=True,exist_ok=True)
    with log.open("w",encoding="utf-8") as stream, contextlib.redirect_stdout(stream):
        result=sim.run_simulation(path,{"include_files":list(includes)})
    row=dict(name=name,scope=scope,ok=result.ok,errors=result.errors,warnings=result.warnings,
             metadata=result.metadata,deck_sha256=digest,mode=mode,
             model_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [ROOT/"models/veriloga/sar8a_plant.va",*map(Path,includes)]})
    dump("results/"+name+".json",row)
    if result.ok:
        vectors,validation=validate_vectors(result.data,text)
        row["waveform_validation"]=validation
        dump("results/"+name+".json",row)
        dump("waves/"+name+".json",vectors)
    print("SIM_RESULT",name,result.ok,result.errors[:2],flush=True)
    return row


def validate_vectors(data,text):
    # With a saved branch current, the in-tree PSF parser also returns a
    # nonphysical property column `units` filled with NaNs. Select exactly
    # the explicit saved traces, never filter/fill a nonfinite real trace.
    wanted={n.lower() for line in re.findall(r"(?m)^save ([^\n]+)",text) for n in line.split()}
    wanted.add("time")
    vectors={k:v for k,v in data.items() if k.lower() in wanted and isinstance(v,list)}
    present={k.lower() for k in vectors}
    assert wanted<=present,("Missing saved traces",wanted-present)
    assert "time" in vectors and len(vectors["time"])>10
    for k,v in vectors.items():
        assert len(v)==len(vectors["time"]) and np.isfinite(np.asarray(v,dtype=float)).all(),k
    ignored=[k for k,v in data.items() if isinstance(v,list) and k.lower() not in wanted]
    return vectors,dict(all_requested_traces_finite=True,ignored_non_trace_metadata=ignored)


def defaults(**kwargs):
    return dict(SUP=.9,VIN_DIFF=.123,PATTERN_MODE=0,PATTERN_WORD=165,
        FAULT_MODE=0,FAULT_BIT=-1,FAULT_FRAME=-1,COMP_DELAY="150p",DELAY_SPREAD=0,**kwargs)


def save_logic():
    return ["SAMPLE","HOLD_START","CMP_CLK","COMP_P","COMP_N","CAPTURE","ADVANCE","PUBLISH",
            "BASE","BUSY","VALID","FAULT"]+[f"D{i}" for i in range(8)]+[f"CODE{i}" for i in range(8)]


def main():
    ap=argparse.ArgumentParser();ap.add_argument("scenario",choices=["gates","logic","strongarm"])
    ap.add_argument("--name");ap.add_argument("--tag",default="recovery");ap.add_argument("--vin",type=float,default=.123)
    ap.add_argument("--supply",type=float,default=.9);ap.add_argument("--temp",type=float,default=27)
    ap.add_argument("--corner",default="tt");ap.add_argument("--pattern",type=int,default=-1)
    ap.add_argument("--fault",type=int,default=0);ap.add_argument("--fault-bit",type=int,default=3)
    ap.add_argument("--delay",default="150p");ap.add_argument("--spread",default="0")
    ap.add_argument("--stop",default="300n");ap.add_argument("--maxstep",default="200p")
    ap.add_argument("--reset-test",action="store_true");args=ap.parse_args()
    if args.scenario=="gates":
        params={"SUP":args.supply};s=source("tb_sar8a_gates",args.tag)
        sigs=["A","B","CK","RST","Q"]+["Y_"+x for x in ("dac","valid","capture","reset","advance","publish","bbm")]
        if args.reset_test:
            s=re.sub(r"(?m)^VSRC_RST .*(?:\n[ \t]+.*)*",
                "VSRC_RST (RST 0) vsource type=pwl wave=[0 SUP 1n SUP 1.02n 0 4.4n 0 4.42n SUP 4.7n SUP 4.72n 0 25.2n 0 25.22n SUP 25.5n SUP 25.52n 0 40n 0]",s)
            s=re.sub(r"(?m)^VSRC_B .*(?:\n[ \t]+.*)*",
                "VSRC_B (B 0) vsource type=pulse val0=0 val1=SUP period=7n delay=2.7n rise=20p fall=20p width=2.5n",s)
    else:
        s=source("tb_sar8a_"+args.scenario,args.tag);params=defaults()
        params.update(SUP=args.supply,VIN_DIFF=args.vin,PATTERN_MODE=int(args.pattern>=0),PATTERN_WORD=max(0,args.pattern),
                      FAULT_MODE=args.fault,FAULT_BIT=args.fault_bit,COMP_DELAY=args.delay,DELAY_SPREAD=args.spread)
        sigs=save_logic()
    text=deck(s,params,args.stop,sigs,corner=args.corner,temp=args.temp,maxstep=args.maxstep)
    row=run(args.name or args.scenario+"_initial",text,scope="native_"+args.scenario)
    raise SystemExit(0 if row["ok"] else 1)


if __name__=="__main__":main()
