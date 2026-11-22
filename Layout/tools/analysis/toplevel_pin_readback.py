"""Read the saved OA pins and edges the top-level floorplan assumes and compare them with floorplan.json pins_um."""
import argparse
import datetime
import json
import shlex
import subprocess
import time

from Layout.design.sar_single_edge import PORT_ORDER
from Layout.project import ROOT, config, write_json

FLOORPLAN = ROOT / "Layout/design/floorplan.json"
OUT = ROOT / "Layout/results/toplevel_pin_readback.json"
PAIR = ("sar8_cdac_with_xref", "layout_se_d2_r2")
CELLVIEWS = {
    "cdac": PAIR,
    "reference": PAIR,
    "comparator": ("sar_strongarm_t28_core", "layout"),
    "bootstrap_n": ("sar_bootstrap_flat_8b_p_core", "layout"),
    "bootstrap_p": ("sar_bootstrap_flat_8b_p_core", "layout"),
    "sar": ("sar8_se_core", "layout_r3"),
}
# Sub-instance of the pair that each pair block covers; other blocks are the whole cellview.
PAIR_PATH = {"cdac": "XCDAC", "reference": "XREF"}
PREFIX = {"XCDAC": "cdac", "XREF": "reference", "XCOMP": "comparator",
          "XBOOTN": "bootstrap_n", "XBOOTP": "bootstrap_p", "SAR": "sar"}
BUS = [f"CODE{i}" for i in range(8)] + ["PRESET"]
M7_TRACKS = [f"D{i}" for i in range(8)] + ["SAMPLE"]
TOL = 5e-4
STRIP = 40.0
EDGE = 0.002


def query(cell, view, *args):
    target = f"{config()['library']}/{cell}/{view}"
    for delay in (0, 2, 4):
        time.sleep(delay)
        run = subprocess.run(["oaq", "--saved", target, *args], capture_output=True, timeout=300)
        result = json.loads(run.stdout)
        if run.returncode == 0 and result["status"] in ("ok", "empty") and result["context"]["cellview"] == target.split("/"):
            return result
        reasons = result.get("reasons", [])
        if not any("timeout" in r.lower() for r in reasons) or delay == 4:
            raise ValueError(f"Incomplete OA read for {target} {args}: {reasons}")


def figures(cell, view, *args):
    result = query(cell, view, *args)
    if result["status"] == "ok" and result.get("reasons"):
        raise ValueError(f"Partial OA read for {cell}/{view} {args}: {result['reasons']}")
    return result.get("figures", [])


def center(box):
    return [round((a + b) / 2, 4) for a, b in zip(*box)]


def to_core(block, point):
    tx, ty = block["native_origin_translation"]
    orient = block.get("instance_orientation", "R0")
    if orient == "R0":
        return [round(tx + point[0], 4), round(ty + point[1], 4)]
    if orient == "MY":
        return [round(tx - point[0], 4), round(ty + point[1], 4)]
    raise ValueError(f"Unsupported orientation {orient}")


def box_to_core(block, box):
    a, b = to_core(block, box[0]), to_core(block, box[1])
    return [[min(a[0], b[0]), min(a[1], b[1])], [max(a[0], b[0]), max(a[1], b[1])]]


def is_text(fig):
    return fig["type"] in ("label", "text") or (fig["lpp"] or [""])[0] == "text"


def conductors(rows, layers):
    """Drawn rectangles and via footprints on the given metal layers."""
    out = []
    for f in rows:
        if f.get("footprints"):
            out += [dict(lpp=p["lpp"], bbox=[p["vertices"][0], p["vertices"][2]], net=f["net"], via=f["via_definition"])
                    for p in f["footprints"] if p["lpp"][0] in layers]
        elif not is_text(f) and f["lpp"] and f["lpp"][0] in layers:
            out.append(dict(lpp=f["lpp"], bbox=f["bbox"], net=f["net"]))
    return out


def identities(cellviews):
    c = config()
    lines = [f"f={shlex.quote(c['library_path'] + '/' + cell + '/' + view + '/layout.oa')}; "
             f"printf '%s %s %s\\n' {shlex.quote(cell + '/' + view)} \"$(sha256sum \"$f\" | cut -c1-64)\" "
             f"\"$(stat -c '%s|%y' \"$f\")\"" for cell, view in cellviews]
    found = subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", c["host"], "bash -s"],
                                    input="\n".join(lines).encode(), timeout=60).decode().splitlines()
    out = {}
    for line in found:
        name, digest, stat = line.split(" ", 2)
        size, mtime = stat.split("|")
        out[name] = dict(library=c["library"], path=f"{c['library_path']}/{name}", layout_oa_sha256=digest,
                         layout_oa_bytes=int(size), layout_oa_mtime=mtime)
    if len(out) != len(cellviews):
        raise ValueError("Missing OA identity")
    return out


def extent(cell, view, box, path=None):
    """Compare the drawn and text extent of a cellview (or one occurrence) with an expected bbox."""
    (x0, y0), (x1, y1) = box
    scope = ["--path", path] if path else []
    outside = {"west": (x0 - STRIP, y0 - STRIP, x0 - 1e-4, y1 + STRIP), "east": (x1 + 1e-4, y0 - STRIP, x1 + STRIP, y1 + STRIP),
               "south": (x0 - STRIP, y0 - STRIP, x1 + STRIP, y0 - 1e-4), "north": (x0 - STRIP, y1 + 1e-4, x1 + STRIP, y1 + STRIP)}
    inside = {"west": (x0, y0, x0 + EDGE, y1), "east": (x1 - EDGE, y0, x1, y1),
              "south": (x0, y0, x1, y0 + EDGE), "north": (x0, y1 - EDGE, x1, y1)}
    edges = {}
    for edge in outside:
        def beyond(f):
            (a, b), (c, d) = f["bbox"]
            return {"west": x0 - a, "east": c - x1, "south": y0 - b, "north": d - y1}[edge]
        far = [f for f in figures(cell, view, "shapes", "--depth", "20", "--region", *map(str, outside[edge]),
                                  "--limit", "10000", *scope) if beyond(f) > 1e-4]
        near = [f for f in figures(cell, view, "shapes", "--depth", "20", "--region", *map(str, inside[edge]),
                                   "--limit", "10000", *scope) if not is_text(f) and abs(beyond(f)) <= 1e-4]
        text = [beyond(f) for f in far if is_text(f)]
        drawn = [f for f in far if not is_text(f)]
        edges[edge] = dict(drawn_reaches_edge=bool(near),
                           drawn_overhang_um=round(max(map(beyond, drawn)), 4) if drawn else 0.0,
                           text_overhang_um=round(max(text), 4) if text else 0.0,
                           edge_drawn_by=sorted({"/".join(f["path"]) or "(top)" for f in near})[:4])
    return edges


def readback():
    plan = json.loads(FLOORPLAN.read_bytes())
    blocks = {b["id"]: b for b in plan["blocks"]}
    planned = plan["pins_um"]
    paths = plan["planned_paths"]
    pitch = plan["routing_rules"]["track_pitch_um"]

    def affected(point):
        return sorted(n for n, p in paths.items()
                      if any(abs(q[0] - point[0]) <= TOL and abs(q[1] - point[1]) <= TOL for q in p["points_um"]))

    pair_instances = query(*PAIR, "instances")["instances"]
    masters = {i["path"][-1]: i for i in pair_instances}
    cellviews = sorted({*CELLVIEWS.values(), *((m["master"][1], m["master"][2]) for m in masters.values())})
    record = dict(
        schema_version=1,
        date=datetime.date.today().isoformat(),
        tool="Layout/tools/analysis/toplevel_pin_readback.py",
        source="saved OA, read with oaq --saved (isolated read-only reader); no edit session involved",
        units="um",
        frames="local = cellview frame of the saved view; core = floorplan core frame after native_origin_translation "
               "and instance_orientation (MY maps x to -x before the translation)",
        floorplan=dict(file="Layout/design/floorplan.json", status=plan["status"], core_bbox=plan["core_bbox"]),
        cellviews=identities(cellviews),
        pair_instances={n: dict(master=m["master"], transform=m["edit_transform"], bbox=m["bbox"]) for n, m in masters.items()},
        placements={k: dict(cellview=list(CELLVIEWS[k]), occurrence=PAIR_PATH.get(k),
                            native_origin_translation=b["native_origin_translation"],
                            instance_orientation=b.get("instance_orientation", "R0")) for k, b in blocks.items()},
    )

    # Root terminals of every block, in one pins query per cellview.
    wanted = {}
    for key in planned:
        inst, _, term = key.partition(".")
        if inst in PREFIX and "@" not in term:
            wanted.setdefault(PREFIX[inst], []).append((key, term))
    pins, raw = {}, {}
    for block_id, items in wanted.items():
        cv = CELLVIEWS[block_id]
        if cv not in raw:
            terms = sorted({t for b, its in wanted.items() if CELLVIEWS[b] == cv for _, t in its})
            raw[cv] = {e["terminal"]: e for e in query(*cv, "pins", *terms)["pins"]}
        for key, term in items:
            entry = raw[cv][term]
            fig, = entry["figures"]
            if entry["status"] != "ok":
                raise ValueError(f"Pin read failed for {key}: {entry['reasons']}")
            local = center(fig["bbox"])
            core = to_core(blocks[block_id], local)
            pins[key] = dict(cellview=list(cv), terminal=term, lpp=fig["lpp"], local_bbox=fig["bbox"], local_center=local,
                             core_center=core, pins_um=planned[key],
                             delta_um=[round(a - b, 4) for a, b in zip(core, planned[key])])

    # (e) Top end of the comparator M3 CLK trunk and the via stack it carries.
    comp = blocks["comparator"]
    m3 = [f for f in figures(*CELLVIEWS["comparator"], "shapes", "--depth", "0", "--layer", "M3")
          if f["type"] == "rect" and f["net"] == "CLK"]
    trunk = max(m3, key=lambda f: f["bbox"][1][1] - f["bbox"][0][1])
    top = trunk["bbox"][1][1]
    stack = [v for v in figures(*CELLVIEWS["comparator"], "vias", "--depth", "0",
                                "--region", "-0.1", str(top - 0.2), "0.1", str(top))
             if any(p["lpp"][0] == "M3" and abs(p["vertices"][2][1] - top) <= TOL for p in v["footprints"])]
    via, = stack
    land = [round(c, 4) for c in via["local_origin"]]
    pins["XCOMP.CLK@trunk_top"] = dict(
        cellview=list(CELLVIEWS["comparator"]), terminal="CLK", lpp=trunk["lpp"], local_bbox=trunk["bbox"],
        trunk_top_edge_local=[0.0, top], trunk_top_edge_core=to_core(comp, [0.0, top]),
        top_via=dict(definition=via["via_definition"], local_origin=land,
                     footprints={p["lpp"][0]: [p["vertices"][0], p["vertices"][2]] for p in via["footprints"]}),
        local_center=land, core_center=to_core(comp, land), pins_um=planned["XCOMP.CLK@trunk_top"],
        delta_um=[round(a - b, 4) for a, b in zip(to_core(comp, land), planned["XCOMP.CLK@trunk_top"])],
        definition="pins_um is the centre of the top CLK via stack; the M3 trunk itself ends one via half-length above it")

    # (c) East extension of the XREF CODE/PRESET M3 bus up to the XREF outline.
    ref = blocks["reference"]
    outline = masters["XREF"]["bbox"]
    bus = {t: pins[f"XREF.{t}"] for t in BUS}
    lo = min(p["local_bbox"][0][1] for p in bus.values()) - pitch["xref_ports"]
    hi = max(p["local_bbox"][1][1] for p in bus.values()) + pitch["xref_ports"]
    start = min(p["local_bbox"][1][0] for p in bus.values())
    region = ["--depth", "20", "--region", str(start), str(lo), str(outline[1][0] + 0.5), str(hi), "--limit", "10000"]
    near = conductors(figures(*PAIR, "shapes", *region) + figures(*PAIR, "vias", *region), ("M3",))
    tracks = {}
    for t, p in bus.items():
        (_, y0), (x1, y1) = p["local_bbox"]
        band = (p["local_center"][1] - pitch["xref_ports"] / 2, p["local_center"][1] + pitch["xref_ports"] / 2)
        hits = [c for c in near if c["bbox"][1][0] > x1 + 1e-4 and c["bbox"][0][0] < outline[1][0]
                and c["bbox"][1][1] > band[0] and c["bbox"][0][1] < band[1]]
        tracks[t] = dict(pin_east_edge_local=x1, extension_local=[[x1, y0], [outline[1][0], y1]],
                         extension_core=box_to_core(ref, [[x1, y0], [outline[1][0], y1]]),
                         m3_in_half_pitch_band=hits, clear=not hits)
    row_end = [f for f in figures(*PAIR, "shapes", "--depth", "20", "--region", str(start), str(outline[0][1]),
                                  str(outline[1][0] + 0.5), str(outline[1][1]), "--limit", "10000")
               if f["path"] and f["path"][0] == "XREF"]
    drawn = [f for f in row_end if not is_text(f)]
    widest = max(row_end, key=lambda f: f["bbox"][1][0])
    record["xref_bus_extension"] = dict(
        outline_local=outline, outline_core=box_to_core(ref, outline),
        bus_pin_center_x_local=bus["CODE0"]["local_center"][0],
        inset_from_outline_um=round(outline[1][0] - bus["CODE0"]["local_center"][0], 4),
        searched_local=[[start, lo], [outline[1][0] + 0.5, hi]], searched_layers=["M3", "VIA2/VIA3 M3 enclosures"],
        tracks=tracks, all_clear=all(t["clear"] for t in tracks.values()),
        outline_set_by=dict(lpp=widest["lpp"], type=widest["type"], occurrence="/".join(widest["path"]), bbox=widest["bbox"]),
        drawn_east_edge_local=round(max(f["bbox"][1][0] for f in drawn), 4),
        drawn_east_edge_core=to_core(ref, [max(f["bbox"][1][0] for f in drawn), 0])[0],
        row_end_cells=sorted({"/".join(f["path"][:2]) for f in drawn if f["lpp"] == ["prBoundary", "drawing"]
                              and f["bbox"][1][0] > start - 1.0}))

    # (d) SAR macro metal on M5-M7 under the planned M7 D0-D7/SAMPLE tracks.
    sar = CELLVIEWS["sar"]
    upper = {layer: [f for f in figures(*sar, "shapes", "--depth", "20", "--layer", layer, "--limit", "10000") if not is_text(f)]
             for layer in ("M5", "VIA5", "M6", "VIA6", "M7", "VIA7", "M8")}
    boundary, = [f for f in figures(*sar, "shapes", "--depth", "0", "--layer", "prBoundary")]
    track_rows = {}
    for t in M7_TRACKS:
        y = pins[f"SAR.{t}"]["local_center"][1]
        under = {layer: sorted({(f["bbox"][0][0], f["bbox"][1][0], f["net"]) for f in rows if f["bbox"][0][1] <= y <= f["bbox"][1][1]})
                 for layer, rows in upper.items() if layer in ("M5", "M6", "M7")}
        nearest = {layer: round(min((min(abs(f["bbox"][0][1] - y), abs(f["bbox"][1][1] - y)) for f in rows
                                     if not f["bbox"][0][1] <= y <= f["bbox"][1][1]), default=float("nan")), 4)
                   for layer, rows in upper.items() if layer in ("M5", "M6") and rows}
        track_rows[t] = dict(y_local=y, y_core=pins[f"SAR.{t}"]["core_center"][1],
                             crossing_under_centreline={k: [dict(x=[a, b], net=n) for a, b, n in v] for k, v in under.items()},
                             nearest_non_crossing_edge_um=nearest)
    stripes = sorted({(f["bbox"][0][0], f["bbox"][1][0], f["bbox"][0][1], f["bbox"][1][1], f["net"]) for f in upper["M6"]
                      if f["bbox"][1][1] - f["bbox"][0][1] > 10})
    record["sar_m7_tracks"] = dict(
        boundary_local=boundary["bbox"], boundary_lower_left_is_origin=boundary["bbox"][0] == [0.0, 0.0],
        boundary_core=box_to_core(blocks["sar"], boundary["bbox"]),
        shape_counts={k: len(v) for k, v in upper.items()},
        m6_stripes=[dict(x=[a, b], y=[c, d], net=n) for a, b, c, d, n in stripes],
        m5_shapes_are=sorted({(round(f["bbox"][1][0] - f["bbox"][0][0], 4), round(f["bbox"][1][1] - f["bbox"][0][1], 4), f["net"])
                              for f in upper["M5"]}),
        tracks=track_rows)
    sar_pins = [pins[f"SAR.{t}"] for t in PORT_ORDER]
    record["sar_west_pins"] = dict(
        port_order_matches=[p["terminal"] for p in sorted(sar_pins, key=lambda p: p["local_center"][1])]
        == [p["terminal"] for p in sar_pins],
        on_formula=all(abs(p["local_center"][0] - 0.17) <= TOL and abs(p["local_center"][1] - (1.4 + 0.6 * i)) <= TOL
                       for i, p in enumerate(sar_pins)),
        layers=sorted({tuple(p["lpp"]) for p in sar_pins}), pin_rect_um=sorted({(round(p["local_bbox"][1][0] - p["local_bbox"][0][0], 4),
                                                                                 round(p["local_bbox"][1][1] - p["local_bbox"][0][1], 4)) for p in sar_pins}))

    # Block edges: drawn geometry against the floorplan native bbox, text reported separately.
    extents = {}
    for block_id, block in blocks.items():
        cv = CELLVIEWS[block_id]
        if block_id == "bootstrap_p":
            extents[block_id] = dict(same_master_as="bootstrap_n")
            continue
        native = block["evidence"].get("native_bbox") if block_id != "sar" else boundary["bbox"]
        extents[block_id] = dict(cellview=list(cv), occurrence=PAIR_PATH.get(block_id), native_bbox=native,
                                 edges=extent(*cv, native, PAIR_PATH.get(block_id)))
    record["block_extents"] = extents

    differences = [dict(pin=k, pins_um=v["pins_um"], readback_core=v["core_center"], delta_um=v["delta_um"],
                        planned_paths=affected(v["pins_um"]))
                   for k, v in pins.items() if max(map(abs, v["delta_um"])) > TOL]
    record["pins"] = pins
    record["not_read"] = sorted(k for k in planned if k.split(".")[0] not in PREFIX)
    record["differences"] = differences
    record["paths_by_pin"] = {k: affected(v["pins_um"]) for k, v in pins.items()}
    record["notes"] = notes(record)
    return record


def notes(r):
    """Findings that change no pins_um value but qualify how a planned path or check uses it."""
    clk, bus, sar = r["pins"]["XCOMP.CLK@trunk_top"], r["xref_bus_extension"], r["sar_m7_tracks"]
    edges = r["block_extents"]
    stripes = ", ".join(f"{s['net']} x {s['x'][0]}-{s['x'][1]}" for s in sar["m6_stripes"])
    nearest = min(v for t in sar["tracks"].values() for v in t["nearest_non_crossing_edge_um"].values())
    pad = sar["m5_shapes_are"][0]
    return [
        dict(topic="CMP_CLK landing", planned_paths=r["paths_by_pin"]["XCOMP.CLK@trunk_top"],
             text=f"pins_um XCOMP.CLK@trunk_top {clk['pins_um']} is the centre of the top {clk['top_via']['definition']} "
                  f"stack at local {clk['local_center']}. The M3 trunk ends at local y {clk['trunk_top_edge_local'][1]} "
                  f"(core y {clk['trunk_top_edge_core'][1]}); interfaces.json rounds that edge to -0.23. "
                  "The M4 drop ends on the via centre, so its via3 stacks on the existing via2."),
        dict(topic="XREF bus east extension", planned_paths=sorted({p for t in BUS for p in r["paths_by_pin"][f"XREF.{t}"]}),
             text=f"All nine M3 tracks are {'clear' if bus['all_clear'] else 'NOT clear'} from the pin ends (local x "
                  f"{bus['tracks']['PRESET']['pin_east_edge_local']}) to the outline: no M3 or via M3 enclosure in their "
                  f"half-pitch bands, searched at full depth to local x {bus['searched_local'][1][0]}. The row-end cell "
                  f"{', '.join(bus['row_end_cells'])} sits in the row above the bus."),
        dict(topic="XREF outline", planned_paths=[],
             text=f"The XREF east outline (local x {bus['outline_local'][1][0]}, core x {bus['outline_core'][1][0]}) is set by the "
                  f"{bus['outline_set_by']['lpp'][0]} label of {bus['outline_set_by']['occurrence']}; drawn XREF geometry ends at "
                  f"local x {bus['drawn_east_edge_local']} (core x {bus['drawn_east_edge_core']})."),
        dict(topic="SAR bbox", planned_paths=[],
             text=f"The layout_r3 OA bbox exceeds its prBoundary by standard-cell text only "
                  f"(+{edges['sar']['edges']['east']['text_overhang_um']} um east, "
                  f"+{edges['sar']['edges']['west']['text_overhang_um']} um west); drawn geometry stays inside the boundary. "
                  "Block bbox checks use the boundary."),
        dict(topic="Comparator bbox", planned_paths=[],
             text=f"VINN/VINP pin text overhangs the native bbox by {edges['comparator']['edges']['west']['text_overhang_um']}/"
                  f"{edges['comparator']['edges']['east']['text_overhang_um']} um; drawn geometry is the native bbox."),
        dict(topic="SAR metal under the M7 tracks",
             planned_paths=sorted({p for t in M7_TRACKS for p in r["paths_by_pin"][f"SAR.{t}"]}),
             text=f"The macro has no M7, VIA6, VIA7 or M8. M5 holds only {pad[0]} x {pad[1]} um via pads on the rail rows; "
                  f"M6 holds four full-height stripes ({stripes}), which every M7 track crosses. The nearest M5/M6 edge that "
                  f"does not cross a track centre is {nearest} um away. Top-level via6/via7 onto the stripes must stay off the "
                  "track rows."),
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--renotes", action="store_true", help="rebuild only the notes of an existing record")
    args = ap.parse_args()
    if args.renotes:
        record = json.loads(open(args.out, "rb").read())
        record["notes"] = notes(record)
    else:
        record = readback()
    write_json(args.out, record)
    print(json.dumps(dict(differences=record["differences"], bus_clear=record["xref_bus_extension"]["all_clear"],
                          sar_counts=record["sar_m7_tracks"]["shape_counts"]), indent=1))


if __name__ == "__main__":
    main()
