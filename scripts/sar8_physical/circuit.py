"""PDK-passive CMOS candidate; no internal behavioral event sources."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = "SAR_ADC_T28"
PREFIX = "sar8p_"
CTRL = "sar_logic_8b_physical"
TOP = "sar_adc8_join_r4"
BOOT = "sar_bootstrap_flat_8b_p"

spec = importlib.util.spec_from_file_location("_physical_reference", ROOT / "scripts/sar8_simple/circuit.py")
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
Part = old.Part


class Cell(old.Cell):
    def g(self, kind, y, *args, name=None):
        self.add(name or f"X{len(self.parts):03d}", PREFIX + kind,
                 dict(zip(("A", "B"), args)) | {"Y": y, "VDD": "VDD", "VSS": "VSS"})
        return y

    def delay(self, role, source, target):
        self.add("XD_" + target, PREFIX + "delay_" + role,
                 {"A": source, "Y": target, "VDD": "VDD", "VSS": "VSS"})


def mom(c, name, a, b, nominal_ff):
    # Integer unit count. Geometry is deliberately explicit and checked in OA;
    # actual capacitance is measured, not forced to the nominal name.
    count = max(1, round(nominal_ff / 5))
    c.add(name, "cfmom_2t", {"PLUS": a, "MINUS": b}, "tsmcN28",
          Wfinger="50n", Sfinger="50n", Lfinger="2.5u", Nfinger="8",
          StartMn="1", StopMn="3", mismatch="1", m=str(count))


def map_passives(cell):
    output = []
    for p in cell.parts:
        if p.lib == "analogLib" and p.master == "cap":
            text = p.params["c"]
            value = float(text[:-1]) * {"f": 1, "p": 1000}[text[-1]]
            temp = Cell("tmp", [], [])
            mom(temp, p.name, p.terms["PLUS"], p.terms["MINUS"], value)
            output.extend(temp.parts)
        elif p.lib == "analogLib" and p.master == "res":
            assert p.params["r"] == "10k"
            output.append(Part(p.name, "rupolym", p.terms.copy(), "tsmcN28",
                               dict(ResCalc="l_&_w", w="1u", l="17.13u", m="1")))
        else:
            output.append(p)
    cell.parts = output
    return cell


def primitives():
    cells = []
    for src in old.logic_cells():
        parts = [Part(p.name, p.master.replace("sar8s_", PREFIX),
                      copy.deepcopy(p.terms), p.lib, copy.deepcopy(p.params)) for p in src.parts]
        cells.append(map_passives(Cell(src.name.replace("sar8s_", PREFIX), src.inputs[:], src.outputs[:], parts)))
    template = next(c for c in cells if c.name == PREFIX + "delay_valid")
    for role, count in (("restore", 1), ("capture", 10)):
        obj = copy.deepcopy(template)
        obj.name = PREFIX + "delay_" + role
        for part in obj.parts:
            if part.master == "cfmom_2t":
                part.params["m"] = str(count)
        cells.append(obj)
    return cells


def controller():
    cells = []
    for src in old.controller_cells():
        if src.name in ("sar8s_bp_slice", "sar8s_bp_p8", "sar8s_bp_n8"):
            continue
        name = CTRL if src.name == old.TOP else src.name.replace("sar8s_", PREFIX)
        parts = [Part(p.name, p.master.replace("sar8s_", PREFIX),
                      copy.deepcopy(p.terms), p.lib, copy.deepcopy(p.params)) for p in src.parts]
        obj = Cell(name, src.inputs[:], src.outputs[:], parts)
        if name == CTRL:
            obj.parts = [p for p in obj.parts if p.name not in ("XBPP", "XBPN")]
            obj.outputs = [f"D{i}" for i in range(7, -1, -1)] + ["CMP_CLK", "PHI_U"]
            obj.outputs += [f"CODE{i}" for i in range(7, -1, -1)]
        cells.append(map_passives(obj))
    return cells


def inv_stage(c, name, a, y, mult):
    for suffix, master, source, width in (("N", "nch_mac", "VSS", "500n"),
                                          ("P", "pch_mac", "VDD", "1u")):
        c.add(name + suffix, master, {"D": y, "G": a, "S": source, "B": source},
              "tsmcN28", Wfg=width, l="30n", fingers="1", simM=str(mult))


def reference():
    cells = []
    c = Cell(PREFIX + "nonoverlap", ["CODE", "VDD", "VSS"], ["H", "L"])
    c.g("inv", "CB", "CODE")
    for request, output in (("CODE", "H"), ("CB", "L")):
        c.delay("bbm", request, output + "D")
        c.g("and2", output, request, output + "D")
    cells.append(c)
    for bit in range(8):
        c = Cell(PREFIX + f"refdrv_b{bit}", ["H", "L", "VDD", "VSS"],
                 ["GPP", "GPN", "GNP", "GNN"])
        strength = max(1, (2**bit + 7) // 8)
        # Identical number of stages for all four gates; complementary
        # controls are resolved upstream, then independently buffered.
        for gate, command, inverted in (("GPP", "L", True), ("GPN", "H", False),
                                         ("GNP", "H", True), ("GNN", "L", False)):
            start = command
            if not inverted:
                c.g("inv", gate + "PRE", command)
                start = gate + "PRE"
            inv_stage(c, gate + "A", start, gate + "A", 1)
            inv_stage(c, gate + "B", gate + "A", gate + "B", max(1, strength // 4))
            inv_stage(c, gate + "C", gate + "B", gate + "DRV", strength)
            for index, first, last in ((0, gate+"DRV", gate+"RG"), (1, gate+"RG", gate)):
                c.add(f"R{gate}{index}", "rupolym", {"PLUS": first, "MINUS": last}, "tsmcN28",
                      ResCalc="l_&_w", w="1u", l="17.13u", segments="5", connection="Series", m=str(2**bit))
        cells.append(c)
    c = Cell(PREFIX + "refword", ["SAMPLE", "PHI_U"] + [f"CODE{i}" for i in range(8)] + [f"D{i}" for i in range(8)]
             + ["VDD", "VSS"], [f"G{s}{rail}{i}" for s in "PN" for rail in "PN" for i in range(8)])
    # Clear only the decided bit first; add only the next trial after that
    # rail settles. Other banks remain clamped to their previous rails.
    first="PHI_U"
    for i in range(3):
        c.g("buf",f"FIRST{i}",first);first=f"FIRST{i}"
    c.g("or2","REQ_RESET","SAMPLE","ACK")
    c.add("XREQUEST",PREFIX+"sr",{"S":"PHI_U","R":"REQ_RESET","Q":"REQ_Q","VDD":"VDD","VSS":"VSS"})
    c.delay("capture","REQ_Q","LATE_CLK")
    c.delay("valid","LATE_CLK","ACK")
    c.g("or2","CAP_REQ",first,"LATE_CLK")
    c.g("clkbuf","CAP_CLK","CAP_REQ")
    for bit in range(8):
        c.add(f"XMUX{bit}",PREFIX+"mux2",{"D0":f"CODE{bit}","D1":f"D{bit}","SEL":"PHI_U",
              "Y":f"TARGET{bit}","VDD":"VDD","VSS":"VSS"})
    c.g("inv","MSB_DN","TARGET7")
    c.g("inv","Q7","MSB_QN")
    for bit in range(8):
        c.add(f"XSTORE{bit}", PREFIX + "dffr", {"D": "MSB_DN" if bit==7 else f"TARGET{bit}", "CK": "CAP_CLK",
              "RST": "SAMPLE", "Q": "MSB_QN" if bit==7 else f"Q{bit}", "VDD": "VDD", "VSS": "VSS"})
        c.add(f"XBBM{bit}", PREFIX + "nonoverlap", {"CODE": f"Q{bit}", "H": f"H{bit}",
              "L": f"L{bit}", "VDD": "VDD", "VSS": "VSS"})
        c.add(f"XDRV{bit}", PREFIX + f"refdrv_b{bit}", {"H": f"H{bit}", "L": f"L{bit}",
              "VDD": "VDD", "VSS": "VSS", **{p: f"{p}{bit}" for p in ("GPP", "GPN", "GNP", "GNN")}})
    cells.append(c)
    return cells


def bootstrap():
    c = Cell(BOOT, ["CLKS", "Vin"], ["VOUT"])
    # Captured user-selected twelve-MOS topology, not a new Bootstrap.
    # Keep this declarative source usable without an ignored OA snapshot.
    rows=[("MNCLK","nch_18_mac","CLKSB","CLKS","gnd!","gnd!"),
          ("M8","nch_18_mac","BBOT","CLKSB","gnd!","gnd!"),
          ("M4A","nch_18_mac","CTRL","G","BBOT","gnd!"),
          ("MRSTG","nch_18_mac","GRESET","CLKSB","gnd!","gnd!"),
          ("Maux","nch_18_mac","G","VDD!","GRESET","gnd!"),
          ("Msin","nch_18_mac","BBOT","G","Vin","gnd!"),
          ("M4C","nch_18_mac","CTRL","CLKS","BBOT","gnd!"),
          ("Mmain","nch_18_mac","VOUT","G","Vin","gnd!"),
          ("MPCLK","pch_18_mac","CLKSB","CLKS","VDD!","VDD!"),
          ("M4B","pch_18_mac","CTRL","CLKS","VDD!","VDD!"),
          ("M4","pch_18_mac","G","CTRL","BTOP","BTOP"),
          ("M2","pch_18_mac","BTOP","G","VDD!","BTOP")]
    for name,master,d,g,s,b in rows:
        c.add(name,master,dict(D=d,G=g,S=s,B=b),"tsmcN28",
              Wfg="1u",l="150.0n",fingers="1",simM="1")
    mom(c,"Cboot","BTOP","BBOT",1000)
    return c


def top():
    c = Cell(TOP, ["SAMPLE", "VINP", "VINN", "VREFP", "VREFN", "VDD!", "gnd!"],
             [f"D{i}" for i in range(7, -1, -1)])
    power = {"VDD": "VDD!", "VSS": "gnd!"}
    c.add("XSAMPLE", PREFIX + "clkbuf", {"A": "SAMPLE", "Y": "SAMPLE_INT", **power})
    for s in "PN":
        c.add("XBOOT" + s, BOOT, {"CLKS": "SAMPLE_INT", "Vin": "VIN" + s, "VOUT": "TOP" + s})
    c.add("XCDAC", "sar8j_r1_cdac", {**{f"G{s}{q}{b}": f"G{s}{q}{b}" for s in "PN" for q in "PN" for b in range(8)},
          "VREFP": "VREFP", "VREFN": "VREFN", "TOPP": "TOPP", "TOPN": "TOPN", **power})
    ctrl = controller()[-1]
    c.add("XCTRL", CTRL, {p: power.get(p, "SAMPLE_INT" if p == "SAMPLE" else p) for p in ctrl.inputs + ctrl.outputs})
    ref = reference()[-1]
    c.add("XREF", ref.name, {p: power.get(p, "SAMPLE_INT" if p == "SAMPLE" else p) for p in ref.inputs + ref.outputs})
    c.add("XCOMP", "sar_strongarm_t28", {"CLK": "CMP_CLK", "VINP": "TOPP", "VINN": "TOPN",
          "OUTP": "COMP_P", "OUTN": "COMP_N", **power})
    for signal in ("CMP_CLK", "COMP_P", "COMP_N"):
        mom(c, "CL_" + signal, signal, "gnd!", 10)
    return c


def passive_bench():
    c = Cell("tb_sar8p_passives", [], [])
    c.add("VDC", "vdc", {"PLUS": "IN", "MINUS": "gnd!"}, "analogLib", vdc="0.9", acm="1")
    c.add("RPDK", "rupolym", {"PLUS": "IN", "MINUS": "gnd!"}, "tsmcN28",
          ResCalc="l_&_w", w="1u", l="17.13u", m="1")
    mom(c, "CUNIT", "IN", "gnd!", 5)
    return c


def unit_bench():
    c = Cell("tb_sar8p_unit", [], [])
    c.add("VVDD", "vdc", {"PLUS": "VDD", "MINUS": "gnd!"}, "analogLib", vdc="0.9")
    c.add("VSAMPLE", "vpulse", {"PLUS": "SAMPLE", "MINUS": "gnd!"}, "analogLib",
          v1="0", v2="0.9", td="1n", pw="39.9n", per="100n", tr="100p", tf="100p")
    c.add("VUPDATE", "vdc", {"PLUS": "PHI_U", "MINUS": "gnd!"}, "analogLib", vdc="0")
    for bit in range(8):
        c.add(f"VCODE{bit}", "vdc", {"PLUS": f"CODE{bit}", "MINUS": "gnd!"},
              "analogLib", vdc="0.9" if bit == 7 else "0")
        c.add(f"VDREG{bit}","vdc",{"PLUS":f"D{bit}","MINUS":"gnd!"},"analogLib",vdc="0")
    ref = reference()[-1]
    c.add("XREF", ref.name, {p: "gnd!" if p == "VSS" else p for p in ref.inputs + ref.outputs})
    c.add("VREFHIGH", "vdc", {"PLUS": "VREFP", "MINUS": "gnd!"}, "analogLib", vdc="0.9")
    c.add("VREFLOW", "vdc", {"PLUS": "VREFN", "MINUS": "gnd!"}, "analogLib", vdc="0")
    for side in "PN":
        c.add("VTOP" + side, "vdc", {"PLUS": "TOP" + side, "MINUS": "gnd!"}, "analogLib", vdc="0.45")
    terms = {f"G{s}{rail}{bit}": f"G{s}{rail}{bit}" for s in "PN" for rail in "PN" for bit in range(8)}
    terms.update(TOPP="TOPP", TOPN="TOPN", VREFP="VREFP", VREFN="VREFN", VDD="VDD", VSS="gnd!")
    c.add("XCDAC", "sar8j_r1_cdac", terms)
    return c


def integration_bench():
    c = Cell("tb_sar_adc8_join_r4", [], [])
    dut = top()
    c.add("XDUT", TOP, {p: p for p in dut.inputs + dut.outputs})
    for name, net, value in (("VVDD", "VDD!", "SUP"), ("VREFHIGH", "VREFP_SRC", "SUP"),
                             ("VREFLOW", "VREFN_SRC", "0"), ("VVINP", "VINP_SRC", ".45+VDIFF/2"),
                             ("VVINN", "VINN_SRC", ".45-VDIFF/2")):
        c.add(name, "vdc", {"PLUS": net, "MINUS": "gnd!"}, "analogLib", vdc=value)
    c.add("VSAMPLE", "vpulse", {"PLUS": "SAMPLE", "MINUS": "gnd!"}, "analogLib",
          v1="SUP", v2="0", td="41n", pw="59.9n", per="100n", tr="100p", tf="100p")
    for side in "PN":
        c.add("RIN" + side, "res", {"PLUS": "VIN" + side + "_SRC", "MINUS": "VIN" + side}, "analogLib", r="50")
        c.add("RREF" + side, "res", {"PLUS": "VREF" + side + "_SRC", "MINUS": "VREF" + side}, "analogLib", r="50")
        c.add("CREF" + side, "cap", {"PLUS": "VREF" + side, "MINUS": "gnd!"}, "analogLib", c="4p")
    for bit in range(8):
        c.add(f"COUT{bit}", "cap", {"PLUS": f"D{bit}", "MINUS": "gnd!"}, "analogLib", c="5f")
    return c


def all_objects():
    return hierarchy() + [passive_bench(), unit_bench(), integration_bench()]


def hierarchy():
    return primitives() + controller() + reference() + [bootstrap(), top()]


if __name__ == "__main__":
    objects = all_objects()
    assert len({c.name for c in objects}) == len(objects)
    for c in objects:
        assert not any(p.lib == "analogLib" for p in c.parts) or c.name.startswith("tb_")
    print(json.dumps([asdict(c) for c in objects], indent=2))
