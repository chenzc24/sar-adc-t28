"""Record of the chip-level objects and the integrated chip sar8_adc_chip/layout_full from fetched evidence.

Writes Layout/results/chip_objects.json: every object cell (OA view, build, geometry summary, cell-level DRC by rule
and LVS), the output register's place and route and its timing check (Layout/results/output_register_timing.json),
the integration build and its routes, chip DRC by rule (installed chip deck) against the partial assembly
(Layout/results/chip_assembly.json, same deck) and against the ring alone and the core alone, each marker placed in
the ring, the ADC core or the object region it falls in, chip LVS with its top-cell counts, and ERC by check against
the partial assembly and the ring cell's baseline (Layout/results/io_ring_verification.json).
"""
import argparse
import datetime
import json
import re

from Layout.design import chip_objects_geometry as geo
from Layout.design.chip_objects import WORK as OBJ
from Layout.design.toplevel_route import WORK as EVIDENCE
from Layout.project import ROOT, write_json
from Layout.tools.analysis.toplevel_lvs_record import top_summary

CORE = (363.885, 449.0, 485.885, 560.0)
OBJECT_CELLS = {
    "output_register": ("sar8_out_reg", "oreg-r1-build3", "oreg-r1-drc2", "oreg-r1-lvs2"),
    "clamps": ("sar8_esd_clamps", "obj-clamps-b3", "obj-clamps-drc3", "obj-clamps-lvs4"),
    "decap_analog": ("sar8_decap_analog", "obj-decap-analog-b8", "obj-decap-analog-drc8", "obj-decap-analog-lvs8"),
    "decap_pair": ("sar8_decap_pair", "obj-decap-pair-b8", "obj-decap-pair-drc8", "obj-decap-pair-lvs8"),
    "decap_sar": ("sar8_decap_sar", "obj-decap-sar-b8", "obj-decap-sar-drc8", "obj-decap-sar-lvs8"),
    "decap_dvdd": ("sar8_decap_dvdd", "obj-decap-dvdd-b8", "obj-decap-dvdd-drc8", "obj-decap-dvdd-lvs8"),
    "core_vss_ring": ("sar8_core_vss_ring", "obj-vss-ring-b3", "obj-vss-ring-drc3", None),
    "adc_guard_ring": ("sar8_adc_guard_ring", "obj-guard-ring-b3", "obj-guard-ring-drc3", None),
}
OBJECT_CELLS_R2 = {    # views layout_r2: the pad decaps grown to their planned capacitance, the analog clamp moved
    "clamps": ("sar8_esd_clamps", "obj-clamps-r2-b1", "obj-clamps-r2-drc1", "obj-clamps-r2-lvs1"),
    "decap_analog": ("sar8_decap_analog", "obj-decap-analog-r2-b3", "obj-decap-analog-r2-drc3", "obj-decap-analog-r2-lvs3"),
    "decap_pair": ("sar8_decap_pair", "obj-decap-pair-r2-b3", "obj-decap-pair-r2-drc3", "obj-decap-pair-r2-lvs3"),
    "decap_sar": ("sar8_decap_sar", "obj-decap-sar-r2-b3", "obj-decap-sar-r2-drc3", "obj-decap-sar-r2-lvs3"),
    "decap_dvdd": ("sar8_decap_dvdd", "obj-decap-dvdd-r2-b1", "obj-decap-dvdd-r2-drc1", "obj-decap-dvdd-r2-lvs1"),
}
NMOSCAP_F = 6.23e-12 / 164           # drawn CREF of layout_route_full: 164 nmoscap (2.5 / 0.8 um) = 6.23 pF


def density(rule):
    return ".DN." in rule or rule.startswith("Mx.DN") or rule == "OD.S.14"


def warning(rule):
    return "WARN" in rule


def obj_manifest(identity):
    return json.loads((OBJ / identity / "manifest.json").read_bytes())


def ev_manifest(identity):
    return json.loads((EVIDENCE / identity / "manifest.json").read_bytes())


def regions():
    out = {"adc_core": CORE}
    for r in geo.plan()["reserved_regions"]:
        if r["id"] in ("adc_core", "analog_input_channel", "reference_channel", "digital_channel", "bottom_channel",
                       "sar_feed_channel"):
            continue
        (x0, y0), (x1, y1) = r["bbox"]
        out[r["id"]] = (x0, y0, x1, y1)
    band = geo.ring_band()
    out["core_vss_ring"] = (band[0][0], band[0][0], band[0][1], band[0][1])
    return out


def where(x, y, regs):
    if not (110 <= x <= 650 and 110 <= y <= 650):
        return "io_ring"
    for name in ("output_register", "pclampc_analog", "pclampc_pair", "pclampc_sar", "analog_pad_decap",
                 "pair_pad_decap", "sar_pad_decap", "dvdd_decap", "adc_core", "adc_guard_ring"):
        x0, y0, x1, y1 = regs[name]
        if x0 <= x <= x1 and y0 <= y <= y1:
            return name
    o0, _, o1, _ = regs["core_vss_ring"]
    inner = (o0 + 17.5, o1 - 17.5)
    if not (inner[0] <= x <= inner[1] and inner[0] <= y <= inner[1]):
        return "core_vss_ring_band"
    return "opening"


def markers(path):
    """Marker counts by rule and area from an ASCII DRC results database."""
    t = path.read_text(encoding="latin1").splitlines()
    scale = float(t[0].split()[1])
    regs = regions()
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
                a = where(x, y, regs)
                out.setdefault(rule, {}).setdefault(a, 0)
                out[rule][a] += 1
                i, k = i + cnt + 1, k + 1
        else:
            i += 1
    return out


def objects(table=None):
    out = {}
    for name, (cell, build, drc, lvs) in (table or OBJECT_CELLS).items():
        b = json.loads((OBJ / build / "build.json").read_bytes())
        intent = json.loads((OBJ / build / "intent.json").read_bytes())
        view = intent.get("view", "layout")
        oa = [l.split()[0] for l in b["stdout"] if l.endswith(f"/{cell}/{view}/layout.oa")]
        rec = dict(cell=f"SAR_ADC_T28_LAYOUT/{cell}/{view}", build=build, layout_oa_sha256=oa[0] if oa else None,
                   build_ok=b["ok"], guarded_unchanged=not any("GUARDED_VIEW_CHANGED" in l for l in b["stdout"]),
                   content=dict(rects=intent["rects"], pcells=intent["pcells"], instances=intent["instances"]))
        d = obj_manifest(drc)["checks"]["drc"]
        rules = d["markers_by_rule"]
        rec["drc"] = dict(identity=drc, deck="drc_rule_T28_cell", markers=d["markers"], by_rule=rules,
                          density_or_fill={r: n for r, n in rules.items() if density(r)},
                          warnings={r: n for r, n in rules.items() if warning(r)},
                          other={r: n for r, n in rules.items() if not density(r) and not warning(r)})
        if lvs:
            m = obj_manifest(lvs)
            rec["lvs"] = dict(identity=lvs, verdict=m["checks"]["lvs"].get("verdict"),
                              virtual_connect=m["decks"]["lvs"].get("virtual_connect_name"),
                              source_sha256=m.get("source_netlist", {}).get("sha256"))
        else:
            rec["lvs"] = dict(note="No devices in this cell (metal, OD and PP only); its connectivity is part of chip LVS.")
        out[name] = rec
    return out


def esr_estimate(content, summary):
    """Series resistance per rail from the drawn port: the M6 neck plus a resistor network of the M6 collector (nodes at
    the bars it crosses) and the M5 bars (each collecting its share uniformly along its length: R/3 per segment),
    0.428 ohm/sq (M2-M7, tech LEF). The M4 straps between the bars are left out, so this bounds the ESR from above.
    A net with two ports (revision 2) combines them in parallel, which assumes they draw from separate bars."""
    import numpy as np
    rs = geo.SHEET_OHM
    out = {}
    for key, port in summary["ports"].items():
        net = port.get("net", key)
        col = port["collector"]
        yc, wcol = (col[1] + col[3]) / 2, col[3] - col[1]
        px = (port["pad"][0] + port["pad"][2]) / 2
        bars = sorted({(round((r["box"][0] + r["box"][2]) / 2, 3), r["box"][1], r["box"][3]) for r in content["rects"]
                       if r["layer"] == "M5" and r["net"] == net and abs(r["box"][2] - r["box"][0] - 2.0) < 1e-6})
        on = [b for b in bars if b[1] <= yc <= b[2]]
        lengths = np.array([b[2] - b[1] for b in on])
        share = lengths / lengths.sum()
        rbar = [1.0 / sum(1.0 / (rs / 2.0 * s / 3.0) for s in (yc - lo, hi - yc) if s > 0) for _, lo, hi in on]
        nodes = sorted(set([b[0] for b in on] + [px]))
        idx = {x: i for i, x in enumerate(nodes)}
        n = len(nodes) + len(on)
        g, cur = np.zeros((n, n)), np.zeros(n)

        def add(a, b, r):
            g[a, a] += 1 / r
            g[b, b] += 1 / r
            g[a, b] -= 1 / r
            g[b, a] -= 1 / r
        for a, b in zip(nodes, nodes[1:]):
            add(idx[a], idx[b], rs / wcol * (b - a))
        for k, (x, _, _) in enumerate(on):
            add(len(nodes) + k, idx[x], rbar[k])
            cur[len(nodes) + k] = share[k]
        keep = [i for i in range(n) if i != idx[px]]
        v = np.zeros(n)
        v[keep] = np.linalg.solve(g[np.ix_(keep, keep)], cur[keep])
        mesh = float(np.dot(share, v[len(nodes):]))
        out[key] = dict(neck_ohm=round(port["neck_ohm"], 3), collector_and_bars_ohm=round(mesh, 2),
                        total_ohm=round(mesh + port["neck_ohm"], 2), collector_width_um=round(wcol, 2), bars=len(on))
    for net in sorted({p.get("net", k) for k, p in summary["ports"].items()}):
        keys = [k for k, p in summary["ports"].items() if p.get("net", k) == net]
        if len(keys) > 1:
            out[net + " (ports in parallel)"] = dict(total_ohm=round(1 / sum(1 / out[k]["total_ohm"] for k in keys), 2))
    return out


# Drawn ring feeds as squares along each trunk's centreline (Layout/design/chip_routes.py, the partial assembly's
# trunks; Layout/design/chip_integration.py, the SAR near-pin stubs): (layer, length, width) from the pad landing bar
# to the ADC pin, and for each decap port the squares from the port to the pin. The 2 um and 1 um necks at the pins
# are the routing session's; the AVSS_analog neck is M9.
FEED_SEGMENTS = {
    "analog": {"AVDD": [("M9", 58.8, 10), ("M9", 26, 10), ("M9", 28, 6), ("M9", 2.5, 2)],
               "AVSS": [("M8", 58.8, 10), ("M8", 26, 10), ("M8", 28, 6), ("M9", 3.2, 2)]},
    "pair": {"AVDD": [("M9", 294.7, 10), ("M9", 127, 6), ("M9", 2.5, 2)],
             "AVSS": [("M8", 302.7, 10), ("M8", 187, 6), ("M8", 2.5, 2)]},
    "sar": {"AVDD": [("M9", 123.8, 10), ("M9", 72.1, 6), ("M9", 2.5, 2)],
            "AVSS": [("M8", 48.8, 10), ("M8", 101.5, 10), ("M8", 112.1, 4), ("M8", 2.5, 1)]},
}
FEED_FROM_PORT = {   # revision 2 ports: (layer, length, width) from the port to the pin
    "analog": {"AVDD": [("M9", 26, 6), ("M9", 2.5, 2)], "AVSS": [("M8", 17, 6), ("M9", 3.2, 2)]},
    "pair": {"AVDD": [("M9", 19.5, 6), ("M9", 2.5, 2)], "AVSS": [("M8", 9, 6), ("M8", 2.5, 2)]},
    "sar": {"AVDD": [("M9", 14, 6), ("M9", 27.1, 6), ("M9", 2.5, 2)],
            "AVSS": [("M8", 11, 5), ("M8", 36.1, 4), ("M8", 2.5, 1)]},
}


def ring_feed():
    """Loop resistance (AVDD plus AVSS) at 125 C with rcworst_T thickness, pad-to-pin and bulk-to-pin (from the
    nearest decap port), against the plan's 10 um M8 values (constraints.json pad_bulk_decoupling)."""
    from Layout.tools.analysis.ring_supply import rsh
    plan = json.loads((ROOT / "Layout/specs/constraints.json").read_bytes())["stage6_supply_model"][
        "pad_bulk_decoupling"]["ring_feed_at_10um_M8_ohm"]
    ohm = lambda segs: sum(rsh(layer, 125, True) * length / width for layer, length, width in segs)
    out = {}
    for b in FEED_SEGMENTS:
        pad = {n: ohm(s) for n, s in FEED_SEGMENTS[b].items()}
        bulk = {n: ohm(s) for n, s in FEED_FROM_PORT[b].items()}
        out[b] = dict(pad_to_pin_ohm=round(sum(pad.values()), 3), bulk_to_pin_ohm=round(sum(bulk.values()), 3),
                      per_rail=dict(pad_to_pin={n: round(v, 3) for n, v in pad.items()},
                                    bulk_to_pin={n: round(v, 3) for n, v in bulk.items()}),
                      plan_10um_m8=dict(pad_to_pin_ohm=plan["pad_to_pin_125C_rcworst"][b],
                                        bulk_to_pin_ohm=plan["bulk_to_pin_125C_rcworst"][b]))
    return out


def object_geometry(rev=1):
    out = {}
    for b in geo.DECAPS:
        content, s = geo.decap(b, rev)
        s["capacitance_pF"] = round(s["devices"] * NMOSCAP_F * 1e12, 1)
        s["esr_upper_bound_per_rail"] = esr_estimate(content, s)
        out[f"decap_{b}"] = s
    out["clamps"] = geo.clamps(rev)[1]
    if rev == 2:
        return out
    out["core_vss_ring"] = geo.vss_ring()[1]
    out["adc_guard_ring"] = geo.guard_ring()[1]
    return out


def chip_checks(spec):
    """DRC by rule, ERC and the flat LUP/ESD counts of one chip view from its evidence."""
    v = ev_manifest(spec["checks"])
    lv = ev_manifest(spec.get("lvs") or spec["checks"])
    lvs = lv["checks"]["lvs"]
    out = dict(drc=v["checks"]["drc"]["markers_by_rule"], markers=v["checks"]["drc"]["markers"],
               erc=lvs.get("erc_results_by_check", {}), manifest=v, lvs_manifest=lv)
    out["flat"] = obj_manifest(spec["flat"])["checks"]["drc"]["markers_by_rule"] if spec.get("flat") else {}
    return out


def variant(spec, ref_name, ref):
    """A chip view built the same way (Layout/design/chip_integration.py --view --core-view --objects-rev), by rule
    against a reference chip view: hierarchical DRC (with each marker's area), flat LUP/ESD, LVS, supply-only LVS and
    ERC. spec: view, build, checks (DRC, and LVS unless lvs is given), lvs, flat, vcs."""
    mine = chip_checks(spec)
    v, vd = mine["manifest"], mine["drc"]
    rd = ref["drc"]
    intent = json.loads((OBJ / spec["build"] / "intent.json").read_bytes())
    build = json.loads((OBJ / spec["build"] / "build.json").read_bytes())
    content = json.loads((OBJ / spec["build"] / "content.json").read_bytes())
    area = markers(EVIDENCE / spec["checks"] / "drc/DRC_RES.db")
    changed = {r: dict(variant=vd.get(r, 0), reference=rd.get(r, 0), variant_by_area=area.get(r, {}),
                       density_or_fill=density(r))
               for r in sorted(set(vd) | set(rd)) if vd.get(r, 0) != rd.get(r, 0)}
    out = dict(cellview=f"SAR_ADC_T28_LAYOUT/sar8_adc_chip/{intent['view']}", reference=ref_name, build=spec["build"],
               ok=build["ok"], replace_masters=content.get("replace_masters"),
               object_views={i["cell"]: i.get("view", "layout") for i in content.get("instances", [])},
               guarded_unchanged=not any("GUARDED_VIEW_CHANGED" in l for l in build["stdout"]),
               layout_oa_sha256=next((l.split()[0] for l in build["stdout"]
                                      if l.endswith(f"/{intent['view']}/layout.oa")), None),
               drc=dict(identity=spec["checks"], markers=mine["markers"], reference=ref["markers"],
                        non_density=sum(n for r, n in vd.items() if not density(r)),
                        reference_non_density=sum(n for r, n in rd.items() if not density(r)),
                        changed_rules=changed))
    lv_id = spec.get("lvs") or spec["checks"]
    lvs = mine["lvs_manifest"]["checks"]["lvs"]
    rep = EVIDENCE / lv_id / "lvs/lvs.rep"
    out["lvs"] = dict(identity=lv_id, verdict=lvs.get("verdict"),
                      source_sha256=mine["lvs_manifest"].get("source_netlist", {}).get("sha256"),
                      top=top_summary(rep.read_text(encoding="latin1"), "sar8_adc_chip") if rep.exists() else None)
    erc, erc_ref = mine["erc"], ref["erc"]
    out["erc"] = dict(variant=erc, total=sum(erc.values()), reference_total=sum(erc_ref.values()),
                      changed={k: [erc_ref.get(k, 0), erc.get(k, 0)] for k in set(erc) | set(erc_ref)
                               if erc.get(k, 0) != erc_ref.get(k, 0)})
    if spec.get("vcs"):
        m = obj_manifest(spec["vcs"])
        out["lvs"]["supply_only_virtual_connect"] = dict(identity=spec["vcs"], verdict=m["checks"]["lvs"].get("verdict"),
                                                         erc=m["checks"].get("erc", {}).get("results_by_check"))
    if spec.get("flat"):
        f, fr = mine["flat"], ref["flat"]
        out["flat_lup_esd"] = dict(identity=spec["flat"], variant=f, reference=fr,
                                   changed={r: [fr.get(r, 0), f.get(r, 0)] for r in set(f) | set(fr)
                                            if f.get(r, 0) != fr.get(r, 0)})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chip-build", default="chip-full-b2")
    ap.add_argument("--chip-checks", required=True)
    ap.add_argument("--partial", default="chip-asm-a3-chk")
    ap.add_argument("--ring-baseline", default="chip-base-ring-drc")
    ap.add_argument("--core-baseline", default="chip-base-core-drc")
    ap.add_argument("--timing", default="Layout/results/output_register_timing.json")
    ap.add_argument("--out", default="Layout/results/chip_objects.json")
    ap.add_argument("--hcell-lvs", help="chip LVS with the decaps and the register as HCELLs too (chip_assembly run)")
    ap.add_argument("--supply-vc-lvs", help="chip LVS joining only the supply nets by name (chip_objects run)")
    ap.add_argument("--flat-full", help="flat LUP/ESD DRC of layout_full (chip_objects run)")
    ap.add_argument("--flat-partial", help="flat LUP/ESD DRC of the partial assembly (chip_objects run)")
    ap.add_argument("--variant", nargs=7, action="append", default=[],
                    metavar=("VIEW", "BUILD", "DRC", "LVS", "FLAT", "VCS", "REFERENCE"),
                    help="another chip view built the same way, compared by rule against REFERENCE (layout_full or an "
                         "earlier --variant view)")
    ap.add_argument("--objects-rev2", action="store_true", help="record the layout_r2 object cells (grown pad decaps)")
    a = ap.parse_args()
    chip = ev_manifest(a.chip_checks)
    part = ev_manifest(a.partial)
    ring = ev_manifest(a.ring_baseline)["checks"]["drc"]["markers_by_rule"]
    core = ev_manifest(a.core_baseline)["checks"]["drc"]["markers_by_rule"]
    full = chip["checks"]["drc"]["markers_by_rule"]
    prev = part["checks"]["drc"]["markers_by_rule"]
    area = markers(EVIDENCE / a.chip_checks / "drc/DRC_RES.db")
    rules = sorted(set(full) | set(prev))
    by_rule = {r: dict(chip_full=full.get(r, 0), chip_partial=prev.get(r, 0), ring_alone=ring.get(r, 0),
                       core_alone=core.get(r, 0), chip_full_by_area=area.get(r, {}), density_or_fill=density(r))
               for r in rules}
    new = {r: v for r, v in by_rule.items() if v["chip_full"] > v["chip_partial"] and not v["density_or_fill"]}
    gone = {r: v for r, v in by_rule.items() if v["chip_full"] < v["chip_partial"] and not v["density_or_fill"]}
    lvs = chip["checks"]["lvs"]
    rep = EVIDENCE / a.chip_checks / "lvs/lvs.rep"
    erc_full = lvs.get("erc_results_by_check", {})
    erc_part = part["checks"]["lvs"].get("erc_results_by_check", {})
    ringv = json.loads((ROOT / "Layout/results/io_ring_verification.json").read_bytes())["erc"]
    build = json.loads((OBJ / a.chip_build / "build.json").read_bytes())
    routes = json.loads((OBJ / a.chip_build / "routes.json").read_bytes())
    timing = json.loads((ROOT / a.timing).read_bytes()) if (ROOT / a.timing).exists() else None
    record = dict(
        schema_version=1, date=datetime.date.today().isoformat(), tool="Layout/tools/analysis/chip_objects_record.py",
        issue="chenzc24/sar-adc-t28#12, #18",
        objects=objects(), geometry=object_geometry(),
        output_register=dict(source="design/chip/output_register.scs", clocking="CP of every DFQD1 on SAMPLE_CORE "
                             "directly (no clock buffer), DEL250D1 on each D for hold (user decision 2026-11-22)",
                             route=json.loads((ROOT / "work/layout/output-register/r1/route.json").read_bytes()),
                             convert=json.loads((ROOT / "work/layout/output-register/r1/convert.json").read_bytes()),
                             timing=timing),
        integration=dict(cellview="SAR_ADC_T28_LAYOUT/sar8_adc_chip/layout_full", copied_from="sar8_adc_chip/layout",
                         build=a.chip_build, ok=build["ok"],
                         guarded_unchanged=not any("GUARDED_VIEW_CHANGED" in l for l in build["stdout"]),
                         layout_oa_sha256=next((l.split()[0] for l in build["stdout"] if l.endswith("/layout_full/layout.oa")), None),
                         routes=routes),
        drc=dict(deck="drc_rule_T28_chip (installed chip deck: FULL_CHIP and WITH_SEALRING)", identity=a.chip_checks,
                 markers=dict(chip_full=chip["checks"]["drc"]["markers"], chip_partial=part["checks"]["drc"]["markers"],
                              ring_alone=sum(ring.values()), core_alone=sum(core.values())),
                 by_rule=by_rule, new_non_fill_rules=new, removed_non_fill_rules=gone),
        lvs=dict(identity=a.chip_checks, verdict=lvs.get("verdict"), cells=lvs.get("cells"),
                 top=top_summary(rep.read_text(encoding="latin1"), "sar8_adc_chip") if rep.exists() else None,
                 source="Layout/design/chip_full_source.py on the partial assembly's source",
                 source_sha256=chip.get("source_netlist", {}).get("sha256")),
        erc=dict(chip_full=erc_full, chip_full_total=sum(erc_full.values()), chip_partial=erc_part,
                 chip_partial_total=sum(erc_part.values()), ring_cell=ringv["this_ring"]["counts"],
                 ring_cell_total=ringv["this_ring"]["total"], ring_name_probe=ringv["name_probe"]["counts"]),
        evidence=dict(host="thu-wei", chip_build=a.chip_build, chip_checks=a.chip_checks, partial=a.partial,
                      ring_baseline=a.ring_baseline, core_baseline=a.core_baseline),
    )
    if a.hcell_lvs:
        m = ev_manifest(a.hcell_lvs)["checks"]["lvs"]
        record["lvs"]["with_object_hcells"] = dict(identity=a.hcell_lvs, verdict=m.get("verdict"),
                                                   hcells_added=["sar8_out_reg", "sar8_decap_analog", "sar8_decap_pair",
                                                                 "sar8_decap_sar", "sar8_decap_dvdd"])
    if a.supply_vc_lvs:
        m = obj_manifest(a.supply_vc_lvs)
        record["lvs"]["supply_only_virtual_connect"] = dict(
            identity=a.supply_vc_lvs, verdict=m["checks"]["lvs"].get("verdict"),
            virtual_connect_name=m["decks"]["lvs"].get("virtual_connect_name"),
            erc=m["checks"].get("erc", {}).get("results_by_check"),
            meaning="Only the supply nets are joined by name, so ADC_D0-7, D0_CORE-D7_CORE and SAMPLE_CORE (CK) must "
                    "be physically connected for CORRECT")
    if a.flat_full and a.flat_partial:
        f, p = obj_manifest(a.flat_full), obj_manifest(a.flat_partial)
        record["drc"]["flat_lup_esd"] = dict(
            why="Hierarchical chip DRC under-reports net-based rules such as LUP.5.2.x (found by the partial assembly's "
                "session); the chip deck run flat with only the LUP.* and ESD.* rule checks selected",
            identity=dict(chip_full=a.flat_full, chip_partial=a.flat_partial),
            selected=len(f["decks"]["drc"]["selected"]), dropped_inactive=f["decks"]["drc"].get("dropped_inactive"),
            chip_full=f["checks"]["drc"]["markers_by_rule"], chip_partial=p["checks"]["drc"]["markers_by_rule"])
        record["evidence"].update(flat_full=a.flat_full, flat_partial=a.flat_partial)
    record["evidence"].update(hcell_lvs=a.hcell_lvs, supply_vc_lvs=a.supply_vc_lvs)
    refs = {"layout_full": dict(drc=full, markers=chip["checks"]["drc"]["markers"], erc=erc_full,
                                flat=record["drc"].get("flat_lup_esd", {}).get("chip_full", {}))}
    record["variants"] = {}
    for view, build_id, checks, lvs_id, flat, vcs, reference in a.variant:
        spec = dict(view=view, build=build_id, checks=checks, lvs=lvs_id, flat=flat, vcs=vcs)
        record["variants"][view] = variant(spec, reference, refs[reference])
        refs[view] = {k: v for k, v in chip_checks(spec).items() if not k.endswith("manifest")}
        record["evidence"]["variant_" + view] = spec
    if a.objects_rev2:
        record["objects_r2"] = objects(OBJECT_CELLS_R2)
        record["geometry_r2"] = object_geometry(2)
        record["ring_feed_r2"] = ring_feed()
    write_json(ROOT / a.out, record)
    print(json.dumps(dict(drc=record["drc"]["markers"], new=list(new), gone=list(gone), lvs=record["lvs"]["verdict"],
                          erc=record["erc"]["chip_full_total"]), indent=1))


if __name__ == "__main__":
    main()
