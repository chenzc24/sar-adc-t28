"""Bounded compact-export DOUT diagnostics; not output-interface qualification."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

from extract_events import OWN, ROOT, RUNS, read_small, receipt_file, spice_time_ns

MAX_BINARY_BATCH_BYTES = 32 * 1024 * 1024
NUMERICAL_TIME_EPS_NS = 1e-6


def unavailable(reason):
    return dict(status="unavailable", sampled_ready_ns=None,
                sampled_ready_bracket_ns=None, reason=reason)


def sampled_ready(t_ns, values_v, vdd_v, expected_bit, start_ns, end_ns,
                  *, band_fraction, justified_max_grid_gap_ns):
    """First in-band sample after the last bad sample, through end's bracket."""
    t, values, rail = (np.asarray(x, dtype=float) for x in (t_ns, values_v, vdd_v))
    if (len(t) < 2 or values.shape != t.shape or rail.shape != t.shape
            or not all(np.isfinite(x).all() for x in (t, values, rail))
            or not np.all(np.diff(t) > 0) or not np.all(rail > 0)):
        return unavailable("Missing/nonfinite data or nonmonotonic compact time grid")
    if (expected_bit not in (0, 1) or not math.isfinite(start_ns) or not math.isfinite(end_ns)
            or start_ns >= end_ns or band_fraction is None or not 0 < band_fraction < .5):
        return unavailable("Expected bit, interval or legacy diagnostic band unavailable")
    if justified_max_grid_gap_ns is None or justified_max_grid_gap_ns <= 0:
        return unavailable("Compact-grid resolution bound unavailable")
    if t[0] > start_ns or t[-1] < end_ns:
        return unavailable("Observation does not bracket both diagnostic endpoints")
    begin = int(np.searchsorted(t, start_ns, side="left"))
    end = int(np.searchsorted(t, end_ns, side="left"))
    left = begin if t[begin] == start_ns else begin - 1
    max_gap = float(np.diff(t[left:end + 1]).max()) if end > left else None
    if max_gap is None or max_gap > justified_max_grid_gap_ns + NUMERICAL_TIME_EPS_NS:
        return dict(**unavailable("Compact-grid gap exceeds provenance-derived resolution bound"),
                    observed_max_gap_ns=max_gap)
    indices = np.arange(begin, end + 1)
    if len(indices) < 2:
        return unavailable("Fewer than two samples in the diagnostic interval")
    errors = np.abs(values[indices] - expected_bit * rail[indices])
    good = errors < band_fraction * rail[indices]
    bad = np.flatnonzero(~good)
    first = int(bad[-1] + 1) if len(bad) else 0
    details = dict(checked_samples=len(indices), observed_max_gap_ns=max_gap,
                   read_bracket_ns=[float(t[end] if t[end] == end_ns else t[end - 1]), float(t[end])],
                   all_checked_samples_in_band=bool(np.all(good)),
                   last_out_of_band_sample_ns=float(t[indices[bad[-1]]]) if len(bad) else None)
    if len(indices) - first < 2:
        return dict(**unavailable("No two-sample in-band suffix through the read bracket"), **details)
    k = int(indices[first])
    return dict(status="sampled_estimate", sampled_ready_ns=float(t[k]),
                sampled_ready_bracket_ns=[float(t[k - 1]) if first else start_ns, float(t[k])],
                reason="First sampled in-band suffix; intersample behavior and receiver validity unqualified",
                **details)


def grid_bound(summary):
    text = summary.get("effective_settings", {}).get("maxstep", "")
    match = re.match(r"([0-9.eE+-]+)\s*(fs|ps|ns|us|ms|s)\b", text)
    spacing = summary.get("plot_estimate_spacing_ps")
    if match is None or spacing is None or spacing <= 0:
        return None
    return float(spacing) / 1000 + spice_time_ns(match[1] + match[2])


def frame_diagnostic(t, dout, vdd, frame, expected_word, *, band_fraction, max_gap):
    events = frame["events"]
    if expected_word is None or not isinstance(expected_word, int) or not 0 <= expected_word <= 255:
        return unavailable("Prior case's expected output word unavailable")
    start = events["SEQ_SAMPLE_close"]["time_ns"]
    read = events["test_read_time"]["time_ns"]
    window = events["test_read_window_start"]["time_ns"]
    if (events["SEQ_SAMPLE_close"]["status"] != "observed"
            or any(x is None for x in (start, read, window))):
        return unavailable("Frame anchor or legacy observer schedule unavailable")
    if dout.ndim != 2 or dout.shape != (len(t), 8):
        return unavailable("Eight output columns unavailable")
    bits, windows = [], []
    for bit in range(8):
        args = dict(band_fraction=band_fraction, justified_max_grid_gap_ns=max_gap)
        item = sampled_ready(t, dout[:, bit], vdd, (expected_word >> bit) & 1, start, read, **args)
        item.update(bit=bit, expected_bit=(expected_word >> bit) & 1)
        bits.append(item)
        windows.append(sampled_ready(t, dout[:, bit], vdd, (expected_word >> bit) & 1, window, read, **args))
    ready = max(x["sampled_ready_ns"] for x in bits) if all(x["sampled_ready_ns"] is not None for x in bits) else None
    write = events["last_write"]["time_ns"]
    return dict(frame=frame["frame"], expected_word_from_prior_case=expected_word,
        status="sampled_diagnostic" if ready is not None else "unavailable",
        search_start_SEQ_SAMPLE_close_ns=start, legacy_observer_window_ns=[window, read],
        sampled_bus_ready_ns=ready, sampled_bus_ready_from_SEQ_SAMPLE_close_ns=None if ready is None else ready - start,
        last_native_write_crossing_ns=write,
        sampled_bus_ready_minus_last_write_ns=None if ready is None or write is None else ready - write,
        per_bit=bits,
        legacy_window_all_checked_samples_in_expected_band=(
            all(x["all_checked_samples_in_band"] for x in windows)
            if all("all_checked_samples_in_band" in x for x in windows) else None),
        legacy_window_per_bit=windows,
        qualified_DOUT_valid_time_ns=None, setup_requirement_ns=None, hold_requirement_ns=None,
        silicon_acceptance=dict(status="undecided", pass_=None,
            reason="Receiver thresholds, interface timing and intersample glitches are unverified"))


def compact_path(folder, receipt, name):
    records = [x for x in receipt["files"] if x["name"] == name]
    if len(records) != 1:
        raise ValueError("Missing/duplicate compact receipt entry: " + name)
    item = records[0]
    path = folder / name
    if not path.exists():
        path = path.with_name(path.stem + "." + item["sha256"][:12] + path.suffix)
    if path.stat().st_size != item["bytes"]:
        raise ValueError("Compact binary size mismatch")
    return path, item


def main():
    common_inputs = []
    table_path = OWN / "events.json"
    table = json.loads(read_small(table_path, common_inputs, "existing_event_table"))
    if table["extractor_sha256"] != hashlib.sha256((OWN / "extract_events.py").read_bytes()).hexdigest():
        raise ValueError("Regenerate events.json with the current extractor before this diagnostic")
    if [x["run_id"] for x in table["runs"]] != list(RUNS):
        raise ValueError("Unexpected event-table run identities")
    work = []
    for event_run in table["runs"]:
        run = event_run["run_id"]
        folder = ROOT / "output/managed_execution/runs" / run / "collected"
        inputs = []
        receipt_input = next(x for x in event_run["inputs"] if x["role"] == "collection_receipt")
        receipt = json.loads(read_small(folder / "collection_receipt.json", inputs, "collection_receipt",
                                        receipt_input["sha256"]))
        path, item = compact_path(folder, receipt, "derived/wave.bin")
        work.append((event_run, folder, receipt, inputs, path, item))
    binary_bytes = sum(x[-1]["bytes"] for x in work)
    if binary_bytes > MAX_BINARY_BATCH_BYTES:
        raise ValueError("Compact binary batch exceeds 32 MiB")
    planned_bytes = binary_bytes + sum(x["bytes"] for x in common_inputs)
    for event_run, folder, receipt, inputs, path, item in work:
        planned_bytes += sum(x["bytes"] for x in inputs)
        planned_bytes += sum(x["bytes"] for x in receipt["files"]
                             if x["name"] in ("derived/wave.meta.json", "derived/wave.columns"))
        planned_bytes += sum(x["bytes"] for x in event_run["inputs"]
                             if x["role"] in ("existing_local_derived_summary", "frozen_observer"))
    if planned_bytes > MAX_BINARY_BATCH_BYTES:
        raise ValueError("Compact binaries plus consumed metadata exceed 32 MiB batch")
    runs = []
    for event_run, folder, receipt, inputs, path, item in work:
        run = event_run["run_id"]
        meta = json.loads(receipt_file(folder, receipt, "derived/wave.meta.json", inputs))
        names = receipt_file(folder, receipt, "derived/wave.columns", inputs).decode().splitlines()
        summary_input = next(x for x in event_run["inputs"] if x["role"] == "existing_local_derived_summary")
        summary = json.loads(read_small(ROOT / summary_input["path"], inputs, "existing_local_derived_summary",
                                        summary_input["sha256"]))
        if summary["run_id"] != run or len(summary["frames"]) != len(event_run["frames"]):
            raise ValueError("Prior case identity/frame-count mismatch")
        observer_input = next(x for x in event_run["inputs"] if x["role"] == "frozen_observer")
        observer = read_small(ROOT / observer_input["path"], inputs, "frozen_observer", observer_input["sha256"]).decode()
        band_match = re.search(r"rail_error\s*<\s*([0-9.]+)\s*\*\s*V\(VDD\)", observer)
        band = float(band_match[1]) if band_match else None
        if len(set(names)) != len(names) or len(names) != meta["columns"]:
            raise ValueError("Compact column metadata mismatch")
        if item["bytes"] != meta["points"] * len(names) * 8 or not meta["PSF_END"]:
            raise ValueError("Compact binary shape/end metadata mismatch")
        blob = path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        if digest != item["sha256"]:
            raise ValueError("Compact binary SHA256 mismatch")
        inputs.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest, bytes=len(blob),
                           role="collected:derived/wave.bin", expected_sha256_matches=True))
        matrix = np.frombuffer(blob, dtype="<f8").reshape((meta["points"], len(names)))
        required = ["time", "vdd!"] + ["d" + str(i) for i in range(8)]
        missing = [x for x in required if x not in names]
        if missing:
            frames = [dict(frame=f["frame"], **unavailable("Missing compact columns: " + ", ".join(missing)))
                      for f in event_run["frames"]]
        else:
            t = matrix[:, names.index("time")] * 1e9
            vdd = matrix[:, names.index("vdd!")]
            dout = matrix[:, [names.index("d" + str(i)) for i in range(8)]]
            frames = [frame_diagnostic(t, dout, vdd, f, old.get("expected"),
                        band_fraction=band, max_gap=grid_bound(summary))
                      for f, old in zip(event_run["frames"], summary["frames"])]
        runs.append(dict(run_id=run, input_hashes=inputs, compact_binary_bytes=item["bytes"],
            nominal_export_min_spacing_ps=summary.get("plot_estimate_spacing_ps"),
            provenance_derived_grid_gap_bound_ns=grid_bound(summary),
            band_fraction_from_legacy_observer=band,
            band_role="Strict +/-fraction*VDD around expected zero or VDD; old diagnostic, not VIL/VIH",
            missing_columns=missing, frames=frames))
        del matrix, blob
    payload = dict(schema_version=1, common_inputs=common_inputs, time_unit="ns",
        compact_binary_batch_bytes=binary_bytes, compact_binary_batch_limit_bytes=MAX_BINARY_BATCH_BYTES,
        total_consumed_evidence_bytes=planned_bytes,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope="Existing approximately 20 ps compact exports only; sampled-ready estimates, no raw PSF",
        unknowns=["No proof of intersample glitch absence", "No receiver VIL/VIH or setup/hold specification",
            "90/98 ns are historical observer times, not an approved silicon interface",
            "Matching the final word before final write does not qualify conversion completion"], runs=runs)
    output = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(output.encode()) > 1024 * 1024:
        raise ValueError("Output exceeds 1 MiB")
    (OWN / "dout_sampled.json").write_text(output, encoding="utf-8")
    print(json.dumps(dict(runs=len(runs), frames=sum(len(r["frames"]) for r in runs),
                         compact_binary_batch_bytes=binary_bytes, qualified_DOUT_valid_time_ns=None)))


if __name__ == "__main__":
    main()
