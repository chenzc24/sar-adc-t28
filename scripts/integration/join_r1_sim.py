"""Immutable exact-OA joint R1 decks; only stimulus/analysis wrappers vary."""
from __future__ import annotations
import argparse
import contextlib
from concurrent.futures import as_completed
import math
from pathlib import Path
import re
import sys

from join_r1 import ROOT, OUT, TB, VA, dump, sha, read_json, audit_export, blocks


def signals():
    sigs=["SAMPLE","VINP_SRC","VINN_SRC","VINP","VINN","TOPP","TOPN",
          "CMP_CLK","COMP_P","COMP_N","VREFP","VREFN","VDD!","VVDD:p","VREFHIGH:p","VREFLOW:p"]
    sigs += [f"D{b}" for b in range(8)]
    sigs += [f"XDUT.XCTRL.{n}" for n in ["PHI_W","PHI_U","ACTIVE","DATA"]+
             [f"CODE{b}" for b in range(8)]+[f"T{b}" for b in range(8)]]
    sigs += [f"XDUT.B{bank}_{rail}{b}" for bank in "PN" for rail in "HL" for b in range(8)]
    sigs += [f"XDUT.G{s}{q}{b}" for s in "PN" for q in "PN" for b in range(8)]
    sigs += [f"XDUT.XCDAC.B{s}{b}" for s in "PN" for b in range(8)]
    sigs += [f"XDUT.XBOOT{s}.{n}" for s in "PN" for n in ("G","CLKSB")]
    return sigs


POINTS={"control":.453515625,"nfull":-.8,"pfull":.8,
        "nhalf":-.003515625,"phalf":.003515625,"small":.123}


def prepare(name, point="control", *, tag="primary", fine=False):
    export=OUT/f"exports/{tag}/input.scs"
    text=export.read_text(encoding="utf-8")
    export_audit=read_json(OUT/f"exports/{tag}/audit.json")
    assert sha(export)==export_audit["export_sha256"]
    audit_export(text)
    original_defs=blocks(text)
    step = point in ("carry_up","carry_down","full_reverse")
    if step:
        first,second={"carry_up":(-.003515625,.003515625),
                      "carry_down":(.003515625,-.003515625),
                      "full_reverse":(.8,-.8)}[point]
    else:first=second=POINTS[point]
    # Values are set in the EXISTING exported variable declaration, not by
    # appending eager-bound dependent parameter overrides.
    def variables(match):
        keys=match[1].replace("\\", "").split()
        params={"SUP":.9,"VDIFF":first}
        assert set(keys)<=params.keys(),keys
        return "parameters "+" ".join(f"{k}={params[k]:.14g}" for k in keys)
    text,n=re.subn(r"(?m)^parameters (.*(?:\n[ \t]+.*)*)",variables,text)
    assert n==1,n
    if step:
        for side,sign in (("P",1),("N",-1)):
            initial=.45+sign*first/2; later=.45+sign*second/2
            source=f"VVIN{side} (VIN{side}_SRC 0) vsource type=pwl wave=[0 {initial:.14g} 101n {initial:.14g} 102n {later:.14g} 200n {later:.14g}]"
            text,n=re.subn(rf"(?m)^VVIN{side} .*(?:\n[ \t]+.*)*",source,text)
            assert n==1,n
    text=text.replace("save=allpub","save=selected").replace("reltol=1e-4","reltol=1e-5")
    text=text.replace("vabstol=1e-6","vabstol=1e-8").replace("iabstol=1e-12","iabstol=1e-13")
    text=re.sub(r"(?m)^\w+ info [^\n]*\n","",text)
    includes=re.findall(r'(?m)^ahdl_include "([^"]+)"',text)
    assert len(includes)==1 and includes[0].endswith(f"/{VA.stem}/veriloga/veriloga.va"),includes
    # Only include location changes; upload the EXACT versioned OA source.
    text=re.sub(r'(?m)^ahdl_include "[^"]+"',f'ahdl_include "{VA.name}"',text)
    assert blocks(text)==original_defs,"Never modify any exported DUT body"
    text += f"\ntran_join tran stop=200n maxstep={'10p' if fine else '50p'} errpreset=conservative"
    # Preserve full-rate smoke/fine evidence; later bounded cases save 10-ps
    # strobes to avoid repeatedly transferring >0.4 GB of ASCII per case.
    # Solver tolerances are unchanged. The fine case remains full-rate.
    if not fine:text += " strobeperiod=10p strobeoutput=strobeonly"
    text += "\n"
    selected_signals=signals()+(["XDUT.XCOMP.X","XDUT.XCOMP.Y","XDUT.XCOMP.TAIL"] if fine else [])
    text += "save "+" ".join(selected_signals)+"\n"
    path=OUT/f"decks/{name}.scs"
    assert not path.exists(),"Use a fresh immutable case name: "+name
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding="utf-8")
    context=dict(name=name,point=point,export_tag=tag,export_sha256=sha(export),deck_sha256=sha(path),
                 gate_va_sha256=sha(VA),stimulus_vdiff_by_frame=[first,second],supply_v=.9,
                 temperature_c=27,corner="tt",MOM_corner="tt",resolution_bits=8,
                 sample_rate_hz=10e6,stop_ns=200,maxstep_ps=10 if fine else 50,
                 output_strobe_ps=0 if fine else 10,
                 saved_signals=selected_signals,
                 native_controller=True,native_StrongARM=True,native_Bootstrap=True,
                 native_MOM_and_3x_reference_pass_MOS=True,ideal_DAC_plant=False,
                 physical_noise=False,mismatch=False,
                 scope="exact_saved_R1_OA_DUT_plus_stimulus_analysis_wrapper")
    dump(f"cases/{name}.json",context)
    print("PREPARED",name,point,flush=True)
    return path


def run(names):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    cases=[read_json(OUT/f"cases/{name}.json") for name in names]
    for c in cases:
        assert not (OUT/f"runs/{c['name']}_result.json").exists(),"Preserve run "+c['name']
        assert sha(OUT/f"decks/{c['name']}.scs")==c["deck_sha256"] and sha(VA)==c["gate_va_sha256"]
    sim=SpectreSimulator.from_env(profile="t28_io",work_dir=OUT/"spectre",timeout=1800,
         spectre_args=[*spectre_mode_args("aps"),"+lqtimeout","60"])
    progress=sys.stdout
    log=OUT/"runner.log";log.parent.mkdir(parents=True,exist_ok=True)
    with log.open("a",encoding="utf-8") as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        with sim.parallel_pool(max_workers=2) as pool:
            tasks={pool.submit(OUT/f"decks/{c['name']}.scs",{"include_files":[str(VA)]}):c for c in cases}
            for future in as_completed(tasks):
                case=tasks[future]; name=case["name"]
                result=future.result()
                row=dict(ok=result.ok,errors=result.errors,warnings=result.warnings,metadata=result.metadata,
                         deck_sha256=case["deck_sha256"],gate_va_sha256=case["gate_va_sha256"])
                dump(f"runs/{name}_result.json",row)
                if result.ok:
                    requested={s.lower().replace("\\","") for s in case.get("saved_signals",signals())}
                    # The PSF parser may expose terminal current aliases, so
                    # retain actual trace names and validate voltage keys.
                    w={str(k).strip('"').replace("\\","").lower():v for k,v in result.data.items() if isinstance(v,list) and str(k).lower()!="units"}
                    assert "time" in w and len(w["time"])>10
                    for k,v in w.items():
                        assert len(v)==len(w["time"]) and all(math.isfinite(x) for x in v),k
                    for s in requested:
                        if ":" not in s:assert s in w,(name,"Missing saved voltage",s)
                    dump(f"runs/{name}_waveform.json",w)
                print("SPECTRE",name,result.ok,result.errors[:2],file=progress,flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run","progress"])
    ap.add_argument("--name");ap.add_argument("--point",default="control",choices=list(POINTS)+["carry_up","carry_down","full_reverse"])
    ap.add_argument("--tag",default="primary");ap.add_argument("--fine",action="store_true")
    ap.add_argument("--names",nargs="+");a=ap.parse_args()
    if a.action=="prepare":prepare(a.name or a.point,a.point,tag=a.tag,fine=a.fine)
    elif a.action=="progress":
        from virtuoso_bridge import VirtuosoClient
        name=a.name or a.point
        logs=(OUT/"runner.log").read_text(errors="replace")
        commands=[line for line in logs.splitlines() if line.startswith("[Command]") and "/"+name+".scs " in line]
        assert commands,"No dispatched run: "+name
        remote=re.search(r"\+log (\S+)",commands[-1])[1]
        path=OUT/f"diagnostics/{name}_progress.log";path.parent.mkdir(parents=True,exist_ok=True)
        c=VirtuosoClient.from_env(profile="t28_io",log_to_ciw=False)
        with (OUT/f"diagnostics/{name}_transfer.log").open("a") as stream,contextlib.redirect_stdout(stream):
            result=c.download_file(remote,path)
        assert result.ok,result.errors
        for line in path.read_text(errors="replace").splitlines():
            if re.search(r"(?:^\s*tran_join:|^spectre completes|^Simulation started|^Number of accepted|^Total time required for tran)",line):print(line)
    else:run(a.names or [a.name or a.point])


if __name__=="__main__":main()
