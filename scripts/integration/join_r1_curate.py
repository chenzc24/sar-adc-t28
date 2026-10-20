"""Curate reproducible hashes/metrics without raw netlists, PDK models or OA."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from join_r1 import ROOT, OUT, VA, TOP, TB, ARRAY, GATE, objects, read_json, sha, object_digest
from freeze_r0 import check as check_r0, schematic_surface

CASES=["control","nfull","pfull","nhalf","phalf","small","carry_up","carry_down","full_reverse",
       "nfull_fine","nhalf_fine"]


def text_sha(path):
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").replace("\r\n","\n").encode()).hexdigest()


def main():
    check_r0()
    target=ROOT/"verification/integration/join_r1_results.json"
    assert not target.exists(),"Published evidence is immutable; use a new revision"
    audit=read_json(OUT/"exports/primary/audit.json")
    assert audit["export_sha256"]==sha(OUT/"exports/primary/input.scs")
    assert (OUT/"postflight_final.log").read_text().strip().endswith("PREFLIGHT_MATCH_23_UNCHANGED")
    assert sha(OUT/"gate_final_readback.va")==sha(VA)
    for obj in objects():
        assert not read_json(OUT/f"oa/{obj.name}_markers.json"),obj.name
    frozen=read_json(ROOT/"verification/integration/join_r0_sources.json")
    for name,entry in frozen["live_readback"]["cells"].items():
        assert object_digest(schematic_surface(read_json(OUT/f"dependencies_after/{name}.json")))==entry["surface_sha256"]
    cases=[]
    for name in CASES:
        a=read_json(OUT/f"analysis/{name}.json")
        assert a["result_ok"]
        ctx=read_json(OUT/f"cases/{name}.json")
        run=read_json(OUT/f"runs/{name}_result.json")
        assert run["ok"] and sha(OUT/f"decks/{name}.scs")==a["deck_sha256"]==run["deck_sha256"]
        cases.append({k:a[k] for k in ("name","result_ok","frames","reference_stress",
            "minimum_opposite_rail_deadtime_ps","simultaneous_gate_enable_banks","raw_both_on_banks",
            "CMI_warning_count","warning_codes","suppression_or_LTE_lines",
            "comparator_stress_from_saved_internal_nodes","top_node_ranges","bounded_join_pass",
            "deck_sha256","export_sha256")} | dict(point=ctx["point"],maxstep_ps=ctx["maxstep_ps"],
                output_strobe_ps=ctx.get("output_strobe_ps",0),
                gate_va_sha256=ctx["gate_va_sha256"],waveform_sha256=sha(OUT/f"runs/{name}_waveform.json")))
    files=[ROOT/p for p in ["config/sar8_join_r1.yaml","scripts/integration/join_r1.py",
        "scripts/integration/join_r1_sim.py","scripts/integration/join_r1_analyze.py",
        "scripts/integration/join_r1_curate.py","verification/integration/test_join_r1.py"]]
    data=dict(baseline_id="SAR8_JOIN_R1_3X_IDEAL_GATE_NATIVE_ASYNC",frozen_circuit=True,
              time_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
              qualified=False,scope="TT .9V 27C bounded nominal native joint integration; ideal reference gate boundary",
              cells=dict(top=TOP,bench=TB,array=ARRAY,reference_gate=GATE),
              R0_source_lock_sha256=sha(ROOT/"verification/integration/join_r0_sources.json"),
              source_text_LF_sha256={p.relative_to(ROOT).as_posix():text_sha(p) for p in files},
              gate_VA_exact_byte_sha256=sha(VA),
              new_OA_schematic_surface_sha256={o.name:object_digest(schematic_surface(read_json(OUT/f"oa/{o.name}.json"))) for o in objects()},
              saved_OA_export_audit=audit,
              old_native_cells_before_after_unchanged=True,
              simulator="Spectre21.1 APS conservative reltol1e-5 vabstol1e-8 iabstol1e-13",
              cases=cases,
              completed_runs=len(cases),frames=sum(len(c["frames"]) for c in cases),
              functional_frames_pass=sum(f["frame_pass"] for c in cases for f in c["frames"]),
              bounded_SOA_and_function_cases_pass=sum(c["bounded_join_pass"] for c in cases),
              worst_compare_error_mv=max(f["max_compare_error_mv"] for c in cases for f in c["frames"]),
              worst_reference_terminal=max((c["reference_stress"]|dict(case=c["name"]) for c in cases),key=lambda v:v["value_v"]),
              exclusions=["PVT","MC/mismatch","transient noise","full-code static linearity","FFT/SNDR/ENOB",
                          "actual reference gate-driver energy","native reference buffer","layout/PEX/reliability signoff"])
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print("CURATED",len(cases),"runs",data["functional_frames_pass"],"functional frames",
          "SOA_AND_FUNCTION",data["bounded_SOA_and_function_cases_pass"],flush=True)


if __name__=="__main__":main()
