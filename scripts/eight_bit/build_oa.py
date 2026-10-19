"""Create only the explicitly owned 8-bit OA cells, with readback/export gates."""
from __future__ import annotations

import argparse
import json
import os
import sys

from common import ROOT, OUT, LIB, CU, CDAC, CTRL, MACRO_TB, BOOT_TB, NATIVE, SIZED, COMP_TB, dump, config, digest
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_create_pin as pin,
    schematic_label_instance_term as term,
)
from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update
from virtuoso_bridge.virtuoso.symbol.ops import (
    symbol_create_instance_label, symbol_create_logical_label,
    symbol_create_pin, symbol_create_rect, symbol_create_selection_box, symbol_set_term_order,
)

CMAC = "sar_comparator_macro_8b"
READONLY = ("sar_cdac_macro_10b", "sar_sampling_macro", "sar_comparator_macro", "sar_bootstrap", NATIVE, "sar_strongarm_t28")


def skill(client, expr):
    r = client.execute_skill(expr, timeout=120)
    if r.errors:
        raise RuntimeError(str(r))
    return r.output


def exists(client, cell):
    return (skill(client, f'ddGetObj("{LIB}" "{cell}")') or "").strip() not in ("", "nil")


def refuse(client, *cells):
    assert not any(exists(client, c) for c in cells), f"Refuse existing target(s): {cells}"


def settings(client, cell, values):
    for name, params in values.items():
        _run_batched_param_update(client, LIB, cell, name, params)
    with client.schematic.modify(LIB, cell, timeout=180):
        pass


def add(sch, name, master, x, y, terms, lib="analogLib"):
    sch.add(inst(lib, master, "symbol", name, x, y, "R0"))
    for port, net in terms.items():
        sch.add(term(name, port, net))


def switch(sch, name, x, y, a, b, ctrl):
    add(sch, name, "switch", x, y, {"N+":a, "N-":b, "NC+":ctrl, "NC-":"VSS"})


def wide_symbol(client, cell, inputs, outputs, bidirectional=(), order=None):
    height = max(len(inputs), len(outputs) + len(bidirectional)) * .5 + .75
    with client.symbol.create(LIB, cell, timeout=120) as sym:
        sym.add(symbol_create_rect("device", "drawing", .75, -.5, 7.25, height))
        sym.add(symbol_create_selection_box(0, -.75, 8, height+.25))
        for names, x, lx, justify, direction in ((inputs, 0, .9, "centerLeft", "input"),
                                                 (outputs, 8, 7.1, "centerRight", "output"),
                                                 (bidirectional, 8, 7.1, "centerRight", "inputOutput")):
            start = len(outputs) if direction == "inputOutput" else 0
            for i, name in enumerate(names):
                y = height - .5 - (i+start)*.5
                sym.add(symbol_create_pin(name, x, y, direction=direction, half_size=.025,
                                          label_x=lx, label_y=y, label_justification=justify))
        sym.add(symbol_create_instance_label(2, height+.4))
        sym.add(symbol_create_logical_label(4, height/2))
        sym.add(symbol_set_term_order(order or [*inputs, *outputs, *bidirectional]))


def check(client, cell, *, electrical=True):
    if electrical:
        with client.schematic.modify(LIB, cell, timeout=180):
            pass
        data = client.schematic.read(LIB, cell, include_positions=True, param_filters=None)
        dump(f"oa/{cell}_readback.json", data)
        cv = f'dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")'
        markers = client.fetch(cv+"~>markers", ["objType", "severity", "bBox"])
        dump(f"oa/{cell}_markers.json", markers)
        assert not markers, (cell, markers)
    if cell not in (MACRO_TB, BOOT_TB, COMP_TB):
        dump(f"oa/{cell}_ports.json", client.symbol.read_ports(LIB, cell))
    print("OA_CHECKED", cell, flush=True)


def preflight(client):
    lib = client.library.get(LIB)
    assert lib.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and lib.technology_library == "tsmcN28"
    dump("oa/library.json", vars(lib))
    dump("oa/windows_before.json", client.list_windows())
    for cell in READONLY:
        data = client.schematic.read(LIB, cell, param_filters=None, include_positions=True)
        path = OUT / "oa" / (cell+"_before.json")
        if path.exists():
            assert json.loads(path.read_text()) == data, f"Read-only dependency changed: {cell}"
        else:
            dump(f"oa/{cell}_before.json", data)


def cdac(client):
    refuse(client, CDAC)
    caps, switches = {}, []
    inputs = ["BASE", "CLK_SAMPLE", *[f"SEL{q}<{b}>" for q in (0,1) for b in range(8)], "VCM", "VREFN", "VREFP", "VSS"]
    with client.schematic.create(LIB, CDAC) as sch:
        for i, name in enumerate(inputs):
            sch.add(pin(name, -10, 12-i, "R0", direction="input"))
        for name, y in (("TOPP", 10), ("TOPN", -9)):
            sch.add(pin(name, 25, y, "R180", direction="inputOutput"))
    for side, y, ref0, ref1 in (("P", 10, "VREFP", "VREFN"), ("N", -9, "VREFN", "VREFP")):
        for group in ((7,6,5,4), (3,2,1,0), (None,)):
            with client.schematic.modify(LIB, CDAC, timeout=180) as sch:
                for bit in group:
                    suffix = f"{bit}{side}" if bit is not None else "DUMMY"+side
                    x = 2*(7-bit) if bit is not None else 18
                    cap, bot = "C"+suffix, "B"+suffix
                    add(sch, cap, "cap", x, y, {"PLUS":"TOP"+side, "MINUS":bot})
                    caps[cap] = {"c":f"{CU * (2**bit if bit is not None else 1):.12g}"}
                    for k, target, ctrl in (("S", "VCM", "CLK_SAMPLE"), ("0", ref0, f"SEL0<{bit}>" if bit is not None else "BASE"),
                                             *(([("1", ref1, f"SEL1<{bit}>")] if bit is not None else []))):
                        nm = "S"+suffix+k
                        switch(sch, nm, x, y-2-2*len([n for n in switches if n.startswith("S"+suffix)]), bot, target, ctrl)
                        switches.append(nm)
    values = {**caps, **{n:{"rc":"RBOTTOM", "ro":"1T", "vt1":"350m", "vt2":"550m"} for n in switches}}
    settings(client, CDAC, values)
    wide_symbol(client, CDAC, inputs, [], ["TOPN", "TOPP"])
    check(client, CDAC)
    state = client.schematic.read(LIB, CDAC, param_filters=None)
    assert sum(i["cell"] == "cap" for i in state["instances"]) == 18
    assert sum(i["cell"] == "switch" for i in state["instances"]) == 52
    assert not any("LSB" in n or "BRIDGE" in n for n in state["nets"])


def copy_schematic(client, source, target):
    refuse(client, target)
    skill(client, f'''let((s d) s=dbOpenCellViewByType("{LIB}" "{source}" "schematic" "schematic" "r")
      unless(s error("missing copy source")) when(s~>modified error("unsaved copy source"))
      d=dbCopyCellView(s "{LIB}" "{target}" "schematic" nil nil nil)
      unless(d error("copy failed")) schCheck(d) dbSave(d) dbClose(d) t)''')


def controller(client):
    refuse(client, CTRL)
    inputs = ["COMP_P", "COMP_N", "CLK_SAMPLE", "CLK_TRIAL", "CLK_LATCH", "VDD", "VSS"]
    outputs = [*[f"SEL{q}_{b}" for q in (0,1) for b in range(7,-1,-1)], "BASE", *[f"D{b}" for b in range(7,-1,-1)], "BUSY", "VALID"]
    # Create a semantic symbol directly; no floating schematic is left to
    # shadow the behavioral view during hierarchical netlisting.
    wide_symbol(client, CTRL, inputs, outputs)
    result = skill(client, f'schViewToView("{LIB}" "{CTRL}" "{LIB}" "{CTRL}" "symbol" "veriloga" "schSymbolToPinList" "ahdlPinListToveriloga")')
    assert result and result.strip() != "nil", result
    path = f'/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{CTRL}/veriloga/veriloga.va'
    source = ROOT / "models/veriloga/sar_macro_controller_8b.va"
    client.upload_file(source, path, timeout=120)
    skill(client, f'ahdlUpdateViewInfo("{LIB}" ?cell "{CTRL}" ?view "veriloga")')
    check(client, CTRL, electrical=False)


def macro(client, repair=False):
    if not repair:
        refuse(client, MACRO_TB, CMAC)
        copy_schematic(client, "sar_comparator_macro", CMAC)
        settings(client, CMAC, {"CKBP":{"c":"CKB"}, "CKBN":{"c":"CKB"}})
        client.symbol.generate_from_schematic(LIB, CMAC, overwrite=False, timeout=120)
    else:
        assert exists(client, MACRO_TB) and exists(client, CMAC)
        cv = f'dbFindOpenCellViewByName("{LIB}" "{MACRO_TB}" "schematic")'
        skill(client, f'let((cv) cv={cv} when(cv && cv~>modified error("unsaved owned target")) t)')
    check(client, CMAC)
    values = {}
    with client.schematic.create(LIB, MACRO_TB, timeout=180) as sch:
        add(sch, "XSAMPLE", "sar_sampling_macro", -18, 12,
            {"VINP":"VINP", "VINN":"VINN", "TOPP":"TOPP", "TOPN":"TOPN", "CLK_SAMPLE":"CLK_SAMPLE", "VSS":"gnd!"}, LIB)
        add(sch, "XCDAC", CDAC, -2, 5, {"TOPP":"TOPP", "TOPN":"TOPN", "VCM":"VCM", "VREFP":"VREFP", "VREFN":"VREFN", "VSS":"gnd!", "BASE":"BASE", "CLK_SAMPLE":"CLK_SAMPLE",
            **{f"SEL{q}<{b}>":f"SEL{q}<{b}>" for q in (0,1) for b in range(8)}}, LIB)
        add(sch, "XCOMP", CMAC, 12, 12, {"TOPP":"TOPP", "TOPN":"TOPN", "COMP_P":"COMP_P", "COMP_N":"COMP_N", "VCM":"VCM", "VDD":"VDD!", "VSS":"gnd!", "CMP_RESET":"CMP_RESET"}, LIB)
        add(sch, "XCTRL", CTRL, 22, 2, {"COMP_P":"COMP_P", "COMP_N":"COMP_N", "CLK_SAMPLE":"CLK_SAMPLE", "CLK_TRIAL":"CLK_TRIAL", "CLK_LATCH":"CLK_LATCH", "VDD":"VDD!", "VSS":"gnd!", "BASE":"BASE", "BUSY":"BUSY", "VALID":"VALID",
            **{f"SEL{q}_{b}":f"SEL{q}<{b}>" for q in (0,1) for b in range(8)}, **{f"D{b}":f"DOUT<{b}>" for b in range(8)}}, LIB)
        for i, (name, net, dc) in enumerate((("VVDD", "VDD!", ".9"), ("VVCM", "VCM", ".45"), ("V_SRC_REFP", "VREFP_IDEAL", ".9"), ("V_SRC_REFN", "VREFN_IDEAL", "0"),
                                             ("V_SRC_INP", "VINP", "0.45+VDIFF/2"), ("V_SRC_INN", "VINN", "0.45-VDIFF/2"))):
            add(sch, name, "vdc", -20+i*3, -18, {"PLUS":net, "MINUS":"gnd!"})
            values[name] = {"vdc":dc}
        for i, (name, net, v1, v2, td, pw, per) in enumerate((("VSAMPLE", "CLK_SAMPLE", ".9", "0", "41n", "100n", "200n"),
                ("VTRIAL", "CLK_TRIAL", "0", ".9", "46n", "200p", "5n"), ("VLATCH", "CLK_LATCH", "0", ".9", "45.5n", "200p", "5n"),
                ("VCMPRESET", "CMP_RESET", ".9", "0", "44n", "1.53n", "5n"))):
            add(sch, name, "vpulse", 2+i*3, -18, {"PLUS":net, "MINUS":"gnd!"})
            values[name] = {"v1":v1,"v2":v2,"td":td,"pw":pw,"per":per,"tr":"20p","tf":"20p"}
        for side, x in (("P", 8), ("N", 11)):
            for index, (name, master, a, b, key, value) in enumerate((("RREF"+side, "res", "VREF"+side+"_IDEAL", "VREF"+side, "r", "RREF"),
                    ("CREF"+side, "cap", "VREF"+side, "gnd!", "c", "CDECAP"), ("CTOP"+side, "cap", "TOP"+side, "VCM", "c", "CTOPPAR"))):
                add(sch, name, master, x, -8-3*index, {"PLUS":a,"MINUS":b})
                values[name] = {key:value}
        for i, net in enumerate([*[f"DOUT<{b}>" for b in range(8)], "BUSY", "VALID"]):
            add(sch, "RLOAD"+str(i), "res", 20+i, -18, {"PLUS":net,"MINUS":"gnd!"})
            values["RLOAD"+str(i)] = {"r":"1G"}
    settings(client, MACRO_TB, values)
    client.open_window(LIB, MACRO_TB, view="schematic")
    export(client, MACRO_TB)


def bootstrap(client, candidate=NATIVE, tag="initial", repair=False):
    if not repair:
        refuse(client, BOOT_TB)
    else:
        skill(client, f'let((cv) cv=dbFindOpenCellViewByName("{LIB}" "{BOOT_TB}" "schematic") when(cv && cv~>modified error("unsaved owned target")) t)')
    values = {}
    with client.schematic.create(LIB, BOOT_TB, timeout=180) as sch:
        for variant, y in (("OLD", 15), ("NEW", -10)):
            add(sch, "XCDAC_"+variant, CDAC, 18, y, {"BASE":"BASE", "CLK_SAMPLE":"PHI", "TOPP":"TOPP_"+variant, "TOPN":"TOPN_"+variant,
                 "VCM":"VCM", "VREFP":"VCM", "VREFN":"VCM", "VSS":"gnd!", **{f"SEL0<{b}>":"BASE" for b in range(8)}, **{f"SEL1<{b}>":"gnd!" for b in range(8)}}, LIB)
            for side, dy in (("P", 5), ("N", -6)):
                vin, vout = "VIN"+side+"_"+variant, "TOP"+side+"_"+variant
                terms = ({"PHI":"PHI", "PHIB":"PHIB", "VDD":"VDD!", "VSS":"gnd!", "VIN":vin, "VOUT":vout} if variant=="OLD" else {"CLKS":"PHI", "CLKSB":"CLKB_"+side, "Vin":vin, "VOUT":vout})
                add(sch, "X"+variant+"_"+side, "sar_bootstrap" if variant=="OLD" else candidate, 6, y+dy, terms, LIB)
                nm = "VIN_"+variant+"_"+side
                add(sch, nm, "vpulse", -6, y+dy, {"PLUS":vin+"_SRC", "MINUS":"gnd!"})
                sign = "+" if side=="P" else "-"
                opp = "-" if side=="P" else "+"
                values[nm] = {"v1":"0.45"+opp+"VDIFF/2", "v2":"0.45"+sign+"VDIFF/2", "td":"205n", "tr":"100p", "tf":"100p", "pw":"80n", "per":"400n"}
                rn = "RIN_"+variant+"_"+side
                add(sch, rn, "res", 1, y+dy, {"PLUS":vin+"_SRC", "MINUS":vin})
                values[rn] = {"r":"50"}
        for name, master, net, params, y in (("VVDD", "vdc", "VDD!", {"vdc":".9"}, 15), ("VVCM", "vdc", "VCM", {"vdc":".45"}, 11),
              ("VPHI", "vpulse", "PHI", {"v1":"0","v2":".9","td":"11n","pw":"39n","per":"100n","tr":"100p","tf":"100p"}, 7),
              ("VPHIB", "vpulse", "PHIB", {"v1":".9","v2":"0","td":"10n","pw":"41n","per":"100n","tr":"100p","tf":"100p"}, 3),
              ("VBASE", "vpulse", "BASE", {"v1":"0","v2":".9","td":"52n","pw":"50n","per":"100n","tr":"100p","tf":"100p"}, -1)):
            add(sch, name, master, -12, y, {"PLUS":net, "MINUS":"gnd!"})
            values[name] = params
        for side, y in (("P", -4), ("N", -15)):
            add(sch, "RMON_"+side, "res", 13, y, {"PLUS":"CLKB_"+side,"MINUS":"gnd!"})
            values["RMON_"+side] = {"r":"1T"}
    settings(client, BOOT_TB, values)
    client.open_window(LIB, BOOT_TB, view="schematic")
    export(client, BOOT_TB, tag)


def sized_bootstrap(client, width):
    # Independent candidate: the prior 10-bit native source is never resized.
    assert width in (1, 2)
    if not exists(client, SIZED):
        copy_schematic(client, NATIVE, SIZED)
        client.symbol.generate_from_schematic(LIB, SIZED, overwrite=False, timeout=120)
    settings(client, SIZED, {"Mmain":{"w":f"{width}u", "Wfg":f"{width}u", "l":"150n", "nf":"1", "fingers":"1"}})
    check(client, SIZED)
    bootstrap(client, candidate=SIZED, tag=f"w{width}u", repair=True)


def comparator_interface(client, tag="initial"):
    if tag=="initial":
        refuse(client, COMP_TB)
    else:
        skill(client, f'let((cv) cv=dbFindOpenCellViewByName("{LIB}" "{COMP_TB}" "schematic") when(cv && cv~>modified error("unsaved owned target")) t)')
    candidate = SIZED if exists(client, SIZED) else NATIVE
    ports=client.symbol.read_ports(LIB,"sar_strongarm_t28")
    assert {t["name"] for t in ports["terms"]}=={"CLK","VINP","VINN","OUTP","OUTN","VDD","VSS"}
    dump("oa/strongarm_interface_ports.json",ports)
    values={}
    with client.schematic.create(LIB, COMP_TB, timeout=180) as sch:
        add(sch,"XCDAC",CDAC,18,5,{"BASE":"BASE","CLK_SAMPLE":"PHI","TOPP":"TOPP","TOPN":"TOPN","VCM":"VCM","VREFP":"VCM","VREFN":"VCM","VSS":"gnd!",
            **{f"SEL0<{b}>":"BASE" for b in range(8)}, **{f"SEL1<{b}>":"gnd!" for b in range(8)}},LIB)
        for side,y in (("P",12),("N",-8)):
            add(sch,"XNEW_"+side,candidate,4,y,{"CLKS":"PHI","CLKSB":"CLKB_"+side,"Vin":"VIN"+side,"VOUT":"TOP"+side},LIB)
            add(sch,"VIN_SRC_"+side,"vpulse",-10,y,{"PLUS":"VIN"+side+"_SRC","MINUS":"gnd!"})
            sign,opp=("+","-") if side=="P" else ("-","+")
            values["VIN_SRC_"+side]={"v1":".45"+opp+"VDIFF/2","v2":".45"+sign+"VDIFF/2","td":"205n","tr":"100p","tf":"100p","pw":"80n","per":"400n"}
            for name,master,a,b,params,x in (("RIN_"+side,"res","VIN"+side+"_SRC","VIN"+side,{"r":"50"},-3),
                    ("RMON_"+side,"res","CLKB_"+side,"gnd!",{"r":"1T"},13),
                    ("CLOAD_"+side,"cap","OUT"+side,"gnd!",{"c":"5f"},32)):
                add(sch,name,master,x,y,{"PLUS":a,"MINUS":b});values[name]=params
        add(sch,"XCMP","sar_strongarm_t28",25,4,{"CLK":"CMP_CLK","VINP":"TOPP","VINN":"TOPN","OUTP":"OUTP","OUTN":"OUTN","VDD":"VDD!","VSS":"gnd!"},LIB)
        for i,(name,master,net,params) in enumerate((("VVDD","vdc","VDD!",{"vdc":".9"}),("VVCM","vdc","VCM",{"vdc":".45"}),
                ("VPHI","vpulse","PHI",{"v1":"0","v2":".9","td":"11n","pw":"39n","per":"100n","tr":"100p","tf":"100p"}),
                ("VBASE","vpulse","BASE",{"v1":"0","v2":".9","td":"52n","pw":"50n","per":"100n","tr":"100p","tf":"100p"}),
                ("VCMPCLK","vpulse","CMP_CLK",{"v1":"0","v2":"CMP_HIGH","td":"55n","pw":"2n","per":"100n","tr":"20p","tf":"20p"}))):
            add(sch,name,master,-15+i*4,-18,{"PLUS":net,"MINUS":"gnd!"});values[name]=params
    settings(client,COMP_TB,values)
    client.open_window(LIB,COMP_TB,view="schematic")
    export(client,COMP_TB,tag)


def export(client, cell, tag="initial"):
    check(client, cell)
    path = OUT / "oa_netlists" / cell / tag
    assert not (path / "input.scs").exists(), "Preserve existing exact OA export"
    result = client.schematic.export_netlist(LIB, cell, path, simulator="spectre", timeout=180)
    dump(f"oa/{cell}_{tag}_export.json", result)
    print("EXPORTED", cell, result["input_file"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preflight", "cdac", "controller", "macro", "repair-macro", "bootstrap", "size", "comparator", "final"))
    parser.add_argument("--width", type=int, choices=(1,2), default=1)
    parser.add_argument("--tag",default="initial")
    args = parser.parse_args()
    os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
    client = VirtuosoClient.from_env(profile="t28_io")
    if args.action == "size":
        sized_bootstrap(client,args.width)
        return
    if args.action == "comparator":
        comparator_interface(client,args.tag)
        return
    if args.action == "repair-macro":
        macro(client, repair=True)
        return
    if args.action == "final":
        for cell in READONLY:
            now = client.schematic.read(LIB, cell, param_filters=None, include_positions=True)
            assert now == json.loads((OUT / "oa" / (cell+"_before.json")).read_text()), cell
        for cell in (CDAC, CMAC, MACRO_TB, BOOT_TB):
            check(client, cell)
        for cell in (SIZED, COMP_TB):
            if exists(client,cell):check(client,cell)
        comparisons=[]
        for cell,tag in ((MACRO_TB,"initial"),(BOOT_TB,"w1u"),(COMP_TB,"w1u")):
            export(client,cell,"final")
            original=OUT/"oa_netlists"/cell/tag/"input.scs"
            fresh=OUT/"oa_netlists"/cell/"final/input.scs"
            clean=lambda s:"\n".join(line for line in s.splitlines() if not line.startswith("// Generated on:"))
            assert clean(original.read_text())==clean(fresh.read_text()), f"Saved OA differs from simulated hierarchy: {cell}"
            comparisons.append({"cell":cell,"simulated_oa_sha256":digest(original),"fresh_oa_sha256":digest(fresh),"equal_except_generation_date":True})
        va_path=OUT/"oa/controller_final.va"
        result=client.download_file(f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{CTRL}/veriloga/veriloga.va",va_path,timeout=120)
        assert not result.errors,result
        assert va_path.read_bytes()==(ROOT/"models/veriloga/sar_macro_controller_8b.va").read_bytes()
        dump("oa/final_readonly_check.json", {"unchanged":list(READONLY),"fresh_exports":comparisons,"controller_va_matches_local":True})
        return
    {"preflight":preflight,"cdac":cdac,"controller":controller,"macro":macro,"bootstrap":bootstrap}[args.action](client)


if __name__ == "__main__":
    main()
