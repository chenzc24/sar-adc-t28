"""Read-only baseline, available PDK passives and owned-name preflight."""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path

from virtuoso_bridge import VirtuosoClient

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_physical"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def dump(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--passive", action="append", default=[])
    args = parser.parse_args()
    c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
    info = c.library.get("SAR_ADC_T28")
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    windows = c.list_windows()
    dump("preflight/library.json", dataclasses.asdict(info))
    dump("preflight/windows.json", windows)
    cells = c.fetch('ddGetObj("tsmcN28")~>cells', ["name"])
    passives = sorted(row["name"] for row in cells if row["name"].lower().startswith(("r", "cfmom")))
    dump("preflight/passive_names.json", passives)
    print("PDK_PASSIVE_NAMES", passives, flush=True)
    targets = c.fetch('ddGetObj("SAR_ADC_T28")~>cells', ["name"])
    conflicts = [row["name"] for row in targets if row["name"].startswith("sar8p_")
                 or row["name"] in ("sar_logic_8b_physical", "sar_bootstrap_flat_8b_p",
                                         "sar_adc8_join_r4", "tb_sar_adc8_join_r4")]
    dump("preflight/name_conflicts.json", conflicts)
    assert not conflicts, conflicts
    for name in ("sar_adc8_join_r3", "sar_bootstrap_canvas_flat_8b", "sar8j_r1_cdac",
                 "sar_strongarm_t28", "sar_logic_8b_async_simple"):
        data = c.schematic.read("SAR_ADC_T28", name, include_positions=True, param_filters=None)
        dump(f"baseline/{name}.json", data)
        print("BASELINE_READ", name, len(data["instances"]), flush=True)
    for name in args.passive:
        assert name in passives
        symbol = c.symbol.read_ports("tsmcN28", name)
        params = c.fetch(f'cdfGetCellCDF(ddGetObj("tsmcN28" "{name}"))~>parameters',
                         ["name", "type", "defValue", "value", "choices", "editable", "callback"])
        dump(f"pdk/{name}.json", dict(symbol=symbol, parameters=params))
        brief = [{k: p[k] for k in ("name", "type", "defValue", "choices", "editable")}
                 for p in params]
        print("PDK_INTERFACE", name, json.dumps(dict(symbol=symbol, parameters=brief)), flush=True)
    print("READONLY_PREFLIGHT_OK", "windows", len(windows), flush=True)


if __name__ == "__main__":
    main()
