"""Immutable OA-derived Spectre cases for the simplified native controller."""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

from oa import OUT, ROOT

spec = importlib.util.spec_from_file_location("_sar8s_spectre", ROOT / "scripts/sar8_async/simulate.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def signals():
    return (["SAMPLE", "VIN", "CMP_CLK", "COMP_P", "COMP_N", "TOPP", "TOPN",
             "XCTRL.PHI_W", "XCTRL.PHI_U", "XCTRL.DATA", "XCTRL.ACTIVE",
             "XCTRL.XTIM.QUIET", "XCTRL.XTIM.QUIET_D", "XCTRL.XTIM.RAW"]
            + [f"D{i}" for i in range(8)] + [f"XCTRL.T{i}" for i in range(8)]
            + [f"XCTRL.CODE{i}" for i in range(8)]
            + [f"B{bank}_{rail}{i}" for bank in ("P", "N") for rail in ("H", "L") for i in range(8)])


def make_case(kind, tag):
    strongarm = kind == "strongarm"
    cell = "tb_sar8s_strongarm" if strongarm else "tb_sar8s_logic"
    path = OUT / "exports" / cell / tag / "input.scs"
    source = path.read_text(encoding="utf-8")
    params = runner.defaults()
    stop = "100n"; corner = "tt"; temp = 27; supply = .9
    if kind in ("two_cycles", "strongarm"):
        stop = "202n" if kind == "two_cycles" else "100n"
        if kind == "two_cycles":
            source, count = re.subn(r"(?m)^VVIN .*(?:\n[ \t]+.*)*", "VVIN (VIN 0) vsource type=pwl wave=[0 0.123 101n 0.123 102n -0.3 202n -0.3]", source)
            assert count == 1, "Expected exactly one VVIN source"
    elif kind.startswith("pattern_"):
        params.update(PATTERN_MODE=1, PATTERN_WORD=int(kind.split("_")[1]))
    elif kind in ("slow", "fast"):
        params.update(PATTERN_MODE=1, PATTERN_WORD=165,
                      COMP_DELAY="1200p" if kind == "slow" else "20p",
                      DELAY_SPREAD="40p" if kind == "slow" else "0")
    elif kind in ("ss", "ff"):
        corner, supply, temp = ("ss", .81, 125) if kind == "ss" else ("ff", .99, -40)
        params.update(PATTERN_MODE=1, PATTERN_WORD=165, SUP=supply)
    elif kind == "recovery":
        stop = "300n"
        params.update(PATTERN_MODE=1, PATTERN_WORD=165, FAULT_MODE=1, FAULT_BIT=3, FAULT_FRAME=1)
    elif kind == "interrupt":
        stop = "155n"
        params.update(PATTERN_MODE=1, PATTERN_WORD=165)
        source, count = re.subn(r"(?m)^VSAMPLE .*(?:\n[ \t]+.*)*",
            "VSAMPLE (SAMPLE 0) vsource type=pwl wave=[0 0 1n 0 1.02n SUP 41.02n SUP 41.04n 0 55n 0 55.02n SUP 95.02n SUP 95.04n 0 155n 0]", source)
        assert count == 1
    else:
        raise ValueError(kind)
    return runner.deck(source, params, stop, signals(), corner=corner, temp=temp, maxstep="50p"), dict(
        cell=cell, export_tag=tag, source_export=str(path.relative_to(ROOT)),
        supply_v=supply, corner=corner, temperature_c=temp, physical_cdac=False,
        comparator="native_StrongARM" if strongarm else "behavioral_variable_delay")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=["two_cycles", "pattern_0", "pattern_255", "pattern_85", "pattern_170", "slow", "fast", "ss", "ff", "recovery", "interrupt", "strongarm"])
    ap.add_argument("--tag", default="initial")
    ap.add_argument("--name"); ap.add_argument("--maxstep", default="50p")
    args = ap.parse_args()
    text, context = make_case(args.case, args.tag)
    text = text.replace("maxstep=50p", "maxstep=" + args.maxstep)
    name = args.name or args.case + "_" + args.tag + "_aps"
    runner.dump("contexts/" + name + ".json", context)
    result = runner.run(name, text, scope="native_sar8s_controller_ideal_DAC_" + context["comparator"], mode="aps")
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
