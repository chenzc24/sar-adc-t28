#!/usr/bin/env python3
"""Export the OA transmission-gate fixture through the Virtuoso netlister."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIBRARY = "SAR_ADC_T28"
CELL = "tb_tg_switch_char"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/switch_characterization/netlist/tb_tg_switch_char"),
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    result = client.schematic.export_netlist(
        LIBRARY,
        CELL,
        args.output_root,
        simulator="spectre",
        recreate_all=True,
        timeout=120,
    )
    input_file = Path(result["input_file"])
    if not input_file.is_file():
        raise RuntimeError(f"Missing exported input.scs: {input_file}")
    summary = {
        "library": LIBRARY,
        "cell": CELL,
        "input_file": str(input_file),
        "source_file": result["source_file"],
        "source_dir": result["source_dir"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
