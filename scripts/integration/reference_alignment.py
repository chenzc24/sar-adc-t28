"""Netlist-only shared reference timing; frozen R1/native circuit read-only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil

import join_r1 as r1
import join_r1_sim as runner

ROOT=r1.ROOT
BASE=r1.OUT
OUT=ROOT/"output/sar8_reference_alignment"
VA=ROOT/"models/veriloga/sar8j_aligned_refgate.va"


def dump(name,value):
    path=OUT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def native_top(body):
    body=re.sub(r"\bXG[PN][0-7] \([^)]*\) sar8j_(?:r1|aligned)_refgate initial_high=[01]", "",body)
    body=re.sub(r"\bXGCOMMIT \([^)]*\) sar8j_refcommit(?: settle_s=[\w.]+)?", "",body)
    return " ".join(body.split())


def aligned_deck(text,settle_ps=200):
    """Change only ideal gate statements and include; audit all native bodies."""
    before=r1.blocks(text)
    text,count=re.subn(r"(XG[PN][0-7] \([^)]*)(\) sar8j_r1_refgate)",
                       r"\1 GCOMMIT) sar8j_aligned_refgate",text)
    assert count==16,count
    raw=" ".join(f"B{bank}_{rail}{b}" for bank in "PN" for b in range(8) for rail in "HL")
    line=f"    XGCOMMIT (SAMPLE VDD! 0 {raw} GCOMMIT) sar8j_refcommit settle_s={settle_ps}p\n"
    text=text.replace("    XGN7 (",line+"    XGN7 (",1)
    text=text.replace('ahdl_include "sar8j_r1_refgate.va"',f'ahdl_include "{VA.name}"')
    after=r1.blocks(text)
    assert set(before)==set(after)
    for cell,body in before.items():
        assert (native_top(body)==native_top(after[cell]) if cell==r1.TOP else body==after[cell]),cell
    assert text.count("sar8j_aligned_refgate ")==16
    assert text.count("sar8j_refcommit ")==1
    return text


def prepare(point,settle_ps=200,suffix=""):
    assert re.fullmatch(r"[a-zA-Z0-9_-]*",suffix),"Safe case suffix required"
    name=f"{point}_a{settle_ps}"+("_"+suffix if suffix else "")
    baseline={"nfull":"nfull_fine","nhalf":"nhalf_fine"}.get(point,point)
    context=r1.read_json(BASE/f"cases/{baseline}.json")
    original=BASE/f"decks/{baseline}.scs"
    assert r1.sha(original)==context["deck_sha256"]
    source=original.read_text(encoding="utf-8")
    text=aligned_deck(source,settle_ps)
    text=re.sub(r"(?m)^tran_join tran .*", "tran_join tran stop=200n maxstep=10p errpreset=conservative",text)
    # Fine saves for all comparisons: no output strobes hiding sub-10ps peaks.
    extras=["XDUT.GCOMMIT","XDUT.XCOMP.X","XDUT.XCOMP.Y","XDUT.XCOMP.TAIL"]
    saves=list(dict.fromkeys(context["saved_signals"]+extras))
    text=re.sub(r"(?m)^save .*", "save "+" ".join(saves),text)
    deck=OUT/f"decks/{name}.scs"
    assert not deck.exists(),"Immutable case already exists: "+name
    deck.parent.mkdir(parents=True,exist_ok=True)
    deck.write_text(text,encoding="utf-8")
    context.update(name=name,deck_sha256=r1.sha(deck),gate_va_sha256=r1.sha(VA),
                   saved_signals=saves,maxstep_ps=10,output_strobe_ps=0,
                   baseline_case=baseline,baseline_deck_sha256=r1.sha(original),
                   settle_ps=settle_ps,gate_edge_ps=20,minimum_BBM_ps=100,
                   native_subcircuits_unchanged=True,native_top_except_ideal_gates_unchanged=True,
                   scope="R1_native_circuit_with_shared_ideal_reference_timing_only")
    dump(f"cases/{name}.json",context)
    dep=OUT/"dependencies/sar_strongarm_t28.json"
    dep.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(BASE/"dependencies/sar_strongarm_t28.json",dep)
    print("PREPARED",name,flush=True)
    return name


def run(names):
    # Reuse the exact native APS transport/parser contract, route ALL writes to
    # this experiment. No R1 prepare/analyze function is invoked here.
    runner.OUT=OUT; runner.VA=VA; runner.dump=dump
    runner.run(names)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=["prepare","run"])
    ap.add_argument("names",nargs="+")
    ap.add_argument("--settle-ps",type=int,default=200)
    ap.add_argument("--suffix",default="",help="Fresh case identity for an exact replay")
    args=ap.parse_args()
    if args.action=="prepare":
        for point in args.names:prepare(point,args.settle_ps,args.suffix)
    else:run(args.names)
