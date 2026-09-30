#!/usr/bin/env python3
"""Screen T28 GMAIN-to-VIN hold devices in the top-plate path only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

import run_bootstrap_full_cdac_isolation as full
from audit_bootstrap_current_paths import numeric
from run_bootstrap_protected_eval import run_spectre


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/top_plate_gmain_first_device"
INPUTS = (-0.8, -0.4, 0.0, 0.4, 0.8)
VARIANTS = ("ideal_hold", "nmos_hold_m4", "pmos_hold_m4",
            "tg_hold_m1", "tg_hold_m2", "tg_hold_m4")
PRIOR_TOP_ONLY_SOURCE_HASH = (
    "ae4158b6fc0290b70913b7b3358b444dfda00e43f7efa882526186997ca3ec53"
)
HOLD_RELAY = (
    "    SHOLD (GMAIN VIN OFF_MAIN VSS) relay rclosed=1 ropen=1e12 "
    "vt1=0.3 vt2=0.6\n"
)
TOP_SAVES = (
    "PHI PHIB OFF_MAIN BASE VINP_TOP VINN_TOP TOPP_TOP TOPN_TOP "
    "XTOPBOOT_P.GMAIN XTOPBOOT_N.GMAIN"
)
CURRENT_SAVES = (
    "RINP_TOP:currents RINN_TOP:currents "
    "XTOPBOOT_P.MN11:currents XTOPBOOT_N.MN11:currents"
)
CHECKPOINTS_NS = (249.7, 250.18, 250.34, 251.28, 251.8, 252.4, 270.0)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected one bounded deck statement: {old[:70]}")
    return text.replace(old, new, 1)


def deck(variant: str, vdiff: float) -> str:
    if variant not in VARIANTS or vdiff not in INPUTS:
        raise ValueError("Unplanned variant/input point")
    text = full.deck("ideal_clamp", vdiff, off_bias="vin")
    if vdiff == 0.8 and hashlib.sha256(text.encode()).hexdigest() != PRIOR_TOP_ONLY_SOURCE_HASH:
        raise ValueError("The exact prior full-CDAC top-plate source changed")
    if text.count(HOLD_RELAY) != 1 or text.count("XTOPBOOT_P (") != 1:
        raise ValueError("Top-plate bootstrap/control contract changed")

    # Remove the *instance* of the old bottom-plate comparison fixture.
    # Its uninstantiated subcircuit definition can remain without loading.
    text, count = re.subn(
        r"(?ms)^XBP \(.*?\) sar_cdac_bottom_plate_eval_10b\n", "", text)
    if count != 1:
        raise ValueError("Expected one removable bottom-plate fixture")
    if "XBP (" in text:
        raise ValueError("Bottom-plate fixture still active")
    for name in ("VVN_BP", "VVP_BP"):
        text, count = re.subn(rf"(?ms)^{name} \(.*?width=80n\n", "", text)
        if count != 1:
            raise ValueError(f"Expected one {name} stimulus")
    for name in ("RPROBEN", "RPROBEP", "RINN_BP", "RINP_BP"):
        text, count = re.subn(rf"(?m)^{name} .*\n", "", text)
        if count != 1:
            raise ValueError(f"Expected one {name} auxiliary branch")

    text = replace_once(text, f"save {full.SAVES}\n", f"save {TOP_SAVES}\n")
    text = replace_once(
        text,
        f"// Netlist-only full-CDAC ideal_clamp, Vdiff={vdiff:+.3f} V; no OA modification",
        f"// Top-plate-only GMAIN hold screen {variant}, Vdiff={vdiff:+.3f} V; no OA edit",
    )
    if variant == "nmos_hold_m4":
        match = re.search(
            r"(?ms)^    MN7 \(G VDD GCLAMP VSS\) nch_18_mac\b.*?"
            r"(?=^    MN13 )", text)
        if match is None or match.group().count("multi=4") != 1:
            raise ValueError("Known T28 1.8-V NMOS geometry changed")
        device = match.group().replace(
            "MN7 (G VDD GCLAMP VSS)",
            "MN14 (GMAIN OFF_MAIN VIN VIN)", 1,
        )
        text = replace_once(text, HOLD_RELAY, device)
        text += "save XTOPBOOT_P.MN14:currents XTOPBOOT_N.MN14:currents\n"
    elif variant == "pmos_hold_m4" or variant.startswith("tg_hold_m"):
        multi = int(variant.rsplit("m", 1)[1]) if variant.startswith("tg_hold_m") else 4
        match = re.search(
            r"(?ms)^    MP4 \(CTRL PHI VDD VDD\) pch_18_mac\b.*?"
            r"(?=^    MN9 )", text)
        if match is None or match.group().count("multi=4") != 1:
            raise ValueError("Known T28 1.8-V PMOS geometry changed")
        device = match.group().replace(
            "MP4 (CTRL PHI VDD VDD)",
            "MP14 (GMAIN PGATE VIN GMAIN)", 1,
        ).replace("multi=4", f"multi={multi}", 1)
        text = replace_once(
            text, HOLD_RELAY,
            "    SPTRACK (PGATE G PHI VSS) relay rclosed=1 ropen=1e12 "
            "vt1=0.3 vt2=0.6\n"
            "    SPHOLD (PGATE VSS OFF_MAIN VSS) relay rclosed=1 "
            "ropen=1e12 vt1=0.3 vt2=0.6\n" + device,
        )
        if variant.startswith("tg_hold_m"):
            nmatch = re.search(
                r"(?ms)^    MN7 \(G VDD GCLAMP VSS\) nch_18_mac\b.*?"
                r"(?=^    MN13 )", text)
            if nmatch is None or nmatch.group().count("multi=4") != 1:
                raise ValueError("Known T28 NMOS geometry changed")
            ndevice = nmatch.group().replace(
                "MN7 (G VDD GCLAMP VSS)",
                "MN14 (GMAIN OFF_MAIN VIN VIN)", 1,
            ).replace("multi=4", f"multi={multi}", 1)
            text = replace_once(text, device, ndevice + device)
            text += "save XTOPBOOT_P.MN14:currents XTOPBOOT_N.MN14:currents\n"
        text += (
            "save XTOPBOOT_P.MP14:currents XTOPBOOT_N.MP14:currents "
            "XTOPBOOT_P.PGATE XTOPBOOT_N.PGATE\n"
        )
    else:
        if text.count(HOLD_RELAY) != 1:
            raise ValueError("Ideal top-plate baseline relay missing")
    return text + f"save {CURRENT_SAVES}\n"


def analyze(data: dict[str, object], log_path: Path,
            variant: str, vdiff: float) -> dict[str, object]:
    waves = numeric(data)
    time = waves["time"]
    if len(time) < 25_000 or not np.isfinite(time).all() or not (np.diff(time) > 0).all():
        raise ValueError("Incomplete or nonmonotonic PSF time axis")
    for name, values in waves.items():
        if len(values) != len(time) or not np.isfinite(values).all():
            raise ValueError(f"Incomplete or nonfinite PSF signal: {name}")

    def at(name: str, ns: float) -> float:
        if name not in waves:
            raise ValueError(f"Missing signal {name}")
        return float(np.interp(ns * 1e-9, time, waves[name]))

    if not (at("phi", 250.18) < 0.3 and at("off_main", 250.18) < 0.3
            and at("phib", 251.28) < 0.3 and at("off_main", 251.28) > 0.6
            and at("phib", 251.8) > 0.6 and at("base", 252.4) > 0.6):
        raise ValueError("GMAIN-off, BOOT-reset, reference phase order failed")

    checkpoints = []
    for ns in CHECKPOINTS_NS:
        top_diff = at("topp_top", ns) - at("topn_top", ns)
        checkpoints.append({
            "time_ns": ns,
            "top_diff_v": top_diff,
            "top_raw_error_mv": 1e3 * (top_diff - vdiff),
            "gmain_p_v": at("xtopboot_p.gmain", ns),
            "gmain_n_v": at("xtopboot_n.gmain", ns),
            "vinp_v": at("vinp_top", ns),
            "vinn_v": at("vinn_top", ns),
            "off_main_v": at("off_main", ns),
        })
    log = log_path.read_text(encoding="utf-8", errors="replace")
    suppressed = re.search(r"(\d+) warnings suppressed", log)
    result: dict[str, object] = {
        "held_top_raw_error_mv": checkpoints[-1]["top_raw_error_mv"],
        "top_preoff_error_mv": checkpoints[1]["top_raw_error_mv"],
        "top_prereset_error_mv": checkpoints[3]["top_raw_error_mv"],
        "top_postreset_error_mv": checkpoints[4]["top_raw_error_mv"],
        "gmain_minus_vin_270_mv": {
            side: 1e3 * (at(f"xtopboot_{side}.gmain", 270.0)
                         - at(f"vin{side}_top", 270.0))
            for side in ("p", "n")
        },
        "mn11_drain_current_270_ua": {
            side: 1e6 * at(f"xtopboot_{side}.mn11:1", 270.0)
            for side in ("p", "n")
        },
        "source_resistor_current_270_ua": {
            side: 1e6 * at(f"rin{side}_top:1", 270.0)
            for side in ("p", "n")
        },
        "printed_cmi_count": len(re.findall(r"WARNING \(CMI-\d+\)", log)),
        "printed_cmi_instances": sorted(set(re.findall(
            r"WARNING \(CMI-\d+\): ([^:]+):", log))),
        "warnings_suppressed": int(suppressed.group(1)) if suppressed else 0,
        "printed_warning_lines": [line.strip() for line in log.splitlines()
                                  if "WARNING (" in line][:16],
        "checkpoints": checkpoints,
    }
    if variant != "ideal_hold":
        active = (time >= 200e-9) & (time <= 285e-9)
        devices = ("mn14", "mp14") if variant.startswith("tg_hold_m") else (
            ("mn14",) if variant == "nmos_hold_m4" else ("mp14",))
        result["hold_device_drain_current_270_ua"] = {
            device: {side: 1e6 * at(f"xtopboot_{side}.{device}:1", 270.0)
                     for side in ("p", "n")}
            for device in devices
        }
        result["hold_device_terminal_peaks_v"] = {}
        for device in devices:
            peaks = {}
            for side in ("p", "n"):
                gate = waves["off_main" if device == "mn14"
                             else f"xtopboot_{side}.pgate"][active]
                gmain = waves[f"xtopboot_{side}.gmain"][active]
                vin = waves[f"vin{side}_top"][active]
                peaks[side] = {
                    "vds": float(np.max(abs(gmain - vin))),
                    "vgs": float(np.max(abs(gate - vin))),
                    "vgd": float(np.max(abs(gate - gmain))),
                }
            result["hold_device_terminal_peaks_v"][device] = peaks
        if variant == "pmos_hold_m4" or variant.startswith("tg_hold_m"):
            result["pgate_by_phase_v"] = {
                side: {str(ns): at(f"xtopboot_{side}.pgate", ns)
                       for ns in (249.7, 251.28, 270.0)}
                for side in ("p", "n")
            }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--vdiff", type=float, choices=INPUTS, required=True)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    name = (f"{args.variant}_vd{'m' if args.vdiff < 0 else 'p'}"
            f"{abs(round(args.vdiff * 1000)):03d}")
    expected = deck(args.variant, args.vdiff)
    path = OUTPUT / "decks" / f"{name}.scs"
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.analyze_only:
        if path.read_text(encoding="utf-8") != expected:
            raise ValueError("Generated deck changed since simulation")
        raw = OUTPUT / "spectre" / name / f"{name}.raw/tran.tran.tran"
        parsed = parse_spectre_psf_ascii(raw)
        if not parsed.ok:
            raise RuntimeError(f"PSF parse failed: {parsed.errors}")
        data = parsed.data
    else:
        path.write_text(expected, encoding="utf-8")
        result, data = run_spectre(path, args.profile, OUTPUT)
        if not result.ok or not data:
            raise RuntimeError(f"Spectre failed: {result.status.value} {result.errors[:5]}")
    metrics = analyze(data, OUTPUT / "spectre" / name / "spectre.out",
                      args.variant, args.vdiff)
    row = {
        "name": name,
        "variant": args.variant,
        "vdiff_v": args.vdiff,
        "oa_export_sha256": full.SOURCES["ideal_clamp"][1],
        "deck_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        **metrics,
    }
    (OUTPUT / f"{name}.json").write_text(
        json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: row[key] for key in (
        "name", "held_top_raw_error_mv", "gmain_minus_vin_270_mv",
        "printed_cmi_count", "warnings_suppressed")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
