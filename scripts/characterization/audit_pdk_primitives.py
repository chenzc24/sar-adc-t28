#!/usr/bin/env python3
"""Read-only audit of the PDK primitives used by SAR_ADC_T28.

The script queries symbol terminals through the bridge's public reader and
queries cell CDF metadata through a read-only SKILL expression.  It does not
open, edit, or save any PDK cellview.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from virtuoso_bridge import VirtuosoClient


CELLS = (
    ("tsmcN28", "nch_mac"),
    ("tsmcN28", "pch_mac"),
    ("tsmcN28", "cfmom_2t"),
    ("tsmcN28", "cfmom_wo"),
    ("tsmcN28", "pcapacitor"),
    ("analogLib", "vdc"),
    ("analogLib", "gnd"),
)

PARAMETER_ALLOWLIST = {
    "nch_mac": {"model", "description", "l", "Wfg", "w", "fingers", "nf", "simM"},
    "pch_mac": {"model", "description", "l", "Wfg", "w", "fingers", "nf", "simM"},
    "cfmom_2t": {
        "model", "description", "calcParam", "Wfinger", "Sfinger", "Lfinger",
        "Nfinger", "StartMn", "StopMn", "mismatch", "c", "m", "pdkVersion",
    },
    "cfmom_wo": {
        "model", "description", "calcParam", "Wfinger", "Sfinger", "Lfinger",
        "Nfinger", "StartMn", "StopMn", "mismatch", "c", "m", "pdkVersion",
    },
    "pcapacitor": {"model", "description", "c", "w", "l"},
    "vdc": {"vdc", "acm", "acp", "srcType"},
    "gnd": set(),
}


def _cdf_parameters(client: VirtuosoClient, library: str, cell: str) -> list[dict[str, object]]:
    expression = f'cdfGetCellCDF(ddGetObj("{library}" "{cell}"))~>parameters'
    parameters = client.fetch(
        expression,
        ["name", "type", "defValue", "value", "units", "prompt", "choices", "editable"],
        timeout=30,
    )
    allowed = PARAMETER_ALLOWLIST[cell]
    return [parameter for parameter in parameters if parameter.get("name") in allowed]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    client = VirtuosoClient.from_env(profile=args.profile)
    inventory: dict[str, object] = {}
    for library, cell in CELLS:
        symbol = client.symbol.read_ports(library, cell)
        inventory[f"{library}/{cell}"] = {
            "terminals": [term["name"] for term in symbol.get("terms", [])],
            "pin_order": symbol.get("pinOrder", []),
            "cdf_parameters": _cdf_parameters(client, library, cell),
        }

    rendered = json.dumps(inventory, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
