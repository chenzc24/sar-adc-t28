"""Record of the partial chip assembly sar8_adc_chip/layout (Stage 5) from fetched evidence.

Writes Layout/results/chip_assembly.json: the build and its guarded views, the routes drawn and not drawn with every
pad landing, the landing points left for the undrawn chip objects, the pad geometry read from the placed masters,
chip DRC by rule (installed chip deck) against the same deck on the ring alone and on the core alone, chip LVS with
its top-cell counts, and ERC by check against the ring cell's baseline (Layout/results/io_ring_verification.json).
"""
import argparse
import datetime
import json
import re

from Layout.design import chip_routes
from Layout.design.toplevel_route import WORK as EVIDENCE
from Layout.project import ROOT, write_json
from Layout.tools.analysis.toplevel_lvs_record import top_summary

CHIP_WORK = ROOT / "work/layout/chip"
CORE = (363.885, 449.0, 485.885, 560.0)


def manifest(identity):
    return json.loads((EVIDENCE / identity / "manifest.json").read_bytes())


def markers(identity):
    """Marker boxes by rule from a fetched DRC_RES.db, each tagged ring, opening or core by its centre."""
    t = (EVIDENCE / identity / "drc/DRC_RES.db").read_text(encoding="latin1").splitlines()
    scale = float(t[0].split()[1])
    out, i = {}, 1
    while i < len(t):
        line = t[i].strip()
        if re.match(r"^[A-Za-z][\w.:]*$", line) and i + 1 < len(t) and re.match(r"^\d+ \d+ \d+", t[i + 1]):
            rule, n, nh = line, int(t[i + 1].split()[0]), int(t[i + 1].split()[2])
            i, k = i + 2 + nh, 0
            while i < len(t) and k < n:
                m = re.match(r"^[ep] \d+ (\d+)", t[i])
                if not m:
                    i += 1
                    continue
                cnt = int(m.group(1))
                pts = [tuple(int(v) / scale for v in t[i + 1 + q].split()[:2]) for q in range(cnt)]
                x, y = sum(p[0] for p in pts) / cnt, sum(p[1] for p in pts) / cnt
                area = "core" if CORE[0] <= x <= CORE[2] and CORE[1] <= y <= CORE[3] else \
                    "opening" if 110 <= x <= 650 and 110 <= y <= 650 else "ring"
                out.setdefault(rule, {}).setdefault(area, 0)
                out[rule][area] += 1
                i, k = i + cnt + 1, k + 1
        else:
            i += 1
    return out


def drc(args):
    chip = manifest(args.checks)["checks"]["drc"]["markers_by_rule"]
    ring = manifest(args.ring_baseline)["checks"]["drc"]["markers_by_rule"]
    core = manifest(args.core_baseline)["checks"]["drc"]["markers_by_rule"]
    where = markers(args.checks)
    # density windows and the empty-area OD rule belong to fill (Layout/specs/fill-policy.md)
    density = lambda r: ".DN." in r or r.startswith("Mx.DN") or r.endswith(".DN.1") or r == "OD.S.14"
    rows = {}
    for rule in sorted(set(chip) | set(ring) | set(core)):
        rows[rule] = dict(chip=chip.get(rule, 0), ring_alone=ring.get(rule, 0), core_alone=core.get(rule, 0),
                          chip_by_area=where.get(rule, {}), density=density(rule))
    new = {r: v for r, v in rows.items() if not v["density"] and v["chip"] > v["ring_alone"] + v["core_alone"]}
    return dict(deck="drc_rule_T28_chip (installed chip deck: drc_rule_T28_cell with FULL_CHIP and WITH_SEALRING)",
                chip_markers=sum(chip.values()), ring_alone_markers=sum(ring.values()), core_alone_markers=sum(core.values()),
                ring_cell_deck_baseline="0 results with the generator's cell-level selection (81 checks deselected; "
                                        "Layout/results/io_ring_verification.json)",
                by_rule=rows, non_density_rules_above_baselines=new,
                evidence=dict(chip=args.checks, ring_alone=args.ring_baseline, core_alone=args.core_baseline))


def lvs_erc(args):
    m = manifest(args.checks)["checks"]["lvs"]
    rep = (EVIDENCE / args.checks / "lvs/lvs.rep").read_text(encoding="utf-8", errors="replace")
    ring = json.loads((ROOT / "Layout/results/io_ring_verification.json").read_bytes())["erc"]["this_ring"]["counts"]
    erc = m.get("erc_results_by_check", {})
    errors = sorted(set(re.findall(r"(?m)^\s*Error:\s*(.*)$", rep)))
    return dict(lvs=dict(verdict=m["verdict"], cells=m["cells"], top=top_summary(rep, "sar8_adc_chip"), errors=errors,
                         deck=manifest(args.checks)["decks"]["lvs"]),
                erc=dict(chip=erc, ring_cell_baseline=ring, total=dict(chip=sum(erc.values()), ring=sum(ring.values())),
                         by_check={k: [erc.get(k, 0), ring.get(k, 0)] for k in sorted(set(erc) | set(ring))}))


def build(args):
    content = json.loads((CHIP_WORK / args.build / "content.json").read_bytes())
    info = content["info"]
    built = json.loads((CHIP_WORK / args.build / "build.json").read_bytes())
    bond = json.loads((CHIP_WORK / "bond_openings.json").read_bytes())
    pins = json.loads((CHIP_WORK / "core_pins.json").read_bytes())
    plan = chip_routes.ring_plan()
    pads = {p["position"]: p for p in plan["pads"]}
    pending = {
        "output_register": dict(region="output_register", adc_pins={f"D{k}": [485.885, 502.4 + 1.2 * k] for k in range(8)},
                                adc_pin_layer="M7", clock="SAMPLE_CORE: tap the drawn SAMPLE M8 route (x 550 vertical)",
                                q_outputs={f"D{k}_CORE": pins[pads_pos]["union"] for k, pads_pos in
                                           enumerate(("right_3", "right_2", "right_1", "bottom_7", "bottom_5", "bottom_4",
                                                      "bottom_2", "bottom_1"))},
                                dvdd=dict(pad="right_4", core_pin=pads["right_4"]["core_pin_um"], extent=pins["right_4"]["union"])),
        "core_vss_ring": dict(region="core_vss_ring (M7)", vss_pads={p: dict(core_pin=pads[p]["core_pin_um"], extent=pins[p]["union"])
                                                                      for p in ("left_7", "top_7")}),
        "adc_guard_ring": dict(region="adc_guard_ring (2 um P+, AVSS_CORE)", core_guard_pin=dict(net="0", name="0_guard",
                               layer="M2", box_um=[485.485, 500.2, 485.885, 500.8]),
                               feed=dict(route="AVSS_guard", pad="left_0", core_pin=pads["left_0"]["core_pin_um"],
                                         extent=pins["left_0"]["union"]),
                               note="PSUB2 already marks this outline as the ADC P-well domain"),
        "pad_decaps": {k: dict(region=v["pad_decap"], routes=v["routes"]) for k, v in plan["supply_plan"]["adc_branches"].items()},
        "pclampc": [r["id"] for r in plan["reserved_regions"] if r["kind"] == "clamp"],
        "unrouted_avss_core_pads": [p for p, v in pads.items() if v.get("core_net") == "AVSS_CORE" and
                                    p not in ("top_3", "left_6", "right_8")],
    }
    return dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/chip_record.py",
        stage="Stage 5 of chenzc24/sar-adc-t28#12: partial chip assembly (ring, core and the core-to-pad routes that "
              "need no undrawn chip object)",
        cellview=dict(library="SAR_ADC_T28_LAYOUT", cell="sar8_adc_chip", view="layout", build=args.build,
                      generator="Layout/design/chip_assembly.py build, geometry Layout/design/chip_routes.py",
                      instances=dict(XRING="sar8_io_ring/layout at (0, 0) R0",
                                     XADC="sar8_adc_core/layout_route_guard at (363.885, 449.0) R0"),
                      build_ok=built["ok"], guarded=built["guarded"], rects=built["rects"], labels=built["labels"],
                      psub2=chip_routes.PSUB2, poc_label=chip_routes.POC_LABEL),
        routes=dict(drawn=info["routed"], landings=info["landings"], not_drawn=info["not_routed"]),
        pending_objects=pending,
        pad_geometry=dict(source=f"ring readback {args.readback} and pad probe chip-pad-probe-20261122c (read-only)",
                          bond_centres={k: v["centre"] for k, v in bond.items()},
                          bond_centre_shift_um=sorted({tuple(v["delta"]) for v in bond.values()}),
                          core_pins={k: v for k, v in pins.items() if isinstance(v, dict)}),
        drc=drc(args), **lvs_erc(args),
        evidence=dict(readback=args.readback, build=args.build, checks=args.checks, host="thu-wei"),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("build", "readback", "checks", "ring-baseline", "core-baseline"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--out", default="Layout/results/chip_assembly.json")
    args = ap.parse_args()
    record = build(args)
    write_json(ROOT / args.out, record)
    d = record["drc"]
    print(json.dumps(dict(drc=dict(chip=d["chip_markers"], ring=d["ring_alone_markers"], core=d["core_alone_markers"],
                                   new=d["non_density_rules_above_baselines"]),
                          lvs=record["lvs"]["verdict"], lvs_errors=record["lvs"]["errors"], erc=record["erc"]["total"]),
                     indent=1))


if __name__ == "__main__":
    main()
