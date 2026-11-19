import re
from collections import Counter
from pathlib import Path

from tools.saradc.candidates import definitions

ROOT = Path(__file__).resolve().parents[1]


def test_physical_bottom_bound_counts_each_unit_once(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools/saradc/measure"))
    from tools.saradc.measure.single_edge_lpe import bottom_state

    lsb = 1.8 / 256
    v = {"vdd!": .99, "vrefp": .9, "vrefn": 0.}
    groups = {}
    for side, word in (("n", 127), ("p", 128)):
        groups[side] = []
        for bit in range(8):
            selected = bool(word & (1 << bit))
            for switch in "np":
                v[f"xdut.g{side}{switch}{bit}"] = v["vdd!"] * selected
            group = [f"{side}.{bit}.{i}" for i in range(1 << bit)]
            groups[side].append(group)
            v.update(dict.fromkeys(group, v["vrefn" if selected else "vrefp"]))
    assert bottom_state(v, groups, lsb)["weighted_bound_lsb"] == 0
    for node in groups["n"][7]:
        v[node] -= lsb / 2
    result = bottom_state(v, groups, lsb)
    assert result["gate_words"] == [127, 128]
    assert abs(result["weighted_bound_lsb"] - .25) < 1e-12
    v[groups["p"][0][0]] -= lsb
    assert bottom_state(v, groups, lsb)["weighted_bound_lsb"] > .25
    v["xdut.gnp7"] = v["vdd!"]
    assert bottom_state(v, groups, lsb) is None


def test_frontend_uses_the_measured_native_cells():
    design = ROOT / "design"
    entry = (design / "dut_single_edge.scs").read_text()
    blocks = {}
    for name in re.findall(r'^include "([^"]+)"', entry, re.M):
        blocks.update(definitions((design / name).read_text()))
    analog = {"sar8j_r1_cdac", "sar_strongarm_t28", "sar_bootstrap_flat_8b_p"}
    top = "sar_adc8_join_r4"
    cells = Counter()

    def walk(block):
        for line in blocks[block].splitlines()[1:]:
            device = re.match(r"\s*(\w+)\s+\([^)]+\)\s+(\w+)", line)
            if not device:
                continue
            instance, master = device.groups()
            if master == "iprobe" or (block == top and
                    (master in analog or (instance.startswith("CL_") and master == "cfmom_2t"))):
                continue
            if master in blocks:
                walk(master)
            else:
                assert master.endswith("BWP12T30P140"), (block, instance, master)
                cells[master] += 1

    walk(top)
    assert sum(cells.values()) == 156
    assert sum(n for name, n in cells.items() if name.startswith("DEL")) == 10
    assert cells["XOR2D1BWP12T30P140"] == 2
    assert cells["DFCNQD1BWP12T30P140"] == 10
    assert cells["LHCNDQD1BWP12T30P140"] == 1


def test_trial_word_network_on_every_decision_history():
    source = (ROOT / "design/xtor/sar/single_edge.scs").read_text()
    body = definitions(source)["sar8_next_word"]
    gates = re.findall(r"^\s*X\w+ \(([^)]+)\) (\w+)D1BWP12T30P140", body, re.M)
    ops = {"AN2": lambda a, b: a and b, "OR2": lambda a, b: a or b,
           "INV": lambda a: not a}
    for expected in range(256):
        word = 128
        for bit in reversed(range(8)):
            nodes = {"DATA": bool(expected & (1 << bit)), "DONE": False, "VSS": False}
            nodes.update({"CODE%d" % k: bool(word & (1 << k)) for k in range(8)})
            for pins, kind in gates:
                *inputs, out, _, _ = pins.split()
                nodes[out] = ops[kind](*(nodes[i] for i in inputs))
            decided = sum(1 << k for k in range(8) if nodes["D%d" % k])
            assert decided == expected & ~((2 << bit) - 1)
            assert bool(word & 1) == (bit == 0)
            word = sum(1 << k for k in range(8) if nodes["NEXT%d" % k])
            assert word == ((expected & ~((1 << bit) - 1)) | ((1 << bit) >> 1))
        assert word == expected
        nodes.update({"DONE": True})
        nodes.update({"CODE%d" % k: bool(word & (1 << k)) for k in range(8)})
        for pins, kind in gates:
            *inputs, out, _, _ = pins.split()
            nodes[out] = ops[kind](*(nodes[i] for i in inputs))
        assert sum(1 << k for k in range(8) if nodes["D%d" % k]) == expected
