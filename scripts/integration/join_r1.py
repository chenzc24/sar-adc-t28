"""New, owned OA R1 hierarchy; read-only frozen analog/native logic dependencies."""
from __future__ import annotations

import argparse
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_join_r1"
LIB = "SAR_ADC_T28"
TOP = "sar_adc8_join_r1"
TB = "tb_sar_adc8_join_r1"
ARRAY = "sar8j_r1_cdac"
GATE = "sar8j_r1_refgate"
VA = ROOT / f"models/veriloga/{GATE}.va"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
sys.path.insert(0, str(ROOT / "scripts/sar8_simple"))
from circuit import Cell, hierarchy
sys.path.insert(0, str(Path(__file__).parent))
from freeze_r0 import check as check_r0, read_json, schematic_surface, object_digest, blocks


def dump(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str)+"\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def skill(c, expr, timeout=60):
    r = c.execute_skill(expr, timeout=timeout)
    if r.errors: raise RuntimeError(r.errors)
    return r.output


def exists(c, cell, view=None):
    suffix = f' "{view}"' if view else ""
    return skill(c, f'ddGetObj("{LIB}" "{cell}"{suffix})').strip() not in ("nil", "")


def switches():
    objects = []
    for b in range(8):
        obj = Cell(f"sar8j_r1_sw_b{b}", ["GP", "GN", "VREFP", "VREFN", "VDD", "VSS"], ["BOT"])
        for name, model, gate, ref, body, w in (("MP_HIGH", "pch_mac", "GP", "VREFP", "VDD", "175n"),
                                               ("MN_LOW", "nch_mac", "GN", "VREFN", "VSS", "150n")):
            obj.add(name, model, {"D":"BOT", "G":gate, "S":ref, "B":body}, "tsmcN28",
                    Wfg=w, w=w, l="30n", fingers="1", simM=str(3*(1<<b)))
        objects.append(obj)
    return objects


def array():
    inputs = [f"G{s}{q}{b}" for s in "PN" for q in "PN" for b in range(8)]
    obj = Cell(ARRAY, inputs+["VREFP", "VREFN", "VDD", "VSS"], ["TOPP", "TOPN"])
    geo = dict(Wfinger="50n", Sfinger="50n", Lfinger="2u", Nfinger="8", StartMn="1", StopMn="3", mismatch="1")
    for s in "PN":
        for b in range(9):
            bot = f"B{s}{b}" if b < 8 else "VREF"+s
            obj.add(f"CMOM{s}{b}", "cfmom_2t", {"PLUS":"TOP"+s,"MINUS":bot}, "tsmcN28",
                    **geo, m=str((1<<b) if b < 8 else 1))
            if b < 8:
                obj.add(f"XS{s}{b}", f"sar8j_r1_sw_b{b}", {"GP":f"G{s}P{b}", "GN":f"G{s}N{b}",
                        "VREFP":"VREFP", "VREFN":"VREFN", "VDD":"VDD", "VSS":"VSS", "BOT":bot})
    return obj


def top():
    # Native Bootstrap contains inherited VDD!/gnd!, so the unique joint top
    # exposes those SAME global rails instead of leaving an unrelated VDD port.
    obj = Cell(TOP, ["SAMPLE", "VINP", "VINN", "VREFP", "VREFN", "VDD!", "gnd!"],
               [f"D{b}" for b in range(7,-1,-1)]+["CMP_CLK", "COMP_P", "COMP_N", "TOPP", "TOPN"])
    power = {"VDD":"VDD!", "VSS":"gnd!"}
    for s in "PN":
        obj.add("XBOOT"+s, "sar_bootstrap_canvas_flat_8b", {"CLKS":"SAMPLE", "CLKSB":"CLKB"+s,
                "Vin":"VIN"+s, "VOUT":"TOP"+s})
        obj.add("RMCLK"+s, "res", {"PLUS":"CLKB"+s,"MINUS":"gnd!"}, "analogLib", r="1T")
    obj.add("XCDAC", ARRAY, {p:power.get(p,p) for p in array().inputs+array().outputs})
    ctrl = hierarchy()[-1]
    obj.add("XCTRL", ctrl.name, {p:power.get(p,p) for p in ctrl.inputs+ctrl.outputs})
    obj.add("XCOMP", "sar_strongarm_t28", {"CLK":"CMP_CLK","VINP":"TOPP","VINN":"TOPN",
            "OUTP":"COMP_P","OUTN":"COMP_N", **power})
    for s in "PN":
        # Cross-map request banks; DO NOT swap analog inputs/comparator polarity.
        bank = "N" if s == "P" else "P"
        midpoint = 127 if s == "P" else 128
        for b in range(8):
            obj.add(f"XG{s}{b}", GATE, {"SAMPLE":"SAMPLE", "EH":f"B{bank}_H{b}", "EL":f"B{bank}_L{b}",
                    **power, "GP":f"G{s}P{b}", "GN":f"G{s}N{b}"}, initial_high=str((midpoint>>b)&1))
    for net in ctrl.outputs+["COMP_P", "COMP_N", "TOPP", "TOPN"]:
        # Tiny DC monitor conductance avoids dangling observation nets, and
        # preserves the already tested explicit native output loads.
        obj.add("RM_"+net, "res", {"PLUS":net,"MINUS":"gnd!"}, "analogLib", r="1T")
        if net.startswith(("BP_", "BN_", "D")) or net in ("CMP_CLK","COMP_P","COMP_N"):
            obj.add("CL_"+net, "cap", {"PLUS":net,"MINUS":"gnd!"}, "analogLib",
                    c="5f" if net.startswith("D") else "10f")
    return obj


def bench():
    obj = Cell(TB, [], [])
    obj.add("XDUT", TOP, {p:p for p in top().inputs+top().outputs})
    for name, net, dc in (("VVDD","VDD!","SUP"), ("VREFHIGH","VREFP_SRC","SUP"),
                           ("VREFLOW","VREFN_SRC","0"), ("VVINP","VINP_SRC",".45+VDIFF/2"),
                           ("VVINN","VINN_SRC",".45-VDIFF/2")):
        obj.add(name,"vdc",{"PLUS":net,"MINUS":"gnd!"},"analogLib",vdc=dc)
    obj.add("VSAMPLE","vpulse",{"PLUS":"SAMPLE","MINUS":"gnd!"},"analogLib",
            v1="0",v2="SUP",td="1n",pw="39.9n",per="100n",tr="100p",tf="100p")
    for s in "PN":
        obj.add("RIN"+s,"res",{"PLUS":"VIN"+s+"_SRC","MINUS":"VIN"+s},"analogLib",r="50")
        obj.add("RREF"+s,"res",{"PLUS":"VREF"+s+"_SRC","MINUS":"VREF"+s},"analogLib",r="50")
        obj.add("CREF"+s,"cap",{"PLUS":"VREF"+s,"MINUS":"gnd!"},"analogLib",c="4p")
    for p in top().outputs:
        obj.add("ROBS_"+p,"res",{"PLUS":p,"MINUS":"gnd!"},"analogLib",r="1T")
    return obj


def objects():
    return switches()+[array(), top(), bench()]


def preflight(c, after=False):
    check_r0()
    info = c.library.get(LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and info.technology_library == "tsmcN28", info
    windows = c.list_windows()
    dump("preflight"+("_after" if after else "")+".json", dict(library=dataclasses.asdict(info), windows=windows,
         time_utc=datetime.now(timezone.utc).isoformat()))
    lock = read_json(ROOT/"verification/integration/join_r0_sources.json")
    for name, record in lock["live_readback"]["cells"].items():
        data = c.schematic.read(LIB,name,include_positions=False)
        assert object_digest(schematic_surface(data)) == record["surface_sha256"], "Frozen source changed: "+name
        dump(f"dependencies{'_after' if after else ''}/{name}.json", data)
    if not after:
        for name in [o.name for o in objects()]+[GATE]:
            for w in windows:
                assert name+" " not in w["name"], "New target GUI-open: "+name
            if exists(c,name):
                assert (OUT/f"owned/{name}.json").exists(), "Existing unowned target: "+name
    print("PREFLIGHT_MATCH_23_UNCHANGED", flush=True)


def make_symbol(c, obj, passive=False):
    from virtuoso_bridge.virtuoso.symbol.ops import (symbol_create_rect, symbol_create_selection_box,
        symbol_create_pin, symbol_create_instance_label, symbol_create_logical_label, symbol_set_term_order)
    h=max(len(obj.inputs),len(obj.outputs))*.8+1
    with c.symbol.create(LIB,obj.name,timeout=180) as s:
        s.add(symbol_create_rect("device","drawing",.75,-.5,11.25,h))
        s.add(symbol_create_selection_box(0,-.75,12,h+.25))
        for names,x,lx,direction,just in ((obj.inputs,0,.9,"input","centerLeft"),
            (obj.outputs,12,11.1,"inputOutput" if passive else "output","centerRight")):
            for j,n in enumerate(names):
                y=h-.5-j*.8
                s.add(symbol_create_pin(n,x,y,direction=direction,label_x=lx,label_y=y,
                                       label_height=.35,label_justification=just))
        s.add(symbol_create_instance_label(2,h+.5,height=.6))
        s.add(symbol_create_logical_label(6,-1.2,height=.4))
        s.add(symbol_set_term_order(obj.inputs+obj.outputs))


def set_params(c, obj):
    from types import SimpleNamespace
    from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update
    class Queue:
        def __init__(self): self.expressions=[]
        def execute_skill(self,expr,timeout=30):
            self.expressions.append(expr)
            return SimpleNamespace(errors=[])
    queue=Queue()
    for p in obj.parts:
        if p.params: _run_batched_param_update(queue,LIB,obj.name,p.name,p.params)
    for i in range(0,len(queue.expressions),8):
        skill(c,"progn("+" ".join(queue.expressions[i:i+8])+")",timeout=180)


def readback(c, obj):
    data = c.schematic.read(LIB,obj.name,include_positions=True,param_filters=None)
    marks = c.fetch(f'dbOpenCellViewByType("{LIB}" "{obj.name}" "schematic" "" "r")~>markers',
                    ["objType","severity","bBox"])
    dump(f"oa/{obj.name}.json",data); dump(f"oa/{obj.name}_markers.json",marks)
    assert not marks,(obj.name,marks)
    actual={p["name"]:p for p in data["instances"]}
    assert set(actual)=={p.name for p in obj.parts},obj.name
    for p in obj.parts:
        a=actual[p.name]
        assert (a["lib"],a["cell"],a["terms"])==(p.lib,p.master,p.terms),(obj.name,p.name,a["terms"],p.terms)
        from freeze_r0 import number_or_expression
        for k,want in p.params.items():
            got=a["params"].get(k)
            assert number_or_expression(want)==number_or_expression(got),(obj.name,p.name,k,want,got)
    assert set(data["pins"])==set(obj.inputs+obj.outputs),(obj.name,data["pins"])
    print("OA_OK",obj.name,len(obj.parts),flush=True)
    return data


def build(c, obj):
    from virtuoso_bridge.virtuoso.schematic.ops import (schematic_create_inst_by_master_name as inst,
        schematic_create_pin as pin, schematic_label_instance_term as term)
    record=OUT/f"owned/{obj.name}.json"
    if exists(c,obj.name):
        assert record.exists() and read_json(record)==json.loads(json.dumps(dataclasses.asdict(obj)))
        if (OUT/f"owned_complete/{obj.name}.json").exists():return readback(c,obj)
        assert not any(obj.name+" " in w["name"] for w in c.list_windows()),"Partial owned target is GUI-open"
        dump(f"partial_before_retry/{obj.name}.json",c.schematic.read(LIB,obj.name,include_positions=True))
    dump(f"owned/{obj.name}.json",dataclasses.asdict(obj))
    passive=obj.name==ARRAY or obj.name.startswith("sar8j_r1_sw_")
    with c.schematic.create(LIB,obj.name,timeout=240) as s:
        for names,x,direction in ((obj.inputs,-20,"input"),(obj.outputs,230,"inputOutput" if passive else "output")):
            for j,n in enumerate(names):s.add(pin(n,x,25-j*1.5,"R0",direction=direction))
    # IC618 has a finite literal stack: submit bounded edit functions, not one
    # several-hundred-terminal generated function. Intermediate check markers
    # are expected while the new owned schematic is being populated; final
    # readback below demands zero markers and exact complete connectivity.
    for start in range(0,len(obj.parts),12):
      with c.schematic.modify(LIB,obj.name,timeout=240) as s:
        for i in range(start,min(start+12,len(obj.parts))):
            p=obj.parts[i]
            if obj.name==ARRAY:
                side="P" if "P" in p.name else "N"
                b=int(p.name[-1]); x=b*20; y=20 if side=="P" else -30
                if p.name.startswith("XS"):y-=15
            elif obj.name.startswith("sar8j_r1_sw_"):
                x=0 if i==0 else 12;y=0
            elif obj.name==TOP:
                positions={"XBOOTP":(0,35),"XBOOTN":(0,10),"XCDAC":(40,0),
                           "XCOMP":(70,15),"XCTRL":(110,-5)}
                x,y=positions.get(p.name,((i%8)*30,-80-(i//8)*16))
            else:x=(i%6)*35;y=-(i//6)*50
            s.add(inst(p.lib,p.master,"symbol",p.name,x,y,"R0"))
            if p.lib=="tsmcN28" and p.master in ("pch_mac","nch_mac"):
                s.add_net_label_to_transistor(p.name,drain_net=p.terms["D"],gate_net=p.terms["G"],
                                            source_net=p.terms["S"],body_net=p.terms["B"])
            else:
                for t,n in p.terms.items():s.add(term(p.name,t,n))
    set_params(c,obj)
    if obj.inputs or obj.outputs:make_symbol(c,obj,passive)
    with c.schematic.modify(LIB,obj.name,timeout=180):pass
    data=readback(c,obj)
    dump(f"owned_complete/{obj.name}.json",dict(complete=True))
    return data


def import_gate(c):
    if exists(c,GATE):
        assert read_json(OUT/f"owned/{GATE}.json")["sha256"]==sha(VA)
        if exists(c,GATE,"veriloga"):
            target=OUT/"gate_remote_readback.va"
            r=c.download_file(f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{GATE}/veriloga/veriloga.va",target)
            assert r.ok and sha(target)==sha(VA)
            if read_json(OUT/f"owned/{GATE}.json").get("completed"):return
    else:
        dump(f"owned/{GATE}.json",dict(sha256=sha(VA)))
        obj=Cell(GATE,["SAMPLE","EH","EL","VDD","VSS"],["GP","GN"])
        make_symbol(c,obj)
    # Explicit destination is required by this IC618 session; nil/nil fails
    # before skeleton creation. This is the already-used project import path.
    if not exists(c,GATE,"veriloga"):
        skill(c,f'schViewToView("{LIB}" "{GATE}" "{LIB}" "{GATE}" "symbol" "veriloga" "schSymbolToPinList" "ahdlPinListToveriloga")')
    target=f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{GATE}/veriloga/veriloga.va"
    result=c.upload_file(VA,target);assert result.ok,result.errors
    skill(c,f'ahdlUpdateViewInfo("{LIB}" ?cell "{GATE}" ?view "veriloga")')
    # Only this per-bank initial polarity is instance-specific; timing is frozen
    # in the versioned VA defaults. No native-controller state is introduced.
    skill(c,f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "{GATE}")) unless(d d=cdfCreateBaseCellCDF(ddGetObj("{LIB}" "{GATE}"))) cdfCreateParam(d ?name "initial_high" ?prompt "initial_high" ?type "string" ?defValue "0" ?parseAsNumber "yes" ?parseAsCEL "yes") cdfSaveCDF(d))')
    dump("oa/"+GATE+"_symbol.json",c.symbol.read_ports(LIB,GATE))
    dump(f"owned/{GATE}.json",dict(sha256=sha(VA),completed=True))
    print("IMPORTED_GATE",sha(VA),flush=True)


def audit_export(text):
    old=read_json(ROOT/"verification/integration/join_r0_sources.json")
    defs=blocks(text)
    for name,digest in old["native_controller_subckt_sha256"].items():
        assert hashlib.sha256(defs[name].encode()).hexdigest()==digest,"Native controller changed: "+name
    assert hashlib.sha256(defs["sar_strongarm_t28"].encode()).hexdigest()==old["comparator_subckt_sha256"]
    assert hashlib.sha256(defs["sar_bootstrap_canvas_flat_8b"].encode()).hexdigest()==old["analog_subckt_sha256"]["sar_bootstrap_canvas_flat_8b"]
    assert "sar8a_plant" not in text and "cdac8_dualrail_controller" not in text
    rows=[]
    # Compare every pass MOS instance line, including CDF-generated geometry,
    # while normalizing the explicit new gate terminal names/multiplicity.
    frozen=blocks((ROOT/"output/cdac8_uniform_scale/decks/control_m3.scs").read_text())
    def line(body,name):
        return re.search(rf"\b{name} \((.*?)\) (\w+) (.*?)(?= \w+ \(|$)",body).groups()
    for b in range(8):
        body=defs[f"sar8j_r1_sw_b{b}"]
        assert len(re.findall(r"\b(?:nch_mac|pch_mac)\b",body))==2
        for name,gate in (("MP_HIGH","GP"),("MN_LOW","GN")):
            ports,model,params=line(body,name)
            priorports,priormodel,priorparams=line(frozen[f"cdac8_dr_sw_b{b}"],name)
            assert model==priormodel and ports.split()==["BOT",gate,"VREFP" if gate=="GP" else "VREFN","VDD" if gate=="GP" else "VSS"]
            # Compare parsed params, not whitespace/order generated by CDF.
            a=dict(re.findall(r"(\w+)=([^ ]+)",params));p=dict(re.findall(r"(\w+)=([^ ]+)",priorparams))
            p["multi"]=str(3*(1<<b))
            from freeze_r0 import number_or_expression
            assert {k:number_or_expression(v) for k,v in a.items()}=={k:number_or_expression(v) for k,v in p.items()},(name,b,a,p)
        rows.append(dict(cell=f"sar8j_r1_sw_b{b}",pass_MOS=2,multiplicity=3*(1<<b)))
    assert len(re.findall(r"\bcfmom_2t\b",defs[ARRAY]))==18
    return dict(frozen_native_cells_matched=23,reference_leaves=rows,nominal_MOM_declarations=18,
                ideal_DAC_plant_absent=True,subckt_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in defs.items()})


def main():
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["preflight","build","readback","export","postflight","open"])
    ap.add_argument("--cell");ap.add_argument("--tag",default="primary")
    ap.add_argument("--zoom",nargs=4,type=float);args=ap.parse_args()
    from virtuoso_bridge import VirtuosoClient
    c=VirtuosoClient.from_env(profile="t28_io",timeout=30,log_to_ciw=False)
    if args.action in ("preflight","postflight"):return preflight(c,args.action=="postflight")
    if args.action=="build":
        preflight(c)
        import_gate(c)
        for obj in objects():build(c,obj)
    elif args.action=="readback":
        path=OUT/"gate_final_readback.va"
        result=c.download_file(f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{GATE}/veriloga/veriloga.va",path)
        assert result.ok and sha(path)==sha(VA),"Gate VA differs from frozen source"
        for obj in objects():
            if not args.cell or obj.name==args.cell:readback(c,obj)
    elif args.action=="export":
        folder=OUT/"exports"/args.tag
        assert not (folder/"input.scs").exists(),"Use a fresh export tag"
        readback(c,bench())
        result=c.schematic.export_netlist(LIB,TB,folder,simulator="spectre",timeout=300)
        dump(f"exports/{args.tag}/receipt.json",result)
        path=Path(result["input_file"]);assert path.exists()
        audit=audit_export(path.read_text(encoding="utf-8"));audit["export_sha256"]=sha(path)
        dump(f"exports/{args.tag}/audit.json",audit)
        print("EXPORTED_AUDITED",path,flush=True)
    elif args.action=="open":
        cell=args.cell or TOP
        assert cell in {TOP,TB,ARRAY}
        result=c.open_window(LIB,cell,view="schematic");assert not result.errors,result.errors
        if args.zoom:
            # Same IC618-verified hiZoomIn signature as sar8_simple/oa.py.
            wins=[w for w in c.list_windows() if f"{LIB} {cell} schematic" in w["name"]]
            assert len(wins)==1,wins
            x0,y0,x1,y1=args.zoom;assert x1>x0 and y1>y0
            skill(c,f'hiZoomIn(window({int(wins[0]["num"])}) list({x0}:{y0} {x1}:{y1}))')
            skill(c,f'hiRedraw(window({int(wins[0]["num"])}))')


if __name__=="__main__":main()
