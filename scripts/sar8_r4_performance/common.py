"""Immutable R4 source and characterization paths."""
from pathlib import Path
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/sar8_r4_performance"
SOURCE = ROOT / "netlist/sar8_physical"
MODELS = ROOT / "models/veriloga/sar8_r4_performance"
LSB = 1.8 / 256
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def blocks(text):
    text = re.sub(r"\\\r?\n\s*", " ", text)
    return {m[1]: " ".join(m[0].split()) for m in re.finditer(r"(?ms)^subckt (\w+) .*?^ends \1\s*$", text)}


def verify_source():
    provenance = read(SOURCE / "provenance.json")
    for name, expected in provenance["files"].items():
        assert sha(SOURCE / name) == expected, name
    dut = (SOURCE / "dut.scs").read_text()
    assert "ahdl_include" not in dut
    assert "sar_adc8_join_r4" in blocks(dut)
    return provenance


def base_deck():
    verify_source()
    run = (SOURCE / "tt_nominal.scs").read_text()
    run = run[:run.index("\ntran_physical")]
    run = run.replace('include "dut.scs"', (SOURCE / "dut.scs").read_text())
    run = run.replace('include "tb.scs"', (SOURCE / "tb.scs").read_text())
    return run
