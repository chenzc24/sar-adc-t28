"""Analyze exact-OA R2 runs and compare the tested timing-only experiment."""
from __future__ import annotations
import argparse
import hashlib
import json

import join_r1_analyze as native
import reference_alignment_analyze as timing
from join_r2 import ROOT,OUT,VAS,TOP,TB,GATE,COMMIT,dump,r1
from freeze_r0 import object_digest,schematic_surface


def analyze(name):
    native.OUT=OUT;native.dump=dump
    entry=native.analyze(name,plot=False)
    assert entry["result_ok"],entry
    wave=timing.load_wave(OUT/f"runs/{name}_waveform.json")
    phase=timing.phase_stress(wave);handoffs=timing.handoffs(wave)
    old=r1.read_json(ROOT/"verification/integration/reference_alignment_results.json")
    prior=next(c for c in old["cases"] if c["name"]==name+"_a200")
    # Prior curated waveform hash binds comparison to the actual tested run.
    assert r1.sha(ROOT/f"output/sar8_reference_alignment/runs/{name}_a200_waveform.json")==prior["waveform_sha256"]
    maxerr=max(f["max_compare_error_mv"] for f in entry["frames"])
    olderr=max(f["max_compare_error_mv"] for f in prior["aligned"]["frames"])
    deltas=dict(max_compare_error_mv=maxerr-olderr)
    for p in ("conversion","second_acquisition"):
        for metric in ("reference_max_v","comparator_max_v"):
            deltas[p+"_"+metric]=phase[p][metric]-prior["phase_stress"][p][metric]
    row=dict(name=name,context=entry["context"],metrics=timing.summary(entry),phase_stress=phase,
             handoffs=handoffs,prior_alignment_deltas=deltas,
             waveform_sha256=r1.sha(OUT/f"runs/{name}_waveform.json"),
             exact_saved_OA_export_sha256=entry["export_sha256"])
    dump(f"comparison/{name}.json",row)
    print("R2",name,"functional",all(f["frame_pass"] for f in entry["frames"]),
          "convert_ref",phase["conversion"]["reference_max_v"],
          "convert_comp",phase["conversion"]["comparator_max_v"],
          "restore_comp",phase["second_acquisition"]["comparator_max_v"],
          "SOA",entry["bounded_join_pass"],"delta",deltas,flush=True)
    return row


def curate(names):
    text_sha=lambda p:hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()
    paths=[ROOT/"config/sar8_join_r2.yaml",*VAS.values()]+[
        ROOT/f"scripts/integration/{s}.py" for s in ("join_r2","join_r2_sim","join_r2_analyze")]
    manifest=dict(baseline_id="SAR8_JOIN_R2_ALIGNED_IDEAL_REFERENCE_GATES",
        role="active_development_baseline",qualified=False,frozen_circuit=False,
        library="SAR_ADC_T28",top=TOP,testbench=TB,
        source_text_LF_sha256={p.relative_to(ROOT).as_posix():text_sha(p) for p in paths},
        exact_gate_VA_sha256={name:r1.sha(p) for name,p in VAS.items()},
        OA_preflight=r1.read_json(OUT/"preflight.json"),
        OA_postflight=r1.read_json(OUT/"preflight_after.json"),
        OA_surface_sha256={name:object_digest(schematic_surface(r1.read_json(OUT/f"oa/{name}.json"))) for name in (TOP,TB)},
        exact_saved_OA_export_audit=r1.read_json(OUT/"exports/primary/audit.json"),
        simulator="Spectre21.1 APS TT/.9V/27C 200ns maxstep10ps full-rate",
        cases=[r1.read_json(OUT/f"comparison/{n}.json") for n in names],
        known_failure="negative-full acquisition midpoint restore comparator overvoltage",
        exclusions=["transistor timing synchronizer","PVT","noise","mismatch","full-code or FFT qualification","layout/lifetime"])
    # Keep private environment details in ignored preflight logs, not the
    # tracked summary. The library/technology binding and matched count suffice.
    for key in ("OA_preflight","OA_postflight"):
        manifest[key]={k:manifest[key][k] for k in ("library","frozen_cells_matched")}
    target=ROOT/"verification/integration/join_r2_results.json"
    target.write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("names",nargs="+")
    ap.add_argument("--curate",action="store_true")
    ap.add_argument("--curate-only",action="store_true",help="Summarize already analyzed cases")
    args=ap.parse_args()
    if not args.curate_only:
        for name in args.names:analyze(name)
    if args.curate or args.curate_only:curate(args.names)
