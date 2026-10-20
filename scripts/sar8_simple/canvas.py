"""Offline canonical Canvas projection of the unchanged native21-cell graph.

No HTTP, credentials, bridge or simulation. Apply the generated Project Code
with MCP, then compare its exported netlist to reference.cir with verify.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from circuit import hierarchy, TOP

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_simple_canvas"
GATES = {"sar8s_inv": "inverter", "sar8s_buf": "buffer",
         "sar8s_and2": "and-gate", "sar8s_or2": "or-gate",
         "sar8s_nand2": "nand-gate", "sar8s_xor2": "xor-gate"}


def note(identity, text, x, y, size=1):
    return dict(id=identity, kind="text", anchor=dict(kind="free", position=dict(x=x,y=y)),
                content=dict(runs=[text]), alignment="start", rotation=0, locked=False,
                styleOverride=dict(sizeScale=size), zIndex=2)


def label(identity, bind, x, y, order, alignment="middle"):
    return dict(id=identity, kind="instance-label", bind=bind, order=order,
                alignment=alignment, anchor=dict(offset=[x,y], fallback=[x,y]))


def interface(c):
    ins = [p for p in c.inputs if p not in ("VDD", "VSS")]
    outs = c.outputs[:]
    places = []
    for side, ports in (("west", ins), ("east", outs)):
        for index, p in enumerate(ports):
            places.append(dict(terminalId="term-"+p, side=side,
                               offset=(index-(len(ports)-1)//2)*30))
    places += [dict(terminalId="term-VDD", side="north", offset=0),
               dict(terminalId="term-VSS", side="south", offset=0)]
    return places


def block_symbol(c):
    places = interface(c)
    half_w = 120 if len(c.inputs+c.outputs)>12 else 100
    half_h = max(70, max(abs(p["offset"]) for p in places)+40)
    pins, prim = [], [dict(kind="polygon", points=[[-half_w,-half_h],[half_w,-half_h],
                      [half_w,half_h],[-half_w,half_h]],fill="none",stroke="foreground")]
    for p in places:
        side, off, name = p["side"], p["offset"], p["terminalId"][5:]
        x,y = {"west":(-half_w-10,off),"east":(half_w+10,off),
               "north":(off,-half_h-10),"south":(off,half_h+10)}[side]
        end = dict(x=x+(10 if side=="west" else -10 if side=="east" else 0),
                   y=y+(10 if side=="north" else -10 if side=="south" else 0))
        pins.append(dict(name=name,at=dict(x=x,y=y),direction=side,role="hierarchical-port",
                         presentation=dict(leadLength=10,showName=True,visibility="visible")))
        prim.append(dict(kind="line",**{"from":dict(x=x,y=y),"to":end}))
    return dict(symbol=dict(id="block-"+c.name,name=c.name,hierarchicalBlock=True,
                           schemaVersion=1,variants=[],pins=pins,primitives=prim,
                           viewBox=dict(x=-half_w-10,y=-half_h-10,width=2*(half_w+10),height=2*(half_h+10))),
                generatedFrom=dict(name=c.name,presentation=dict(pinPlacements=places),
                                   terminals=[dict(id="term-"+p,name=p,direction=("inout" if p in ("VDD","VSS") else
                                               "input" if p in c.inputs else "output")) for p in c.inputs+c.outputs]))


def placement(c, part, index):
    name = c.name
    if name == TOP:
        fixed={"XTIM":(350,300),"XSEQ":(1050,300),"XBPP":(2700,360),"XBPN":(2700,1030)}
        if part.name in fixed: return fixed[part.name]
        if part.name.startswith("XBIT"):
            n=7-int(part.name[-1]); return 300+(n%4)*570, 720+(n//4)*390
        n=index-12
        return [(300,1450),(300,1640),(750,1450),(750,1640),(1150,1540),(1550,1540),(1850,1540)][n]
    if name == "sar8s_bitseq8":
        if part.name == "X001": return 700,240
        bit=int(part.name[-1])
        return {7:(300,240),6:(1300,240),5:(1900,240),4:(2500,240),
                3:(700,650),2:(1300,650),1:(1900,650),0:(2500,650)}[bit]
    if name in ("sar8s_bp_p8","sar8s_bp_n8"):
        n=7-int(part.name[-1]); return 300+(n%4)*580, 220+(n//4)*390
    if name == "sar8s_bit": return [(300,240),(750,240),(1150,240)][index]
    if name == "sar8s_timing":
        positions=[(220,180),(620,180),(220,400),(220,600),(580,600),(920,600),
                   (580,400),(960,400),(1320,400),(1640,400),(1960,400),(2500,400),
                   (2350,740),(1970,740),(1640,740),(220,980),(220,1160),(220,1340),
                   (620,1060),(960,1160),(1300,1160),(1700,1160),(2100,1160),
                   (2100,1440),(2500,1300),(2890,1300)]
        return positions[index]
    if name == "sar8s_bp_slice":
        return [(220,180),(220,420),(600,420),(1000,420),(1390,420),
                (600,180),(1000,180),(1390,180)][index]
    return 320+(index%4)*420, 220+(index//4)*280


def build(seed):
    cells=hierarchy(); byname={c.name:c for c in cells}
    defs={d["symbol"]["id"]:copy.deepcopy(d) for d in seed["componentDefinitions"]
          if not d["symbol"]["id"].startswith("hierarchical-")}
    # Remove historical built-in assets not used by the new implementation.
    required=set(GATES.values()) | {"port","nmos","pmos","resistor","capacitor"}
    defs={k:v for k,v in defs.items() if k in required}
    assert required <= defs.keys()
    for c in cells: defs["block-"+c.name]=block_symbol(c)
    project=dict(schemaVersion=seed["schemaVersion"],id=seed["id"],
                 name="SAR8 Simple Async — Gate-level Controller",topDocumentId=TOP,
                 defaults=dict(instance=dict(mirror="none",rotation=0),instancesByType={},
                               label=dict(alignment="middle",locked=False,rotation=0),routeLeg=dict(mode="manual")),
                 documents=[],componentDefinitions=list(defs.values()),externalSubcircuitDefinitions=[],
                 simulationFolders=[],source=dict(dialect="none",entry=None,files=[],sourcePolicy="copy"),
                 symbolLibrary=seed["symbolLibrary"],structureRevision=seed["structureRevision"])
    references=[]
    for c in cells:
        d=dict(id=c.name,name=c.name,netlist=dict(name=c.name,formalParameters=[],terminals=[]),
               presentation=dict(grid=10,compactness="normal",styleProfileId="razavi-textbook-v1",
                                 labelSubscriptAfterFirst=False,labelSubscriptItalic=False,
                                 cellSymbol=dict(pinPlacements=interface(c))),
               instances=[],routes=[],connections=dict(contacts=[],unrouted=[]),nets=[],junctions=[],
               annotations=[],drafting=dict(objects=[]),connectivityEvidence=[],layoutGroups=[],
               constraints=[],sourceStatus="connectivity-modified",revision=0,noConnects=[])
        signal_endpoints=[]; hidden={"VDD":[],"VSS":[]}
        for index,p in enumerate(c.parts):
            x,y=placement(c,p,index)
            if p.lib=="SAR_ADC_T28":
                typ=GATES.get(p.master,"block-"+p.master)
                ins=dict(type=typ,id=p.name,name=p.name,coordinate=[x,y],parameters={},
                         target=dict(kind="subcircuit",childDocumentId=p.master))
                terms=p.terms
            elif p.lib=="tsmcN28":
                typ="pmos" if p.master=="pch_mac" else "nmos"
                ins=dict(type=typ,id=p.name,name=p.name,coordinate=[x,y],variant="textbook-3terminal",
                         parameters=dict(w=p.params["Wfg"],l=p.params["l"],nf=p.params["fingers"],m=p.params["simM"]),
                         target=dict(kind="model",deviceClass="mos",name=p.master))
                terms=p.terms
            else:
                typ="resistor" if p.master=="res" else "capacitor"
                ins=dict(type=typ,id=p.name,name=p.name,coordinate=[x,y],
                         parameters=dict(value=p.params["r" if typ=="resistor" else "c"]),
                         target=dict(kind="primitive",deviceClass=typ))
                terms={"1":p.terms["PLUS"],"2":p.terms["MINUS"]}
            sym=defs[typ]["symbol"]
            bb=sym["viewBox"]
            ins["labels"]=[label("name-"+p.name,"name",-35 if typ.startswith("block-") else 0,
                                 bb["y"]-20,index,"end" if typ.startswith("block-") else "middle")]
            if typ in ("nmos","pmos","capacitor","resistor"):
                ins["labels"]=[label("name-"+p.name,"name",40,-10,index,"start")]
            if typ.startswith("block-"):
                ins["labels"].append(dict(id="master-"+p.name,kind="instance-value",order=index,
                    alignment="end",anchor=dict(offset=[-35,bb["y"]-42],fallback=[x-35,y+bb["y"]-42]),
                    text=dict(runs=[p.master.removeprefix("sar8s_")])))
            if typ in ("capacitor","resistor"):
                ins["labels"].append(dict(id="value-"+p.name,kind="instance-value",order=index,
                    bind="value",alignment="start",anchor=dict(offset=[40,15],fallback=[x+40,y+15])))
            d["instances"].append(ins)
            pins={z["name"]:z for z in sym["pins"]}
            for pin,net in terms.items():
                if pin=="B" and typ in ("nmos","pmos") or pin not in pins:
                    assert net in hidden,(c.name,p.name,pin,net)
                    hidden[net].append(dict(terminal=[p.name,pin]));continue
                z=pins[pin]; pos=(x+z["at"]["x"],y+z["at"]["y"])
                signal_endpoints.append((p.name,pin,net,pos,z["direction"]))
        # Formal pins form an aligned interface strip. The output bank in the
        # source graph is deliberately absent: D0..7 are working SAR bits.
        max_x=max(i["coordinate"][0] for i in d["instances"])+450
        max_y=max(i["coordinate"][1] for i in d["instances"])+250
        output_sources={p:next((e for e in signal_endpoints if e[2]==p and e[4]=="east"),None) for p in c.outputs}
        direct_outputs={}
        for n,p in enumerate(c.inputs+c.outputs):
            inp=p in c.inputs; num=(c.inputs if inp else c.outputs).index(p)
            source=output_sources.get(p)
            x,y=(60,100+num*40) if inp else (source[3][0]+110,source[3][1]) if source else (max_x,100+num*40)
            iid="p-"+p; nid="formal-"+p
            d["instances"].append(dict(type="port",id=iid,coordinate=[x,y],
                **({} if inp else dict(mirror="horizontal")),
                labels=[label("name-"+iid,dict(kind="cell-terminal-name",terminalId="term-"+p),
                              -20 if inp else 20,5,100+n,"end" if inp else "start")]))
            d["netlist"]["terminals"].append(dict(id="term-"+p,name=p,direction="inout" if p in hidden else
                "input" if inp else "output",netId=nid,interfaceInstanceIds=[iid]))
            d["nets"].append(dict(id=nid,at=dict(terminal=[iid,"P"])))
            if p in hidden and hidden[p]:
                d["connections"]["unrouted"].append([dict(terminal=[iid,"P"]),*hidden[p]])
            if source:
                direct_outputs[(source[0],source[1])]=iid
        for n,(iid,pin,net,(x,y),side) in enumerate(signal_endpoints):
            nid="formal-"+net if iid.startswith("p-") else f"net-{iid}-{pin}"
            if not iid.startswith("p-"): d["nets"].append(dict(id=nid,at=dict(terminal=[iid,pin])))
            if (iid,pin) in direct_outputs:
                rid=f"wire-{iid}-{pin}"
                d["routes"].append(dict(id=rid,legId=rid+"-leg",start=dict(terminal=[iid,pin]),
                                        end=dict(terminal=[direct_outputs[(iid,pin)],"P"])))
                continue
            dx,dy={"west":(-50,0),"east":(50,0),"north":(0,-30),"south":(0,30)}[side]
            j=f"j-{iid}-{pin}"; rid=f"wire-{iid}-{pin}"; ann=f"label-{iid}-{pin}"
            d["junctions"].append(dict(id=j,coordinate=[x+dx,y+dy],role="route-anchor"))
            d["routes"].append(dict(id=rid,legId=rid+"-leg",start=dict(terminal=[iid,pin]),end=dict(junction=j)))
            # A bound local Net Label connects equivalent named stubs. This
            # is real named connectivity, not independent drafting text.
            d["annotations"].append(dict(id=ann,kind="net-label",netId=nid,order=200+n,
                bind=dict(kind="net-name",netId=nid),alignment="end" if side=="west" else "start",
                anchor=dict(kind="free",position=dict(x=x+dx+(15 if dy else -5 if dx<0 else 5),
                                                       y=y+dy+(-8 if dy<=0 else 10)))))
            d["connectivityEvidence"].append(dict(id="claim-"+ann,kind="name-claim",name=net,
                netId=nid,scope="local",owner=dict(kind="net-label",annotationId=ann)))
        d["drafting"]["objects"] += [note("title",c.name,60,-80,1.35),
            note("convention","同名标签为本 Cell 内真实连接；VDD/VSS 按端口贯穿。双击实例展开。",60,-40)]
        if c.name==TOP:
            d["drafting"]["objects"] += [note("sample-rule","SAMPLE：清 D / 初始化 T7；PHI_W：写当前位；PHI_U：移位并复位比较器。",60,-125),
                note("stop-rule","ACTIVE = OR(T7..T0)，只抑制下一次比较；不是额外状态。无输出银行 / EOC。",60,1810),
                note("scope","门级 / MOS / RC 连接对应当前 Virtuoso 版本；未在 Canvas 运行 T28 仿真。",60,1850)]
        if c.name=="sar8s_bit": d["drafting"]["objects"].append(note("equation","NEXT_D = TOKEN ? DATA : D；CODE = D OR TOKEN；SAMPLE 直接复位 DFF。",60,max_y+30))
        if c.name=="sar8s_timing": d["drafting"]["objects"].append(note("loop","判决检测 → PHI_W → 延时 → PHI_U → 复位 / 建立间隔 → 下一次 CMP_CLK",60,1630))
        if c.name.startswith("sar8s_delay_"): d["drafting"]["objects"].append(note("delay","两个 RC + 反相器；另有快速回零 MOS。R=10k/级，C 为当前种子值，非 PVT 保证。",60,max_y+30))
        if c.name=="sar8s_bp_slice":
            next(a for a in d["annotations"] if a["id"]=="label-XD_ON0-VDD")["anchor"]["position"]["y"]+=18
        wire_local_pairs(d, signal_endpoints, c.inputs+c.outputs, defs)
        labels=[a for i in d["instances"] for a in i.get("labels",[])]+d["annotations"]
        for order,a in enumerate(labels): a["order"]=order
        project["documents"].append(d)
        references.append(".subckt "+c.name+" "+" ".join(c.inputs+c.outputs))
        for p in c.parts:
            if p.lib=="SAR_ADC_T28":
                references.append(p.name+" "+" ".join(p.terms[k] for k in byname[p.master].inputs+byname[p.master].outputs)+" "+p.master)
            elif p.lib=="tsmcN28":
                references.append(p.name+" "+" ".join(p.terms[k] for k in ("D","G","S","B"))+" "+p.master+f" w={p.params['Wfg']} l={p.params['l']} m={p.params['simM']} nf={p.params['fingers']}")
            else: references.append(p.name+" "+p.terms["PLUS"]+" "+p.terms["MINUS"]+" "+p.params["r" if p.master=="res" else "c"])
        references.append(".ends "+c.name)
    # Top first, functional children next, transistor/gate leaves last.
    order=[TOP,"sar8s_timing","sar8s_bitseq8","sar8s_bit","sar8s_bp_p8","sar8s_bp_n8","sar8s_bp_slice"]
    project["documents"].sort(key=lambda d:order.index(d["id"]) if d["id"] in order else len(order)+list(byname).index(d["id"]))
    assert len(project["documents"])==21
    assert all(len([i for i in d["instances"] if not i["id"].startswith("p-")])==len(byname[d["id"]].parts) for d in project["documents"])
    return project,"\n".join(references)+"\n"


def wire_local_pairs(d, endpoints, formals, definitions):
    """Replace short internal two-pin named links with actual orthogonal wire.

    Keep shared controls/feedback and long paths as explicit named connections.
    Test full segments against every unrelated symbol body before drawing.
    """
    groups={}
    for e in endpoints: groups.setdefault(e[2],[]).append(e)
    for net,group in groups.items():
        if net in formals or len(group)!=2: continue
        source=next((e for e in group if e[4]=="east"),None)
        target=next((e for e in group if e[4]=="west"),None)
        if source is None or target is None: continue
        sx,sy=source[3];tx,ty=target[3]
        if tx-sx<100 or tx-sx>750: continue
        mid=10*round((sx+tx)/20)
        points=[(sx,sy),(mid,sy),(mid,ty),(tx,ty)]
        points=[p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
        blocked=False
        for inst in d["instances"]:
            if inst["id"] in (source[0],target[0]) or inst["type"]=="port": continue
            bb=definitions[inst["type"]]["symbol"]["viewBox"]
            x,y=inst["coordinate"];left=x+bb["x"]-10;right=left+bb["width"]+20
            top=y+bb["y"]-10;bottom=top+bb["height"]+20
            for a,b in zip(points,points[1:]):
                blocked |= (a[1]==b[1] and top<a[1]<bottom and max(a[0],b[0])>left and min(a[0],b[0])<right)
                blocked |= (a[0]==b[0] and left<a[0]<right and max(a[1],b[1])>top and min(a[1],b[1])<bottom)
        if blocked: continue
        removed={f"wire-{e[0]}-{e[1]}" for e in group}
        anns={f"label-{e[0]}-{e[1]}" for e in group}
        junctions={f"j-{e[0]}-{e[1]}" for e in group}
        d["routes"]=[r for r in d["routes"] if r["id"] not in removed]
        d["annotations"]=[a for a in d["annotations"] if a["id"] not in anns]
        d["connectivityEvidence"]=[e for e in d["connectivityEvidence"] if e["owner"]["annotationId"] not in anns]
        d["junctions"]=[j for j in d["junctions"] if j["id"] not in junctions]
        rid="direct-"+net
        legs=[dict(id=rid+f"-{i}",bend=rid+f"-bend-{i}",coordinate=list(p)) for i,p in enumerate(points[1:-1])]
        legs.append(dict(id=rid+"-end",terminal=[target[0],target[1]]))
        d["routes"].append(dict(id=rid,start=dict(terminal=[source[0],source[1]]),legs=legs))
        nid=f"net-{source[0]}-{source[1]}";aid="label-direct-"+net
        d["annotations"].append(dict(id=aid,kind="net-label",netId=nid,bind=dict(kind="net-name",netId=nid),
            anchor=dict(kind="free",position=dict(x=(sx+mid)//2,y=sy-12))))
        d["connectivityEvidence"].append(dict(id="claim-"+aid,kind="name-claim",name=net,
            netId=nid,scope="local",owner=dict(kind="net-label",annotationId=aid)))


def main():
    seed=json.loads((OUT/"native-seed.analog.json").read_text(encoding="utf-8"))
    project,reference=build(seed)
    (OUT/"generated.analog.json").write_text(json.dumps(project,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (OUT/"reference.cir").write_text(reference,encoding="utf-8")
    print(json.dumps(dict(documents=len(project["documents"]),instances=sum(len(c.parts) for c in hierarchy()),
        bytes=(OUT/"generated.analog.json").stat().st_size,source_sha256=hashlib.sha256(Path(__file__).with_name("circuit.py").read_bytes()).hexdigest())))


if __name__=="__main__": main()
