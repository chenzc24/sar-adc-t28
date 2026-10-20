"""Same full-rate acceptance checks, bound to fresh saved-OA R3 runs."""
from __future__ import annotations
import argparse
import hashlib
import json

import reference_edge_slew_analyze as checks
from join_r3 import ROOT,OUT,TOP,TB,VAS,dump,r1
from join_r3_sim import POINTS
from freeze_r0 import object_digest,schematic_surface


def candidate_rows():
    m=r1.read_json(ROOT/"verification/integration/reference_edge_slew_results.json")
    return {r["point"]:r for r in m["cases"] if r["edge_ps"]==50}


def metrics_vector(row):
    m=row["metrics"]
    return dict(reference_max_v=m["reference_stress"]["value_v"],
        comparator_max_v=m["comparator_stress_from_saved_internal_nodes"]["value_v"],
        max_compare_error_mv=max(f["max_compare_error_mv"] for f in m["frames"]),
        held_error_mv=row["max_abs_held_error_mv"],
        first_compare_error_mv=row["max_abs_pre_first_compare_error_mv"],
        N3_VGD_max_v=row["N3"]["VGD_max_v"])


def analyze(name):
    checks.OUT=OUT;checks.dump=dump
    row=checks.analyze(name)
    prior=candidate_rows()[name]
    assert r1.sha(ROOT/prior["source_folder"]/f"runs/{prior['source_case']}_waveform.json")==prior["waveform_sha256"]
    a,b=metrics_vector(row),metrics_vector(prior)
    row["delta_from_tested_50ps_candidate"]={k:a[k]-b[k] for k in a}
    # R3 changes the top name/parameter ordering only, not electrical conditions.
    row["matches_prior_candidate_within_tolerance"]=all(
        abs(d)<(1e-5 if k.endswith("_v") else .01)
        for k,d in row["delta_from_tested_50ps_candidate"].items())
    assert row["bounded_case_pass"] and row["matches_prior_candidate_within_tolerance"],row["delta_from_tested_50ps_candidate"]
    dump(f"comparison/{name}.json",row)
    print("R3_VS_CANDIDATE",name,row["delta_from_tested_50ps_candidate"],flush=True)
    return row


def figures():
    import matplotlib.pyplot as plt
    import numpy as np
    figdir=ROOT/"docs/figures/sar8_join_r3";figdir.mkdir(parents=True,exist_ok=True)
    fresh=r1.read_json(OUT/"snippets/pfull.json")
    old=r1.read_json(ROOT/"output/sar8_reference_edge_slew/snippets/pfull_e50ps.json")
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
    for s,label,color,style in ((fresh,"Saved OA R3","#2676aa","-"),
                                (old,"Previous 50 ps candidate","#cc7538","--")):
        t=np.asarray(s["time_ns"]);bn=np.asarray(s["xdut.xcdac.bn3"])
        axes[0].plot(t,1e3*bn,style,color=color,label=label)
        axes[1].plot(t,np.asarray(s["xdut.gnp3"])-bn,style,color=color,label=label)
    axes[0].axhline(0,color=".4",ls=":",label="Nominal low reference")
    axes[0].set_ylabel("N3 bottom (mV)")
    axes[1].axhline(.99,color="#98517e",ls="-.",label="Model screen = 0.99 V")
    axes[1].set_ylabel("N3 PMOS VGD (V)")
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2)
    axes[-1].set_xlim(101.12,101.55);axes[-1].set_xlabel("Time (ns)")
    axes[0].set_title("+0.8 V both frames; 0.1 ns restore / 50 ps reference gates",fontsize=11)
    fig.tight_layout();fig.savefig(figdir/"saved_OA_restore_confirmation.png",dpi=160);plt.close(fig)


def curate():
    rows=[r1.read_json(OUT/f"comparison/{p}.json") for p in POINTS]
    paths=[ROOT/"config/sar8_join_r3.yaml",*VAS.values()]+[
        ROOT/f"scripts/integration/{s}.py" for s in ("join_r3","join_r3_sim","join_r3_analyze")]
    m=dict(baseline_id="SAR8_JOIN_R3_RESTORE_100PS_EDGE_50PS",role="active_development_baseline",
        qualified=False,frozen_circuit=False,library="SAR_ADC_T28",top=TOP,testbench=TB,
        source_text_LF_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest() for p in paths},
        prior_candidate_manifest_sha256=r1.sha(ROOT/"verification/integration/reference_edge_slew_results.json"),
        exact_gate_VA_sha256={n:r1.sha(p) for n,p in VAS.items()},
        timing=dict(restore_guard_ps=100,gate_edge_ps=50,BBM_ps=100,commit_stable_ps=200),
        saved_OA_readback_audit=r1.read_json(OUT/"saved_OA_readback_audit.json"),
        OA_surface_sha256={n:object_digest(schematic_surface(r1.read_json(OUT/f"oa/{n}.json"))) for n in (TOP,TB)},
        exact_saved_OA_export_audit=r1.read_json(OUT/"exports/primary/audit.json"),
        final_saved_OA_export_audit=r1.read_json(OUT/"exports/final/audit.json"),
        shared_CDF_before=r1.read_json(OUT/"cdf_before.json"),shared_CDF_after=r1.read_json(OUT/"cdf_after.json"),
        cases=rows,simulator="Spectre21.1 APS TT/0.9V/27C 200ns maxstep10ps full-rate",
        exclusions=["PVT","noise","mismatch","full-code/FFT","physical reference timing driver",
                    "all-bootstrap-internal stress","layout/lifetime signoff"])
    for key,file in (("OA_preflight","preflight.json"),("OA_postflight","preflight_after.json")):
        raw=r1.read_json(OUT/file);m[key]={k:raw[k] for k in
            ("library","frozen_cells_matched","R2_original_2ns_20ps_readback_verified") if k in raw}
    m["all_four_fresh_cases_pass"]=all(r["bounded_case_pass"] and r["matches_prior_candidate_within_tolerance"] for r in rows)
    assert m["all_four_fresh_cases_pass"]
    target=ROOT/"verification/integration/join_r3_results.json"
    target.write_text(json.dumps(m,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    figures()


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="*");ap.add_argument("--curate",action="store_true")
    a=ap.parse_args()
    for name in a.names:analyze(name)
    if a.curate:curate()
