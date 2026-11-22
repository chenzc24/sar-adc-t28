"""Record of the SAR guard-ring view sar8_adc_core/layout_route_guard (Stage 5) from fetched evidence.

Writes Layout/results/toplevel_route_guard.json: build and read-only guard, the ring geometry, DRC by rule against
layout_route_full, and connectivity on the branch-labelled stream (the ring's own pin labelled VSS_G).
"""
import argparse
import datetime
import hashlib
import json

from Layout.design.toplevel_route import WORK, block_masters
from Layout.project import ROOT, write_json
from Layout.tools.analysis import toplevel_full_connectivity as conn


def manifest(identity):
    return json.loads((WORK / identity / "manifest.json").read_bytes())


def build(args):
    content = json.loads((ROOT / args.content).read_bytes())
    receipt = json.loads((WORK / args.build / "build.json").read_bytes())
    base = manifest(args.full_checks)["checks"]["drc"]["markers_by_rule"]
    guard = manifest(args.checks)["checks"]["drc"]["markers_by_rule"]
    delta = {k: [base.get(k, 0), guard.get(k, 0)] for k in sorted(set(base) | set(guard)) if base.get(k, 0) != guard.get(k, 0)}
    density = lambda r: ".DN." in r or r.startswith("Mx.DN") or r == "OD.S.14"
    summary = json.loads((ROOT / args.full_content).read_bytes())["summary"]
    hcells = set(block_masters(WORK / args.placement_stream / "fixture.gds"))
    connectivity = conn.check(WORK / args.conn / "spice/layout.sp", WORK / args.placement_netlist / "spice/layout.sp",
                              hcells, summary, WORK / args.conn / "spice.console", guard=True)
    stdout = "\n".join(receipt["stdout"])
    return dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/toplevel_guard_record.py",
        stage="Stage 5 of chenzc24/sar-adc-t28#12: the SAR P+ guard ring (floorplan sar_guard_ring) with its own VSS strap",
        cellview=dict(library="SAR_ADC_T28_LAYOUT", cell="sar8_adc_core", view="layout_route_guard",
                      copied_from="layout_route_full", build=args.build, build_ok=receipt["ok"],
                      read_only_views=["layout_place", "layout_route_int", "layout_route_full"],
                      read_only_views_unchanged="READ_ONLY_VIEW_CHANGED" not in stdout,
                      stream_layout_oa_sha256=manifest(args.checks)["source"]["layout_oa_sha256"]),
        generator=dict(geometry="Layout/design/toplevel_guard_routes.py", builder="Layout/design/toplevel_full.py --stage guard",
                       geometry_sha256=hashlib.sha256((ROOT / "Layout/design/toplevel_guard_routes.py").read_bytes()).hexdigest(),
                       rects=len(content["rects"]), ring=content["summary"]["guard_ring"]),
        evidence=dict(build=args.build, checks=args.checks, connectivity=args.conn, host="thu-wei"),
        drc=dict(full_markers=sum(base.values()), guard_markers=sum(guard.values()), delta_by_rule=delta,
                 non_density_changes=sorted(k for k in delta if not density(k)),
                 verdict="only density windows changed (deferred to fill); no new geometry rule"
                 if not [k for k in delta if not density(k)] else "geometry rules changed"),
        connectivity=connectivity,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("content", "build", "checks", "conn", "full-checks", "full-content", "placement-stream", "placement-netlist"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--out", default="Layout/results/toplevel_route_guard.json")
    args = ap.parse_args()
    record = build(args)
    write_json(ROOT / args.out, record)
    print(json.dumps(dict(drc=record["drc"]["verdict"], delta=record["drc"]["delta_by_rule"],
                          connectivity=record["connectivity"]["verdict"]), indent=1))


if __name__ == "__main__":
    main()
