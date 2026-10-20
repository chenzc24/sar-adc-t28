"""All-bank, both-polarity terminal-stress reconstruction and reset metrics."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import numpy as np

from support import OUT, blocks, dump, load, statements


def instances(text):
    result = {}
    for line in statements(text):
        match = re.match(r"\s*(\w+)\s+\(([^)]*)\)\s+(\w+)\b", line)
        if match:
            result[match[1]] = (match[2].split(), match[3])
    return result


def warnings(result):
    log = (Path(result["metadata"]["output_dir"]).parent / "spectre.out").read_text(errors="replace")
    return {
        "printed_cmi": len(re.findall(r"WARNING \(CMI-", log)),
        "suppressed": sum(map(int, re.findall(r"(\d+) warnings suppressed", log))),
        "instances": sorted(set(re.findall(r"WARNING \(CMI-\d+\): ([^:]+):", log))),
        "lte_relaxations": log.count("WARNING (SPECTRE-16780)"),
    }


def analyze(name, category):
    result = load(f"{category}/{name}_result.json")
    assert result["ok"], result["errors"]
    case = load(f"cases/{name}.json")
    data = load(f"{category}/{name}_waveform.json")
    wave = {k: np.asarray(v, dtype=float) for k, v in data.items() if k != "units"}
    time = wave["time"]
    assert np.isfinite(time).all() and (np.diff(time) > 0).all()
    end = case["case"].get("stop_ns", 300) * 1e-9
    assert time[-1] >= end - 1e-15, (name, time[-1], end)
    different = {k: list(v.shape) for k, v in wave.items() if len(v) != len(time)}
    assert not different, (name, len(time), different)
    assert all(np.isfinite(v).all() for v in wave.values())
    ns = time * 1e9
    reset_mask = (ns % 100 >= 89.9) & (ns % 100 <= 99)
    settled_mask = (ns >= 100) & reset_mask
    text = (OUT / "decks" / f"{name}.scs").read_text()
    sub = blocks(text)
    top_inst = instances(text)
    cdac_nodes, cdac_master = top_inst["XCDAC"]
    cdac_body = sub[cdac_master]
    ports = statements(cdac_body)[0].split()[2:]
    assert len(ports) == len(cdac_nodes)
    cdac_map = dict(zip(ports, cdac_nodes, strict=True))
    leaf_instances = instances(cdac_body)
    assert sum(n.startswith("XS") for n in leaf_instances) == 18, "All banks must be reconstructed"
    zeros = np.zeros_like(time)

    def voltage(net):
        net = net.lower().replace("\\", "")
        if net == "0":
            return zeros
        assert net in wave, (name, net)
        return wave[net]

    all_worst = {"value_v": -1}
    reset_worst = {"value_v": -1}
    steady_reset_worst = {"value_v": -1}
    terminal_peaks = []
    device_count = 0
    for leaf, (nodes, master) in leaf_instances.items():
        if not leaf.startswith("XS"):
            continue
        leaf_body = sub[master]
        leaf_ports = statements(leaf_body)[0].split()[2:]
        mapping = dict(zip(leaf_ports, nodes, strict=True))

        def resolve(node):
            if node in mapping:
                parent = mapping[node]
                return cdac_map[parent] if parent in cdac_map else "XCDAC." + parent
            return f"XCDAC.{leaf}.{node}"

        for device, (nets, model) in instances(leaf_body).items():
            if not model.startswith(("nch_", "pch_")):
                continue
            device_count += 1
            assert len(nets) == 4
            d, g, s, b = [voltage(resolve(net)) for net in nets]
            pairs = {"vds": d-s, "vgs": g-s, "vgd": g-d, "vbs": b-s, "vbd": b-d}
            for label, values in pairs.items():
                for mask, target in ((np.ones_like(time, dtype=bool), all_worst),
                                     (reset_mask, reset_worst), (settled_mask, steady_reset_worst)):
                    if not mask.any():
                        continue
                    indices = np.flatnonzero(mask)
                    idx = indices[np.argmax(np.abs(values[mask]))]
                    if abs(values[idx]) > target["value_v"]:
                        target.update(value_v=float(abs(values[idx])), signed_v=float(values[idx]),
                                      instance=f"XCDAC.{leaf}.{device}", terminal=label,
                                      time_ns=float(ns[idx]))
                if np.max(np.abs(values)) > .990001:
                    idx = int(np.argmax(np.abs(values)))
                    terminal_peaks.append({"instance": f"XCDAC.{leaf}.{device}", "terminal": label,
                                           "abs_v": float(abs(values[idx])), "time_ns": float(ns[idx])})
    assert device_count >= 216 and reset_worst["value_v"] >= 0
    bottoms = [wave[f"xcdac.b{s}{b}"] for s in "pn" for b in range(9)]
    reset_max = max(float(x[reset_mask].max()) for x in bottoms)
    reset_min = min(float(x[reset_mask].min()) for x in bottoms)
    sup = case["parameters"]["SUP"]
    vdiff = case["parameters"]["VDIFF"]
    ls = 2 * sup / 256
    last_cycle = int((end * 1e9 - 99) // 100)
    sample_ns = 100 * last_cycle + 89
    at = lambda key, instant: float(np.interp(instant, ns, wave[key]))
    code = sum(int(at(f"dout<{b}>", sample_ns) > sup/2) * (1 << b) for b in range(8))
    fixed = case["parameters"]["FIXED_CODE"]
    expected_code = fixed if case["parameters"]["OPEN_LOOP"] and fixed >= 0 else int(np.clip(np.floor((vdiff+sup)/ls), 0, 255))
    residuals = []
    if not case["parameters"]["OPEN_LOOP"]:
        for j in range(8):
            instant = 100 * last_cycle + 45.9 + 5*j
            trial = sum(int(at(f"sel1<{b}>", instant) > sup/2) * (1 << b) for b in range(8))
            expected = vdiff + sup - trial*ls
            residuals.append((at("topp", instant)-at("topn", instant)-expected)*1000)
    reset_error = max(abs(at(f"xcdac.b{s}{b}", 100*last_cycle+98)-sup/2)
                      for s in "pn" for b in range(9)) * 1000
    hold_error = None
    if case["parameters"]["OPEN_LOOP"] and fixed == 128:
        hold_error = 1000 * (at("topp", 100*last_cycle+70)-at("topn", 100*last_cycle+70)-vdiff)
    currents = {key: float(np.max(np.abs(wave[key][reset_mask]))*1000)
                for key in ("vvdd:p", "vvcm:p", "vrefhigh:p", "vreflow:p")}
    row = {"name": name, "category": category, "variant": case["variant"], "case": case["case"],
           "reconstructed_mos_count": device_count,
           "result_ok": True, "warnings": warnings(result), "all_terminal_worst": all_worst,
           "reset_terminal_worst": reset_worst, "post_startup_reset_worst": steady_reset_worst,
           "terminal_violations": terminal_peaks, "reset_bottom_max_v": reset_max,
           "reset_bottom_min_v": reset_min, "reset_error_at_98ns_mv": reset_error,
           "last_code": code, "expected_code": expected_code, "code_pass": code == expected_code,
           "comparison_raw_max_mv": max(map(abs, residuals), default=None),
           "fixed128_hold_error_mv": hold_error,
           "reset_source_abs_current_ma": currents,
           "reset_stress_pass": reset_worst["value_v"] <= .990001,
           "all_core_stress_pass": all_worst["value_v"] <= .990001,
           "scope": "reconstructed all reference-switch/driver MOS terminals; not foundry signoff"}
    dump(f"metrics/{name}.json", row)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("category")
    parser.add_argument("--names", nargs="+")
    args = parser.parse_args()
    rows = []
    for path in sorted((OUT / args.category).glob("*_result.json")):
        name = path.stem.removesuffix("_result")
        if args.names and name not in args.names:
            continue
        row = analyze(name, args.category)
        rows.append(row)
        print(name, "reset", round(row["reset_terminal_worst"]["value_v"], 6),
              "all", round(row["all_terminal_worst"]["value_v"], 6),
              "bottom", round(row["reset_bottom_min_v"], 6), round(row["reset_bottom_max_v"], 6),
              "CMI", row["warnings"]["printed_cmi"], "code", row["last_code"],
              "err", row["comparison_raw_max_mv"], flush=True)
    dump(f"summary_{args.category}{'_partial' if args.names else ''}.json", rows)


if __name__ == "__main__":
    main()
