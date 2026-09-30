#!/usr/bin/env python3
"""Replace only ideal GMAIN hold relay with a T28 1.8-V NMOS in full CDAC."""

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
OUTPUT = ROOT / "output/bootstrap_t28_hold_pulldown"
MULTIPLIERS = (4, 16, 64)
INPUTS = (-0.8, -0.4, 0.0, 0.4, 0.8)
IDEAL_PROBE_FILE_HASH = "1341fa5e5b0bce5cef9a33202a6746325af32386ffe024ef1908f2fa7095b2fc"
# Same baseline deck after universal-newline normalization of the CRLF file.
IDEAL_PROBE_TEXT_HASH = "092e91a66c576af2874cd51cc6d2f97443f84ed904d9c6d36bbfe5b7e106c6f0"
HOLD_RELAY = (
    "    SHOLD (GMAIN VSS OFF_MAIN VSS) relay rclosed=1 ropen=1e12 "
    "vt1=0.3 vt2=0.6\n"
)


def deck(multi: int, vdiff: float) -> str:
    if multi not in MULTIPLIERS or vdiff not in INPUTS:
        raise ValueError("Unplanned device/input point")
    base = full.deck("ideal_clamp", vdiff, probe=True, off_bias="vss")
    if vdiff == 0.8 and hashlib.sha256(base.encode()).hexdigest() != IDEAL_PROBE_TEXT_HASH:
        raise ValueError("Previous ideal-control deck changed")
    if base.count(HOLD_RELAY) != 1:
        raise ValueError("Expected one ideal SHOLD relay")
    match = re.search(
        r"(?ms)^    MN7 \(G VDD GCLAMP VSS\) nch_18_mac\b.*?"
        r"(?=^    MN13 )", base)
    if match is None or match.group().count("multi=4") != 1:
        raise ValueError("Known 1.8-V PDK device geometry changed")
    device = (match.group()
              .replace("MN7 (G VDD GCLAMP VSS)",
                       "MN14 (GMAIN OFF_MAIN VSS VSS)", 1)
              .replace("multi=4", f"multi={multi}", 1))
    text = base.replace(HOLD_RELAY, device, 1)
    text = text.replace(
        "// Netlist-only full-CDAC ideal_clamp, "
        f"Vdiff={vdiff:+.3f} V, hold off bias=VSS; no OA modification",
        "// Netlist-only partial T28 GMAIN hold pull-down "
        f"multi={multi}, Vdiff={vdiff:+.3f} V; STRACK remains ideal")
    if text.count("MN14 (GMAIN OFF_MAIN VSS VSS) nch_18_mac") != 1:
        raise ValueError("Hold device substitution failed")
    return text + "save XBP.XB9P.MN14:currents XBP.XB9N.MN14:currents\n"


def analyze(data: dict[str, object], vdiff: float, log: Path) -> dict[str, object]:
    result = full.analyze(data, vdiff, log)
    waves = numeric(data)
    time = waves["time"]
    if len(time) < 25_000 or not np.isfinite(time).all() or not (np.diff(time) > 0).all():
        raise ValueError("Incomplete or nonmonotonic PSF time axis")
    for name, values in waves.items():
        if len(values) != len(time) or not np.isfinite(values).all():
            raise ValueError(f"Incomplete or nonfinite PSF signal: {name}")
    log_text = log.read_text(encoding="utf-8", errors="replace")
    suppressed = re.search(r"(\d+) warnings suppressed", log_text)
    result["warnings_suppressed"] = int(suppressed.group(1)) if suppressed else 0
    result["printed_cmi_instances"] = sorted(set(re.findall(
        r"WARNING \(CMI-\d+\): ([^:]+):", log_text)))

    def at(name: str, ns: float) -> float:
        if name not in waves:
            raise ValueError(f"Missing signal {name}")
        return float(np.interp(ns * 1e-9, waves["time"], waves[name]))

    def fall_below(name: str, threshold: float) -> float:
        t = waves["time"]
        v = waves[name]
        hits = np.flatnonzero((t >= 250.2e-9) & (t <= 251.3e-9)
                              & (v <= threshold))
        if not len(hits):
            raise ValueError(f"{name} did not fall below {threshold} V before reset")
        i = int(hits[0])
        if i == 0 or v[i - 1] <= threshold:
            return float(t[i] * 1e9)
        crossing = t[i - 1] + (t[i] - t[i - 1]) * (
            (v[i - 1] - threshold) / (v[i - 1] - v[i]))
        return float(crossing * 1e9)

    result["gmain_p_by_phase_v"] = {
        str(ns): at("xbp.xb9p.gmain", ns)
        for ns in (250.18, 250.34, 251.28, 252.4, 270.0)
    }
    result["gmain_n_by_phase_v"] = {
        str(ns): at("xbp.xb9n.gmain", ns)
        for ns in (250.18, 250.34, 251.28, 252.4, 270.0)
    }
    result["gmain_below_0p1_v_ns"] = {
        side: fall_below(f"xbp.xb9{side}.gmain", 0.1)
        for side in ("p", "n")
    }
    result["gmain_off_before_boot_reset_margin_ns"] = {
        side: 251.3 - result["gmain_below_0p1_v_ns"][side]
        for side in ("p", "n")
    }
    result["hold_device_drain_current_ua"] = {
        side: {str(ns): 1e6 * at(f"xbp.xb9{side}.mn14:1", ns)
               for ns in (250.34, 251.28, 252.4, 270.0)}
        for side in ("p", "n")
    }
    # Representative 1.8-V pull-down terminals: D=GMAIN, G=OFF_MAIN,
    # S=B=VSS. This is a diagnostic voltage comparison, not foundry SOA.
    active = (waves["time"] >= 200e-9) & (waves["time"] <= 285e-9)
    gate = waves["off_main"][active]
    result["hold_device_terminal_peaks_v"] = {
        side: {
            "vds": float(np.max(abs(waves[f"xbp.xb9{side}.gmain"][active]))),
            "vgs": float(np.max(abs(gate))),
            "vgd": float(np.max(abs(
                gate - waves[f"xbp.xb9{side}.gmain"][active]))),
        }
        for side in ("p", "n")
    }
    if "probe_currents_ua" not in result:
        raise ValueError("Missing MN11/reference/source current probe")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--multi", type=int, choices=MULTIPLIERS)
    parser.add_argument("--vdiff", type=float, choices=INPUTS, default=0.8)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    cases = (args.multi,) if args.multi is not None else MULTIPLIERS
    rows = []
    for multi in cases:
        name = f"m{multi}_vd{'m' if args.vdiff < 0 else 'p'}{abs(round(args.vdiff * 1000)):03d}"
        expected = deck(multi, args.vdiff)
        path = OUTPUT / "decks" / f"{name}.scs"
        path.parent.mkdir(parents=True, exist_ok=True)
        if args.analyze_only:
            if path.read_text(encoding="utf-8") != expected:
                raise ValueError(f"Generated deck changed: {name}")
            raw = OUTPUT / "spectre" / name / f"{name}.raw/tran.tran.tran"
            parsed = parse_spectre_psf_ascii(raw)
            if not parsed.ok:
                raise RuntimeError(f"PSF parse failed: {name}: {parsed.errors}")
            data = parsed.data
        else:
            path.write_text(expected, encoding="utf-8")
            result, data = run_spectre(path, args.profile, OUTPUT)
            if not result.ok or not data:
                raise RuntimeError(f"Spectre failed for {name}: "
                                   f"{result.status.value} {result.errors[:5]}")
        metrics = analyze(data, args.vdiff,
                          OUTPUT / "spectre" / name / "spectre.out")
        row = {
            "name": name,
            "multiplicity": multi,
            "per_finger_l_nm": 150,
            "per_finger_w_nm": 320,
            "vdiff_v": args.vdiff,
            "ideal_control_deck_sha256": IDEAL_PROBE_FILE_HASH if args.vdiff == 0.8 else None,
            "deck_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            **metrics,
        }
        (OUTPUT / f"{name}.json").write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8")
        rows.append(row)
        print(json.dumps({key: row[key] for key in (
            "name", "held_bottom_raw_error_mv", "b9_acquisition_error_mv",
            "printed_cmi_count")}), flush=True)
    if len(rows) > 1:
        summary = OUTPUT / f"summary_vd{'m' if args.vdiff < 0 else 'p'}{abs(round(args.vdiff * 1000)):03d}.json"
        summary.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
