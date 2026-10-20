"""Create only this target's new OA hierarchy; read back before exporting."""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import json
import math
import os
import re
from pathlib import Path

from circuit import LIB, Cell, hierarchy
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_inst_by_master_name as inst
from virtuoso_bridge.virtuoso.schematic.ops import schematic_create_pin as pin
from virtuoso_bridge.virtuoso.schematic.ops import schematic_label_instance_term as term
from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update
from virtuoso_bridge.virtuoso.symbol.ops import (symbol_create_rect, symbol_create_pin,
    symbol_create_selection_box, symbol_create_instance_label, symbol_create_logical_label,
    symbol_set_term_order)

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"output/sar8_async_impl"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER","1")


def dump(name,obj):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,default=str)+"\n",encoding="utf-8")


def exists(c,cell,view=None):
    arg=' "'+view+'"' if view else ''
    r=c.execute_skill(f'ddGetObj("{LIB}" "{cell}"{arg})',timeout=15)
    if r.errors:raise RuntimeError(r.errors)
    return r.output.strip() not in ("nil","")


def symbol(c,obj):
    top=max(len(obj.inputs),len(obj.outputs))*1.2
    with c.symbol.create(LIB,obj.name,timeout=120) as s:
        s.add(symbol_create_rect("device","drawing",.5,-1,11.5,top+1))
        s.add(symbol_create_selection_box(0,-1,12,top+1))
        for names,x,direction in ((obj.inputs,0,"input"),(obj.outputs,12,"output")):
            for i,name in enumerate(names):
                y=top-i*1.2
                s.add(symbol_create_pin(name,x,y,direction=direction,
                    label_x=.8 if x==0 else 11.2,label_y=y,
                    label_height=.7,
                    label_justification="centerLeft" if x==0 else "centerRight"))
        s.add(symbol_create_instance_label(2,top+2,height=.9))
        s.add(symbol_create_logical_label(6,-2,height=.7))
        s.add(symbol_set_term_order(obj.inputs+obj.outputs))


def readback(c,obj):
    data=c.schematic.read(LIB,obj.name,include_positions=True,param_filters=None)
    marks=c.fetch(f'dbOpenCellViewByType("{LIB}" "{obj.name}" "schematic" "" "r")~>markers',
                  ["objType","severity","bBox"])
    dump(f"oa/{obj.name}.json",data);dump(f"oa/{obj.name}_markers.json",marks)
    actual={i["name"]:i for i in data["instances"]}
    assert set(actual)=={p.name for p in obj.parts},(obj.name,"instances")
    for p in obj.parts:
        a=actual[p.name]
        assert (a["lib"],a["cell"])==(p.lib,p.master),(obj.name,p.name,a)
        assert a["terms"]==p.terms,(obj.name,p.name,a["terms"],p.terms)
        for key,want in p.params.items():
            got=a["params"].get(key)
            def number(v):
                m=re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([a-zA-Z]*)",str(v))
                if not m:return None
                suffix=m[2].lower();scale={"":1,"t":1e12,"g":1e9,"meg":1e6,"k":1e3,"m":1e-3,"u":1e-6,"n":1e-9,"p":1e-12,"f":1e-15}.get(suffix)
                return None if scale is None else float(m[1])*scale
            x,y=number(want),number(got)
            ok=(x is not None and y is not None and math.isclose(x,y,rel_tol=1e-8,abs_tol=1e-24)) or str(want)==str(got)
            assert ok,(obj.name,p.name,key,want,got)
    pins=data["pins"]
    assert set(pins)==set(obj.inputs+obj.outputs),(obj.name,pins)
    if obj.inputs or obj.outputs:
        ports=c.symbol.read_ports(LIB,obj.name)
        assert set(t["name"] for t in ports["terms"])==set(obj.inputs+obj.outputs)
        dump(f"oa/{obj.name}_symbol.json",ports)
    if marks:raise RuntimeError(f"{obj.name}: check markers {marks}")
    print("OA_OK",obj.name,len(obj.parts),flush=True)
    return data


def build(c,obj,rebuild=False):
    if exists(c,obj.name):
        record=OUT/"owned"/(obj.name+".json")
        if not record.exists():raise RuntimeError(f"Existing unowned cell: {obj.name}")
        previous=json.loads(record.read_text(encoding="utf-8"))
        if rebuild:
            # Replacing an owned child symbol relocates its terminal artwork
            # before parent stubs are rebuilt. Audit live ownership/masters,
            # preserve the transient readback, then reconstruct parents in
            # dependency order and demand complete final connectivity.
            live=c.schematic.read(LIB,obj.name,include_positions=True,param_filters=None)
            actual={i["name"]:(i["lib"],i["cell"]) for i in live["instances"]}
            assert actual=={p["name"]:(p["lib"],p["master"]) for p in previous["parts"]}
            dump("before_rebuild/"+obj.name+"_live.json",live)
            for w in c.list_windows():
                if obj.name+" " in w["name"]:raise RuntimeError("Target GUI-open; refuse replacement")
            dump("before_rebuild/"+obj.name+".json",previous)
        elif previous!=dataclasses.asdict(obj):
            raise RuntimeError(f"Source differs from owned OA: {obj.name}; explicit repair required")
        else:
            readback(c,obj);return
    # A source ownership receipt is not evidence the creation succeeded.
    dump("owned/"+obj.name+".json",dataclasses.asdict(obj))
    with c.schematic.create(LIB,obj.name,timeout=240) as s:
        rows=max(1,(len(obj.parts)+3)//4)
        for direction,names,x in (("input",obj.inputs,-20),("output",obj.outputs,110)):
            for i,p in enumerate(names):s.add(pin(p,x,12-i*2,"R0" if direction=="input" else "R180",direction=direction))
        for i,p in enumerate(obj.parts):
            # Small leaf symbols use MOS terminal-aware stubs; hierarchy is spaced
            # generously so text/ports do not overlap neighbouring symbols.
            x=(i%4)*28;y=-(i//4)*(100 if obj.name.startswith("tb_") else 30)
            s.add(inst(p.lib,p.master,"symbol",p.name,x,y,"R0"))
            for t,n in p.terms.items():s.add(term(p.name,t,n))
    for p in obj.parts:
        if p.params:_run_batched_param_update(c,LIB,obj.name,p.name,p.params)
    with c.schematic.modify(LIB,obj.name,timeout=180):pass
    if obj.inputs or obj.outputs:symbol(c,obj)
    # Recheck after symbol interface changes to remove stale cross-view
    # terminal mismatch markers created before the new symbol existed.
    with c.schematic.modify(LIB,obj.name,timeout=180):pass
    readback(c,obj)


def preflight(c):
    info=c.library.get(LIB)
    assert info.path=="/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28",info
    assert info.technology_library=="tsmcN28",info
    windows=c.list_windows();dump("preflight_windows.json",windows)
    for w in windows:
        if "sar8a_" in w["name"] or "sar_logic_8b_async" in w["name"]:
            raise RuntimeError("Owned target already GUI-open; inspect locks/unsaved state first")
    dump("library.json",dataclasses.asdict(info))
    dump("dependency_strongarm_before.json",c.schematic.read(LIB,"sar_strongarm_t28",param_filters=None))
    print("PREFLIGHT_OK",info.path,info.technology_library,flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("command",choices=["preflight","leaves","controller","readback","check","symbols","markers","export"])
    ap.add_argument("--cell");ap.add_argument("--tag",default="primary")
    ap.add_argument("--rebuild-owned",action="store_true");args=ap.parse_args()
    c=VirtuosoClient.from_env(profile="t28_io");objects=hierarchy()
    if args.command=="check":
        import bench
        objects += [bench.gate_bench(),bench.logic_bench(),bench.logic_bench(True)]
    if args.command=="preflight":preflight(c);return
    if args.command=="markers":
        assert args.cell
        data=c.fetch(f'dbOpenCellViewByType("{LIB}" "{args.cell}" "schematic" "" "r")~>markers',
                     ["objType","severity","msg","message","reason","bBox"])
        print(json.dumps(data,indent=2));return
    if args.command=="export":
        assert args.cell
        folder=OUT/"exports"/args.cell/args.tag
        if (folder/"input.scs").exists():raise RuntimeError("Preserve previous export; use a new --tag")
        r=c.schematic.export_netlist(LIB,args.cell,folder,simulator="spectre",timeout=300)
        dump(f"exports/{args.cell}/{args.tag}/receipt.json",r)
        p=Path(r["input_file"]);assert p.exists()
        print("EXPORTED",p,hashlib.sha256(p.read_bytes()).hexdigest(),flush=True);return
    if args.command=="leaves":objects=[a for a in objects if a.name in {x.name for x in __import__("circuit").logic_cells()}]
    elif args.command=="controller":objects=objects[len(__import__("circuit").logic_cells()):]
    if args.cell:objects=[a for a in objects if a.name==args.cell]
    assert objects
    for o in objects:
        if args.command in ("readback","check"):
            if args.command=="check":
                with c.schematic.modify(LIB,o.name,timeout=180):pass
            readback(c,o)
        elif args.command=="symbols":
            assert (OUT/"owned"/(o.name+".json")).exists(),o.name
            symbol(c,o)
            # Symbol replacement invalidates cached instTerms even when
            # terminal coordinates are unchanged; refresh before readback.
            with c.schematic.modify(LIB,o.name,timeout=180):pass
            readback(c,o)
        else:build(c,o,rebuild=args.rebuild_owned)


if __name__=="__main__":main()
