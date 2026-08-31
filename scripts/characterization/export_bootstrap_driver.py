#!/usr/bin/env python3
"""Export the owned transistor-level bootstrap hierarchy through Spectre."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIBRARY = "SAR_ADC_T28"
CELL = "tb_sar_bootstrap_transient"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("output/bootstrap_driver_design/netlist/tb_sar_bootstrap_transient"),
    )
    args = parser.parse_args()
    client = VirtuosoClient.from_env(profile=args.profile)
    result = client.schematic.export_netlist(
        LIBRARY, CELL, args.output_dir, simulator="spectre", recreate_all=True, timeout=180
    )
    input_file = Path(result["input_file"])
    if not input_file.is_file():
        raise RuntimeError(f"Missing exported input.scs: {input_file}")
    printable = {
        key: str(result[key])
        for key in ("input_file", "source_file", "source_dir")
    }
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
