"""Read-only R3 characterization: saved OA DUT, measurement wrappers only."""
from __future__ import annotations
import argparse
from concurrent.futures import as_completed
import contextlib
import dataclasses
import gc
import json
import math
from pathlib import Path
import re
import sys

import join_r3 as r3

ROOT=r3.ROOT
OUT=ROOT/"output/sar8_r3_performance"
MANIFEST=ROOT/"verification/integration/join_r3_results.json"
LSB=1.8/256
MONITOR=ROOT/"models/veriloga/r3_performance/r3_perf_monitor.va"
STIM=ROOT/"models/veriloga/r3_performance/r3_transition_stim.va"


def dump(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+"\n",encoding="utf-8")


def baseline():
    m=r3.r1.read_json(MANIFEST)
    for rel,h in m["source_text_LF_sha256"].items():
        import hashlib
        assert hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest()==h,rel
    return m


def preflight():
    from virtuoso_bridge import VirtuosoClient
    c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    m=baseline();info=c.library.get(r3.LIB)
    assert info.path=="/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and info.technology_library=="tsmcN28"
    for obj in (r3.top(),r3.bench()):
        d=c.schematic.read(r3.LIB,obj.name,include_positions=True,param_filters=None)
        assert r3.object_digest(r3.schematic_surface(d))==m["OA_surface_sha256"][obj.name]
        for p in d["instances"]:
            if obj.name==r3.TOP and re.fullmatch(r"XG[PN][0-7]",p["name"]):
                from freeze_r0 import number_or_expression as num
                assert num(p["params"]["restore_guard_s"])==num("100p")
                assert num(p["params"]["edge_s"])==num("50p")
        dump(f"oa/{obj.name}.json",d)
    for name,path in r3.VAS.items():
        target=OUT/f"oa/{name}.va";target.parent.mkdir(parents=True,exist_ok=True)
        result=c.download_file(f"{info.path}/{name}/veriloga/veriloga.va",target)
        assert result.ok and r3.r1.sha(target)==r3.r1.sha(path)
    folder=OUT/"exports/primary";assert not folder.exists()
    exported=c.schematic.export_netlist(r3.LIB,r3.TB,folder,simulator="spectre",timeout=300)
    dump("exports/primary/receipt.json",exported)
    path=Path(exported["input_file"])
    audit=r3.audit_export(path.read_text());audit["export_sha256"]=r3.r1.sha(path)
    assert audit["subckt_sha256"]==m["exact_saved_OA_export_audit"]["subckt_sha256"]
    dump("exports/primary/audit.json",audit)
    dump("preflight.json",dict(library=dataclasses.asdict(info),windows=c.list_windows(),
         parent_manifest_sha256=r3.r1.sha(MANIFEST),R3_saved_export_matches=True))
    print("SAVED_R3_EXACT_EXPORT_OK",flush=True)


def wrapper():
    baseline()
    p=OUT/"exports/primary/input.scs"
    assert r3.r1.sha(p)==r3.r1.read_json(OUT/"exports/primary/audit.json")["export_sha256"]
    text=p.read_text();blocks=r3.r1.blocks(text)
    text,n=re.subn(r"(?m)^parameters (.*(?:\n[ \t]+.*)*)","parameters SUP=.9 VDIFF=.8",text);assert n==1
    text=text.replace("save=allpub","save=selected").replace("reltol=1e-4","reltol=1e-5")
    text=text.replace("vabstol=1e-6","vabstol=1e-8").replace("iabstol=1e-12","iabstol=1e-13")
    text=re.sub(r"(?m)^\w+ info [^\n]*\n","",text)
    for n,path in r3.VAS.items():
        text,nsub=re.subn(rf'(?m)^ahdl_include "[^"]+/{n}/veriloga/veriloga.va"',f'ahdl_include "{path.name}"',text)
        assert nsub==1
    assert r3.r1.blocks(text)==blocks
    return text


def stage(name,text,ctx):
    p=OUT/f"decks/{name}.scs";assert not p.exists(),"Immutable case "+name
    assert r3.r1.blocks(text)==r3.r1.blocks(wrapper()),"DUT edits forbidden"
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding="utf-8")
    # Immutable testbench source snapshots; later source edits cannot alter queued jobs.
    snapshots=[]
    for item in ctx.get("testbench_includes",[]):
        src=Path(item);dest=OUT/"inputs"/r3.r1.sha(src)/src.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():dest.write_bytes(src.read_bytes())
        assert r3.r1.sha(dest)==r3.r1.sha(src)
        snapshots.append(str(dest))
    ctx["testbench_includes"]=snapshots
    ctx.update(name=name,deck_sha256=r3.r1.sha(p),export_sha256=r3.r1.sha(OUT/"exports/primary/input.scs"),
               gate_va_sha256={n:r3.r1.sha(p) for n,p in r3.VAS.items()},corner="tt",supply_v=.9,
               temperature_c=27,mismatch=False,transient_noise=False,unmodified_saved_R3_DUT=True)
    dump(f"cases/{name}.json",ctx)


def pilot():
    saves=[f"D{b}" for b in range(8)]+["SAMPLE","TOPP","TOPN","CMP_CLK","XDUT.XCTRL.ACTIVE"]
    for mt in (1,4):
        text=wrapper()+"\ntran_perf tran stop=200n maxstep=10p errpreset=conservative strobeperiod=1n strobedelay=0 strobeoutput=strobeonly\n"
        stage(f"pilot_mt{mt}_s0",text+"save "+" ".join(saves)+"\n",dict(kind="pilot",threads=mt,stop_ns=200,maxstep_ps=10))


def run(names,workers=2):
    from virtuoso_bridge.spectre.runner import SpectreSimulator,spectre_mode_args
    baseline()
    cases=[r3.r1.read_json(OUT/f"cases/{n}.json") for n in names]
    progress=sys.stdout
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"runner.log").open("a",encoding="utf-8") as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        sim=SpectreSimulator.from_env(profile="t28_io",work_dir=OUT/"spectre",timeout=172800,
            spectre_args=[*spectre_mode_args("aps"),"+lqtimeout","60"])
        with sim.parallel_pool(max_workers=workers) as pool:
            fs={}
            for c in cases:
                assert not (OUT/f"runs/{c['name']}_result.json").exists()
                p=OUT/f"decks/{c['name']}.scs";assert r3.r1.sha(p)==c["deck_sha256"]
                for fpath in c.get("testbench_includes",[]):
                    fp=Path(fpath)
                    assert r3.r1.sha(fp)==fp.parent.name
                fs[pool.submit(p,dict(include_files=[str(p) for p in r3.VAS.values()]+c.get("testbench_includes",[]),
                    spectre_args=[f"+mt={c['threads']}"]))]=c
            for f in as_completed(fs):
                c=fs[f];r=f.result();name=c["name"]
                dump(f"runs/{name}_result.json",dict(ok=r.ok,errors=r.errors,warnings=r.warnings,
                    metadata=r.metadata,deck_sha256=c["deck_sha256"]))
                if r.ok:
                    w={str(k).strip('"').replace("\\","").lower():v for k,v in r.data.items()
                       if isinstance(v,list) and str(k).lower()!="units"}
                    assert "time" in w
                    assert all(len(v)==len(w["time"]) and all(math.isfinite(x) for x in v) for v in w.values())
                    dump(f"runs/{name}_waveform.json",w)
                print("SPECTRE",name,r.ok,r.errors[:2],file=progress,flush=True)
                r.data.clear();del r;gc.collect()


def observed(text):
    text+='\nXMEASURE (SAMPLE CMP_CLK VDD! D0 D1 D2 D3 D4 D5 D6 D7) r3_perf_monitor\n'
    return text+f'ahdl_include "{MONITOR.name}"\n'


def prepare_static(first,last,refine=6,span=.25,tag="",warm=4):
    nframes=warm+(last-first+1)*(2+refine)
    text=wrapper()
    text,n=re.subn(r"(?m)^VVIN[PN] \([^\n]+$","",text);assert n==2
    text+=f'\nXSTIM (VINP_SRC VINN_SRC D0 D1 D2 D3 D4 D5 D6 D7) r3_transition_stim first_k={first} last_k={last} warmup={warm} refine={refine} half_span_lsb={span:.12g}\n'
    text+=f'ahdl_include "{STIM.name}"\n'
    text=observed(text)
    text+=f'\ntran_perf tran stop={nframes*100}n maxstep=10p errpreset=conservative strobeperiod=1n strobeoutput=strobeonly\n'
    text+='save D0 D1 D2 D3 D4 D5 D6 D7 VINP_SRC VINN_SRC SAMPLE CMP_CLK\n'
    stage(f"static_{first:03d}_{last:03d}{tag}",text,dict(kind="static",threads=4,stop_ns=nframes*100,
        maxstep_ps=10,frames=nframes,warmup=warm,first_k=first,last_k=last,refine=refine,
        half_span_lsb=span,threshold_bracket_width_lsb=2*span/2**refine,
        testbench_includes=[str(MONITOR),str(STIM)],
        testbench_source_sha256={str(p.relative_to(ROOT)):r3.r1.sha(p) for p in (MONITOR,STIM)}))


def prepare_dynamic(count=1024,bin_number=461,tag="",warm=4):
    nframes=warm+count;freq=10e6*bin_number/count;amp=.9*10**(-1/20)
    text=wrapper()
    for side,phase in (("P",0),("N",180)):
        statement=f'VVIN{side} (VIN{side}_SRC 0) vsource type=sine dc=.45 sinedc=.45 ampl={amp/2:.16g} freq={freq:.16g} sinephase={phase}'
        text,n=re.subn(rf"(?m)^VVIN{side} \([^\n]+$",statement,text);assert n==1
    text=observed(text)
    text+=f'\ntran_perf tran stop={nframes*100}n maxstep=10p errpreset=conservative strobeperiod=1n strobeoutput=strobeonly\n'
    text+='save D0 D1 D2 D3 D4 D5 D6 D7 VINP_SRC VINN_SRC SAMPLE CMP_CLK\n'
    stage(f"sine_{count}_k{bin_number}{tag}",text,dict(kind="dynamic",threads=4,stop_ns=nframes*100,
        maxstep_ps=10,frames=nframes,warmup=warm,samples=count,coherent_bin=bin_number,
        frequency_hz=freq,input_dbfs=-1,differential_amplitude_v=amp,
        testbench_includes=[str(MONITOR)],testbench_source_sha256={str(MONITOR.relative_to(ROOT)):r3.r1.sha(MONITOR)}))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["preflight","pilot","measure-smoke","prepare-full","run"])
    p.add_argument("names",nargs="*");p.add_argument("--workers",type=int,default=2);a=p.parse_args()
    if a.action=="preflight":preflight()
    elif a.action=="pilot":pilot()
    elif a.action=="measure-smoke":
        prepare_static(128,129,refine=2,tag="_smoke_v3",warm=1)
        prepare_dynamic(count=4,bin_number=1,tag="_smoke_v3",warm=1)
    elif a.action=="prepare-full":
        for lo,hi in ((1,64),(65,128),(129,192),(193,255)):prepare_static(lo,hi)
        prepare_dynamic()
    else:run(a.names,workers=a.workers)
