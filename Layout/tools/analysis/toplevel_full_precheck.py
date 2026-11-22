"""Local spacing screen of the Stage 4b rectangles before a build (not a DRC sign-off).

Checks, per layer, the new rectangles against each other, against the Stage 4a routes of layout_route_int and
against the flattened block geometry of the placement stream: different nets must not touch and must keep the
width/run-length dependent minimum space; same-net shapes must either touch or keep that space (no slivers).
PCell geometry is not included.
"""
import argparse
from collections import defaultdict
import json

import gdstk

from Layout.design.toplevel_full_routes import build
from Layout.project import ROOT

LAYERS = {f"M{i}": (30 + i, 0) for i in range(2, 10)} | {f"VIA{i}": (50 + i, 0) for i in range(1, 9)}


def required(layer, wa, wb, prl):
    w = max(wa, wb)
    if layer == "M9":
        return 1.5 if w > 4.5 and prl > 4.5 else 1.0
    if layer == "M8":
        return 1.5 if w > 4.5 and prl > 4.5 else 0.5 if w > 1.5 and prl > 1.5 else 0.4
    if layer in ("VIA7", "VIA8"):
        return 0.34
    if layer.startswith("VIA"):
        return 0.08 if prl > -0.04 else 0.07
    for wl, pl, s in ((1.5, 1.5, 0.5), (0.63, 0.63, 0.15), (0.47, 0.47, 0.13), (0.16, 0.22, 0.1), (0.13, 0.22, 0.08),
                      (0.09, 0.22, 0.06)):
        if w > wl and prl > pl:
            return s
    return 0.05


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    # parallel run length: overlap of projections on the axis perpendicular to the gap
    prl = (min(a[3], b[3]) - max(a[1], b[1])) if dx > 0 else (min(a[2], b[2]) - max(a[0], b[0]))
    return (dx * dx + dy * dy) ** 0.5, prl, dx == 0 and dy == 0


def width(r):
    return min(r[2] - r[0], r[3] - r[1])


def check(base_gds, routes_json, limit=1.6):
    c = build()
    new = [(r["net"], r["layer"], tuple(r["box"])) for r in c.rects]
    old = [(n, l, tuple(b)) for n, l, *b, _ in json.loads((ROOT / routes_json).read_bytes())["rects"]]
    old = [(n if n != "VSS_SHIELD" else "0", l, b) for n, l, b in old]
    lib = gdstk.read_gds(str(base_gds))
    top = next(x for x in lib.cells if x.name == "sar8_adc_core").copy("f")
    top.flatten()
    inv = {v: k for k, v in LAYERS.items()}
    blocks = [("#block", inv[(p.layer, p.datatype)], tuple(round(v, 4) for xy in p.bounding_box() for v in xy))
              for p in top.polygons if (p.layer, p.datatype) in inv]
    grid = defaultdict(list)
    cell = 2.0
    def key(box):
        for i in range(int(box[0] // cell) - 1, int(box[2] // cell) + 2):
            for j in range(int(box[1] // cell) - 1, int(box[3] // cell) + 2):
                yield i, j
    allshapes = [("new",) + s for s in new] + [("4a",) + s for s in old] + [("blk",) + s for s in blocks]
    for idx, (_, _, layer, box) in enumerate(allshapes):
        for k in key(box):
            grid[(layer,) + k].append(idx)
    findings = defaultdict(list)
    seen = set()
    for ia, (sa, na, layer, a) in enumerate(allshapes):
        if sa != "new":
            continue
        for k in key(a):
            for ib in grid[(layer,) + k]:
                if ib == ia or (min(ia, ib), max(ia, ib)) in seen:
                    continue
                seen.add((min(ia, ib), max(ia, ib)))
                sb, nb, _, b = allshapes[ib]
                d, prl, touch = gap(a, b)
                if d > limit:
                    continue
                req = required(layer, width(a), width(b), prl)
                if sb == "blk":
                    if touch:
                        findings["touches_block"].append((layer, na, a, b))
                    elif d < req - 1e-6:
                        findings["near_block"].append((layer, na, a, b, round(d, 3), req))
                    continue
                if na != nb:
                    if touch:
                        findings["short"].append((layer, na, nb, a, b))
                    elif d < req - 1e-6:
                        findings["spacing"].append((layer, na, nb, a, b, round(d, 3), req))
                elif not touch and d < req - 1e-6 and not layer.startswith("VIA"):
                    # A third same-net shape that covers the gap closes it.
                    gx0, gx1 = sorted((min(a[2], b[2]), max(a[0], b[0])))
                    gy0, gy1 = sorted((min(a[3], b[3]), max(a[1], b[1])))
                    if gx1 - gx0 < 1e-9:
                        gx0, gx1 = max(a[0], b[0]), min(a[2], b[2])
                    if gy1 - gy0 < 1e-9:
                        gy0, gy1 = max(a[1], b[1]), min(a[3], b[3])
                    covered = any(allshapes[ic][1] == na and allshapes[ic][3][0] <= gx0 + 1e-9
                                  and allshapes[ic][3][2] >= gx1 - 1e-9 and allshapes[ic][3][1] <= gy0 + 1e-9
                                  and allshapes[ic][3][3] >= gy1 - 1e-9
                                  for kk in key((gx0, gy0, gx1, gy1)) for ic in grid[(layer,) + kk])
                    if not covered:
                        findings["same_net_sliver"].append((layer, na, a, b, round(d, 3), req))
                elif layer.startswith("VIA") and not touch and d < req - 1e-6:
                    findings["via_spacing"].append((layer, na, a, b, round(d, 3), req))
                elif layer.startswith("VIA") and touch and a != b:
                    findings["via_overlap"].append((layer, na, a, b))
    return {k: v for k, v in findings.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("base_gds")
    ap.add_argument("routes_json", help="routes.json of the Stage 4a geometry (work/layout/toplevel-route/<id>/)")
    args = ap.parse_args()
    f = check(args.base_gds, args.routes_json)
    print(json.dumps({k: len(v) for k, v in f.items()}))
    for k, v in f.items():
        print("##", k)
        for row in v[:12]:
            print("  ", row)


if __name__ == "__main__":
    main()
