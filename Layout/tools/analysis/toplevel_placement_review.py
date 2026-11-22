"""Verify the saved placement-only ADC core against floorplan.json: transforms, block bboxes, overlaps and pins."""
import argparse
import datetime
import itertools
import json

from Layout.design.toplevel_placement import CELL, INSTANCES, PIN_OWNER, VIEW
from Layout.project import ROOT, write_json
from Layout.tools.analysis.toplevel_pin_readback import CELLVIEWS, FLOORPLAN, OUT as READBACK, center, figures, identities, is_text, query

OUT = ROOT / "Layout/results/toplevel_placement.json"
TOL = 0.005
EXACT = 5e-4
STRIP = 40.0


def rect(block):
    (x, y), (w, h) = block["origin"], block["size"]
    return [[round(x, 4), round(y, 4)], [round(x + w, 4), round(y + h, 4)]]


def deltas(a, b):
    return [round(a[i][j] - b[i][j], 4) for i in (0, 1) for j in (0, 1)]


def gap(a, b):
    dx = max(a[0][0] - b[1][0], b[0][0] - a[1][0])
    dy = max(a[0][1] - b[1][1], b[0][1] - a[1][1])
    return round(max(dx, dy), 4)


def edges(box, path):
    """Drawn (non-text) geometry of one occurrence at each edge of the floorplan block, in the top frame."""
    (x0, y0), (x1, y1) = box
    side = {"west": (0, -1, x0), "east": (0, 1, x1), "south": (1, -1, y0), "north": (1, 1, y1)}
    out = {}
    for edge, (axis, sign, at) in side.items():
        lo, hi = [x0 - STRIP, y0 - STRIP], [x1 + STRIP, y1 + STRIP]
        band_lo, band_hi = [x0, y0], [x1, y1]
        if sign > 0:
            lo[axis], band_lo[axis], band_hi[axis] = at + TOL, at - TOL, at + TOL
        else:
            hi[axis], band_lo[axis], band_hi[axis] = at - TOL, at - TOL, at + TOL

        def reach(f):
            return sign * (f["bbox"][1 if sign > 0 else 0][axis] - at)

        beyond = [f for f in figures(CELL, VIEW, "shapes", "--path", path, "--depth", "20", "--region",
                                     *map(str, lo + hi), "--limit", "10000") if reach(f) > TOL]
        band = [f for f in figures(CELL, VIEW, "shapes", "--path", path, "--depth", "20", "--region",
                                   *map(str, band_lo + band_hi), "--limit", "10000") if not is_text(f) and abs(reach(f)) <= TOL]
        drawn = [f for f in beyond if not is_text(f)]
        text = [reach(f) for f in beyond if is_text(f)]
        out[edge] = dict(edge_um=at, drawn_within_tol=bool(band),
                         drawn_edge_offset_um=round(max(map(reach, band)), 4) if band else None,
                         drawn_beyond_tol=[dict(lpp=f["lpp"], bbox=f["bbox"], path=f["path"]) for f in drawn[:3]],
                         text_beyond_um=round(max(text), 4) if text else 0.0)
    return out


def review(identity):
    plan = json.loads(FLOORPLAN.read_bytes())
    blocks = {b["id"]: b for b in plan["blocks"]}
    intent = json.loads((ROOT / "work/layout/toplevel-placement" / identity / "intent.json").read_bytes())
    build = json.loads((ROOT / "work/layout/toplevel-placement" / identity / "build.json").read_bytes())
    readback = json.loads(READBACK.read_bytes())
    core = [plan["core_bbox"][:2], plan["core_bbox"][2:]]

    top = {"/".join(i["path"]): i for i in query(CELL, VIEW, "instances", "--depth", "1", "--limit", "500")["instances"]}
    found = dict(top)
    for path in sorted({p.split("/")[0] for _, p in INSTANCES.values() if "/" in p}):
        found.update({"/".join(i["path"]): i for i in query(CELL, VIEW, "instances", path, "--depth", "1")["instances"]})
    transforms = {}
    for row in intent["instances"]:
        inst = top[row["name"]]
        (x, y), orient, mag = inst["edit_transform"]
        transforms[row["name"]] = dict(
            master=inst["master"], expected_master=[intent["library"], row["cell"], row["view"]],
            xy=[x, y], expected_xy=row["xy"], orient=orient, expected_orient=row["orient"], magnification=mag,
            ok=inst["master"] == [intent["library"], row["cell"], row["view"]] and orient == row["orient"] and mag == 1.0
            and max(abs(x - row["xy"][0]), abs(y - row["xy"][1])) <= EXACT)

    shapes = figures(CELL, VIEW, "shapes", "--depth", "0", "--limit", "100")
    vias = figures(CELL, VIEW, "vias", "--depth", "0", "--limit", "100")
    content = dict(top_instances=sorted(top), top_shapes=[dict(lpp=s["lpp"], bbox=s["bbox"]) for s in shapes],
                   top_vias=len(vias),
                   ok=sorted(top) == sorted({r["name"] for r in intent["instances"]}) and not vias
                   and [(s["lpp"], s["bbox"]) for s in shapes] == [(["prBoundary", "drawing"], core)])

    checks = {}
    for block_id, (_, path) in INSTANCES.items():
        want = rect(blocks[block_id])
        oa = found[path]["bbox"]
        e = edges(want, path)
        drawn_ok = all(v["drawn_within_tol"] and not v["drawn_beyond_tol"] for v in e.values())
        oa_ok = max(map(abs, deltas(oa, want))) <= TOL
        # Every edge is either drawn geometry or the cellview's own text-defined outline; nothing drawn is outside.
        basis_ok = all(not v["drawn_beyond_tol"] for v in e.values()) and all(
            v["drawn_within_tol"] or abs(deltas(oa, want)[i]) <= TOL
            for i, v in enumerate([e["west"], e["south"], e["east"], e["north"]]))
        checks[block_id] = dict(occurrence=path, floorplan_bbox=want, oa_bbox=oa, oa_bbox_delta_um=deltas(oa, want),
                                oa_bbox_within_tol=oa_ok, drawn_extent_within_tol=drawn_ok, edges=e,
                                inside_core=core[0][0] <= oa[0][0] and core[0][1] <= oa[0][1]
                                and oa[1][0] <= core[1][0] and oa[1][1] <= core[1][1],
                                ok=(oa_ok or drawn_ok) and basis_ok)

    pairs = []
    for a, b in itertools.combinations(INSTANCES, 2):
        pairs.append(dict(blocks=[a, b], floorplan_gap_um=gap(rect(blocks[a]), rect(blocks[b])),
                          oa_bbox_gap_um=gap(checks[a]["oa_bbox"], checks[b]["oa_bbox"])))
    overlaps = dict(pairs=pairs, min_floorplan_gap_um=min(p["floorplan_gap_um"] for p in pairs),
                    min_oa_bbox_gap_um=min(p["oa_bbox_gap_um"] for p in pairs),
                    ok=all(p["floorplan_gap_um"] > 2 * TOL and p["oa_bbox_gap_um"] > 0 for p in pairs))

    planned = plan["pins_um"]
    keys = [k for k in planned if k.split(".")[0] in PIN_OWNER and "@" not in k]
    args = [a for k in keys for a in ("--at", PIN_OWNER[k.split(".")[0]], k.split(".", 1)[1])]
    rows = query(CELL, VIEW, "pins", *args, "--limit", "500")["pins"]
    pins = {}
    for k, row in zip(keys, rows):
        fig, = row["figures"]
        if row["status"] != "ok" or row["terminal"] != k.split(".", 1)[1]:
            raise ValueError(f"Pin read failed for {k}: {row['reasons']}")
        c = center(fig["bbox"])
        pins[k] = dict(occurrence=PIN_OWNER[k.split(".")[0]], lpp=fig["lpp"], bbox=fig["bbox"], center=c, pins_um=planned[k],
                       delta_um=[round(a - b, 4) for a, b in zip(c, planned[k])])
    x, y = planned["XCOMP.CLK@trunk_top"]
    stack = [v for v in figures(CELL, VIEW, "vias", "--path", "XCOMP", "--depth", "0", "--region",
                                str(x - .1), str(y - .1), str(x + .1), str(y + .1))
             if v["net"] in (None, "CLK") and v["via_definition"] == "M3_M2"]
    via = min(stack, key=lambda v: max(abs(a - b) for a, b in zip(center(v["bbox"]), (x, y))))
    pins["XCOMP.CLK@trunk_top"] = dict(occurrence="XCOMP", via=via["via_definition"], bbox=via["bbox"], center=center(via["bbox"]),
                                       pins_um=[x, y], delta_um=[round(a - b, 4) for a, b in zip(center(via["bbox"]), (x, y))])
    worst = max(max(map(abs, p["delta_um"])) for p in pins.values())

    views = sorted({*CELLVIEWS.values(), *((v["master"][1], v["master"][2]) for v in readback["pair_instances"].values())})
    now = identities([*views, (CELL, VIEW)])
    unchanged = {k: now[k]["layout_oa_sha256"] == v["layout_oa_sha256"] for k, v in readback["cellviews"].items()}

    record = dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/toplevel_placement_review.py",
        source="saved OA, read with oaq --saved", units="um", frame="sar8_adc_core core frame (floorplan.json)",
        cellview=dict(library=intent["library"], cell=CELL, view=VIEW, **{k: v for k, v in now[f"{CELL}/{VIEW}"].items() if k != "library"}),
        build=dict(identity=identity, generator="Layout/design/toplevel_placement.py", evidence=build["evidence"],
                   build_il_sha256=intent["build_il_sha256"], floorplan_sha256=intent["floorplan_sha256"],
                   console=[line for line in build["stdout"] if line.startswith(("PLACED", "PLACEMENT_BUILD_OK"))]),
        scope=intent["scope"], tolerance_um=TOL,
        bbox_note="OA bboxes include text. The comparator and SAR OA bboxes exceed their blocks by pin and standard-cell "
                  "text only; the XREF east edge is the text-defined outline of its row-end cell. Each block passes when "
                  "nothing drawn lies outside it by more than the tolerance and every edge is met by drawn geometry or by "
                  "the cellview's own outline.",
        transforms=transforms, content=content, blocks=checks, overlaps=overlaps,
        pins=pins, pins_max_delta_um=worst, pins_ok=worst <= TOL,
        block_views_unchanged=unchanged,
    )
    record["verdict"] = dict(transforms=all(t["ok"] for t in transforms.values()), content=content["ok"],
                             blocks=all(c["ok"] for c in checks.values()), no_overlaps=overlaps["ok"],
                             inside_core=all(c["inside_core"] for c in checks.values()), pins=record["pins_ok"],
                             block_views_unchanged=all(unchanged.values()))
    record["verdict"]["pass"] = all(record["verdict"].values())
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("identity")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    record = review(args.identity)
    write_json(args.out, record)
    print(json.dumps(dict(verdict=record["verdict"], pins_max_delta_um=record["pins_max_delta_um"],
                          blocks={k: dict(oa=v["oa_bbox_within_tol"], drawn=v["drawn_extent_within_tol"], ok=v["ok"])
                                  for k, v in record["blocks"].items()},
                          min_gap=record["overlaps"]["min_floorplan_gap_um"]), indent=1))


if __name__ == "__main__":
    main()
