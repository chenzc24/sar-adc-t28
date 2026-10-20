"""Small, reproducible acceptance summary; functional and SOA gates separate."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from analyze import analyze, load
from circuit import TOP, hierarchy
from netlist_logic import normalized
from oa import OUT, ROOT

CASES = ["two_cycles", "two_cycles_fine", "pattern_0", "pattern_255", "pattern_85", "pattern_170",
         "fast", "slow", "ss", "ff", "recovery", "interrupt", "strongarm"]


def main():
    reports = {}; summaries = []
    expected = {"two_cycles": [145, 85], "two_cycles_fine": [145, 85],
                "pattern_0": [0], "pattern_255": [255], "pattern_85": [85], "pattern_170": [170],
                "fast": [165], "slow": [165], "ss": [165], "ff": [165],
                "recovery": [165, 160, 165], "interrupt": [160, 165], "strongarm": [145]}
    for case in CASES:
        name = case + "_simple_v2_aps"
        row = analyze(name); reports[case] = row
        frames = row["frames"]
        assert [frame["word_at_read"] for frame in frames] == expected[case], (case, frames)
        assert not row["any_bottom_overlap"], case
        assert not row["sampling_illegal_rising_edges"] and row["sampling_initialization_observed"], case
        for index, frame in enumerate(frames):
            partial = (case == "recovery" and index == 1) or (case == "interrupt" and index == 0)
            if not partial:
                assert frame["comparisons"] == frame["writes"] == frame["updates"] == 8, (case, frame)
                assert frame["token_at_read"] == 0 and frame["write_tokens"] == [128, 64, 32, 16, 8, 4, 2, 1]
                assert frame["word_stable_in_read_window"]
            elif case == "recovery":
                assert (frame["comparisons"], frame["writes"], frame["updates"], frame["token_at_read"]) == (5, 4, 4, 8)
            else:
                assert frame["comparisons"] < 8 and frame["writes"] < 8
            assert frame["bottom_codes_correct_at_write"] and frame["token_single_hot_at_every_write"]
            assert not frame["bottom_changed_during_compare_or_100ps_write_hold"]
            assert all(margin > .10 for margin in frame.get("write_to_update_ns", []))
            assert all(margin > .10 for margin in frame.get("write_to_comparator_reset_ns", []))
        cmi = [line for line in row["device_warning_lines"] if "CMI-" in line]
        compact = []
        for frame in frames:
            compact.append({key: frame[key] for key in ("sample_end_ns", "next_sample_ns", "read_time_ns", "read_window_ns",
                "comparisons", "writes", "updates", "word_at_read", "token_at_read", "write_tokens", "write_ns",
                "write_to_update_ns", "write_to_comparator_reset_ns", "comparator_low_ns", "word_stable_in_read_window",
                "bottom_changed_during_compare_or_100ps_write_hold", "token_transition_multihot_max_ns") if key in frame})
        record, context, _, _ = load(name)
        export_path = ROOT / context["source_export"]
        deck = (OUT / "decks" / (name + ".scs")).read_text(encoding="utf-8")
        assert normalized(deck) == normalized(export_path.read_text(encoding="utf-8")), (case, "DUT changed")
        summaries.append(dict(name=name, scope=record["scope"], context=context,
            deck_sha256=record["deck_sha256"], waves_sha256=row["waves_sha256"],
            export_sha256=hashlib.sha256(export_path.read_bytes()).hexdigest(),
            all_requested_traces_finite=record["waveform_validation"]["all_requested_traces_finite"],
            functional_checks_pass=True, execution_ok=True, frames=compact,
            PHI_W_extrema=row["extrema"]["xctrl.phi_w"], CMI_warnings=cmi,
            warning_summary=[line for line in row["device_warning_lines"] if "suppressed" in line],
            all_bottom_controls_mutually_exclusive_at_half_supply=True,
            sampling_initialization_and_no_illegal_clock_edges=True,
            result_directory=record["metadata"].get("output_dir")))
        summaries[-1]["model_includes"] = [dict(path=path, section=section) for path, section in
            re.findall(r'(?m)^include "([^"\n]+)" section=(\S+)', deck)]
    old = analyze("two_cycles_simple_v1_aps")
    normal = reports["two_cycles"]; fine = reports["two_cycles_fine"]
    assert not any("CMI-" in line for line in normal["device_warning_lines"]), "Nominal drive repair still has stress"
    assert not any("CMI-" in line for line in fine["device_warning_lines"]), "Fine nominal still has stress"
    comparison = dict(v1_min_v=old["extrema"]["xctrl.phi_w"]["min_v"],
        v2_min_v=normal["extrema"]["xctrl.phi_w"]["min_v"], fine_min_v=fine["extrema"]["xctrl.phi_w"]["min_v"],
        interpretation="Stronger write-clock drive sensitivity; not proof of a unique coupling root cause")
    assert abs(comparison["v2_min_v"] - comparison["fine_min_v"]) < .002
    hierarchy_audit = json.loads((OUT / "audit/hierarchy.json").read_text(encoding="utf-8"))
    result = dict(stage="native_bounded_verification_not_full_ADC_qualified", top=TOP,
        profile="t28_io", library="SAR_ADC_T28", simulator="Spectre 21.1.0.509.isr12 APS",
        bridge_version="0.8.0", native_runs=len(summaries),
        nominal_functional_and_device_warning_screens_pass=True,
        full_256_native_Spectre_sweep_completed=False, native_hierarchy_audit=hierarchy_audit,
        write_clock_drive_comparison=comparison, cases=summaries,
        open_gates=["physical CDAC/bootstrap/reference/load integration", "PDK/layout/tolerance implementation of ideal RC delays",
                    "metastability error probability and fixed read-window robustness", "noise/mismatch/power/layout and full ADC performance"],
        qualified=False)
    result["post_run_plant_source_readback"] = json.loads((OUT / "dependencies/plant_hashes.json").read_text(encoding="utf-8"))
    if any(item["CMI_warnings"] for item in summaries):
        result["open_gates"].insert(0, "device SOA warnings in bounded nonnominal case(s): " +
            ", ".join(item["name"] for item in summaries if item["CMI_warnings"]))
    folder = ROOT / "verification/sar8_simple"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    cells = [dict(name=obj.name, inputs=obj.inputs, outputs=obj.outputs, direct_instances=len(obj.parts),
                  child_cells=sorted({part.master for part in obj.parts if part.lib == "SAR_ADC_T28"}))
             for obj in hierarchy()]
    (folder / "cells.json").write_text(json.dumps(cells, indent=2) + "\n", encoding="utf-8")
    print("ACCEPTANCE_SUMMARY", len(summaries), comparison, result["open_gates"])


if __name__ == "__main__":
    main()
