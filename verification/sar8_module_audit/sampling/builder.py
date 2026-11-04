"""Prepare local, load-preserving SS-hot startup fixtures; never run a simulator.

The full native control/reference load shell is retained deliberately. This is
an intermediate isolation fixture, not a claimed minimal or qualified module.
Only the two native CMP_CLK output drivers are removed to expose an undriven
reset boundary. Retained device parameters and terminal connections are frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = HERE / "fixture_spec.json"
DRIVERS = {
    "XDUT.XCTRL.XTIM.X025.X001.MP",
    "XDUT.XCTRL.XTIM.X025.X001.MN",
}
CLOCK = "XDUT.CMP_CLK"
FORMAL_POINTS = [(101.0, "0"), (101.1, "SUP"), (141.0, "SUP"),
                 (141.1, "0"), (201.0, "0"), (201.1, "SUP"),
                 (241.0, "SUP"), (241.1, "0")]
PROTECTED_SOURCES = ["VVINP", "VVINN", "VREFLOW", "VREFHIGH", "RINP",
                     "RINN", "RREFP", "RREFN", "CREFP", "CREFN"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_params(text: str) -> str:
    return " ".join(text.split())


def parse_cells(text: str) -> dict:
    flat = text.replace("\\\n", " ")
    return {m[1]: (m[2].split(), m[3]) for m in re.finditer(
        r"(?ms)^subckt (\w+) ([^\n]+)\n(.*?)^ends \1", flat)}


def flatten(text: str) -> dict:
    cells = parse_cells(text)
    devices = {}

    def walk(master, path, bind):
        ports, body = cells[master]
        for m in re.finditer(r"(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)", body):
            label, raw_nodes, model, params = m.groups()
            name = path + "." + label
            nodes = [bind.get(n, n if n in {"0", "VDD!"} else path + "." + n)
                     for n in raw_nodes.split()]
            if model in cells:
                assert len(nodes) == len(cells[model][0]), name
                walk(model, name, dict(zip(cells[model][0], nodes)))
            else:
                devices[name] = {"nodes": nodes, "model": model,
                                 "parameters": normalized_params(params)}

    top = "sar_adc8_join_r4"
    walk(top, "XDUT", dict(zip(cells[top][0], cells[top][0])))
    return devices


def safe_node(node: str) -> str:
    return node.replace(".", "__")


def mos(device: dict) -> bool:
    return device["model"].startswith(("nch_", "pch_"))


def native_drivers(devices: dict, node: str) -> set:
    return {name for name, d in devices.items()
            if mos(d) and node in [d["nodes"][0], d["nodes"][2]]}


def make_fixture(devices: dict) -> tuple[str, dict]:
    assert native_drivers(devices, CLOCK) == DRIVERS
    kept = {n: d for n, d in devices.items() if n not in DRIVERS}
    assert not native_drivers(kept, CLOCK), "ideal reset boundary still has native driver"
    lines = ["// Local extracted load shell; not Spectre compiled.",
             "// CMP_CLK output MP/MN removed before exposing CMP_RESET.",
             "subckt sampling_reset_fixture SAMPLE VDD! VINN VINP VREFN VREFP CMP_RESET "
             + " ".join("D" + str(i) for i in range(8)) + " 0"]
    rows = {}
    for index, (name, d) in enumerate(kept.items()):
        prefix = "M" if mos(d) else "C" if d["model"] == "cfmom_2t" else "R"
        label = prefix + f"{index:04d}"
        nodes = ["CMP_RESET" if n == CLOCK else safe_node(n) for n in d["nodes"]]
        lines.append(f"{label} ({' '.join(nodes)}) {d['model']} {d['parameters']}")
        rows[name] = dict(d, fixture_label=label, fixture_nodes=nodes)
    lines.append("ends sampling_reset_fixture")
    return "\n".join(lines) + "\n", rows


def sample_points(case: str) -> list:
    if case == "high_dc_short_low":
        # A genuine 101ns opening requires low immediately beforehand. The
        # high-DC control therefore has a declared 100ps low plateau, not zero
        # low history and not the exact historical first-frame stimulus.
        before = [(0.0, "SUP"), (100.8, "SUP"), (100.9, "0")]
    elif case == "low_dc_precharge":
        before = [(0.0, "0")]
    else:
        raise ValueError(case)
    return before + FORMAL_POINTS


def source_lines(text: str) -> dict:
    return {m[1]: m[0] for m in re.finditer(r"(?m)^(\w+) \([^\n]+$", text)}


def make_deck(case: str, original_tb: str) -> str:
    src = source_lines(original_tb)
    includes = re.findall(r'(?m)^include ".*" section=.*$', original_tb)
    assert sum("ttmacro_mos_moscap" in s for s in includes) == 1
    includes = [s.replace("ttmacro_mos_moscap", "ssmacro_mos_moscap") for s in includes]
    wave = " ".join(f"{t:g}n {v}" for t, v in sample_points(case))
    lines = ["// SS / 0.81V / 125C local startup diagnosis; not Spectre compiled.",
             "simulator lang=spectre", "global 0 VDD!", "parameters SUP=0.81"]
    lines += includes + ['include "fixture_dut.scs"',
        "XF (SAMPLE VDD! VINN VINP VREFN VREFP CMP_RESET D0 D1 D2 D3 D4 D5 D6 D7 0) sampling_reset_fixture"]
    # Preserve original input values, PWL transitions, source impedances and
    # reference network verbatim in both controls.
    lines += [src[k] for k in PROTECTED_SOURCES]
    lines += [src[f"COUT{i}"] for i in range(8)]
    lines += ["VVDD (VDD! 0) vsource dc=SUP type=dc",
              "VCMP_RESET (CMP_RESET 0) vsource dc=0 type=dc",
              f"VSAMPLE (SAMPLE 0) vsource type=pwl wave=[{wave}]",
              "simulatorOptions options method=gear2only reltol=1e-6 vabstol=1e-8 "
              "iabstol=1e-13 temp=125 tnom=27 scalem=1.0 scale=1.0 "
              "gmin=1e-12 rforce=1 checklimitdest=psf",
              "saveOptions options save=allpub currents=selected subcktiprobes=no useprobes=no",
              "save VVDD:1 VREFHIGH:1 VREFLOW:1 VVINP:1 VVINN:1 VSAMPLE:1 VCMP_RESET:1",
              "// Observe one formal acquisition; future pulse edges retain 100ns period.",
              "tran_startup tran stop=160n maxstep=10p errpreset=conservative lteratio=10"]
    return "\n".join(lines) + "\n"


def fanout(devices: dict, node: str) -> list:
    entries = []
    for name, d in devices.items():
        for index, n in enumerate(d["nodes"]):
            if n == node:
                role = "dgsb"[index] if mos(d) else str(index + 1)
                entries.append({"instance": name, "terminal": role, "model": d["model"]})
    return entries


def inventory(original: dict, kept: dict, rows: dict) -> dict:
    watch = ["XDUT.SEQ_SAMPLE", "XDUT.SAMPLE_INT", "XDUT.PRESET",
             "XDUT.SAMPLE_MATCH", "XDUT.COMP_P", "XDUT.COMP_N", CLOCK]
    result = {"schema_version": 1, "scope": "physical control/reference load shell retained",
              "loads": {}, "removed_driver_input_load": [],
              "ideal_sources_on_retained_driver_outputs": []}
    for node in watch:
        before, after = fanout(original, node), fanout(kept, node)
        expected = [e for e in before if e["instance"] not in DRIVERS]
        assert after == expected, node
        result["loads"][node] = dict(original=before, retained=after,
            retained_count=len(after), original_count=len(before),
            only_declared_driver_removal=True)
    for name in sorted(DRIVERS):
        result["removed_driver_input_load"].append({"instance": name,
            "upstream_gate_node": original[name]["nodes"][1],
            "effect": "upstream final-driver input loses this native gate load; no claim of exact controller equivalence"})
    result["boundary"] = {"node": CLOCK, "fixture_port": "CMP_RESET",
        "removed_drivers": sorted(DRIVERS), "native_driver_count_after_cut": 0,
        "forced_value_v": 0, "role": "testbench comparator reset only"}
    result["all_devices"] = rows
    return result


def payloads() -> dict[str, bytes]:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for key, rec in spec["sources"].items():
        assert sha((ROOT / rec["path"]).read_bytes()) == rec["sha256"], key
    dut = (ROOT / spec["sources"]["candidate_dut"]["path"]).read_text(encoding="utf-8")
    tb = (ROOT / spec["sources"]["candidate_testbench"]["path"]).read_text(encoding="utf-8")
    devices = flatten(dut)
    assert len(devices) == 2508 and sum(mos(d) for d in devices.values()) == 1833
    fixture, rows = make_fixture(devices)
    kept = {n: d for n, d in devices.items() if n not in DRIVERS}
    inv = inventory(devices, kept, rows)
    outputs = {"fixture_dut.scs": fixture.encode(),
        "startup_high_dc_short_low.scs": make_deck("high_dc_short_low", tb).encode(),
        "startup_low_dc_precharge.scs": make_deck("low_dc_precharge", tb).encode(),
        "boundary_loads.json": (json.dumps(inv, indent=2) + "\n").encode()}
    manifest = {
        "schema_version": 1, "status": "local_prepared_not_Spectre_compiled",
        "simulator_invoked": False, "remote_operation": False, "recipe_created": False,
        "scope": "SS-hot paired startup-history diagnosis; one formal acquisition",
        "inputs": spec["sources"], "spec_sha256": sha(SPEC.read_bytes()),
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "retained_devices": len(kept), "retained_MOS": sum(mos(d) for d in kept.values()),
        "removed_native_driver_instances": sorted(DRIVERS),
        "retained_device_parameters_unchanged": True,
        "retained_device_connections_unchanged_except_boundary_alias": True,
        "physical_control_and_reference_load_shell_retained": True,
        "clock_fanout_preserved": [n for n in inv["loads"] if n != CLOCK],
        "comparator_reset_state": {"source_v": 0, "native_clock_drivers_removed_first": True},
        "requested_conditions": {"MOS_corner": "ss", "temperature_c": 125,
            "VDD_v": 0.81, "reference_v": [0, 0.9], "input_source_ohm_each": 50,
            "reference_source_ohm_each": 50, "reference_decap_f_each": 4e-12,
            "passives_corner": "tt", "noise": False, "mismatch": False, "PEX": False,
            "requested_reltol": 1e-6, "requested_maxstep_ps": 10,
            "effective_solver_settings_verified": False},
        "common_formal_clock": {"source_rise_start_ns": 101, "source_fall_start_ns": 141,
            "edge_duration_ns": 0.1, "period_ns": 100,
            "source_half_crossings_ns": [101.05, 141.05],
            "actual_SEQ_SAMPLE_crossings_ns": None, "closing_edge_shift_allowed": False},
        "measurement": {"preclose": "actual SEQ_SAMPLE falling half crossing minus0.2ns",
            "held_ns": 141.8, "held_requires": "after actual close, before any comparator/DAC action",
            "source_target_at_held_v": -0.81, "droop_limit_v": None,
            "startup_limit_v": None, "Cboot_initial_charge_forced": False},
        "cases": {"high_dc_short_low": {"SAMPLE_at_DC": "SUP",
            "fall_start_ns": 100.8, "low_plateau_ns": 0.1,
            "original_high_DC_failure_reproduction": False},
            "low_dc_precharge": {"SAMPLE_at_DC": "0", "low_until_ns": 101}},
        "single_external_source_delta": "VSAMPLE history only; identical source for t>=101ns",
        "strict_Bootstrap_only_causality": False,
        "limitations": ["high-DC control needs a short low phase to share a real101ns opening; this is not zero-precharge startup",
            "SAMPLE history also changes controller/reference DC state; Cboot contribution cannot be isolated by this pair alone",
            "comparator output-driver cut removes two upstream gate loads; fanout at actual sample clock and comparator outputs is retained",
            "inactive control load shell is larger than a minimal module and may still draw current or switch internally",
            "not original full-ADC reproduction, not functional ADC qualification, no power-ramp experiment",
            "must verify actual reference preset, comparator reset, physical sample window and native convergence before interpreting held error"],
        "artifacts": {n: {"sha256": sha(b), "bytes": len(b)} for n, b in outputs.items()}}
    outputs["fixture_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = payloads()
    for name, content in outputs.items():
        target = HERE / name
        if target.exists():
            assert target.read_bytes() == content, f"existing artifact differs: {name}; no overwrite"
        elif args.check:
            raise AssertionError("missing artifact: " + name)
        else:
            target.write_bytes(content)
    print(json.dumps({"artifacts": len(outputs), "reproduction": "PASS",
                      "simulator_invoked": False, "bytes": sum(map(len, outputs.values()))}))


if __name__ == "__main__":
    main()
