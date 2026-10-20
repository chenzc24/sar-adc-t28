"""Native CMOS implementation of the sample-initialized asynchronous loop.

Only the old, measured primitive TOPOLOGIES are copied; no old OA cell is
modified or instantiated. There is one comparator-clock SR latch, no phase FSM.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

LIB = "SAR_ADC_T28"
TOP = "sar_logic_8b_async_simple"
PREFIX = "sar8s_"


@dataclass
class Part:
    name: str
    master: str
    terms: dict[str, str]
    lib: str = LIB
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class Cell:
    name: str
    inputs: list[str]
    outputs: list[str]
    parts: list[Part] = field(default_factory=list)

    def add(self, name, master, terms, lib=LIB, **params):
        assert name not in {p.name for p in self.parts}, (self.name, name)
        self.parts.append(Part(name, master, terms, lib, params))

    def g(self, kind, y, *args, name=None):
        assert len(args) in (1, 2)
        self.add(name or f"X{len(self.parts):03d}", PREFIX + kind,
                 dict(zip(("A", "B"), args)) | {"Y": y, "VDD": "VDD", "VSS": "VSS"})
        return y

    def ff(self, name, d, ck, reset, q):
        self.add(name, PREFIX + "dffr", {"D": d, "CK": ck, "RST": reset,
                 "Q": q, "VDD": "VDD", "VSS": "VSS"})

    def delay(self, role, source, target):
        self.add("XD_" + target, PREFIX + "delay_" + role,
                 {"A": source, "Y": target, "VDD": "VDD", "VSS": "VSS"})


def logic_cells():
    path = Path(__file__).resolve().parents[1] / "sar8_async/circuit.py"
    spec = importlib.util.spec_from_file_location("_sar8s_primitive_reference", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    keep = {"inv", "nand2", "and2", "buf", "or2", "xor2", "mux2", "sr", "dffr"}
    cells = []
    for old in module.logic_cells():
        if old.name.removeprefix("sar8a_") not in keep:
            continue
        parts = [Part(p.name, p.master.replace("sar8a_", PREFIX),
                      copy.deepcopy(p.terms), p.lib, copy.deepcopy(p.params)) for p in old.parts]
        cells.append(Cell(old.name.replace("sar8a_", PREFIX), old.inputs[:], old.outputs[:], parts))
    c = Cell(PREFIX + "clkbuf", ["A", "VDD", "VSS"], ["Y"])
    c.g("inv", "AB", "A")
    # PDK CDF limits a single pch_mac finger to 3 um; keep the accepted
    # physical sizing explicit instead of assuming a 4-um request survived.
    for name, model, source, width in (("MN", "nch_mac", "VSS", "2u"), ("MP", "pch_mac", "VDD", "3u")):
        c.add(name, model, {"D": "Y", "G": "AB", "S": source, "B": source}, "tsmcN28",
              Wfg=width, l="30n", fingers="1", simM="1")
    cells.append(c)
    for role, cap in {"quiet": "150f", "valid": "5f", "write": "20f", "bbm": "5f"}.items():
        c = Cell(PREFIX + "delay_" + role, ["A", "VDD", "VSS"], ["Y"])
        for index, source, node, output in ((0, "A", "RC0", "B"), (1, "B", "RC1", "Y")):
            c.add(f"R{index}", "res", {"PLUS": source, "MINUS": node}, "analogLib", r="10k")
            c.add(f"C{index}", "cap", {"PLUS": node, "MINUS": "VSS"}, "analogLib", c=cap)
            c.g("inv", output, node)
        c.g("inv", "AB", "A")
        for name, master, drain, gate, source, width in (
            ("MN_CLEAR", "nch_mac", "RC0", "AB", "VSS", "2u"),
            ("MP_CLEAR", "pch_mac", "RC1", "A", "VDD", "3u")):
            c.add(name, master, {"D": drain, "G": gate, "S": source, "B": source},
                  "tsmcN28", Wfg=width, l="30n", fingers="1", simM="1")
        cells.append(c)
    return cells


def controller_cells():
    cells = []
    c = Cell(PREFIX + "timing", ["SAMPLE", "ACTIVE", "COMP_P", "COMP_N", "VDD", "VSS"],
             ["CMP_CLK", "PHI_W", "PHI_U", "DATA"])
    c.g("inv", "SN", "SAMPLE")
    c.g("and2", "LIVE", "SN", "ACTIVE")
    c.g("buf", "PR", "COMP_P"); c.g("buf", "NR", "COMP_N")
    c.g("inv", "NRB", "NR"); c.g("and2", "DATA", "PR", "NRB")
    c.g("xor2", "RAW", "PR", "NR")
    c.delay("valid", "RAW", "RAW_D")
    c.g("and2", "DEC", "RAW", "RAW_D")
    c.g("and2", "WD", "DEC", "CMP_CLK")
    # ACTIVE only controls the NEXT launch. Never feed a moving token back
    # into the ongoing write/update pulse: skewed token outputs can briefly
    # overlap or be empty, which must not split that clock pulse.
    c.g("and2", "WRITE_REQ", "WD", "SN")
    c.g("clkbuf", "PHI_W", "WRITE_REQ")
    c.delay("write", "PHI_W", "WRITE_D")
    c.g("and2", "UD", "PHI_W", "WRITE_D")
    c.g("and2", "PHI_U", "UD", "SN")
    for signal, inverse in (("CMP_CLK", "CN"), ("PHI_W", "WN"), ("PHI_U", "UN")):
        c.g("inv", inverse, signal)
    c.g("and2", "Q0", "CN", "WN"); c.g("and2", "Q1", "Q0", "UN")
    c.g("and2", "QUIET", "Q1", "LIVE")
    c.delay("quiet", "QUIET", "QUIET_D")
    c.g("and2", "CLOCK_SET", "QUIET", "QUIET_D")
    c.g("or2", "CLOCK_RESET", "SAMPLE", "PHI_U")
    c.add("XCLOCK", PREFIX + "sr", {"S": "CLOCK_SET", "R": "CLOCK_RESET",
          "Q": "CLOCK_Q", "VDD": "VDD", "VSS": "VSS"})
    c.g("buf", "CMP_CLK", "CLOCK_Q")
    cells.append(c)

    c = Cell(PREFIX + "bitseq8", ["SAMPLE", "PHI_U", "VDD", "VSS"],
             [f"T{i}" for i in range(7, -1, -1)])
    # Inverted first FF provides SAMPLE-set MSB without another reset net.
    c.ff("XF7", "VDD", "PHI_U", "SAMPLE", "NT7"); c.g("inv", "T7", "NT7")
    for i in range(6, -1, -1):
        c.ff(f"XF{i}", f"T{i+1}", "PHI_U", "SAMPLE", f"T{i}")
    cells.append(c)

    c = Cell(PREFIX + "bit", ["SAMPLE", "TOKEN", "DATA", "PHI_W", "VDD", "VSS"], ["D", "CODE"])
    c.add("XMUX", PREFIX + "mux2", {"D0": "D", "D1": "DATA", "SEL": "TOKEN",
          "Y": "NEXT_D", "VDD": "VDD", "VSS": "VSS"})
    c.ff("XSTORE", "NEXT_D", "PHI_W", "SAMPLE", "D")
    c.g("or2", "CODE", "D", "TOKEN")
    cells.append(c)

    c = Cell(PREFIX + "bp_slice", ["SAMPLE", "CODE", "VDD", "VSS"], ["HIGH", "LOW"])
    c.g("inv", "SN", "SAMPLE"); c.g("inv", "CB", "CODE")
    for bit, code, output in ((0, "CB", "LOW"), (1, "CODE", "HIGH")):
        c.g("and2", f"REQ{bit}", code, "SN")
        c.delay("bbm", f"REQ{bit}", f"ON{bit}")
        c.g("and2", output, f"REQ{bit}", f"ON{bit}")
    cells.append(c)
    for bank in ("p", "n"):
        c = Cell(PREFIX + f"bp_{bank}8", ["SAMPLE"] + [f"C{i}" for i in range(7, -1, -1)] + ["VDD", "VSS"],
                 [f"H{i}" for i in range(7, -1, -1)] + [f"L{i}" for i in range(7, -1, -1)])
        for i in range(8):
            # Mirror the reference CHOICE, not the final gate signal. Both
            # banks retain their own turn-off-immediate/turn-on-delayed BBM.
            c.add(f"XB{i}", PREFIX + "bp_slice", {"SAMPLE": "SAMPLE", "CODE": f"C{i}",
                  "HIGH": f"H{i}" if bank == "p" else f"L{i}",
                  "LOW": f"L{i}" if bank == "p" else f"H{i}", "VDD": "VDD", "VSS": "VSS"})
        cells.append(c)

    outputs = [f"D{i}" for i in range(7, -1, -1)] + ["CMP_CLK"]
    outputs += [f"B{bank}_{rail}{i}" for bank in ("P", "N") for rail in ("H", "L") for i in range(7, -1, -1)]
    c = Cell(TOP, ["SAMPLE", "COMP_P", "COMP_N", "VDD", "VSS"], outputs)
    def child(name, master, mapping=None):
        obj = next(item for item in cells if item.name == master)
        mapping = mapping or {}
        c.add(name, master, {p: mapping.get(p, p) for p in obj.inputs + obj.outputs})
    child("XTIM", PREFIX + "timing")
    child("XSEQ", PREFIX + "bitseq8")
    for i in range(8):
        child(f"XBIT{i}", PREFIX + "bit", {"TOKEN": f"T{i}", "D": f"D{i}", "CODE": f"CODE{i}"})
    for bank in ("P", "N"):
        mapping = {f"C{i}": f"CODE{i}" for i in range(8)}
        mapping.update({f"{rail}{i}": f"B{bank}_{rail}{i}" for rail in ("H", "L") for i in range(8)})
        child("XBP" + bank, PREFIX + f"bp_{bank.lower()}8", mapping)
    for j in range(4):
        c.g("or2", f"A{j}", f"T{2*j}", f"T{2*j+1}")
    c.g("or2", "A01", "A0", "A1"); c.g("or2", "A23", "A2", "A3")
    c.g("or2", "ACTIVE", "A01", "A23")
    cells.append(c)
    return cells


def hierarchy():
    return logic_cells() + controller_cells()
