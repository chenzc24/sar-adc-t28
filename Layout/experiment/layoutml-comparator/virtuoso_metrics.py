"""Measure the streamed physical outline and the explicit Calibre RC network."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from klayout import db as kdb

TOP="sar_strongarm_lml_exp"


def outlines(gds):
    lay=kdb.Layout()
    lay.read(str(gds))
    cell=lay.cell(TOP)
    assert cell and lay.dbu==.001
    def shapes(layer,typ=0):
        idx=lay.find_layer(layer,typ)
        return kdb.Region(cell.begin_shapes_rec(idx)).merged() if idx is not None else kdb.Region()
    bbox=cell.bbox()
    diffusion=shapes(6)
    gates=shapes(17)&diffusion
    active=kdb.Region()
    for polygon in diffusion.each():
        if not (kdb.Region(polygon)&gates).is_empty():
            active.insert(polygon)
    return {"bbox_nm":[bbox.left,bbox.bottom,bbox.right,bbox.top],
            "width_um":bbox.width()*.001, "height_um":bbox.height()*.001,
            "area_um2":bbox.area()*1e-6,"active_gate_boxes_nm":[[b.left,b.bottom,b.right,b.top] for b in
                    sorted((p.bbox() for p in gates.each()),key=lambda b:(b.bottom,b.left))],
            "mos_active_od_area_um2":active.area()*1e-6,"mos_active_od_islands":active.count(),
            "metal_area_um2":{n:shapes(k).area()*1e-6 for k,n in ((31,"M1"),(32,"M2"),(33,"M3"),(34,"M4"))},
            "via_cuts":{n:shapes(k).count() for k,n in ((51,"VIA1"),(52,"VIA2"),(53,"VIA3"))},
            "contacts":shapes(30).count()}


def explicit_caps(pex_dir):
    def content(name):
        return (pex_dir/name).read_text(encoding="latin1").replace("\\\n"," ")
    def ff(value):
        suffix={"a":1e-3,"f":1.0,"p":1e3,"n":1e6}
        if value[-1] in suffix:return float(value[:-1])*suffix[value[-1]]
        return float(value)*1e15
    bindings=content("extracted.scs."+TOP+".pxi")
    device_table=content("extracted.scs")
    internal=content("extracted.scs.pex")
    owners={"VDD":"VDD","VSS":"VSS","0":"0"}
    for m in re.finditer(r"^x_PM_\S+?\\%(\w+)\s+\(([^)]*)\)\s+PM_",bindings,re.M):
        for node in m[2].split():
            if node=="0":continue
            assert owners.setdefault(node,m[1])==m[1]
    inputs={}
    input_geometry={}
    for m in re.finditer(r"^X\S+\s+\(\s*(\S+)\s+(\S+)\s+(\S+)\s+\S+\s*\)\s+nch_mac\b([^\n]*)",device_table,re.M):
        drain,gate,source=[owners[n] for n in m.groups()[:3]]
        if gate in ("VINN","VINP"):
            inputs[gate]={drain,source}
            input_geometry[gate]=dict(re.findall(r"\b(\w+)=([^\s]+)",m[4].split("//")[0]))
    tail,=inputs["VINN"] & inputs["VINP"]
    a,=inputs["VINN"]-{tail}
    b,=inputs["VINP"]-{tail}
    names={tail:"TAIL",a:"X",b:"Y"}
    ground=Counter()
    coupling=Counter()
    count_ground=count_mutual=0
    for m in re.finditer(r"^subckt PM_\S+?\\%(\w+)\s+\([^)]*\)(.*?)^ends\b",internal,re.M|re.S):
        net=names.get(m[1],m[1])
        for c in re.finditer(r"^c\S+\s+\(\s*(\S+)\s+(\S+)\s*\)\s+capacitor c=(\S+)",m[2],re.M|re.I):
            if "0" in (c[1],c[2]):
                ground[net]+=ff(c[3]);count_ground+=1
    for c in re.finditer(r"^cc_\S+\s+\(\s*(\S+)\s+(\S+)\s*\)\s+capacitor c=(\S+)",bindings,re.M|re.I):
        first,second=[names.get(owners[n],owners[n]) for n in (c[1],c[2])]
        assert first!=second
        coupling[tuple(sorted([first,second]))]+=ff(c[3]);count_mutual+=1
    assert count_mutual and count_ground
    nets=set(ground) | {n for pair in coupling for n in pair}
    metrics={n:{"to_ground_fF":ground[n],"to_other_nets_fF":sum(c for pair,c in coupling.items() if n in pair)}
             for n in sorted(nets)}
    for ns in metrics.values():ns["total_fF"]=sum(ns.values())
    return {"method":"Each explicit capacitance to 0 and each coupling to a different equipotential net, with other nets held at AC ground. Excludes MOS model capacitances and external testbench loads.",
            "internal_net_names":names,"ground_cap_count":count_ground,"mutual_cap_count":count_mutual,
            "input_instance_parameter_count":{n:len(v) for n,v in input_geometry.items()},
            "unequal_input_instance_parameters":sorted(k for k in set(input_geometry["VINP"])|set(input_geometry["VINN"])
                                                       if input_geometry["VINP"].get(k)!=input_geometry["VINN"].get(k)),
            "per_net":metrics,"mutual_fF":{"-".join(k):v for k,v in sorted(coupling.items())}}


def checked_measurements(physical,extraction):
    manifest=json.loads((physical/"manifest.json").read_text())
    rc=json.loads((extraction/"manifest.json").read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert manifest["status"]==rc["status"]=="completed" and rc["binding"]["source_run"]==physical.name
    assert sha(physical/"fixture.gds")==manifest["gds"]["sha256"]==rc["gds_sha256"]
    for n,h in rc["netlists"].items():assert sha(extraction/"pex"/n)==h
    return {"physical_run":physical.name,"xrc_run":extraction.name,"oa_sha256":manifest["oa_sha256"],
            "gds_sha256":rc["gds_sha256"],"extracted_hashes":rc["netlists"],
            "source":manifest["source"],"lvs":manifest["checks"]["lvs"]["verdict"],
            "markers":manifest["checks"]["drc"]["markers_by_rule"],
            "geometry":outlines(physical/"fixture.gds"),"capacitance":explicit_caps(extraction/"pex")}
