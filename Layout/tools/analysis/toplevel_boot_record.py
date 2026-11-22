"""Record of sar8_adc_core/layout_route_boot_r2 (Stage 5): layout_route_guard with both Bootstrap instances on the
revised filled Bootstrap sar_bootstrap_flat_8b_p_filled/layout_r2, from fetched evidence.

Writes Layout/results/toplevel_route_boot_r2.json: the pin check of the new master against the old one, the build and
its guarded views, DRC by rule and by failing density area against layout_route_guard, connectivity on the
branch-labelled stream, core LVS, flat LUP/ESD on the partial chip stream with this core substituted (and a control
with the layout_route_guard core through the same substitution), and the typical xRC of the unlabelled stream against
the same extraction of layout_route_guard: TOP totals and imbalance, the adopted route budgets, VIN and the boot-cap
plates.
"""
import argparse
import datetime
import hashlib
import json
import re

import gdstk

from Layout.design.toplevel_route import WORK, block_masters
from Layout.project import ROOT, write_json
from Layout.tools.analysis import toplevel_full_connectivity as conn
from Layout.tools.analysis import toplevel_full_parasitics as fpara
from Layout.tools.analysis.toplevel_lvs_record import top_summary
from Layout.tools.analysis.toplevel_route_parasitics import Extraction, analyze
from Layout.tools.analysis.toplevel_route_record import budgets, evaluate

BOOT = {"bootstrap_n": (18.475, 76.2, 42.995, 101.19), "bootstrap_p": (49.235, 76.2, 73.755, 101.19)}
DIE_ORIGIN = (363.885, 449.0)    # core origin in the chip stream
DENSITY = ("PO.DN.3", "PO.DN.3.1", "OD.S.14", "OD.DN.3")


def manifest(identity):
    return json.loads((WORK / identity / "manifest.json").read_bytes())


def results(path, polygons=False):
    """Results by rule from an ASCII DRC database: boxes (or polygons) in microns."""
    t = path.read_text(encoding="latin1").splitlines()
    scale = float(t[0].split()[1])
    out, i = {}, 1
    while i < len(t):
        line = t[i].strip()
        if re.match(r"^[A-Za-z][\w.:]*$", line) and i + 1 < len(t) and re.match(r"^\d+ \d+ \d+", t[i + 1]):
            rule, n, nh = line, int(t[i + 1].split()[0]), int(t[i + 1].split()[2])
            i, k = i + 2 + nh, 0
            out.setdefault(rule, [])
            while i < len(t) and k < n:
                m = re.match(r"^([ep]) \d+ (\d+)", t[i])
                if not m:
                    i += 1
                    continue
                cnt = int(m.group(2))
                pts = [tuple(int(v) / scale for v in t[i + 1 + q].split()[:2]) for q in range(cnt)]
                if polygons:
                    if m.group(1) == "p":
                        out[rule].append(gdstk.Polygon(pts))
                else:
                    out[rule].append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts),
                                      max(p[1] for p in pts)))
                i, k = i + cnt + 1, k + 1
        else:
            i += 1
    return out


def drc(args):
    base = manifest(args.guard_checks)["checks"]["drc"]["markers_by_rule"]
    new = manifest(args.checks)["checks"]["drc"]["markers_by_rule"]
    delta = {k: [base.get(k, 0), new.get(k, 0)] for k in sorted(set(base) | set(new)) if base.get(k, 0) != new.get(k, 0)}
    density = lambda r: ".DN." in r or r.startswith("Mx.DN") or r == "OD.S.14"  # noqa: E731
    a = results(WORK / args.guard_checks / "drc/DRC_RES.db", polygons=True)
    b = results(WORK / args.checks / "drc/DRC_RES.db", polygons=True)
    boot = [gdstk.rectangle(v[:2], v[2:]) for v in BOOT.values()]
    area = {}
    for rule in DENSITY:
        ua, ub = gdstk.boolean(a.get(rule, []), [], "or"), gdstk.boolean(b.get(rule, []), [], "or")
        inside = lambda ps: round(sum(q.area() for q in gdstk.boolean(ps, boot, "and")), 1)  # noqa: E731
        area[rule] = dict(failing_um2=[round(sum(p.area() for p in ua), 1), round(sum(p.area() for p in ub), 1)],
                          inside_bootstrap_outlines_um2=[inside(ua), inside(ub)])
    return dict(guard_markers=sum(base.values()), boot_r2_markers=sum(new.values()), delta_by_rule=delta,
                non_density_changes=sorted(k for k in delta if not density(k)),
                failing_density_area=area,
                note="Density violations are window regions; a merged failing region that splits when part of it passes "
                     "counts as more markers. The failing area is the like-for-like measure.",
                verdict="only density windows changed; failing density area drops on every listed rule"
                if not [k for k in delta if not density(k)] else "geometry rules changed")


def flat(identity):
    """LUP/ESD result counts of a flat chip probe, each LUP result tagged by the Bootstrap it falls in."""
    res = results(WORK / identity / "probe.db")
    counts = {k: len(v) for k, v in res.items() if v}
    where = {}
    for rule, boxes in res.items():
        if not rule.startswith("LUP."):
            continue
        for x0, y0, x1, y1 in boxes:
            cx, cy = (x0 + x1) / 2 - DIE_ORIGIN[0], (y0 + y1) / 2 - DIE_ORIGIN[1]
            tag = next((k for k, (a, b, c, d) in BOOT.items() if a <= cx <= c and b <= cy <= d), "elsewhere")
            where.setdefault(rule, {}).setdefault(tag, 0)
            where[rule][tag] += 1
    selected = (WORK / identity / "selected.txt").read_text().split()
    return dict(evidence=identity, rules_selected=len(selected), results_by_rule=counts, lup_by_bootstrap=where)


def plates(ex):
    """Boot-cap plates: the two nets on the MOM capacitors of each Bootstrap, with their capacitance to ground and total."""
    c = ex.capacitance()
    out = {}
    for name, nodes, model, block in ex.devices:
        if block not in BOOT or "cfmom" not in model:
            continue
        for node in nodes[:2]:
            out.setdefault(block, set()).add(ex.net(node))
    return {blk: {net: dict(to_ground_fF=round(c[net].get("0", 0.0) * 1e15, 3),
                            total_fF=round(sum(c[net].values()) * 1e15, 3)) for net in sorted(nets)}
            for blk, nets in sorted(out.items())}


def xrc(args):
    new, old = Extraction(WORK / args.xtr / "pex"), Extraction(WORK / args.guard_xtr / "pex")
    cn, co = new.capacitance(), old.capacitance()
    total = lambda c, n: round(sum(c[n].values()) * 1e15, 3)  # noqa: E731
    nets = ("TOPN", "TOPP", "COMP_P", "COMP_N", "CMP_CLK", "SEQ_SAMPLE", "VINN", "VINP")
    rows = {n: dict(guard_fF=total(co, n), boot_r2_fF=total(cn, n)) for n in nets}
    for r in rows.values():
        r["change_fF"] = round(r["boot_r2_fF"] - r["guard_fF"], 3)
    top = dict(imbalance_fF=round(abs(rows["TOPN"]["boot_r2_fF"] - rows["TOPP"]["boot_r2_fF"]), 3),
               guard_imbalance_fF=round(abs(rows["TOPN"]["guard_fF"] - rows["TOPP"]["guard_fF"]), 3))
    par = analyze(WORK / args.placement_pex / "pex", WORK / args.xtr / "pex")
    lim = budgets()
    return dict(evidence=dict(boot_r2=args.xtr, guard=args.guard_xtr, placement_pins_only=args.placement_pex),
                totals=rows, top=top,
                top_limit_fF=dict(imbalance=round(lim["TOP_differential_capacitance_imbalance_F"]["limit"] * 1e15, 3)),
                route_budgets=evaluate(par, lim),
                route_budgets_note="Stage 4a method (added against the pins-only placement); the TOP rows are not "
                                   "like-for-like (toplevel_route_full.md). totals compares with layout_route_guard.",
                vin=fpara.vin(new),
                boot_plates=dict(boot_r2=plates(new), guard=plates(old),
                                 standalone_filled_r2="boot-fill-r2-20261122 (typical): BTOP 37.9, BBOT 40.4 fF to ground"))


def build(args):
    receipt = json.loads((WORK / args.build / "build.json").read_bytes())
    content = json.loads((WORK / args.build / "content.json").read_bytes())
    summary = json.loads((ROOT / args.full_content).read_bytes())["summary"]
    hcells = set(block_masters(WORK / args.placement_stream / "fixture.gds"))
    connectivity = conn.check(WORK / args.conn / "spice/layout.sp", WORK / args.placement_netlist / "spice/layout.sp",
                              hcells, summary, WORK / args.conn / "spice.console", guard=True)
    lvs_m = manifest(args.lvs)
    rep = (WORK / args.lvs / "lvs/lvs.rep").read_text(encoding="utf-8", errors="replace")
    stdout = "\n".join(receipt["stdout"])
    pin_check = json.loads((ROOT / args.pin_check).read_bytes())
    lup, control = flat(args.flat), flat(args.flat_control)
    return dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/toplevel_boot_record.py",
        stage="Stage 5 of chenzc24/sar-adc-t28#12: the routed core on the revised filled Bootstrap (latch-up spacing "
              "fixed, planned fill); ADC qualification of the revision is the Bootstrap session's",
        cellview=dict(library="SAR_ADC_T28_LAYOUT", cell="sar8_adc_core", view="layout_route_boot_r2",
                      copied_from="layout_route_guard", build=args.build, build_ok=receipt["ok"],
                      remaster=content["remaster"],
                      read_only_views=["layout_place", "layout_route_int", "layout_route_full", "layout_route_guard"],
                      read_only_views_unchanged="READ_ONLY_VIEW_CHANGED" not in stdout,
                      stream=args.checks, stream_layout_oa_sha256=manifest(args.checks)["source"]["layout_oa_sha256"],
                      stream_sha256=manifest(args.checks)["gds"]["sha256"]),
        generator=dict(builder="Layout/design/toplevel_full.py --stage boot_r2",
                       builder_sha256=hashlib.sha256((ROOT / "Layout/design/toplevel_full.py").read_bytes()).hexdigest()),
        pin_check=pin_check,
        drc=drc(args), connectivity=connectivity,
        lvs=dict(evidence=args.lvs, verdict=lvs_m["checks"]["lvs"]["verdict"], cells=lvs_m["checks"]["lvs"]["cells"],
                 top=top_summary(rep, "sar8_adc_core"), hcells=lvs_m["decks"]["lvs"].get("hcells"),
                 virtual_connect_name=lvs_m["decks"]["lvs"].get("virtual_connect_name"),
                 source=dict(generator="Layout/design/toplevel_lvs_source.py --bootstrap-reference boot-core-r2b-20261122",
                             sha256=lvs_m.get("source_netlist", {}).get("sha256"),
                             note="The r2 reference.cdl is byte-identical to the frozen core's (boot-core-20261121). "
                                  "The wrapper and its fill flatten into the top; the fill adds no devices or nets."),
                 well_diodes="LVS FILTER D(pnwdio) LAYOUT OPEN (installed deck)"),
        flat_chip_lup_esd=dict(substitution="sar8_adc_core of chip-asm-a3-chk/fixture.gds replaced by this view's stream "
                                            "(copy of the Bootstrap session's substitute_master.py), flat chip deck with "
                                            "every LUP.* and ESD.* check selected",
                               boot_r2=lup, control_layout_route_guard=control),
        xrc=xrc(args),
        evidence=dict(build=args.build, checks=args.checks, connectivity=args.conn, lvs=args.lvs, xrc=args.xtr,
                      guard_xrc=args.guard_xtr, flat=args.flat, flat_control=args.flat_control, host="thu-wei"),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("build", "checks", "guard-checks", "conn", "lvs", "flat", "flat-control", "xtr", "guard-xtr",
              "placement-pex", "placement-stream", "placement-netlist", "full-content", "pin-check"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--out", default="Layout/results/toplevel_route_boot_r2.json")
    args = ap.parse_args()
    record = build(args)
    write_json(ROOT / args.out, record)
    x = record["xrc"]
    print(json.dumps(dict(drc=record["drc"]["verdict"], connectivity=record["connectivity"]["verdict"],
                          lvs=record["lvs"]["verdict"], lup=record["flat_chip_lup_esd"]["boot_r2"]["results_by_rule"],
                          control=record["flat_chip_lup_esd"]["control_layout_route_guard"]["results_by_rule"],
                          top=x["top"], budgets=all(r["pass"] for r in x["route_budgets"]),
                          plates=x["boot_plates"]), indent=1))


if __name__ == "__main__":
    main()
