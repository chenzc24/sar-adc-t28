"""Stimulus-only extension of the immutable 100ps SAR8 restore candidate."""
from __future__ import annotations
import argparse
import hashlib
import re
import shutil

import restore_guard as guard

ROOT=guard.ROOT
OUT=ROOT/"output/sar8_restore_cross_input"
CASES={"pfull_g100ps":(.8,.8),"n_to_p_g100ps":(-.8,.8),"p_to_n_g100ps":(.8,-.8)}
TRANSITION_NS=(100.8,100.9)


def dump(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(guard.json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def candidate():
    guard.baseline()
    manifest=guard.base.r1.read_json(ROOT/"verification/integration/restore_guard_results.json")
    for rel,h in manifest["source_text_LF_sha256"].items():
        assert hashlib.sha256((ROOT/rel).read_text(encoding="utf-8").encode()).hexdigest()==h,rel
    row=next(r for r in manifest["cases"] if r["restore_guard_ps"]==100)
    folder=ROOT/row["source_folder"];name=row["source_case"]
    deck=folder/f"decks/{name}.scs"
    assert guard.base.r1.sha(deck)==row["context"]["deck_sha256"]
    assert guard.base.r1.sha(folder/f"runs/{name}_waveform.json")==row["waveform_sha256"]
    assert deck.read_text(encoding="utf-8")==guard.patch(
        (guard.BASE/"decks/nfull.scs").read_text(encoding="utf-8"),100)
    return row,deck


def without_stimulus(text):
    text,n=re.subn(r"(?m)^(parameters .*?VDIFF=)[^ \n]+",r"\1<INPUT>",text);assert n==1
    text,n=re.subn(r"(?m)^VVIN([PN]) \([^\n]+$",r"VVIN\1 <SOURCE>",text);assert n==2
    return text


def patch(text,name):
    v0,v1=CASES[name]
    original=text
    text,n=re.subn(r"(?m)^(parameters .*?VDIFF=)[^ \n]+",rf"\g<1>{v0:.14g}",text);assert n==1
    if v0!=v1:
        for side,sign in (("P",1),("N",-1)):
            a=.45+sign*v0/2;b=.45+sign*v1/2
            source=(f"VVIN{side} (VIN{side}_SRC 0) vsource dc={a:.14g} type=pwl "
                    f"wave=[0 {a:.14g} 100.8n {a:.14g} 100.9n {b:.14g} 200n {b:.14g}]")
            text,n=re.subn(rf"(?m)^VVIN{side} \([^\n]+$",source,text);assert n==1
    assert without_stimulus(text)==without_stimulus(original),"Non-stimulus edit"
    assert guard.base.r1.blocks(text)==guard.base.r1.blocks(original),"Native circuit changed"
    assert text.count(" restore_guard_s=100p")==16
    return text


def prepare():
    row,prior=candidate()
    original=prior.read_text(encoding="utf-8")
    for name,values in CASES.items():
        deck=OUT/f"decks/{name}.scs";assert not deck.exists(),"Immutable case: "+name
        deck.parent.mkdir(parents=True,exist_ok=True)
        deck.write_text(patch(original,name),encoding="utf-8")
        ctx=dict(row["context"])
        ctx.update(name=name,point=name,deck_sha256=guard.base.r1.sha(deck),
                   stimulus_vdiff_by_frame=list(values),
                   stimulus_transition_ns=list(TRANSITION_NS) if values[0]!=values[1] else None,
                   candidate_case="restore_guard/nfull_g100ps",
                   candidate_deck_sha256=row["context"]["deck_sha256"],
                   only_input_stimulus_changed_from_candidate=True,
                   scope="netlist_only_100ps_restore_cross_input_TT")
        dump(f"cases/{name}.json",ctx)
        print("PREPARED",name,list(values),flush=True)
    dep=OUT/"dependencies/sar_strongarm_t28.json";dep.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(guard.BASE/"dependencies/sar_strongarm_t28.json",dep)


def run(names):
    candidate()
    guard.runner.OUT=OUT;guard.runner.dump=dump
    guard.runner.run(names)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run"])
    ap.add_argument("names",nargs="*");args=ap.parse_args()
    if args.action=="prepare":prepare()
    else:run(args.names or list(CASES))
