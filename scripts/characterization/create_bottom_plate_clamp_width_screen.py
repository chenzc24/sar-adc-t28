#!/usr/bin/env python3
"""Build independently named narrow-width T28 top-clamp OA variants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from virtuoso_bridge import VirtuosoClient

import create_bootstrap_bottom_plate_eval as base


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "bootstrap_bottom_plate_clamp_width_screen.yaml"
OUTPUT = ROOT / "output" / "bootstrap_bottom_plate_clamp_width_screen"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="t28_io")
    parser.add_argument("--width-nm", type=int, required=True, choices=(100, 185, 200, 250, 500))
    parser.add_argument("--rebuild-owned", action="store_true",
                        help="Replace only the exact selected experimental CDAC/TB cells")
    args = parser.parse_args()
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    variant = next(v for v in config["variants"] if v["clamp_width_nm"] == args.width_nm)
    assert variant["pdk_finger_width_nm"] * variant["multiplier"] == args.width_nm

    base.CDAC = f"sar_cdac_bottom_plate_clamp_w{args.width_nm}_eval_10b"
    base.TB = f"tb_sar_bottom_plate_clamp_w{args.width_nm}_eval"
    base.T28_CLAMP = True
    client = VirtuosoClient.from_env(profile=args.profile)
    info = client.library.get(base.LIB)
    if info.technology_library != "tsmcN28":
        raise RuntimeError(f"Unexpected technology binding: {info}")
    if args.rebuild_owned:
        base.rebuild_owned(client)
    for cell in (base.CDAC, base.TB):
        if base.exists(client, cell):
            raise RuntimeError(f"Refusing to overwrite {base.LIB}/{cell}")

    base.create_cdac(client)
    for side in ("P", "N"):
        for stem in ("SCLAMPTOP", "SCLAMPLSB"):
            base.set_owned_params(client, base.CDAC, f"{stem}{side}",
                                  Wfg=f"{variant['pdk_finger_width_nm']}n",
                                  simM=str(variant["multiplier"]))
    with client.schematic.modify(base.LIB, base.CDAC, timeout=120):
        pass
    base.create_symbol(client)
    base.create_tb(client)

    result = {
        cell: {
            "schematic": client.schematic.read(base.LIB, cell,
                                               include_positions=False,
                                               param_filters=None),
            "markers": base.markers(client, cell),
        }
        for cell in (base.CDAC, base.TB)
    }
    result["symbol_ports"] = client.symbol.read_ports(base.LIB, base.CDAC)
    if any(result[cell]["markers"] for cell in (base.CDAC, base.TB)):
        raise RuntimeError("Schematic check markers remain")
    out = OUTPUT / f"w{args.width_nm}" / "readback"
    out.mkdir(parents=True, exist_ok=True)
    (out / "readback.json").write_text(json.dumps(result, indent=2) + "\n",
                                       encoding="utf-8")
    print(json.dumps({"width_nm": args.width_nm,
                      "cdac_instances": len(result[base.CDAC]["schematic"]["instances"]),
                      "tb_instances": len(result[base.TB]["schematic"]["instances"]),
                      "markers": [result[base.CDAC]["markers"],
                                  result[base.TB]["markers"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
