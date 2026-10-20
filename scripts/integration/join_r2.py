"""Saved OA adoption of tested ideal reference timing; R1 stays read-only."""
from __future__ import annotations
import argparse
import dataclasses
import json
import re
from pathlib import Path

import join_r1 as r1
from freeze_r0 import object_digest,schematic_surface,number_or_expression

ROOT=r1.ROOT
OUT=ROOT/"output/sar8_join_r2"
LIB=r1.LIB
TOP="sar_adc8_join_r2"
TB="tb_sar_adc8_join_r2"
COMMIT="sar8j_refcommit"
GATE="sar8j_aligned_refgate"
VAS={n:ROOT/f"models/veriloga/sar8_join_r2/{n}.va" for n in (COMMIT,GATE)}


def dump(name,value):
    path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+"\n",encoding="utf-8")


def models():
    commit=r1.Cell(COMMIT,["SAMPLE","VDD","VSS"]+
        [f"{q}{i}" for i in range(16) for q in "HL"],["COMMIT"])
    gate=r1.Cell(GATE,["SAMPLE","EH","EL","VDD","VSS","COMMIT"],["GP","GN"])
    return [commit,gate]


def top():
    obj=r1.top();obj.name=TOP
    for p in obj.parts:
        if re.fullmatch(r"XG[PN][0-7]",p.name):
            p.master=GATE;p.terms["COMMIT"]="GCOMMIT"
    ports={"SAMPLE":"SAMPLE","VDD":"VDD!","VSS":"gnd!","COMMIT":"GCOMMIT"}
    for i,(bank,b) in enumerate((bank,b) for bank in "PN" for b in range(8)):
        ports[f"H{i}"]=f"B{bank}_H{b}";ports[f"L{i}"]=f"B{bank}_L{b}"
    obj.add("XGCOMMIT",COMMIT,ports,settle_s="200p")
    return obj


def bench():
    obj=r1.bench();obj.name=TB
    next(p for p in obj.parts if p.name=="XDUT").master=TOP
    return obj


def check_split():
    prior=(ROOT/"models/veriloga/sar8j_aligned_refgate.va").read_text()
    for name,path in VAS.items():
        pattern=rf"(?s)module {name}\(.*?endmodule"
        assert re.search(pattern,path.read_text())[0]==re.search(pattern,prior)[0],name


def preflight(c,after=False):
    check_split()
    info=c.library.get(LIB)
    assert info.path=="/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library=="tsmcN28"
    windows=c.list_windows()
    frozen=r1.read_json(ROOT/"verification/integration/join_r1_results.json")
    hashes=dict(frozen["new_OA_schematic_surface_sha256"])
    native=r1.read_json(ROOT/"verification/integration/join_r0_sources.json")
    hashes.update({n:v["surface_sha256"] for n,v in native["live_readback"]["cells"].items()})
    for name,expected in hashes.items():
        actual=c.schematic.read(LIB,name,include_positions=False)
        assert object_digest(schematic_surface(actual))==expected,"Frozen OA changed: "+name
        dump(f"dependencies{'_after' if after else ''}/{name}.json",actual)
    for obj in models()+[top(),bench()]:
        if not after:
            assert not any(f"{LIB} {obj.name} " in w["name"] for w in windows),"Target GUI-open"
            if r1.exists(c,obj.name):
                assert (OUT/f"owned/{obj.name}.json").exists(),"Unowned existing target: "+obj.name
    dump("preflight_after.json" if after else "preflight.json",
         dict(library=dataclasses.asdict(info),windows=windows,frozen_cells_matched=len(hashes)))
    print("PREFLIGHT",len(hashes),"frozen OA cells match",flush=True)


def import_model(c,obj):
    path=VAS[obj.name]
    receipt=OUT/f"owned/{obj.name}.json"
    if r1.exists(c,obj.name):
        assert receipt.exists() and r1.read_json(receipt)["sha256"]==r1.sha(path)
        if r1.read_json(receipt).get("complete"):return read_model(c,obj)
    else:
        dump(f"owned/{obj.name}.json",dict(sha256=r1.sha(path)))
        r1.make_symbol(c,obj)
    if not r1.exists(c,obj.name,"veriloga"):
        r1.skill(c,f'schViewToView("{LIB}" "{obj.name}" "{LIB}" "{obj.name}" "symbol" "veriloga" "schSymbolToPinList" "ahdlPinListToveriloga")')
    remote=f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{obj.name}/veriloga/veriloga.va"
    result=c.upload_file(path,remote);assert result.ok,result.errors
    r1.skill(c,f'ahdlUpdateViewInfo("{LIB}" ?cell "{obj.name}" ?view "veriloga")')
    param,default=("initial_high","0") if obj.name==GATE else ("settle_s","200p")
    # Exact IC618 import/CDF path already used for frozen R1, no native CDF edits.
    r1.skill(c,f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "{obj.name}")) unless(d d=cdfCreateBaseCellCDF(ddGetObj("{LIB}" "{obj.name}"))) unless(cdfFindParamByName(d "{param}") cdfCreateParam(d ?name "{param}" ?prompt "{param}" ?type "string" ?defValue "{default}" ?parseAsNumber "yes" ?parseAsCEL "yes")) cdfSaveCDF(d))')
    data=read_model(c,obj)
    dump(f"owned/{obj.name}.json",dict(sha256=r1.sha(path),complete=True))
    return data


def read_model(c,obj):
    target=OUT/f"oa/{obj.name}_remote.va";target.parent.mkdir(parents=True,exist_ok=True)
    remote=f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{obj.name}/veriloga/veriloga.va"
    result=c.download_file(remote,target)
    assert result.ok and r1.sha(target)==r1.sha(VAS[obj.name]),obj.name
    ports=c.symbol.read_ports(LIB,obj.name)
    dump(f"oa/{obj.name}_symbol.json",ports)
    print("VA_BYTES_OK",obj.name,flush=True)
    return ports


def build(c,obj):
    from virtuoso_bridge.virtuoso.schematic.ops import (
        schematic_create_inst_by_master_name as inst,schematic_create_pin as pin,
        schematic_label_instance_term as term)
    receipt=OUT/f"owned/{obj.name}.json"
    if r1.exists(c,obj.name):
        assert receipt.exists() and r1.read_json(receipt)==json.loads(json.dumps(dataclasses.asdict(obj)))
        if (OUT/f"owned_complete/{obj.name}.json").exists():return r1.readback(c,obj)
        raise RuntimeError("Partial owned schematic retained; inspect before retry: "+obj.name)
    dump(f"owned/{obj.name}.json",dataclasses.asdict(obj))
    with c.schematic.create(LIB,obj.name,timeout=180) as s:
        for names,x,direction in ((obj.inputs,-20,"input"),(obj.outputs,250,"output")):
            for j,n in enumerate(names):s.add(pin(n,x,25-j*1.5,"R0",direction=direction))
    for start in range(0,len(obj.parts),12):
        with c.schematic.modify(LIB,obj.name,timeout=180) as s:
            for i in range(start,min(start+12,len(obj.parts))):
                p=obj.parts[i]
                if obj.name==TOP:
                    core={"XBOOTP":(0,35),"XBOOTN":(0,10),"XCDAC":(40,0),
                          "XCOMP":(70,15),"XCTRL":(110,-5),"XGCOMMIT":(0,-170)}
                    if re.fullmatch(r"XG[PN][0-7]",p.name):
                        x=int(p.name[-1])*30;y=-80 if p.name[2]=="P" else -110
                    else:x,y=core.get(p.name,((i%8)*30,-230-(i//8)*12))
                else:x=(i%6)*35;y=-(i//6)*50
                s.add(inst(p.lib,p.master,"symbol",p.name,x,y,"R0"))
                for t,n in p.terms.items():s.add(term(p.name,t,n))
    r1.set_params(c,obj)
    if obj.inputs or obj.outputs:r1.make_symbol(c,obj)
    with c.schematic.modify(LIB,obj.name,timeout=180):pass
    data=r1.readback(c,obj)
    dump(f"owned_complete/{obj.name}.json",dict(complete=True))
    return data


def canonical_top(body):
    matches=list(re.finditer(r"\b(\w+) \(([^)]*)\) (\w+)(.*?)(?= \w+ \(|$)",body))
    return {m[1]:(m[2],m[3],{k:number_or_expression(v) for k,v in re.findall(r"(\w+)=([^ ]+)",m[4])})
            for m in matches}


def audit_export(text):
    audit=r1.audit_export(text)
    actual=r1.blocks(text)
    tested=r1.blocks((ROOT/"output/sar8_reference_alignment/decks/nfull_a200.scs").read_text())
    assert set(actual)==(set(tested)-{r1.TOP})|{TOP}
    for name,body in tested.items():
        if name!=r1.TOP:assert actual[name]==body,"Native body differs: "+name
    a=canonical_top(actual[TOP]);b=canonical_top(tested[r1.TOP])
    assert a==b,"Saved OA top differs from tested ideal timing experiment"
    audit.update(native_all_subckts_unchanged=True,top_electrical_statements_match_tested_alignment=True,
                 top_statement_count=len(a))
    return audit


def main():
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["preflight","build","readback","export","postflight","open"])
    ap.add_argument("--tag",default="primary");args=ap.parse_args()
    from virtuoso_bridge import VirtuosoClient
    c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    # Helpers remain unedited; isolate all helper output writes to R2.
    r1.OUT=OUT;r1.dump=dump
    if args.action in ("preflight","postflight"):return preflight(c,args.action=="postflight")
    if args.action=="build":
        preflight(c)
        for obj in models():import_model(c,obj)
        for obj in (top(),bench()):build(c,obj)
    elif args.action=="readback":
        for obj in models():read_model(c,obj)
        for obj in (top(),bench()):r1.readback(c,obj)
    elif args.action=="export":
        folder=OUT/"exports"/args.tag
        assert not (folder/"input.scs").exists(),"Use fresh export tag"
        r1.readback(c,top());r1.readback(c,bench())
        result=c.schematic.export_netlist(LIB,TB,folder,simulator="spectre",timeout=300)
        dump(f"exports/{args.tag}/receipt.json",result)
        path=Path(result["input_file"]);assert path.exists()
        audit=audit_export(path.read_text());audit["export_sha256"]=r1.sha(path)
        dump(f"exports/{args.tag}/audit.json",audit)
        print("EXPORTED_AUDITED",path,flush=True)
    else:
        result=c.open_window(LIB,TOP,view="schematic");assert not result.errors,result.errors


if __name__=="__main__":main()
