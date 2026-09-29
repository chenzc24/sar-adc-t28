#!/usr/bin/env python3
"""Export the exact OA StrongARM fixture and run nominal Spectre vectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii
from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args


LIB = "SAR_ADC_T28"
TB = "tb_sar_strongarm_t28"
ROOT = Path("output/strongarm_t28_first_pass")
CASES_MV = (10.0, -10.0, 0.87890625, -0.87890625, 0.439453125, -0.439453125)


def assert_export(source: str) -> dict:
    if source.count("subckt sar_strongarm_t28 ") != 1:
        raise RuntimeError("Exported DUT subckt missing or repeated")
    section = source.split("subckt sar_strongarm_t28 ", 1)[1].split(
        "ends sar_strongarm_t28", 1)[0]
    devices = [line.split()[0] for line in section.splitlines()
               if line.strip().startswith(("MN", "MP"))]
    if len(devices) != 11 or len(set(devices)) != 11:
        raise RuntimeError(f"Expected 11 unique PDK MOS devices, got {devices}")
    for token in ("nch_mac", "pch_mac", "section=ttmacro_mos_moscap",
                  "XCMP (", "VINP", "VINN", "OUTP", "OUTN", "COUTP", "COUTN"):
        if token not in source:
            raise RuntimeError(f"Export missing {token}")
    if "dc=vinp" not in source or "dc=vinn" not in source:
        raise RuntimeError("Parameterized input sources missing")
    return {"mos_instances": devices,
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest()}


def build_deck(source: str, differential_mv: float) -> str:
    vinp = 0.45 + differential_mv * 0.0005
    vinn = 0.45 - differential_mv * 0.0005
    # OA export declares unresolved design variables. Resolve only that
    # top-level testbench parameter line; preserve the exported DUT subckt.
    if source.count("parameters vinn vinp") != 1:
        raise RuntimeError("Unexpected exported design-variable declaration")
    deck = source.replace(
        "parameters vinn vinp",
        f"parameters vinn={vinn:.12g} vinp={vinp:.12g}", 1,
    )
    return deck + "\ntran_decision tran stop=12n maxstep=2p\nsave OUTP OUTN CLK VINP VINN\n"


def crossing(times: list[float], values: list[float], threshold: float,
             start: float, stop: float, direction: int) -> float | None:
    for index in range(1, min(len(times), len(values))):
        t0, t1 = times[index - 1], times[index]
        if t1 < start or t0 > stop:
            continue
        a, b = direction * values[index - 1], direction * values[index]
        if a < threshold <= b:
            fraction = (threshold - a) / (b - a) if b != a else 0.0
            point = t0 + fraction * (t1 - t0)
            if start <= point <= stop:
                return point
    return None


def nearest(times: list[float], values: list[float], t: float) -> float:
    index = min(range(len(times)), key=lambda k: abs(times[k] - t))
    return values[index]


def analyze(data: dict, differential_mv: float) -> dict:
    needed = ("time", "CLK", "OUTP", "OUTN")
    missing = [key for key in needed if key not in data]
    if missing:
        raise RuntimeError(f"Missing PSF signals: {missing}; available={list(data)}")
    times = [float(v) for v in data["time"]]
    clock = [float(v) for v in data["CLK"]]
    outp = [float(v) for v in data["OUTP"]]
    outn = [float(v) for v in data["OUTN"]]
    signed = [(p - n) * (1 if differential_mv > 0 else -1)
              for p, n in zip(outp, outn)]
    edge = crossing(times, clock, 0.45, 4.9e-9, 5.2e-9, 1)
    decision = crossing(times, signed, 0.45, 5e-9, 7e-9, 1)
    if edge is None:
        raise RuntimeError("Clock rising edge not found")
    result = {
        "input_differential_mv": differential_mv,
        "clock_rise_ns": edge * 1e9,
        "decision_ns": None if decision is None else decision * 1e9,
        "resolution_ps": None if decision is None else (decision - edge) * 1e12,
        "reset_outp_v": nearest(times, outp, 4.9e-9),
        "reset_outn_v": nearest(times, outn, 4.9e-9),
        "decision_outp_v": nearest(times, outp, 6.5e-9),
        "decision_outn_v": nearest(times, outn, 6.5e-9),
        "second_reset_outp_v": nearest(times, outp, 9.9e-9),
        "second_reset_outn_v": nearest(times, outn, 9.9e-9),
    }
    result["nominal_pass"] = bool(
        result["reset_outp_v"] > 0.81 and result["reset_outn_v"] > 0.81
        and result["second_reset_outp_v"] > 0.81
        and result["second_reset_outn_v"] > 0.81
        and result["resolution_ps"] is not None
        and result["resolution_ps"] <= 1500
        and (result["decision_outp_v"] - result["decision_outn_v"])
        * (1 if differential_mv > 0 else -1) > 0.45
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--case-mv", type=float, action="append")
    args = parser.parse_args()
    export_dir = ROOT / "netlist" / TB
    client = VirtuosoClient.from_env(profile=args.profile)
    result = client.schematic.export_netlist(
        LIB, TB, export_dir, simulator="spectre", recreate_all=True, timeout=180)
    source_path = Path(result["input_file"])
    source = source_path.read_text(encoding="utf-8")
    provenance = assert_export(source)
    provenance.update({"cellview": f"{LIB}/{TB}/schematic",
                       "source_file": str(source_path), "model_corner": "TT",
                       "supply_v": 0.9, "temperature_c": 27,
                       "simulator": "Spectre 21.1 (bridge t28_io)",
                       "output_format": "psfascii"})
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    if args.export_only:
        print(json.dumps(provenance, indent=2))
        return 0

    results = []
    failures = 0
    for differential_mv in (args.case_mv or CASES_MV):
        label = f"{'p' if differential_mv > 0 else 'n'}{abs(differential_mv):.6f}mV"
        deck = ROOT / "decks" / f"{label}.scs"
        deck.parent.mkdir(parents=True, exist_ok=True)
        deck.write_text(build_deck(source, differential_mv), encoding="utf-8")
        work = ROOT / "spectre" / label
        simulator = SpectreSimulator.from_env(
            spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
            spectre_args=spectre_mode_args("spectre"), timeout=600,
            work_dir=work, output_format="psfascii", profile=args.profile)
        run = simulator.run_simulation(deck, {})
        case = {"name": label, "differential_mv": differential_mv,
                "ok": run.ok, "status": run.status.value,
                "errors": run.errors[:10], "warnings": run.warnings[:10]}
        psf = work / f"{label}.raw" / "tran_decision.tran.tran"
        if run.ok and psf.is_file():
            parsed = parse_spectre_psf_ascii(psf)
            case["parse_errors"] = parsed.errors
            if not parsed.errors:
                case.update(analyze(parsed.data, differential_mv))
        else:
            case["missing_psf"] = str(psf)
        results.append(case)
        if not case.get("nominal_pass", False):
            failures += 1
    summary = {"provenance": provenance, "cases": results,
               "nominal_all_pass": failures == 0}
    destination = ROOT / "summary.json"
    destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
