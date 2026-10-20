"""Adopt explicit R3 timing in saved OA, preserving the R1/R2 circuit."""
from __future__ import annotations
import argparse
import dataclasses
import json
import re

import join_r2 as old
from freeze_r0 import object_digest, schematic_surface

r1=old.r1
ROOT=old.ROOT
OUT=ROOT/"output/sar8_join_r3"
LIB=old.LIB
TOP="sar_adc8_join_r3"
TB="tb_sar_adc8_join_r3"
GATE=old.GATE
COMMIT=old.COMMIT
VAS=old.VAS
OLD_TOP=old.TOP
OLD_TB=old.TB


def dump(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+"\n",encoding="utf-8")


def top():
    obj=old.top();obj.name=TOP
    for p in obj.parts:
        if re.fullmatch(r"XG[PN][0-7]",p.name):
            p.params.update(restore_guard_s="100p",edge_s="50p")
    return obj


def bench():
    obj=old.bench();obj.name=TB
    next(p for p in obj.parts if p.name=="XDUT").master=TOP
    return obj


def preflight(c,after=False):
    info=c.library.get(LIB)
    assert info.path=="/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library=="tsmcN28"
    windows=c.list_windows()
    frozen=r1.read_json(ROOT/"verification/integration/join_r0_sources.json")
    hashes={n:v["surface_sha256"] for n,v in frozen["live_readback"]["cells"].items()}
    hashes.update(r1.read_json(ROOT/"verification/integration/join_r1_results.json")["new_OA_schematic_surface_sha256"])
    hashes.update(r1.read_json(ROOT/"verification/integration/join_r2_results.json")["OA_surface_sha256"])
    for name,expected in hashes.items():
        data=c.schematic.read(LIB,name,include_positions=name in (OLD_TOP,OLD_TB),param_filters=None)
        assert object_digest(schematic_surface(data))==expected,"Historical OA changed: "+name
        if after and name==OLD_TOP:
            from freeze_r0 import number_or_expression as num
            gates=[p for p in data["instances"] if re.fullmatch(r"XG[PN][0-7]",p["name"])]
            assert len(gates)==16
            for p in gates:
                assert num(p["params"]["restore_guard_s"])==num("2n")
                assert num(p["params"]["edge_s"])==num("20p")
        dump(f"dependencies{'_after' if after else ''}/{name}.json",data)
    for obj in old.models():old.read_model(c,obj)
    cdf=c.fetch(f'cdfGetBaseCellCDF(ddGetObj("{LIB}" "{GATE}"))~>parameters',
                ["name","type","defValue","value","callback"])
    dump("cdf_after.json" if after else "cdf_before.json",cdf)
    for obj in (top(),bench()):
        if not after:
            assert not any(f"{LIB} {obj.name} " in w["name"] for w in windows),"Target GUI-open"
            if r1.exists(c,obj.name):assert (OUT/f"owned/{obj.name}.json").exists(),"Unowned target"
    dump("preflight_after.json" if after else "preflight.json",
         dict(library=dataclasses.asdict(info),frozen_cells_matched=len(hashes),windows=windows,
              R2_original_2ns_20ps_readback_verified=after))
    print("PREFLIGHT",len(hashes),"historical OA surfaces unchanged",flush=True)


def expose_cdf(c):
    # Same verified CDF import path used by R2; do not alter model defaults.
    before=r1.read_json(OUT/"cdf_before.json")
    for name,value in (("restore_guard_s","2n"),("edge_s","20p")):
        r1.skill(c,f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "{GATE}")) unless(d error("missing gate CDF")) unless(cdfFindParamByName(d "{name}") cdfCreateParam(d ?name "{name}" ?prompt "{name}" ?type "string" ?defValue "{value}" ?parseAsNumber "yes" ?parseAsCEL "yes")) cdfSaveCDF(d))')
    after=c.fetch(f'cdfGetBaseCellCDF(ddGetObj("{LIB}" "{GATE}"))~>parameters',
                  ["name","type","defValue","value","callback"])
    actual={p["name"]:p for p in after}
    for p in before:assert actual[p["name"]]==p,"Existing CDF parameter changed"
    dump("cdf_exposed.json",after)


def readback(c):
    for obj,prior in ((top(),OLD_TOP),(bench(),OLD_TB)):
        data=r1.readback(c,obj)
        baseline=r1.read_json(OUT/f"dependencies/{prior}.json")
        a={p["name"]:p for p in data["instances"]}
        b={p["name"]:p for p in baseline["instances"]}
        assert set(a)==set(b)
        for name,p in a.items():
            p=json.loads(json.dumps(p));q=json.loads(json.dumps(b[name]))
            if obj.name==TOP and re.fullmatch(r"XG[PN][0-7]",name):
                # Compare every other CDF property, master, terminal and position.
                for k in ("restore_guard_s","edge_s"):
                    p["params"].pop(k,None);q["params"].pop(k,None)
            if obj.name==TB and name=="XDUT":p["cell"]=q["cell"]
            assert p==q,(obj.name,name,"Non-timing instance change",p,q)
        def nets(d):
            return {n:{**v,"connections":sorted(v["connections"])} for n,v in d["nets"].items()}
        assert nets(data)==nets(baseline) and data["pins"]==baseline["pins"]
    dump("saved_OA_readback_audit.json",dict(only16_gate_timing_overrides=True,
        native_params_connectivity_positions_unchanged=True,zero_markers=True))


def audit_export(text):
    actual=r1.blocks(text)
    previous=r1.blocks((ROOT/"output/sar8_join_r2/exports/primary/input.scs").read_text())
    assert set(actual)==(set(previous)-{OLD_TOP})|{TOP}
    for name,body in previous.items():
        if name!=OLD_TOP:assert actual[name]==body,"Native subcircuit changed: "+name
    tested=r1.blocks((ROOT/"output/sar8_reference_edge_slew/decks/nfull_e50ps.scs").read_text())
    assert old.canonical_top(actual[TOP])==old.canonical_top(tested[OLD_TOP]),"Not tested 50 ps candidate"
    records=old.canonical_top(actual[TOP])
    gates={n:p for n,p in records.items() if re.fullmatch(r"XG[PN][0-7]",n)}
    assert len(gates)==16
    from freeze_r0 import number_or_expression as num
    for n,(_,master,p) in gates.items():
        assert master==GATE and p["restore_guard_s"]==num("100p") and p["edge_s"]==num("50p"),n
    return dict(native_all_subckts_unchanged=True,top_matches_tested_50ps_candidate=True,
        explicit_timing_gate_instances=len(gates),top_statement_count=len(records),
        subckt_sha256={n:object_digest(b) for n,b in actual.items()})


def main():
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["preflight","build","readback","export","postflight","open"])
    ap.add_argument("--tag",default="primary");a=ap.parse_args()
    from virtuoso_bridge import VirtuosoClient
    c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    r1.OUT=OUT;r1.dump=dump;old.OUT=OUT;old.dump=dump
    if a.action in ("preflight","postflight"):return preflight(c,a.action=="postflight")
    if a.action=="build":
        preflight(c);expose_cdf(c)
        objects=[top(),bench()]
        old.TOP=TOP # same R2 placement branch, no change to old source.
        for obj in objects:old.build(c,obj)
        old.TOP=OLD_TOP
        readback(c)
    elif a.action=="readback":readback(c)
    elif a.action=="export":
        readback(c)
        folder=OUT/"exports"/a.tag
        assert not (folder/"input.scs").exists(),"Use fresh export tag"
        result=c.schematic.export_netlist(LIB,TB,folder,simulator="spectre",timeout=300)
        dump(f"exports/{a.tag}/receipt.json",result)
        from pathlib import Path
        path=Path(result["input_file"]);assert path.exists()
        audit=audit_export(path.read_text());audit["export_sha256"]=r1.sha(path)
        dump(f"exports/{a.tag}/audit.json",audit)
        print("EXPORTED_AUDITED",path,flush=True)
    else:
        result=c.open_window(LIB,TOP,view="schematic");assert not result.errors,result.errors


if __name__=="__main__":main()
