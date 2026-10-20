"""Only change16 ideal reference ramp parameters; preserve every baseline."""
from __future__ import annotations
import argparse
from concurrent.futures import as_completed
import contextlib
import gc
import hashlib
import json
import math
import re
import shutil
import sys

import restore_cross_input as cross

guard=cross.guard
ROOT=cross.ROOT
OUT=ROOT/"output/sar8_reference_edge_slew"
EDGES_PS=(50,100)
POINTS=("nfull","pfull","n_to_p","p_to_n")


def dump(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def baselines():
    neg,_=cross.candidate()
    rows={"nfull":dict(folder=guard.OUT,name="nfull_g100ps",evidence=neg)}
    manifest=guard.base.r1.read_json(ROOT/"verification/integration/restore_cross_input_results.json")
    for rel,h in manifest["source_text_LF_sha256"].items():
        assert hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest()==h,rel
    for r in manifest["cases"]:
        rows[r["name"].removesuffix("_g100ps")]=dict(folder=cross.OUT,name=r["name"],evidence=r)
    assert set(rows)==set(POINTS)
    for r in rows.values():
        folder,name,e=r["folder"],r["name"],r["evidence"]
        assert guard.base.r1.sha(folder/f"decks/{name}.scs")==e["context"]["deck_sha256"]
        assert guard.base.r1.sha(folder/f"runs/{name}_waveform.json")==e["waveform_sha256"]
    return rows


def patch(text,edge_ps):
    assert edge_ps in EDGES_PS
    suffix=f" edge_s={edge_ps}p"
    new,n=re.subn(r"(sar8j_aligned_refgate\s+initial_high=[01] restore_guard_s=100p)",rf"\1{suffix}",text)
    assert n==16
    assert new.replace(suffix,"")==text
    assert new.count("edge_s=")==16
    return new


def prepare():
    old=baselines()
    for edge in EDGES_PS:
        for point in POINTS:
            r=old[point];name=f"{point}_e{edge}ps"
            p=OUT/f"decks/{name}.scs";assert not p.exists(),"Immutable case: "+name
            text=(r["folder"]/f"decks/{r['name']}.scs").read_text(encoding="utf-8")
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(patch(text,edge),encoding="utf-8")
            ctx=dict(r["evidence"]["context"])
            ctx.update(name=name,point=point,edge_ps=edge,deck_sha256=guard.base.r1.sha(p),
                       baseline_case=r["name"],baseline_folder=r["folder"].relative_to(ROOT).as_posix(),
                       baseline_deck_sha256=r["evidence"]["context"]["deck_sha256"],
                       stimulus_transition_ns=ctx.get("stimulus_transition_ns"),
                       only16_edge_parameter_overrides=True,
                       scope="100ps_restore_ideal_reference_slew_TT_no_OA_adoption")
            dump(f"cases/{name}.json",ctx)
            print("PREPARED",name,flush=True)
    dep=OUT/"dependencies/sar_strongarm_t28.json";dep.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(guard.BASE/"dependencies/sar_strongarm_t28.json",dep)


def run(names):
    from virtuoso_bridge.spectre.runner import SpectreSimulator,spectre_mode_args
    baselines()
    cases=[guard.base.r1.read_json(OUT/f"cases/{n}.json") for n in names]
    for c in cases:
        assert not (OUT/f"runs/{c['name']}_result.json").exists()
        assert guard.base.r1.sha(OUT/f"decks/{c['name']}.scs")==c["deck_sha256"]
        assert guard.base.r1.sha(guard.base.VAS[guard.base.GATE])==c["gate_va_sha256"]
        assert guard.base.r1.sha(guard.base.VAS[guard.base.COMMIT])==c["commit_va_sha256"]
    sim=SpectreSimulator.from_env(profile="t28_io",work_dir=OUT/"spectre",timeout=1800,
        spectre_args=[*spectre_mode_args("aps"),"+lqtimeout","60"])
    progress=sys.stdout
    with (OUT/"runner.log").open("a",encoding="utf-8") as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        with sim.parallel_pool(max_workers=2) as pool:
            tasks={pool.submit(OUT/f"decks/{c['name']}.scs",{"include_files":[str(p) for p in guard.base.VAS.values()]}):c for c in cases}
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
                    w.clear()
                print("SPECTRE",name,result.ok,result.errors[:2],file=progress,flush=True)
                # Completed Futures retain result objects; discard only already-persisted arrays.
                result.data.clear();del result;gc.collect()


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run"])
    ap.add_argument("names",nargs="*");a=ap.parse_args()
    if a.action=="prepare":prepare()
    else:run(a.names or [f"{p}_e{e}ps" for e in EDGES_PS for p in POINTS])
