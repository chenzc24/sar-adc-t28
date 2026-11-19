"""Compare a saved SAR placement to its electrical intent and trace actual metal and vias."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from klayout import db

from Layout.design.sar_timing import CORE, STD, SUFFIX
from Layout.project import ROOT

NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?", re.IGNORECASE)


def readback(path):
    placements, bindings, pads, ports = {}, defaultdict(dict), defaultdict(list), {}
    for line in path.read_text(encoding="utf-8").splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "VIEW":
            lib, cell, box = rest.split(maxsplit=2)
            bbox = list(map(float, NUM.findall(box)))
        elif kind == "INST":
            name, src, master, orient, coords = rest.split(maxsplit=4)
            values = list(map(float, NUM.findall(coords)))
            placements[name] = (src, master, orient, values[:2], values[2:])
        elif kind == "BIND":
            name, term, net = rest.split()
            bindings[name][term] = net
        elif kind == "LAND":
            name, term, layer, box = rest.split(maxsplit=3)
            pads[name, term].append((layer, list(map(float, NUM.findall(box)))))
        elif kind == "PORT":
            name, layer, box = rest.split(maxsplit=2)
            ports[name] = (layer, list(map(float, NUM.findall(box))))
    return (lib, cell, bbox), placements, bindings, pads, ports


def metal_graph(layout, top):
    profile = json.loads((ROOT / "Layout/specs/layout-query-t28.json").read_text())
    engine = db.LayoutToNetlist(CORE, layout.dbu)
    masks = {}
    for name, entry in (profile["metals"] | profile["vias"]).items():
        idx = layout.find_layer(*entry["layer"])
        if idx is None:
            continue
        r = db.Region(top.begin_shapes_rec(idx))
        engine.register(r, name)
        engine.connect(r)
        masks[name] = r
    for via, entry in profile["vias"].items():
        if via in masks:
            engine.connect(masks[entry["lower"]], masks[via])
            engine.connect(masks[entry["upper"]], masks[via])
    engine.extract_netlist()
    return engine, masks


def source_contacts(layout, top, intent, pads, component, component_nets, by_net):
    def polygons(number):
        return db.Region(top.begin_shapes_rec(layout.layer(number, 0))).merged()

    active = polygons(6) - polygons(17)
    cuts = polygons(30)
    poly = polygons(17)

    def point(x, y):
        return db.Point(round(x / layout.dbu), round(y / layout.dbu))

    def region_at(region, x, y):
        pt = point(x, y)
        # A small interior box avoids interpreting a boundary touch as contact.
        return region.interacting(db.Region(db.Box(pt.x - 1, pt.y - 1, pt.x + 1, pt.y + 1)))

    def add(n, name, term, x, y):
        ident = component("M1", x, y)
        by_net[n][name + "." + term].add(ident)
        component_nets[ident].add(n)
        return ident

    result = []
    for seam in intent["clear_rows"]:
        x, y, w = seam["x"], seam["y"], seam["width"]
        source = x if seam["shared"] else x - 0.065
        source_od = region_at(active, source, y + w / 2)
        if source_od.count() != 1:
            raise ValueError("Missing common source diffusion")
        contacts = cuts.inside(source_od)
        if not contacts.count():
            raise ValueError("Source has no contact cut")
        supply = seam["net"]
        tap = x + (-0.61 if supply == "VSS" else 0.61)
        for idx, name in enumerate(seam["devices"]):
            q = intent["instances"][name]
            src_rect = next(b for lay, b in pads[name, "S"] if lay == "OD")
            drain_rect = next(b for lay, b in pads[name, "D"] if lay == "OD")

            def mid(b):
                return (sum(b[::2]) / 2, sum(b[1::2]) / 2)

            if (
                region_at(source_od, *mid(src_rect)).is_empty()
                or not region_at(source_od, *mid(drain_rect)).is_empty()
            ):
                raise ValueError("Shared source/drain separation failed on " + name)
            src = add(supply, name, "S", source, y + 0.945)
            body = add(supply, name, "B", tap, y + 0.945)
            if body != src:
                raise ValueError("Source and body tap are disconnected")
            gate = q["xy"][0] + (0.015 if q["orient"] == "R0" else -0.015)
            gy = y - 0.19 if idx == 0 else y + w + 0.19
            pg = region_at(poly, gate, y + w / 2)
            if region_at(pg, gate, gy).is_empty() or region_at(cuts, gate, gy).is_empty():
                raise ValueError("Missing contact to clear gate " + name)
            add(q["pins"]["G"], name, "G", gate, gy)
        if seam["shared"]:
            result.append({"devices": seam["devices"], "net": supply, "contact_count": contacts.count()})
    return result


def comparator_escapes(layout, top, ports, intent, component):
    m2 = db.Region(top.begin_shapes_rec(layout.layer(32, 0))).merged()
    v1 = db.Region(top.begin_shapes_rec(layout.layer(51, 0))).merged()
    data = {}
    for n, block, term in (
        ("COMP_N", "X003/X000", "I"),
        ("COMP_P", "X002/X000", "I"),
        ("CMP_CLK", "X025/X001", "ZN"),
    ):
        inst = "XCTRL__XTIM__" + block.replace("/", "__") + "__XLIB"
        _layer, p = ports[n]
        px, py = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        matches = [
            (x, y)
            for name, pin, l, x, y in intent["access_checks"]
            if name == inst and pin == term and l == 1 and abs(py - y) < 0.0001
        ]
        ((x, y),) = matches

        def dbu(v):
            return round(v / layout.dbu)

        straight = db.Region(db.Box(dbu(px), dbu(y - 0.015), dbu(x), dbu(y + 0.015)))
        if not (straight - m2).is_empty() or component("M2", px, py) != component("M1", x, y):
            raise ValueError("Incomplete comparator breakout " + n)
        cut_count = v1.interacting(straight).count()
        if cut_count != 1:
            raise ValueError("Unexpected breakout cuts " + n)
        data[n] = {
            "metal": "M2",
            "centerline_um": round(x - px, 4),
            "via1_cuts": cut_count,
            "pin_center_um": [round(px, 4), round(py, 4)],
        }
    return data


def inspect(intent_path, folder):
    intent = json.loads(intent_path.read_text())
    physical = json.loads((folder / "sar-physical.json").read_text())
    if hashlib.sha256((folder / "fixture.gds").read_bytes()).hexdigest() != physical["gds_sha256"]:
        raise ValueError("GDS does not match the DRC input")
    identity, placed, bindings, pads, ports = readback(folder / "sar-readback.txt")
    fill = {"FILL_ODPO": "sar8_timing_fill_odpo", "FILL_METAL": "sar8_timing_fill_metal"}
    extra = placed.keys() - intent["instances"].keys()
    if extra and (
        extra != fill.keys()
        or any(placed[n][:4] != (identity[0], fill[n], "R0", [0.0, 0.0]) or bindings[n] for n in extra)
    ):
        raise ValueError("Unexpected physical-only instances")
    if identity[:2] != (physical["library"], CORE) or set(placed) - extra != set(intent["instances"]):
        raise ValueError("OA identity or instance set changed")
    for name, q in intent["instances"].items():
        lib, master, orient, xy, _ = placed[name]
        expected_lib = STD if q["master"].endswith(SUFFIX) else "tsmcN28"
        if (
            lib != expected_lib
            or (master, orient, xy) != (q["master"], q["orient"], q["xy"])
            or bindings[name] != q["pins"]
        ):
            raise ValueError("OA readback differs at " + name)
    if set(ports) != set(intent["ports"]) or sorted(ports) != physical["labels"]:
        raise ValueError("Wrong OA/stream interface")
    layout = db.Layout()
    layout.read(str(folder / "fixture.gds"))
    top = layout.cell(CORE)
    engine, masks = metal_graph(layout, top)

    def component(layer, x, y):
        p = db.Point(round(x / layout.dbu), round(y / layout.dbu))
        hit = engine.probe_net(masks[layer], p)
        if hit is None:
            raise ValueError(f"Missing {layer} on {x:g}, {y:g}")
        return hit.cluster_id

    component_nets = defaultdict(set)
    by_net = defaultdict(lambda: defaultdict(set))
    for (name, pin), shapes in pads.items():
        n = bindings[name][pin]
        for layer, (x0, y0, x1, y1) in shapes:
            if layer not in masks:
                continue
            c = component(layer, (x0 + x1) / 2, (y0 + y1) / 2)
            component_nets[c].add(n)
            by_net[n][name + "." + pin].add(c)
    for n, (layer, (x0, y0, x1, y1)) in ports.items():
        c = component(layer, (x0 + x1) / 2, (y0 + y1) / 2)
        component_nets[c].add(n)
        by_net[n]["PORT " + n].add(c)
    pairs = source_contacts(layout, top, intent, pads, component, component_nets, by_net)
    escapes = comparator_escapes(layout, top, ports, intent, component)
    shorts = [{"component": k, "nets": sorted(v)} for k, v in component_nets.items() if len(v) > 1]
    traced, unjoined = {}, {}
    for n, terms in by_net.items():
        common = set.intersection(*terms.values()) if terms else set()
        if len(common) == 1 and len(component_nets[next(iter(common))]) == 1:
            traced[n] = len(terms)
        else:
            unjoined[n] = len(set.union(*terms.values()))
    expected = set(intent["routed_signal_candidates"])
    rc_nets = [intent["instances"][b["resistor"]]["pins"]["MINUS"] for b in intent["banks"]]
    summary = {
        "identity": physical["identity"],
        "view": "/".join([identity[0], CORE, physical.get("view", "layout")]),
        "bbox_um": identity[2],
        "electrical_inputs": intent["inputs"],
        "gds_sha256": physical["gds_sha256"],
        "structural_sha256": physical["geometry_sha256"],
        "instance_counts": dict(
            sorted(Counter(q["master"] for q in intent["instances"].values()).items())
        ),
        "instances_checked": len(placed),
        "terminal_bindings_checked": sum(map(len, bindings.values())),
        "native_ports": len(ports),
        "shared_source_pairs": pairs,
        "comparator_escapes": escapes,
        "total_electrical_nets": len(intent["nets"]),
        "metal_tested_nets": len(by_net),
        "routed_nets_without_foreign_terminals": {n: traced[n] for n in sorted(traced)},
        "intended_routes_with_unjoined_or_shorted_terminals": {
            n: unjoined.get(n) for n in sorted(expected - traced.keys())
        },
        "rc_nodes_with_all_metal_endpoints_joined": {n: traced.get(n) for n in rc_nets},
        "foreign_net_clusters": shorts,
        "multiple_or_conflicting_components": {n: unjoined[n] for n in sorted(unjoined)},
        "drc_markers": physical["drc_total"],
        "drc_rule_counts": physical["rules"],
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intent", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument(
        "--require-complete", action="store_true", help="Require every source net to be joined"
    )
    args = parser.parse_args()
    result = inspect(args.intent, args.checkpoint)
    (args.checkpoint / "metal-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "instances_checked",
                    "native_ports",
                    "metal_tested_nets",
                    "intended_routes_with_unjoined_or_shorted_terminals",
                    "rc_nodes_with_all_metal_endpoints_joined",
                    "foreign_net_clusters",
                    "drc_rule_counts",
                )
            },
            indent=2,
        )
    )

    if (
        result["intended_routes_with_unjoined_or_shorted_terminals"]
        or result["foreign_net_clusters"]
        or (
            args.require_complete
            and len(result["routed_nets_without_foreign_terminals"]) != result["total_electrical_nets"]
        )
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
