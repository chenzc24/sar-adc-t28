"""Combine the detailed route with the native base and emit net-bound OA polygons."""

import argparse
import hashlib
import json
from pathlib import Path
from klayout import db
from Layout.design.sar_timing import CORE
from Layout.project import ROOT
from Layout.tools.analysis.check_sar_timing import readback
from Layout.tools.physical.sar_route import conductor_map


def overlay_shapes(path):
    ly = db.Layout()
    ly.read(str(path))
    top = ly.top_cell()
    layers = {}
    for idx in ly.layer_indexes():
        info = ly.get_info(idx)
        r = db.Region(top.shapes(idx))
        for i in top.each_inst():
            if i.cell.name == "ROUTEBASE":
                continue
            if not i.cell.name.startswith(("VIA", "NR_VIA")):
                raise ValueError(i.cell.name)
            r += db.Region(i.cell.begin_shapes_rec(idx)).transformed(i.trans)
        if not r.is_empty():
            layers[info.layer, info.datatype] = r.merged()
    return layers


def run(intent, base, route, permissive=False):
    meta = readback(base / "sar-readback.txt")
    ly = db.Layout()
    ly.read(str(base / "fixture.gds"))
    t = ly.cell(CORE)
    assert abs(ly.dbu - 0.001) < 1.0e-12
    additions = overlay_shapes(route / "overlay.gds")
    metadata = json.loads((base / "sar-physical.json").read_text())
    design = json.loads(intent.read_text())
    overlay_hash = hashlib.sha256((route / "overlay.gds").read_bytes()).hexdigest()
    repairs = {}
    if "routing_outline_um" not in design:
        reviewed = json.loads((ROOT / "Layout/design/sar-route-repairs.json").read_text())
        if overlay_hash == reviewed["overlay_sha256"]:
            if metadata["geometry_sha256"] != reviewed["seed_geometry_sha256"]:
                raise ValueError("The archived Innovus overlay belongs to a different base")
            repairs = reviewed["repairs"]
    if repairs:
        for layer, changes in repairs.items():
            key = int(layer), 0
            r = additions.get(key, db.Region())
            for op, box in changes:
                if op not in ("add", "remove"):
                    raise ValueError("Unknown route repair operation " + op)
                b = db.Region(db.Box(*box))
                r = r - b if op == "remove" else r + b
            additions[key] = r.merged()
    for (n, d), r in additions.items():
        t.shapes(ly.layer(n, d)).insert(r)
    ly.write(str(route / "combined.gds"))
    engine, masks, _, labels, ends = conductor_map(ly, t, design, meta)
    if set(ends) != set(design["nets"]):
        raise ValueError("Native metal audit does not cover the source net set")
    opened = {n: len(set.union(*v.values())) for n, v in ends.items() if not set.intersection(*v.values())}
    print("GDS connectivity", len(ends), "nets, opens", opened)
    if opened and not permissive:
        raise ValueError("Incomplete metal")
    lines = []
    for (n, d), r in sorted(additions.items()):
        layer = "M" + str(n - 30) if 31 <= n <= 36 else "V" + str(n - 50)
        native = layer.replace("V", "VIA")
        for poly in r.decompose_trapezoids_to_region().each():
            bb = poly.bbox()
            if poly.area() != bb.area():
                raise ValueError("Non-Manhattan detailed route")
            hit = engine.probe_net(masks[layer], bb.center())
            name = labels.get(hit.cluster_id) if hit else None
            if name is None:
                raise ValueError(f"Orphan detailed routing at {native} {bb}")
            coords = " ".join(str(v) for v in (bb.left, bb.bottom, bb.right, bb.top))
            lines.append(f"{native} {name} {coords}")
    (route / "route-rects.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    record = {
        "seed_geometry_sha256": metadata["geometry_sha256"],
        "intent_sha256": hashlib.sha256(intent.read_bytes()).hexdigest(),
        "innovus_stream_sha256": overlay_hash,
        "archived_repairs_applied": bool(repairs),
        "connected_nets": len(ends) - len(opened),
    }
    (route / "route-provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    (route / "apply-route.il").write_text(
        'load("sar_timing.il")\n'
        f'if(errset(stApplyDetailedRoute(getShellEnvVar("SAR_ROUTED_VIEW") {len(design["instances"])}) t) '
        'then exit(0) else exit(1))\n',
        encoding="ascii",
    )
    print(len(lines), "net-bound rectangles")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("intent", type=Path)
    ap.add_argument("base", type=Path)
    ap.add_argument("route", type=Path)
    args = ap.parse_args()
    run(args.intent, args.base, args.route)
