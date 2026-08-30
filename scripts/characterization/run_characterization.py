#!/usr/bin/env python3
"""Run first-pass TT device characterization from Virtuoso-exported netlists.

EVAS is intentionally not used here: these decks contain PDK transistors,
DC/AC analyses, and device currents, all of which require Spectre's analog
solver.  The exported schematic netlist remains the circuit source of truth;
this script only adds the requested analysis and save statements.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii


CELLS = ("tb_nmos_char", "tb_pmos_char", "tb_cap_char")


def _insert_before_info(netlist: str, statements: str) -> str:
    marker = "modelParameter info"
    if marker not in netlist:
        raise ValueError(f"Netlist insertion marker missing: {marker}")
    return netlist.replace(marker, statements.rstrip() + "\n" + marker, 1)


def _build_nmos(base: str) -> str:
    base = base.replace("VDS (VD 0) vsource dc=0 type=dc", "VDS (VD 0) vsource dc=900m type=dc")
    return _insert_before_info(
        base,
        """
dc_transfer dc dev=VGS param=dc start=0 stop=900m step=5m
save MN0:oppoint VGS:p VDS:p VD VG
""",
    )


def _build_pmos(base: str) -> str:
    base = base.replace("VD (VD 0) vsource dc=900m type=dc", "VD (VD 0) vsource dc=0 type=dc")
    return _insert_before_info(
        base,
        """
dc_transfer dc dev=VG param=dc start=900m stop=0 step=-5m
save MP0:oppoint VG:p VD:p VDD:p VD VG VDD
""",
    )


def _build_cap(base: str) -> str:
    base = base.replace(
        "VBIAS (VCAP 0) vsource dc=0 type=dc",
        "VBIAS (VCAP 0) vsource dc=0 mag=1 type=sine",
    )
    return _insert_before_info(
        base,
        """
ac_cap ac start=1K stop=10G dec=20
save C0:1 VBIAS:p VCAP
""",
    )


BUILDERS = {
    "tb_nmos_char": _build_nmos,
    "tb_pmos_char": _build_pmos,
    "tb_cap_char": _build_cap,
}

ANALYSIS_FILES = {
    "tb_nmos_char": "dc_transfer.dc",
    "tb_pmos_char": "dc_transfer.dc",
    "tb_cap_char": "ac_cap.ac",
}

SIGNAL_ALLOWLIST = {
    "tb_nmos_char": {
        "dc", "VD", "VG", "VDS:p", "MN0:id", "MN0:gm", "MN0:gds",
        "MN0:gmoverid", "MN0:self_gain", "MN0:ft", "MN0:vth",
    },
    "tb_pmos_char": {
        "dc", "VD", "VG", "VDD", "VD:p", "MP0:id", "MP0:gm", "MP0:gds",
        "MP0:gmoverid", "MP0:self_gain", "MP0:ft", "MP0:vth",
    },
    "tb_cap_char": {"freq", "C0:1", "VBIAS:p", "VCAP"},
}


def _value_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return {
            "count": len(value),
            "first": repr(value[0]) if value else None,
            "last": repr(value[-1]) if value else None,
        }
    return {"value": repr(value)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument(
        "--netlist-root",
        type=Path,
        default=Path("output/pdk_characterization/netlists"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/pdk_characterization/spectre"),
    )
    args = parser.parse_args()

    args.output_root.mkdir(parents=True, exist_ok=True)
    deck_dir = args.output_root / "decks"
    deck_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {}
    failures = 0
    for cell in CELLS:
        source = args.netlist_root / cell / "input.scs"
        if not source.is_file():
            raise FileNotFoundError(f"Exported netlist missing: {source}")
        deck = deck_dir / f"{cell}.scs"
        deck.write_text(BUILDERS[cell](source.read_text(encoding="utf-8")), encoding="utf-8")

        work_dir = args.output_root / cell
        simulator = SpectreSimulator.from_env(
            spectre_cmd=os.getenv("SPECTRE_CMD", "spectre"),
            spectre_args=spectre_mode_args("spectre"),
            timeout=600,
            work_dir=work_dir,
            output_format="psfascii",
            profile=args.profile,
        )
        result = simulator.run_simulation(deck, {})
        analysis_path = work_dir / f"{cell}.raw" / ANALYSIS_FILES[cell]
        analysis_data: dict[str, Any] = {}
        analysis_errors: list[str] = []
        if result.ok and analysis_path.is_file():
            parsed = parse_spectre_psf_ascii(analysis_path)
            analysis_data = parsed.data
            analysis_errors = parsed.errors

        summary[cell] = {
            "status": result.status.value,
            "ok": result.ok,
            "errors": result.errors[:10],
            "warnings": result.warnings[:10],
            "analysis_errors": analysis_errors,
            "signals": {
                key: _value_summary(value)
                for key, value in sorted(analysis_data.items())
                if key in SIGNAL_ALLOWLIST[cell]
            },
        }
        if not result.ok:
            failures += 1

    summary_path = args.output_root / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"summary: {summary_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
