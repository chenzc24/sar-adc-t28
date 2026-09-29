#!/usr/bin/env python3
"""Exact-OA-netlist diagnostic of a full W185 split CDAC driving StrongARM."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args

from run_strongarm_t28 import crossing


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "config" / "strongarm_cdac_integration.yaml"
ROOT = PROJECT / "output" / "strongarm_cdac_integration"
SOURCE = ROOT / "netlist" / "tb_sar_cdac_strongarm_diag" / "input.scs"
CDAC_BASELINE = (PROJECT / "output" / "bootstrap_bottom_plate_clamp_width_screen"
                 / "w185" / "netlist" / "tb_sar_bottom_plate_clamp_w185_eval" / "input.scs")
COMPARATOR_BASELINE = (PROJECT / "output" / "strongarm_t28_first_pass"
                       / "netlist" / "tb_sar_strongarm_t28" / "input.scs")


def load_config() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if (data["library"] != "SAR_ADC_T28"
            or data["testbench"] != "tb_sar_cdac_strongarm_diag"):
        raise RuntimeError("Unexpected OA source")
    return data


def subckt(source: str, name: str) -> str:
    start, end = f"subckt {name} ", f"ends {name}"
    if source.count(start) != 1 or source.count(end) != 1:
        raise RuntimeError(f"Missing or repeated {name} subcircuit")
    return start + source.split(start, 1)[1].split(end, 1)[0] + end


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_source(source: str, config: dict[str, Any]) -> dict[str, Any]:
    if source.count("XCMP (COMP_CLK CMP_OUTN CMP_OUTP VDD TOPN_BP TOPP_BP 0) sar_strongarm_t28") != 1:
        raise RuntimeError("Comparator is not connected directly to CDAC top plates")
    if source.count("XBP (") != 1 or source.count(") sar_cdac_bottom_plate_clamp_w185_eval_10b") != 1:
        raise RuntimeError("Expected exactly one W185 full-CDAC instance")
    for node in ("TOPP_BP", "TOPN_BP", "COMP_CLK", "CMP_OUTP", "CMP_OUTN"):
        if node not in source:
            raise RuntimeError(f"Missing diagnostic node {node}")
    if source.count("COUTP (CMP_OUTP 0) capacitor c=5f") != 1:
        raise RuntimeError("Unexpected comparator output load")
    names = (config["cdac"], config["comparator"])
    hashes = {name: digest(subckt(source, name)) for name in names}
    for name, baseline in ((config["cdac"], CDAC_BASELINE),
                           (config["comparator"], COMPARATOR_BASELINE)):
        if baseline.is_file() and hashes[name] != digest(subckt(baseline.read_text(encoding="utf-8"), name)):
            raise RuntimeError(f"Saved {name} differs from previous validated export")
    return {"source_sha256": digest(source), "subckt_sha256": hashes,
            "model_section": "ttmacro_mos_moscap", "simulator": "Spectre 21.1"}


def export(config: dict[str, Any], profile: str) -> dict[str, Any]:
    client = VirtuosoClient.from_env(profile=profile)
    info = client.library.get(config["library"])
    if (info.path != "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
            or info.technology_library != "tsmcN28"):
        raise RuntimeError(f"Unexpected library mapping: {info}")
    result = client.schematic.export_netlist(config["library"], config["testbench"],
                                             SOURCE.parent, simulator="spectre",
                                             recreate_all=True, timeout=180)
    source = Path(result["input_file"]).read_text(encoding="utf-8")
    provenance = validate_source(source, config)
    provenance.update({"cellview": f"{config['library']}/{config['testbench']}/schematic",
                       "source_file": str(result["input_file"]), "profile": profile})
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n",
                                           encoding="utf-8")
    return provenance


def read_source(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    source = SOURCE.read_text(encoding="utf-8")
    provenance = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    if validate_source(source, config)["source_sha256"] != provenance["source_sha256"]:
        raise RuntimeError("OA export changed after provenance capture")
    return source, provenance


def build_deck(source: str, config: dict[str, Any], differential_v: float,
               clock_high_v: float) -> str:
    timing = config["timing"]
    vcm = float(config["conditions"]["common_mode_v"])
    vinp, vinn = vcm + differential_v / 2, vcm - differential_v / 2
    clamp_open = (float(timing["bootstrap_open_s"])
                  - float(timing["clamp_to_bootstrap_delay_s"]))
    if not (float(timing["sample_start_s"]) < clamp_open
            < float(timing["bootstrap_open_s"]) < float(timing["base_connect_s"])
            < float(timing["comparator_clock_start_s"])):
        raise RuntimeError("Invalid sample, clamp, bottom-switch, reference, comparator ordering")
    clamp_delay = float(timing["sample_start_s"]) % 100e-9
    clamp_width = clamp_open - float(timing["sample_start_s"])
    old = "parameters comp_clock_high vinp_target vinn_target clamp_delay clamp_width\n"
    new = (f"parameters comp_clock_high={clock_high_v:.12g} "
           f"vinp_target={vinp:.12g} vinn_target={vinn:.12g} "
           f"clamp_delay={clamp_delay:.12g} clamp_width={clamp_width:.12g}\n")
    if source.count(old) != 1:
        raise RuntimeError("OA design-variable declaration changed")
    deck = source.replace(old, new, 1)
    old_save = "saveOptions options save=allpub\n"
    if deck.count(old_save) != 1:
        raise RuntimeError("OA save statement changed")
    deck = deck.replace(old_save, "saveOptions options save=selected\n", 1)
    deck += (f"\ntran_interface tran stop={float(timing['stop_s']):.12g} "
             f"maxstep={float(timing['maxstep_s']):.12g} errpreset=conservative\n"
             "save TOPP_BP TOPN_BP XBP.LSBP XBP.LSBN VINP_BP VINN_BP "
             "COMP_CLK CMP_OUTP CMP_OUTN CLAMP BASE PHI XCMP.X XCMP.Y\n")
    for name in (config["cdac"], config["comparator"]):
        if subckt(deck, name) != subckt(source, name):
            raise RuntimeError(f"Analysis deck changed {name} subcircuit")
    return deck


def interpolate(times: list[float], values: list[float], t: float) -> float:
    index = bisect.bisect_left(times, t)
    if index == 0:
        return float(values[0])
    if index >= len(times):
        return float(values[-1])
    a, b = index - 1, index
    ratio = (t - times[a]) / (times[b] - times[a])
    return float(values[a]) + ratio * (float(values[b]) - float(values[a]))


def signal(data: dict[str, Any], name: str, t: float) -> float:
    return interpolate([float(item) for item in data["time"]], data[name], t)


def differential(data: dict[str, Any], t: float) -> float:
    return signal(data, "TOPP_BP", t) - signal(data, "TOPN_BP", t)


def metrics(data: dict[str, Any], config: dict[str, Any], differential_v: float,
            clock_high_v: float) -> dict[str, Any]:
    required = {"time", "TOPP_BP", "TOPN_BP", "VINP_BP", "VINN_BP",
                "COMP_CLK", "CMP_OUTP", "CMP_OUTN"}
    if not required.issubset(data):
        raise RuntimeError(f"Missing PSF signals: {sorted(required - set(data))}")
    timing = config["timing"]
    before = float(timing["pre_clock_probe_s"])
    probe = float(timing["decision_probe_s"])
    top_before = differential(data, before)
    source_before = signal(data, "VINP_BP", before) - signal(data, "VINN_BP", before)
    result = {"source_differential_v": differential_v,
              "clock_high_v": clock_high_v,
              "actual_source_differential_v": source_before,
              "top_differential_pre_clock_v": top_before,
              "top_common_mode_pre_clock_v":
                  (signal(data, "TOPP_BP", before) + signal(data, "TOPN_BP", before)) / 2,
              "top_differential_at_1p5ns_v": differential(data, probe),
              "output_differential_at_1p5ns_v":
                  signal(data, "CMP_OUTP", probe) - signal(data, "CMP_OUTN", probe)}
    if clock_high_v > 0:
        times = [float(value) for value in data["time"]]
        clock = [float(value) for value in data["COMP_CLK"]]
        output = [float(p) - float(n) for p, n in zip(data["CMP_OUTP"], data["CMP_OUTN"])]
        # A zero-differential deterministic run may pick a polarity from
        # floating-point asymmetry.  That is a control, not a correctness test.
        input_sign = (0 if differential_v == 0 else
                      1 if top_before > 0 else -1 if top_before < 0 else 0)
        edge = crossing(times, clock, clock_high_v / 2,
                        float(timing["comparator_clock_start_s"]) - 0.1e-9,
                        float(timing["comparator_clock_start_s"]) + 0.1e-9, 1)
        decided = (crossing(times, [input_sign * item for item in output],
                            float(config["targets"]["output_differential_threshold_v"]),
                            edge, edge + float(config["targets"]["maximum_decision_time_s"]), 1)
                   if edge is not None and input_sign else None)
        result.update({"clock_edge_s": edge, "expected_output_sign_from_top_plate": input_sign,
                       "decision_time_s": decided,
                       "resolution_s": None if decided is None else decided - edge,
                       "resolved_within_window": decided is not None})
    return result


def compare_on_off(enabled: dict[str, Any], disabled: dict[str, Any],
                   config: dict[str, Any], decision_time_s: float | None) -> dict[str, Any]:
    timing = config["timing"]
    start = float(timing["comparator_clock_start_s"])
    stop = float(timing["peak_window_end_s"])
    pre = float(timing["pre_clock_probe_s"])
    base = differential(enabled, pre) - differential(disabled, pre)
    enabled_times = [float(item) for item in enabled["time"]]
    disabled_times = [float(item) for item in disabled["time"]]
    enabled_diff = [float(p) - float(n) for p, n in zip(enabled["TOPP_BP"], enabled["TOPN_BP"])]
    disabled_diff = [float(p) - float(n) for p, n in zip(disabled["TOPP_BP"], disabled["TOPN_BP"])]
    times = [t for t in enabled_times if start <= t <= stop]
    if not times:
        raise RuntimeError("No samples in comparator-kickback window")
    excursions = [(interpolate(enabled_times, enabled_diff, t)
                   - interpolate(disabled_times, disabled_diff, t) - base)
                  for t in times]
    peak_index = max(range(len(excursions)), key=lambda index: abs(excursions[index]))
    return {"peak_abs_clock_induced_differential_v": max(abs(x) for x in excursions),
            "signed_peak_clock_induced_differential_v": excursions[peak_index],
            "peak_clock_induced_time_s": times[peak_index],
            "clock_induced_differential_at_1p5ns_v":
                differential(enabled, float(timing["decision_probe_s"]))
                - differential(disabled, float(timing["decision_probe_s"])) - base,
            "clock_induced_differential_at_decision_v":
                None if decision_time_s is None else
                interpolate(enabled_times, enabled_diff, decision_time_s)
                - interpolate(disabled_times, disabled_diff, decision_time_s) - base,
            "pre_clock_on_off_baseline_delta_v": base,
            "comparison_window_samples": len(times)}


def run_case(source: str, config: dict[str, Any], profile: str,
             differential_v: float, clock_high_v: float,
             *, reuse_existing: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    label = (f"d{('p' if differential_v > 0 else 'n' if differential_v < 0 else 'z')}"
             f"{abs(differential_v)*1e6:.6f}uV_"
             f"clock{clock_high_v:.1f}V")
    deck = build_deck(source, config, differential_v, clock_high_v)
    deck_path = ROOT / "decks" / f"{label}.scs"
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    work = ROOT / "spectre" / label
    if reuse_existing:
        if not deck_path.is_file() or deck_path.read_text(encoding="utf-8") != deck:
            raise RuntimeError(f"Existing deck differs from OA/config: {label}")
        log = work / "spectre.out"
        if not log.is_file():
            raise FileNotFoundError(f"Existing Spectre log missing: {label}")
        content = log.read_text(encoding="utf-8", errors="replace")
        if "spectre completes with 0 errors" not in content:
            raise RuntimeError(f"Existing Spectre run was not successful: {label}")
        ok, status, errors, warnings = True, "reused_validated_spectre_result", [], []
    else:
        deck_path.write_text(deck, encoding="utf-8")
        simulator = SpectreSimulator.from_env(
            spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
            spectre_args=spectre_mode_args("spectre"), timeout=1200,
            work_dir=work, output_format="psfascii", profile=profile)
        result = simulator.run_simulation(deck_path, {})
        ok, status, errors, warnings = (result.ok, result.status.value,
                                        result.errors[:12], result.warnings[:20])
    case: dict[str, Any] = {"label": label, "ok": ok,
                            "status": status, "errors": errors,
                            "warnings": warnings, "deck": str(deck_path),
                            "deck_sha256": digest(deck), "result_dir": str(work)}
    if not ok:
        return case, {}
    psfs = list((work / f"{label}.raw").glob("*.tran.tran"))
    if len(psfs) != 1:
        case["parse_error"] = f"Expected one transient PSF, got {len(psfs)}"
        return case, {}
    parsed = parse_spectre_psf_ascii(psfs[0])
    case["psf_file"] = str(psfs[0])
    case["parse_errors"] = parsed.errors
    if parsed.errors:
        return case, {}
    case.update(metrics(parsed.data, config, differential_v, clock_high_v))
    log = work / "spectre.out"
    if log.is_file():
        content = log.read_text(encoding="utf-8", errors="replace")
        case["model_limit_warning_codes"] = sorted(set(re.findall(r"CMI-27\d\d", content)))
        case["spectre_error_count"] = len(re.findall(r"\bERROR \(", content))
    return case, parsed.data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("export", "run", "analyze-existing"), required=True)
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--differential-uv", type=float)
    args = parser.parse_args()
    config = load_config()
    if args.stage == "export":
        print(json.dumps(export(config, args.profile), indent=2))
        return 0
    source, provenance = read_source(config)
    values = ([args.differential_uv * 1e-6] if args.differential_uv is not None else
              [float(item) for item in config["inputs"]["differential_v"]])
    cases: list[dict[str, Any]] = []
    comparisons = []
    for differential_v in values:
        runs: dict[float, dict[str, Any]] = {}
        run_cases: dict[float, dict[str, Any]] = {}
        for clock_high_v in (0.0, 0.9):
            case, data = run_case(source, config, args.profile, differential_v, clock_high_v,
                                  reuse_existing=args.stage == "analyze-existing")
            cases.append(case)
            print(json.dumps({key: value for key, value in case.items()
                              if key not in {"warnings"}}, indent=2), flush=True)
            if not case["ok"] or not data:
                break
            runs[clock_high_v] = data
            run_cases[clock_high_v] = case
        if len(runs) == 2:
            comparisons.append({"differential_v": differential_v,
                                **compare_on_off(runs[0.9], runs[0.0], config,
                                                 run_cases[0.9].get("decision_time_s"))})
        else:
            break
    summary = {"provenance": provenance, "cases": cases, "on_off_comparisons": comparisons}
    suffix = "all" if args.differential_uv is None else f"{args.differential_uv:g}uV"
    path = ROOT / f"summary_{suffix}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"summary: {path}")
    return 0 if len(comparisons) == len(values) and all(case["ok"] for case in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
