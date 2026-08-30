#!/usr/bin/env python3
"""Export the PDK characterization schematics through Virtuoso's netlister."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


LIBRARY = "SAR_ADC_T28"
CELLS = ("tb_nmos_char", "tb_pmos_char", "tb_cap_char")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/pdk_characterization/netlists"),
    )
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    summary: dict[str, object] = {}
    for cell in CELLS:
        result = client.schematic.export_netlist(
            LIBRARY,
            cell,
            args.output_root / cell,
            simulator="spectre",
            recreate_all=True,
            timeout=120,
        )
        input_file = Path(result["input_file"])
        if not input_file.is_file():
            raise RuntimeError(f"Missing exported input.scs for {cell}: {input_file}")
        summary[cell] = {
            "input_file": str(input_file),
            "source_file": result["source_file"],
            "source_dir": result["source_dir"],
        }

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
