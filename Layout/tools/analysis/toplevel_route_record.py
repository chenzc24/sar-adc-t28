"""Assemble the Stage 4a record of the core-internal routes from fetched evidence.

Inputs are the work/layout/toplevel-route/<id>/ copies of the native runs: the placement baseline
(stream, DRC, netlist, labelled extraction), the routed view's build receipt and its checks (stream,
DRC, netlist, extraction). Writes Layout/results/toplevel_route_internal.json.
"""
import argparse
import datetime
import hashlib
import json

from Layout.design.toplevel_route import WORK, compare_streams
from Layout.design.toplevel_routes import plan
from Layout.project import ROOT, write_json
from Layout.tools.analysis import toplevel_route_connectivity as conn
from Layout.tools.analysis import toplevel_route_parasitics as para
from Layout.tools.analysis import toplevel_route_precheck as pre

CONSTRAINTS = ROOT / "Layout/specs/constraints.json"


def manifest(identity):
    return json.loads((WORK / identity / "manifest.json").read_bytes())


def budgets():
    b = json.loads(CONSTRAINTS.read_bytes())["electrical_budgets"]
    for key in ("comparator_input_route_capacitance_F", "reference_gate_route_delay_s", "sar_handshake_route_delay_s"):
        if not b[key]["status"].startswith("adopted"):
            raise ValueError(f"{key} is not adopted")
    return b


def evaluate(p, b):
    top = b["comparator_input_route_capacitance_F"]
    hs = b["sar_handshake_route_delay_s"]
    code = b["reference_gate_route_delay_s"]
    imbalance = b["TOP_differential_capacitance_imbalance_F"]
    n = p["nets"]
    rows = []

    def row(item, limit, value, unit, scope):
        rows.append(dict(item=item, limit=round(float(limit), 4), measured=float(value), unit=unit, scope=scope,
                         pass_=bool(value <= limit)))

    for side in ("TOPN", "TOPP"):
        row(f"{side} added capacitance", top["limit"] * 1e15, n[side]["added_fF"], "fF",
            "routed total minus the CDAC, comparator-input and Bootstrap-output pieces of the placement view; "
            "all partners counted, signal coupling included")
        row(f"{side} sampler route resistance", top["sampler_route_resistance_limit_ohm"],
            n[side]["switch_to_cdac_plate_resistance_max_ohm"], "ohm",
            "Bootstrap switch terminals to the shorted CDAC capacitor terminals; includes both blocks' own wiring")
    row("TOP side imbalance of added capacitance", imbalance["limit"] * 1e15,
        round(abs(n["TOPN"]["added_fF"] - n["TOPP"]["added_fF"]), 4), "fF", "|added TOPN - added TOPP|")
    for net in ("COMP_P", "COMP_N", "CMP_CLK"):
        row(f"{net} route load", hs["load_limit_F"][net] * 1e15, n[net]["added_fF"], "fF",
            "capacitance the route adds to the net, all partners; the Stage 2 runs kept the ~10 fF model load on top")
        rx = "sar" if net != "CMP_CLK" else "comparator"
        row(f"{net} one-way delay (Elmore bound)", hs["limit"] * 1e12, n[net]["elmore_delay_ps"][rx], "ps",
            "driver drain/source terminals to receiver gate terminals, coupling grounded, 1 fF per receiver gate")
    for net in [f"CODE{i}" for i in range(8)] + ["PRESET"]:
        row(f"{net} one-way delay (Elmore bound)", code["limit"] * 1e12, n[net]["elmore_delay_ps"]["reference"], "ps",
            "SAR driver terminals to XREF gate terminals, coupling grounded, 1 fF per receiver gate")
    for r in rows:
        r["pass"] = r.pop("pass_")
    return rows


def symmetry(p, ex_routed, ex_place):
    cr, cb = ex_routed.capacitance(), ex_place.capacitance()
    f = lambda d, a, c: round(d[a].get(c, 0.0) * 1e18, 2)
    core = dict(CLK_OUTP=f(cb, "CMP_CLK__XCOMP", "COMP_P__XCOMP"), CLK_OUTN=f(cb, "CMP_CLK__XCOMP", "COMP_N__XCOMP"),
                CLK_VINP=f(cb, "CMP_CLK__XCOMP", "TOPP__XCOMP"), CLK_VINN=f(cb, "CMP_CLK__XCOMP", "TOPN__XCOMP"))
    sar = dict(CLK_COMP_P=f(cb, "CMP_CLK__SAR", "COMP_P__SAR"), CLK_COMP_N=f(cb, "CMP_CLK__SAR", "COMP_N__SAR"))
    routed = dict(CLK_COMP_P=f(cr, "CMP_CLK", "COMP_P"), CLK_COMP_N=f(cr, "CMP_CLK", "COMP_N"),
                  CLK_TOPP=f(cr, "CMP_CLK", "TOPP"), CLK_TOPN=f(cr, "CMP_CLK", "TOPN"))
    n = p["nets"]
    return dict(
        unit="aF",
        comparator_core_placement=core, sar_macro_placement=sar, routed_total=routed,
        clk_output_mirror_difference=dict(core=round(core["CLK_OUTP"] - core["CLK_OUTN"], 2),
                                          sar_macro=round(sar["CLK_COMP_P"] - sar["CLK_COMP_N"], 2),
                                          routed_total=round(routed["CLK_COMP_P"] - routed["CLK_COMP_N"], 2)),
        clk_input_mirror_difference=dict(core=round(core["CLK_VINP"] - core["CLK_VINN"], 2),
                                         routed_total=round(routed["CLK_TOPP"] - routed["CLK_TOPN"], 2)),
        comp_p_minus_comp_n_added_fF=round(n["COMP_P"]["added_fF"] - n["COMP_N"]["added_fF"], 4),
        seq_sample_arm_elmore_ps=n["SEQ_SAMPLE"]["elmore_delay_ps"],
        reference="decisions.cmp_clk_north_drop.verify: v8 core largest mirror difference 7.4 aF")


def build(args):
    p_ids = dict(stream=args.placement_drc, netlist=args.placement_netlist, pex=args.placement_pex)
    r_ids = dict(build=args.build, checks=args.checks, pex=args.pex)
    base_drc = manifest(args.placement_drc)["checks"]["drc"]["markers_by_rule"]
    chk = manifest(args.checks)
    route_drc = chk["checks"]["drc"]["markers_by_rule"]
    delta = {k: [base_drc.get(k, 0), route_drc.get(k, 0)] for k in sorted(set(base_drc) | set(route_drc))
             if base_drc.get(k, 0) != route_drc.get(k, 0)}
    new_rules = sorted(k for k in route_drc if k not in base_drc)
    hcells = json.loads((WORK / args.generate / "routes.json").read_bytes())["hcells"]
    connectivity = conn.check(WORK / args.checks / "spice/layout.sp", WORK / args.placement_netlist / "spice/layout.sp",
                              set(hcells), WORK / args.checks / "spice.console")
    ex_place = para.Extraction(WORK / args.placement_pex / "pex")
    ex_route = para.Extraction(WORK / args.pex / "pex")
    parasitics = para.analyze(WORK / args.placement_pex / "pex", WORK / args.pex / "pex")
    b = budgets()
    rows = evaluate(parasitics, b)
    stream_match = compare_streams(WORK / args.checks / "fixture.gds", WORK / args.generate / "candidate.gds")
    build_receipt = json.loads((WORK / args.build / "build.json").read_bytes())
    intent = json.loads((WORK / args.build / "intent.json").read_bytes())
    record = dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/toplevel_route_record.py",
        stage="Stage 4a of chenzc24/sar-adc-t28#12: core-internal routes (21 planned paths that end only on block pins)",
        cellview=dict(library=intent["library"], cell=intent["cell"], view=intent["view"],
                      built_from=intent["placement"], build=build_receipt["identity"],
                      build_ok=build_receipt["ok"], placement_unchanged="PLACEMENT_CHANGED" not in build_receipt["stdout"]),
        generator=dict(routes="Layout/design/toplevel_routes.py", builder="Layout/design/toplevel_route.py",
                       routes_sha256=intent["routes_sha256"], floorplan_sha256=intent["floorplan_sha256"],
                       rectangles=intent["rects"], labels=intent["labels"], nets=intent["nets"]),
        evidence=dict(placement=p_ids, routed=r_ids, host="thu-wei", root="<remote_root>/evidence/<id>"),
        stream=dict(oa_stream_vs_generated_geometry={k: v["equal"] for k, v in stream_match.items()},
                    gds=chk["gds"]),
        drc=dict(deck="calibre_rule/drc/drc_rule_T28_cell (installed, unmodified switches)",
                 placement_markers=sum(base_drc.values()), routed_markers=sum(route_drc.values()),
                 routed_markers_by_rule=route_drc, delta_by_rule=delta, new_rules=new_rules,
                 verdict="no new rule; only density windows, OD.S.14 and the two block-level advisories remain, "
                         "all present in the placement view" if not new_rules else "new rules present"),
        connectivity=connectivity,
        floorplan_rules=pre.regions(),
        parasitics=dict(deck="calibre_rule/rcx/calibre.rcx typical, flat RC + coupling (-rcc)", method=para.__doc__.strip(),
                        nets=parasitics["nets"], shield=parasitics["VSS_SHIELD"]),
        budgets=rows, budgets_pass=all(r["pass"] for r in rows),
        comparator_symmetry=symmetry(parasitics, ex_route, ex_place),
        deviations_from_floorplan=[
            "Extra M3 VSS shield on y 66.9 um between the COMP_P and CMP_CLK stubs into the SAR pins, tied to the "
            "corridor shields at x 88.4-90.8. Without it the routes added 60 aF more CLK coupling to COMP_P than to "
            "COMP_N (trial adc-core-route-c2-pex); with it 10.5 aF (adc-core-route-c3-pex).",
            "The 73.5 um channel shield starts at x 48.215 (east edge of top_fill_exclusion_inputs) instead of 47.3: "
            "with a 0.1 um width its lower edge entered that TOP fill exclusion by 0.035 um.",
            "The VSS shields form one floating net (VSS_SHIELD, 15.5 fF, no device terminals); the VSS tie belongs to "
            "the supply stage. Parasitics count shield coupling as load.",
            "Wires are 0.1 um wide; layer changes use two cuts per level (0.13 um pitch). The CMP_CLK drop is 0.05 um "
            "wide over the core and lands with one VIA3 on the existing M3_M2 via (decisions.cmp_clk_north_drop).",
        ],
        limitations=[
            "Typical-corner flat xRC only; no CWORST/CBEST extraction of the routed core.",
            "Delays are Elmore bounds between device terminals with coupling grounded (no Miller factor) and 1 fF per "
            "receiver gate; no transient was run (no ADC simulation in this stage).",
            "Resistances and delays include the blocks' own pin-side wiring and gate resistance, so they bound the "
            "route-only values from above.",
            "No fill, no fill-exclusion layers drawn; density DRC stays deferred to top-level fill.",
            "Out of scope and not drawn: D0-D7, SAMPLE, VINN/VINP, ADC.* boundary pins, VREF and supply feeds, the SAR "
            "guard ring and the decoupling.",
        ],
        open_items=[
            "decisions.cmp_clk_north_drop.verify: CLK-to-output mirror difference is 37.2 aF in total (2.1 aF core, "
            "24.4 aF inside the SAR macro from its frozen pin order, about 10.5 aF from the routes) against the 7.4 aF "
            "v8 core level; CLK-to-input difference 5.3 aF from the declared unmirrored TOPP crossing. The comparator "
            "TT decision screen with the extracted environment is still to run.",
            "Tie VSS_SHIELD to VSS when the supply feeds are routed.",
            "Equalize COMP_P/COMP_N on extracted capacitance: added load differs by 0.09 fF (5.05 vs 5.14 fF).",
        ],
        inputs_sha256=dict(constraints=hashlib.sha256(CONSTRAINTS.read_bytes()).hexdigest(),
                           floorplan=hashlib.sha256((ROOT / "Layout/design/floorplan.json").read_bytes()).hexdigest()),
        floorplan_status=plan()["status"],
    )
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("placement-drc", "placement-netlist", "placement-pex", "generate", "build", "checks", "pex"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--out", default="Layout/results/toplevel_route_internal.json")
    args = ap.parse_args()
    record = build(args)
    write_json(ROOT / args.out, record)
    print(json.dumps(dict(budgets_pass=record["budgets_pass"], drc=record["drc"]["verdict"],
                          connectivity=record["connectivity"]["verdict"],
                          stream=record["stream"]["oa_stream_vs_generated_geometry"]), indent=1))


if __name__ == "__main__":
    main()
