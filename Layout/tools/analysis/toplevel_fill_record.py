"""Record of the Stage 5 core fill (chenzc24/sar-adc-t28#12): Layout/results/toplevel_fill.json.

Collects the pair refill (blocks, DRC/LVS, TOP fixed load, standalone weights against the frozen stream), the
Bootstrap and core passes, the geometric checks of the fill hierarchy, the OA build, the density DRC of the filled
wrapper against the routed baseline, and the coupled extraction of the filled wrapper against the unfilled routed
core with the same labels and deck (TOP totals and fixed load, the comparator handshake loads, TOP coupling to fill).

  python -m Layout.tools.analysis.toplevel_fill_record
"""
import argparse
import json
from pathlib import Path

from Layout.design import toplevel_fill as tf
from Layout.project import ROOT, write_json
from Layout.tools.analysis.toplevel_route_parasitics import Extraction

RUNS = ROOT / "work/output/managed_execution/runs"
PAIR_PEX = ROOT / "work/layout/reference-driver/pex"
# Revision 2 fills the final routed view layout_route_guard (layout_route_full plus the SAR P+ guard ring).
EVIDENCE = dict(pair_fill="se-xref-peripheral-routed-fill", pair="se-xref-peripheral-routed",
                frozen_pair="se-xref-peripheral-dense", boot="adc-core-fill2-boot", core="adc-core-fill2-core",
                library="adc-core-fill2-lib", build="adc-core-fill2-build", oa_checks="adc-core-fill2-oa-chk",
                checks="adc-core-fill2-chk", baseline_checks="adc-core-guard-g1-chk",
                baseline_pex="adc-core-fill2-base-xtr", route_full_pex="adc-core-full-p2h-xtr-raw")
CORE_VIEW = "layout_route_guard"
# Revision 1 on layout_route_full: built in OA as sar8_adc_core_filled/layout_fill1; kept as a cross-check.
REVISION1 = dict(boot="adc-core-fill1-boot", core="adc-core-fill1-core-b", core_with_tcd="adc-core-fill1-core",
                 library="adc-core-fill1-libb", build="adc-core-fill1-build", checks="adc-core-fill1-chk",
                 baseline_checks="adc-core-full-p2h-chk")
GAIN = dict(refilled="xref-routedfill-tt-gain-a", frozen="xref-fill-tt-after-dense")
FIXED_PAIR = ("0", "VDD", "VSS", "VREFP", "VREFN")
FIXED_CORE = ("0", "VDD!", "VREFP", "VREFN", "VREFP_TRUNK", "VREFN_TRUNK")
HANDSHAKE = {"COMP_P": 11.4, "COMP_N": 11.4, "CMP_CLK": 11.1}
# Route loads of layout_route_full (Layout/results/toplevel_route_full.json, labelled-piece method, unfilled).
ROUTE_LOAD_UNFILLED = {"COMP_P": 5.04, "COMP_N": 5.15, "CMP_CLK": 5.03}
LIMITS = dict(top_fixed_per_side_fF=57.0, top_imbalance_fF=1.0, top_route_allowance_fF=9.8, gain_error=0.047,
              linearity_lsb=0.25)


def fF(v):
    return round(v * 1e15, 4)


def manifest(identity, name="manifest.json"):
    path = tf.WORK / "evidence" / identity / name
    if not path.exists():
        tf.fetch(identity, [name])
    return json.loads(path.read_text())


def pair_load(identity):
    c = Extraction(str(PAIR_PEX / identity / "pex"), top=tf.PAIR).capacitance()
    out = {}
    for n in ("TOPP", "TOPN"):
        parts = {k: fF(c[n].get(k, 0.0)) for k in FIXED_PAIR}
        out[n] = dict(fixed_fF=round(sum(parts.values()), 4), components_fF=parts, total_fF=fF(sum(c[n].values())))
    out["imbalance_fF"] = round(abs(out["TOPP"]["fixed_fF"] - out["TOPN"]["fixed_fF"]), 4)
    return out


def weights(run):
    data = json.loads((RUNS / run / "collected/derived/result.json").read_text())
    return dict(run=run, gain_ratio=data["gain_ratio"], gain_error_percent=round(100 * data["gain_error"], 4),
                dnl_lsb=round(data["dnl_abs_max"], 4), inl_lsb=round(data["inl_abs_max"], 4),
                stable=data["all_plateaus_stable"], failures=data["failures"],
                effective_weights_v=data["post"]["metrics"]["effective_weights_v"])


def drc(identity):
    m = manifest(identity)
    return dict(markers=m["checks"]["drc"]["markers"], markers_by_rule=m["checks"]["drc"]["markers_by_rule"])


def core_pex(identity, top):
    folder = tf.WORK / "evidence" / identity / "pex"
    names = ("extracted.scs", "extracted.scs.pex", f"extracted.scs.{top}.pxi")
    if not all((folder / n).exists() for n in names):
        tf.fetch(identity, ["pex/" + n for n in names])
    return Extraction(str(folder), top=top)


def core_parasitics():
    filled = core_pex(EVIDENCE["checks"], tf.WRAPPER)
    unfilled = core_pex(EVIDENCE["baseline_pex"], tf.CORE)
    full = core_pex(EVIDENCE["route_full_pex"], tf.CORE)
    cf, cu, cr = filled.capacitance(), unfilled.capacitance(), full.capacitance()
    # The deck merges dummy metal into each conductor layer (metal<n>i = M<n>i OR DUM<n>) and the floating fill adds
    # no net: its coupling appears as capacitance to ground. Block-internal names differ by the wrapper's instance
    # prefix, and unnamed nets are renumbered, so the partner split compares ground and the routed nets only.
    out = dict(files=dict(filled=filled.files, unfilled=unfilled.files, layout_route_full=full.files), nets={},
               fill_model="Dummy metal is part of each conductor layer; floating fill extracts to ground")
    for n in ("TOPN", "TOPP", "COMP_P", "COMP_N", "CMP_CLK", "SEQ_SAMPLE", "VINN", "VINP"):
        tot_f, tot_u = sum(cf[n].values()), sum(cu[n].values())
        out["nets"][n] = dict(filled_total_fF=fF(tot_f), unfilled_total_fF=fF(tot_u), change_fF=fF(tot_f - tot_u),
                              to_ground_change_fF=fF(cf[n].get("0", 0.0) - cu[n].get("0", 0.0)),
                              route_full_unfilled_total_fF=fF(sum(cr[n].values())),
                              ring_change_fF=fF(tot_u - sum(cr[n].values())))
    for n in ("TOPN", "TOPP"):
        fixed = {k: fF(cf[n].get(k, 0.0)) for k in FIXED_CORE}
        fixed_u = {k: fF(cu[n].get(k, 0.0)) for k in FIXED_CORE}
        out["nets"][n].update(fixed_filled_fF=round(sum(fixed.values()), 4), fixed_unfilled_fF=round(sum(fixed_u.values()), 4),
                              fixed_components_filled_fF=fixed, fixed_components_unfilled_fF=fixed_u)
    t = out["nets"]
    out["top"] = dict(total_difference_filled_fF=round(abs(t["TOPN"]["filled_total_fF"] - t["TOPP"]["filled_total_fF"]), 4),
                      total_difference_unfilled_fF=round(abs(t["TOPN"]["unfilled_total_fF"] - t["TOPP"]["unfilled_total_fF"]), 4),
                      fixed_difference_filled_fF=round(abs(t["TOPN"]["fixed_filled_fF"] - t["TOPP"]["fixed_filled_fF"]), 4),
                      fixed_change_fF={n: round(t[n]["fixed_filled_fF"] - t[n]["fixed_unfilled_fF"], 4) for n in ("TOPN", "TOPP")})
    load = {n: ROUTE_LOAD_UNFILLED[n] + t[n]["ring_change_fF"] + t[n]["change_fF"] for n in HANDSHAKE}
    out["handshake"] = {n: dict(route_load_layout_route_full_fF=ROUTE_LOAD_UNFILLED[n], ring_change_fF=t[n]["ring_change_fF"],
                                fill_change_fF=t[n]["change_fF"], route_load_filled_fF=round(load[n], 3),
                                limit_fF=HANDSHAKE[n], pass_=load[n] <= HANDSHAKE[n]) for n in HANDSHAKE}
    return out


def build_record():
    W = tf.WORK
    pair_seed = json.loads((W / EVIDENCE["pair_fill"] / "seed.json").read_text())
    boot_seed = json.loads((W / EVIDENCE["boot"] / "seed.json").read_text())
    tf.use_revision(2)
    core_seed = json.loads((W / EVIDENCE["core"] / "seed.json").read_text())
    library = json.loads((W / EVIDENCE["library"] / "library.json").read_text())
    verify = json.loads((W / EVIDENCE["library"] / "verify.json").read_text())
    build1 = json.loads((W / REVISION1["build"] / "build.json").read_text())
    build2_path = W / "adc-core-fill2-build" / "build.json"
    build2 = json.loads(build2_path.read_text()) if build2_path.exists() else None
    wrapper = json.loads((W / EVIDENCE["checks"] / "wrapper.json").read_text())
    oa_stream = None
    if build2 and build2.get("ok"):
        oc = manifest(EVIDENCE["oa_checks"])
        # Compared shape by shape (gdstk) with the assembly that was checked and extracted: every layer and text equal.
        oa_stream = dict(layout_oa_sha256=oc["source"]["layout_oa_sha256"], gds_sha256=oc["gds"]["sha256"],
                         drc=oc["checks"]["drc"]["markers_by_rule"], matches_checked_assembly=True)
    conflicts = json.loads((W / "pair_fill_conflicts.json").read_text())
    pm = json.loads((PAIR_PEX / EVIDENCE["pair"] / "manifest.json").read_text())
    fills = {k: manifest(EVIDENCE[k], "fill_manifest.json") for k in ("pair_fill", "boot", "core")}
    fills1 = {k: manifest(REVISION1[k], "fill_manifest.json") for k in ("boot", "core", "core_with_tcd")}
    chk1, base1 = manifest(REVISION1["checks"]), manifest(REVISION1["baseline_checks"])
    chk = manifest(EVIDENCE["checks"])
    base = manifest(EVIDENCE["baseline_checks"])
    load = {k: pair_load(EVIDENCE[k]) for k in ("pair", "frozen_pair")}
    gain = {k: weights(v) for k, v in GAIN.items()}
    filled_rules, base_rules = chk["checks"]["drc"]["markers_by_rule"], base["checks"]["drc"]["markers_by_rule"]
    parasitics = core_parasitics()
    top = parasitics["nets"]
    record = dict(
        stage="Stage 5 of chenzc24/sar-adc-t28#12: fill of the routed ADC core by owner (Layout/specs/fill-policy.md)",
        date="2026-11-22",
        evidence=EVIDENCE, weight_runs=GAIN,
        core=dict(view=f"{tf.CORE}/{CORE_VIEW}", layout_oa_sha256=base["source"]["layout_oa_sha256"],
                  stream_sha256=base["gds"]["sha256"]),
        pair=dict(
            seed=tf.PAIR_SEED, seed_gds_sha256=pair_seed["seed"]["sha256"], blocked_seed_gds_sha256=pair_seed["seed_gds_sha256"],
            context_polygons=pair_seed["context_polygons"], entry_blocks_by_layer=pair_seed["entry_blocks_by_layer"],
            entry_margin_um=pair_seed["entry_margin_um"], bounds_native_um=pair_seed["bounds_native_um"],
            fill_jobs={k: dict(job_sha256=v["job_sha256"], gds_sha256=v["gds_sha256"])
                       for k, v in fills["pair_fill"]["steps"].items()},
            stream_gds_sha256=pm["gds"]["sha256"], lvs=pm["checks"]["lvs"]["verdict"], drc=pm["checks"]["drc"],
            pex_sha256=pm["checks"]["pex"]["sha256"], functional_sha256=pm["comparison_functional_sha256"],
            overlap_with_routed_core=dict(frozen=conflicts[EVIDENCE["frozen_pair"]], refilled=conflicts[EVIDENCE["pair"]]),
            top_load=load, weights=gain,
            pass_=bool(max(load["pair"]["TOPP"]["fixed_fF"], load["pair"]["TOPN"]["fixed_fF"]) <= LIMITS["top_fixed_per_side_fF"]
                       and load["pair"]["imbalance_fF"] <= LIMITS["top_imbalance_fF"]
                       and gain["refilled"]["gain_error_percent"] <= 100 * LIMITS["gain_error"]
                       and max(gain["refilled"]["dnl_lsb"], gain["refilled"]["inl_lsb"]) <= LIMITS["linearity_lsb"]
                       and gain["refilled"]["stable"] and not gain["refilled"]["failures"])),
        bootstrap=dict(bounds_core_um=boot_seed["bounds_core_um"], mirrored_from_um=boot_seed["mirrored_from_um"],
                       placement=boot_seed["placement"], dummy_tcd_inserted=False,
                       fill_jobs={k: dict(job_sha256=v["job_sha256"], gds_sha256=v["gds_sha256"])
                                  for k, v in fills["boot"]["steps"].items()}),
        core_pass=dict(bounds_core_um=core_seed["bounds_core_um"], exclusions=core_seed["exclusions"],
                       dummy_tcd=fills["core"].get("dummy_tcd"),
                       fill_jobs={k: dict(job_sha256=v["job_sha256"], gds_sha256=v["gds_sha256"])
                                  for k, v in fills["core"]["steps"].items()},
                       with_tcd_superseded=dict(evidence=REVISION1["core_with_tcd"],
                                                reason="The utility's default dummy TCD put one TCD_H (drawn OD/PO/NW) at "
                                                       "x 11.7-20.7, y 68.4-71.9, beside the CDAC array's TOPN half")),
        fill_hierarchy=dict(top=library["top"], masters=library["masters"], cells=library["cells"],
                            gds_sha256=library["library_gds_sha256"], area_um2_by_layer=library["area_um2_by_layer"]),
        verification=verify,
        oa=dict(revision2=dict(wrapper=f"{tf.WRAPPER}/layout_fill2", core=f"{tf.CORE}/{CORE_VIEW}", fill=f"{tf.FILL_TOP}/layout",
                               built=bool(build2 and build2.get("ok")), build=build2,
                               checked_stream=dict(source="GDS assembly of the guard stream, the fill library and the wrapper texts "
                                                          "(toplevel_fill wrapper-gds)", **wrapper),
                               assembly_matches_oa_stream_in_revision1=True,
                               oa_stream=dict(evidence=EVIDENCE["oa_checks"], **oa_stream) if oa_stream else None),
                revision1=dict(wrapper=build1["wrapper"], core=f"{tf.CORE}/{build1['core_view']}", fill="sar8_adc_core_fill1/layout",
                               build_stdout=build1["stdout"], stream_gds_sha256=chk1["gds"]["sha256"],
                               stream_layout_oa_sha256=chk1["source"].get("layout_oa_sha256"),
                               drc=chk1["checks"]["drc"]["markers_by_rule"],
                               baseline_drc=base1["checks"]["drc"]["markers_by_rule"],
                               core_jobs={k: v["job_sha256"] for k, v in fills1["core"]["steps"].items()},
                               boot_fill_identical_to_revision2=True)),
        drc=dict(filled=dict(markers=chk["checks"]["drc"]["markers"], markers_by_rule=filled_rules),
                 routed_baseline=dict(markers=base["checks"]["drc"]["markers"], markers_by_rule=base_rules),
                 closed=sorted(set(base_rules) - set(filled_rules)),
                 remaining={k: v for k, v in filled_rules.items()},
                 new=sorted(set(filled_rules) - set(base_rules))),
        extraction=parasitics,
        limits=LIMITS,
        stage5_top=dict(
            pair_fixed_fF={n: load["pair"][n]["fixed_fF"] for n in ("TOPP", "TOPN")},
            pair_imbalance_fF=load["pair"]["imbalance_fF"],
            core_total_fF={n: top[n]["filled_total_fF"] for n in ("TOPN", "TOPP")},
            core_total_difference_fF=parasitics["top"]["total_difference_filled_fF"],
            core_fixed_fF={n: top[n]["fixed_filled_fF"] for n in ("TOPN", "TOPP")},
            core_fixed_difference_fF=parasitics["top"]["fixed_difference_filled_fF"],
            fill_change_total_fF={n: top[n]["change_fF"] for n in ("TOPN", "TOPP")},
            fill_change_to_ground_fF={n: top[n]["to_ground_change_fF"] for n in ("TOPN", "TOPP")}))
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="Layout/results/toplevel_fill.json")
    args = ap.parse_args()
    record = build_record()
    write_json(ROOT / args.out, record)
    print(json.dumps(dict(pair=dict(load=record["pair"]["top_load"]["pair"], weights={k: {x: v[x] for x in (
        "gain_ratio", "gain_error_percent", "dnl_lsb", "inl_lsb")} for k, v in record["pair"]["weights"].items()},
        pass_=record["pair"]["pass_"]), drc=record["drc"], stage5_top=record["stage5_top"],
        handshake=record["extraction"]["handshake"]), indent=1))


if __name__ == "__main__":
    main()
