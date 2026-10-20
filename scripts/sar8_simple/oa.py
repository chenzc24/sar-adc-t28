"""Build only the new sar8s hierarchy through the proven bridge builder."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

from circuit import LIB, TOP, Cell, hierarchy
from virtuoso_bridge import VirtuosoClient

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_simple"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")

# Reuse readback/CDF/schematic/symbol infrastructure without changing its
# source, old receipts, cells, outputs, or script entry points.
spec = importlib.util.spec_from_file_location("_sar8s_oa_builder", ROOT / "scripts/sar8_async/oa.py")
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)
builder.OUT = OUT
dump = builder.dump


def bench(strongarm=False):
    c = Cell("tb_sar8s_strongarm" if strongarm else "tb_sar8s_logic", [], [])
    c.add("VVDD", "vdc", {"PLUS": "VDD", "MINUS": "gnd!"}, "analogLib", vdc="SUP")
    # No conversion is valid before the first COMPLETE acquisition. The
    # 1-ns leading guard aligns the legacy plant's frame counter explicitly.
    c.add("VSAMPLE", "vpulse", {"PLUS": "SAMPLE", "MINUS": "gnd!"}, "analogLib",
          v1="0", v2="SUP", td="1n", pw="40n", per="100n", tr="20p", tf="20p")
    c.add("VVIN", "vdc", {"PLUS": "VIN", "MINUS": "gnd!"}, "analogLib", vdc="VIN_DIFF")
    top = hierarchy()[-1]
    c.add("XCTRL", TOP, {p: "gnd!" if p == "VSS" else p for p in top.inputs + top.outputs})
    plant = {p: p for p in ["VDD", "VIN", "SAMPLE", "CMP_CLK", "TOPP", "TOPN"]}
    plant.update(VSS="gnd!", P="MODEL_P" if strongarm else "COMP_P", N="MODEL_N" if strongarm else "COMP_N")
    # Ideal binary DAC observes the ACTUAL P-high reference selects, not an
    # independently computed expected code. N/switch exclusivity audited too.
    plant.update({f"C{i}": f"BP_H{i}" for i in range(8)})
    c.add("XPLANT", "sar8a_plant", plant, pattern_mode="PATTERN_MODE", pattern_word="PATTERN_WORD",
          fault_mode="FAULT_MODE", fault_bit="FAULT_BIT", fault_frame="FAULT_FRAME",
          min_delay_s="COMP_DELAY", delay_spread_s="DELAY_SPREAD")
    if strongarm:
        c.add("XCOMP", "sar_strongarm_t28", {"CLK": "CMP_CLK", "VINP": "TOPP", "VINN": "TOPN",
              "OUTP": "COMP_P", "OUTN": "COMP_N", "VDD": "VDD", "VSS": "gnd!"})
    nets = top.outputs + ["COMP_P", "COMP_N", "TOPP", "TOPN"] + (["MODEL_P", "MODEL_N"] if strongarm else [])
    for index, net in enumerate(nets):
        c.add(f"RM{index:02d}", "res", {"PLUS": net, "MINUS": "gnd!"}, "analogLib", r="1T")
        if net.startswith(("BP_", "BN_", "D")) or net in ("CMP_CLK", "COMP_P", "COMP_N"):
            c.add(f"CL{index:02d}", "cap", {"PLUS": net, "MINUS": "gnd!"}, "analogLib",
                  c="5f" if net.startswith("D") else "10f")
    return c


def preflight(c):
    info = c.library.get(LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28", info
    assert info.technology_library == "tsmcN28", info
    dump("library.json", dataclasses.asdict(info))
    windows = c.list_windows(); dump("preflight_windows.json", windows)
    names = {obj.name for obj in hierarchy()} | {"tb_sar8s_logic", "tb_sar8s_strongarm"}
    for window in windows:
        assert not any(name + " " in window["name"] for name in names), window
    for name in sorted(names):
        if builder.exists(c, name):
            assert (OUT / "owned" / (name + ".json")).exists(), f"Unowned target exists: {name}"
    for dependency in ("sar8a_plant", "sar_strongarm_t28"):
        assert builder.exists(c, dependency, "symbol"), dependency
    print("PREFLIGHT_OK", info.path, info.technology_library, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["preflight", "build", "readback", "check", "export", "open", "dependencies"])
    ap.add_argument("--cell"); ap.add_argument("--rebuild-owned", action="store_true")
    ap.add_argument("--zoom", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--tag", default="initial")
    args = ap.parse_args()
    c = VirtuosoClient.from_env(profile="t28_io")
    objects = hierarchy() + [bench(), bench(True)]
    if args.command == "dependencies":
        info = c.library.get(LIB)
        path = OUT / "dependencies/sar8a_plant_remote.va"
        path.parent.mkdir(parents=True, exist_ok=True)
        result = c.download_file(info.path + "/sar8a_plant/veriloga/veriloga.va", path)
        assert result.ok, result.errors
        local = ROOT / "models/veriloga/sar8a_plant.va"
        hashes = {"local_sha256": hashlib.sha256(local.read_bytes()).hexdigest(),
                  "remote_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        assert hashes["local_sha256"] == hashes["remote_sha256"], hashes
        dump("dependencies/plant_hashes.json", hashes)
        dump("dependencies/strongarm_readback_after.json", c.schematic.read(LIB, "sar_strongarm_t28", param_filters=None))
        print("DEPENDENCIES_OK", hashes, flush=True); return
    if args.command == "preflight":
        preflight(c); return
    if args.command == "export":
        assert args.cell in {"tb_sar8s_logic", "tb_sar8s_strongarm"}
        folder = OUT / "exports" / args.cell / args.tag
        assert not (folder / "input.scs").exists(), "Use a fresh export tag"
        result = c.schematic.export_netlist(LIB, args.cell, folder, simulator="spectre", timeout=300)
        dump(f"exports/{args.cell}/{args.tag}/receipt.json", result)
        p = Path(result["input_file"]); assert p.exists()
        print("EXPORTED", str(p), hashlib.sha256(p.read_bytes()).hexdigest(), flush=True); return
    if args.command == "open":
        assert args.cell in {o.name for o in objects}
        result = c.open_window(LIB, args.cell, view="schematic")
        assert not result.errors and result.output not in ("", "nil"), result
        windows = [window for window in c.list_windows() if
                   f"{LIB} {args.cell} schematic" in window["name"]]
        assert len(windows) == 1, windows
        if args.zoom:
            x0, y0, x1, y1 = args.zoom
            assert x1 > x0 and y1 > y0
            number = int(windows[0]["num"])
            # IC618 SKILL Finder verifies hiZoomIn(w_window, l_bBox);
            # the troubleshooting reference's hiZoom alias is unavailable.
            result = c.execute_skill(f'hiZoomIn(window({number}) list({x0}:{y0} {x1}:{y1}))')
            assert not result.errors, result.errors
            result = c.execute_skill(f'hiRedraw(window({number}))')
            assert not result.errors, result.errors
        dump("review/" + args.cell + "_window.json", windows[0])
        path = OUT / "review" / (args.cell + ".png")
        capture = c.screenshot(output=path, target=int(windows[0]["num"]))
        assert capture.ok, capture.errors
        print("REVIEW_OPEN", args.cell, str(path), flush=True); return
    if args.cell:
        objects = [o for o in objects if o.name == args.cell]
    assert objects
    if args.command == "build":
        preflight(c)
    for obj in objects:
        if args.command in ("readback", "check"):
            if args.command == "check":
                assert (OUT / "owned" / (obj.name + ".json")).exists()
                with c.schematic.modify(LIB, obj.name, timeout=180):
                    pass
            builder.readback(c, obj)
        else:
            builder.build(c, obj, rebuild=args.rebuild_owned)


if __name__ == "__main__":
    main()
