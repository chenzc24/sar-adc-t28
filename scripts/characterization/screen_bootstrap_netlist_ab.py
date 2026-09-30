#!/usr/bin/env python3
"""Fast netlist-only A/B screen of full-control T28 bootstrap changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

from audit_bootstrap_current_paths import HASH, NODES, SOURCE, numeric
from run_bootstrap_protected_eval import run_spectre


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/bootstrap_netlist_fast_ab"
INTERNAL = ("G", "GCLAMP", "CTRL", "BTOP", "BBOT", "P1", "P2")
PAIRS = (("gs", "G", "S"), ("gd", "G", "D"), ("gb", "G", "B"),
         ("ds", "D", "S"), ("bs", "B", "S"), ("bd", "B", "D"))
LIMITS = {"nch_mac": 0.99, "pch_mac": 0.99,
          "nch_18_mac": 1.98, "pch_18_mac": 1.98}
VARIANTS = ("baseline", "body_vss_core", "body_vss_18", "early_phib",
            "body_vss_18_early", "body_vss_18_source_off_bound",
            "split_main_gate_bound", "split_main_gate_bound_early")


def source_text() -> str:
    raw = SOURCE.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != HASH:
        raise ValueError(f"OA export changed: {actual}")
    source = raw.decode("utf-8")
    for clause in ("MN9 (BBOT G VIN VIN) nch_mac",
                   "MN11 (VOUT G VIN VIN) nch_18_mac",
                   "MN12 (BBOT PHIB VSS VSS) nch_mac",
                   "RINP (VINP_SRC VINP) resistor r=50",
                   "RINN (VINN_SRC VINN) resistor r=50"):
        if source.count(clause) != 1:
            raise ValueError(f"Source contract changed: {clause}")
    return source


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Expected exactly one occurrence: {old}")
    return source.replace(old, new, 1)


def variant_source(base: str, variant: str) -> tuple[str, list[str]]:
    if variant not in VARIANTS:
        raise ValueError(variant)
    text = base
    edits = []
    if variant in {"body_vss_core", "body_vss_18", "body_vss_18_early",
                   "body_vss_18_source_off_bound", "split_main_gate_bound",
                   "split_main_gate_bound_early"}:
        text = replace_once(text, "MN9 (BBOT G VIN VIN) nch_mac",
                            "MN9 (BBOT G VIN VSS) nch_mac")
        edits.append("MN9 body VIN -> VSS")
    if variant in {"body_vss_18", "body_vss_18_early",
                   "body_vss_18_source_off_bound", "split_main_gate_bound",
                   "split_main_gate_bound_early"}:
        thick = re.search(r"(?ms)^    MN7 \(G VDD GCLAMP VSS\) nch_18_mac\b"
                          r".*?(?=^    MN13 )", base)
        thin = re.search(r"(?ms)^    MN9 \(BBOT G VIN VSS\) nch_mac\b"
                         r".*?(?=^    MN11 )", text)
        if thick is None or thin is None:
            raise ValueError("Cannot locate exact thick/thin PDK device statements")
        replacement = thick.group().replace(
            "MN7 (G VDD GCLAMP VSS)", "MN9 (BBOT G VIN VSS)", 1)
        text = text[:thin.start()] + replacement + text[thin.end():]
        edits.append("MN9 known 1.8-V PDK class and geometry")
    if variant in {"early_phib", "body_vss_18_early",
                   "split_main_gate_bound_early"}:
        text = replace_once(text, "rise=100p fall=100p width=41n",
                            "rise=100p fall=100p width=40.2n")
        edits.append("PHIB rising edge 251.0 -> 250.2 ns")
    if variant == "body_vss_18_source_off_bound":
        for name, successor in (("MN7", "MN13"), ("MN10", "MN12")):
            match = re.search(rf"(?ms)^    {name} \(.*?"
                              rf"(?=^    {successor} )", text)
            if match is None:
                raise ValueError(f"Cannot remove original {name} discharge device")
            text = text[:match.start()] + text[match.end():]
        text = replace_once(
            text, "    CBOOT (BTOP BBOT) capacitor c=200f",
            "    // Ideal source-relative off bound; not a T28 implementation\n"
            "    SOFF (G VIN PHIB VSS) relay rclosed=1 ropen=1e12 "
            "vt1=0.3 vt2=0.6\n"
            "    CBOOT (BTOP BBOT) capacitor c=200f")
        edits.append("MN7/MN10 ground clamp -> ideal PHIB relay G-to-VIN")
    if variant in {"split_main_gate_bound", "split_main_gate_bound_early"}:
        text = replace_once(text, "MN11 (VOUT G VIN VIN) nch_18_mac",
                            "MN11 (VOUT GMAIN VIN VIN) nch_18_mac")
        text = replace_once(
            text, "    CBOOT (BTOP BBOT) capacitor c=200f",
            "    // Ideal independent main-gate steering bound; not T28 switches\n"
            "    STRACK (GMAIN G PHI VSS) relay rclosed=1 ropen=1e12 "
            "vt1=0.3 vt2=0.6\n"
            "    SHOLD (GMAIN VIN PHIB VSS) relay rclosed=1 ropen=1e12 "
            "vt1=0.3 vt2=0.6\n"
            "    CBOOT (BTOP BBOT) capacitor c=200f")
        edits.append("MN11 independent GMAIN; ideal sample/hold relays")
    return text, edits


def deck(text: str, variant: str) -> str:
    text = replace_once(text, "saveOptions options save=allpub",
                        "saveOptions options save=selected")
    internal = tuple(node for node in INTERNAL
                     if variant != "body_vss_18_source_off_bound" or node != "GCLAMP")
    if variant in {"split_main_gate_bound", "split_main_gate_bound_early"}:
        internal += ("GMAIN",)
    nodes = sorted(set(NODES) | {f"{side}.{node}" for side in ("XP", "XN")
                                  for node in internal})
    currents = ("VSP", "VSN", "RINP", "RINN", "CLOADP", "CLOADN",
                "XP.MN9", "XN.MN9", "XP.MN11", "XN.MN11", "XP.MN12", "XN.MN12")
    return (text + f"\n// Netlist-only variant {variant}; no OA modification\n"
            + "tran tran stop=285n maxstep=5p errpreset=conservative\n"
            + f"save {' '.join(nodes)}\n"
            + f"save {' '.join(f'{name}:currents' for name in currents)}\n")


def mos_map(text: str) -> dict[str, dict[str, str]]:
    subckt = re.search(r"(?ms)^subckt sar_bootstrap_protected_full18_eval\b"
                        r".*?^ends sar_bootstrap_protected_full18_eval\s*$", text)
    if subckt is None:
        raise ValueError("DUT subcircuit missing")
    devices = {}
    for name, pins, model in re.findall(
            r"(?m)^\s+(M[NP]\d+) \(([^)]+)\) "
            r"(nch_mac|pch_mac|nch_18_mac|pch_18_mac)\b", subckt.group()):
        terminals = pins.split()
        if len(terminals) != 4 or name in devices:
            raise ValueError(f"MOS mapping malformed: {name}")
        devices[name] = dict(zip(("D", "G", "S", "B"), terminals)) | {"model": model}
    if len(devices) not in (10, 12):
        raise ValueError(f"Expected 10 or 12 DUT MOS devices, got {len(devices)}")
    return devices


def interp(waves: dict[str, np.ndarray], key: str, ns: float) -> float:
    return float(np.interp(ns * 1e-9, waves["time"], waves[key]))


def analyze(text: str, data: dict[str, object], variant: str,
            edits: list[str], log_path: Path) -> dict[str, object]:
    waves = numeric(data)
    time = waves["time"]
    for key in ("vinp", "vinn", "voutp", "voutn", "rinp:1", "rinn:1",
                "xp.mn9:1", "xp.mn9:4", "xp.mn11:1", "cloadp:1",
                "xn.mn11:1", "cloadn:1"):
        if key not in waves:
            raise ValueError(f"Missing waveform: {key}")
    devices = mos_map(text)

    def voltage(side: str, node: str) -> np.ndarray:
        if node == "VSS":
            return np.zeros_like(time)
        if node == "VDD":
            return np.full_like(time, 0.9)
        if node == "VIN":
            return waves["vinp" if side == "xp" else "vinn"]
        if node == "VOUT":
            return waves["voutp" if side == "xp" else "voutn"]
        if node in {"PHI", "PHIB"}:
            return waves[node.lower()]
        return waves[f"{side}.{node.lower()}"]

    active = (time >= 200e-9) & (time <= 285e-9)
    stress = []
    for side in ("xp", "xn"):
        for name, device in devices.items():
            for pair, pos, neg in PAIRS:
                values = voltage(side, device[pos]) - voltage(side, device[neg])
                peak = float(np.max(abs(values)))
                limit = LIMITS[device["model"]]
                if peak > limit:
                    stress.append({"side": side, "device": name,
                                   "model": device["model"], "pair": pair,
                                   "peak_abs_v": peak, "limit_v": limit})
    stress.sort(key=lambda row: row["peak_abs_v"] / row["limit_v"], reverse=True)

    checkpoints = []
    for ns in (249.8, 250.1, 250.2, 250.5, 251.0, 251.5, 270.0):
        vinp = interp(waves, "vinp", ns)
        vinn = interp(waves, "vinn", ns)
        voutp = interp(waves, "voutp", ns)
        voutn = interp(waves, "voutn", ns)
        checkpoints.append({
            "time_ns": ns, "input_diff_v": vinp - vinn,
            "vinp_v": vinp, "vinn_v": vinn,
            "output_diff_v": voutp - voutn,
            "raw_error_mv": 1e3 * (voutp - voutn - 0.8),
            "live_input_error_mv": 1e3 * (voutp - voutn - vinp + vinn),
            "rinp_ua": 1e6 * interp(waves, "rinp:1", ns),
            "rinn_ua": 1e6 * interp(waves, "rinn:1", ns),
            "mn9_body_p_ua": 1e6 * interp(waves, "xp.mn9:4", ns),
            "mn9_drain_p_ua": 1e6 * interp(waves, "xp.mn9:1", ns),
            "mn12_drain_p_ua": 1e6 * interp(waves, "xp.mn12:1", ns),
            "bbot_p_v": interp(waves, "xp.bbot", ns),
            "gate_p_v": interp(waves, "xp.g", ns),
            "gate_n_v": interp(waves, "xn.g", ns),
            "main_gate_p_v": interp(waves, "xp.gmain", ns)
            if "xp.gmain" in waves else interp(waves, "xp.g", ns),
            "main_gate_n_v": interp(waves, "xn.gmain", ns)
            if "xn.gmain" in waves else interp(waves, "xn.g", ns),
            "phi_v": interp(waves, "phi", ns),
            "phib_v": interp(waves, "phib", ns),
        })
    kcl_p = waves["xp.mn11:1"] + waves["cloadp:1"]
    kcl_n = waves["xn.mn11:1"] + waves["cloadn:1"]
    kcl_peak_na = 1e9 * max(float(np.max(abs(kcl_p[active]))),
                              float(np.max(abs(kcl_n[active]))))
    if kcl_peak_na > 0.001:
        raise ValueError(f"Output-node KCL failed: {kcl_peak_na} nA")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    cmi = re.findall(r"CMI-\d+", log)
    held = checkpoints[-1]
    source_drop_ua = (0.85 - held["vinp_v"]) / 50 * 1e6
    source_balance_na = 1e3 * abs(source_drop_ua - held["rinp_ua"])
    if source_balance_na > 0.1:
        raise ValueError(f"Input source/resistor balance failed: {source_balance_na} nA")
    return {
        "variant": variant, "edits": edits, "source_sha256": HASH,
        "variant_source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "signal_count": len(waves) - 1,
        "held_raw_error_mv": held["raw_error_mv"],
        "acquisition_error_mv": checkpoints[0]["raw_error_mv"],
        "held_input_source_current_p_ua": held["rinp_ua"],
        "held_input_source_drop_mv": 1e3 * (0.85 - held["vinp_v"]),
        "held_source_resistor_balance_error_na": source_balance_na,
        "held_mn9_body_current_p_ua": held["mn9_body_p_ua"],
        "held_mn12_drain_current_p_ua": held["mn12_drain_p_ua"],
        "output_kcl_peak_residual_na": kcl_peak_na,
        "stress_over_diagnostic_limit_count": len(stress),
        "stress_over_diagnostic_limit": stress[:12],
        "printed_cmi_warning_count": len(cmi),
        "checkpoints": checkpoints,
        "spectre_log": str(log_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--variant", choices=VARIANTS)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    base = source_text()
    variants = (args.variant,) if args.variant else VARIANTS
    summaries = []
    for variant in variants:
        modified, edits = variant_source(base, variant)
        deck_path = OUTPUT / "decks" / f"{variant}.scs"
        deck_path.parent.mkdir(parents=True, exist_ok=True)
        expected_deck = deck(modified, variant)
        if args.analyze_only:
            if deck_path.read_text(encoding="utf-8") != expected_deck:
                raise ValueError(f"Existing {variant} deck differs")
            wave = (OUTPUT / "spectre" / variant / f"{variant}.raw"
                    / "tran.tran.tran")
            parsed = parse_spectre_psf_ascii(wave)
            if not parsed.ok:
                raise RuntimeError(f"Cannot parse {wave}: {parsed.errors}")
            data = parsed.data
        else:
            deck_path.write_text(expected_deck, encoding="utf-8")
            result, data = run_spectre(deck_path, args.profile, OUTPUT)
            if not result.ok or not data:
                raise RuntimeError(f"{variant} Spectre failed: {result.status.value}"
                                   f" {result.errors[:5]}")
        log_path = OUTPUT / "spectre" / variant / "spectre.out"
        summary = analyze(modified, data, variant, edits, log_path)
        summary["analysis_deck_sha256"] = hashlib.sha256(
            deck_path.read_bytes()).hexdigest()
        summary_path = OUTPUT / f"{variant}.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n",
                                encoding="utf-8")
        summaries.append(summary)
        print(json.dumps({key: summary[key] for key in (
            "variant", "held_raw_error_mv", "held_input_source_current_p_ua",
            "stress_over_diagnostic_limit_count", "printed_cmi_warning_count")}),
            flush=True)
    if len(summaries) > 1:
        (OUTPUT / "summary.json").write_text(
            json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
