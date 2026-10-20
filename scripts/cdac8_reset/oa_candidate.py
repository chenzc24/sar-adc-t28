"""Independent native OA implementation; no modification of historical cells."""
from __future__ import annotations

import argparse
import sys

from support import LIB, OUT, ROOT, dump, load, selected_variant
from experiment import Variant
from virtuoso_bridge import VirtuosoClient

# Reuse pure builders / CDF callbacks, not the old target's writers or exports.
sys.path.append(str(ROOT / "scripts/cdac8_device"))
from oa import add, mos, pins, symbol, setparams, PORTS, CTRL_IN, CTRL_OUT


def require_new(c, cell):
    r = c.execute_skill(f'ddGetObj("{LIB}" "{cell}")')
    assert not r.errors and r.output.strip() == "nil", (cell, r)


def check(c, cell):
    with c.schematic.modify(LIB, cell, timeout=180):
        pass
    state = c.schematic.read(LIB, cell, param_filters=None, include_positions=True)
    marks = c.fetch(f'dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")~>markers',
                    ["objType", "severity", "bBox"])
    dump(f"oa/{cell}.json", state)
    dump(f"oa/{cell}_markers.json", marks)
    assert not marks, (cell, marks)
    print("OA_OK", cell, flush=True)
    return state


def export(c, cell, tag="primary"):
    target = OUT / "oa_netlists" / cell / tag
    assert not (target / "input.scs").exists(), "Preserve exact original export"
    check(c, cell)
    result = c.schematic.export_netlist(LIB, cell, target, simulator="spectre", timeout=240)
    dump(f"oa/{cell}_{tag}_export.json", result)
    assert (target / "input.scs").is_file()
    print("OA_EXPORTED", cell, tag, flush=True)


def switches(c, variant):
    for bit in range(8):
        cell = f"cdac8_reset_sw_b{bit}"
        require_new(c, cell)
        scale = 1 << bit
        values = {}
        rows = [
            ("MP_HIGH", "pch_mac", 8, 6, "BOT", "EH_B", "VREFP", "VDD", .175, "MULT_R", 1),
            ("MN_LOW", "nch_mac", 8, 1, "BOT", "EL_D", "VREFN", "VSS", .15, "MULT_R", 1),
            ("MN_CM", "nch_mac", 28, 1, "BOT", "ES_N" if variant.n_buffer != "none" else "ES", "VCM", "VSS", .25, "MULT_S", 1),
            ("MP_CM", "pch_mac", 28, 6, "BOT", "ES_B", "VCM", "VDD", .30, "MULT_S", 1),
        ]
        for stem, x, y, output, input_node, strength_n, strength_p in (
            ("IH", 0, 1, "EH_B", "EH", 1, 1),
            ("IS", 0, -8, "ES_B", "ES", variant.p_fast, 1),
            ("IL1", 8, -9, "EL_B", "EL", 1, 1),
            ("IL2", 18, -9, "EL_D", "EL_B", 1, 1),
        ):
            rows += [(f"MN_{stem}", "nch_mac", x, y, output, input_node, "VSS", "VSS", .25, "MULT_D", strength_n),
                     (f"MP_{stem}", "pch_mac", x, y+5, output, input_node, "VDD", "VDD", .30, "MULT_D", strength_p)]
        if variant.n_buffer != "none":
            stages = [("IN2", "ES_N", "ES_B", variant.n_strength)] if variant.n_buffer == "shared" else [
                ("IN1", "ES_NB", "ES", 1), ("IN2", "ES_N", "ES_NB", variant.n_strength)]
            for j, (stem, output, input_node, strength) in enumerate(stages):
                rows += [(f"MN_{stem}", "nch_mac", 30+j*8, -9, output, input_node, "VSS", "VSS", .25, "MULT_D", strength),
                         (f"MP_{stem}", "pch_mac", 30+j*8, -4, output, input_node, "VDD", "VDD", .30, "MULT_D", strength)]
        inputs = ["EH", "EL", "ES", "VCM", "VREFP", "VREFN", "VDD", "VSS"]
        with c.schematic.create(LIB, cell, timeout=180) as sch:
            pins(sch, inputs, ["BOT"], xout=50)
            for name, master, x, y, d, g, source, body, width, mult, strength in rows:
                mos(sch, name, master, x, y, d, g, source, body)
                values[name] = {"Wfg": f"{width}u", "w": f"{width}u", "l": "30n",
                                "fingers": "1", "simM": f"{scale*strength}*{mult}"}
        setparams(c, cell, values)
        symbol(c, cell, inputs, ["BOT"])
        check(c, cell)


def array(c, literal):
    cell = "cdac8_reset_device" if literal else "cdac8_reset_nominal"
    require_new(c, cell)
    old_state = load("preflight/cdac8_device_nominal.json")
    old_params = {i["name"]: i["params"] for i in old_state["instances"]}
    values = {}
    with c.schematic.create(LIB, cell, timeout=180) as sch:
        pins(sch, PORTS, ["TOPP", "TOPN"], xout=130)
        for side, y in (("P", 25), ("N", -20)):
            for bit in range(9):
                count = 1 << bit if bit < 8 else 1
                suffix = f"{side}{bit}"
                bottom = "B" + suffix
                x = bit*12
                if literal:
                    add(sch, "XC"+suffix, f"cdac8_bank_{count}", x, y,
                        {"TOP": "TOP"+side, "BOT": bottom}, LIB)
                else:
                    name = "CMOM"+suffix
                    add(sch, name, "cfmom_2t", x, y, {"PLUS": "TOP"+side, "MINUS": bottom}, "tsmcN28")
                    values[name] = {key: old_params[name][key] for key in
                                    ("Wfinger", "Sfinger", "Lfinger", "Nfinger", "StartMn", "StopMn", "mismatch", "m")}
                e0 = f"SEL0<{bit}>" if bit < 8 else "BASE"
                e1 = f"SEL1<{bit}>" if bit < 8 else "VSS"
                eh, el = (e0, e1) if side == "P" else (e1, e0)
                add(sch, "XS"+suffix, f"cdac8_reset_sw_b{bit if bit<8 else 0}", x, y-14,
                    {"BOT": bottom, "EH": eh, "EL": el, "ES": "CLK_SAMPLE", "VCM": "VCM",
                     "VREFP": "VREFP", "VREFN": "VREFN", "VDD": "VDD", "VSS": "VSS"}, LIB)
    if values:
        setparams(c, cell, values)
    symbol(c, cell, PORTS, ["TOPP", "TOPN"])
    check(c, cell)


def bench(c, variant, literal=False, strongarm=False):
    cell = "tb_cdac8_reset_strongarm" if strongarm else "tb_cdac8_reset_literal" if literal else "tb_cdac8_reset_nominal"
    array_cell = "cdac8_reset_device" if literal else "cdac8_reset_nominal"
    require_new(c, cell)
    values = {}
    with c.schematic.create(LIB, cell, timeout=180) as sch:
        terms = {p: p for p in PORTS}
        terms.update(VDD="VDD!", VSS="gnd!", CLK_SAMPLE="DAC_SAMPLE", TOPP="TOPP", TOPN="TOPN")
        add(sch, "XCDAC", array_cell, 0, 8, terms, LIB)
        ctrl = {n: n for n in CTRL_IN+CTRL_OUT}
        ctrl.update(CLK_SAMPLE="PHI", VDD="VDD!", VSS="gnd!")
        ctrl.update({f"SEL{q}_{b}": f"SEL{q}<{b}>" for q in (0, 1) for b in range(8)})
        ctrl.update({f"D{b}": f"DOUT<{b}>" for b in range(8)})
        add(sch, "XCTRL", "cdac8_controller", 26, 4, ctrl, LIB)
        values["XCTRL"] = {"open_loop": "OPEN_LOOP", "fixed_code": "FIXED_CODE", "dead_time_s": "DEAD_TIME"}
        add(sch, "XINPUT", "cdac8_device_sequence", -24, -3,
            {"VDD": "VDD!", "VSS": "gnd!", "VINP_SRC": "VINP_SRC", "VINN_SRC": "VINN_SRC"}, LIB)
        values["XINPUT"] = {"stimulus_mode": "STIM_MODE", "differential_v": "VDIFF", "frequency_hz": "FIN"}
        for side, y in (("P", 17), ("N", -7)):
            add(sch, "RIN"+side, "res", -20, y, {"PLUS": "VIN"+side+"_SRC", "MINUS": "VIN"+side})
            values["RIN"+side] = {"r": "50"}
            add(sch, "XBOOT"+side, "sar_bootstrap_canvas_flat_8b", -10, y,
                {"CLKS": "PHI", "CLKSB": "CLKB"+side, "Vin": "VIN"+side, "VOUT": "TOP"+side}, LIB)
            add(sch, "RMON"+side, "res", -2, y-3, {"PLUS": "CLKB"+side, "MINUS": "gnd!"})
            values["RMON"+side] = {"r": "1T"}
        if strongarm:
            add(sch, "XCOMP", "sar_strongarm_t28", 13, 17,
                {"CLK": "CMP_CLK", "VINP": "TOPP", "VINN": "TOPN", "OUTP": "COMP_P", "OUTN": "COMP_N", "VDD": "VDD!", "VSS": "gnd!"}, LIB)
            for i, net in enumerate(("COMP_P", "COMP_N", "CMP_RESET")):
                name = "CMPLOAD"+str(i)
                add(sch, name, "cap" if i < 2 else "res", 48, 18-i*4, {"PLUS": net, "MINUS": "gnd!"})
                values[name] = {"c": "5f"} if i < 2 else {"r": "1T"}
        else:
            add(sch, "XCOMP", "sar_comparator_macro_8b", 13, 17,
                {"TOPP": "TOPP", "TOPN": "TOPN", "COMP_P": "COMP_P", "COMP_N": "COMP_N", "CMP_RESET": "CMP_RESET", "VDD": "VDD!", "VSS": "gnd!", "VCM": "VCM"}, LIB)
            add(sch, "RCMPCLK", "res", 48, 6, {"PLUS": "CMP_CLK", "MINUS": "gnd!"})
            values["RCMPCLK"] = {"r": "1T"}
        for i, (name, net, dc) in enumerate((("VVDD", "VDD!", "SUP"), ("VVCM", "VCM", "SUP/2"), ("VREFHIGH", "VREFP_SRC", "SUP"), ("VREFLOW", "VREFN_SRC", "0"))):
            add(sch, name, "vdc", -25+i*4, -22, {"PLUS": net, "MINUS": "gnd!"})
            values[name] = {"vdc": dc}
        waveforms = [("VPHI", "PHI", "1n", "39.9n", "100n", "100p"),
                     ("VDACSAMPLE", "DAC_SAMPLE", "42n", f"{48+variant.gap_ps/1000:.9g}n", "100n", "20p"),
                     ("VPREPARE", "PREPARE", "90n", "200p", "100n", "20p"),
                     ("VHOLD", "HOLD_START", "43n", "200p", "100n", "20p"),
                     ("VTRIAL", "CLK_TRIAL", "48n", "200p", "5n", "20p"),
                     ("VLATCH", "CLK_LATCH", "47.5n", "200p", "5n", "20p"),
                     ("VCOMPARE", "CLK_COMPARE", "46n", "1.53n", "5n", "20p")]
        for i, (name, net, delay, width, period, edge) in enumerate(waveforms):
            add(sch, name, "vpulse", -5+i*4, -27, {"PLUS": net, "MINUS": "gnd!"})
            values[name] = {"v1": "SUP" if name == "VDACSAMPLE" else "0", "v2": "0" if name == "VDACSAMPLE" else "SUP", "td": delay,
                            "pw": width, "per": period, "tr": edge, "tf": f"{variant.edge_ps}p" if name == "VDACSAMPLE" else edge}
        for i, side in enumerate("PN"):
            add(sch, "RREF"+side, "res", 13+i*6, -8, {"PLUS": "VREF"+side+"_SRC", "MINUS": "VREF"+side})
            values["RREF"+side] = {"r": "RREF"}
            add(sch, "CREF"+side, "cap", 13+i*6, -13, {"PLUS": "VREF"+side, "MINUS": "gnd!"})
            values["CREF"+side] = {"c": "CDECAP"}
        for i, net in enumerate([*[f"DOUT<{b}>" for b in range(8)], "BUSY", "VALID"]):
            name = "RLOAD"+str(i)
            add(sch, name, "res", 28+i*2, -22, {"PLUS": net, "MINUS": "gnd!"})
            values[name] = {"r": "1G"}
    setparams(c, cell, values)
    export(c, cell)
    c.open_window(LIB, cell, view="schematic")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["switches", "nominal", "literal", "strongarm"])
    args = parser.parse_args()
    variant = Variant(**selected_variant())
    c = VirtuosoClient.from_env(profile="t28_io")
    info = c.library.get(LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and info.technology_library == "tsmcN28"
    if args.mode == "switches":
        switches(c, variant)
    elif args.mode in ("literal", "nominal"):
        array(c, args.mode == "literal")
        bench(c, variant, literal=args.mode == "literal")
    else:
        bench(c, variant, strongarm=True)


if __name__ == "__main__":
    main()
