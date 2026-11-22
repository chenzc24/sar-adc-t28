"""Local geometric pre-check of the core-internal routes against the streamed placement view.

For every route rectangle it finds block shapes on the same layer: overlaps are allowed only inside the
planned landing pins of that net, and every other block shape must keep the given clearance. Route
shapes of different nets must not touch and must keep the Mx minimum space. This is a screening aid
before Calibre DRC and connectivity, not a sign-off.
"""
import argparse
from collections import defaultdict
import json

import gdstk

from Layout.design.toplevel_routes import GDS, Rect, build
from Layout.project import ROOT

READBACK = ROOT / "Layout/results/toplevel_pin_readback.json"
# Planned landing pins per net (readback names).
LANDINGS = {
    "TOPN": ["XCDAC.TOPN", "XCOMP.VINN", "XBOOTN.VOUT"], "TOPP": ["XCDAC.TOPP", "XCOMP.VINP", "XBOOTP.VOUT"],
    "COMP_P": ["XCOMP.OUTP", "SAR.COMP_P"], "COMP_N": ["XCOMP.OUTN", "SAR.COMP_N"],
    "CMP_CLK": ["SAR.CMP_CLK", "XCOMP.CLK@trunk_top"],
    "SEQ_SAMPLE": ["SAR.SEQ_SAMPLE", "XBOOTN.CLKS", "XBOOTP.CLKS"],
    **{f"CODE{i}": [f"XREF.CODE{i}", f"SAR.CODE{i}"] for i in range(8)}, "PRESET": ["XREF.PRESET", "SAR.PRESET"],
}


def core_bbox(pin):
    """Pin bbox in the core frame from the readback local bbox and the block transform."""
    plan = json.loads((ROOT / "Layout/design/floorplan.json").read_bytes())
    owner = pin["owner_block"]
    b = next(x for x in plan["blocks"] if x["id"] == owner)
    tx, ty = b["native_origin_translation"]
    (x0, y0), (x1, y1) = pin["local_bbox"]
    if b.get("instance_orientation") == "MY":
        x0, x1 = -x1, -x0
    return (x0 + tx, y0 + ty, x1 + tx, y1 + ty)


def landing_boxes():
    rb = json.loads(READBACK.read_bytes())
    owner = {"XCDAC": "cdac", "XREF": "reference", "XCOMP": "comparator", "XBOOTN": "bootstrap_n",
             "XBOOTP": "bootstrap_p", "SAR": "sar"}
    out = {}
    for net, names in LANDINGS.items():
        boxes = []
        for n in names:
            p = dict(rb["pins"][n], owner_block=owner[n.split(".")[0]])
            boxes.append((n, p["lpp"][0], core_bbox(p)))
        out[net] = boxes
    return out


def distance(rect, poly, limit):
    """Smallest d (5 nm steps, up to limit) at which rect grown by d meets poly; None beyond limit."""
    r = gdstk.rectangle((rect.x0, rect.y0), (rect.x1, rect.y1))
    if gdstk.boolean(r, poly, "and"):
        return 0.0
    lo, hi = 0, round(limit / 0.005)
    grown = gdstk.offset(r, hi * 0.005, join="miter")
    if not gdstk.boolean(grown, poly, "and"):
        return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if gdstk.boolean(gdstk.offset(r, mid * 0.005, join="miter"), poly, "and"):
            hi = mid
        else:
            lo = mid
    return round(hi * 0.005, 3)


def check(gds, limit=0.3):
    routes = build()
    lib = gdstk.read_gds(str(gds))
    top = next(c for c in lib.cells if c.name == "sar8_adc_core").copy("flat")
    top.flatten()
    layers = {v: k for k, v in GDS.items()}
    block = defaultdict(list)
    for p in top.polygons:
        key = (p.layer, p.datatype)
        if key in layers:
            block[layers[key]].append(p)
    lands = landing_boxes()
    findings = []
    for s in routes.rects:
        for poly in block[s.layer]:
            (bx0, by0), (bx1, by1) = poly.bounding_box()
            if bx1 < s.x0 - limit or bx0 > s.x1 + limit or by1 < s.y0 - limit or by0 > s.y1 + limit:
                continue
            d = distance(s, poly, limit)
            if d is None:
                continue
            region = (max(s.x0, bx0), max(s.y0, by0), min(s.x1, bx1), min(s.y1, by1))
            landing = None
            if d == 0.0:
                for name, layer, (px0, py0, px1, py1) in lands.get(s.net, []):
                    if layer == s.layer and px0 - 1e-6 <= region[0] and region[2] <= px1 + 1e-6 \
                            and py0 - 1e-6 <= region[1] and region[3] <= py1 + 1e-6:
                        landing = name
            findings.append(dict(net=s.net, layer=s.layer, role=s.role, rect=[s.x0, s.y0, s.x1, s.y1],
                                 block_bbox=[round(v, 4) for v in (bx0, by0, bx1, by1)], distance_um=d,
                                 landing=landing))
    # Route-to-route spacing between different nets on one layer.
    internal = []
    by_layer = defaultdict(list)
    for s in routes.rects:
        by_layer[s.layer].append(s)
    for layer, rs in by_layer.items():
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a.net == b.net:
                    continue
                dx = max(b.x0 - a.x1, a.x0 - b.x1, 0)
                dy = max(b.y0 - a.y1, a.y0 - b.y1, 0)
                d = round((dx * dx + dy * dy) ** 0.5, 4)
                if d < 0.08:
                    internal.append(dict(layer=layer, nets=[a.net, b.net], a=[a.x0, a.y0, a.x1, a.y1],
                                         b=[b.x0, b.y0, b.x1, b.y1], distance_um=d))
    unexpected = [f for f in findings if f["distance_um"] == 0.0 and not f["landing"]]
    close = [f for f in findings if f["distance_um"] and f["distance_um"] < 0.1]
    landed = sorted({(f["net"], f["landing"]) for f in findings if f["landing"]})
    missing = [(net, n) for net, ls in lands.items() for n, _, _ in ls if (net, n) not in landed]
    return dict(route_rects=len(routes.rects), unexpected_overlaps=unexpected, block_shapes_within_0p1um=close,
                route_to_route_below_0p08um=internal, landed=landed, landings_without_overlap=missing,
                nearest_block_by_layer={L: min([f["distance_um"] for f in findings if f["layer"] == L
                                                and f["distance_um"] and not f["landing"]] or [None])
                                        for L in by_layer})


def regions():
    """Route shapes inside the keep-outs and TOP fill exclusions, each with the reason it is allowed."""
    plan = json.loads((ROOT / "Layout/design/floorplan.json").read_bytes())
    reg = {g["id"]: g["bbox"] for g in plan["reserved_regions"]}
    lands = landing_boxes()
    routes = build()

    def inside(s, box, strict=False):
        (x0, y0), (x1, y1) = box
        return s.x0 < x1 and s.x1 > x0 and s.y0 < y1 and s.y1 > y0

    def within(s, box):
        x0, y0, x1, y1 = box
        return x0 - 1e-6 <= s.x0 and s.x1 <= x1 + 1e-6 and y0 - 1e-6 <= s.y0 and s.y1 <= y1 + 1e-6

    out = {}
    for rid in ("cdac_array_keepout", "comparator_keepout", "top_fill_exclusion_tee", "top_fill_exclusion_inputs",
                "top_fill_exclusion_n_drop", "top_fill_exclusion_p_drop"):
        (x0, y0), (x1, y1) = reg[rid]
        rows = []
        for s in routes.rects:
            if not inside(s, reg[rid]):
                continue
            clipped = Rect(s.net, s.layer, max(s.x0, x0), max(s.y0, y0), min(s.x1, x1), min(s.y1, y1), s.role)
            pin = next((n for n, layer, box in lands.get(s.net, []) if layer == s.layer and within(clipped, box)), None)
            metal = int(s.layer[-1]) if s.layer.startswith(("M", "VIA")) else 0
            if rid == "cdac_array_keepout":
                why = f"inside the {pin} pin footprint" if pin else None
            elif rid == "comparator_keepout":
                low = s.layer in ("M1", "M2", "M3") or s.layer in ("VIA1", "VIA2")
                why = ("below M4" if low else
                       "accepted CMP_CLK drop (decisions.cmp_clk_north_drop)" if s.net == "CMP_CLK" else None)
            else:
                horizontal = (clipped.x1 - clipped.x0) >= (clipped.y1 - clipped.y0)
                drop = rid.endswith("_drop")
                if s.net in ("TOPN", "TOPP"):
                    why = "TOP net"
                elif s.net == "CMP_CLK" and rid == "top_fill_exclusion_inputs":
                    why = "accepted CMP_CLK drop (decisions.cmp_clk_north_drop)"
                elif s.net in ("COMP_P", "COMP_N") and rid == "top_fill_exclusion_inputs" and s.role == "riser":
                    why = "comparator output pin landing (riser start)"
                elif drop and horizontal and clipped.x1 - clipped.x0 >= x1 - x0 - 1e-6:
                    why = "right-angle crossing of the TOP drop"
                else:
                    why = None
            rows.append(dict(net=s.net, layer=s.layer, role=s.role, rect=[clipped.x0, clipped.y0, clipped.x1, clipped.y1],
                             allowed_because=why))
        out[rid] = dict(shapes=len(rows), not_allowed=[r for r in rows if not r["allowed_because"]],
                        non_top_nets=sorted({r["net"] for r in rows if r["net"] not in ("TOPN", "TOPP")}))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gds", help="stream of the placement view")
    ap.add_argument("--out")
    args = ap.parse_args()
    result = check(args.gds)
    text = json.dumps(result, indent=1)
    if args.out:
        (ROOT / args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
