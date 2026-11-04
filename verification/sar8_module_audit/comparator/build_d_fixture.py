"""Build local, uncompiled comparator fixtures from one hash-locked source.

No simulator, network client, managed recipe or circuit-parameter editor exists
here. Native leaf subcircuits are copied verbatim after LF normalization. Only
testbench wrappers remove feedback and expose diagnostic inputs; sources stay read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = HERE / "fixture_spec.json"
DEST = HERE / "generated" / "deterministic_v2"
START_NS = (20, 60, 100, 140, 180, 220)
SIGNS = (1, 1, -1, 1, -1, -1)
VDIFF = 0.0017578125
CORNERS = {"tt": ("tt", 0.9, 27), "sscold": ("ss", 0.81, -40)}
TIMING_KEEP = {"X016", "X015", "X004", "X000", "X014", "X013", "X010",
               "X009", "X008", "X005", "X003", "X002", "X006", "XD_RAW_D",
               "X011", "XD_WRITE_D"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def blocks(text: str) -> dict[str, str]:
    found = list(re.finditer(r"(?ms)^subckt (\w+) .*?^ends \1\b", text))
    result = {m[1]: m[0] for m in found}
    if len(result) != len(found):
        raise ValueError("Duplicate subcircuit definitions")
    return result


def statements(block: str) -> list[str]:
    return [line.strip() for line in block.replace("\\\n", " ").splitlines()
            if line.strip() and not line.lstrip().startswith("//")]


def ports(block: str) -> list[str]:
    return statements(block)[0].split()[2:]


def instances(block: str):
    for line in statements(block)[1:-1]:
        match = re.fullmatch(r"(\w+)\s+\(([^)]*)\)\s+(\w+)(.*)", line)
        if not match:
            raise ValueError("Unsupported source statement: " + line)
        yield match[1], match[2].split(), match[3], match[4].strip()


def closure(definitions: dict[str, str], roots: list[str]) -> list[str]:
    seen: set[str] = set()

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        for _, _, master, _ in instances(definitions[name]):
            if master in definitions:
                visit(master)

    for name in roots:
        visit(name)
    return sorted(seen)


def flatten(definitions, root_cell, root_binding, prefix="XDUT"):
    """Expand device terminals for structural fanout audit, without model reads."""
    result = {}

    def walk(cell, binding, scope):
        def node(name):
            if name == "0":
                return "0"
            if name in binding:
                return binding[name]
            if name == "VDD!":
                return "VDD!"
            return scope + "." + name

        for name, args, master, params in instances(definitions[cell]):
            resolved = [node(n) for n in args]
            full = scope + "." + name
            if master in definitions:
                pins = ports(definitions[master])
                if len(pins) != len(resolved):
                    raise ValueError("Port count mismatch: " + full)
                walk(master, dict(zip(pins, resolved)), full)
            else:
                result[full] = {"model": master, "nodes": resolved,
                                "parameters": " ".join(params.split())}

    walk(root_cell, root_binding, prefix)
    return result


def fanout(devices, node):
    found = []
    for instance, record in devices.items():
        pins = "dgsb" if record["model"].startswith(("nch_", "pch_")) else None
        for i, value in enumerate(record["nodes"]):
            if value == node:
                found.append({"instance": instance,
                              "terminal": pins[i] if pins else str(i + 1),
                              "model": record["model"],
                              "parameter_sha256": sha(record["parameters"].encode())})
    return sorted(found, key=lambda x: (x["instance"], x["terminal"]))


def check_source(spec):
    source = {s["id"]: s for s in spec["sources"]}
    for item in source.values():
        path = ROOT / item["path"]
        if sha(path.read_bytes()) != item["sha256"]:
            raise ValueError("Frozen source hash mismatch: " + item["id"])
    return source


def rewrite_wrappers(original):
    # Keep the receiver and forward validity/write cone. X016/X013/XD_WRITE_D
    # and X015 retain original PHI_W and clock input loads, not clock feedback.
    lines = ["subckt audit_cmp_timing CMP_CLK COMP_N COMP_P DATA PHI_U PHI_W SAMPLE VDD VSS"]
    found = set()
    for name, args, master, params in instances(original["sar8p_timing"]):
        if name in TIMING_KEEP:
            lines.append("    " + name + " (" + " ".join(args) + ") " + master
                         + (" " + params if params else ""))
            found.add(name)
    if found != TIMING_KEEP:
        raise ValueError("Frozen forward-cone instance set changed")
    timing = "\n".join(lines + ["ends audit_cmp_timing"])

    ctrl_ports = ["CMP_CLK"] + ["CODE" + str(i) for i in range(8)]
    ctrl_ports += ["COMP_N", "COMP_P"] + ["D" + str(i) for i in range(8)]
    ctrl_ports += ["PHI_U", "SAMPLE_GUARD", "REG_RESET"]
    ctrl_ports += ["TOKEN" + str(i) for i in range(8)] + ["VDD", "VSS"]
    lines = ["subckt audit_cmp_ctrl " + " ".join(ctrl_ports),
             "    XTIM (CMP_CLK COMP_N COMP_P DATA PHI_U PHI_W SAMPLE_GUARD VDD VSS) audit_cmp_timing"]
    for name, args, master, params in instances(original["sar8i_ctrl"]):
        if name.startswith("XBIT"):
            bit = int(name[4:])
            args = ["REG_RESET" if n == "SAMPLE" else "TOKEN" + str(bit)
                    if n == "T" + str(bit) else n for n in args]
            lines.append("    " + name + " (" + " ".join(args) + ") " + master
                         + (" " + params if params else ""))
    ctrl = "\n".join(lines + ["ends audit_cmp_ctrl"])
    return {"audit_cmp_timing": timing, "audit_cmp_ctrl": ctrl}


def stimulus_points():
    start = [(0.0, 0.0)]
    vp = [(0.0, 0.45 + SIGNS[0] * VDIFF / 2)]
    vn = [(0.0, 0.45 - SIGNS[0] * VDIFF / 2)]
    prior = SIGNS[0]
    for at, sign in zip(START_NS, SIGNS):
        start.extend([(float(at), 0.0), (at + .1, "SUP"),
                      (at + 12., "SUP"), (at + 12.1, 0.0)])
        update = at - 8
        vp.extend([(update, .45 + prior * VDIFF / 2),
                   (update + .1, .45 + sign * VDIFF / 2)])
        vn.extend([(update, .45 - prior * VDIFF / 2),
                   (update + .1, .45 - sign * VDIFF / 2)])
        prior = sign
    start.append((260.0, 0.0))
    vp.append((260.0, vp[-1][1]))
    vn.append((260.0, vn[-1][1]))
    return {"CMP_CLK": start, "TOPP": vp, "TOPN": vn,
            "REG_RESET": [(0., "SUP"), (10., "SUP"), (10.1, 0.), (260., 0.)]}


def pwl(points):
    return " ".join(f"{t:.12g}n {v if isinstance(v, str) else format(v, '.15g')}"
                    for t, v in points)


def prepare():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    source = check_source(spec)
    original = blocks((ROOT / source["rx2_dut"]["path"]).read_text())
    modified = dict(original)
    modified.update(rewrite_wrappers(original))
    selected = closure(modified, ["audit_cmp_ctrl", "sar_strongarm_t28"])
    # The ADC analog chain is deliberately absent from this D-family fixture.
    if any(any(tag in n for tag in ["bootstrap", "cdac", "refword"])
           for n in selected):
        raise ValueError("Fixture expanded back into ADC analog hierarchy")
    module_ports = ["TOPP", "TOPN", "CMP_CLK", "SAMPLE_GUARD", "REG_RESET"]
    module_ports += ["TOKEN" + str(i) for i in range(8)] + ["VDD", "VSS"]
    module_ports += ["D" + str(i) for i in range(8)]
    code = " ".join("CODE" + str(i) for i in range(8))
    data = " ".join("D" + str(i) for i in range(8))
    wrapper = "subckt audit_comparator_d " + " ".join(module_ports) + "\n"
    wrapper += ("    XCTRL (CMP_CLK " + code + " COMP_N COMP_P " + data
                + " PHI_U SAMPLE_GUARD REG_RESET "
                + " ".join("TOKEN" + str(i) for i in range(8))
                + " VDD VSS) audit_cmp_ctrl\n")
    wrapper += "    XCOMP (CMP_CLK COMP_N COMP_P VDD TOPN TOPP VSS) sar_strongarm_t28\n"
    load_lines = []
    for name, args, master, params in instances(original["sar_adc8_join_r4"]):
        if name in ["CL_COMP_N", "CL_COMP_P", "CL_CMP_CLK"]:
            args = ["VSS" if n == "0" else n for n in args]
            line = "    " + name + " (" + " ".join(args) + ") " + master + " " + params
            load_lines.append(line)
    if len(load_lines) != 3:
        raise ValueError("Three exact MOM loads required")
    wrapper += "\n".join(load_lines) + "\nends audit_comparator_d\n"
    modified["audit_comparator_d"] = wrapper
    cell_text = ("// Local comparator fixture. NOT SPECTRE COMPILED.\n"
                 + "\n\n".join(modified[n] for n in selected) + "\n\n" + wrapper)

    old_binding = {p: p for p in ports(original["sar_adc8_join_r4"])}
    old_flat = flatten(original, "sar_adc8_join_r4", old_binding)
    new_binding = {p: p for p in module_ports}
    new_binding.update(TOPP="XDUT.TOPP", TOPN="XDUT.TOPN", CMP_CLK="XDUT.CMP_CLK",
                       VDD="VDD!", VSS="0")
    new_flat = flatten(modified, "audit_comparator_d", new_binding)
    protected = ["XDUT.COMP_P", "XDUT.COMP_N",
                 "XDUT.XCTRL.XTIM.PR", "XDUT.XCTRL.XTIM.NR",
                 "XDUT.XCTRL.DATA", "XDUT.XCTRL.PHI_W"]
    preserved = {}
    for node in protected:
        old, new = fanout(old_flat, node), fanout(new_flat, node)
        if old != new:
            raise ValueError("Lost/changed receiver fanout: " + node)
        preserved[node] = old
    # All comparator/receiver MOS parameters and terminal bindings stay identical.
    core_prefix = ("XDUT.XCOMP.", "XDUT.XCTRL.XTIM.X002.",
                   "XDUT.XCTRL.XTIM.X003.")
    immutable = [n for n in old_flat if n.startswith(core_prefix)]
    for name in immutable:
        if old_flat[name] != new_flat[name]:
            raise ValueError("Comparator or receiver changed: " + name)
    removed_clock = [item for item in fanout(old_flat, "XDUT.CMP_CLK")
                     if item not in fanout(new_flat, "XDUT.CMP_CLK")]
    if len(removed_clock) != 2 or any(".X025.X001." not in r["instance"]
                                    or r["terminal"] != "d" for r in removed_clock):
        raise ValueError("Unexpected clock-node load removal")
    new_clock = [item for item in fanout(new_flat, "XDUT.CMP_CLK")
                 if item not in fanout(old_flat, "XDUT.CMP_CLK")]
    if new_clock:
        raise ValueError("Unexpected extra native clock load")
    boundaries = ["XDUT.PHI_U", "XDUT.ACTIVE", "XDUT.SAMPLE_INT"]
    boundaries += ["XDUT.CODE" + str(i) for i in range(8)]
    boundaries += ["D" + str(i) for i in range(8)]
    removed = {}
    for node in boundaries:
        old = fanout(old_flat, node)
        now = fanout(new_flat, node)
        absent = [item for item in old if item not in now]
        if absent:
            removed[node] = absent

    audit = {
        "status": "structural_review_only_not_Spectre_compiled",
        "retained_native_MOS": sum(v["model"].startswith(("nch_", "pch_")) for v in new_flat.values()),
        "original_ADC_MOS": sum(v["model"].startswith(("nch_", "pch_")) for v in old_flat.values()),
        "unchanged_comparator_receiver_primitive_count": len(immutable),
        "native_subcircuit_hashes": {n: sha(original[n].encode()) for n in selected if n in original},
        "preserved_terminal_fanout": preserved,
        "clock_cut": {
            "removed_native_driver": "XDUT.XCTRL.XTIM.X025 sar8p_buf (both inverters removed)",
            "removed_driver_primitives": [{"instance": n, **record}
                                          for n, record in old_flat.items()
                                          if n.startswith("XDUT.XCTRL.XTIM.X025.")],
            "removed_clock_node_terminals": removed_clock,
            "retained_clock_node_terminals": fanout(new_flat, "XDUT.CMP_CLK"),
            "ideal_driver": "VCMP_CLK -> CMP_CLK",
            "original_producer_parallel_connection": False,
            "limitation": "Original clock output junction loading and source impedance are removed; ideal diagnostic clock cannot qualify original asynchronous timing."
        },
        "removed_timing_instances": [{"instance": "XDUT.XCTRL.XTIM." + n, "master": master,
                                      "original_nodes": args}
                                     for n, args, master, _ in instances(original["sar8p_timing"])
                                     if n not in TIMING_KEEP],
        "removed_controller_instances": [{"instance": "XDUT.XCTRL." + n, "master": master}
                                         for n, _, master, _ in instances(original["sar8i_ctrl"])
                                         if n != "XTIM" and not n.startswith("XBIT")],
        "register_diagnostic_bindings": {"reset": "REG_RESET independent from SAMPLE_GUARD",
                                         "token_inputs": "TOKEN0=SUP; TOKEN1..TOKEN7=0; no advancement",
                                         "leaf_bit_cells": "original eight sar8p_bit unchanged"},
        "native_MOS_partition": {
            "N4_comparator": sum(n.startswith("XDUT.XCOMP.") and r["model"].startswith(("nch_", "pch_")) for n, r in new_flat.items()),
            "receiver_forward_cone": sum(n.startswith("XDUT.XCTRL.XTIM.") and r["model"].startswith(("nch_", "pch_")) for n, r in new_flat.items()),
            "eight_register_loads": sum(n.startswith("XDUT.XCTRL.XBIT") and r["model"].startswith(("nch_", "pch_")) for n, r in new_flat.items())
        },
        "excluded_ADC_top_instances": [name for name, _, _, _ in instances(original["sar_adc8_join_r4"])
                                       if name not in ["XCTRL", "XCOMP", "CL_COMP_N", "CL_COMP_P", "CL_CMP_CLK"]],
        "removed_boundary_terminal_fanout": removed,
        "boundary_limitations": [
            "Reference-word, sample sequencing and analog-chain loads beyond PHI_U/ACTIVE/CODE/D are absent and enumerated above.",
            "Complete immediate DATA, PHI_W, PR/NR and COMP_P/N native loads are identical; the two removed CMP_CLK driver drain terminals are explicit.",
            "PHI_U/reset/registered-output absolute delays cannot qualify the original ADC without restoring the excluded boundary loads.",
            "Long reset intervals are diagnostic stimulus, not a new allocated comparison or ADC sample-time budget.",
            "Physical reset completion and input-update-during-reset are future native-wave checks, not established by this structural build."
        ]
    }
    source_deck = (ROOT / source["rx2_deck"]["path"]).read_text()
    includes = [line for line in source_deck.splitlines() if line.startswith('include "') and 'section=' in line]
    if len(includes) != 7:
        raise ValueError("Unexpected model include list")
    stimuli = stimulus_points()
    save = ["TOPP", "TOPN", "CMP_CLK", "SAMPLE_GUARD", "REG_RESET", "VDD!", "D0", "D7",
            "XDUT.COMP_P", "XDUT.COMP_N", "XDUT.PHI_U",
            "XDUT.XCTRL.DATA", "XDUT.XCTRL.PHI_W",
            "XDUT.XCTRL.XTIM.X002.N", "XDUT.XCTRL.XTIM.X003.N"]
    save += ["XDUT.XCTRL.XTIM." + n for n in
             ["PR", "NR", "NRB", "RAW", "RAW_D", "DEC", "WRITE_REQ"]]
    save += ["XDUT.XCOMP." + n for n in ["X", "Y", "TAIL"]]
    physical_aliases = {"XDUT.TOPP": "TOPP", "XDUT.TOPN": "TOPN",
                        "XDUT.CMP_CLK": "CMP_CLK"}
    save += [physical_aliases.get(n, n) for item in new_flat.values()
             for n in item["nodes"] if n != "0"]
    save += [name + ":" + str(port)
             for name in new_flat if name.startswith(core_prefix)
             for port in range(1, 5)]
    save += ["VVDD:1", "VCMP_CLK:1"]
    save = sorted(set(save))
    artifacts = {"cells.scs": cell_text, "boundary_audit.json": json_text(audit)}
    cases = []
    for label, (corner, sup, temp) in CORNERS.items():
        head = ["// Local deterministic comparator/receiver diagnostic. NOT SPECTRE COMPILED.",
                "// Ideal inputs; no CDAC kickback, noise, mismatch or ADC timing qualification.",
                "simulator lang=spectre", "global 0 VDD!", f"parameters SUP={sup}"]
        head += [line.replace("ssmacro_mos_moscap", corner + "macro_mos_moscap") for line in includes]
        head += ['include "cells.scs"',
                 "XDUT (" + " ".join("VDD!" if p == "VDD" else "0" if p == "VSS"
                                       else p for p in module_ports) + ") audit_comparator_d",
                 "VVDD (VDD! 0) vsource dc=SUP"]
        for node, points in stimuli.items():
            head.append("V" + node + " (" + node + " 0) vsource type=pwl wave=[" + pwl(points) + "]")
        head.append("VSAMPLE_GUARD (SAMPLE_GUARD 0) vsource dc=0")
        head += ["VTOKEN" + str(i) + " (TOKEN" + str(i) + " 0) vsource dc="
                 + ("SUP" if i == 0 else "0") for i in range(8)]
        head += [f"simulatorOptions options temp={temp} tnom=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13 method=gear2only",
                 "tran_d tran stop=260n maxstep=5p errpreset=conservative",
                 "saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no"]
        head += ["save " + n for n in save]
        artifacts[label + ".scs"] = "\n".join(head) + "\n"
        cases.append({"id": label, "entry": label + ".scs", "corner": corner,
                      "vdd_v": sup, "temperature_c": temp,
                      "only_environment_differs": True,
                      "pass": None, "spectre_compiled": False})
    manifest = {
        "status": "not_Spectre_compiled", "simulation_pass": None,
        "source_run": spec["frozen_candidate"]["run_id"],
        "source_DUT_sha256": source["rx2_dut"]["sha256"],
        "fixture_spec_sha256": sha(SPEC.read_bytes()),
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "native_cell_policy": "Exact LF-normalized source text; wrapper changes explicitly audited",
        "files": {name: sha(text.encode()) for name, text in artifacts.items()},
        "cases": cases,
        "stimulus": {"start_events_ns": list(START_NS), "input_signs": list(SIGNS),
                     "differential_input_abs_v": VDIFF, "CM_v": 0.45,
                     "input_update_before_start_ns": 8, "input_edge_ns": .1,
                     "clock_rise_fall_ns": .1, "clock_half_level_high_ns": 12.,
                     "register_reset": "independent initial high until10ns, low after10.1ns",
                     "token": "independent fixed onehot TOKEN0, no token chain",
                     "observation_stop_ns": 260, "timing_budget_allocated": False},
        "required_future_checks": [
            "physical comparator reset before every input update/start",
            "correct resolved sign and stable DATA before actual write aperture",
            "no accepted reset/false/duplicate write",
            "all relevant MOS terminal peaks at native points",
            "no re-use of these ideal-input traces as charge-kickback evidence"
        ],
        "unknown_budgets": spec["unknown_budgets"],
        "extraction_scope": "Comparator and exact receiver/write fanout; excluded outer boundary loads are a declared limitation requiring parent review",
        "remote_submission": False, "managed_recipe_created": False
    }
    artifacts["manifest.json"] = json_text(manifest)
    return artifacts, audit


def emit(artifacts, destination=DEST):
    """Create a new immutable generation; never replace different old output."""
    for name, text in artifacts.items():
        path = destination / name
        if path.exists() and path.read_bytes() != text.encode():
            raise FileExistsError("Refusing to replace immutable fixture: " + str(path))
    destination.mkdir(parents=True, exist_ok=True)
    for name, text in artifacts.items():
        path = destination / name
        if not path.exists():
            with path.open("xb") as out:
                out.write(text.encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create immutable local artifacts only")
    args = parser.parse_args()
    artifacts, audit = prepare()
    if args.write:
        emit(artifacts)
    print(json_text({"status": "not_Spectre_compiled", "local_structure_checks": "PASS",
                     "written": args.write, "files": list(artifacts),
                     "fixture_MOS": audit["retained_native_MOS"],
                     "original_ADC_MOS": audit["original_ADC_MOS"],
                     "protected_fanout_ports": len(audit["preserved_terminal_fanout"]),
                     "declared_external_load_boundaries": len(audit["removed_boundary_terminal_fanout"])}))


if __name__ == "__main__":
    main()
