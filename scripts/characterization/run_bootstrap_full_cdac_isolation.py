#!/usr/bin/env python3
"""Screen protected bootstrap turn-off in the exact exported full CDAC."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

import screen_bootstrap_netlist_ab as ab
import test_bootstrap_isolate_before_reset as isolated
from audit_bootstrap_current_paths import numeric
from run_bootstrap_protected_eval import run_spectre


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output/bootstrap_full_cdac_isolation"
SOURCES = {
    "ideal_clamp": (
        ROOT / "output/bootstrap_bottom_plate_eval/netlist/"
        "tb_sar_bottom_plate_eval/input.scs",
        "965cbc2f99712c0f5d72af0eefcf28abdf398340f31cff32d96a0e1fd36e50ac",
        "sar_cdac_bottom_plate_eval_10b",
    ),
    "t28_clamp": (
        ROOT / "output/bootstrap_bottom_plate_eval/t28_clamp/netlist/"
        "tb_sar_bottom_plate_t28clamp_eval/input.scs",
        "02c8ffc923915c279c1a316a1984e8cb677e6c3be06147a822f9d42aa36944ef",
        "sar_cdac_bottom_plate_t28clamp_eval_10b",
    ),
}
INPUTS = (-0.8, -0.4, 0.0, 0.4, 0.8)
SAVES = (
    "PHI PHIB OFF_MAIN CLAMP BASE VINP_BP VINN_BP VINP_TOP VINN_TOP "
    "TOPP_BP TOPN_BP TOPP_TOP TOPN_TOP XBP.B9P XBP.B9N "
    "XBP.XB9P.GMAIN XBP.XB9N.GMAIN XBP.XB9P.BBOT "
    "XTOPBOOT_P.GMAIN XTOPBOOT_N.GMAIN"
)
PROBE_SAVES = (
    "RINP_BP:currents RINN_BP:currents "
    "XBP.XB9P.MN11:currents XBP.XB9N.MN11:currents "
    "XBP.S9P0:currents XBP.S9N0:currents "
    "XBP.C9P:currents XBP.C9N:currents"
)
TIMES_NS = (249.3, 249.48, 249.7, 250.18, 250.34, 251.28,
            251.8, 251.95, 252.4, 270.0)


def exact_source(kind: str) -> tuple[str, str]:
    path, expected, cdac = SOURCES[kind]
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError(f"OA export hash changed: {path}: {actual}")
    text = raw.decode("utf-8")
    if text.count(") sar_bootstrap\n") != 24:
        raise ValueError("Expected 22 bottom and 2 top bootstrap calls")
    if f"subckt {cdac} BASE CLAMP PHI PHIB" not in text:
        raise ValueError("CDAC formal-port contract changed")
    return text, cdac


def protected_subckt(off_bias: str = "vin") -> str:
    source, reset_ns, challenge = isolated.controlled_source("reset_gap_1ns")
    if reset_ns != 251.3 or challenge:
        raise ValueError("Protected bootstrap source contract changed")
    match = re.search(
        r"(?ms)^subckt sar_bootstrap_protected_full18_eval\b.*?"
        r"^ends sar_bootstrap_protected_full18_eval$", source)
    if match is None:
        raise ValueError("Protected bootstrap subcircuit missing")
    block = match.group().replace("sar_bootstrap_protected_full18_eval",
                                  "sar_bootstrap")
    if block.count("SHOLD (GMAIN VIN OFF_MAIN VSS) relay") != 1:
        raise ValueError("Independent GMAIN relay missing")
    if off_bias == "vss":
        block = ab.replace_once(
            block, "SHOLD (GMAIN VIN OFF_MAIN VSS) relay",
            "SHOLD (GMAIN VSS OFF_MAIN VSS) relay")
    elif off_bias != "vin":
        raise ValueError(off_bias)
    if len(ab.mos_map(source)) != 12:
        raise ValueError("Protected MOS-device map changed")
    return block


def deck(kind: str, vdiff: float, probe: bool = False,
         off_bias: str = "vin") -> str:
    text, cdac = exact_source(kind)
    old = re.search(r"(?ms)^subckt sar_bootstrap\b.*?^ends sar_bootstrap$",
                    text)
    if old is None or text.count("subckt sar_bootstrap ") != 1:
        raise ValueError("Original bootstrap definition changed")
    text = text[:old.start()] + protected_subckt(off_bias) + text[old.end():]

    # All 22 bottom bootstrap instances plus both top-plate references.
    call = "(PHI PHIB VDD "
    if text.count(call) != 24:
        raise ValueError(f"Expected 24 bootstrap calls, got {text.count(call)}")
    text = text.replace(call, "(PHI PHIB OFF_MAIN VDD ")
    text = ab.replace_once(
        text, f"subckt {cdac} BASE CLAMP PHI PHIB",
        f"subckt {cdac} BASE CLAMP PHI PHIB OFF_MAIN")
    text = ab.replace_once(
        text, "XBP (BASE CLAMP PHI PHIB BASE",
        "XBP (BASE CLAMP PHI PHIB OFF_MAIN BASE")
    text = ab.replace_once(
        text, "rise=100p fall=100p width=41n",
        "rise=100p fall=100p width=41.3n")
    text = ab.replace_once(
        text, "VPHI (PHI 0) vsource",
        "VOFFMAIN (OFF_MAIN 0) vsource type=pulse val0=900m val1=0 "
        "period=100n delay=10n rise=100p fall=100p width=40.2n\n"
        "VPHI (PHI 0) vsource")

    vinp, vinn = 0.45 + vdiff / 2, 0.45 - vdiff / 2
    params = (f"parameters vinp_target={vinp:.12g} "
              f"vinn_target={vinn:.12g} clamp_delay=11n "
              f"clamp_width=38.5n\n")  # 211 to 249.5 ns
    text = ab.replace_once(
        text, "parameters vinp_target vinn_target clamp_delay clamp_width\n",
        params)
    text = ab.replace_once(text, "saveOptions options save=allpub",
                           "saveOptions options save=selected")
    comment = (f"// Netlist-only full-CDAC {kind}, Vdiff={vdiff:+.3f} V; "
               "no OA modification" if off_bias == "vin" else
               f"// Netlist-only full-CDAC {kind}, Vdiff={vdiff:+.3f} V, "
               "hold off bias=VSS; no OA modification")
    return (text + f"\n{comment}\n"
            "tran tran stop=285n maxstep=10p errpreset=conservative\n"
            f"save {SAVES}\n"
            + (f"save {PROBE_SAVES}\n" if probe else ""))


def analyze(data: dict[str, object], vdiff: float,
            log_path: Path) -> dict[str, object]:
    waves = numeric(data)

    def at(name: str, ns: float) -> float:
        if name not in waves:
            raise ValueError(f"Missing saved signal {name}")
        return float(np.interp(ns * 1e-9, waves["time"], waves[name]))

    def delta(p: str, n: str, ns: float) -> float:
        return at(p, ns) - at(n, ns)

    if not (at("phi", 250.18) < 0.3 and at("off_main", 250.18) < 0.3
            and at("phib", 251.28) < 0.3 and at("off_main", 251.28) > 0.6
            and at("phib", 251.8) > 0.6 and at("base", 251.95) < 0.3
            and at("base", 252.4) > 0.6):
        raise ValueError("Off/reset/reference phase order failed")
    checkpoints = []
    for ns in TIMES_NS:
        top = delta("topp_top", "topn_top", ns)
        bottom = delta("topp_bp", "topn_bp", ns)
        checkpoints.append({
            "time_ns": ns,
            "top_diff_v": top,
            "bottom_top_diff_v": bottom,
            "top_error_mv": 1e3 * (top - vdiff),
            "bottom_oracle_gap_mv": 1e3 * (-bottom - vdiff),
            "bottom_input_diff_v": delta("vinp_bp", "vinn_bp", ns),
            "bottom_b9_diff_v": delta("xbp.b9p", "xbp.b9n", ns),
            "clamp_v": at("clamp", ns),
            "off_main_v": at("off_main", ns),
            "phib_v": at("phib", ns),
            "base_v": at("base", ns),
        })
    log = log_path.read_text(encoding="utf-8", errors="replace")
    return {
        "held_top_raw_error_mv": checkpoints[-1]["top_error_mv"],
        "held_bottom_raw_error_mv": checkpoints[-1]["bottom_oracle_gap_mv"],
        "b9_acquisition_error_mv": 1e3 * (
            checkpoints[0]["bottom_b9_diff_v"] - vdiff),
        "bottom_preoff_top_diff_v": checkpoints[3]["bottom_top_diff_v"],
        "bottom_prereset_top_diff_v": checkpoints[5]["bottom_top_diff_v"],
        "bottom_postreset_top_diff_v": checkpoints[6]["bottom_top_diff_v"],
        "bottom_main_off_top_step_mv": 1e3 * (
            checkpoints[5]["bottom_top_diff_v"]
            - checkpoints[3]["bottom_top_diff_v"]),
        "bottom_reset_top_step_mv": 1e3 * (
            checkpoints[6]["bottom_top_diff_v"]
            - checkpoints[5]["bottom_top_diff_v"]),
        "bottom_postreference_raw_error_mv": checkpoints[8][
            "bottom_oracle_gap_mv"],
        "bottom_b9_postreference_diff_v": checkpoints[8]["bottom_b9_diff_v"],
        "bottom_held_input_diff_v": checkpoints[-1]["bottom_input_diff_v"],
        "bottom_hold_common_mode_v": 0.5 * (
            at("topp_bp", 270) + at("topn_bp", 270)),
        "representative_gmain_p_preoff_v": at("xbp.xb9p.gmain", 250.18),
        "representative_gmain_p_prereset_v": at("xbp.xb9p.gmain", 251.28),
        "representative_bbot_p_prereset_v": at("xbp.xb9p.bbot", 251.28),
        "gmain_p_minus_b9_p_270_mv": 1e3 * (
            at("xbp.xb9p.gmain", 270) - at("xbp.b9p", 270)),
        "gmain_n_minus_b9_n_270_mv": 1e3 * (
            at("xbp.xb9n.gmain", 270) - at("xbp.b9n", 270)),
        "gmain_p_minus_vinp_270_mv": 1e3 * (
            at("xbp.xb9p.gmain", 270) - at("vinp_bp", 270)),
        "vinp_bp_270_v": at("vinp_bp", 270),
        "vinn_bp_270_v": at("vinn_bp", 270),
        "printed_cmi_count": len(re.findall(r"CMI-\d+", log)),
        "printed_sfe_1131_count": log.count("SFE-1131"),
        "spectre_warning_lines": [line.strip() for line in log.splitlines()
                                  if "WARNING (" in line][:12],
        "checkpoints": checkpoints,
    } | ({
        "probe_currents_ua": {
            name: {str(ns): 1e6 * at(name, ns) for ns in (251.28, 252.4, 270.0)}
            for name in (
                "rinp_bp:1", "rinn_bp:1", "xbp.xb9p.mn11:1",
                "xbp.xb9n.mn11:1", "xbp.s9p0:1", "xbp.s9n0:1",
                "xbp.c9p:1", "xbp.c9n:1")
        }
    } if "xbp.xb9p.mn11:1" in waves else {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--kind", choices=SOURCES)
    parser.add_argument("--vdiff", type=float)
    parser.add_argument("--probe", action="store_true",
                        help="Save representative MN11/reference currents")
    parser.add_argument("--off-bias", choices=("vin", "vss"), default="vin")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    if args.probe and (args.kind != "ideal_clamp" or args.vdiff != 0.8):
        parser.error("--probe requires --kind ideal_clamp --vdiff 0.8")
    cases = [(kind, v) for kind in SOURCES for v in INPUTS
             if (kind == "ideal_clamp" or abs(v) == 0.8)
             and (args.kind is None or kind == args.kind)
             and (args.vdiff is None or abs(v - args.vdiff) < 1e-12)]
    rows = []
    for kind, vdiff in cases:
        name = f"{kind}_vd{'m' if vdiff < 0 else 'p'}{abs(round(vdiff * 1000)):03d}"
        if args.off_bias == "vss":
            name += "_offvss"
        if args.probe:
            name += "_probe"
        expected = deck(kind, vdiff, args.probe, args.off_bias)
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
        metrics = analyze(data, vdiff, OUTPUT / "spectre" / name / "spectre.out")
        row = {"name": name, "kind": kind, "vdiff_v": vdiff,
               "off_bias": args.off_bias,
               "oa_export_sha256": SOURCES[kind][1],
               "protected_source_sha256": ab.HASH,
               "deck_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               **metrics}
        (OUTPUT / f"{name}.json").write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8")
        rows.append(row)
        print(json.dumps({key: row[key] for key in (
            "name", "held_top_raw_error_mv", "held_bottom_raw_error_mv",
            "b9_acquisition_error_mv", "printed_cmi_count")}), flush=True)
    if len(rows) > 1:
        summary_name = f"summary_{args.off_bias}_{args.kind or 'all'}.json"
        (OUTPUT / summary_name).write_text(
            json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
