#!/usr/bin/env python3
"""Measure turn-off currents on the exact full-control bootstrap OA export."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

from run_bootstrap_protected_eval import run_spectre


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "output/bootstrap_protected_eval/full18/netlist"
          / "tb_sar_bootstrap_protected_full18_eval/input.scs")
OUTPUT = ROOT / "output/bootstrap_current_path_audit"
HASH = "f466793e8655f2d81bdb7ce98d1041f00cdd90a374be3341750d2cb22a9bdd4d"
NODES = ("PHI", "PHIB", "VINP_SRC", "VINN_SRC", "VINP", "VINN",
         "VOUTP", "VOUTN", "XP.G", "XN.G", "XP.BBOT", "XN.BBOT",
         "XP.BTOP", "XN.BTOP", "XP.CTRL", "XN.CTRL")
CURRENT_INSTANCES = ("VSP", "VSN", "RINP", "RINN", "CLOADP", "CLOADN",
                     "XP.MN9", "XN.MN9", "XP.MN11", "XN.MN11",
                     "XP.MP8", "XN.MP8", "XP.MN7", "XN.MN7",
                     "XP.MN10", "XN.MN10")
TIMES_NS = (249.8, 250.1, 250.5, 251.0, 251.2, 251.3, 251.5, 252.0, 270.0)


def exact_source() -> str:
    raw = SOURCE.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != HASH:
        raise ValueError(f"Exact OA export changed: {actual}")
    text = raw.decode("utf-8")
    for statement in (
        "MN9 (BBOT G VIN VIN) nch_mac",
        "MN11 (VOUT G VIN VIN) nch_18_mac",
        "RINP (VINP_SRC VINP) resistor r=50",
        "RINN (VINN_SRC VINN) resistor r=50",
        "VSP (VINP_SRC 0) vsource type=pulse val0=50m val1=850m",
        "XP (PHI PHIB VDD VINP VOUTP 0) sar_bootstrap_protected_full18_eval",
        "XN (PHI PHIB VDD VINN VOUTN 0) sar_bootstrap_protected_full18_eval",
    ):
        if statement not in text:
            raise ValueError(f"OA source contract missing: {statement}")
    return text


def deck(source: str) -> str:
    setting = "saveOptions options save=allpub"
    if source.count(setting) != 1:
        raise ValueError("Source saveOptions contract changed")
    voltage_saves = " ".join(NODES)
    current_saves = " ".join(f"{name}:currents" for name in CURRENT_INSTANCES)
    return (
        source.replace(setting, "saveOptions options save=selected", 1)
        + "\n// Analysis-only waveform probe; OA devices and connections unchanged\n"
        + "tran tran stop=285n maxstep=5p errpreset=conservative\n"
        + f"save {voltage_saves}\n"
        + f"save {current_saves}\n"
    )


def numeric(data: dict[str, object]) -> dict[str, np.ndarray]:
    # The bridge's PSF-ASCII parser also returns a repeated metadata field
    # named "units"; it is not a waveform and has a different length.
    arrays = {key.strip('"').lower(): np.asarray(values, dtype=float)
              for key, values in data.items() if key.lower() != "units"}
    time = arrays["time"]
    if len(time) < 1000 or not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError("Invalid transient time base")
    if any(len(values) != len(time) or not np.all(np.isfinite(values))
           for values in arrays.values()):
        raise ValueError("Invalid or misaligned waveform")
    return arrays


def at(waves: dict[str, np.ndarray], key: str, ns: float) -> float:
    return float(np.interp(ns * 1e-9, waves["time"], waves[key]))


def charge_fc(waves: dict[str, np.ndarray], key: str,
              start_ns: float, stop_ns: float) -> float:
    time = waves["time"]
    lo, hi = start_ns * 1e-9, stop_ns * 1e-9
    inside = (time > lo) & (time < hi)
    times = np.concatenate(([lo], time[inside], [hi]))
    current = np.interp(times, time, waves[key])
    return float(np.trapezoid(current, times) * 1e15)


def preliminary(data: dict[str, object]) -> dict[str, object]:
    waves = numeric(data)
    t = waves["time"]
    checkpoints = []
    for ns in TIMES_NS:
        index = int(np.argmin(abs(t - ns * 1e-9)))
        vip, vin = waves["vinp"][index], waves["vinn"][index]
        vop, von = waves["voutp"][index], waves["voutn"][index]
        checkpoints.append({
            "time_ns": float(t[index] * 1e9),
            "input_diff_v": float(vip - vin),
            "output_diff_v": float(vop - von),
            "error_vs_ideal_mv": float(1e3 * (vop - von - 0.8)),
            "error_vs_live_input_mv": float(1e3 * (vop - von - vip + vin)),
            "vinp_v": float(vip), "vinn_v": float(vin),
            "mn9_p_vbd_v": float(vip - waves["xp.bbot"][index]),
            "mn9_n_vbd_v": float(vin - waves["xn.bbot"][index]),
            "gate_p_v": float(waves["xp.g"][index]),
            "gate_n_v": float(waves["xn.g"][index]),
            "rinp_ua": float(1e6 * waves["rinp:1"][index]),
            "rinn_ua": float(1e6 * waves["rinn:1"][index]),
            "cloadp_ua": float(1e6 * waves["cloadp:1"][index]),
            "cloadn_ua": float(1e6 * waves["cloadn:1"][index]),
            "xp_mn9_terminals_ua": [float(1e6 * waves[f"xp.mn9:{n}"][index])
                                      for n in range(1, 5)],
            "xn_mn9_terminals_ua": [float(1e6 * waves[f"xn.mn9:{n}"][index])
                                      for n in range(1, 5)],
            "xp_mn11_terminals_ua": [float(1e6 * waves[f"xp.mn11:{n}"][index])
                                       for n in range(1, 5)],
            "xn_mn11_terminals_ua": [float(1e6 * waves[f"xn.mn11:{n}"][index])
                                       for n in range(1, 5)],
        })
    phases = []
    for start, stop in ((250.1, 251.0), (251.0, 251.5), (251.5, 270.0)):
        dvoutp = at(waves, "voutp", stop) - at(waves, "voutp", start)
        dvoutn = at(waves, "voutn", stop) - at(waves, "voutn", start)
        phases.append({
            "start_ns": start, "stop_ns": stop,
            "delta_voutp_mv": 1e3 * dvoutp,
            "delta_voutn_mv": 1e3 * dvoutn,
            "delta_vout_diff_mv": 1e3 * (dvoutp - dvoutn),
            "rinp_charge_fc": charge_fc(waves, "rinp:1", start, stop),
            "mn9_p_body_charge_fc": charge_fc(waves, "xp.mn9:4", start, stop),
            "mn9_p_drain_charge_fc": charge_fc(waves, "xp.mn9:1", start, stop),
            "mn11_p_drain_charge_fc": charge_fc(waves, "xp.mn11:1", start, stop),
            "cloadp_charge_fc": charge_fc(waves, "cloadp:1", start, stop),
            "cloadn_charge_fc": charge_fc(waves, "cloadn:1", start, stop),
            "cloadp_expected_fc": 219.5 * dvoutp,
            "cloadn_expected_fc": 219.5 * dvoutn,
        })
    segment = (t >= 249.8e-9) & (t <= 270e-9)
    kcl_p = waves["xp.mn11:1"][segment] + waves["cloadp:1"][segment]
    kcl_n = waves["xn.mn11:1"][segment] + waves["cloadn:1"][segment]
    return {"oa_export_sha256": HASH,
            "saved_signal_count": len(waves) - 1,
            "saved_current_signal_names": sorted(k for k in waves if ":" in k),
            "checkpoints": checkpoints,
            "phases": phases,
            "output_node_kcl_peak_residual_na": {
                "p": float(1e9 * np.max(abs(kcl_p))),
                "n": float(1e9 * np.max(abs(kcl_n))),
            }}


def validate(summary: dict[str, object]) -> None:
    last = summary["checkpoints"][-1]
    source_current_ua = (0.85 - last["vinp_v"]) / 50.0 * 1e6
    if abs(last["rinp_ua"] - source_current_ua) > 0.001:
        raise ValueError("High-side resistor voltage/current mismatch")
    mn9 = last["xp_mn9_terminals_ua"]
    if abs(last["rinp_ua"] + mn9[0]) > 0.001 or abs(sum(mn9)) > 0.001:
        raise ValueError("High-side MN9/input current balance failed")
    if any(value > 0.001 for value in
           summary["output_node_kcl_peak_residual_na"].values()):
        raise ValueError("Output-node KCL mismatch")
    for phase in summary["phases"]:
        for side in ("p", "n"):
            if abs(phase[f"cload{side}_charge_fc"] -
                   phase[f"cload{side}_expected_fc"]) > 0.01:
                raise ValueError(f"{side}-side load charge mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    source = exact_source()
    out_deck = OUTPUT / "decks/bootstrap_current_paths.scs"
    if not args.analyze_only:
        out_deck.parent.mkdir(parents=True, exist_ok=True)
        out_deck.write_text(deck(source), encoding="utf-8")
        result, data = run_spectre(out_deck, args.profile, OUTPUT)
        if not result.ok or not data:
            raise RuntimeError(f"Spectre did not complete: {result.status.value} {result.errors[:5]}")
    else:
        wave = OUTPUT / "spectre/bootstrap_current_paths/bootstrap_current_paths.raw/tran.tran.tran"
        parsed = parse_spectre_psf_ascii(wave)
        if not parsed.ok:
            raise RuntimeError(f"Cannot read {wave}: {parsed.errors}")
        data = parsed.data
    summary = preliminary(data)
    validate(summary)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "preliminary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(path),
                      "saved_signals": summary["saved_signal_count"],
                      "currents": summary["saved_current_signal_names"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
