#!/usr/bin/env python3
"""Reconstruct bootstrap MOS terminal stress from an exact OA export and run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/bootstrap_driver_design/netlist/tb_sar_bootstrap_transient/input.scs"
RUN = ROOT / "output/bootstrap_driver_error_reduction/smoke_baseline/run_summary.json"
OUTPUT = ROOT / "output/bootstrap_soa_map"
EXPECTED_SHA256 = "f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c"
EXPECTED_DEVICES = {
    "MN1", "MN2", "MN3", "MN5", "MN7", "MN9", "MN10", "MN11", "MN12", "MN13", "MP4", "MP8",
}
PAIRS = {"Vgs": ("G", "S"), "Vgd": ("G", "D"), "Vgb": ("G", "B"),
         "Vds": ("D", "S"), "Vbs": ("B", "S"), "Vbd": ("B", "D")}


def device_map(source: str) -> dict[str, dict[str, str]]:
    match = re.search(r"(?ms)^subckt sar_bootstrap\b.*?^ends sar_bootstrap\s*$", source)
    if not match:
        raise ValueError("Exact OA sar_bootstrap definition missing")
    found: dict[str, dict[str, str]] = {}
    for name, terminals, model in re.findall(
        r"(?m)^    (M[NP]\d+) \(([^)]+)\) (nch_mac|pch_mac)\b", match.group()
    ):
        nodes = terminals.split()
        if len(nodes) != 4 or name in found:
            raise ValueError(f"Ambiguous MOS terminals for {name}: {terminals}")
        found[name] = dict(zip(("D", "G", "S", "B"), nodes)) | {"model": model}
    if set(found) != EXPECTED_DEVICES:
        raise ValueError(f"OA MOS inventory changed: {sorted(set(found) ^ EXPECTED_DEVICES)}")
    return found


def waveform(signals: dict[str, np.ndarray], node: str, side: str,
             count: int, supply: float) -> np.ndarray:
    if node == "VSS":
        return np.zeros(count)
    if node == "VDD":
        return np.full(count, supply)
    key = {"VIN": f"VIN{side}", "VOUT": f"VOUT{side}"}.get(node)
    if key is None:
        key = node if node in ("PHI", "PHIB") else f"XB{side}.{node}"
    if key not in signals:
        raise ValueError(f"Required OA terminal net {side}/{node} not saved as {key}")
    return signals[key]


def peak(time: np.ndarray, values: np.ndarray, mask: np.ndarray,
         limit: float) -> dict[str, float]:
    t, v = time[mask], values[mask]
    idx = int(np.argmax(np.abs(v)))
    above = (np.abs(v) > limit).astype(float)
    approximate_ns = float(np.sum((t[1:] - t[:-1]) * (above[1:] + above[:-1]) / 2) * 1e9)
    return {"peak_abs_v": float(abs(v[idx])), "signed_at_peak_v": float(v[idx]),
            "time_ns": float(t[idx] * 1e9), "sampled_above_limit_ns": approximate_ns}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != EXPECTED_SHA256:
        raise ValueError(f"OA export SHA-256 mismatch: {source_hash}")
    devices = device_map(source_bytes.decode("utf-8"))
    run = json.loads(args.run.read_text(encoding="utf-8"))
    if run["oa_export_sha256"] != source_hash or run["case_count"] != 1:
        raise ValueError("Run does not match exact OA export or single-case contract")
    record = run["records"][0]
    if record["name"] != "screen_baseline_vdp800" or not record["spectre_ok"]:
        raise ValueError("Expected successful baseline +0.8-V differential run")
    if not any("CMI-275" in warning for warning in record["warnings"]):
        raise ValueError("Retained Spectre SOA warnings are missing")

    signals = {name: np.asarray(samples, dtype=float)
               for name, samples in record["signals"].items()}
    time = signals["time"]
    if time.size < 1000 or not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError("Invalid transient time base")
    if any(array.size != time.size or not np.all(np.isfinite(array))
           for array in signals.values()):
        raise ValueError("Saved waveforms missing, misaligned, or non-finite")
    supply = float(run["configuration"]["conditions"]["supply_v"])
    limit = 0.99  # Nominal PDK log warning level, not an approved transient SOA rule.
    driven = (time >= 200e-9) & (time <= 285e-9)
    if np.count_nonzero(driven) < 1000:
        raise ValueError("Driven-cycle waveform is incomplete")

    rows: list[dict[str, object]] = []
    lookup: dict[tuple[str, str, str], dict[str, object]] = {}
    for side in ("P", "N"):
        for device, mapping in devices.items():
            terminal = {pin: waveform(signals, node, side, time.size, supply)
                        for pin, node in mapping.items() if pin != "model"}
            for pair, (positive, negative) in PAIRS.items():
                values = terminal[positive] - terminal[negative]
                row: dict[str, object] = {"side": side, "device": device,
                                          "model": mapping["model"], "pair": pair,
                                          "positive_net": mapping[positive],
                                          "negative_net": mapping[negative],
                                          "full": peak(time, values, np.ones(time.size, dtype=bool), limit),
                                          "driven": peak(time, values, driven, limit)}
                rows.append(row)
                lookup[(side, device, pair)] = row
    if len(rows) != 2 * len(devices) * len(PAIRS):
        raise ValueError("Incomplete side/device/terminal-pair coverage")

    warning_pattern = re.compile(
        r"XB([PN])\.(M[NP]\d+): (Vgs|Vgd|Vgb|Vds|Vbs|Vbd)\(=([+-]?[\d.]+)\s*(m?V)\)"
    )
    witnesses = []
    for warning in record["warnings"]:
        match = warning_pattern.search(warning)
        if not match:
            continue
        side, device, pair, printed, unit = match.groups()
        observed = abs(float(printed)) * (1e-3 if unit == "mV" else 1.0)
        reconstructed = lookup[(side, device, pair)]["full"]["peak_abs_v"]
        witnesses.append({"warning": warning, "observed_v": observed,
                          "reconstructed_full_peak_v": reconstructed,
                          "within_20mv": reconstructed + 0.02 >= observed})
    if not witnesses or not all(item["within_20mv"] for item in witnesses):
        raise ValueError("Saved-waveform terminal reconstruction disagrees with SOA log")

    ranking = sorted(rows, key=lambda row: row["driven"]["peak_abs_v"], reverse=True)
    summary = {"oa_export_sha256": source_hash, "run_case": record["name"],
               "spectre_ok": True, "temperature_c": 27, "supply_v": supply,
               "input_differential_v": 0.8, "screen_level_v": limit,
               "screen_is_not_foundry_signoff": True,
               "time_window_ns": [200.0, 285.0],
               "device_count_per_side": len(devices), "metric_count": len(rows),
               "warning_witness_count": len(witnesses),
               "warning_witnesses": witnesses, "ranked_metrics": ranking}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                encoding="utf-8")
    with (args.output / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["side", "device", "model", "pair", "positive_net", "negative_net",
                  "full_peak_abs_v", "full_signed_at_peak_v", "full_time_ns",
                  "driven_peak_abs_v", "driven_signed_at_peak_v", "driven_time_ns",
                  "driven_sampled_above_limit_ns"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in ranking:
            writer.writerow({"side": row["side"], "device": row["device"],
                             "model": row["model"], "pair": row["pair"],
                             "positive_net": row["positive_net"],
                             "negative_net": row["negative_net"],
                             "full_peak_abs_v": row["full"]["peak_abs_v"],
                             "full_signed_at_peak_v": row["full"]["signed_at_peak_v"],
                             "full_time_ns": row["full"]["time_ns"],
                             "driven_peak_abs_v": row["driven"]["peak_abs_v"],
                             "driven_signed_at_peak_v": row["driven"]["signed_at_peak_v"],
                             "driven_time_ns": row["driven"]["time_ns"],
                             "driven_sampled_above_limit_ns":
                                 row["driven"]["sampled_above_limit_ns"]})
    print(json.dumps({"devices_per_side": len(devices), "metrics": len(rows),
                      "warning_witnesses": len(witnesses),
                      "top_driven": ranking[:8]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
