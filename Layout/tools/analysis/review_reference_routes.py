"""Read saved OA geometry, verify every M6 gate branch, and draw the south interface."""
import argparse
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from Layout.design.reference_driver import CDAC, CDAC_VIEW, COMBINED, DRIVER, LIBRARY
from Layout.project import ROOT, write_json


def query(cell, view, *args):
    target = f"{LIBRARY}/{cell}/{view}"
    for delay in (0, 2, 4):
        time.sleep(delay)
        run = subprocess.run(["oaq", "--saved", target, *args], capture_output=True, timeout=120)
        result = json.loads(run.stdout)
        if run.returncode == 0 and result["status"] == "ok" and result["context"]["cellview"] == target.split("/"):
            break
        reasons = result.get("reasons", [])
        if not any("timeout" in r.lower() for r in reasons) or delay == 4:
            raise ValueError(f"Incomplete OA read for {target}: {reasons}")
    return result


def center(box):
    return tuple(round((a + b) / 2, 4) for a, b in zip(*box))


def endpoints(box):
    # The M6 rectangles have square caps, half a wire width at either end.
    (x0, y0), (x1, y1) = box
    x, y = center(box)
    dx, dy = x1 - x0, y1 - y0
    if abs(min(dx, dy) - .16) > 1e-5:
        raise ValueError("Unexpected width on the joined M6 gate route")
    points = [(x0 + dy / 2, y), (x1 - dy / 2, y)] if dx > dy else [(x, y0 + dx / 2), (x, y1 - dx / 2)]
    return [tuple(round(v, 4) for v in p) for p in points]


def verify(figures, pins, ports):
    adjacency = defaultdict(list)
    total = 0.
    for fig in figures:
        a, b = endpoints(fig["bbox"])
        d = abs(a[0] - b[0]) + abs(a[1] - b[1])
        adjacency[a].append((b, d))
        adjacency[b].append((a, d))
        total += d
    start, *ends = [pins[p] for p in ports]
    distances = {start: 0.}
    stack = [start]
    while stack:
        a = stack.pop()
        for b, length in adjacency[a]:
            if b not in distances:
                distances[b] = distances[a] + length
                stack.append(b)
    if len(figures) not in (3, 5) or len(distances) != len(figures) + 1 or any(len(adjacency[p]) != 1 for p in [start, *ends]):
        raise ValueError(f"Disconnected or unexpected branch at {ports}")
    return round(total, 4), [round(distances[p], 4) for p in ends]


def review(identity, image=None):
    out = ROOT / "work/layout/reference-driver" / identity
    intent = json.loads((out / "intent.json").read_bytes())
    view = intent["view"]
    outputs = [n for n in intent["driver_ports"] if n.startswith("G")]
    targets = {n: [p for p, v in intent["cdac_pin_binding"].items() if v == n] for n in outputs}
    args = [arg for n in outputs for child, port in [("XREF", n), *(("XCDAC", p) for p in targets[n])]
            for arg in ("--at", child, port)]
    batch = query(COMBINED, view, "pins", *args)
    pins = {}
    for pin in batch["pins"]:
        fig, = pin["figures"]
        if pin["status"] != "ok" or fig["lpp"] != ["M6", "drawing"]:
            raise ValueError("Missing M6 pin")
        pins[(fig["path"][0], pin["terminal"])] = center(fig["bbox"])
    m6 = query(COMBINED, view, "shapes", "--layer", "M6")["figures"]
    m3 = query(DRIVER, view, "shapes", "--layer", "M3")["figures"]
    cells = query(DRIVER, view, "instances")["instances"]
    blocks = query(COMBINED, view, "instances")["instances"]
    routes, branches = {}, {}
    for n, receivers in targets.items():
        wire = [f for f in m6 if f["type"] == "rect" and f.get("net") == n]
        routes[n], lengths = verify(wire, pins, [("XREF", n), *(("XCDAC", p) for p in receivers)])
        branches.update(zip(receivers, lengths))
    result = dict(cellview=batch["context"]["cellview"], frame=batch["context"]["frame"],
                  units=batch["context"]["units"], m6_tree_um=routes, branch_um=branches,
                  total_m6_um=round(sum(routes.values()), 4),
                  bbox_by_instance={i["path"][-1]: i["bbox"] for i in blocks},
                  active_instances={i["path"][-1]: i["master"][1] for i in cells if i["path"][-1].startswith("X")})
    ref_rails = []
    if len(outputs) == 16:
        # Both children are placed R0 at (0, 0). Check the CDAC half-cell
        # conductors that extend into the B0 escape, including both VREF drops.
        for side, half in (("N", "XN"), ("P", "XP")):
            gate = f"G{side}N0"
            xs = [pins[("XCDAC", p)][0] for p in targets[gate]]
            region = [str(min(xs) - .3), "-26.5", str(max(xs) + .3), "-23.75"]
            shapes = query(CDAC, CDAC_VIEW, "shapes", "--path", f"XCORE/{half}",
                           "--layer", "M6", "--region", *region)["figures"]
            rails = [f for f in shapes if f.get("net") in ("VREFP", "VREFN") and f["lpp"] == ["M6", "drawing"]]
            if {f["net"] for f in rails} != {"VREFP", "VREFN"}:
                raise ValueError(f"Missing native reference drops on {half}")
            ref_rails.extend(rails)
            gaps = []
            for a in (f["bbox"] for f in m6 if f.get("net") == gate and f["type"] == "rect"):
                for b in (f["bbox"] for f in rails):
                    dx, dy = [max(0., a[0][i]-b[1][i], b[0][i]-a[1][i]) for i in (0, 1)]
                    gaps.append((dx*dx + dy*dy)**.5)
            if min(gaps) <= 0:
                raise ValueError(f"{gate} touches a CDAC reference trunk in saved OA")
            result.setdefault("b0_ref_min_edge_gap_um", {})[gate] = round(min(gaps), 4)
        bus = [f"CODE{i}" for i in range(8)] + ["PRESET"]
        sides = {}
        for cell, cell_view in [(DRIVER, view), ("sar8_se_core", "layout_r3")]:
            rows = query(cell, cell_view, "pins", *bus)["pins"]
            coords = {}
            for row in rows:
                fig, = row["figures"]
                if row["status"] != "ok" or fig["lpp"] != ["M3", "drawing"]:
                    raise ValueError(f"Unexpected bus landing on {cell}")
                coords[row["terminal"]] = center(fig["bbox"])
            if sorted(coords, key=lambda n: coords[n][1]) != bus or len({p[0] for p in coords.values()}) != 1:
                raise ValueError(f"Unexpected bus order or edge alignment on {cell}")
            sides[cell] = coords
        result["m3_bus_centers_local_um"] = sides
        result["longest_qn_m3_rect_um"] = max(
            (round(f["bbox"][1][0] - f["bbox"][0][0], 4), f["net"])
            for f in m3 if f["type"] == "rect" and (f.get("net") or "").startswith("QN"))
    if branches != intent["branch_um"] or abs(result["total_m6_um"] - intent["combined_gate_wire_um"]) > .001:
        raise ValueError("OA branch geometry differs from generated intent")
    write_json(out / "oa-route-review.json", result)
    if image:
        draw(image, blocks, cells, query(DRIVER, view, "shapes", "--layer", "M2")["figures"], m3, m6, ref_rails)
    return result


def draw(path, blocks, cells, m2, m3, m6, ref_rails):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle
    fig, ax = plt.subplots(figsize=(13, 3.3), layout="constrained")
    def box(item, color):
        (x, y), (xx, yy) = item["bbox"]
        ax.add_patch(Rectangle((x, y), xx - x, yy - y, facecolor=color))
    for item in blocks:
        box(item, "#e4e9ec")
    for item in ref_rails:
        box(item, "#ca9a44")
    for item in sorted(cells, key=lambda i: i["path"][-1].startswith("X")):
        box(item, "#335b53" if item["path"][-1].startswith("X") else "#bccbc6")
    for item in m2:
        if item["type"] == "rect" and item.get("net") not in (None, "VSS", "VDD"):
            box(item, "#98afc1")
    for item in m3 + m6:
        if item["type"] != "rect":
            continue
        net = item.get("net") or ""
        color = "#547bae" if item["lpp"][0] == "M3" else (
            "#b8531e" if net.endswith("7") else "#29837f" if net.startswith("G") else "#786095")
        box(item, color)
    xref = next(i for i in blocks if i["path"][-1] == "XREF")["bbox"]
    ax.set(xlim=(-2, 71), ylim=(xref[0][1] - 1, -22.8), aspect="equal", xlabel="X (µm)", ylabel="Y (µm)",
           title="Single-edge D2 reference driver and CDAC south edge · saved OA")
    ax.legend(handles=[Patch(facecolor=c, label=t) for c,t in (
        ("#335b53","Logic"),("#98afc1","M2"),("#547bae","M3"),("#29837f","B0–B6 M6"),
        ("#b8531e","B7 M6"),("#786095","Supply M6"),("#ca9a44","B0 VREF trunks"))], ncol=7, loc="upper center", bbox_to_anchor=(.5, -.27))
    fig.savefig(path, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity")
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()
    print(json.dumps(review(args.identity, args.image), indent=2))
