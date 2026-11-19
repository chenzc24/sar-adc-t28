"""Summarize accepted waveform and receiver measurements from one managed SAR corner."""

import hashlib
import json


def summarize(folder):
    artifact = folder / "derived/result.json"
    receipt = json.loads((folder / "collection_receipt.json").read_text())
    item = next(row for row in receipt["files"] if row["name"] == "derived/result.json")
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != item["sha256"]:
        raise ValueError("Result does not match its managed collection receipt")
    result = json.loads(artifact.read_text())
    ctx = result["context"]
    frames = result["frames"]
    state = receipt["status"]
    if (
        not result["analysis_complete"]
        or state["simulation"]["status"] != "complete"
        or state["analysis"]["status"] != "complete"
    ):
        raise ValueError("Native simulation and waveform analysis must both be complete")
    bits = [b for frame in frames for b in frame["bits"]]
    if len(frames) != ctx["frames"] or len(bits) != 8 * len(frames):
        raise ValueError("Missing conversion or per-bit data")
    headroom = []
    for f in frames:
        updates = [e["time_s"] for e in f["events"] if e["signal"] == "update" and e["rising"]]
        if len(updates) != 8:
            raise ValueError("Missing update edges")
        headroom.append((ctx["frame_origin_s"] + f["frame"] * ctx["period_s"] + 90e-9 - updates[-1]) * 1e9)
    taps = [f["extracted_timing"] for f in frames]

    def samples(metric):
        return [v for frame in taps for v in frame.get(metric, [])]

    skew = samples("write_skew_ps")
    guard = samples("update_to_next_compare_ps")
    clock_ok = (
        all(t["receiver_write_counts"] == [8] * 8 for t in taps)
        and len(skew) == len(bits)
        and len(guard) == 7 * len(frames)
    )
    observed = [f["code_98"] for f in frames]
    return dict(
        run_id=state["run_id"],
        host=state["host"],
        recipe_sha256=state["registered"]["recipe_hash"],
        result_sha256=item["sha256"],
        physical_id=ctx["physical_id"],
        gds_sha256=ctx["gds_sha256"],
        mos=ctx["mos"],
        vdd_v=ctx["vdd_v"],
        temperature_c=ctx["temperature_c"],
        frames=len(frames),
        bit_decisions=len(bits),
        codes=observed,
        all_codes_correct=result["all_code_pass"],
        functional_timing_pass=result["pass_function_timing"],
        all_screens_pass=result["all_screens_pass"],
        distributed_receivers_pass=clock_ok,
        pass_corner=bool(
            result["all_code_pass"]
            and result["pass_function_timing"]
            and result["all_screens_pass"]
            and clock_ok
            and min(headroom) >= 0
            and min(guard) > 0
        ),
        worst_conversion_ns=max(f["conversion_ns"] for f in frames),
        min_margin_to_90ns_read_ns=min(headroom),
        min_margin_to_next_sample_ns=min(f["deadline_margin_ns"] for f in frames),
        max_bit_clock_skew_ps=max(skew) if skew else None,
        min_quiet_update_to_next_compare_ns=min(guard) * 1e-3 if guard else None,
        min_receiver_valid_to_write_ps=min(b["receiver_margin_ps"] for b in bits),
        max_cdac_bottom_error_lsb=max(b["bottom"]["weighted_bound_lsb"] for b in bits),
        native_warning_codes=result["warning_codes"],
        first_issue=result["first_issue"],
    )
