"""Boolean verification of the actual exported Canvas gate hierarchy.

Ideal edge-triggered registers, settled Boolean gates and NAND-latch memory.
This checks connectivity/algorithm; ignores analog gate td, slew, metastability,
setup/hold and the BBM time interval. It is not a SPICE transient simulation.
"""
from __future__ import annotations

import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "netlist/dut/sar_logic_8b_canvas.cir"
OUT = ROOT / "output/sar8_logic"
LEAF = {"inverter", "buffer", "nand_gate", "and_gate", "and_gate_3",
        "or_gate", "xor_gate", "d_flip_flop_reset"}


def read_subcircuits():
    logical = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw.startswith("+"):
            logical[-1] += " " + raw[1:]
        elif raw and not raw.startswith("*"):
            logical.append(raw)
    subs, current = {}, None
    for line in logical:
        tok = line.split()
        if tok[0].lower() == ".subckt":
            current = tok[1]
            ports = tok[2:tok.index("params:")] if "params:" in tok else tok[2:]
            subs[current] = {"ports": ports, "instances": []}
        elif tok[0].lower() == ".ends":
            current = None
        elif current and tok[0].startswith("X"):
            core = tok[:next((i for i, t in enumerate(tok) if "=" in t), len(tok))]
            subs[current]["instances"].append((core[0], core[-1], core[1:-1]))
    return subs


class Circuit:
    def __init__(self):
        self.subs = read_subcircuits()
        self.gates, self.regs = [], []
        self.values = {}
        top = self.subs["SAR8_TOP"]
        self.expand("SAR8_TOP", dict(zip(top["ports"], top["ports"])), "")
        self.clocks = {name: 0 for name, _ in self.regs}

    def expand(self, cell, ports, prefix):
        def node(n):
            return ports.get(n, prefix + n)
        for name, master, nodes in self.subs[cell]["instances"]:
            formal = self.subs[master]["ports"]
            assert len(formal) == len(nodes), (name, formal, nodes)
            mapped = dict(zip(formal, map(node, nodes)))
            path = prefix + name
            if master == "d_flip_flop_reset":
                self.regs.append((path, mapped))
                self.values[mapped["Q"]] = 0
                self.values[mapped["QBAR"]] = 1
            elif master in LEAF:
                self.gates.append((master, mapped))
            else:
                self.expand(master, mapped, path + "/")

    def get(self, name):
        return self.values.get(name, 0)

    def settle(self):
        for _ in range(100):
            changed = False
            for _, p in self.regs:
                if self.get(p["RST"]):
                    for key, value in (("Q", 0), ("QBAR", 1)):
                        changed |= self.get(p[key]) != value
                        self.values[p[key]] = value
            for master, p in self.gates:
                bits = [self.get(p[k]) for k in ("A", "B", "C") if k in p]
                if master == "inverter": value = 1 - bits[0]
                elif master == "buffer": value = bits[0]
                elif master == "nand_gate": value = int(not all(bits))
                elif master.startswith("and_gate"): value = int(all(bits))
                elif master == "or_gate": value = int(any(bits))
                elif master == "xor_gate": value = bits[0] ^ bits[1]
                else: raise AssertionError(master)
                changed |= self.get(p["Y"]) != value
                self.values[p["Y"]] = value
            if not changed:
                return
        raise AssertionError("Boolean network did not settle")

    def step(self, **inputs):
        self.values.update(inputs)
        self.settle()
        captures = []
        for name, p in self.regs:
            ck = self.get(p["CK"])
            if ck and not self.clocks[name] and not self.get(p["RST"]):
                captures.append((p, self.get(p["D"])))
        for p, value in captures:
            self.values[p["Q"]] = value
            self.values[p["QBAR"]] = 1 - value
        self.settle()
        self.clocks = {name: self.get(p["CK"]) for name, p in self.regs}

    def output(self):
        return sum(self.get("D" + str(b)) << b for b in range(8))

    def pulse(self, name):
        self.step(**{name: 1})
        self.step(**{name: 0})

    def acquire(self):
        self.step(CLK_SAMPLE=1)
        assert not self.get("BUSY") and not self.get("VALID")
        # A raw latch pulse while not converting must not shift the token.
        self.pulse("CLK_LATCH")
        self.step(CLK_SAMPLE=0)
        self.pulse("CLK_LATCH")
        assert self.get("T7")

    def convert(self, code, fault_bit=None):
        previous = self.output()
        self.acquire()
        assert self.output() == previous
        self.pulse("HOLD_START")
        assert self.get("BUSY")
        for b in range(7, -1, -1):
            assert self.get("T" + str(b)), b
            bit = (code >> b) & 1
            self.step(COMP_P=bit, COMP_N=(bit if b == fault_bit else 1 - bit))
            self.step(CLK_COMPARE=1)
            assert self.get("CMP_CLK")
            self.step(CLK_LATCH=1)
            assert self.get("CMP_CLK"), "Final comparison clock was truncated"
            if b:
                assert self.output() == previous and not self.get("VALID")
            self.step(CLK_LATCH=0)
            self.step(CLK_COMPARE=0)
            if b:
                self.pulse("CLK_TRIAL")
        assert not self.get("BUSY")
        assert self.get("FAULT") == (fault_bit is not None)
        assert self.get("VALID") == (fault_bit is None)
        assert self.output() == (code if fault_bit is None else previous)
        self.pulse("PREPARE")
        assert not self.get("HOLD")
        assert self.get("VALID") == (fault_bit is None)


def main():
    timing = yaml.safe_load((ROOT / "config/sar8_logic_timing.yaml").read_text(encoding="utf-8"))
    phase = timing["phase_commands_ns"]
    assert timing["resolution_bits"] == 8
    assert phase["sample_fall"] < phase["cdac_vcm_release"] < phase["hold_start"]
    assert phase["hold_start"] < phase["first_compare_rise"] < phase["first_latch_rise"]
    assert phase["first_latch_rise"] < phase["first_compare_rise"] + phase["compare_high_width"] < phase["first_next_trial_rise"]
    assert phase["first_latch_rise"] + 7 * timing["bit_period_ns"] < phase["prepare_rise"]
    assert phase["prepare_rise"] < phase["cdac_vcm_reconnect"] < phase["next_sample_rise"]
    c = Circuit()
    c.step(VDD=1, VSS=0, RST_N=0, CLK_SAMPLE=0, PREPARE=0,
           HOLD_START=0, CLK_TRIAL=0, CLK_LATCH=0, CLK_COMPARE=0,
           COMP_P=0, COMP_N=1)
    c.step(RST_N=1)
    for code in range(256):
        c.convert(code)
    for bit in range(8):
        c.convert(0xA5, fault_bit=bit)
    c.convert(0x3C)
    c.acquire()
    c.pulse("HOLD_START")
    c.step(RST_N=0, HOLD_START=1, CLK_TRIAL=1)
    assert c.output() == 0 and not c.get("BUSY") and not c.get("VALID")
    assert not c.get("HOLD") and not c.get("TRIAL_EN")
    summary = {"status": "pass", "all_codes": 256, "fault_positions": 8,
               "reset_dominance": True, "output_retention": True,
               "full_final_compare_pulse_boolean": True,
               "registers": len(c.regs), "combinational_gates": len(c.gates),
               "scope": "Boolean topology; no analog delay/setup/hold/PVT or BBM interval proof"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "boolean_check.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
