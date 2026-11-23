"""Supply rail budget of the chip with the drawn pad decoupling (sar8_adc_chip/layout_full_fill5_r3).

Stage 4b (Layout/tools/analysis/toplevel_full_rail.py, Layout/results/toplevel_route_full.json) checked the in-core
branches against the planned pad bulk: about 114 / 114 / 132 pF at 2 ohm ESR per rail, and the ring feed of the
10 um M8 model. This reruns the same Stage 1 models (rail_budget.supply_check, ring_supply.chip) with the drawn
values of the chip objects (Layout/results/chip_objects.json):
- pad bulk: geometry_r3 (analog: nmoscap plus MOM) and geometry_r2 (pair, SAR);
- bulk ESR per rail: the drawn model (an upper bound), and 1 ohm per rail as the less-damped sensitivity case;
- ring feed: the drawn loop resistances at 125 C rcworst_T (ring_feed_r2), pad-to-bulk and bulk-to-pin.
The in-core decoupling and loops are the Stage 4b drawn values; the core views since then (layout_route_boot_r2, the
filled layout_fill5) keep the supply routing of layout_route_full. Writes Layout/results/chip_rail_recheck.json.
"""
import argparse
import json

from Layout.project import ROOT, write_json
from Layout.tools.analysis import rail_budget as rb
from Layout.tools.analysis import ring_supply as rs
from Layout.tools.analysis.toplevel_full_rail import BRANCHES

LIMIT_V = 0.045
BRANCH = ("analog", "pair", "sar")


def drawn_bulk(objects, esr_override=None):
    out = {}
    for name in BRANCH:
        g = objects["geometry_r3" if name == "analog" else "geometry_r2"][f"decap_{name}"]
        esr = g["esr_upper_bound_per_rail"]
        parallel = [v["total_ohm"] for k, v in esr.items() if k.endswith("(ports in parallel)")]
        rails = parallel or [v["total_ohm"] for k, v in esr.items() if "#" not in k]
        feed = objects["ring_feed_r2"][name]
        out[name] = dict(bulk_f=g["capacitance_pF"] * 1e-12,
                         esr_ohm_per_rail=esr_override if esr_override is not None else sum(rails) / len(rails),
                         pad_to_bulk_ohm=max(feed["pad_to_pin_ohm"] - feed["bulk_to_pin_ohm"], 0.),
                         bulk_to_pin_ohm=feed["bulk_to_pin_ohm"])
    return out


def extracted_bulk(objects, periphery):
    """drawn_bulk with the ring feeds from the periphery extraction (Layout/results/chip_periphery.json supply_feeds):
    per rail the star of pad, decap port and ADC pin, scaled from 25 C typical to 125 C rcworst_T by the trunk layer
    (AVDD M9, AVSS M8; the via stacks are scaled with it). The decap's star arm adds to its ESR per rail."""
    scale = dict(AVDD=rs.rsh("M9", 125, True) / rs.rsh("M9"), AVSS=rs.rsh("M8", 125, True) / rs.rsh("M8"))
    out = drawn_bulk(objects)
    for name in BRANCH:
        rails = periphery["supply_feeds"][name]["rails"]
        star = {k: {arm: v * scale[k] for arm, v in r["star_ohm"].items()} for k, r in rails.items()}
        out[name].update(pad_to_bulk_ohm=sum(s["pad"] for s in star.values()),
                         bulk_to_pin_ohm=sum(s["pin"] for s in star.values()),
                         esr_ohm_per_rail=out[name]["esr_ohm_per_rail"] + sum(max(s["decap"], 0.) for s in star.values()) / 2)
    return out


def run(objects, stage4b, esr_override=None, drawn=None):
    drawn = drawn or drawn_bulk(objects, esr_override)
    k = rb.CORNER_CHARGE
    rows = {}
    for name in BRANCH:
        b, s4 = BRANCHES[name], stage4b["supply"]["branches"][name]
        pulse = .2e-9 if b["event_c"] < .1e-12 else .5e-9
        q = (b["event_c"] * k, b["repeat_c"] * k)
        d = drawn[name]
        cases = []
        for loop in s4["in_core_loop_ohm_125c"]:
            feed = d["bulk_to_pin_ohm"] + loop
            r = rb.supply_check(*q, s4["cap_F"], feed, pulse=pulse, bulk=True, bulk_f=d["bulk_f"],
                                bulk_esr_ohm_per_rail=d["esr_ohm_per_rail"])
            cases.append(dict(feed_ohm=round(feed, 3), droop_V=round(r["droop_v"], 4),
                              pin_peak_A=round(r["pin_peak_a"], 5)))
        rows[name] = dict(drawn={k_: round(v, 15) if k_ == "bulk_f" else round(v, 3) for k_, v in d.items()},
                          block_cap_F=s4["cap_F"], with_drawn_bulk=cases,
                          stage4b_with_planned_bulk_droop_V=s4["with_pad_bulk_droop_V"],
                          core_alone_droop_V=s4["core_alone_droop_V"],
                          worst_droop_V=max(c["droop_V"] for c in cases))
    updates, _ = rb.schedule(*rb.CORNERS["ffc"])
    charges = {n: (BRANCHES[n]["event_c"] * k, BRANCHES[n]["repeat_c"] * k) for n in BRANCH}
    events = {n: [(u, qq, .5e-9) for u, qq in zip(updates, [c[0]] + [c[1]] * 7 + [c[0]])] for n, c in charges.items()}
    coupled = []
    for idx in (0, -1):
        core = {n: stage4b["supply"]["branches"][n]["in_core_loop_ohm_125c"][idx] for n in BRANCH}
        ckt, _ = rs.chip(shared_bus=True, bus_temp_c=125., core_feed_ohm=core,
                         blocks={n: stage4b["supply"]["branches"][n]["cap_F"] for n in BRANCH}, drawn=drawn)
        t, v = ckt.run(events)
        coupled.append(dict(core_feed_ohm=core, droop_all_firing_V={n: round(rs.droop(ckt, t, v, n), 4) for n in BRANCH}))
    worst = max([r["worst_droop_V"] for r in rows.values()] +
                [x for c in coupled for x in c["droop_all_firing_V"].values()])
    return dict(branches=rows, coupled_shared_bus_125c_rcworst=coupled, worst_droop_V=round(worst, 4),
                limit_V=LIMIT_V, pass_=worst <= LIMIT_V)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="Layout/results/chip_rail_recheck.json")
    a = ap.parse_args()
    objects = json.loads((ROOT / "Layout/results/chip_objects.json").read_bytes())
    stage4b = json.loads((ROOT / "Layout/results/toplevel_route_full.json").read_bytes())["rail_budget"]
    record = dict(
        schema_version=1, tool="Layout/tools/analysis/chip_rail_recheck.py",
        chip_view="SAR_ADC_T28_LAYOUT/sar8_adc_chip/layout_full_fill5_r3",
        basis=dict(models="rail_budget.supply_check (per branch, pad bulk) and ring_supply.chip (shared TACVDD/TACVSS "
                          "bus, all branches firing on the same FF-cold updates, 125 C rcworst)",
                   in_core="Stage 4b drawn decoupling and in-core loops (toplevel_route_full.json rail_budget)",
                   pad_bulk="chip_objects.json geometry_r3 (analog), geometry_r2 (pair, SAR); ESR = drawn model",
                   ring_feed="chip_objects.json ring_feed_r2 (drawn, 125 C rcworst)",
                   charge="Stage 1 calibration and the 1.3 corner charge allowance"),
        drawn_esr=run(objects, stage4b),
        esr_1_ohm_per_rail=run(objects, stage4b, esr_override=1.0))
    periphery = ROOT / "Layout/results/chip_periphery.json"
    cases = ["drawn_esr", "esr_1_ohm_per_rail"]
    if periphery.exists():
        p = json.loads(periphery.read_bytes())
        record["basis"]["extracted_feed"] = ("chip_periphery.json supply_feeds (extraction " + p["extraction"]["identity"]
                                             + ", 25 C typical, scaled to 125 C rcworst_T by the trunk layer)")
        record["extracted_feed"] = run(objects, stage4b, drawn=extracted_bulk(objects, p))
        cases.append("extracted_feed")
    write_json(ROOT / a.out, record)
    for case in cases:
        r = record[case]
        print(case, "worst", r["worst_droop_V"], "pass", r["pass_"],
              {n: (b["drawn"]["bulk_f"], b["drawn"]["esr_ohm_per_rail"], b["worst_droop_V"],
                   b["stage4b_with_planned_bulk_droop_V"]) for n, b in r["branches"].items()},
              [c["droop_all_firing_V"] for c in r["coupled_shared_bus_125c_rcworst"]])


if __name__ == "__main__":
    main()
