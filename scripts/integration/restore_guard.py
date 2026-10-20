"""Change only16 ideal-gate restore delays; all R2 sources remain read-only."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil

import join_r2 as base
import join_r2_sim as runner

ROOT=base.ROOT
BASE=base.OUT
OUT=ROOT/"output/sar8_restore_guard"
GUARDS_PS=(100,500)


def dump(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def baseline():
    manifest=base.r1.read_json(ROOT/"verification/integration/join_r2_results.json")
    for relative,digest in manifest["source_text_LF_sha256"].items():
        text=(ROOT/relative).read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode()).hexdigest()==digest,relative
    row=next(c for c in manifest["cases"] if c["name"]=="nfull")
    assert base.r1.sha(BASE/"decks/nfull.scs")==row["context"]["deck_sha256"]
    assert base.r1.sha(BASE/"runs/nfull_waveform.json")==row["waveform_sha256"]
    for name,path in base.VAS.items():assert base.r1.sha(path)==manifest["exact_gate_VA_sha256"][name]
    return row


def patch(text,guard_ps):
    assert guard_ps in GUARDS_PS
    original=text
    # Includes continued lines/initial_high without changing any other byte.
    text,count=re.subn(r"(sar8j_aligned_refgate\s+initial_high=[01])",
                       rf"\1 restore_guard_s={guard_ps}p",text)
    assert count==16,count
    assert text.replace(f" restore_guard_s={guard_ps}p","")==original
    assert len(re.findall(r"restore_guard_s=",text))==16
    return text


def prepare(guard_ps):
    row=baseline();name=f"nfull_g{guard_ps}ps"
    original=(BASE/"decks/nfull.scs").read_text()
    text=patch(original,guard_ps)
    deck=OUT/f"decks/{name}.scs";assert not deck.exists(),"Immutable case: "+name
    deck.parent.mkdir(parents=True,exist_ok=True);deck.write_text(text,encoding="utf-8")
    context=dict(row["context"])
    context.update(name=name,deck_sha256=base.r1.sha(deck),restore_guard_ps=guard_ps,
                   baseline_case="R2/nfull",baseline_deck_sha256=row["context"]["deck_sha256"],
                   only16_restore_parameter_overrides=True,scope="R2_native_circuit_restore_guard_only")
    dump(f"cases/{name}.json",context)
    dep=OUT/"dependencies/sar_strongarm_t28.json";dep.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(BASE/"dependencies/sar_strongarm_t28.json",dep)
    print("PREPARED",name,flush=True)
    return name


def run(names):
    baseline()
    runner.OUT=OUT;runner.dump=dump
    runner.run(names)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run"])
    ap.add_argument("names",nargs="*");args=ap.parse_args()
    if args.action=="prepare":
        for g in GUARDS_PS:prepare(g)
    else:run(args.names or [f"nfull_g{g}ps" for g in GUARDS_PS])
