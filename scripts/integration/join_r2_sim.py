"""Run untouched saved-OA R2 DUT with stimulus/analysis wrappers only."""
from __future__ import annotations
import argparse
import contextlib
from concurrent.futures import as_completed
import math
import re
import sys

import join_r1_sim
from join_r2 import OUT,VAS,GATE,COMMIT,dump,r1,audit_export


def prepare(point):
    assert point in ("nfull","nhalf")
    export=OUT/"exports/primary/input.scs"
    audit=r1.read_json(OUT/"exports/primary/audit.json")
    assert r1.sha(export)==audit["export_sha256"]
    text=export.read_text();audit_export(text);before=r1.blocks(text)
    v={"nfull":-.8,"nhalf":-.003515625}[point]
    def variables(match):
        keys=match[1].replace("\\","").split();values={"SUP":.9,"VDIFF":v}
        assert set(keys)<=values.keys(),keys
        return "parameters "+" ".join(f"{k}={values[k]:.14g}" for k in keys)
    text,n=re.subn(r"(?m)^parameters (.*(?:\n[ \t]+.*)*)",variables,text);assert n==1
    text=text.replace("save=allpub","save=selected").replace("reltol=1e-4","reltol=1e-5")
    text=text.replace("vabstol=1e-6","vabstol=1e-8").replace("iabstol=1e-12","iabstol=1e-13")
    text=re.sub(r"(?m)^\w+ info [^\n]*\n","",text)
    includes=re.findall(r'(?m)^ahdl_include "([^"]+)"',text)
    assert len(includes)==2,includes
    for name,path in VAS.items():
        expected=f"/{name}/veriloga/veriloga.va"
        old=next(p for p in includes if p.endswith(expected))
        text=text.replace(f'ahdl_include "{old}"',f'ahdl_include "{path.name}"')
    assert r1.blocks(text)==before,"No DUT edits permitted"
    saves=join_r1_sim.signals()+["XDUT.GCOMMIT","XDUT.XCOMP.X","XDUT.XCOMP.Y","XDUT.XCOMP.TAIL"]
    text+="\ntran_join tran stop=200n maxstep=10p errpreset=conservative\n"
    text+="save "+" ".join(saves)+"\n"
    path=OUT/f"decks/{point}.scs";assert not path.exists(),"Preserve case "+point
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding="utf-8")
    dump(f"cases/{point}.json",dict(name=point,point=point,export_sha256=r1.sha(export),
        deck_sha256=r1.sha(path),gate_va_sha256=r1.sha(VAS[GATE]),commit_va_sha256=r1.sha(VAS[COMMIT]),
        stimulus_vdiff_by_frame=[v,v],supply_v=.9,temperature_c=27,corner="tt",MOM_corner="tt",
        resolution_bits=8,sample_rate_hz=10e6,stop_ns=200,maxstep_ps=10,output_strobe_ps=0,
        saved_signals=saves,native_controller=True,native_StrongARM=True,native_Bootstrap=True,
        native_MOM_and_3x_reference_pass_MOS=True,ideal_DAC_plant=False,
        physical_noise=False,mismatch=False,scope="exact_saved_R2_OA_DUT_plus_stimulus_analysis_wrapper"))
    print("PREPARED",point,flush=True)


def run(names):
    from virtuoso_bridge.spectre.runner import SpectreSimulator,spectre_mode_args
    cases=[r1.read_json(OUT/f"cases/{n}.json") for n in names]
    for c in cases:
        assert not (OUT/f"runs/{c['name']}_result.json").exists()
        assert r1.sha(OUT/f"decks/{c['name']}.scs")==c["deck_sha256"]
        assert r1.sha(VAS[GATE])==c["gate_va_sha256"] and r1.sha(VAS[COMMIT])==c["commit_va_sha256"]
    sim=SpectreSimulator.from_env(profile="t28_io",work_dir=OUT/"spectre",timeout=1800,
        spectre_args=[*spectre_mode_args("aps"),"+lqtimeout","60"])
    progress=sys.stdout
    with (OUT/"runner.log").open("a",encoding="utf-8") as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        with sim.parallel_pool(max_workers=2) as pool:
            tasks={pool.submit(OUT/f"decks/{c['name']}.scs",{"include_files":[str(p) for p in VAS.values()]}):c for c in cases}
            for future in as_completed(tasks):
                c=tasks[future];result=future.result();name=c["name"]
                dump(f"runs/{name}_result.json",dict(ok=result.ok,errors=result.errors,warnings=result.warnings,
                    metadata=result.metadata,deck_sha256=c["deck_sha256"],gate_va_sha256=c["gate_va_sha256"],
                    commit_va_sha256=c["commit_va_sha256"]))
                if result.ok:
                    w={str(k).strip('"').replace("\\","").lower():v for k,v in result.data.items()
                       if isinstance(v,list) and str(k).lower()!="units"}
                    assert "time" in w and len(w["time"])>10
                    for k,v in w.items():
                        assert len(v)==len(w["time"]) and all(math.isfinite(x) for x in v),k
                    for s in c["saved_signals"]:
                        if ":" not in s:assert s.lower().replace("\\","") in w,s
                    dump(f"runs/{name}_waveform.json",w)
                print("SPECTRE",name,result.ok,result.errors[:2],file=progress,flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run"])
    ap.add_argument("names",nargs="+");args=ap.parse_args()
    if args.action=="prepare":
        for name in args.names:prepare(name)
    else:run(args.names)
