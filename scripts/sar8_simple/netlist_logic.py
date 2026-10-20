"""Functional abstraction of the actual exported CMOS hierarchy, NOT SPICE.

INV/NAND/SR/DFF and explicit R/C delays are abstracted. This exercises wiring
and event sequencing, not analog setup/hold, transistor stress or PVT margins.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import heapq
import itertools
import json
import re

from circuit import TOP, hierarchy
from oa import OUT, dump


def blocks(text):
    joined = re.sub(r"\\\n\s*", " ", text)
    result = {}
    for m in re.finditer(r"(?ms)^subckt (\w+) ([^\n]+)\n(.*?)^ends \1", joined):
        parts = [(ref, pins.split(), master) for ref, pins, master in
                 re.findall(r"(?m)^\s*(\w+) \(([^)]+)\)\s+(\w+)", m[3])]
        result[m[1]] = (m[2].split(), parts)
    return result


def normalized(text):
    joined = re.sub(r"\\\n\s*", " ", text)
    return {m[1]: re.sub(r"\s+", " ", m[2]).strip() for m in
            re.finditer(r"(?ms)^subckt (\w+) (.*?)^ends \1", joined)}


@dataclass
class Primitive:
    kind: str
    nets: dict
    version: int = 0
    clock: int = 0


class Engine:
    def __init__(self, text):
        self.blocks = blocks(text)
        self.parts = []; self.listeners = {}; self.v = {"VDD": 1, "VSS": 0}
        self.queue = []; self.serial = 0; self.time = 0.; self.trace = []; self.epoch = 0
        self.word = 0; self.index = 0; self.stuck = -1; self.cmp_delay = .2
        self.expand(TOP, {p: p for p in self.blocks[TOP][0]}, "XCTRL")
        self.v.update({net: 0 for part in self.parts for net in part.nets.values() if net not in self.v})
        for index, part in enumerate(self.parts):
            for net in set(part.nets.values()):
                self.listeners.setdefault(net, []).append(index)
        for index in range(len(self.parts)):
            self.evaluate(index)

    def expand(self, name, mapping, path):
        ports, parts = self.blocks[name]
        if name in ("sar8s_inv", "sar8s_nand2", "sar8s_clkbuf", "sar8s_sr", "sar8s_dffr") or name.startswith("sar8s_delay_"):
            self.parts.append(Primitive(name, mapping)); return
        for reference, pins, master in parts:
            if master in ("resistor", "capacitor"):
                continue
            assert master in self.blocks, (name, reference, master)
            child_ports = self.blocks[master][0]; assert len(child_ports) == len(pins)
            nets = {cp: mapping.get(net, path + "." + net) for cp, net in zip(child_ports, pins)}
            self.expand(master, nets, path + "." + reference)

    def later(self, when, call):
        self.serial += 1; heapq.heappush(self.queue, (when, self.serial, call))

    def drive(self, net, value):
        value = int(bool(value))
        if self.v.get(net, 0) == value:
            return
        self.v[net] = value
        if net in ("CMP_CLK", "XCTRL.PHI_W", "XCTRL.PHI_U"):
            self.trace.append((self.time, net, value))
        if net == "SAMPLE" and value:
            self.epoch += 1; self.index = 0
        if net == "CMP_CLK":
            self.epoch += 1; epoch = self.epoch
            if value:
                bit = 7 - self.index; self.index += 1
                assert bit >= 0, "Ninth comparison"
                if bit != self.stuck:
                    decision = bool(self.word & (1 << bit))
                    def ready():
                        if epoch == self.epoch:
                            self.drive("COMP_P", decision); self.drive("COMP_N", not decision)
                    self.later(self.time + self.cmp_delay + .02 * (bit % 3), ready)
            else:
                def reset():
                    if epoch == self.epoch:
                        self.drive("COMP_P", 1); self.drive("COMP_N", 1)
                self.later(self.time + .05, reset)
        for index in self.listeners.get(net, ()):
            self.evaluate(index)

    def evaluate(self, index):
        part = self.parts[index]; value = lambda pin: self.v.get(part.nets[pin], 0)
        if part.kind == "sar8s_dffr":
            ck = value("CK"); rising = ck and not part.clock; part.clock = ck
            if value("RST"):
                new = 0
            elif rising:
                new = value("D")
            else:
                return
            output, delay = "Q", .07
        elif part.kind == "sar8s_sr":
            if value("R"):
                new = 0
            elif value("S"):
                new = 1
            else:
                return
            output, delay = "Q", .025
        elif part.kind.startswith("sar8s_delay_"):
            new = value("A"); output = "Y"
            delay = {"quiet": 2.6, "write": .4, "valid": .12, "bbm": .12}[part.kind.split("_")[-1]] if new else .035
        elif part.kind == "sar8s_clkbuf":
            new, output, delay = value("A"), "Y", .035
        else:
            new = 1 - value("A") if part.kind == "sar8s_inv" else 1 - (value("A") & value("B"))
            output, delay = "Y", .015
        part.version += 1; version = part.version
        def update():
            if part.version == version:
                self.drive(part.nets[output], new)
        self.later(self.time + delay, update)

    def frame(self, word, offset=0, stuck=-1, cmp_delay=.2):
        self.word = word; self.stuck = stuck; self.cmp_delay = cmp_delay
        first = len(self.trace)
        self.later(offset, lambda: (self.drive("COMP_P", 1), self.drive("COMP_N", 1)))
        for when, value in ((offset + 1, 1), (offset + 41, 0)):
            self.later(when, lambda v=value: self.drive("SAMPLE", v))
        while self.queue and self.queue[0][0] < offset + 100:
            self.time, _, call = heapq.heappop(self.queue); call()
        trace = [row for row in self.trace[first:] if row[0] > offset + 41]
        return dict(output=sum((1 << bit) * self.v[f"D{bit}"] for bit in range(8)),
                    token=sum((1 << bit) * self.v[f"XCTRL.T{bit}"] for bit in range(8)),
                    counts={net: sum(row[1] == net and row[2] for row in trace)
                            for net in ("CMP_CLK", "XCTRL.PHI_W", "XCTRL.PHI_U")})


def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="simple_v1"); args = ap.parse_args()
    paths = {cell: OUT / "exports" / cell / args.tag / "input.scs" for cell in ("tb_sar8s_logic", "tb_sar8s_strongarm")}
    text = paths["tb_sar8s_logic"].read_text(encoding="utf-8")
    norm = normalized(text); other = normalized(paths["tb_sar8s_strongarm"].read_text(encoding="utf-8"))
    legacy = normalized((OUT.parent / "sar8_async_impl/exports/tb_sar8a_strongarm/recovery/input.scs").read_text(encoding="utf-8"))
    assert other["sar_strongarm_t28"] == legacy["sar_strongarm_t28"], "StrongARM differs from earlier baseline"
    objects = {obj.name: obj for obj in hierarchy()}
    assert set(objects) <= set(norm)
    assert all(norm[name] == other[name] for name in objects)
    parsed = blocks(text)
    for name, obj in objects.items():
        assert {p[0] for p in parsed[name][1]} == {p.name for p in obj.parts}, (name, "parser omitted instance")
    for name in objects:
        assert not re.search(r"\b(?:bsource|vsource|sar8a_plant|veriloga)\b", norm[name]), name
    def count(name):
        result = Counter()
        for p in objects[name].parts:
            if p.master in objects:
                result.update(count(p.master))
            else:
                result[p.lib + "/" + p.master] += 1
        return result
    rows = []
    for word in range(256):
        engine = Engine(text)
        result = engine.frame(word)
        if result["token"] != 0:
            dump("audit/functional_debug.json", dict(word=word, result=result, values=engine.v, trace=engine.trace))
        assert result["output"] == word and result["token"] == 0 and set(result["counts"].values()) == {8}, (word, result)
        rows.append(result)
    for bit in range(8):
        e = Engine(text); fault = e.frame(165, stuck=bit)
        assert fault["counts"]["CMP_CLK"] == 8 - bit and fault["counts"]["XCTRL.PHI_W"] == 7 - bit
        recovery = e.frame(90, offset=100)
        assert recovery["output"] == 90 and set(recovery["counts"].values()) == {8}, (bit, recovery)
    for latency in (.02, 1.2):
        result = Engine(text).frame(165, cmp_delay=latency)
        assert result["output"] == 165 and set(result["counts"].values()) == {8}
    primitive_counts = Counter(part.kind for part in Engine(text).parts)
    assert primitive_counts["sar8s_sr"] == 1 and primitive_counts["sar8s_dffr"] == 16
    summary = dict(scope="actual_OA_export_functional_abstraction_NOT_Spectre", export_tag=args.tag,
                   netlist_sha256=hashlib.sha256(text.encode()).hexdigest(), all_256_words_pass=True,
                   stuck_recovery_positions=8, variable_delay_cases=2, native_cells=len(objects),
                   hierarchy_counts=dict(count(TOP)), comparator_clock_SR_latches=primitive_counts["sar8s_sr"],
                   SAR_and_pointer_DFFs=primitive_counts["sar8s_dffr"],
                   identical_controller_in_both_benches=True, behavioral_elements_in_controller=0,
                   unchanged_StrongARM_from_legacy_export=True,
                   StrongARM_body_sha256=hashlib.sha256(other["sar_strongarm_t28"].encode()).hexdigest(),
                   hierarchy_sha256=hashlib.sha256(json.dumps({k: norm[k] for k in sorted(objects)}, sort_keys=True).encode()).hexdigest(),
                   limitations="state/delay abstractions; no analog setup/hold/PVT/SOA proof")
    dump("audit/hierarchy.json", summary); dump("audit/functional_patterns.json", rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
