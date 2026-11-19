"""Compare the reviewed draft with the streamed GDS and locate real Calibre markers."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

import klayout.db as kdb

from native_handoff import TOP, LIB, reference
import review


# Layer numbers are read from the installed XStream layer map for this run.
LAYER_INPUTS = {"OD": ("diff", "tap"), "PO": ("poly",), "PO/dummy1": ("poly_dummy",),
                "CO": ("mcon",), "M1": ("met1",), "M2": ("met2",), "M3": ("met3",),
                "VIA1": ("via",), "VIA2": ("via2",), "NW": ("nwell",),
                "NP": ("nsdm",), "PP": ("psdm",)}
RULE_GROUPS = {
    "gate_contact_enclosure": {"CO.EN.7"},
    "poly_shape_and_poly_dummy_spacing": {"PO.W.3", "PO.S.3", "PO.S.17", "PO.R.2", "PO.R.10", "SR_DPO.S.1", "SR_DPO.S.5"},
    "implant_and_pmetal": {"PMET.EX.1", "PMET.O.1", "PP.EN.1", "PP.A.1", "NP.A.1", "NP.S.9"},
    "metal_spacing_jogs_area": {"G.4:M1i", "M1.S.1", "M1.S.7", "M1.S.8", "M1.A.3", "M2.A.2", "M2.A.3"},
    "deck_warnings": {"DIODMY_L:WARNING", "IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1"},
}


def parse_drc(path, counts):
    lines = path.read_text(encoding="latin1").splitlines()
    assert lines[0].split() == [TOP, "1000"]
    markers = defaultdict(list)
    rule = None
    for i, line in enumerate(lines):
        if line in counts:
            rule = line
        record = re.fullmatch(r"([pe]) (\d+) (\d+)", line)
        if record:
            assert rule and int(record[2]) == len(markers[rule])+1
            points = [list(map(int, s.split())) for s in lines[i+1:i+1+int(record[3])]]
            assert all(len(row) == (2 if record[1] == "p" else 4) for row in points)
            markers[rule].append((record[1], points))
    assert {r:len(v) for r,v in markers.items()} == counts
    return markers


def marker_box(entry):
    points = entry[1]
    xs = [x for row in points for x in row[::2]]
    ys = [y for row in points for y in row[1::2]]
    return [min(xs),min(ys),max(xs),max(ys)]


def region(rects):
    out = kdb.Region()
    for rect in rects:
        out.insert(kdb.Box(*rect))
    return out.merged()


def verify(run, work, mc):
    manifest = json.loads((run/"manifest.json").read_text())
    assert manifest["top"]==TOP and manifest["library"]==LIB and manifest["status"]=="completed"
    gds = run/"fixture.gds"
    assert hashlib.sha256(gds.read_bytes()).hexdigest() == manifest["gds"]["sha256"]
    ly=kdb.Layout()
    ly.read(str(gds))
    assert ly.dbu==0.001 and [c.name for c in ly.top_cells()]==[TOP]
    cell=ly.cell(TOP)
    layermap=json.loads((work/"layermap.json").read_text())
    stats, compiled, ast, _=review.evaluate(mc)
    assert stats["lml_sha256"]==manifest["source"]["lml_sha256"]
    assert stats["netlist_sha256"]==manifest["source"]["electrical_sha256"]
    layers, xor = {}, {}
    for name, inputs in LAYER_INPUTS.items():
        key=name if "/" in name else name+"/drawing"
        number, datatype=map(int,layermap[key])
        idx=ly.find_layer(number,datatype)
        if idx is None:
            raise ValueError(f"Missing streamed layer {key}")
        actual=kdb.Region(cell.begin_shapes_rec(idx)).merged()
        rects=[r for layer in inputs for r in compiled["layers_nm"][layer]]
        if name=="M2":
            rects.extend(pin["box"] for pin in ast["cellPorts"])
        draft=region(rects)
        xor[name]={"gds_layer_datatype":[number,datatype], "draft_nm2":draft.area(),
                   "native_nm2":actual.area(), "draft_only_nm2":(draft-actual).area(),
                   "native_only_nm2":(actual-draft).area(), "xor_nm2":(draft^actual).area(),
                   "draft_polygons":draft.count(), "native_polygons":actual.count()}
        layers[name]=actual
    devices=json.loads((work/"devices.json").read_text())
    actual_gates=layers["PO"] & layers["OD"]
    channel_xor=(actual_gates ^ region([x["channel_nm"] for x in devices])).area()
    assert channel_xor==0 and actual_gates.count()==11
    text=(run/"readback.txt").read_text()
    nts=re.findall(r"^IT (\w+) (\w+) (\w+)$",text,re.M)
    ref,_=reference()
    expected={(name,t,n) for name,(nets,_,_) in ref.items() for t,n in zip("DGSB",nets)}
    assert len(nts)==44 and set(nts)==expected
    pins={}
    for line in text.splitlines():
        if line.startswith("PORT "):
            _,name,layer,bbox=line.split(maxsplit=3)
            assert layer=="M2"
            pins[name]=[round(1000*float(n)) for n in re.findall(r"-?[\d.]+",bbox)]
    assert pins=={p["name"]:p["box"] for p in ast["cellPorts"]}
    counts=manifest["checks"]["drc"]["markers_by_rule"]
    groups={g:sum(counts.get(r,0) for r in rules) for g,rules in RULE_GROUPS.items()}
    other=set(counts).difference(*RULE_GROUPS.values())
    if other:
        groups["other"]=sum(counts[r] for r in other)
    assert sum(groups.values())==sum(counts.values())
    markers=parse_drc(run/"drc/DRC_RES.db",counts)
    heads={}
    for pc in ast["pcells"]:
        entry=compiled["store"]["realizations"][pc["realization"]]
        pmap={p["port"]:p["box"] for p in entry["ports_local_nm"]}
        for i,inst in enumerate(pc["devices"]):
            heads[inst.split()[1]]=mc.transform_local_box(pmap[f"G_{i+1}"], *pc["atNm"],pc["orient"])
    by_gate=Counter()
    for m in markers.get("CO.EN.7",[]):
        x1,y1,x2,y2=marker_box(m)
        hits=[n for n,(l,b,r,t) in heads.items() if l<=x1<=x2<=r and b<=y1<=y2<=t]
        by_gate[hits[0] if len(hits)==1 else "unassigned"]+=1
    lvs_text=(run/"lvs/lvs.rep").read_text(encoding="latin1")
    matched={}
    for name, regex in {
        "ports":r"^\s*Ports:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
        "nets":r"^\s*Nets:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
        "nch_mac":r"^\s*Instances:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+MN\(nch_mac\)",
        "pch_mac":r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+MP\(pch_mac\)"}.items():
        match=re.search(regex,lvs_text,re.M)
        matched[name]=list(map(int,match.groups())) if match else None
    filtered=re.search(r"(\d+) layout instances were filtered",lvs_text)
    filtered_diodes=re.search(r"^\s*(\d+)\s+0\s+\*\s+D \(2 pins\)",lvs_text,re.M)
    stream=(run/"stream.log").read_text(encoding="latin1")
    warn_codes=re.findall(r"^WARNING \(([-A-Z0-9]+)\)",stream,re.M)
    raw_names=["readback.txt","stream.log","drc/DRC.rep","drc/DRC_RES.db","lvs/lvs.rep"]
    rec={
        "run":manifest["identity"],"host":manifest["host"],"oa_cellview":[LIB,TOP,"layout"],
        "source":manifest["source"],"oa_sha256":manifest["oa_sha256"],"gds":manifest["gds"],
        "raw_directory_on_host":str(Path(manifest["checks"]["oa"]["command"][-1]).parent).replace("\\","/"),
        "rules_decks":manifest["decks"],
        "raw_reports":{n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in raw_names},
        "bbox_um":[v*ly.dbu for v in (cell.bbox().left,cell.bbox().bottom,cell.bbox().right,cell.bbox().top)],
        "oa_readback":{"primitive_pdk":"tsmcN28", "transistors":11,"explicit_inst_terms_verified":len(nts),
                       "ports_m2_nm":pins,"native_vias":int(re.search(r"NATIVE_VIAS (\d+)",text)[1])},
        "gds_vs_layoutml":{"layers":xor,"active_gate_intersections":actual_gates.count(),
                           "channel_xor_nm2":channel_xor,
                           "scope":"Merged polygons at 1 nm DBU on the specified drawing / dummy-purpose layers, plus M2 pin metal in the draft. Technology-only device recognition and annotation layers have no common surrogate comparison."},
        "lvs":{"verdict":manifest["checks"]["lvs"]["verdict"],"counts_columns":["layout_matched","source_matched","layout_unmatched","source_unmatched"],
               "matched":matched,"initial_layout_only_diodes":int(filtered_diodes[1]) if filtered_diodes else None,
               "filtered_layout_instances":int(filtered[1]) if filtered else None},
        "drc":{"verdict":manifest["checks"]["drc"]["verdict"],"total_markers":sum(counts.values()),
               "total_rule_names":len(counts),"by_rule":counts,"by_group":groups,
               "gate_contact_markers_by_instance":dict(by_gate),
               "sample_boxes_nm":{r:[marker_box(m) for m in v[:2]] for r,v in markers.items()}},
        "stream_warning_codes":warn_codes, "pex": "not run", "postlayout_tt": "not run",
    }
    if (run/"times.json").is_file():
        times=json.loads((run/"times.json").read_text())
        rec["elapsed_seconds_from_remote_submission"]={k:round(v-times["submitted"],2) for k,v in times.items()}
    return rec,layers,markers


def plot(layers, markers, dest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch, Patch, Rectangle
    from matplotlib.path import Path as MPath
    plt.rcParams.update({"font.family":["Microsoft YaHei","DejaVu Sans"],"axes.unicode_minus":False,
                         "axes.spines.top":False,"axes.spines.right":False})
    fig=plt.figure(figsize=(11.2,7.0),layout="constrained")
    grid=fig.add_gridspec(2,2,width_ratios=[1.05,1])
    plan=fig.add_subplot(grid[:,0])
    top=fig.add_subplot(grid[0,1])
    low=fig.add_subplot(grid[1,1])
    colors={"NW":"#c1d7b2","OD":"#7fb597","PO/dummy1":"#c2bbc9","PO":"#be6583","M1":"#268a95",
            "M2":"#6479c5","M3":"#e59235","CO":"#35373b","VIA1":"#364b74","VIA2":"#6b461a"}
    def draw(axis,names):
        for name in names:
            for poly in layers[name].each():
                vertices=[];codes=[]
                rings=[list(poly.each_point_hull())]
                rings.extend(list(poly.each_point_hole(i)) for i in range(poly.holes()))
                for ring in rings:
                    vertices.extend((p.x*.001,p.y*.001) for p in ring+[ring[0]])
                    codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(ring)-1)+[MPath.CLOSEPOLY])
                axis.add_patch(PathPatch(MPath(vertices,codes),facecolor=colors[name],edgecolor=colors[name],
                                         alpha=0.76 if name.startswith("M") else 0.60,linewidth=.35))
        axis.set_aspect("equal")
        axis.tick_params(labelsize=8)
        axis.set_xlabel("x (µm)",fontsize=9)
        axis.set_ylabel("y (µm)",fontsize=9)
    def highlight(axis,rule):
        edges=[]
        for typ,pts in markers[rule]:
            if typ=="p":
                edges.append([(x*.001,y*.001) for x,y in pts+[pts[0]]])
            else:
                edges.extend([[(a*.001,b*.001),(c*.001,d*.001)] for a,b,c,d in pts])
        axis.add_collection(LineCollection(edges,colors="#b12e27",linewidths=1.0))
    def window(bounds,label):
        xl,yl,xr,yr=bounds
        plan.add_patch(Rectangle((xl,yl),xr-xl,yr-yl,fill=False,edgecolor="#262626",lw=.9,ls="--"))
        plan.annotate(label,(xl,yr),xytext=(-10,3),textcoords="offset points",fontweight="bold",fontsize=9)
    draw(plan,colors)
    plan.set_xlim(-1.08,1.08);plan.set_ylim(-.32,2.67)
    plan.set_title("从原生 OA 导出的比较器",loc="left",fontsize=13,fontweight="bold")
    plan.legend(handles=[Patch(color=colors[n],label=n) for n in ("OD","PO","M1","M2","M3")],
                loc="upper left",ncol=5,fontsize=8,frameon=False,handlelength=.8,columnspacing=.7)
    a=(-.87,1.035,-.36,1.255); b=(-.625,.890,-.420,1.095)
    window(a,"A");window(b,"B")
    draw(top,["OD","PO","CO"]);highlight(top,"CO.EN.7")
    top.set(xlim=(a[0],a[2]),ylim=(a[1],a[3]))
    top.set_title("A   三个 PMOS 栅接触头",loc="left",fontsize=12,fontweight="bold")
    top.text(.01,.02,"红线为 CO.EN.7 原始标记",transform=top.transAxes,fontsize=9)
    draw(low,["M1","VIA1"]);highlight(low,"M1.S.1")
    low.set(xlim=(b[0],b[2]),ylim=(b[1],b[3]))
    low.set_title("B   OUTN 的 M1 凹口",loc="left",fontsize=12,fontweight="bold")
    if [-550,930,-545,1085] in [marker_box(m) for m in markers["M1.S.1"]]:
        low.annotate("5 nm",(-.5475,.973),(-.598,1.059),fontsize=10,color="#8b211e",
                     arrowprops={"arrowstyle":"->","color":"#8b211e","lw":1})
    fig.savefig(dest,dpi=175,facecolor="white")
    plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--run",type=Path,required=True)
    p.add_argument("--layoutml",type=Path,required=True)
    args=p.parse_args()
    sys.path.insert(0,str(args.layoutml.resolve()/"explorations/Q-tech-decoupling"))
    import meso_compiler
    report,layers,markers=verify(args.run,args.run.parent,meso_compiler)
    (review.HERE/"native_screen.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    plot(layers,markers,review.HERE/"native_screen.png")
