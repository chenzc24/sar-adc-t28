#!/usr/bin/env python3
"""Export the three bootstrap-main-switch OA fixtures through Spectre."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIBRARY = "SAR_ADC_T28"
CELLS = (
    "tb_bootstrap_core_main_char",
    "tb_bootstrap_dnw_main_char",
    "tb_bootstrap_18_main_char",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/bootstrap_main_switch_screening/netlist"),
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    result = {}
    for cell in CELLS:
        exported = client.schematic.export_netlist(
            LIBRARY,
            cell,
            args.output_root / cell,
            simulator="spectre",
            recreate_all=True,
            timeout=120,
        )
        input_file = Path(exported["input_file"])
        if not input_file.is_file():
            raise RuntimeError(f"Missing exported input.scs: {input_file}")
        result[cell] = {
            "input_file": str(input_file),
            "source_file": exported["source_file"],
            "source_dir": exported["source_dir"],
        }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
