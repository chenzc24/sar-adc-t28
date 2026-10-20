"""Exact-OA candidate runs; no DUT rewrites after native export."""
from __future__ import annotations

import argparse
import re

from experiment import configure
from support import OUT, OLD, batch, blocks, digest, dump, load, sha, selected_variant


def prepare(name, cell="tb_cdac8_reset_nominal", **case):
    source = OUT / "oa_netlists" / cell / "primary/input.scs"
    text = source.read_text()
    bootstrap = blocks(text)["sar_bootstrap_canvas_flat_8b"]
    original = (OLD / "oa_netlists/tb_cdac8_nominal/balanced/input.scs").read_text()
    assert bootstrap == blocks(original)["sar_bootstrap_canvas_flat_8b"]
    # Every waveform property of the input clock is retained.
    clock = lambda s: re.search(r"(?m)^VPHI .*\n[^\n]*", s)[0]
    assert clock(text) == clock(original), "Input PHI drift"
    configured, parameters = configure(text, **case)
    assert blocks(configured) == blocks(text), "Exact OA DUT must not be patched"
    path = OUT / "decks" / (name + ".scs")
    if path.exists():
        existing = load(f"cases/{name}.json")
        assert path.read_text() == configured and existing["source_sha256"] == sha(source)
        assert existing["case"] == case and existing["parameters"] == parameters
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(configured, encoding="utf-8")
    dump(f"cases/{name}.json", {
        "name": name, "variant": selected_variant(), "case": case,
        "parameters": parameters, "source": str(source), "source_sha256": sha(source),
        "bootstrap_sha256": digest(bootstrap), "phi_unchanged": True,
        "scope": "exact_saved_oa_dut_only_test_parameters_and_simulator_settings_changed",
    })
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["nominal", "literal", "strongarm", "pvt", "integration"])
    args = parser.parse_args()
    if args.mode == "nominal":
        paths = [prepare("oa_nominal", stop_ns=300),
                 prepare("oa_fixed128", vdiff=.8, open_loop=1, fixed_code=128, stop_ns=300),
                 prepare("oa_negative", vdiff=-.8, stop_ns=200)]
    elif args.mode in ("literal", "integration"):
        paths = [prepare("oa_literal", cell="tb_cdac8_reset_literal", stop_ns=300),
                 prepare("oa_literal_fixed128", cell="tb_cdac8_reset_literal", vdiff=.8,
                         open_loop=1, fixed_code=128, stop_ns=300)]
        if args.mode == "integration":
            paths.append(prepare("oa_strongarm", cell="tb_cdac8_reset_strongarm", stop_ns=200))
    elif args.mode == "strongarm":
        paths = [prepare("oa_strongarm", cell="tb_cdac8_reset_strongarm", stop_ns=300)]
    else:
        cases = [("tt", .9, 27, x) for x in (-.453515625, 0, .8)]
        cases += [(corner, supply, temp, .453515625)
                  for corner in ("ss", "ff") for supply in (.81, .99) for temp in (-40, 125)]
        paths = [prepare(f"pvt_{corner}_{round(supply*1000)}_{temp}_{round(vdiff*1000)}",
                         vdiff=vdiff, sup=supply, corner=corner, temp=temp, stop_ns=200)
                 for corner, supply, temp, vdiff in cases]
    batch(paths, args.mode)


if __name__ == "__main__":
    main()
