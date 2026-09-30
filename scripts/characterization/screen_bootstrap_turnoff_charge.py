#!/usr/bin/env python3
"""Single-factor Spectre screen of charge transfer at MN11 turn-off."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

import screen_bootstrap_netlist_ab as ab
import test_bootstrap_isolate_before_reset as isolated
from audit_bootstrap_current_paths import charge_fc, numeric
from run_bootstrap_protected_eval import run_spectre


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/bootstrap_turnoff_charge_screen"
CASES = {
    "edge_50ps": ("50p", 50, "219.5f", 219.5, "1", 1),
    "edge_100ps_load_219p5f": ("100p", 100, "219.5f", 219.5, "1", 1),
    "edge_300ps": ("300p", 300, "219.5f", 219.5, "1", 1),
    "edge_600ps": ("600p", 600, "219.5f", 219.5, "1", 1),
    "load_109p75f": ("100p", 100, "109.75f", 109.75, "1", 1),
    "load_439f": ("100p", 100, "439f", 439.0, "1", 1),
    "hold_1kohm": ("100p", 100, "219.5f", 219.5, "1k", 1000),
    "hold_5kohm": ("100p", 100, "219.5f", 219.5, "5k", 5000),
    "hold_20kohm": ("100p", 100, "219.5f", 219.5, "20k", 20000),
}
START_NS = 250.18
END_NS = 251.28  # before PHIB reset at 251.3 ns


def variant(case: str) -> tuple[str, str, int, float, int]:
    edge, edge_ps, load, load_ff, hold, hold_ohm = CASES[case]
    source, reset_ns, challenge = isolated.controlled_source("reset_gap_1ns")
    if reset_ns != 251.3 or challenge:
        raise ValueError("Unexpected isolation control contract")
    source = ab.replace_once(
        source,
        "VOFFMAIN (OFF_MAIN 0) vsource type=pulse val0=900m val1=0 "
        "period=100n delay=10n rise=100p fall=100p width=40.2n",
        "VOFFMAIN (OFF_MAIN 0) vsource type=pulse val0=900m val1=0 "
        f"period=100n delay=10n rise=100p fall={edge} width=40.2n",
    )
    if load != "219.5f":
        for side in ("N", "P"):
            source = ab.replace_once(
                source, f"CLOAD{side} (VOUT{side} 0) capacitor c=219.5f",
                f"CLOAD{side} (VOUT{side} 0) capacitor c={load}",
            )
    if hold != "1":
        source = ab.replace_once(
            source,
            "SHOLD (GMAIN VIN OFF_MAIN VSS) relay rclosed=1 ropen=1e12",
            f"SHOLD (GMAIN VIN OFF_MAIN VSS) relay rclosed={hold} ropen=1e12",
        )
    deck = isolated.deck(source, "reset_gap_1ns")
    deck = ab.replace_once(
        deck, "// Independent OFF_MAIN / PHIB reset timing case reset_gap_1ns",
        f"// Single-factor turn-off charge screen case {case}",
    )
    return source, deck, edge_ps, load_ff, hold_ohm


def analyze(source: str, data: dict[str, object], case: str,
            edge_ps: int, load_ff: float, hold_ohm: int,
            log_path: Path) -> dict[str, object]:
    summary = ab.analyze(source, data, case,
                         ["OFF_MAIN return-edge/load screen"], log_path)
    waves = numeric(data)

    def at(name: str, ns: float) -> float:
        return float(np.interp(ns * 1e-9, waves["time"], waves[name]))

    def diff(name: str, ns: float) -> float:
        return at(f"{name}p", ns) - at(f"{name}n", ns)

    def gate_transition_ps(side: str) -> float | None:
        time_ns = waves["time"] * 1e9
        gate = waves[f"x{side}.gmain"]
        start = at(f"x{side}.gmain", START_NS)
        target = at(f"vin{side}", END_NS)
        if start <= target:
            raise ValueError(f"GMAIN did not start boosted on {side}: {start}, {target}")
        window = np.flatnonzero((time_ns >= START_NS) & (time_ns <= END_NS))

        def crossing(fraction: float) -> float | None:
            threshold = target + fraction * (start - target)
            reached = window[gate[window] <= threshold]
            if len(reached) == 0:
                return None
            i = int(reached[0])
            if i == 0:
                raise ValueError(f"Invalid GMAIN crossing on {side}: {fraction}")
            return float(np.interp(threshold, [gate[i], gate[i - 1]],
                                   [time_ns[i], time_ns[i - 1]]))

        t90, t10 = crossing(0.9), crossing(0.1)
        return 1e3 * (t10 - t90) if t90 is not None and t10 is not None else None

    per_side = {}
    for side in ("p", "n"):
        delta_mv = 1e3 * (at(f"vout{side}", END_NS)
                           - at(f"vout{side}", START_NS))
        load_charge_fc = charge_fc(waves, f"cload{side}:1",
                                   START_NS, END_NS)
        mn11_charge_fc = charge_fc(waves, f"x{side}.mn11:1",
                                   START_NS, END_NS)
        expected_fc = load_ff * delta_mv * 1e-3  # fF*mV = 0.001 fC
        per_side[side] = {
            "output_step_mv": delta_mv,
            "mn11_drain_charge_fc": mn11_charge_fc,
            "load_current_charge_fc": load_charge_fc,
            "c_delta_v_fc": expected_fc,
            "charge_balance_residual_fc": mn11_charge_fc + load_charge_fc,
            "load_c_delta_v_residual_fc": load_charge_fc - expected_fc,
            "gmain_pre_off_v": at(f"x{side}.gmain", START_NS),
            "gmain_pre_reset_v": at(f"x{side}.gmain", END_NS),
            "gmain_pre_reset_minus_vin_mv": 1e3 * (
                at(f"x{side}.gmain", END_NS) - at(f"vin{side}", END_NS)),
            "gmain_90_to_10_ps": gate_transition_ps(side),
        }
    if any(abs(row["charge_balance_residual_fc"]) > 0.003
           or abs(row["load_c_delta_v_residual_fc"])
           > max(0.02, 0.01 * abs(row["c_delta_v_fc"]))
           for row in per_side.values()):
        raise ValueError(f"Charge balance failed: {case}: {per_side}")
    summary.update({
        "off_main_fall_ps": edge_ps,
        "per_side_load_ff": load_ff,
        "hold_relay_rclosed_ohm": hold_ohm,
        "integration_window_ns": [START_NS, END_NS],
        "acquisition_error_mv": 1e3 * (diff("vout", 249.8) - 0.8),
        "pre_off_error_mv": 1e3 * (diff("vout", START_NS) - 0.8),
        "pre_reset_error_mv": 1e3 * (diff("vout", END_NS) - 0.8),
        "turnoff_diff_step_mv": 1e3 * (diff("vout", END_NS)
                                      - diff("vout", START_NS)),
        "post_reset_error_mv": 1e3 * (diff("vout", 251.8) - 0.8),
        "per_side": per_side,
    })
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    cases = (args.case,) if args.case else tuple(CASES)
    rows = []
    for case in cases:
        source, expected, edge_ps, load_ff, hold_ohm = variant(case)
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
        summary = analyze(source, data, case, edge_ps, load_ff, hold_ohm,
                          log_path)
        summary["analysis_deck_sha256"] = hashlib.sha256(
            deck_path.read_bytes()).hexdigest()
        (OUTPUT / f"{case}.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        rows.append(summary)
        print(json.dumps({key: summary[key] for key in (
            "variant", "off_main_fall_ps", "per_side_load_ff",
            "hold_relay_rclosed_ohm",
            "turnoff_diff_step_mv", "pre_reset_error_mv",
            "held_raw_error_mv", "printed_cmi_warning_count")}), flush=True)
    if len(rows) > 1:
        (OUTPUT / "summary.json").write_text(
            json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
