"""Bounded native scenarios; the observer counts real transistor-level edges."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from simulate import source,deck,defaults,run,save_logic
from oa import OUT,ROOT,dump


def statement(s,name,value):
    pat=rf"(?m)^{name} .*(?:\n[ \t]+.*)*"
    assert len(re.findall(pat,s))==1,name
    return re.sub(pat,lambda m:value,s,count=1)


def build_case(kind,tag="recovery",maxstep="200p"):
    native_comp=kind.startswith("strongarm")
    text=source("tb_sar8a_strongarm" if native_comp else "tb_sar8a_logic",tag)
    p=defaults();stop="300n";scope="native_logic_behavioral_plant";meta={}
    if kind=="exhaustive":p.update(PATTERN_MODE=2,PATTERN_WORD=0);stop="25.6u"
    elif kind in ("fault_stuck","fault_illegal"):
        p.update(PATTERN_MODE=1,PATTERN_WORD=165,FAULT_FRAME=1,FAULT_BIT=3,FAULT_MODE=1 if kind=="fault_stuck" else 2)
    elif kind=="slow":p.update(PATTERN_MODE=1,PATTERN_WORD=165,COMP_DELAY="1500p");stop="100n"
    elif kind in ("abort","system_reset","duplicate_start"):
        p.update(PATTERN_MODE=1,PATTERN_WORD=165)
        if kind=="abort":
            text=statement(text,"VSRC_PREPARE","VSRC_PREPARE (PREPARE 0) vsource type=pwl wave=[0 0 90n 0 90.02n SUP 100n SUP 100.02n 0 160n 0 160.02n SUP 170n SUP 170.02n 0 290n 0 290.02n SUP 300n SUP]")
        elif kind=="system_reset":
            text=statement(text,"VSRC_RST_N","VSRC_RST_N (RST_N 0) vsource type=pwl wave=[0 0 2n 0 2.02n SUP 160n SUP 160.02n 0 162n 0 162.02n SUP]")
        else:
            stop="100n"
            text=statement(text,"VSRC_HOLD_START","VSRC_HOLD_START (HOLD_START 0) vsource type=pwl wave=[0 0 43n 0 43.02n SUP 43.5n SUP 43.52n 0 60n 0 60.02n SUP 60.5n SUP 60.52n 0 100n 0]")
    elif kind.startswith("strongarm"):
        scope="native_logic_and_unchanged_StrongARM_ideal_sampled_DAC"
        stop="100n"
        p["VIN_DIFF"]={"strongarm_pos":.123046875,"strongarm_neg":-.798046875,"strongarm_high":.798046875}[kind]
    elif kind in ("tt","tight","ff","ss"):
        stop="100n"
    else:raise ValueError(kind)
    if kind=="ff":p["SUP"]=.99;meta.update(corner="ff",temp=-40)
    elif kind=="ss":p["SUP"]=.81;meta.update(corner="ss",temp=125)
    if kind=="tight":maxstep="5p"
    sigs=save_logic()+["VVDD:p"]
    if kind in ("tt","tight"):
        sigs += ["XCTRL.TRIAL","XCTRL.RESET_OK","XCTRL.XSTATUS.COMMIT"]
        sigs += [f"XCTRL.T{i}" for i in range(8)]+[f"SEL{q}_{i}" for q in (0,1) for i in range(8)]
    d=deck(text,p,stop,sigs,maxstep=maxstep,**meta)
    if kind=="exhaustive":
        d=d.replace(f"errpreset=conservative\nsave",f"errpreset=conservative strobeperiod=100n strobedelay=95n strobeoutput=strobeonly\nsave")
    monitor=ROOT/"models/veriloga/sar8a_monitor.va"
    d+='\nXOBSERVER (VDD 0 SAMPLE CMP_CLK CAPTURE ADVANCE VALID FAULT D7 D6 D5 D4 D3 D2 D1 D0) sar8a_monitor\n'
    d+='ahdl_include "sar8a_monitor.va"\n'
    return d,scope,[monitor]


def monitor_rows(name):
    r=json.loads((OUT/"results"/(name+".json")).read_text(encoding="utf-8"));assert r["ok"],r["errors"]
    raw=Path(r["metadata"]["output_dir"])
    path=raw.parent/"spectre.out"
    text=path.read_text(encoding="utf-8",errors="replace")
    rows=[]
    pat=r"SAR8A_FRAME\s+(\d+)\s+CODE\s+(\d+)\s+CAP\s+(\d+)\s+EVAL\s+(\d+)\s+ADV\s+(\d+)\s+VALID\s+(\d+)\s+FAULT\s+(\d+)"
    for vals in re.findall(pat,text):rows.append(dict(zip(("frame","code","cap","eval","adv","valid","fault"),map(int,vals))))
    return rows,text


def check(name,kind):
    rows,text=monitor_rows(name);want_n=256 if kind=="exhaustive" else 3 if kind in ("fault_stuck","fault_illegal","abort","system_reset") else 1
    failures=[]
    if len(rows)!=want_n:failures.append(f"frame count {len(rows)} != {want_n}")
    for row in rows:
        f=row["frame"]
        if kind=="exhaustive":want=f
        elif kind.startswith("strongarm"):want={"strongarm_pos":145,"strongarm_neg":14,"strongarm_high":241}[kind]
        elif kind in ("tt","tight","ff","ss"):want=145
        else:want=165
        if kind=="slow":
            ok=row["valid"]==0 and row["fault"]==1 and row["code"]==0
        elif f==1 and kind in ("fault_stuck","fault_illegal","abort","system_reset"):
            ok=row["valid"]==0 and row["code"]==(0 if kind=="system_reset" else 165)
            if kind!="system_reset":ok &= row["fault"]==1
        else:
            ok=row["valid"]==1 and row["fault"]==0 and row["code"]==want and row["cap"]==row["eval"]==row["adv"]==8
        if not ok:failures.append(row)
    cmi=len(re.findall(r"WARNING \(CMI-",text));suppressed=re.findall(r"(\d+) warnings suppressed",text)
    result=dict(name=name,kind=kind,pass_=not failures,frames=len(rows),rows=rows,failures=failures,
                printed_cmi_warnings=cmi,suppressed_warnings=sum(map(int,suppressed)),
                soa_clean=(cmi==0 and not suppressed))
    dump("analysis/"+name+"_observer.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2));return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument("kind");ap.add_argument("--name");ap.add_argument("--tag",default="recovery")
    ap.add_argument("--check-only",action="store_true");ap.add_argument("--maxstep",default="200p")
    ap.add_argument("--mode",choices=["aps","ax"],default="aps");args=ap.parse_args()
    name=args.name or "native_"+args.kind
    if not args.check_only:
        d,scope,includes=build_case(args.kind,args.tag,args.maxstep)
        r=run(name,d,scope=scope,includes=includes,mode=args.mode)
        if not r["ok"]:raise SystemExit(1)
    checked=check(name,args.kind)
    # A successful simulator exit is not a functional or device-safety pass.
    raise SystemExit(0 if checked["pass_"] and checked["soa_clean"] else 1)


if __name__=="__main__":main()
