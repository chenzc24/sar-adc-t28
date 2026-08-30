#!/usr/bin/env python3
"""Extract compact design data from the first-pass Spectre characterization."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii


def _nearest_index(values: list[float], target: float) -> int:
    return min(range(len(values)), key=lambda index: abs(values[index] - target))


def _read(path: Path) -> dict[str, Any]:
    result = parse_spectre_psf_ascii(path)
    if not result.ok:
        raise RuntimeError(f"Failed to parse {path}: {result.errors}")
    return result.data


def _mos_rows(data: dict[str, Any], prefix: str, device: str) -> list[dict[str, float | str]]:
    sweep = data["dc"]
    ids = data[f"{prefix}:id"]
    gm = data[f"{prefix}:gm"]
    gds = data[f"{prefix}:gds"]
    gm_id = data[f"{prefix}:gmoverid"]
    vth = data[f"{prefix}:vth"]
    ft = data[f"{prefix}:ft"]
    gain = data[f"{prefix}:self_gain"]

    rows: list[dict[str, float | str]] = []
    for index, bias in enumerate(sweep):
        effective_gate = bias if device == "nmos" else 0.9 - bias
        rows.append(
            {
                "device": device,
                "vgs_or_vsg_v": effective_gate,
                "id_a": abs(ids[index]),
                "id_density_ua_per_um": abs(ids[index]) * 1e6,
                "gm_s": gm[index],
                "gds_s": gds[index],
                "gm_over_id_v_inv": gm_id[index],
                "intrinsic_gain_v_per_v": gain[index],
                "ro_ohm": 1.0 / gds[index] if gds[index] else math.inf,
                "ft_hz": ft[index],
                "vth_v": vth[index],
            }
        )
    return rows


def _design_points(rows: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    gm_id = [float(row["gm_over_id_v_inv"]) for row in rows]
    points = []
    for target in (20.0, 15.0, 10.0, 5.0):
        index = _nearest_index(gm_id, target)
        point = dict(rows[index])
        point["target_gm_over_id_v_inv"] = target
        points.append(point)
    return points


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spectre-root",
        type=Path,
        default=Path("output/pdk_characterization/spectre"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/pdk_characterization/analysis"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    nmos = _read(args.spectre_root / "tb_nmos_char/tb_nmos_char.raw/dc_transfer.dc")
    pmos = _read(args.spectre_root / "tb_pmos_char/tb_pmos_char.raw/dc_transfer.dc")
    cap = _read(args.spectre_root / "tb_cap_char/tb_cap_char.raw/ac_cap.ac")

    nrows = _mos_rows(nmos, "MN0", "nmos")
    prows = _mos_rows(pmos, "MP0", "pmos")
    mos_rows = nrows + prows
    _write_csv(args.output_dir / "mos_gmid_lookup.csv", mos_rows)

    cap_rows = []
    for frequency, current in zip(cap["freq"], cap["C0:1"]):
        capacitance = abs(current.imag) / (2.0 * math.pi * frequency)
        cap_rows.append(
            {
                "frequency_hz": frequency,
                "current_real_a": current.real,
                "current_imag_a": current.imag,
                "capacitance_f": capacitance,
                "capacitance_ff": capacitance * 1e15,
            }
        )
    _write_csv(args.output_dir / "cap_ac.csv", cap_rows)

    cap_freqs = [float(row["frequency_hz"]) for row in cap_rows]
    cap_values = [float(row["capacitance_ff"]) for row in cap_rows]
    selected_cap = {}
    for target in (1e3, 1e6, 1e8, 1e9, 1e10):
        index = _nearest_index(cap_freqs, target)
        selected_cap[f"{target:.0e}_hz"] = cap_values[index]

    low_frequency_cap_ff = median(
        value for frequency, value in zip(cap_freqs, cap_values) if frequency <= 1e8
    )
    cdf_cap_ff = 35.6304
    summary = {
        "conditions": {
            "corner": "TT macro model sections from the Virtuoso-exported netlist",
            "temperature_c": 27,
            "mos_geometry": "Wfg=1um, L=30nm, fingers=1, simM=1",
            "mos_drain_bias_v": 0.9,
            "cap_geometry": "cfmom_2t, Wfinger=50nm, Sfinger=50nm, Lfinger=4um, Nfinger=32, M1-M3",
        },
        "nmos": {
            "ion_at_vgs_0p9_a_per_um": float(nrows[-1]["id_a"]),
            "vth_at_vgs_0p9_v": float(nrows[-1]["vth_v"]),
            "gm_at_vgs_0p9_s_per_um": float(nrows[-1]["gm_s"]),
            "design_points": _design_points(nrows),
        },
        "pmos": {
            "ion_at_vsg_0p9_a_per_um": float(prows[-1]["id_a"]),
            "abs_vth_at_vsg_0p9_v": abs(float(prows[-1]["vth_v"])),
            "gm_at_vsg_0p9_s_per_um": float(prows[-1]["gm_s"]),
            "design_points": _design_points(prows),
        },
        "cfmom_2t": {
            "cdf_reported_capacitance_ff": cdf_cap_ff,
            "spectre_low_frequency_capacitance_ff": low_frequency_cap_ff,
            "difference_percent": 100.0 * (low_frequency_cap_ff - cdf_cap_ff) / cdf_cap_ff,
            "selected_frequency_capacitance_ff": selected_cap,
        },
    }
    (args.output_dir / "characterization_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=160)
    for rows, label in ((nrows, "NMOS nch_mac"), (prows, "PMOS pch_mac")):
        ax.semilogx(
            [float(row["id_density_ua_per_um"]) for row in rows],
            [float(row["gm_over_id_v_inv"]) for row in rows],
            linewidth=2,
            label=label,
        )
    ax.set_xlabel("|Id| density (uA/um)")
    ax.set_ylabel("gm/Id (1/V)")
    ax.set_title("T28 core MOS gm/Id at |VDS| = 0.9 V, TT, 27 C")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "mos_gmid.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=160)
    for rows, label in ((nrows, "NMOS nch_mac"), (prows, "PMOS pch_mac")):
        ax.semilogy(
            [float(row["vgs_or_vsg_v"]) for row in rows],
            [max(float(row["id_density_ua_per_um"]), 1e-6) for row in rows],
            linewidth=2,
            label=label,
        )
    ax.set_xlabel("VGS or VSG (V)")
    ax.set_ylabel("|Id| density (uA/um)")
    ax.set_title("T28 core MOS transfer characteristic, TT, 27 C")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "mos_transfer.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=160)
    cap_delta_af = [(value - cdf_cap_ff) * 1e3 for value in cap_values]
    ax.semilogx(cap_freqs, cap_delta_af, linewidth=2, color="#6f42c1")
    ax.axhline(0.0, linestyle="--", linewidth=1.2, color="#d62728", label="CDF value")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Spectre - CDF capacitance (aF)")
    ax.set_title("cfmom_2t capacitance consistency, TT, 27 C")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir / "cap_frequency.png")
    plt.close(fig)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
