#!/usr/bin/env python3
"""Test independent main-switch turn-off before bootstrap reset in Spectre."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

import screen_bootstrap_netlist_ab as ab
from audit_bootstrap_current_paths import numeric
from run_bootstrap_protected_eval import run_spectre


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/bootstrap_isolate_before_reset"
# Widths are measured from PHIB's low-going edge at 210 ns (and repeated
# every 100 ns); the 250-ns cycle is the one used for measurements.
CASES = {
    "reset_same": ("40.2n", 250.2, False),
    "reset_gap_100ps": ("40.4n", 250.4, False),
    "reset_gap_300ps": ("40.6n", 250.6, False),
    "reset_gap_1ns": ("41.3n", 251.3, False),
    "reset_gap_1ns_input_step": ("41.3n", 251.3, True),
    "reset_suppressed": ("80n", None, False),
}


def controlled_source(case: str) -> tuple[str, float | None, bool]:
    width, reset_ns, challenge = CASES[case]
    base = ab.source_text()
    text, _ = ab.variant_source(base, "split_main_gate_bound_early")
    text = ab.replace_once(
        text,
        "subckt sar_bootstrap_protected_full18_eval PHI PHIB VDD VIN VOUT VSS",
        "subckt sar_bootstrap_protected_full18_eval PHI PHIB OFF_MAIN "
        "VDD VIN VOUT VSS")
    text = ab.replace_once(
        text, "XN (PHI PHIB VDD VINN VOUTN 0)",
        "XN (PHI PHIB OFF_MAIN VDD VINN VOUTN 0)")
    text = ab.replace_once(
        text, "XP (PHI PHIB VDD VINP VOUTP 0)",
        "XP (PHI PHIB OFF_MAIN VDD VINP VOUTP 0)")
    text = ab.replace_once(
        text, "SHOLD (GMAIN VIN PHIB VSS) relay",
        "SHOLD (GMAIN VIN OFF_MAIN VSS) relay")
    if width != "40.2n":
        text = ab.replace_once(text, "rise=100p fall=100p width=40.2n",
                               f"rise=100p fall=100p width={width}")
    text = ab.replace_once(
        text, "VPHI (PHI 0) vsource",
        "VOFFMAIN (OFF_MAIN 0) vsource type=pulse val0=900m val1=0 "
        "period=100n delay=10n rise=100p fall=100p width=40.2n\n"
        "VPHI (PHI 0) vsource")
    if challenge:
        text = ab.replace_once(
            text,
            "VSP (VINP_SRC 0) vsource type=pulse val0=50m val1=850m period=400n \\\n"
            "        delay=205n rise=100p fall=100p width=80n",
            "VSP (VINP_SRC 0) vsource type=pwl wave=[0 50m 205n 50m "
            "205.1n 850m 250.50n 850m 250.51n 860m 250.70n 860m "
            "250.71n 850m 285n 850m]")
        text = ab.replace_once(
            text,
            "VSN (VINN_SRC 0) vsource type=pulse val0=850m val1=50m period=400n \\\n"
            "        delay=205n rise=100p fall=100p width=80n",
            "VSN (VINN_SRC 0) vsource type=pwl wave=[0 850m 205n 850m "
            "205.1n 50m 250.50n 50m 250.51n 40m 250.70n 40m "
            "250.71n 50m 285n 50m]")
    if len(ab.mos_map(text)) != 12:
        raise ValueError("DUT MOS map changed unexpectedly")
    return text, reset_ns, challenge


def deck(source: str, case: str) -> str:
    text = ab.deck(source, "split_main_gate_bound_early")
    text = ab.replace_once(
        text, "// Netlist-only variant split_main_gate_bound_early",
        f"// Independent OFF_MAIN / PHIB reset timing case {case}")
    return text + "save OFF_MAIN\n"


def at(waves: dict[str, np.ndarray], key: str, ns: float) -> float:
    return float(np.interp(ns * 1e-9, waves["time"], waves[key]))


def metrics(data: dict[str, object], reset_ns: float | None,
            challenge: bool) -> dict[str, object]:
    waves = numeric(data)

    def output_diff(ns: float) -> float:
        return at(waves, "voutp", ns) - at(waves, "voutn", ns)

    def input_diff(ns: float) -> float:
        return at(waves, "vinp", ns) - at(waves, "vinn", ns)

    pre_ns = reset_ns - 0.02 if reset_ns is not None else 251.28
    post_ns = reset_ns + 0.5 if reset_ns is not None else 251.8
    before = output_diff(pre_ns)
    after = output_diff(post_ns)
    gap_valid = reset_ns is not None and reset_ns >= 250.4
    result = {
        "off_main_rise_start_ns": 250.2,
        "off_main_rise_complete_ns": 250.3,
        "boot_reset_rise_start_ns": reset_ns,
        "isolation_to_reset_gap_ns": (reset_ns - 250.3)
        if reset_ns is not None else None,
        "reset_window_pre_ns": pre_ns,
        "reset_window_post_ns": post_ns,
        "reset_window_is_separable": gap_valid,
        "reset_window_delta_output_diff_mv": 1e3 * (after - before),
        "output_error_at_250p10_mv": 1e3 * (output_diff(250.10) - 0.8),
        "output_error_at_250p32_mv": 1e3 * (output_diff(250.32) - 0.8),
        "output_error_pre_reset_mv": 1e3 * (before - 0.8),
        "output_error_post_reset_mv": 1e3 * (after - 0.8),
        "main_gate_p_pre_reset_v": at(waves, "xp.gmain", pre_ns),
        "main_gate_n_pre_reset_v": at(waves, "xn.gmain", pre_ns),
        "mn11_p_drain_current_pre_reset_ua":
            1e6 * at(waves, "xp.mn11:1", pre_ns),
        "mn11_n_drain_current_pre_reset_ua":
            1e6 * at(waves, "xn.mn11:1", pre_ns),
        "input_diff_pre_reset_v": input_diff(pre_ns),
        "input_diff_post_reset_v": input_diff(post_ns),
        "phib_pre_reset_v": at(waves, "phib", pre_ns),
        "off_main_pre_reset_v": at(waves, "off_main", pre_ns),
        "boot_bbot_p_pre_reset_v": at(waves, "xp.bbot", pre_ns),
        "boot_bbot_p_post_reset_v": at(waves, "xp.bbot", post_ns),
        "input_delta_250p48_to_250p60_mv": 1e3 * (
            input_diff(250.60) - input_diff(250.48)),
        "output_delta_250p48_to_250p60_mv": 1e3 * (
            output_diff(250.60) - output_diff(250.48)),
    }
    if gap_valid:
        lo = 250.33e-9
        hi = pre_ns * 1e-9
        region = (waves["time"] >= lo) & (waves["time"] <= hi)
        if not np.any(region):
            raise ValueError("Missing off-before-reset waveform region")
        result["mn11_p_peak_abs_current_in_gap_ua"] = float(
            1e6 * np.max(abs(waves["xp.mn11:1"][region])))
        result["mn11_n_peak_abs_current_in_gap_ua"] = float(
            1e6 * np.max(abs(waves["xn.mn11:1"][region])))
    if challenge:
        result["input_step_diff_mv"] = 1e3 * (
            input_diff(250.60) - input_diff(250.48))
        result["output_step_diff_mv"] = 1e3 * (
            output_diff(250.60) - output_diff(250.48))
        result["output_recovered_diff_mv"] = 1e3 * (
            output_diff(250.75) - output_diff(250.48))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    cases = (args.case,) if args.case else tuple(CASES)
    summaries = []
    for case in cases:
        source, reset_ns, challenge = controlled_source(case)
        expected = deck(source, case)
        deck_path = OUTPUT / "decks" / f"{case}.scs"
        deck_path.parent.mkdir(parents=True, exist_ok=True)
        if args.analyze_only:
            if deck_path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"Generated deck changed: {case}")
            wave = OUTPUT / "spectre" / case / f"{case}.raw/tran.tran.tran"
            parsed = parse_spectre_psf_ascii(wave)
            if not parsed.ok:
                raise RuntimeError(f"PSF parse failed: {case}: {parsed.errors}")
            data = parsed.data
        else:
            deck_path.write_text(expected, encoding="utf-8")
            result, data = run_spectre(deck_path, args.profile, OUTPUT)
            if not result.ok or not data:
                raise RuntimeError(f"Spectre failed for {case}: "
                                   f"{result.status.value} {result.errors[:5]}")
        log_path = OUTPUT / "spectre" / case / "spectre.out"
        summary = ab.analyze(source, data, case,
                             ["independent OFF_MAIN and PHIB reset"], log_path)
        summary.update(metrics(data, reset_ns, challenge))
        summary["analysis_deck_sha256"] = hashlib.sha256(
            deck_path.read_bytes()).hexdigest()
        (OUTPUT / f"{case}.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        summaries.append(summary)
        print(json.dumps({key: summary[key] for key in (
            "variant", "boot_reset_rise_start_ns", "held_raw_error_mv",
            "reset_window_delta_output_diff_mv", "held_input_source_current_p_ua",
            "printed_cmi_warning_count")}), flush=True)
    if len(summaries) > 1:
        (OUTPUT / "summary.json").write_text(
            json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
