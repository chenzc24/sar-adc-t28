"""Audit the completed nominal migration, including deliberately failing controls."""
from __future__ import annotations

import json
from pathlib import Path

from common import OUT, ROOT, load, dump, digest


def audit():
    counts={};records=[]
    expected={"veriloga":4,"first_order":4,"electrical":13,"bootstrap":16,"comparator":12}
    for category,count in expected.items():
        paths=sorted((OUT/category).glob("*_result.json"))
        assert len(paths)==count,(category,len(paths),count)
        counts[category]=len(paths)
        for path in paths:
            r=json.loads(path.read_text())
            assert r["ok"] and not r["errors"],path
            assert digest(OUT/"decks"/(r["name"]+".scs"))==r["deck_sha256"],path
            for name,fingerprint in r.get("include_sha256",{}).items():
                assert digest(ROOT/"models/veriloga"/name)==fingerprint,(path,name)
            raw=Path(r["metadata"]["output_dir"])
            log=(raw.parent/"spectre.out").read_text(errors="replace")
            assert "21.1.0.509" in log,raw
            assert raw.is_dir() and r["metadata"]["returncode"]==0,raw
            records.append({"name":r["name"],"deck_sha256":r["deck_sha256"],"physical_result_directory":str(raw)})
    va=load("veriloga/summary.json")
    assert va["static"]["codes"]==256 and va["static"]["samples"]==2048
    assert va["dynamic"]["samples"]==va["allocated_noise"]["samples"]==16384
    assert va["allocated_noise"]["enob_bits"]>=7
    macro=load("electrical/summary.json")
    assert sum(x["kind"]=="nominal" and x["pass"] for x in macro)==10
    assert not next(x for x in macro if x["name"]=="macro8_slow_reference")["pass"]
    first=load("first_order.json")
    assert len(first["spectre_correlations"])==4
    initial=load("bootstrap/summary_initial.json");selected=load("bootstrap/summary_w1u.json")
    assert not all(x["NEW"]["pass"] for x in initial)
    assert len(selected)==5 and all(x["NEW"]["pass"] for x in selected)
    precision=[]
    for x in load("bootstrap/summary_w1u_tight.json"):
        nominal=next(y for y in selected if y["input_v"]==x["input_v"])
        delta_uv=abs(x["NEW"]["held_error_mv"]-nominal["NEW"]["held_error_mv"])*1000
        assert x["NEW"]["pass"] and delta_uv<1,delta_uv
        precision.append(delta_uv)
    isolated=load("bootstrap/summary_w1u_only_new.json")
    assert len(isolated)==2
    for x in isolated:
        assert x["NEW"]["pass"] and x["warnings"]["cmi_count"]==x["warnings"]["suppressed"]==0
        assert x["warnings"]["sfe_1131"]==4
    comparator=load("comparator/summary_w1u.json")
    assert len(comparator)==6
    active=[x for x in comparator if x["clock_enabled"] and x["input_v"]]
    assert all(x["decision_correct"] and x["resolved"] for x in active)
    assert all(x["warnings"]["cmi_count"]==x["warnings"]["suppressed"]==0 for x in comparator)
    for cell in ("sar_cdac_flat_8b","sar_comparator_macro_8b","sar_bootstrap_canvas_flat_8b",
                 "tb_sar_macro_flat_8b","tb_bootstrap_flat_8b","tb_cdac_strongarm_flat_8b"):
        assert load(f"oa/{cell}_markers.json")==[],cell
    oa=load("oa/final_readonly_check.json")
    assert len(oa["unchanged"])==6 and len(oa["fresh_exports"])==3
    assert oa["controller_va_matches_local"] and all(x["equal_except_generation_date"] for x in oa["fresh_exports"])
    for r in oa["fresh_exports"]:
        assert digest(OUT/"oa_netlists"/r["cell"]/"final/input.scs")==r["fresh_oa_sha256"]
    result={"accepted_solver_runs":len(records),"counts":counts,"expected_negative_controls_preserved":True,
        "precision_max_held_delta_uv":max(precision),"oa":oa,
        "selected_native_main_width_um":1,"selected_native_held_error_abs_max_mv":max(abs(x["NEW"]["held_error_mv"]) for x in selected),
        "selected_native_acquisition_error_abs_max_mv":max(abs(x["NEW"]["acquisition_error_mv"]) for x in selected),
        "strongarm_on_minus_off_peak_diff_mv":max(x["on_minus_off_peak_diff_kickback_mv"] for x in comparator if x["clock_enabled"]),
        "source_sha256":{p:digest(ROOT/p) for p in ("config/design_spec.yaml","config/design_spec_10b.yaml","config/eight_bit_flat.yaml",
            "models/veriloga/sar_adc_ideal_8b.va","models/veriloga/sar_macro_controller_8b.va")},"runs":records,
        "scope":"nominal electrical macro plus native sampling/interface; not a full transistor ADC qualification"}
    dump("final_manifest.json",result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("runs","oa","source_sha256")},indent=2))
    return result


if __name__=="__main__":audit()
