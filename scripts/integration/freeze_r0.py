"""Prepare/check source fingerprints and the SAR8 join contract, never edit OA.

This is a selection/algebra checker, NOT the operational gate adapter or a
Spectre runner. The latter must be implemented and validated in a new target.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config/sar8_join_r0.yaml"
OUT = ROOT / "output/sar8_join_r0"
LOCK = ROOT / "verification/integration/join_r0_sources.json"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def config():
    return yaml.safe_load(CFG.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def object_digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def blocks(text):
    joined = re.sub(r"\\\n\s*", " ", text)
    return {m[1]: " ".join(m[2].split()) for m in
            re.finditer(r"(?ms)^subckt (\w+) (.*?)^ends \1", joined)}


def physical_words(code):
    assert isinstance(code, int) and 0 <= code <= 255
    return {"PH": 255-code, "PL": code, "NH": code, "NL": 255-code}


def map_conversion(native):
    """Active-high REQUEST mapping, not direct PMOS-gate polarity."""
    return {"PH": native["BN_H"], "PL": native["BN_L"],
            "NH": native["BP_H"], "NL": native["BP_L"]}


def ideal_gates(eh, el, supply=.9):
    assert (eh, el) in ((0, 0), (0, 1), (1, 0)), "Reject simultaneous rail enables"
    return {"p_gate": supply*(1-eh), "n_gate": supply*el}


def sample_events(rise_ns):
    cfg = config(); timing = cfg["sampling_reference_contract"]
    restore = rise_ns + timing["restore_guard_from_sample_rise_ns"]
    return {"bootstrap_sample_command_ns": rise_ns,
            "reference_restore_request_ns": restore,
            "earliest_new_rail_command_ns": restore+cfg["timing"]["changed_bank_BBM_ps"]/1000,
            "physical_midpoint_words": physical_words(128)}


def number_or_expression(value):
    text = str(value).strip()
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(meg|[TGMKkmunpf]?)(?:[AVFHO]?)", text)
    if match:
        scale = {"": 1., "T": 1e12, "G": 1e9, "M": 1e6, "meg": 1e6,
                 "K": 1e3, "k": 1e3, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
        return format(float(match[1])*scale[match[2]], ".12g")
    return re.sub(r"\s+", "", text)


def schematic_surface(data):
    items = []
    for p in data["instances"]:
        params = p.get("params", {}); geometry = {}
        for key, aliases in {"w": ("w", "Wfg"), "l": ("l",), "nf": ("fingers", "nf"),
                             "m": ("multi", "simM", "m"), "c": ("c",), "r": ("r",)}.items():
            value = next((params[a] for a in aliases if a in params), None)
            if value is not None:geometry[key] = number_or_expression(value)
        items.append({"name": p["name"], "lib": p["lib"], "cell": p["cell"],
                      "terms": p["terms"], "geometry": geometry})
    return {"instances": sorted(items, key=lambda x: x["name"]),
            "pins": {k: {p: v[p] for p in ("direction", "numBits") if p in v}
                     for k, v in data.get("pins", {}).items()}}


def capture():
    from virtuoso_bridge import VirtuosoClient
    assert not LOCK.exists(), "Existing R0 is immutable; use check or prepare a new revision"
    OUT.mkdir(parents=True, exist_ok=True)
    client = VirtuosoClient.from_env(profile="t28_io", timeout=20, log_to_ciw=False)
    lib = client.library.get("SAR_ADC_T28")
    assert lib.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and lib.technology_library == "tsmcN28"
    names = [c["name"] for c in read_json(ROOT / "verification/sar8_simple/cells.json")]
    assert len(names) == 21 and "sar_logic_8b_async_simple" in names
    result = {}
    for name in names + ["sar_bootstrap_canvas_flat_8b", "sar_strongarm_t28"]:
        current = client.schematic.read("SAR_ADC_T28", name, include_positions=False)
        prior = (ROOT / "output/sar8_simple/oa" / (name+".json")) if name in names else (
            ROOT / "output/integration_readiness_20261020" / (name+".json"))
        before = schematic_surface(read_json(prior)); after = schematic_surface(current)
        assert before == after, f"Existing selected schematic changed: {name}"
        (OUT / (name+".json")).write_text(json.dumps(current, indent=2), encoding="utf-8")
        result[name] = {"surface_sha256": object_digest(after), "matched_prior_topology_geometry_and_pins": True,
                        "instances": len(after["instances"])}
        print("READ_ONLY_MATCH", name, flush=True)
    record = {"captured_at_china": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
              "library": lib.name, "remote_path": lib.path, "technology": lib.technology_library,
              "cells": result, "oa_mutations": []}
    (OUT / "live_readback.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    return record


def lock_sources(live):
    cfg = config(); assert not LOCK.exists()
    native_path = ROOT / cfg["modules"]["controller"]["source"]
    native = blocks(native_path.read_text(encoding="utf-8"))
    controller_names = [c["name"] for c in read_json(ROOT / "verification/sar8_simple/cells.json")]
    summary = read_json(ROOT / "verification/sar8_simple/summary.json")
    case = next(c for c in summary["cases"] if c["context"]["comparator"] == "native_StrongARM")
    assert digest(native_path) == case["export_sha256"]
    assert hashlib.sha256(json.dumps({n: native[n] for n in sorted(controller_names)}, sort_keys=True).encode()).hexdigest() == summary["native_hierarchy_audit"]["hierarchy_sha256"]
    assert hashlib.sha256(native["sar_strongarm_t28"].encode()).hexdigest() == summary["native_hierarchy_audit"]["StrongARM_body_sha256"]
    selected = ROOT / cfg["modules"]["reference_switch"]["source"]
    refs = blocks(selected.read_text(encoding="utf-8"))
    metrics = read_json(ROOT / "docs/figures/cdac8_uniform_scale/metrics.json")
    three = [r for r in metrics["cases"] if r["factor"] == 3]
    assert len(three) == 6 and all(r["result_ok"] and r["bounded_pass"] for r in three)
    assert "parameters MP_RATIO=3 MN_RATIO=3" in selected.read_text(encoding="utf-8")
    for bit in range(8):
        text = refs[f"cdac8_dr_sw_b{bit}"]
        assert len(re.findall(r"\b(?:pch_mac|nch_mac)\b", text)) == 2
        assert f"multi={1<<bit}*MULT_R*MP_RATIO" in text and f"multi={1<<bit}*MULT_R*MN_RATIO" in text
    for row in three:
        path = ROOT / f"output/cdac8_uniform_scale/decks/{row['name']}.scs"
        assert digest(path) == row["deck_sha256"]
        assert all(blocks(path.read_text(encoding="utf-8"))[n] == refs[n] for n in refs)
    files = [CFG, Path(__file__), native_path, selected, ROOT / "config/design_spec.yaml",
             ROOT / "config/sar8_simple.yaml", ROOT / "scripts/sar8_simple/circuit.py",
             ROOT / "verification/sar8_simple/cells.json", ROOT / "verification/sar8_simple/summary.json",
             ROOT / "docs/figures/cdac8_uniform_scale/metrics.json"]
    files += [ROOT / f"output/cdac8_uniform_scale/decks/{r['name']}.scs" for r in three]
    rows = [{"path": p.relative_to(ROOT).as_posix(), "sha256": digest(p)} for p in sorted(set(files))]
    record = {"baseline_id": cfg["baseline_id"], "stage": cfg["stage"], "qualified": False,
              "adapter_implemented": False, "joint_simulation_completed": False,
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
              "files": rows, "live_readback": live,
              "native_controller_subckt_sha256": {n: hashlib.sha256(native[n].encode()).hexdigest() for n in sorted(controller_names)},
              "comparator_subckt_sha256": hashlib.sha256(native["sar_strongarm_t28"].encode()).hexdigest(),
              "analog_subckt_sha256": {n: hashlib.sha256(v.encode()).hexdigest() for n, v in sorted(refs.items())},
              "three_x_old_scope": metrics["scope"],
              "three_x_cases": [{k: r[k] for k in ("name", "factor", "code", "expected_code", "bounded_pass", "compare_max_error_mv")} for r in three],
              "three_x_worst_model_port_v": max(r["stress"]["all"]["value_v"] for r in three),
              "three_x_max_compare_error_mv": max(r["compare_max_error_mv"] for r in three),
              "oa_mutations": [], "new_simulations": []}
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print("PREPARED", record["baseline_id"], len(live["cells"]), "unchanged OA cells; 6 existing 3x cases")


def check():
    record = read_json(LOCK)
    for row in record["files"]:
        assert digest(ROOT / row["path"]) == row["sha256"], row["path"]
    assert not record["joint_simulation_completed"] and not record["adapter_implemented"]
    assert not record["oa_mutations"] and not record["new_simulations"]
    print("LOCK_CHECK_PASS", record["baseline_id"], len(record["files"]), "pinned files")


if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("stage", choices=["capture", "prepare", "check"]);args = p.parse_args()
    if args.stage == "capture":capture()
    elif args.stage == "prepare":lock_sources(read_json(OUT / "live_readback.json"))
    else:check()
