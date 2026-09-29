#!/usr/bin/env python3
"""Run OA-derived T28 top-/bottom-plate sampling transients in Spectre."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
from virtuoso_bridge.transport.tunnel import SSHClient


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "bootstrap_bottom_plate_eval.yaml"
OUTPUT = ROOT / "output" / "bootstrap_bottom_plate_eval"
SOURCE_DIR = OUTPUT / "netlist" / "tb_sar_bottom_plate_eval"
SOURCE = SOURCE_DIR / "input.scs"
LIB, CELL = "SAR_ADC_T28", "tb_sar_bottom_plate_eval"
CDAC = "sar_cdac_bottom_plate_eval_10b"


def export_source(profile: str) -> tuple[str, str]:
    client = VirtuosoClient.from_env(profile=profile)
    result = client.schematic.export_netlist(
        LIB, CELL, SOURCE_DIR, simulator="spectre", recreate_all=True, timeout=180,
    )
    source = Path(result["input_file"])
    if not source.is_file():
        raise RuntimeError(f"OA export missing {source}")
    return source.read_text(encoding="utf-8"), hashlib.sha256(source.read_bytes()).hexdigest()


def deck(source: str, vdiff: float, delay_s: float, config: dict[str, Any]) -> str:
    conditions, timing = config["conditions"], config["timing"]
    vcm = float(conditions["common_mode_v"])
    vinp, vinn = vcm + vdiff / 2.0, vcm - vdiff / 2.0
    sample_start = float(timing["sample_start_s"])
    boot_open = float(timing["bootstrap_open_s"])
    clamp_open = boot_open - delay_s
    if not sample_start < clamp_open < boot_open < float(timing["base_connect_s"]):
        raise ValueError("Invalid top-clamp/bottom-switch/reference phase order")
    clamp_delay = sample_start % 100e-9
    clamp_width = clamp_open - sample_start
    params = (
        f"parameters vinp_target={vinp:.12g} vinn_target={vinn:.12g} "
        f"clamp_delay={clamp_delay:.12g} clamp_width={clamp_width:.12g}\n"
    )
    saves = (
        "save PHI PHIB CLAMP BASE VINP_TOP VINN_TOP VINP_BP VINN_BP "
        "TOPP_TOP TOPN_TOP TOPP_BP TOPN_BP XBP.LSBP XBP.LSBN "
        "XBP.B9P XBP.B9N XTOPBOOT_P.G XTOPBOOT_N.G\n"
    )
    analysis = (
        f"tran tran stop={float(timing['stop_s']):.12g} maxstep=10p "
        "errpreset=conservative\n"
    )
    # ADE emits a bare design-variable declaration. Fill only that declaration;
    # every device, connection, model include and hierarchy line stays exact.
    placeholder = "parameters vinp_target vinn_target clamp_delay clamp_width\n"
    if source.count(placeholder) != 1:
        raise RuntimeError("OA export design-variable contract changed")
    configured = source.replace(placeholder, params, 1)
    assert configured.replace(params, placeholder, 1) == source
    save_setting = "saveOptions options save=allpub\n"
    if configured.count(save_setting) != 1:
        raise RuntimeError("OA export save setting changed")
    configured = configured.replace(save_setting, "saveOptions options save=selected\n", 1)
    return configured + "\n" + analysis + saves


def value_at(data: dict[str, Any], signal: str, time_s: float) -> float:
    def values(name: str) -> list[float]:
        for key, value in data.items():
            if key.strip('"').lower() == name.lower():
                if isinstance(value, list):
                    return [float(v.real if isinstance(v, complex) else v) for v in value]
                return [float(value)]
        raise KeyError(f"{name} unavailable; found {list(data)}")
    times = values("time")
    series = values(signal)
    if len(times) != len(series):
        raise ValueError(f"Length mismatch for {signal}")
    index = min(range(len(times)), key=lambda i: abs(times[i] - time_s))
    return series[index]


def analyze(data: dict[str, Any], vdiff: float, delay_s: float,
            config: dict[str, Any]) -> dict[str, float]:
    timing = config["timing"]
    hold = float(timing["hold_measure_s"])
    clamp_open = float(timing["bootstrap_open_s"]) - delay_s
    boot_open = float(timing["bootstrap_open_s"])
    base_connect = float(timing["base_connect_s"])
    def diff(top: str, bottom: str, t: float) -> float:
        return value_at(data, top, t) - value_at(data, bottom, t)
    top_diff = value_at(data, "TOPP_TOP", hold) - value_at(data, "TOPN_TOP", hold)
    bp_diff = value_at(data, "TOPP_BP", hold) - value_at(data, "TOPN_BP", hold)
    acquire = clamp_open - 0.2e-9
    top_acquired = diff("TOPP_TOP", "TOPN_TOP", acquire)
    bp_bottom_acquired = diff("XBP.B9P", "XBP.B9N", acquire)
    bp_clamp_before = diff("TOPP_BP", "TOPN_BP", clamp_open - 0.2e-9)
    bp_clamp_after = diff("TOPP_BP", "TOPN_BP", clamp_open + 0.2e-9)
    bp_boot_before = diff("TOPP_BP", "TOPN_BP", boot_open - 0.2e-9)
    bp_boot_after = diff("TOPP_BP", "TOPN_BP", boot_open + 0.2e-9)
    top_boot_before = diff("TOPP_TOP", "TOPN_TOP", boot_open - 0.2e-9)
    top_boot_after = diff("TOPP_TOP", "TOPN_TOP", boot_open + 0.2e-9)
    bp_base_before = diff("TOPP_BP", "TOPN_BP", base_connect - 0.2e-9)
    bp_base_after = diff("TOPP_BP", "TOPN_BP", base_connect + 0.3e-9)
    top_base_before = diff("TOPP_TOP", "TOPN_TOP", base_connect - 0.2e-9)
    top_base_after = diff("TOPP_TOP", "TOPN_TOP", base_connect + 0.3e-9)
    return {
        "top_diff_v": top_diff,
        "bottom_diff_v": bp_diff,
        "top_raw_error_v": top_diff - vdiff,
        "bottom_raw_error_v": -bp_diff - vdiff,
        "top_acquisition_error_v": top_acquired - vdiff,
        "bottom_b9_acquisition_error_v": bp_bottom_acquired - vdiff,
        "bottom_clamp_step_v": bp_clamp_after - bp_clamp_before,
        "bottom_bootstrap_step_v": bp_boot_after - bp_boot_before,
        "top_bootstrap_step_v": top_boot_after - top_boot_before,
        "bottom_reference_step_v": bp_base_after - bp_base_before,
        "top_reference_step_v": top_base_after - top_base_before,
        "bottom_hold_drift_v": bp_diff - bp_base_after,
        "top_hold_drift_v": top_diff - top_base_after,
        "top_common_mode_v": (value_at(data, "TOPP_TOP", hold) + value_at(data, "TOPN_TOP", hold)) / 2,
        "bottom_common_mode_v": (value_at(data, "TOPP_BP", hold) + value_at(data, "TOPN_BP", hold)) / 2,
    }


def main() -> int:
    global OUTPUT, SOURCE_DIR, SOURCE, CELL, CDAC
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--delay-ps", type=int, action="append",
                        help="Only run selected clamp-to-bootstrap delays, in picoseconds")
    parser.add_argument("--vdiff-mv", type=int, action="append",
                        help="Only run selected differential inputs, in millivolts")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--t28-clamp", action="store_true",
                        help="Use independently named T28 NMOS top-clamp OA variant")
    args = parser.parse_args()
    if args.t28_clamp:
        OUTPUT = OUTPUT / "t28_clamp"
        CELL = "tb_sar_bottom_plate_t28clamp_eval"
        CDAC = "sar_cdac_bottom_plate_t28clamp_eval_10b"
        SOURCE_DIR = OUTPUT / "netlist" / CELL
        SOURCE = SOURCE_DIR / "input.scs"
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if args.no_export:
        source = SOURCE.read_text(encoding="utf-8")
        source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    else:
        source, source_hash = export_source(args.profile)
    if f"subckt {CDAC}" not in source or "subckt sar_bootstrap" not in source:
        raise RuntimeError("OA source missing experimental CDAC or T28 bootstrap")
    if source.count("sar_bootstrap\n") < 24:
        raise RuntimeError("Expected 22 bottom and two top bootstrap instances")
    cases = [(float(v), float(d)) for d in config["timing"]["clamp_to_bootstrap_delay_s"]
             for v in config["conditions"]["differential_input_v"]]
    if args.delay_ps is not None:
        cases = [(v, d) for v, d in cases if round(d * 1e12) in args.delay_ps]
    if args.vdiff_mv is not None:
        cases = [(v, d) for v, d in cases if round(v * 1e3) in args.vdiff_mv]
    if args.case_limit is not None:
        cases = cases[:args.case_limit]
    work = OUTPUT / "spectre"
    work.mkdir(parents=True, exist_ok=True)
    summary_path = work / "run_summary.json"
    summaries = json.loads(summary_path.read_text(encoding="utf-8")) if args.skip_existing and summary_path.exists() else []
    ssh_client = SSHClient.from_env(keep_remote_files=False, profile=args.profile)
    ssh_runner = ssh_client.spectre_runner
    if ssh_runner is None:
        raise RuntimeError("Configured Spectre SSH runner is unavailable")
    for vdiff, delay in cases:
        name = f"vd{'m' if vdiff < 0 else 'p'}{abs(round(vdiff * 1000)):03d}_d{round(delay * 1e12):04d}p"
        if args.skip_existing and any(row.get("name") == name and row.get("ok")
                                      and row.get("oa_export_sha256") == source_hash for row in summaries):
            continue
        case_dir = work / name
        case_dir.mkdir(parents=True, exist_ok=True)
        path = case_dir / f"{name}.scs"
        path.write_text(deck(source, vdiff, delay, config), encoding="utf-8")
        simulator = SpectreSimulator.from_env(
            spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
            spectre_args=spectre_mode_args("spectre"), timeout=600,
            work_dir=case_dir, output_format="psfascii", profile=args.profile,
            ssh_runner=ssh_runner,
        )
        result = simulator.run_simulation(path, {})
        row: dict[str, Any] = {
            "name": name, "vdiff_v": vdiff, "clamp_to_bootstrap_delay_s": delay,
            "oa_export_sha256": source_hash, "ok": result.ok,
            "errors": list(result.errors), "warnings": list(result.warnings),
        }
        raw = case_dir / f"{name}.raw" / "tran.tran"
        if not raw.is_file():
            raw = case_dir / f"{name}.raw" / "tran.tran.tran"
        if result.ok and raw.is_file():
            parsed = parse_spectre_psf_ascii(raw)
            if parsed.ok:
                row.update(analyze(parsed.data, vdiff, delay, config))
            else:
                row["ok"] = False
                row["errors"].extend(parsed.errors)
        summaries.append(row)
        summaries = [old for old in summaries if old.get("name") != name]
        summaries.append(row)
        summary_path.write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(row, indent=2))
    return 0 if all(row["ok"] for row in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
