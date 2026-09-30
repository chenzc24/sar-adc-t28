"""Copied-netlist dynamic-G-rail PGATE driver; external clocks stay ideal."""
from __future__ import annotations

import argparse
import hashlib
import json
import re

import numpy as np

import screen_top_plate_gmain_hold_device as prior

OUTPUT = prior.ROOT / "output/top_plate_pgate_driver"
# D G S B; all new devices use exported thick-oxide geometry.
PINS = {
    "MP15": ("PGATE", "PGATEB", "G", "G"),
    "MP16": ("PGATEB", "PGATE", "G", "G"),
    "MN15": ("PGATE", "OFF_MAIN", "VSS", "VSS"),
    "MN16": ("PGATEB", "OFFB", "VSS", "VSS"),
    "MP17": ("OFFB", "OFF_MAIN", "VDD", "VDD"),
    "MN17": ("OFFB", "OFF_MAIN", "VSS", "VSS"),
}


def deck(vdiff: float, ratio: int) -> str:
    if ratio not in (1, 4, 8):
        raise ValueError("Unplanned driver strength ratio")
    text = prior.deck("tg_hold_m4", vdiff)
    templates = {}
    for kind, pattern in (
        ("N", r"(?ms)^    MN7 \(G VDD GCLAMP VSS\) nch_18_mac\b.*?(?=^    MN13 )"),
        ("P", r"(?ms)^    MP4 \(CTRL PHI VDD VDD\) pch_18_mac\b.*?(?=^    MN9 )"),
    ):
        match = re.search(pattern, text)
        if not match or match.group().count("multi=4") != 1:
            raise ValueError("Exported device template changed")
        templates[kind] = match.group()
    devices = []
    for name, pins in PINS.items():
        device = re.sub(r"^    M\w+ \([^)]*\)",
                        f"    {name} ({' '.join(pins)})", templates[name[1]])
        multi = ratio if name in ("MN15", "MN16") else 1
        devices.append(device.replace("multi=4", f"multi={multi}", 1))
    for relay in ("SPTRACK", "SPHOLD"):
        text, count = re.subn(rf"(?m)^    {relay} .*\n", "", text)
        if count != 1:
            raise ValueError("Expected ideal PGATE steering relay")
    text = prior.replace_once(text, "    MN14 (", "".join(devices) + "    MN14 (")
    text += "\n// Real PGATE dynamic-rail level shifter; STRACK/external clocks ideal\n"
    text += "save VDD " + " ".join(
        f"XTOPBOOT_{s}.{node}" for s in ("P", "N")
        for node in ("G", "PGATEB", "OFFB")) + "\n"
    text += "save " + " ".join(
        f"XTOPBOOT_{s}.{dev}:currents" for s in ("P", "N") for dev in PINS) + "\n"
    assert "SPTRACK (" not in text and "SPHOLD (" not in text
    return text


def analyze(data, log, vdiff):
    if "spectre completes with 0 errors," not in log.read_text(
            encoding="utf-8", errors="replace"):
        raise ValueError("No zero-error Spectre completion in this run log")
    result = prior.analyze(data, log, "tg_hold_m4", vdiff)
    waves = prior.numeric(data)
    time = waves["time"]

    def signal(node, side):
        if node == "VSS":
            return np.zeros_like(time)
        key = node.lower() if node in ("VDD", "OFF_MAIN") else f"xtopboot_{side}.{node.lower()}"
        return waves[key]

    result["driver"] = {}
    for side in ("p", "n"):
        entry = {}
        for ns in (249.7, 250.18, 250.34, 251.28, 251.8, 270.0):
            entry[str(ns)] = {node: float(np.interp(ns * 1e-9, time, signal(node, side)))
                              for node in ("G", "GMAIN", "PGATE", "PGATEB", "OFFB")}
        entry["terminal_peaks_full_run_v"] = {}
        entry["peak_drain_current_full_run_ua"] = {}
        entry["peak_forward_drain_body_v"] = {}
        entry["forward_drain_body_peak_time_ns"] = {}
        for dev, pins in PINS.items():
            vals = [signal(node, side) for node in pins]
            entry["terminal_peaks_full_run_v"][dev] = {
                "DGSB"[i] + "DGSB"[j]: float(np.max(abs(vals[i] - vals[j])))
                for i in range(4) for j in range(i + 1, 4)}
            entry["peak_drain_current_full_run_ua"][dev] = float(
                np.max(abs(waves[f"xtopboot_{side}.{dev.lower()}:1"])) * 1e6)
            forward = vals[0] - vals[3] if dev[1] == "P" else vals[3] - vals[0]
            entry["peak_forward_drain_body_v"][dev] = float(max(0.0, np.max(forward)))
            entry["forward_drain_body_peak_time_ns"][dev] = float(time[np.argmax(forward)] * 1e9)
        off_window = (time >= 250.4e-9) & (time <= 251.28e-9)
        violations = np.flatnonzero(off_window & (abs(signal("PGATE", side)) > 0.01))
        entry["pgate_last_above_10mv_before_reset_ns"] = (
            float(time[violations[-1]] * 1e9) if len(violations) else None)
        result["driver"][side] = entry
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vdiff", type=float, choices=prior.INPUTS, required=True)
    parser.add_argument("--ratio", type=int, choices=(1, 4, 8), default=4)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    name = f"pgate_n{args.ratio}p1_vd{'m' if args.vdiff < 0 else 'p'}{abs(round(args.vdiff*1000)):03d}"
    path = OUTPUT / "decks" / f"{name}.scs"
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = deck(args.vdiff, args.ratio)
    if args.analyze_only:
        if path.read_text(encoding="utf-8") != expected:
            raise ValueError("Simulated deck differs from generator")
        parsed = prior.parse_spectre_psf_ascii(
            OUTPUT / "spectre" / name / f"{name}.raw/tran.tran.tran")
        if not parsed.ok:
            raise RuntimeError(f"PSF parse failed: {parsed.errors}")
        data = parsed.data
    else:
        path.write_text(expected, encoding="utf-8")
        sim, data = prior.run_spectre(path, "t28_io", OUTPUT)
        if not sim.ok or not data:
            raise RuntimeError(f"Spectre failed: {sim.status.value} {sim.errors[:5]}")
    row = {"name": name, "vdiff_v": args.vdiff, "ratio": args.ratio,
           "deck_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
           "oa_export_sha256": prior.full.SOURCES["ideal_clamp"][1],
           **analyze(data, OUTPUT / "spectre" / name / "spectre.out", args.vdiff)}
    (OUTPUT / f"{name}.json").write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: row[key] for key in ("name", "held_top_raw_error_mv",
          "printed_cmi_count", "warnings_suppressed")}), flush=True)


if __name__ == "__main__":
    main()
