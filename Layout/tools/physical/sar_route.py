"""Build the routing abstract from the actual, partially connected SAR core.

Every pin of the abstract represents one physical conductor. The router can
join equivalent source nets across conductors but cannot route through cell
metal, MOM fingers or the already verified delay connections.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from klayout import db

from Layout.design.sar_timing import CORE
from Layout.tools.analysis.check_sar_timing import metal_graph, readback, source_contacts


def conductor_map(layout, top, intent, metadata):
    _, _, bindings, pads, ports = metadata
    engine, masks = metal_graph(layout, top)
    assigned = defaultdict(set)
    by_net = defaultdict(lambda: defaultdict(set))
    objects = {}

    def at(layer, x, y):
        found = engine.probe_net(masks[layer], db.Point(round(x / layout.dbu), round(y / layout.dbu)))
        if found is None:
            raise ValueError(f"No metal at {layer} ({x}, {y})")
        objects[found.cluster_id] = found
        return found.cluster_id

    def bind(net, terminal, layer, box):
        cid = at(layer, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        assigned[cid].add(net)
        by_net[net][terminal].add(cid)

    for (name, pin), locations in pads.items():
        for layer, box in locations:
            if layer in masks and layer.startswith("M"):
                bind(bindings[name][pin], name + "." + pin, layer, box)
    for net, (layer, box) in ports.items():
        bind(net, "PORT." + net, layer, box)
    source_contacts(layout, top, intent, pads, at, assigned, by_net)
    shorts = {c: ns for c, ns in assigned.items() if len(ns) != 1}
    if shorts:
        raise ValueError("Foreign-net cluster: " + str(shorts))
    return engine, masks, objects, {k: next(iter(v)) for k, v in assigned.items()}, by_net


def geometry(region, layer, scale):
    if region.is_empty():
        return []
    rows = [f"      LAYER {layer} ;"]
    for piece in region.merged().decompose_trapezoids_to_region().each():
        b = piece.bbox()
        if b.area() == piece.area():
            coords = (b.left, b.bottom, b.right, b.top)
            kind = "RECT"
        else:
            coords = [q for point in piece.each_point_hull() for q in (point.x, point.y)]
            kind = "POLYGON"
        rows.append("        " + kind + " " + " ".join(f"{q * scale:.3f}" for q in coords) + " ;")
    return rows


def prepare(intent_path, checkpoint, out):
    intent = json.loads(intent_path.read_text())
    layout = db.Layout()
    layout.read(str(checkpoint / "fixture.gds"))
    top = layout.cell(CORE)
    native = readback(checkpoint / "sar-readback.txt")
    e, masks, objects, labels, by_net = conductor_map(layout, top, intent, native)
    mom_keepout = db.Region()
    if "mom_route_clearance_um" in intent:
        for _, master, _, _, bounds in native[1].values():
            if master == "cfmom_2t":
                mom_keepout.insert(db.Box(*(round(v / layout.dbu) for v in bounds)))
        mom_keepout = mom_keepout.sized(round(intent["mom_route_clearance_um"] / layout.dbu)).merged()
    mom_layers = {"M1", "M2", "M3", "V1", "V2"}
    out.mkdir(exist_ok=True, parents=True)
    width, height = intent.get("routing_outline_um", (39.76, 54.40))
    lef = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO ROUTEBASE",
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {width:.3f} BY {height:.3f} ;",
        "  SYMMETRY X Y ;",
    ]
    claimed = {layer: db.Region() for layer in masks}
    names = {}
    grouped = {}
    for net, terms in sorted(by_net.items()):
        if set.intersection(*terms.values()):
            continue
        ids = sorted(set.union(*terms.values()))
        grouped[net] = []
        for k, cid in enumerate(ids):
            pin = f"P{cid}"
            grouped[net].append(pin)
            for level in range(6, 0, -1):
                layer = f"M{level}"
                if layer not in masks:
                    continue
                r = e.shapes_of_net(objects[cid], masks[layer], True).merged()
                if layer in mom_layers:
                    r -= mom_keepout
                if r.is_empty():
                    continue
                claimed[layer] += r
                lef += [
                    "  PIN " + pin,
                    "    DIRECTION " + ("OUTPUT" if k == 0 else "INPUT") + " ;",
                    "    USE SIGNAL ;",
                    "    PORT",
                    *geometry(r, layer, layout.dbu),
                    "    END",
                    "  END " + pin,
                ]
                names[pin] = {"source_net": net, "cluster": cid, "layer": layer}
                break
            else:
                raise ValueError(f"Empty conductor for {net}")
    lef.append("  OBS")
    for layer, mask in masks.items():
        pdk_layer = ("VIA" + layer[1:]) if layer.startswith("V") else layer
        blocked = (mask | mom_keepout) if layer in mom_layers else mask
        lef.extend(geometry(blocked - claimed[layer], pdk_layer, layout.dbu))
    lef += ["  END", "END ROUTEBASE", "END LIBRARY"]
    (out / "fixed.lef").write_text("\n".join(lef) + "\n", encoding="ascii")
    nets = {n: f"n{i:03}" for i, n in enumerate(grouped)}
    v = [
        "module sar_route_overlay ();",
        *["wire " + wire + ";" for wire in nets.values()],
        "ROUTEBASE u_base (",
    ]
    v.append(",\n".join(f"  .{pin}({nets[net]})" for net in grouped for pin in grouped[net]))
    (out / "route.v").write_text("\n".join(v + [");", "endmodule", ""]), encoding="ascii")
    # Top-level ports remain in OA. The router only adds conductors between the abstract pins.
    d = [
        "VERSION 5.8 ;",
        'DIVIDERCHAR "/" ;',
        'BUSBITCHARS "[]" ;',
        "DESIGN sar_route_overlay ;",
        "UNITS DISTANCE MICRONS 1000 ;",
        f"DIEAREA ( 0 0 ) ( {round(width * 1000)} {round(height * 1000)} ) ;",
        "COMPONENTS 1 ;",
        "- u_base ROUTEBASE + FIXED ( 0 0 ) N ;",
        "END COMPONENTS",
        f"NETS {len(nets)} ;",
    ]
    for net, pins in grouped.items():
        d.append(f"- {nets[net]} " + " ".join(f"( u_base {pin} )" for pin in pins) + " + USE SIGNAL ;")
    d += ["END NETS", "END DESIGN"]
    (out / "input.def").write_text("\n".join(d) + "\n", encoding="ascii")
    (out / "outline.tcl").write_text(f"set core_width {width:.3f}\nset core_height {height:.3f}\n", encoding="ascii")
    (out / "map.json").write_text(json.dumps({"nets": nets, "pins": names}, indent=2))
    print(f"{len(nets)} nets, {len(names)} physical conductors, {len(lef)} LEF records")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("intent", type=Path)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    prepare(a.intent, a.checkpoint, a.out)
