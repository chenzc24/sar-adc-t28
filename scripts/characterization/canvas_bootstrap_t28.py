"""Build and size the user's bootstrap with native tsmcN28 devices."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_create_pin as pin,
    schematic_create_wire as wire,
    schematic_create_wire_label as wire_label,
    schematic_label_instance_term as label_term,
)
from virtuoso_bridge.virtuoso.schematic.params import set_instance_params, _run_batched_param_update
from virtuoso_bridge.virtuoso.schematic.reader import read_placement
from virtuoso_bridge.spectre import SpectreSimulator
from virtuoso_bridge.spectre.runner import spectre_mode_args
import hashlib
import re
import bisect
import contextlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/canvas_bootstrap_t28"
SOURCE = ROOT / "config/canvas_bootstrap_topology.json"
LIB, DUT, TB = "SAR_ADC_T28", "sar_bootstrap_canvas_t28", "tb_bootstrap_canvas_t28"
SCALE = 0.009375
MOS = ["Mmain", "M4C", "M2", "Msin", "M4", "Maux", "MRSTG", "M4A", "M8", "M4B"]
SOURCE_NAMES = {"M1": "Mmain", "M10": "M4C", "M2": "M2", "M3": "Msin", "M4": "M4", "M5": "Maux", "M6": "MRSTG", "M7": "M4A", "M8": "M8", "M9": "M4B"}
PORTS = ("Vin", "CLKS", "CLKSB", "VOUT")
NET_NAMES = {
    "net-190f0079ed5a2473":"CTRL", "net-26eb61a1ffd0bda6":"VOUT",
    "net-512fd7583d323dcf":"G", "net-be9d406673ff8cf5":"BBOT",
    "net-cell-pin-p1":"Vin", "net-cell-pin-p2-2":"CLKS",
    "net-cell-pin-p3":"CLKSB", "net-e149e4cee5c7b299":"GRESET",
    "net-power-gnd1":"gnd!", "net-power-vdd1":"VDD!", "net-ui-3":"BTOP",
}
ORIENTS = {
    "R0":(1,0,0,1), "R90":(0,-1,1,0), "R180":(-1,0,0,-1),
    "R270":(0,1,-1,0), "MX":(1,0,0,-1), "MY":(-1,0,0,1),
    "MXR90":(0,1,1,0), "MYR90":(0,-1,-1,0),
}


def orientation(src):
    origin=src["placement"]["position"]
    for name in ORIENTS:
        good=True
        for pin_data in src["pins"]:
            if pin_data["name"]=="B": continue
            local=pin_data["localPosition"]
            x,y=transform(name,(local["x"],-local["y"]))
            cp=pin_data["connection"]["contactPoint"]
            good &= abs(x-cp["x"]+origin["x"])<1e-5 and abs(y+cp["y"]-origin["y"])<1e-5
        if good: return name
    raise ValueError(f"No native orientation for {src['id']}")


def dump(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/name).write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def p(x, y):
    return round((x-180)*SCALE, 7), round((610-y)*SCALE, 7)


def transform(orient, xy):
    a,b,c,d=ORIENTS[orient]
    return a*xy[0]+b*xy[1], c*xy[0]+d*xy[1]


def exists(client, cell):
    r=client.execute_skill(f'ddGetObj("{LIB}" "{cell}")')
    if r.errors:
        raise RuntimeError(str(r))
    return (r.output or "").strip() not in ("", "nil")


def create(client):
    assert not exists(client,DUT) and not exists(client,TB), "Refuse existing targets"
    info=client.library.get(LIB)
    assert info.technology_library == "tsmcN28", info
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    ports={f"tsmcN28/{name}":client.symbol.read_ports("tsmcN28",name)
           for name in ("nch_18_mac","pch_18_mac")}
    placements={}
    with client.schematic.create(LIB,DUT,timeout=180) as sch:
        for src in source["instances"]:
            if src["symbolId"] not in ("nmos","pmos"):
                continue
            name=SOURCE_NAMES[src["id"]]
            model="nch_18_mac" if src["symbolId"]=="nmos" else "pch_18_mac"
            orient=orientation(src)
            gate=next(x for x in src["pins"] if x["name"]=="G")["connection"]["contactPoint"]
            origin=p(gate["x"],gate["y"])
            sch.add(inst("tsmcN28",model,"symbol",name,*origin,orient))
            actual={}
            native={x["name"]: ((x["bbox"][0][0]+x["bbox"][1][0])/2,
                                  (x["bbox"][0][1]+x["bbox"][1][1])/2)
                    for x in ports["tsmcN28/"+model]["terms"]}
            for term in ("D","G","S"):
                off=transform(orient,native[term])
                a=(round(origin[0]+off[0],7),round(origin[1]+off[1],7))
                contact=next(x for x in src["pins"] if x["name"]==term)["connection"]["contactPoint"]
                b=p(contact["x"],contact["y"])
                actual[term]=a
                if abs(a[0]-b[0])+abs(a[1]-b[1])>1e-6:
                    corner=(b[0],a[1])
                    for q,r in ((a,corner),(corner,b)):
                        if q!=r: sch.add(wire([q,r]))
            body=next(x for x in src["pins"] if x["name"]=="B")
            sch.add(label_term(name,"B",NET_NAMES[body["netId"]]))
            placements[name]={"master":model,"origin":origin,"orient":orient,"pins":actual}
        for name,x,y in (("Cboot",460,350),("Cs",700,520)):
            sch.add(inst("analogLib","cap","symbol",name,*p(x,y-20),"R0"))
        for route in source["routes"]:
            if route["id"] in {"route-ui-57","route-ui-59","route-ui-71","route-ui-73"}:
                continue
            pts=[p(x["x"],x["y"]) for x in route["polyline"]]
            for a,b in zip(pts,pts[1:]): sch.add(wire([a,b]))
        for net in source["nets"]:
            routes=[r for r in source["routes"] if r["netId"]==net["id"]]
            if routes:
                at=routes[0]["polyline"][0]
                sch.add(wire_label(*p(at["x"],at["y"]),NET_NAMES[net["id"]],"lowerLeft","R0",height=0.05))
        for x,y,name in ((320,450,"CLKSB"),(720,210,"CLKSB"),(770,260,"gnd!"),(360,490,"gnd!"),(700,550,"gnd!")):
            sch.add(wire_label(*p(x,y),name,"lowerLeft","R0",height=0.05))
        for name,x,y,orient,direction in (("Vin",460,550,"R90","inputOutput"),("CLKS",300,300,"R0","input"),("CLKSB",720,210,"R270","output"),("VOUT",700,500,"R180","output")):
            sch.add(pin(name,*p(x,y),orient,direction=direction))
        # Physical complementary inverter in the same schematic.
        sch.add(inst("tsmcN28","pch_18_mac","symbol","MPCLK",0.4,-0.1,"R0"))
        sch.add(inst("tsmcN28","nch_18_mac","symbol","MNCLK",0.4,-0.9,"R0"))
        sch.add_net_label_to_transistor("MPCLK",drain_net="CLKSB",gate_net="CLKS",source_net="VDD!",body_net="VDD!")
        sch.add_net_label_to_transistor("MNCLK",drain_net="CLKSB",gate_net="CLKS",source_net="gnd!",body_net="gnd!")
    client.open_window(LIB,DUT,view="schematic")
    for name in MOS+["MPCLK","MNCLK"]:
        set_instance_params(client,name,w="1u",l="150n",nf="1",m="1",param_filters=None,strict=True)
    for name in ("Cboot","Cs"):
        set_instance_params(client,name,c="1p",param_filters=None,strict=True)
    with client.schematic.modify(LIB,DUT): pass
    dump("placements.json",placements)
    readback(client)


def readback(client):
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    data=client.schematic.read(LIB,DUT,include_positions=True,param_filters=None)
    dump("native_readback.json",data)
    dump("native_placement.json",read_placement(client,LIB,DUT))
    got={x["name"]:x for x in data["instances"]}
    bad=[]
    for src in source["instances"]:
        if src["id"] not in SOURCE_NAMES: continue
        name=SOURCE_NAMES[src["id"]]
        for term in src["pins"]:
            want=NET_NAMES[term["netId"]]
            actual=got[name]["terms"].get(term["name"])
            if actual!=want: bad.append([name,term["name"],want,actual])
    extra={"MPCLK":{"D":"CLKSB","G":"CLKS","S":"VDD!","B":"VDD!"},
           "MNCLK":{"D":"CLKSB","G":"CLKS","S":"gnd!","B":"gnd!"},
           "Cboot":{"PLUS":"BTOP","MINUS":"BBOT"},
           "Cs":{"PLUS":"VOUT","MINUS":"gnd!"}}
    for name,terms in extra.items():
        for term,want in terms.items():
            actual=got[name]["terms"].get(term)
            if actual!=want:bad.append([name,term,want,actual])
    assert all(x["lib"] in {"tsmcN28","analogLib"} for x in got.values())
    assert sum(x["lib"]=="tsmcN28" for x in got.values())==12
    dump("topology_verification.json",{"native_mos_count":sum(x["lib"]=="tsmcN28" for x in got.values()),"mismatches":bad})
    print("TOPOLOGY",json.dumps(bad),flush=True)
    assert not bad, "Inspect topology mismatches before running"


def create_testbench(client):
    client.symbol.generate_from_schematic(LIB,DUT,overwrite=False,timeout=90)
    with client.schematic.create(LIB,TB) as sch:
        sch.add(inst(LIB,DUT,"symbol","XBOOT",0,0,"R0"))
        for port in PORTS:
            sch.add(label_term("XBOOT",port,port))
        for name,master,x,y,a,b in (
            ("VVDD","vdc",-4,3,"VDD!","gnd!"),
            ("VCLK","vpulse",-4,0,"CLKS","gnd!"),
            ("VVIN","vpulse",-4,-3,"VIN_SRC","gnd!"),
            ("RIN","res",-1,-3,"VIN_SRC","Vin"),
        ):
            sch.add(inst("analogLib",master,"symbol",name,x,y,"R0"))
            sch.add(label_term(name,"PLUS",a))
            sch.add(label_term(name,"MINUS",b))
    client.open_window(LIB,TB,view="schematic")
    for name,params in (
        ("VVDD",{"vdc":"900m"}),
        ("VCLK",{"v1":"0","v2":"900m","td":"11n","tr":"100p","tf":"100p","pw":"39n","per":"100n"}),
        ("VVIN",{"v1":"0.9-VIN_DC","v2":"VIN_DC","td":"205n","tr":"100p","tf":"100p","pw":"80n","per":"400n"}),
        ("RIN",{"r":"50"}),
    ):
        set_instance_params(client,name,**params,param_filters=None,strict=True)
    with client.schematic.modify(LIB,TB): pass
    dump("testbench_readback.json",client.schematic.read(LIB,TB,param_filters=None))
    export(client,"baseline")


def export(client,name):
    path=OUT/"oa_netlists"/name
    result=client.schematic.export_netlist(LIB,TB,path,simulator="spectre",timeout=180)
    print("EXPORTED",name,result["input_file"],flush=True)
    dump(name+"_export.json",result)
    return Path(result["input_file"])


def signal(data,name):
    return next(v for k,v in data.items() if k.strip('"').lower()==name.lower())


def interpolate(t,v,x):
    i=max(1,min(bisect.bisect_left(t,x),len(t)-1))
    f=(x-t[i-1])/(t[i]-t[i-1]) if t[i]!=t[i-1] else 0
    return v[i-1]+f*(v[i]-v[i-1])


def run_cases(name,inputs=(0.05,0.45,0.85)):
    exported=OUT/"oa_netlists"/name/"input.scs"
    source=exported.read_text(encoding="utf-8")
    cfg=ROOT/"config/pdk_mapping.yaml"
    import yaml
    mapping=yaml.safe_load(cfg.read_text())
    model=mapping["virtuoso_netlisted_model_include"]
    prefix="" if "section=ttmacro_mos_moscap" in source else "simulator lang=spectre\n"+"\n".join(f'include "{model}" section={sec}' for sec in mapping["virtuoso_netlisted_sections"])+"\n"
    analysis=("\ntran tran stop=285n maxstep=10p errpreset=conservative\n"
              "save CLKS CLKSB Vin VOUT XBOOT.G XBOOT.BTOP XBOOT.BBOT XBOOT.CTRL XBOOT.GRESET\n"
              "save XBOOT.Mmain:currents XBOOT.Msin:currents\n"
              )
    decks=[]
    for vin in inputs:
        dest=OUT/"decks"/f"{name}_v{round(vin*1000):03d}.scs"
        dest.parent.mkdir(parents=True,exist_ok=True)
        parameterized=re.sub(r'^parameters VIN_DC\s*$',f'parameters VIN_DC={vin:.6g}',source,count=1,flags=re.MULTILINE)
        assert parameterized!=source, "Expected one OA design-variable declaration"
        for a,b in (("reltol=1e-4","reltol=1e-5"),("vabstol=1e-6","vabstol=1e-7"),("iabstol=1e-12","iabstol=1e-13"),("save=allpub","save=selected")):
            parameterized=parameterized.replace(a,b)
        dest.write_text(prefix+parameterized+analysis,encoding="utf-8")
        decks.append((dest,{}))
    sim=SpectreSimulator.from_env(profile="t28_io",work_dir=str(OUT/"spectre"),timeout=600,
                                  spectre_args=spectre_mode_args("spectre"))
    with (OUT/f"{name}_runner.log").open("w",encoding="utf-8") as log:
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            results=sim.run_parallel(decks,max_workers=3)
    rows=[]
    for vin,(deck,_),result in zip(inputs,decks,results):
        row={"candidate":name,"vin_v":vin,"ok":result.ok,"errors":result.errors,"metadata":result.metadata,
             "oa_sha256":hashlib.sha256(source.encode()).hexdigest()}
        if result.ok:
            data=result.data
            t=signal(data,"time")
            traces={key:signal(data,key) for key in ("CLKS","CLKSB","Vin","VOUT","XBOOT.G","XBOOT.BTOP","XBOOT.BBOT","XBOOT.CTRL","XBOOT.GRESET")}
            at=lambda key,x:interpolate(t,traces[key],x*1e-9)
            row.update(acquisition_error_mv=1000*(at("VOUT",249.9)-vin),
                       held_error_mv=1000*(at("VOUT",270)-vin),
                       hold_drift_mv=1000*(at("VOUT",280)-at("VOUT",260)),
                       vgs_track_v=at("XBOOT.G",249.9)-at("Vin",249.9),
                       boot_charge_v=at("XBOOT.BTOP",210)-at("XBOOT.BBOT",210),
                       gate_peak_v=max(traces["XBOOT.G"]))
            row["ron_215_ohm"]=None
            try:
                current=signal(data,"XBOOT.Mmain:1")
                i=interpolate(t,current,215e-9)
                if abs(i)>1e-10:
                    row["ron_215_ohm"]=abs((at("Vin",215)-at("VOUT",215))/i)
            except StopIteration: pass
            acquire=[i for i,ti in enumerate(t) if 211.2e-9<=ti<=249.9e-9]
            bad=[i for i in acquire if abs(traces["VOUT"][i]-vin)>0.000439]
            row["settling_from_211p2_ns"]=(t[bad[-1]]-211.2e-9)*1e9 if bad else 0.0
            dump(f"{deck.stem}_waveform.json",{"time":t,**traces})
        dump(deck.stem+"_result.json",row)
        rows.append(row)
        print("RESULT",name,vin,"ok",result.ok,"acq",row.get("acquisition_error_mv"),"hold",row.get("held_error_mv"),flush=True)
    dump(name+"_summary.json",rows)
    return rows


def apply_sizes(client,widths,cboot="1p"):
    # Named-cell bridge updater avoids the foreground-window dependency of
    # set_instance_params when both the DUT and testbench are already open.
    for name,width in widths.items():
        _run_batched_param_update(client,LIB,DUT,name,{"w":width,"l":"150n","fingers":"1","m":"1"})
    _run_batched_param_update(client,LIB,DUT,"Cboot",{"c":cboot})
    with client.schematic.modify(LIB,DUT): pass


def screen(client):
    candidates=[
        ("main_500n",{"Mmain":"500n"},"1p"),
        ("main_320n",{"Mmain":"320n"},"1p"),
        ("main_320n_reset_2u",{"Mmain":"320n","M8":"2u","MRSTG":"2u","Maux":"2u"},"1p"),
    ]
    all_rows=[]
    for name,widths,cb in candidates:
        print("SIZING",name,flush=True)
        all_widths={device:"1u" for device in MOS+["MPCLK","MNCLK"]}
        all_widths.update(widths)
        apply_sizes(client,all_widths,cb)
        readback(client)
        dump(name+"_sizes.json",client.schematic.read(LIB,DUT,param_filters=None))
        export(client,name)
        rows=run_cases(name)
        all_rows.extend(rows)
        dump("sizing_summary.json",all_rows)
        assert all(r["ok"] for r in rows), "Stop on simulator failure"


def finalize(client):
    widths={name:"1u" for name in MOS+["MPCLK","MNCLK"]}
    widths["Mmain"]="500n"
    apply_sizes(client,widths)
    readback(client)
    dump("selected_sizes.json",client.schematic.read(LIB,DUT,param_filters=None))
    export(client,"selected")
    run_cases("selected",(0.05,0.25,0.45,0.65,0.85))
    inspect_native(client)


def inspect_native(client):
    client.open_window(LIB,DUT,view="schematic")
    windows=client.list_windows()
    dump("windows.json",windows)
    target=next(w for w in windows if f" {DUT} schematic" in (w.get("name") or ""))
    wid=int(target["num"])
    r=client.execute_skill(f'hiZoomIn(window({wid}) list(list(-0.6 -1.5) list(6.2 4.6)))')
    if r.errors: raise RuntimeError(str(r))
    client.execute_skill(f'hiRedraw(window({wid}))')
    image=client.screenshot(OUT/"native_schematic.png",target=wid)
    print("SCHEMATIC_IMAGE",image.output,flush=True)
    cv=f'dbOpenCellViewByType("{LIB}" "{DUT}" "schematic" "" "r")'
    markers=client.fetch(cv+'~>markers',["objType","severity","reason","bBox"])
    dump("check_markers.json",markers)
    print("MARKERS",json.dumps(markers),flush=True)
    assert not markers,"Native schematic must have zero Check & Save markers"


def cleanup_clock_fragments(client):
    # These two disconnected segments belonged to the removed ideal inverter.
    # The physical inverter has its own CLKS/CLKSB wiring below the DUT.
    expr=(f'let((cv count) cv=dbOpenCellViewByType("{LIB}" "{DUT}" "schematic" "schematic" "a") '
          'count=0 foreach(shape cv~>shapes when(shape~>objType=="line" && '
          'length(shape~>points)==2 && abs(yCoord(car(shape~>points))-0.28125)<1e-6 && '
          'abs(yCoord(cadr(shape~>points))-0.28125)<1e-6 && '
          'abs(abs(xCoord(car(shape~>points))-xCoord(cadr(shape~>points)))-0.28125)<1e-6 '
          'dbDeleteObject(shape) count=count+1)) '
          'schCheck(cv) dbSave(cv) count)')
    r=client.execute_skill(expr)
    if r.errors: raise RuntimeError(str(r))
    print("REMOVED_UNUSED_SEGMENTS",r.output,flush=True)
    readback(client)
    inspect_native(client)


def prove_final(client):
    export(client,"final")
    before=(OUT/"oa_netlists/selected/input.scs").read_text()
    after=(OUT/"oa_netlists/final/input.scs").read_text()
    clean=lambda s:"\n".join(x for x in s.splitlines() if not x.startswith("// Generated on:"))
    equal=clean(before)==clean(after)
    dump("final_export_equivalence.json",{"identical_except_generation_time":equal,
          "selected_sha256":hashlib.sha256(before.encode()).hexdigest(),
          "final_sha256":hashlib.sha256(after.encode()).hexdigest()})
    assert equal,"Final exported circuit differs from the five-point simulated circuit"
    readback(client)
    print("FINAL_EXPORT_EQUIVALENT",equal,flush=True)


def main():
    # Native Windows OpenSSH tar transfer cannot use a Unix ControlMaster socket.
    if os.name == "nt": os.environ.setdefault("VB_DISABLE_CONTROL_MASTER","1")
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("create","read","export","run","screen","finalize","inspect","cleanup","prove"))
    args=ap.parse_args()
    client=VirtuosoClient.from_env(profile="t28_io")
    if args.action=="create":
        create(client)
        create_testbench(client)
    elif args.action=="run": run_cases("baseline")
    elif args.action=="export": export(client,"baseline")
    elif args.action=="screen": screen(client)
    elif args.action=="finalize": finalize(client)
    elif args.action=="inspect": inspect_native(client)
    elif args.action=="cleanup": cleanup_clock_fragments(client)
    elif args.action=="prove": prove_final(client)
    else: readback(client)


if __name__=="__main__": main()
