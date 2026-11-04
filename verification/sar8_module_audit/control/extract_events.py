"""Read small immutable evidence; never launch/reduce a simulation or alter it."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[2]
RUNS = ("sar8fix-loaded-both-rx2-tt", "sar8fix-loaded-both-rx2-end210-sscold")
MAX_INPUT_BYTES = 4 * 1024 * 1024
CLASS_NATIVE = "native_point_interpolated_0p5VDD_crossing"
CLASS_COMPACT = "existing_20ps_compact_wave_summary_estimate"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_small(path, inputs, role, expected=None):
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"Input exceeds small-file budget: {path}")
    blob = path.read_bytes()
    digest = sha256(blob)
    if expected is not None and digest != expected:
        raise ValueError(f"SHA256 mismatch: {path}")
    inputs.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest,
                       bytes=len(blob), role=role, expected_sha256=expected,
                       expected_sha256_matches=None if expected is None else True))
    return blob


def receipt_file(folder, receipt, name, inputs):
    entries = [item for item in receipt["files"] if item["name"] == name]
    if len(entries) != 1:
        raise ValueError(f"Receipt has {len(entries)} entries for {name}")
    item = entries[0]
    path = folder / name
    if (not path.exists() or path.stat().st_size > MAX_INPUT_BYTES
            or sha256(path.read_bytes()) != item["sha256"]):
        path = path.with_name(path.stem + "." + item["sha256"][:12] + path.suffix)
    blob = read_small(path, inputs, "collected:" + name, item["sha256"])
    if len(blob) != item["bytes"]:
        raise ValueError(f"Receipt size mismatch: {name}")
    return blob


def parse_events(text, unit="s"):
    factors = {"s": 1e9, "ns": 1.0}
    if unit not in factors:
        raise ValueError("Event time unit must be explicitly s or ns")
    events = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"Malformed event line {number}")
        name, direction, value = fields
        if direction not in ("0", "1"):
            raise ValueError(f"Invalid direction at line {number}")
        instant = float(value) * factors[unit]
        if not math.isfinite(instant) or instant < 0:
            raise ValueError(f"Invalid event time at line {number}")
        events.setdefault((name.lower(), int(direction)), []).append(instant)
    return events


def record(value, status, evidence_class, reason=None, **details):
    if value is not None and not math.isfinite(value):
        raise ValueError("Non-finite time")
    return dict(time_ns=value, status=status, evidence_class=evidence_class,
                reason=reason, **details)


def pick(events, name, direction, start, stop, expected_count=1, index=0):
    times = [t for t in events.get((name.lower(), direction), []) if start <= t < stop]
    details = dict(signal=name, direction=direction, search_interval_ns=[start, stop],
                   observed_count=len(times), expected_count=expected_count)
    if not times:
        return record(None, "not_observed", CLASS_NATIVE, "No crossing in observed interval", **details)
    if len(times) != expected_count or len(set(times)) != len(times) or times != sorted(times):
        return record(None, "ambiguous", CLASS_NATIVE,
                      "Count, duplicate or chronological-order mismatch", **details)
    return record(times[index], "observed", CLASS_NATIVE, **details)


def require_time(event, allowed_classes=None):
    if event["status"] not in ("observed", "estimated", "predicted", "scheduled"):
        raise ValueError("Unusable timing evidence: " + event["status"])
    value = event["time_ns"]
    if value is None or not math.isfinite(value):
        raise ValueError("Missing or non-finite timing evidence")
    if allowed_classes is not None and event["evidence_class"] not in allowed_classes:
        raise ValueError("Wrong evidence class for timing gate")
    return value


def margin_gate(ready, deadline, required_margin_ns=None):
    """Diagnostic gate only. Unknown budget or unusable evidence never passes."""
    try:
        margin = require_time(deadline, {CLASS_NATIVE}) - require_time(ready, {CLASS_NATIVE, CLASS_COMPACT})
    except ValueError as error:
        return dict(status="undecided", pass_=None, measured_margin_ns=None,
                    required_margin_ns=required_margin_ns, reason=str(error))
    if required_margin_ns is None:
        return dict(status="undecided", pass_=None, measured_margin_ns=margin,
                    required_margin_ns=None, reason="Required protection margin is unallocated")
    if not math.isfinite(required_margin_ns) or required_margin_ns < 0:
        raise ValueError("Invalid required margin")
    passed = margin >= required_margin_ns
    return dict(status="pass" if passed else "fail", pass_=passed,
                measured_margin_ns=margin, required_margin_ns=required_margin_ns,
                reason="Synthetic/explicit-budget diagnostic; no default silicon target")


def spice_time_ns(token):
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([fpnum]?s?)", token.strip())
    if not match:
        raise ValueError("Unsupported source time: " + token)
    suffix = match[2]
    scale = {"": 1e9, "s": 1e9, "m": 1e6, "ms": 1e6, "u": 1e3, "us": 1e3,
             "n": 1, "ns": 1, "p": 1e-3, "ps": 1e-3, "f": 1e-6, "fs": 1e-6}[suffix]
    value = float(match[1]) * scale
    if not math.isfinite(value) or value < 0:
        raise ValueError("Invalid source time")
    return value


def pulse_contract(deck):
    matches = re.findall(r"(?m)^VSAMPLE\s+\([^\n]+", deck)
    if len(matches) != 1:
        raise ValueError("Expected one frozen VSAMPLE source")
    fields = dict(re.findall(r"(\w+)\s*=\s*(\S+)", matches[0]))
    if fields.get("type") != "pulse" or fields.get("val0") != "SUP" or fields.get("val1") != "0":
        raise ValueError("Only audited SUP-to-zero SAMPLE pulse supported")
    times = {k: spice_time_ns(fields[k]) for k in ("delay", "rise", "fall", "width", "period")}
    if times["rise"] != times["fall"] or times["period"] <= 0:
        raise ValueError("Only symmetric, positive-period audited pulse supported")
    return dict(**times, close_offset_ns=times["delay"] + times["fall"] / 2,
                next_open_offset_ns=times["delay"] + times["fall"] + times["width"] + times["rise"] / 2,
                source_line=matches[0], unit="ns")


def observer_times(text):
    offsets = [tuple(spice_time_ns(x) for x in pair) for pair in
               re.findall(r"timer\(\s*([^,]+),\s*([^\)]+)\)", text)]
    if offsets.count((90.0, 100.0)) != 1 or offsets.count((98.0, 100.0)) != 1:
        raise ValueError("Frozen observer schedule differs from audited 90/98 ns fixture")
    return dict(read_window_start_ns=90.0, read_time_ns=98.0, period_ns=100.0,
                role="Existing test observation schedule; silicon interface target unallocated")


def collect_frame(events, summary, frame, stop_ns, pulse, observer):
    origin, end = frame * pulse["period"], (frame + 1) * pulse["period"]
    hi = min(end, stop_ns + 1e-7)
    items = {
        "external_SAMPLE_close": record(origin + pulse["close_offset_ns"], "predicted", "source_parameter"),
        "SAMPLE_INT_close": pick(events, "xdut.sample_int", 0, origin, hi),
        "SEQ_SAMPLE_close": pick(events, "xdut.seq_sample", 0, origin, hi),
        "first_compare": pick(events, "xdut.cmp_clk", 1, origin, hi, 8, 0),
        "last_write": pick(events, "xdut.xctrl.phi_w", 1, origin, hi, 8, -1),
        "last_update": pick(events, "xdut.phi_u", 1, origin, hi, 8, -1),
        "test_read_window_start": record(origin + observer["read_window_start_ns"], "scheduled", "observer_schedule"),
        "test_read_time": record(origin + observer["read_time_ns"], "scheduled", "observer_schedule"),
        "next_external_SAMPLE_open": record(origin + pulse["next_open_offset_ns"], "predicted", "source_parameter"),
        "next_SAMPLE_INT_open": pick(events, "xdut.sample_int", 1, end, min(end + pulse["period"], stop_ns + 1e-7)),
        "next_SEQ_SAMPLE_open": pick(events, "xdut.seq_sample", 1, end, min(end + pulse["period"], stop_ns + 1e-7)),
        "DOUT_valid": record(None, "unavailable", "not_measured",
                             "Final write crossing and observer valid do not measure a qualified DOUT-valid time"),
    }
    write_time = items["last_write"]["time_ns"]
    if items["next_SEQ_SAMPLE_open"]["status"] == "observed":
        reset_end = require_time(items["next_SEQ_SAMPLE_open"], {CLASS_NATIVE})
    elif items["next_SAMPLE_INT_open"]["status"] == "observed":
        # A partial search bounded by the next control initialization cannot
        # accidentally attribute a still-later frame's reset to this frame.
        reset_end = require_time(items["next_SAMPLE_INT_open"], {CLASS_NATIVE})
    else:
        reset_end = min(end, stop_ns + 1e-7)
    items["last_reference_RST0_assertion"] = (
        pick(events, "xdut.xref.rst0", 1, write_time, reset_end) if write_time is not None
        else record(None, "unavailable", CLASS_NATIVE, "Last-write anchor unavailable"))
    readiness = summary.get("reset_before_actual_next_sample") or {}
    ready = readiness.get("settled_ns")
    native_next = items["next_SEQ_SAMPLE_open"]
    if readiness.get("observed") and ready is not None and native_next["status"] == "observed":
        if abs(readiness["next_actual_sample_ns"] - require_time(native_next)) > 1e-5:
            raise ValueError("Compact summary and native next-sample identity mismatch")
        if write_time is None or not write_time <= ready < require_time(native_next):
            raise ValueError("Compact ready estimate outside its reference interval")
        items["bottom_ready"] = record(ready, "estimated", CLASS_COMPACT,
            "Fixed reset targets; all 16 bottoms within +/-1.7578125 mV until next sample minus 20 ps; not a budget allocation")
    else:
        items["bottom_ready"] = record(None, "not_observed", CLASS_COMPACT,
            "Existing summary does not establish readiness before an observed next sample")
    anchor = items["SEQ_SAMPLE_close"]
    for item in items.values():
        item["time_from_SEQ_SAMPLE_close_ns"] = (
            item["time_ns"] - anchor["time_ns"]
            if item["time_ns"] is not None and anchor["status"] == "observed" else None)
    legacy_measured = None
    if items["last_update"]["status"] == items["SAMPLE_INT_close"]["status"] == "observed":
        legacy_measured = items["last_update"]["time_ns"] - items["SAMPLE_INT_close"]["time_ns"]
        if abs(legacy_measured - summary["conversion_ns"]) > 1e-5:
            raise ValueError("Historical conversion_ns does not match native events")
    return dict(frame=frame, frame_origin_ns=origin, events=items,
                conversion_ns=summary["conversion_ns"],
                conversion_ns_definition="last PHI_U rising minus SAMPLE_INT falling; original metric unchanged",
                native_legacy_latency_ns=legacy_measured,
                bottom_before_next_sample=margin_gate(items["bottom_ready"], native_next),
                data_before_read_window=dict(status="undecided", pass_=None,
                    reason="DOUT-valid time and silicon read interface budget are unallocated"))


def extract_run(run):
    inputs = []
    verify = ROOT / "verification/sar8_physical_repair"
    manifest = json.loads(read_small(verify / (run + "_manifest.json"), inputs, "frozen_manifest"))
    summary = json.loads(read_small(verify / (run + "_analysis.json"), inputs, "existing_local_derived_summary"))
    if summary["run_id"] != run or manifest["run_id"] != run:
        raise ValueError("Run identity mismatch")
    if not summary.get("frozen_inputs_sha_verified") or not summary.get("events_all_native_points"):
        raise ValueError("Prior analysis does not declare verified native event provenance")
    managed = ROOT / "output/managed_execution/runs" / run
    folder = managed / "collected"
    receipt = json.loads(read_small(folder / "collection_receipt.json", inputs, "collection_receipt"))
    if receipt.get("skipped"):
        raise ValueError("Collection receipt includes skipped files")
    for phase in ("simulation", "analysis"):
        state = json.loads(receipt_file(folder, receipt, phase + ".state.json", inputs))
        if state["status"] != "complete" or state["exit_code"] != 0:
            raise ValueError("Incomplete managed phase: " + phase)
    meta = json.loads(receipt_file(folder, receipt, "derived/wave.meta.json", inputs))
    stop_ns = meta["last_time_s"] * 1e9
    if not meta["PSF_END"] or abs(stop_ns - manifest.get("stop_ns", 200)) > 1e-5:
        raise ValueError("Observation end mismatch")
    event_text = receipt_file(folder, receipt, "derived/wave.events.tsv", inputs).decode()
    deck = read_small(managed / "inputs/test.scs", inputs, "frozen_source_deck", manifest["files"]["test.scs"]).decode()
    read_small(managed / "inputs/dut.scs", inputs, "frozen_DUT_identity", manifest["files"]["dut.scs"])
    observer_text = read_small(managed / "inputs/r4_perf_monitor.va", inputs, "frozen_observer", manifest["files"]["r4_perf_monitor.va"]).decode()
    pulse, observer = pulse_contract(deck), observer_times(observer_text)
    if pulse["period"] != observer["period_ns"]:
        raise ValueError("Frame and observer periods differ")
    if len(summary["frames"]) != 2 or [f["frame"] for f in summary["frames"]] != [0, 1]:
        raise ValueError("Expected the two audited frames in chronological order")
    frames = [collect_frame(parse_events(event_text), f, index, stop_ns, pulse, observer)
              for index, f in enumerate(summary["frames"])]
    passive_sections = re.findall(r"section=(\w+)", deck)
    return dict(run_id=run, corner=manifest["corner"], vdd_v=manifest["vdd"],
                temperature_c=manifest["temp_c"], observation_stop_ns=stop_ns,
                inputs=inputs, pulse=pulse, observer=observer, frames=frames,
                passive_sections=[s for s in passive_sections if "_res_" in s or s.endswith("_mom")],
                passive_process_extremes_verified=False,
                unallocated_budgets=["silicon_read_time", "DOUT_receiver_setup_and_hold",
                    "minimum_reset_to_sampling_margin", "per_bit_compare_and_reference_budget"])


def main():
    payload = dict(schema_version=1, time_unit="ns", input_events_time_unit="s",
        role="Local evidence extraction; no simulation, adoption or silicon acceptance",
        relative_time_origin="Each frame's native-point SEQ_SAMPLE falling 0.5VDD crossing; not calibrated aperture",
        limitations=["No raw waves read or reanalyzed", "Compact readiness is copied from a hashed existing local summary",
            "Collection receipt hashes verify consumed small files; unread wave.bin is not rehashed",
            "90/98 ns are existing observer schedule values, not approved hardware interface targets"],
        extractor_sha256=sha256(Path(__file__).read_bytes()), runs=[extract_run(run) for run in RUNS])
    output = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(output.encode()) > 1024 * 1024:
        raise ValueError("Output budget exceeded")
    (OWN / "events.json").write_text(output, encoding="utf-8")
    print(json.dumps(dict(output=str(OWN / "events.json"), runs=len(payload["runs"]),
        frames=sum(len(run["frames"]) for run in payload["runs"]),
        all_acceptance_gates="undecided: required budgets unallocated"), ensure_ascii=False))


if __name__ == "__main__":
    main()
