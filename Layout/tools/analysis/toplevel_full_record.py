"""Assemble the Stage 4b record of sar8_adc_core/layout_route_full from fetched evidence.

Writes Layout/results/toplevel_route_full.json: build, DRC against layout_route_int, connectivity on the
branch-labelled stream, the adopted route budgets re-checked in the new environment, TOP capacitance on the
unlabelled stream against Stage 4a and the placement (pins only, and with the pair VSS tied as Stage 4b ties it),
VIN coupling, feed resistance per supply branch, decoupling per branch, the reference network (RREF from the PDK
model and the extracted routing, CREF, the CREF N-well junction) and the rail budget rerun with the drawn values.
"""
import argparse
import datetime
import hashlib
import json
import re

from Layout.design.toplevel_route import WORK, block_masters
from Layout.project import ROOT, write_json
from Layout.tools.analysis import toplevel_full_connectivity as conn
from Layout.tools.analysis import toplevel_full_parasitics as fpara
from Layout.tools.analysis.toplevel_route_parasitics import Extraction, analyze
from Layout.tools.analysis.toplevel_route_record import budgets, evaluate

C_PER_UM2_F = 19.0e-15   # nmoscap accumulation at +0.9 V, TT, from the model equations (Stage 4b device survey)
STAGE1_F = {"analog": 9e-12, "comparator_local": 0.47e-12, "pair": 10e-12, "sar": 8e-12}
GROUPS = {"analog": ("DA_west", "DA_slot", "DA_east"), "comparator_local": ("DC_W", "DC_E"),
          "pair": ("DP_S", "DP_E", "DP_SE", "DP_C"), "sar": ("DS_S", "DS_N")}
CREF_GROUPS = ("DR_W", "DR_C", "DR_SE")
CREF_TARGET_F, CREF_TOL, RREF_TARGET_OHM, RREF_TOL = 8e-12, 0.25, 15.0, 0.20
# New top-level metal of Stage 4b. The trunk nets are left out: they now also name the pair's own VREF rails, which
# TOP already coupled to in Stage 4a as unnamed nets (0.68 / 0.66 fF).
STAGE4B_NETS = {"VINN", "VINP", "VDD!", "VREFP", "VREFN", "SAMPLE", *[f"D{k}" for k in range(8)]}
PAIR_REF_RAILS = ("VREFP_TRUNK", "VREFN_TRUNK")
DROOP_LIMIT_V, DECISION_LIMIT_LSB, SPAN_LIMIT_V, PIN_LIMIT_A = 0.045, 0.10, 0.26, 5.2e-3


def manifest(identity):
    return json.loads((WORK / identity / "manifest.json").read_bytes())


def fF(v):
    return round(v * 1e15, 3)


def rupolym_segment_ohm(w_um, l_um, temp_c=25.0):
    """Small-signal TT resistance of one rupolym segment from the PDK model (cln28ull_1d8_elk_v1d8_3, subckt rupolym:
    r_rupolym 584.149 ohm/sq, rend_rupolym 11.2 ohm um per end, layout scale 0.9): body plus both ends."""
    wum, lum, dt = w_um * 0.9, l_um * 0.9, temp_c - 25.0
    w = min(wum, 1.8)
    tfac = 1 + (3e-4 - 4e-7 / w) * dt + (-3.35336659774003e-08 + 1e-9 / w) * dt * dt
    tfac_end = 1 + (-1.795e-3 - 8e-5 / w) * dt + (5e-6 - 1e-7 / w) * dt * dt
    body = (584.148896787797 + 1.05 / wum ** 1.36) * lum / (wum + 0.0062) * tfac
    ends = 2 * 1.12e-5 * 1e6 / (wum + 0.0375) * tfac_end
    return body + ends


def reference_devices(summary):
    rows = {k: v for k, v in summary.items() if k.startswith("RREF")}
    seg = {t: rupolym_segment_ohm(0.5, 0.5, t) for t in (-40.0, 25.0, 125.0)}
    rref = {}
    for pad in ("VREFP", "VREFN"):
        n = sum(v["segments"] for v in rows.values() if v["pad"] == pad)
        rref[pad] = dict(banks=sorted(k for k, v in rows.items() if v["pad"] == pad), segments=n,
                         model_ohm_tt={f"{t:g}C": round(r / n, 3) for t, r in seg.items()})
    groups = [k for k in CREF_GROUPS if k in summary]
    area = sum(summary[k]["gate_um2"] for k in groups)
    c = area * C_PER_UM2_F
    cref = dict(arrays={k: summary[k]["devices"] for k in groups},
                devices=sum(summary[k]["devices"] for k in groups), gate_um2=round(area, 2), estimated_F=round(c, 15),
                target_F=CREF_TARGET_F, tolerance=CREF_TOL,
                within_target_band=bool(CREF_TARGET_F * (1 - CREF_TOL) <= c <= CREF_TARGET_F * (1 + CREF_TOL)))
    return dict(rref=dict(device="rupolym 0.5 x 0.5 um, Parallel, segSp 180 nm", segment_ohm_tt={f"{t:g}C": round(r, 2)
                                                                                                  for t, r in seg.items()},
                          per_rail=rref, target_ohm=RREF_TARGET_OHM, tolerance=RREF_TOL), cref=cref)


def pnwdio(netlist):
    """N-well junction diodes of the CREF wells (VREFN_TRUNK to the substrate) in the layout netlist."""
    n, area, perim = 0, 0.0, 0.0
    for line in open(netlist, encoding="utf-8", errors="replace"):
        tok = line.split()
        if len(tok) > 3 and tok[0].upper().startswith("D") and tok[3] == "pnwdio" and "VREFN_TRUNK" in tok[1:3]:
            n += 1
            area += float(re.search(r"AREA=(\S+)", line).group(1))
            perim += float(re.search(r"PJ=(\S+)", line).group(1))
    return dict(net="VREFN_TRUNK", to="substrate (VSS)", diodes=n, area_um2=round(area * 1e12, 2),
                perimeter_um=round(perim * 1e6, 2))


def top_capacitance(args, placement_pex):
    """TOPN/TOPP totals on the unlabelled stream against Stage 4a and the placement pieces (pins only, and with the
    pair VSS tied to a 0 pin as in Stage 4b); the imbalance is the difference of the absolute totals."""
    raw = Extraction(WORK / args.raw_xtr / "pex").capacitance()
    r4a = Extraction(WORK / args.route_int_pex / "pex").capacitance()
    pins = Extraction(placement_pex).capacitance()
    tied = Extraction(WORK / args.tied_placement_pex / "pex").capacitance()

    def pieces(c, n):
        ps = [k for k in c if k.startswith(n + "__")]
        return sum(sum(c[p].values()) for p in ps) - sum(c[p].get(q, 0.0) for p in ps for q in ps if p != q)

    out = {}
    for n in ("TOPN", "TOPP"):
        out[n] = dict(total_fF=fF(sum(raw[n].values())), stage4a_total_fF=fF(sum(r4a[n].values())),
                      placement_pins_only_fF=fF(pieces(pins, n)), placement_pair_vss_tied_fF=fF(pieces(tied, n)),
                      coupling_to_stage4b_nets_fF={q: round(v * 1e15, 4) for q, v in raw[n].items()
                                                   if q in STAGE4B_NETS and v > 1e-19},
                      coupling_to_pair_reference_rails_fF={q: round(v * 1e15, 4) for q, v in raw[n].items()
                                                           if q in PAIR_REF_RAILS and v > 1e-19})
        out[n]["added_vs_tied_placement_fF"] = round(out[n]["total_fF"] - out[n]["placement_pair_vss_tied_fF"], 3)
        out[n]["change_from_stage4a_fF"] = round(out[n]["total_fF"] - out[n]["stage4a_total_fF"], 3)
    diff = lambda k: round(abs(out["TOPN"][k] - out["TOPP"][k]), 3)
    out.update(imbalance_fF=diff("total_fF"), stage4a_imbalance_fF=diff("stage4a_total_fF"),
               placement_pins_only_imbalance_fF=diff("placement_pins_only_fF"),
               placement_pair_vss_tied_imbalance_fF=diff("placement_pair_vss_tied_fF"))
    lim = budgets()
    out["limits_fF"] = dict(added=fF(lim["comparator_input_route_capacitance_F"]["limit"]),
                            imbalance=fF(lim["TOP_differential_capacitance_imbalance_F"]["limit"]))
    out["pass"] = bool(max(out[n]["added_vs_tied_placement_fF"] for n in ("TOPN", "TOPP")) <= out["limits_fF"]["added"]
                       and out["imbalance_fF"] <= out["limits_fF"]["imbalance"])
    out["evidence"] = dict(full=args.raw_xtr, stage4a=args.route_int_pex, placement_pins_only=args.placement_pex,
                           placement_pair_vss_tied=args.tied_placement_pex)
    return out


def rail_budget(args):
    """Stage 1 rail models (rail_budget.py, ring_supply.py) rerun with the drawn decoupling, CREF and RREF and the
    in-core feeds (Layout/tools/analysis/toplevel_full_rail.py)."""
    data = json.loads((ROOT / args.rail).read_bytes())
    sup = data["supply"]
    branches = {}
    for name, b in sup.items():
        if not isinstance(b, dict) or "core_alone" not in b:
            continue
        worst = max(r["droop_v"] for r in b["core_alone"])
        row = dict(cap_F=b["cap_f"], in_core_loop_ohm_125c=[r["feed_ohm"] for r in b["core_alone"]],
                   core_alone_droop_V=round(worst, 4),
                   core_alone_droop_with_stage1_feed_V=round(b["core_alone_stage1_feed"]["droop_v"], 4))
        if "with_pad_bulk" in b:
            row["with_pad_bulk_droop_V"] = round(max(r["droop_v"] for r in b["with_pad_bulk"]), 4)
        row["pass"] = bool(worst <= DROOP_LIMIT_V)
        branches[name] = row
    coupled = {k: round(max(c["droop_all_firing_v"][k] for c in sup["coupled_shared_bus_125c_rcworst"]), 4)
               for k in sup["coupled_shared_bus_125c_rcworst"][0]["droop_all_firing_v"]}
    ref = data["reference"]
    corners = {k: dict(nominal_decision_error_LSB=round(v["nominal"]["decision_error_lsb"], 4),
                       box_decision_error_LSB=round(v["box"]["decision_error_lsb"], 4),
                       nominal_span_droop_V=round(v["nominal"]["span_droop_v"], 4),
                       box_span_droop_V=round(v["box"]["box_max_span_droop_v"], 4),
                       box_pin_peak_A=round(v["box"]["box_max_pin_peak_a"], 5)) for k, v in ref["corners"].items()}
    worst = lambda k: max(c[k] for c in corners.values())
    return dict(
        model="Layout/tools/analysis/rail_budget.py and ring_supply.py (Stage 1), inputs replaced by the drawn values",
        supply={"branches": branches, "coupled_shared_bus_125c_rcworst_droop_V": coupled, "limit_V": DROOP_LIMIT_V,
                "pass": all(b["pass"] for b in branches.values()) and max(coupled.values()) <= DROOP_LIMIT_V},
        reference={"cref_F": ref["cref_f"], "series_ohm": ref["series_ohm"],
                   "tolerance_box": "series x0.8-1.2, CREF x0.75-1.25 around the drawn value, 0.5-1.5 nH per rail, "
                                    "the 9 x 9 route range",
                   "corners": corners, "limits": dict(decision_error_LSB=DECISION_LIMIT_LSB, span_droop_V=SPAN_LIMIT_V,
                                                      pin_peak_A=PIN_LIMIT_A),
                   "pass": bool(worst("box_decision_error_LSB") <= DECISION_LIMIT_LSB
                                and worst("box_span_droop_V") <= SPAN_LIMIT_V and worst("box_pin_peak_A") <= PIN_LIMIT_A)},
        sensitivity_cref_F={k: dict(box_decision_error_LSB=v["box"], box_span_droop_V=v["droop"], box_pin_peak_A=v["pin"])
                            for k, v in data.get("cref_sweep", {}).items()},
        source=args.rail)


def build(args):
    content = json.loads((ROOT / args.content).read_bytes())
    summary = content["summary"]
    base = manifest(args.route_int_checks)["checks"]["drc"]["markers_by_rule"]
    full = manifest(args.checks)["checks"]["drc"]["markers_by_rule"]
    delta = {k: [base.get(k, 0), full.get(k, 0)] for k in sorted(set(base) | set(full)) if base.get(k, 0) != full.get(k, 0)}
    density = lambda r: ".DN." in r or r.startswith("Mx.DN") or r == "OD.S.14"
    new_rules = sorted(k for k in full if k not in base)
    hcells = set(block_masters(WORK / args.placement_stream / "fixture.gds"))
    connectivity = conn.check(WORK / args.xtr / "spice/layout.sp", WORK / args.placement_netlist / "spice/layout.sp",
                              hcells, summary, WORK / args.xtr / "spice.console")
    placement_pex, full_pex = WORK / args.placement_pex / "pex", WORK / args.xtr / "pex"
    par = analyze(placement_pex, full_pex)
    ex = Extraction(full_pex)
    rows = evaluate(par, budgets())
    decap = {}
    for k, names in GROUPS.items():
        area = sum(summary[n]["gate_um2"] for n in names if n in summary)
        devices = sum(summary[n]["devices"] for n in names if n in summary)
        decap[k] = dict(devices=devices, gate_um2=round(area, 2), estimated_F=round(area * C_PER_UM2_F, 15),
                        stage1_required_F=STAGE1_F[k], ratio=round(area * C_PER_UM2_F / STAGE1_F[k], 3))
    receipt = json.loads((WORK / args.build / "build.json").read_bytes())
    reference = dict(reference_devices(summary), routing=fpara.reference(ex),
                     cref_well_junction=pnwdio(WORK / args.xtr / "spice/layout.sp"))
    for pad, r in reference["routing"].items():
        rail = reference["rref"]["per_rail"][pad]
        # boundary pin to the pair's rail end: pad-side routing, the resistor (model), trunk-side routing
        rail["series_ohm_tt_25C"] = round(rail["model_ohm_tt"]["25C"] + r["pad_pin_to_rref_ohm"] + r["rail_end_to_rref_ohm"], 3)
        rail["within_target_band"] = bool(abs(rail["series_ohm_tt_25C"] / RREF_TARGET_OHM - 1) <= RREF_TOL)
    return dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/toplevel_full_record.py",
        stage="Stage 4b of chenzc24/sar-adc-t28#12: boundary signal routes, the three supply branches with decoupling, "
              "the shield tie and the on-chip reference network (VREF pins, RREFP/RREFN, CREF)",
        cellview=dict(library="SAR_ADC_T28_LAYOUT", cell="sar8_adc_core", view="layout_route_full",
                      copied_from="layout_route_int", build=args.build, build_ok=receipt["ok"],
                      read_only_views_unchanged="READ_ONLY_VIEW_CHANGED" not in "\n".join(receipt["stdout"]),
                      stream_layout_oa_sha256=manifest(args.checks)["source"]["layout_oa_sha256"]),
        generator=dict(geometry="Layout/design/toplevel_full_routes.py", builder="Layout/design/toplevel_full.py",
                       geometry_sha256=hashlib.sha256((ROOT / "Layout/design/toplevel_full_routes.py").read_bytes()).hexdigest(),
                       rects=len(content["rects"]), pcells=len(content["pcells"]),
                       terminals={t["net"]: len(t["pins"]) for t in content["terminals"]},
                       labels=[t["net"] for t in content.get("labels", [])]),
        evidence=dict(build=args.build, checks=args.checks, extraction=args.xtr, unlabelled_extraction=args.raw_xtr,
                      placement_pex=args.placement_pex, placement_pair_vss_tied_pex=args.tied_placement_pex, host="thu-wei"),
        drc=dict(route_int_markers=sum(base.values()), full_markers=sum(full.values()), delta_by_rule=delta,
                 new_rules=new_rules, non_density_changes=sorted(k for k in delta if not density(k)),
                 verdict="only density windows changed (deferred to top-level fill); no new geometry rule"
                 if not [k for k in delta if not density(k)] else "geometry rules changed"),
        connectivity=connectivity,
        route_budgets=rows, route_budgets_pass=all(r["pass"] for r in rows),
        route_budgets_note="The TOP rows use the Stage 4a method (added capacitance against the pins-only placement, "
                           "with the pair VSS floating there); top_capacitance is the like-for-like reading.",
        route_budget_nets={n: {k: v[k] for k in ("added_fF", "routed_total_fF", "elmore_delay_ps",
                                                  "switch_to_cdac_plate_resistance_max_ohm") if k in v}
                           for n, v in par["nets"].items()},
        top_capacitance=top_capacitance(args, placement_pex),
        vin=fpara.vin(ex), feeds=fpara.feeds(ex), decoupling=decap, reference=reference, rail_budget=rail_budget(args),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("content", "build", "checks", "xtr", "raw-xtr", "route-int-checks", "route-int-pex", "placement-stream",
              "placement-netlist", "placement-pex", "tied-placement-pex", "rail"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--out", default="Layout/results/toplevel_route_full.json")
    args = ap.parse_args()
    record = build(args)
    write_json(ROOT / args.out, record)
    print(json.dumps(dict(drc=record["drc"]["verdict"], connectivity=record["connectivity"]["verdict"],
                          budgets=record["route_budgets_pass"], top=record["top_capacitance"]["pass"],
                          supply=record["rail_budget"]["supply"]["pass"],
                          reference=record["rail_budget"]["reference"]["pass"]), indent=1))


if __name__ == "__main__":
    main()
