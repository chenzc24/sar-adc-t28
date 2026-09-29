#!/usr/bin/env python3
"""Read-only OA export and bounded Spectre verification of T28 StrongARM."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import re
from pathlib import Path
from statistics import NormalDist
from typing import Any

import yaml
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args

from run_strongarm_t28 import assert_export, crossing


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "config" / "strongarm_t28_verification.yaml"
ROOT = PROJECT / "output" / "strongarm_t28_verification"
BASELINE = PROJECT / "output" / "strongarm_t28_first_pass" / "netlist" \
    / "tb_sar_strongarm_t28" / "input.scs"


def load_config() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if data["library"] != "SAR_ADC_T28" or data["testbench"] != "tb_sar_strongarm_t28":
        raise RuntimeError("Unexpected StrongARM OA source")
    return data


def dut_block(source: str) -> str:
    start = "subckt sar_strongarm_t28 "
    end = "ends sar_strongarm_t28"
    if source.count(start) != 1 or source.count(end) != 1:
        raise RuntimeError("Missing or repeated StrongARM DUT block")
    return start + source.split(start, 1)[1].split(end, 1)[0] + end


def export_source(config: dict[str, Any], profile: str) -> dict[str, Any]:
    client = VirtuosoClient.from_env(profile=profile)
    info = client.library.get(config["library"])
    if (info.path != "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
            or info.technology_library != "tsmcN28"):
        raise RuntimeError(f"Unexpected library mapping/technology: {info}")
    destination = ROOT / "netlist" / config["testbench"]
    result = client.schematic.export_netlist(
        config["library"], config["testbench"], destination,
        simulator="spectre", recreate_all=True, timeout=180)
    source = Path(result["input_file"]).read_text(encoding="utf-8")
    check = assert_export(source)
    dut_hash = hashlib.sha256(dut_block(source).encode("utf-8")).hexdigest()
    baseline_hash = None
    if BASELINE.is_file():
        baseline_hash = hashlib.sha256(
            dut_block(BASELINE.read_text(encoding="utf-8")).encode("utf-8")
        ).hexdigest()
        if dut_hash != baseline_hash:
            raise RuntimeError("StrongARM OA DUT differs from completed first-pass baseline")
    provenance = {"cellview": f"{config['library']}/{config['testbench']}/schematic",
                  "source_file": str(result["input_file"]),
                  "source_sha256": check["sha256"], "dut_sha256": dut_hash,
                  "baseline_dut_sha256": baseline_hash,
                  "model_section": "ttmacro_mos_moscap",
                  "simulator": "Spectre 21.1", "profile": profile,
                  "device_count": len(check["mos_instances"])}
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n",
                                           encoding="utf-8")
    return provenance


def read_source(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    path = PROJECT / config["source_export"]
    if not path.is_file():
        raise FileNotFoundError(f"Run --stage export first: {path}")
    source = path.read_text(encoding="utf-8")
    provenance = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != provenance["source_sha256"]:
        raise RuntimeError("OA export hash changed after provenance capture")
    assert_export(source)
    return source, provenance


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"Expected one testbench statement {old!r}, got {source.count(old)}")
    return source.replace(old, new, 1)


def design_variables(source: str, differential_v: float, common_mode_v: float) -> str:
    vinn = common_mode_v - differential_v / 2
    vinp = common_mode_v + differential_v / 2
    return replace_once(source, "parameters vinn vinp",
                        f"parameters vinn={vinn:.12g} vinp={vinp:.12g}")


def build_noise_deck(source: str, config: dict[str, Any], *, differential_v: float,
                     seed: int, cycles: int) -> str:
    block = dut_block(source)
    deck = design_variables(source, differential_v,
                            float(config["conditions"]["nominal_common_mode_v"]))
    noise = config["noise"]
    stop = (float(config["conditions"]["first_clock_crossing_s"])
            + cycles * float(config["conditions"]["clock_period_s"]))
    deck += (f"\ntran_noise tran stop={stop:.12g} maxstep={float(noise['maxstep_s']):.12g} "
             f"noisefmax={float(noise['fmax_hz']):.12g} "
             f"noisefmin={float(noise['fmin_hz']):.12g} noiseseed={seed}\n"
             "save OUTP OUTN CLK VINP VINN XCMP.X XCMP.Y\n")
    if dut_block(deck) != block:
        raise RuntimeError("Noise wrapper changed DUT subcircuit")
    return deck


def simulate(deck: str, label: str, profile: str) -> tuple[dict[str, Any], dict[str, Any]]:
    deck_path = ROOT / "decks" / f"{label}.scs"
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    deck_path.write_text(deck, encoding="utf-8")
    work = ROOT / "spectre" / label
    sim = SpectreSimulator.from_env(
        spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
        spectre_args=spectre_mode_args("spectre"), timeout=1200,
        work_dir=work, output_format="psfascii", profile=profile)
    result = sim.run_simulation(deck_path, {})
    case = {"label": label, "deck": str(deck_path),
            "deck_sha256": hashlib.sha256(deck.encode("utf-8")).hexdigest(),
            "ok": result.ok, "status": result.status.value,
            "errors": result.errors[:12], "warnings": result.warnings[:12],
            "result_dir": str(work)}
    if not result.ok:
        return case, {}
    raw = work / f"{label}.raw"
    matches = list(raw.glob("*.tran.tran"))
    if len(matches) != 1:
        case["parse_error"] = f"Expected one transient PSF in {raw}: {matches}"
        return case, {}
    parsed = parse_spectre_psf_ascii(matches[0])
    case["psf_file"] = str(matches[0])
    case["parse_errors"] = parsed.errors
    return case, parsed.data if not parsed.errors else {}


def sample(times: list[float], values: list[float], point: float) -> float:
    index = bisect.bisect_left(times, point)
    if index == 0:
        return float(values[0])
    if index >= len(times):
        return float(values[-1])
    before, after = index - 1, index
    if abs(times[before] - point) < abs(times[after] - point):
        return float(values[before])
    return float(values[after])


def noise_decisions(data: dict[str, Any], config: dict[str, Any],
                    differential_v: float, cycles: int) -> dict[str, Any]:
    for key in ("time", "OUTP", "OUTN", "CLK"):
        if key not in data:
            raise RuntimeError(f"Noise PSF missing {key}; available={list(data)}")
    times = [float(value) for value in data["time"]]
    period = float(config["conditions"]["clock_period_s"])
    first = float(config["conditions"]["first_clock_crossing_s"])
    window = float(config["conditions"]["decision_window_s"])
    threshold = float(config["conditions"]["output_differential_threshold_v"])
    outcomes: list[int] = []
    amplitudes: list[float] = []
    for index in range(cycles):
        t = first + index * period + window
        diff = sample(times, data["OUTP"], t) - sample(times, data["OUTN"], t)
        amplitudes.append(diff)
        outcomes.append(1 if diff >= threshold else -1 if diff <= -threshold else 0)
    positive = outcomes.count(1)
    negative = outcomes.count(-1)
    unresolved = outcomes.count(0)
    expected = 1 if differential_v > 0 else -1 if differential_v < 0 else 0
    errors = (negative if expected == 1 else positive if expected == -1 else None)
    return {"differential_v": differential_v, "cycles": cycles,
            "positive": positive, "negative": negative,
            "unresolved": unresolved, "wrong_polarity": errors,
            "outcomes": outcomes,
            "min_abs_output_diff_v": min(abs(value) for value in amplitudes),
            "max_abs_output_diff_v": max(abs(value) for value in amplitudes)}


def upper_binomial_zero_errors(samples: int, confidence: float = 0.95) -> float:
    return 1.0 - (1.0 - confidence) ** (1.0 / samples)


def noise_stage(source: str, config: dict[str, Any], profile: str,
                *, smoke: bool, cycles_override: int | None,
                differential_override_v: float | None) -> dict[str, Any]:
    cycles = cycles_override or (3 if smoke else int(config["noise"]["cycles"]))
    inputs = ([0.0] if smoke else
              [differential_override_v] if differential_override_v is not None else
              [float(item) for item in config["noise"]["differential_inputs_v"]])
    seeds = [int(config["noise"]["seed"]), int(config["noise"]["seed"]) + 1] if smoke else [int(config["noise"]["seed"])]
    results: list[dict[str, Any]] = []
    for differential_v in inputs:
        for seed in seeds:
            sign = "p" if differential_v > 0 else "n" if differential_v < 0 else "z"
            label = (f"noise_{sign}{abs(differential_v)*1e6:.6f}uV_"
                     f"f{float(config['noise']['fmax_hz'])/1e9:g}G_s{seed}_n{cycles}")
            deck = build_noise_deck(source, config, differential_v=differential_v,
                                    seed=seed, cycles=cycles)
            case, data = simulate(deck, label, profile)
            case.update({"seed": seed, "noise_fmin_hz": config["noise"]["fmin_hz"],
                         "noise_fmax_hz": config["noise"]["fmax_hz"]})
            if data:
                case.update(noise_decisions(data, config, differential_v, cycles))
            results.append(case)
            print(json.dumps({key: value for key, value in case.items()
                              if key not in {"outcomes", "warnings"}}, indent=2), flush=True)
            if not case["ok"] or not data:
                break
    active = None
    if smoke and len(results) == 2 and all(item.get("outcomes") for item in results):
        active = results[0]["outcomes"] != results[1]["outcomes"]
    metric: dict[str, Any] = {"cases": results, "noise_seed_changes_decisions": active}
    if not smoke:
        biased = [item for item in results if item.get("wrong_polarity") is not None]
        if len(biased) == 2 and all(item.get("unresolved") == 0 for item in biased):
            total = sum(int(item["cycles"]) for item in biased)
            wrong = sum(int(item["wrong_polarity"]) for item in biased)
            metric["balanced_wrong_count"] = wrong
            metric["balanced_samples"] = total
            if wrong == 0:
                upper = upper_binomial_zero_errors(total)
                metric["error_probability_upper_95"] = upper
                d = abs(float(biased[0]["differential_v"]))
                metric["sigma_upper_v_if_zero_offset_gaussian"] = (
                    d / NormalDist().inv_cdf(1 - upper))
    return metric


def build_mismatch_deck(source: str, config: dict[str, Any], *,
                        differential_v: float, numruns: int) -> str:
    block = dut_block(source)
    deck = design_variables(source, differential_v,
                            float(config["conditions"]["nominal_common_mode_v"]))
    nominal_section = "section=ttmacro_mos_moscap"
    local_mc_section = f"section={config['mismatch']['model_section'].lower()}"
    if deck.count(nominal_section) != 1:
        raise RuntimeError("Expected exactly one TTMacro MOS model include")
    deck = deck.replace(nominal_section, local_mc_section, 1)
    options = config["mismatch"]
    deck += (
        f"\nmc_mismatch montecarlo numruns={numruns} seed={int(options['seed'])} "
        "variations=mismatch sampling=standard donominal=no "
        'savemismatchparams=yes mismatchparamfile="mismatch_params.txt" '
        "savefamilyplots=yes savedatainseparatedir=yes {\n"
        "  tran_decision tran stop=7n maxstep=2p\n"
        "}\n"
        "save OUTP OUTN CLK\n"
    )
    if dut_block(deck) != block:
        raise RuntimeError("Mismatch wrapper changed DUT subcircuit")
    return deck


def mismatch_case(source: str, config: dict[str, Any], profile: str,
                  *, differential_v: float, numruns: int, smoke: bool) -> dict[str, Any]:
    sign = "p" if differential_v > 0 else "n" if differential_v < 0 else "z"
    prefix = "mismatch_smoke" if smoke else "mismatch"
    label = (f"{prefix}_{sign}{abs(differential_v)*1e6:.6f}uV_"
             f"s{int(config['mismatch']['seed'])}_n{numruns}")
    deck = build_mismatch_deck(source, config, differential_v=differential_v,
                               numruns=numruns)
    deck_path = ROOT / "decks" / f"{label}.scs"
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    deck_path.write_text(deck, encoding="utf-8")
    work = ROOT / "spectre" / label
    sim = SpectreSimulator.from_env(
        spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
        spectre_args=spectre_mode_args("spectre"), timeout=1200,
        work_dir=work, output_format="psfascii", profile=profile)
    result = sim.run_simulation(deck_path, {})
    raw = work / f"{label}.raw"
    files = [str(path.relative_to(raw)) for path in raw.rglob("*") if path.is_file()] \
        if raw.exists() else []
    log = (work / "spectre.out").read_text(encoding="utf-8", errors="replace") \
        if (work / "spectre.out").is_file() else ""
    random_variables_match = re.search(r"Number of random variables:\s*(\d+)", log)
    defined_mismatch_match = re.search(r"Defined mismatch parameters \(subckt based\):\s*(\d+)", log)
    random_variables = int(random_variables_match.group(1)) if random_variables_match else None
    defined_mismatch = int(defined_mismatch_match.group(1)) if defined_mismatch_match else None
    output = {"label": label, "ok": result.ok, "status": result.status.value,
              "errors": result.errors[:12], "warnings": result.warnings[:15],
              "deck": str(deck_path), "raw_files": files[:100],
              "raw_file_count": len(files), "result_dir": str(work),
              "differential_v": differential_v, "numruns": numruns,
              "seed": int(config["mismatch"]["seed"]),
              "model_section": config["mismatch"]["model_section"],
              "random_variables": random_variables,
              "defined_mismatch_parameters": defined_mismatch}
    if result.ok and random_variables and defined_mismatch:
        output["statistics_active"] = True
        sampled_parameters = raw / "mc_mismatch.mismatch.mcdata"
        if sampled_parameters.is_file():
            output["sampled_mismatch_sha256"] = hashlib.sha256(
                sampled_parameters.read_bytes()).hexdigest()
        run_root = raw / "mc_mismatch_separate"
        psfs = sorted(run_root.glob("mc_mismatch-*/mc_mismatch_tran_decision.tran.tran"))
        if len(psfs) != numruns:
            output["parse_error"] = f"Expected {numruns} MC transient files, got {len(psfs)}"
        else:
            sample_time = (float(config["conditions"]["first_clock_crossing_s"])
                           + float(config["conditions"]["decision_window_s"]))
            threshold = float(config["conditions"]["output_differential_threshold_v"])
            decisions = []
            early_differences = []
            early_sample_time = float(config["conditions"]["first_clock_crossing_s"]) + 90e-12
            for index, psf in enumerate(psfs, start=1):
                parsed = parse_spectre_psf_ascii(psf)
                if parsed.errors or any(key not in parsed.data for key in ("time", "OUTP", "OUTN")):
                    output["parse_error"] = f"Failed MC iteration {index}: {parsed.errors}"
                    break
                data = parsed.data
                times = [float(value) for value in data["time"]]
                diff = (sample(times, data["OUTP"], sample_time)
                        - sample(times, data["OUTN"], sample_time))
                early_diff = (sample(times, data["OUTP"], early_sample_time)
                              - sample(times, data["OUTN"], early_sample_time))
                early_differences.append(early_diff)
                decision = 1 if diff >= threshold else -1 if diff <= -threshold else 0
                decisions.append({"iteration": index, "output_diff_v": diff,
                                  "decision": decision})
            if "parse_error" not in output:
                span = max(early_differences) - min(early_differences)
                output["early_output_difference_span_v"] = span
                output["waveform_variation_observed"] = span > 1e-8
                expected = 1 if differential_v > 0 else -1
                output["decisions"] = decisions
                output["correct"] = sum(item["decision"] == expected for item in decisions)
                output["wrong"] = sum(item["decision"] == -expected for item in decisions)
                output["unresolved"] = sum(item["decision"] == 0 for item in decisions)
    else:
        output["statistics_active"] = False
    return output


def mismatch_stage(source: str, config: dict[str, Any], profile: str,
                   *, numruns: int, smoke: bool) -> dict[str, Any]:
    inputs = [float(item) for item in config["mismatch"]["differential_inputs_v"]]
    if smoke:
        inputs = inputs[:1]
    cases = []
    for differential_v in inputs:
        case = mismatch_case(source, config, profile, differential_v=differential_v,
                             numruns=numruns, smoke=smoke)
        cases.append(case)
        print(json.dumps({key: value for key, value in case.items()
                          if key not in {"raw_files", "decisions", "warnings"}},
                         indent=2), flush=True)
        if (not case["ok"] or not case.get("statistics_active")
                or case.get("parse_error") or not case.get("waveform_variation_observed")):
            break
    summary: dict[str, Any] = {"cases": cases}
    if len(cases) == 2:
        hashes = [case.get("sampled_mismatch_sha256") for case in cases]
        summary["paired_samples_same_statistics"] = bool(
            hashes[0] and hashes[0] == hashes[1])
    if (len(cases) == 2 and summary.get("paired_samples_same_statistics")
            and all(len(case.get("decisions", [])) == numruns
                    and case.get("waveform_variation_observed") for case in cases)):
        paired = [
            {"iteration": index + 1,
             "positive_decision": cases[0]["decisions"][index]["decision"],
             "negative_decision": cases[1]["decisions"][index]["decision"]}
            for index in range(numruns)
        ]
        within = sum(item["positive_decision"] == 1 and item["negative_decision"] == -1
                     for item in paired)
        summary["paired_iterations"] = paired
        summary["within_pm_0p439mv"] = within
        summary["outside_or_unresolved"] = numruns - within
        if within == numruns:
            summary["outside_probability_upper_95"] = upper_binomial_zero_errors(numruns)
    return summary


MODEL_SECTIONS = {"TT": "TTMacro_MOS_MOSCAP", "SS": "SSMacro_MOS_MOSCAP",
                  "FF": "FFMacro_MOS_MOSCAP"}


def build_pvt_deck(source: str, config: dict[str, Any], condition: dict[str, Any],
                   differential_v: float) -> str:
    block = dut_block(source)
    vdd = float(condition["supply_v"])
    deck = design_variables(source, differential_v, vdd / 2)
    section = MODEL_SECTIONS[condition["process"]]
    pattern = r"(?im)^(include\s+\"[^\"\n]+\"\s+section=)ttmacro_mos_moscap\s*$"
    deck, count = re.subn(pattern, rf"\g<1>{section}", deck, count=1)
    if count != 1:
        raise RuntimeError("Could not select PVT MOS model section")
    deck = replace_once(deck, "VVDD (VDD 0) vsource dc=900m type=dc",
                        f"VVDD (VDD 0) vsource dc={vdd:.12g} type=dc")
    deck = replace_once(deck, "val1=900m period=5n", f"val1={vdd:.12g} period=5n")
    cap_f = float(condition["output_load_f"])
    for name, net in (("COUTP", "OUTP"), ("COUTN", "OUTN")):
        deck = replace_once(deck, f"{name} ({net} 0) capacitor c=5f",
                            f"{name} ({net} 0) capacitor c={cap_f:.12g}")
    deck = replace_once(deck, "temp=27 tnom=27",
                        f"temp={float(condition['temperature_c']):.12g} tnom=27")
    deck += "\ntran_pvt tran stop=12n maxstep=2p\nsave OUTP OUTN CLK VVDD:p\n"
    if dut_block(deck) != block:
        raise RuntimeError("PVT wrapper changed DUT subcircuit")
    return deck


def integrate_supply_energy(data: dict[str, Any], start: float, stop: float,
                            supply_v: float) -> float | None:
    if "VVDD:p" not in data:
        return None
    times = [float(value) for value in data["time"]]
    current = [float(value) for value in data["VVDD:p"]]
    result = 0.0
    for index in range(1, min(len(times), len(current))):
        t0, t1 = times[index - 1], times[index]
        if t1 <= start or t0 >= stop:
            continue
        left, right = max(t0, start), min(t1, stop)
        if right <= left:
            continue
        i0 = current[index - 1] + (current[index] - current[index - 1]) * (left - t0) / (t1 - t0)
        i1 = current[index - 1] + (current[index] - current[index - 1]) * (right - t0) / (t1 - t0)
        result += -supply_v * (i0 + i1) * (right - left) / 2
    return result


def pvt_metrics(data: dict[str, Any], condition: dict[str, Any],
                differential_v: float) -> dict[str, Any]:
    needed = ("time", "CLK", "OUTP", "OUTN")
    if any(key not in data for key in needed):
        raise RuntimeError(f"PVT PSF missing {needed}; present={list(data)}")
    times = [float(item) for item in data["time"]]
    vdd = float(condition["supply_v"])
    clock = [float(item) for item in data["CLK"]]
    positive = [float(item) for item in data["OUTP"]]
    negative = [float(item) for item in data["OUTN"]]
    sign = 1 if differential_v > 0 else -1
    signed = [sign * (p - n) for p, n in zip(positive, negative)]
    edge = crossing(times, clock, vdd / 2, 4.9e-9, 5.2e-9, 1)
    decided = crossing(times, signed, 0.45, 5e-9, 7e-9, 1)
    if edge is None:
        raise RuntimeError("PVT clock edge missing")
    reset = min(sample(times, positive, 4.9e-9), sample(times, negative, 4.9e-9),
                sample(times, positive, 9.9e-9), sample(times, negative, 9.9e-9))
    final_signed = sample(times, signed, 6.5e-9)
    time_ps = None if decided is None else (decided - edge) * 1e12
    energy_j = integrate_supply_energy(data, edge, edge + 2e-9, vdd)
    return {"differential_v": differential_v, "clock_edge_ns": edge * 1e9,
            "resolution_ps": time_ps, "min_reset_v": reset,
            "signed_output_diff_at_1p5ns_v": final_signed,
            "supply_energy_evaluation_j": energy_j,
            "nominal_window_pass": bool(time_ps is not None and time_ps <= 1500
                                        and reset >= 0.9 * vdd and final_signed >= 0.45)}


def pvt_stage(source: str, config: dict[str, Any], profile: str,
              *, condition_name: str | None, differential_override_v: float | None) -> dict[str, Any]:
    conditions = [item for item in config["pvt_screen"]
                  if condition_name is None or item["name"] == condition_name]
    if not conditions:
        raise ValueError(f"Unknown PVT condition: {condition_name}")
    inputs = ([differential_override_v] if differential_override_v is not None else
              [float(config["targets"]["offset_abs_max_v"]),
               -float(config["targets"]["offset_abs_max_v"])])
    results = []
    for condition in conditions:
        for differential_v in inputs:
            label = f"pvt_{condition['name']}_{'p' if differential_v > 0 else 'n'}"
            deck = build_pvt_deck(source, config, condition, differential_v)
            case, data = simulate(deck, label, profile)
            case["condition"] = condition
            if data:
                case.update(pvt_metrics(data, condition, differential_v))
            results.append(case)
            print(json.dumps({key: value for key, value in case.items()
                              if key != "warnings"}, indent=2), flush=True)
            if not case["ok"] or not data:
                return {"cases": results, "all_pass": False}
    return {"cases": results,
            "all_pass": all(item.get("nominal_window_pass", False) for item in results)}


def build_kickback_deck(source: str, config: dict[str, Any], *,
                        differential_v: float, input_cap_f: float) -> str:
    block = dut_block(source)
    deck = design_variables(source, differential_v,
                            float(config["conditions"]["nominal_common_mode_v"]))
    resistance = float(config["kickback"]["hold_resistance_ohm"])
    for source_name, node, bias, resistor, cap in (
        ("VIPP", "VINP", "VBIASP", "RHOLDP", "CHOLDP"),
        ("VNN_SRC", "VINN", "VBIASN", "RHOLDN", "CHOLDN"),
    ):
        old = f"{source_name} ({node} 0) vsource dc={'vinp' if node == 'VINP' else 'vinn'} type=dc"
        new = (f"{source_name} ({bias} 0) vsource dc={'vinp' if node == 'VINP' else 'vinn'} type=dc\n"
               f"{resistor} ({bias} {node}) resistor r={resistance:.12g}\n"
               f"{cap} ({node} 0) capacitor c={input_cap_f:.12g}")
        deck = replace_once(deck, old, new)
    deck += "\ntran_kickback tran stop=12n maxstep=2p\nsave OUTP OUTN CLK VINP VINN\n"
    if dut_block(deck) != block:
        raise RuntimeError("Kickback wrapper changed DUT subcircuit")
    return deck


def kickback_metrics(data: dict[str, Any], differential_v: float,
                     input_cap_f: float) -> dict[str, Any]:
    for key in ("time", "VINP", "VINN", "OUTP", "OUTN"):
        if key not in data:
            raise RuntimeError(f"Kickback PSF missing {key}")
    times = [float(item) for item in data["time"]]
    inp = [float(item) for item in data["VINP"]]
    inn = [float(item) for item in data["VINN"]]
    baseline = sample(times, inp, 4.9e-9) - sample(times, inn, 4.9e-9)
    steps = [(p - n) - baseline for t, p, n in zip(times, inp, inn)
             if 5e-9 <= t <= 6.5e-9]
    final = sample(times, inp, 6.5e-9) - sample(times, inn, 6.5e-9)
    sign = 1 if differential_v > 0 else -1
    output = sign * (sample(times, data["OUTP"], 6.5e-9)
                     - sample(times, data["OUTN"], 6.5e-9))
    return {"differential_v": differential_v, "input_cap_f": input_cap_f,
            "pre_edge_input_diff_v": baseline,
            "fixture_valid": abs(baseline - differential_v) <= max(1e-6, 0.05 * abs(differential_v)),
            "peak_abs_differential_kickback_v": max(abs(item) for item in steps),
            "pre_compare_differential_shift_v": final - baseline,
            "signed_output_diff_at_1p5ns_v": output,
            "correct_polarity": output >= 0.45}


def kickback_stage(source: str, config: dict[str, Any], profile: str, *,
                   cap_override_f: float | None, differential_override_v: float | None,
                   reuse_existing: bool) -> dict[str, Any]:
    results = []
    resistance = float(config["kickback"]["hold_resistance_ohm"])
    caps = ([cap_override_f] if cap_override_f is not None else
            config["kickback"]["input_capacitances_f"])
    inputs = ([differential_override_v] if differential_override_v is not None else
              config["kickback"]["differential_inputs_v"])
    for input_cap_f in caps:
        for differential_v in inputs:
            input_cap_f, differential_v = float(input_cap_f), float(differential_v)
            label = (f"kickback_r{resistance/1e9:g}G_{input_cap_f*1e15:.3f}f_"
                     f"{'p' if differential_v > 0 else 'n'}")
            if reuse_existing:
                expected_deck = build_kickback_deck(
                    source, config, differential_v=differential_v,
                    input_cap_f=input_cap_f)
                deck_path = ROOT / "decks" / f"{label}.scs"
                if not deck_path.is_file() or deck_path.read_text(encoding="utf-8") != expected_deck:
                    raise RuntimeError(f"Existing kickback deck does not match OA/config: {label}")
                work = ROOT / "spectre" / label
                raw = work / f"{label}.raw"
                psfs = list(raw.glob("*.tran.tran"))
                log = work / "spectre.out"
                if len(psfs) != 1 or not log.is_file():
                    raise FileNotFoundError(f"Existing kickback result incomplete: {label}")
                log_text = log.read_text(encoding="utf-8", errors="replace")
                if not re.search(r"spectre completes with 0 errors", log_text):
                    raise RuntimeError(f"Existing kickback Spectre result failed: {label}")
                parsed = parse_spectre_psf_ascii(psfs[0])
                if parsed.errors:
                    raise RuntimeError(f"Existing kickback PSF parse failed: {parsed.errors}")
                case, data = {"label": label, "ok": True,
                              "status": "reused_validated_spectre_result",
                              "psf_file": str(psfs[0])}, parsed.data
            else:
                deck = build_kickback_deck(source, config, differential_v=differential_v,
                                           input_cap_f=input_cap_f)
                case, data = simulate(deck, label, profile)
            if data:
                case.update(kickback_metrics(data, differential_v, input_cap_f))
            results.append(case)
            print(json.dumps({key: value for key, value in case.items()
                              if key != "warnings"}, indent=2), flush=True)
            if not case["ok"] or not data:
                return {"cases": results}
    return {"cases": results, "all_fixtures_valid": all(
        item.get("fixture_valid", False) for item in results)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("export", "noise-smoke", "noise",
                                            "mismatch-smoke", "mismatch", "pvt",
                                            "kickback"), required=True)
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--cycles", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--differential-uv", type=float)
    parser.add_argument("--fmax-ghz", type=float)
    parser.add_argument("--numruns", type=int)
    parser.add_argument("--condition")
    parser.add_argument("--kickback-cap-ff", type=float)
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()
    config = load_config()
    if args.seed is not None:
        config["noise"]["seed"] = args.seed
        config["mismatch"]["seed"] = args.seed
    if args.fmax_ghz is not None:
        config["noise"]["fmax_hz"] = args.fmax_ghz * 1e9
    if args.stage == "export":
        print(json.dumps(export_source(config, args.profile), indent=2))
        return 0
    source, provenance = read_source(config)
    if args.stage in {"mismatch-smoke", "mismatch"}:
        result = mismatch_stage(source, config, args.profile,
                                numruns=args.numruns or (4 if args.stage == "mismatch-smoke"
                                                         else int(config["mismatch"]["numruns"])),
                                smoke=args.stage == "mismatch-smoke")
        suffix = "" if args.seed is None and args.numruns is None else (
            f"_seed{config['mismatch']['seed']}_n"
            f"{args.numruns or (4 if args.stage == 'mismatch-smoke' else config['mismatch']['numruns'])}")
        path = ROOT / f"{args.stage}{suffix}_summary.json"
        path.write_text(json.dumps({"stage": args.stage, "provenance": provenance,
                                    "result": result}, indent=2) + "\n",
                        encoding="utf-8")
        print(f"summary: {path}")
        valid_cases = all(case["ok"] and case.get("statistics_active")
                          and case.get("waveform_variation_observed")
                          and not case.get("parse_error") for case in result["cases"])
        valid_pair = (args.stage == "mismatch-smoke"
                      or result.get("paired_samples_same_statistics", False))
        return 0 if valid_cases and valid_pair else 1
    if args.stage == "pvt":
        result = pvt_stage(source, config, args.profile,
                           condition_name=args.condition,
                           differential_override_v=(None if args.differential_uv is None
                                                    else args.differential_uv * 1e-6))
        name = f"pvt_{args.condition}_summary.json" if args.condition else "pvt_summary.json"
        path = ROOT / name
        path.write_text(json.dumps({"provenance": provenance, "result": result},
                                   indent=2) + "\n", encoding="utf-8")
        print(f"summary: {path}")
        return 0 if all(case["ok"] and not case.get("parse_errors")
                        for case in result["cases"]) else 1
    if args.stage == "kickback":
        result = kickback_stage(
            source, config, args.profile,
            cap_override_f=(None if args.kickback_cap_ff is None else args.kickback_cap_ff * 1e-15),
            differential_override_v=(None if args.differential_uv is None else args.differential_uv * 1e-6),
            reuse_existing=args.reuse_existing)
        suffix = ("" if args.kickback_cap_ff is None and args.differential_uv is None else
                  f"_cap{args.kickback_cap_ff if args.kickback_cap_ff is not None else 'all'}f_"
                  f"d{args.differential_uv if args.differential_uv is not None else 'all'}uV")
        path = ROOT / (f"kickback_r{float(config['kickback']['hold_resistance_ohm'])/1e9:g}G"
                       f"{suffix}_summary.json")
        path.write_text(json.dumps({"provenance": provenance, "result": result},
                                   indent=2) + "\n", encoding="utf-8")
        print(f"summary: {path}")
        return 0 if result.get("all_fixtures_valid", False) and all(
            case["ok"] and not case.get("parse_errors")
            for case in result["cases"]) else 1
    result = noise_stage(source, config, args.profile,
                         smoke=args.stage == "noise-smoke",
                         cycles_override=args.cycles,
                         differential_override_v=(None if args.differential_uv is None
                                                  else args.differential_uv * 1e-6))
    summary = {"stage": args.stage, "provenance": provenance, "result": result}
    suffix = "" if (args.seed is None and args.cycles is None
                    and args.differential_uv is None and args.fmax_ghz is None) else (
        f"_seed{config['noise']['seed']}_n{args.cycles or config['noise']['cycles']}"
        f"_d{args.differential_uv if args.differential_uv is not None else 'all'}uV"
        f"_f{float(config['noise']['fmax_hz'])/1e9:g}GHz")
    path = ROOT / f"{args.stage}{suffix}_summary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"summary: {path}")
    return 0 if all(case["ok"] and not case.get("parse_errors")
                    for case in result["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
