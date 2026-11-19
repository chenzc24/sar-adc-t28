"""Publish an OA readback, streamed geometry, RC and matched TT for this experiment."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
from klayout import db as kdb

from virtuoso_design import electrical, HERE, ROOT, TOP
from virtuoso_metrics import checked_measurements
from virtuoso_tt import PHYSICAL, SCHEMATIC


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Stream:
    def __init__(self, path):
        self.layout = kdb.Layout()
        self.layout.read(str(path))
        self.cell = self.layout.cell(TOP)
        assert self.cell and self.layout.dbu == 0.001

    def region(self, layer, datatype=0):
        return kdb.Region(self.cell.begin_shapes_rec(self.layout.layer(layer, datatype))).merged()

    def draw(self, axes, layer, color, alpha=1, datatype=0):
        pieces = self.region(layer, datatype).decompose_trapezoids_to_region()
        polys = [[(p.x/1000, p.y/1000) for p in s.each_point_hull()] for s in pieces.each()]
        axes.add_collection(PolyCollection(polys, facecolors=color, edgecolors="none", alpha=alpha))


def structure(physical, measurements, stream):
    intent = read(physical/"intent.json")
    text = (physical/"readback.txt").read_text()
    ports, circuit, _ = electrical()
    trans = {(n, pin): net for n, pin, net in re.findall(r"^IT (\w+) (\w+) (\w+)$", text, re.M)}
    expected={}
    widths={}
    for n,device in intent["mos"].items():
        master="MNTAIL" if n in ("MNTAIL_L","MNTAIL_R") else n
        model,_,nets=circuit[master]
        assert device["model"]==model
        widths[master]=widths.get(master,0)+device["width"]
        expected.update({(n,pin):net for pin,net in zip("DGSB",nets)})
    assert widths=={n:width for n,(_,width,_) in circuit.items()} and trans==expected
    heads = re.findall(r"^GATE_M1 (\w+) ", text, re.M)
    assert sorted(heads) == sorted(intent["mos"])
    actual_ports = dict(re.findall(r"^PORT (\w+) (M\d+) ", text, re.M))
    assert set(actual_ports) == set(ports)
    assert actual_ports == {n: rect[0] for n, rect in intent["ports"].items()}
    geometry = measurements["geometry"]
    assert sorted(geometry["active_gate_boxes_nm"]) == sorted(m["box_nm"] for m in intent["mos"].values())
    od = stream.region(6)
    contacts = stream.region(30)
    sharing = []
    for y1, y2, xs, nets in [(0,1000,[-130,0,130],["X","TAIL","Y"]),
                              (1550,2050,[-260,-130,0,130,260],["VDD","OUTP","VDD","OUTN","VDD"])]:
        row = []
        for x, net in zip(xs,nets):
            # In the overlapping active width, OD spans both adjacent gate centers.
            y = y2 - 200
            bridge = kdb.Region(kdb.Box(x-65,y-5,x+65,y+5))
            assert (bridge-od).is_empty()
            column = contacts & kdb.Region(kdb.Box(x-21,y1,x+21,y2))
            assert column.count() >= 4
            row.append(dict(net=net, x_nm=x, contact_cuts=column.count()))
        sharing.append(row)
    ptype = (stream.region(25) & od - stream.region(3)).merged()
    # A closed P+ diffusion surrounds the active rows, with M1 and contacts on all sides.
    guard, = [p for p in ptype.each() if p.holes() == 1]
    guard_region = kdb.Region(guard)
    guard_m1 = (stream.region(31) & guard_region).merged()
    assert any(p.holes() == 1 for p in guard_m1.each())
    box=guard.bbox()
    l,b,r,t=box.left,box.bottom,box.right,box.top
    sides = [kdb.Box(l,b,l+100,t), kdb.Box(r-100,b,r,t),
             kdb.Box(l,b,r,b+100), kdb.Box(l,t-100,r,t)]
    assert all((contacts & guard_m1 & kdb.Region(s)).count() > 8 for s in sides)
    nw = stream.region(3)
    ntap = (nw & od & stream.region(26)).merged()
    assert nw.count() == ntap.count() == 1
    return dict(terminations=len(trans), native_M1_gate_pins=sorted(heads), port_layers=actual_ports,
                verified_effective_widths_nm=widths,
                shared_diffusion_rows=sharing, closed_p_substrate_ring=True,
                p_substrate_contact_cuts=(contacts & guard_m1).count(), common_nwell_count=nw.count(),
                nwell_tap_contact_cuts=(ntap & contacts).count(),
                native_top_level_vias=int(re.search(r"^NATIVE_VIAS (\d+)",text,re.M)[1]))


def render(stream, intent, geometry, path):
    colors = {"well":"#e2e2f0", "OD":"#9bc7a2", "PO":"#ac5546", "dummy":"#c9b4a9",
              "CO":"#384750", "M1":"#2678a0", "M2":"#dc9e23", "M3":"#ad4778", "M4":"#6557ad", "via":"#263247"}
    fig, (left, right) = plt.subplots(1, 2, figsize=(8.5, 7.2))
    fig.subplots_adjust(left=.085, right=.982, bottom=.165, top=.86, wspace=.20)
    bounds=[v/1000 for v in geometry["bbox_nm"]]
    for ax, name in [(left,"Devices and body contacts"),(right,"Routing and external pins")]:
        ax.set(xlim=(bounds[0]-.13,bounds[2]+.25), ylim=(bounds[1]-.14,bounds[3]+.15),
               aspect="equal", xlabel="x (µm)")
        ax.set_title(name,loc="left",fontsize=12,weight="bold",pad=10)
        ax.set_facecolor("#f8fafb")
        ax.tick_params(labelsize=8,colors="#53606b")
        for spine in ax.spines.values():
            spine.set_color("#c8d0d5")
    left.set_ylabel("y (µm)")
    stream.draw(left,3,colors["well"])
    stream.draw(left,6,colors["OD"])
    stream.draw(left,17,colors["dummy"],datatype=7)
    stream.draw(left,17,colors["PO"])
    stream.draw(left,30,colors["CO"])
    tap=(stream.region(3) & stream.region(26) & stream.region(6)).bbox()
    tails=[(d["gate_center_nm"][0]/1000,d["gate_center_nm"][1]/1000,
            "Tail / 2" if n!="MNTAIL" else "Tail") for n,d in intent["mos"].items() if n.startswith("MNTAIL")]
    for x,y,s in [(0,2.30,"Six PMOS  ·  shared diffusion"),*tails,
                  (.0,.34,"Input pair"),(0,1.23,"Regeneration NMOS"),
                  (tap.center().x/1000,tap.top/1000+.11,"N-well tap")]:
        left.text(x,y,s,ha="center",va="center",fontsize=7.2,color="#253039",
                  bbox=dict(facecolor="white",alpha=.90,edgecolor="none",pad=1.2))
    left.annotate("P+ guard ring",xy=(-.48,-.385),xytext=(.03,-.22),
                  fontsize=7.2,ha="center",va="center",color="#253039",
                  bbox=dict(facecolor="white",alpha=.90,edgecolor="none",pad=1.2),
                  arrowprops=dict(arrowstyle="->",color="#53606b",lw=.75))
    for layer, name, alpha in [(6,"OD",.3),(31,"M1",.8),(32,"M2",.86),(33,"M3",.87),(34,"M4",.87),
                               (51,"via",.94),(52,"via",.94),(53,"via",.94)]:
        stream.draw(right,layer,colors[name],alpha)
    for n,(_,x,y,_,_) in intent["ports"].items():
        xy=(x/1000,y/1000)
        off = {"VINN":(-11,-12),"VINP":(13,-12),"VDD":(1,10),"VSS":(3,-15)}.get(n,(14,1))
        right.annotate(n,xy,xytext=off,textcoords="offset points",ha="center",va="center",
                       fontsize=7.6,color="#20323d",weight="bold",
                       bbox=dict(facecolor="white",alpha=.85,edgecolor="none",pad=.9))
    routing_items=[(n,n) for n in ("M1","M2","M3","M4") if geometry["metal_area_um2"].get(n,0)>0]
    for ax, items in ((left,[("OD","OD"),("PO","Gate"),("dummy","Dummy PO"),("CO","Contact")]),
                      (right,routing_items+[("via","Via")])):
        ax.legend(handles=[Patch(facecolor=colors[c],label=n) for c,n in items],
                  loc="upper center",bbox_to_anchor=(.5,-.105),ncol=len(items),frameon=False,fontsize=8,
                  handlelength=1,columnspacing=.8,handletextpad=.35)
    fig.suptitle(f"StrongARM comparator   |   {geometry['width_um']:.3f} × {geometry['height_um']:.3f} µm",
                 fontsize=14,weight="bold",y=.967)
    fig.savefig(path,dpi=195,facecolor="white")
    plt.close(fig)


def transient(run):
    folder=ROOT/"work/output/managed_execution/runs"/run/"collected"
    report=read(folder/"derived/result.json")
    state=read(folder/"collection_receipt.json")["status"]
    assert state["run_id"]==run and state["simulation"]["status"]==state["analysis"]["status"]=="complete"
    recipe=read(ROOT/"work/layout"/run/"recipe.json")
    fixed={"test.scs","comparator_fixture.scs","analyze_blocks.py","xtor/comparator/comparator.scs"}
    fixture={row["name"]:row["sha256"] for row in recipe["inputs"] if row["name"] in fixed}
    assert set(fixture)==fixed
    return dict(run=run,recipe_sha256=state["registered"]["recipe_hash"],result_sha256=digest(folder/"derived/result.json"),
                gds_sha256=report["context"].get("gds_sha256"),
                spectre_options=recipe["spectre_args"],fixture_sha256=fixture,
                spectre_log_sha256=digest(folder/"spectre.out"),collection_sha256=digest(folder/"collection_receipt.json"),
                pass_validation=report["pass_validation"],pass_functional=report["pass_functional"],
                diagnostic_screens_pass=report["diagnostic_screens_pass"],warnings=report["warning_codes"],
                diagnostics=report["diagnostics"],failures=report["failures"],metrics=report["metrics"]["comparator"])


def trip_brackets(run, gds_hash):
    folder=ROOT/"work/output/managed_execution/runs"/run/"collected"
    r=read(folder/"derived/result.json")
    assert r["analysis_complete"] and r["context"]["gds_sha256"]==gds_hash
    sweeps=r["context"]["threshold_sweeps_uV"]
    samples=r["metrics"]["comparator"]["decisions"]
    assert len(samples)==1+len(sweeps["rising"])+len(sweeps["falling"])
    comparison=transient(run)
    out={"run":run,"recipe_sha256":comparison["recipe_sha256"],"result_sha256":comparison["result_sha256"],
         "warnings":r["warning_codes"],"diagnostics_count":len(r["diagnostics"]),
         "measurement":"VINP minus VINN at TT; VINN at 450 mV, complete 10 ns clock cycles, 50 uV grid."}
    start=1
    for name in ("rising","falling"):
        target=sweeps[name]
        subset=samples[start:start+len(target)]
        assert [round(s["input_v"]*1e6) for s in subset]==target
        assert all(s["decided"] and s["reset_s"]>0 for s in subset)
        negatives=[v for v,s in zip(target,subset) if not s["positive"]]
        positives=[v for v,s in zip(target,subset) if s["positive"]]
        bracket=[max(negatives),min(positives)] if negatives and positives else None
        out[name]=dict(bracket_uV=bracket,monotonic=bool(bracket and bracket[0]<bracket[1]),
                       decisions=[[v,s["positive"],s["delay_s"]] for v,s in zip(target,subset)])
        start+=len(target)
    return out


def main():
    args=argparse.ArgumentParser(description=__doc__)
    for key in ("physical","xrc","tt"):
        args.add_argument(key)
    args.add_argument("--threshold")
    opts=args.parse_args()
    final=PHYSICAL/opts.physical
    baseline=checked_measurements(PHYSICAL/"lml-comp-native-screen-20261118a",PHYSICAL/"sa-oa-old-xrc-20261118a")
    current=checked_measurements(final,PHYSICAL/opts.xrc)
    m=read(final/"manifest.json")
    native_source=(HERE/"virtuoso_core.il").read_bytes()+(HERE/"virtuoso_design.py").read_bytes()
    assert hashlib.sha256(native_source).hexdigest()==m["source"]["native_sha256"]
    assert m["source"]["electrical_sha256"]==digest(ROOT/"design/xtor/comparator/comparator.scs")
    stream=Stream(final/"fixture.gds")
    out=dict(host=m["host"],cellview=[m["library"],TOP,"layout"],
             evidence_root=m["checks"]["stream"]["command"][4].rsplit("/",2)[0],
             checkpoint_sha256=m["checkpoint_sha256"],rule_decks=m["decks"],
             xrc_deck=read(PHYSICAL/opts.xrc/"manifest.json")["deck"],
             baseline=baseline,current=current,readback=structure(final,current,stream),
             history={},tt_schematic=transient(SCHEMATIC),tt_prior_geometry=transient("sa-oa-prior-tt-20261118a"),
             tt_current=transient(opts.tt),
             stream_warnings=[s for s in (final/"stream.log").read_text(errors="replace").splitlines()
                              if s.startswith("WARNING")])
    assert out["tt_schematic"]["fixture_sha256"]==out["tt_current"]["fixture_sha256"]==out["tt_prior_geometry"]["fixture_sha256"]
    assert out["tt_current"]["gds_sha256"] == current["gds_sha256"]
    assert out["tt_prior_geometry"]["gds_sha256"] == baseline["gds_sha256"]
    if opts.threshold:
        out["deterministic_trip"]=trip_brackets(opts.threshold,current["gds_sha256"])
    for gate in sorted((ROOT/"work/output/managed_execution/runs").glob("sa-oa-trip-*")):
        summary=gate/"collected/derived/result.json"
        if gate.name!=opts.threshold and summary.is_file() and (gate/"collected/collection_receipt.json").is_file():
            prior=trip_brackets(gate.name,read(summary)["context"]["gds_sha256"])
            out.setdefault("trip_history_uV",{})[gate.name]={
                "gds_sha256":read(summary)["context"]["gds_sha256"],"result_sha256":prior["result_sha256"],
                "rising":prior["rising"]["bracket_uV"],"falling":prior["falling"]["bracket_uV"]}
    out["qualification"] = dict(drc="cell-level; raw global reminders retained",fill="prefill",
                                transient="TT 0.9 V 27 C; nominal deterministic single-block comparison",
                                coverage_excluded=["top-level routing and fill","integrated ADC timing","PVT",
                                                   "layout-dependent mismatch statistics","transient noise","latch-up and full-chip signoff"])
    for folder in sorted(PHYSICAL.glob("sa-oa-core-*")):
        if (folder/"manifest.json").is_file():
            r=read(folder/"manifest.json")
            out["history"][folder.name]=dict(oa_sha256=r.get("oa_sha256"),checkpoint_sha256=r.get("checkpoint_sha256"),
                                             markers=r["checks"].get("drc",{}).get("markers_by_rule"),
                                             lvs=r["checks"].get("lvs",{}).get("verdict"))
    for path in sorted((ROOT/"work/output/managed_execution/runs").glob("sa-oa-tt-*")):
        if path.name!=opts.tt and (path/"collected/derived/result.json").is_file():
            out.setdefault("tt_intermediate",{})[path.name]=transient(path.name)
    (HERE/"virtuoso_result.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    render(stream,read(final/"intent.json"),current["geometry"],HERE/"virtuoso_core.png")


if __name__=="__main__":
    main()
