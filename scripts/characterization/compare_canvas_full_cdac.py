"""Exact-OA full-CDAC comparison: original bootstrap vs native Canvas W=0.5 um."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
from pathlib import Path

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre import SpectreSimulator
from virtuoso_bridge.spectre.runner import spectre_mode_args
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name as inst,
    schematic_label_instance_term as term,
)
from virtuoso_bridge.virtuoso.schematic.params import _run_batched_param_update

from canvas_bootstrap_t28 import signal, interpolate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/canvas_full_cdac"
LIB = "SAR_ADC_T28"
ORIGINAL, SOURCE = "sar_bootstrap", "sar_bootstrap_canvas_t28"
DUT, TB, CDAC = "sar_bootstrap_canvas_cdac_t28", "tb_bootstrap_canvas_full_cdac", "sar_cdac_macro_10b"
INPUTS = (-0.8, -0.4, 0.0, 0.4, 0.8)


def dump(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def skill(client, expression):
    result = client.execute_skill(expression)
    if result.errors:
        raise RuntimeError(str(result))
    return result.output


def exists(client, cell):
    return (skill(client, f'ddGetObj("{LIB}" "{cell}")') or "").strip() not in ("", "nil")


def inspect(client):
    info = client.library.get(LIB)
    assert info.technology_library == "tsmcN28", info
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28", info
    dump("library.json", vars(info))
    dump("windows.json", client.list_windows())
    for cell in (SOURCE, ORIGINAL, CDAC):
        snapshot = client.schematic.read(LIB, cell, include_positions=True, param_filters=None)
        saved = OUT / (cell + "_before.json")
        if saved.exists():
            assert json.loads(saved.read_text()) == snapshot, f"Read-only dependency changed: {cell}"
        else:
            dump(cell + "_before.json", snapshot)
        dump(cell + "_ports.json", client.symbol.read_ports(LIB, cell))
    print("INSPECTED exact library, technology, three read-only dependencies", flush=True)


def create(client):
    assert not exists(client, DUT) and not exists(client, TB), "Refuse existing targets"
    inspect(client)
    # Verified dbCopyCellView contract from bridge symbol/generator.py; keep the
    # native topology, all derived CDF geometry and original routes unchanged.
    skill(client, f'''let((src dst cap)
      src=dbOpenCellViewByType("{LIB}" "{SOURCE}" "schematic" "schematic" "r")
      unless(src error("native source missing"))
      when(src~>modified error("source is unsaved"))
      dst=dbCopyCellView(src "{LIB}" "{DUT}" "schematic" nil nil nil)
      unless(dst error("copy failed"))
      cap=car(setof(x dst~>instances x~>name=="Cs"))
      unless(cap error("expected standalone Cs missing"))
      dbDeleteObject(cap)
      foreach(shape dst~>shapes
        when(member(shape~>objType list("line" "label")) &&
          xCoord(car(shape~>bBox))>4.7 && xCoord(cadr(shape~>bBox))<5.2 &&
          yCoord(cadr(shape~>bBox))<0.9
          dbDeleteObject(shape)))
      schCheck(dst) dbSave(dst) dbClose(dst) t)''')
    with client.schematic.modify(LIB, DUT):
        pass
    client.symbol.generate_from_schematic(LIB, DUT, overwrite=False, timeout=90)

    source = json.loads((OUT / (SOURCE + "_before.json")).read_text())
    derived = client.schematic.read(LIB, DUT, include_positions=True, param_filters=None)
    dump("candidate_readback.json", derived)
    before = {x["name"]: x for x in source["instances"] if x["name"] != "Cs"}
    after = {x["name"]: x for x in derived["instances"]}
    assert before == after, "Candidate differs from selected native source minus Cs"
    assert len(after) == 13 and sum(x["lib"] == "tsmcN28" for x in after.values()) == 12

    with client.schematic.create(LIB, TB, timeout=180) as sch:
        for variant, y in (("OLD", 14.0), ("NEW", -8.0)):
            sch.add(inst(LIB, CDAC, "symbol", f"XCDAC_{variant}", 18.0, y, "R0"))
            cdac_terms = {"BASE":"BASE", "CLK_SAMPLE":"PHI", "TOPP":f"TOPP_{variant}",
                          "TOPN":f"TOPN_{variant}", "VCM":"VCM", "VREFP":"VCM", "VREFN":"VCM", "VSS":"gnd!"}
            cdac_terms.update({f"SEL0<{b}>":"BASE" for b in range(10)})
            cdac_terms.update({f"SEL1<{b}>":"gnd!" for b in range(10)})
            for port, net in cdac_terms.items():
                sch.add(term(f"XCDAC_{variant}", port, net))
            for side, dy in (("P", 4.0), ("N", -5.0)):
                name = f"X{variant}_{side}"
                sch.add(inst(LIB, ORIGINAL if variant == "OLD" else DUT, "symbol", name, 7.0, y + dy, "R0"))
                pins = ({"PHI":"PHI", "PHIB":"PHIB", "VDD":"VDD!", "VSS":"gnd!",
                         "VIN":f"VIN{side}_{variant}", "VOUT":f"TOP{side}_{variant}"}
                        if variant == "OLD" else
                        {"CLKS":"PHI", "CLKSB":f"CLKB_{side}", "Vin":f"VIN{side}_{variant}", "VOUT":f"TOP{side}_{variant}"})
                for port, net in pins.items():
                    sch.add(term(name, port, net))
                for suffix, master, x, plus, minus in (
                    ("VIN", "vpulse", -4, f"VIN{side}_{variant}_SRC", "gnd!"),
                    ("RIN", "res", 1, f"VIN{side}_{variant}_SRC", f"VIN{side}_{variant}"),
                ):
                    nm = f"{suffix}_{variant}_{side}"
                    sch.add(inst("analogLib", master, "symbol", nm, x, y + dy, "R0"))
                    sch.add(term(nm, "PLUS", plus))
                    sch.add(term(nm, "MINUS", minus))
        for name, master, y, net in (("VVDD", "vdc", 14, "VDD!"), ("VVCM", "vdc", 10, "VCM"),
                                      ("VPHI", "vpulse", 6, "PHI"), ("VPHIB", "vpulse", 2, "PHIB"),
                                      ("VBASE", "vpulse", -2, "BASE")):
            sch.add(inst("analogLib", master, "symbol", name, -10, y, "R0"))
            sch.add(term(name, "PLUS", net))
            sch.add(term(name, "MINUS", "gnd!"))
    settings = [("VVDD", {"vdc":"900m"}), ("VVCM", {"vdc":"450m"}),
                ("VPHI", {"v1":"0", "v2":"900m", "td":"11n", "tr":"100p", "tf":"100p", "pw":"39n", "per":"100n"}),
                ("VPHIB", {"v1":"900m", "v2":"0", "td":"10n", "tr":"100p", "tf":"100p", "pw":"41n", "per":"100n"}),
                ("VBASE", {"v1":"0", "v2":"900m", "td":"52n", "tr":"100p", "tf":"100p", "pw":"50n", "per":"100n"})]
    for variant in ("OLD", "NEW"):
        for side in ("P", "N"):
            target, previous = ("vinp_target", "vinn_target") if side == "P" else ("vinn_target", "vinp_target")
            settings.extend([(f"VIN_{variant}_{side}", {"v1":previous, "v2":target, "td":"205n", "tr":"100p", "tf":"100p", "pw":"80n", "per":"400n"}),
                             (f"RIN_{variant}_{side}", {"r":"50"})])
    for name, params in settings:
        _run_batched_param_update(client, LIB, TB, name, params)
    with client.schematic.modify(LIB, TB):
        pass
    client.open_window(LIB, TB, view="schematic")
    add_monitors(client)


def block(text, name):
    found = re.search(rf"(?ms)^subckt {re.escape(name)}\b.*?^ends {re.escape(name)}$", text)
    if found is None:
        raise ValueError(f"Missing subckt {name}")
    return found.group()


def verify_export(client):
    for cell in (DUT, TB):
        dump(cell + "_readback.json", client.schematic.read(LIB, cell, include_positions=True, param_filters=None))
        cv = f'dbOpenCellViewByType("{LIB}" "{cell}" "schematic" "" "r")'
        markers = client.fetch(cv + "~>markers", ["objType", "severity", "reason", "message", "why", "bBox"])
        dump(cell + "_markers.json", markers)
        assert not markers, f"Check & Save markers in {cell}: {markers}"
    preserved = OUT / "oa_netlist/input.scs"
    target = OUT / ("verification_oa_netlist" if preserved.exists() else "oa_netlist")
    exported = client.schematic.export_netlist(LIB, TB, target, simulator="spectre", timeout=180)
    dump("verification_export.json" if preserved.exists() and target.name != "oa_netlist" else "export.json", exported)
    current = Path(exported["input_file"]).read_text()
    if target.name != "oa_netlist":
        clean = lambda s:"\n".join(line for line in s.splitlines() if not line.startswith("// Generated on:"))
        assert clean(current) == clean(preserved.read_text()), "Refuse to replace primary simulation provenance"
        current = preserved.read_text()
    historical = (ROOT / "output/bootstrap_bottom_plate_eval/netlist/tb_sar_bottom_plate_eval/input.scs").read_text()
    native = (ROOT / "output/canvas_bootstrap_t28/oa_netlists/final/input.scs").read_text()
    normalize = lambda s: re.sub(r"\s+", " ", s.replace("\\\n", " ")).strip()
    expect = block(native, SOURCE).replace(SOURCE, DUT)
    expect, count = re.subn(r"(?m)^    Cs \(VOUT 0\) capacitor c=1p\n", "", expect)
    assert count == 1
    checks = {
        "native_exact_except_cs_and_name": normalize(expect) == normalize(block(current, DUT)),
        "original_bootstrap_exact_historical": normalize(block(historical, ORIGINAL)) == normalize(block(current, ORIGINAL)),
        "full_cdac_exact_historical": normalize(block(historical, CDAC)) == normalize(block(current, CDAC)),
        "no_parallel_single_ended_cs": "Cs (VOUT 0)" not in block(current, DUT),
        "two_cdac_copies": len(re.findall(r"(?m)^XCDAC_(OLD|NEW) ", current)) == 2,
        "oa_sha256": hashlib.sha256(current.encode()).hexdigest(),
    }
    dump("netlist_equivalence.json", checks)
    assert all(v for k, v in checks.items() if k != "oa_sha256"), checks
    print("OA_EQUIVALENCE", json.dumps(checks), flush=True)


def add_monitors(client):
    # A physical inverter output is an observation-only boundary port. Give
    # each a finite, negligible conductance rather than an unterminated stub.
    state = client.schematic.read(LIB, TB)
    assert not any(i["name"].startswith("RMON_") for i in state["instances"])
    with client.schematic.modify(LIB, TB) as sch:
        for side, y in (("P", -3.0), ("N", -12.0)):
            name = "RMON_" + side
            sch.add(inst("analogLib", "res", "symbol", name, 13.0, y, "R0"))
            sch.add(term(name, "PLUS", "CLKB_" + side))
            sch.add(term(name, "MINUS", "gnd!"))
    for side in ("P", "N"):
        _run_batched_param_update(client, LIB, TB, "RMON_" + side, {"r":"1T"})
    with client.schematic.modify(LIB, TB):
        pass
    verify_export(client)


def final_check(client):
    for cell in (SOURCE, ORIGINAL, CDAC):
        after = client.schematic.read(LIB, cell, include_positions=True, param_filters=None)
        before = json.loads((OUT / (cell + "_before.json")).read_text())
        dump(cell + "_after.json", after)
        assert before == after, f"Read-only dependency changed: {cell}"
    fresh = client.schematic.export_netlist(LIB, TB, OUT / "final_oa_netlist", simulator="spectre", timeout=180)
    old = (OUT / "oa_netlist/input.scs").read_text()
    new = Path(fresh["input_file"]).read_text()
    clean = lambda s:"\n".join(line for line in s.splitlines() if not line.startswith("// Generated on:"))
    assert clean(old) == clean(new), "Saved OA no longer matches the simulated primary circuit"
    dump("final_check.json", {"read_only_dependencies_unchanged":True,
                              "saved_oa_matches_simulated_export_except_date":True,
                              "simulated_oa_sha256":hashlib.sha256(old.encode()).hexdigest(),
                              "final_oa_sha256":hashlib.sha256(new.encode()).hexdigest()})
    windows = client.list_windows()
    dump("final_windows.json", windows)
    target = next(w for w in windows if f" {TB} schematic" in (w.get("name") or ""))
    wid = int(target["num"])
    skill(client, f'hiZoomIn(window({wid}) list(list(-11 -15) list(25 22)))')
    skill(client, f'hiRedraw(window({wid}))')
    client.screenshot(OUT / "comparison_schematic.png", target=wid)
    print("FINAL_CHECK read-only dependencies unchanged; saved OA matches simulations", flush=True)


def save_names():
    names = ["PHI", "PHIB", "BASE", "VCM", "VDD!", "CLKB_P", "CLKB_N"]
    for variant in ("OLD", "NEW"):
        for side in ("P", "N"):
            names.extend([f"TOP{side}_{variant}", f"VIN{side}_{variant}", f"VIN{side}_{variant}_SRC",
                          f"XCDAC_{variant}.B9{side}", f"XCDAC_{variant}.LSB{side}",
                          f"X{variant}_{side}.G", f"X{variant}_{side}.BTOP", f"X{variant}_{side}.BBOT",
                          f"X{variant}_{side}.CTRL"])
            names.extend([f"X{variant}_{side}.{n}" for n in (("GCLAMP", "P1", "P2") if variant == "OLD" else ("GRESET",))])
    return names


def remove_old_branch(source):
    """Diagnostic only: retain unused definitions, omit old top-level loads."""
    targets = {"XCDAC_OLD", "XOLD_P", "XOLD_N", "VIN_OLD_P", "VIN_OLD_N", "RIN_OLD_P", "RIN_OLD_N"}
    lines, removed, keep = source.splitlines(keepends=True), set(), []
    i = 0
    while i < len(lines):
        head = lines[i].split()
        name = head[0] if head and not lines[i][0].isspace() else None
        statement = [lines[i]]
        i += 1
        while statement[-1].rstrip().endswith("\\"):
            statement.append(lines[i])
            i += 1
        if name in targets:
            removed.add(name)
        else:
            keep.extend(statement)
    assert removed == targets, removed
    return "".join(keep)


def matched_reset(source, vd):
    """Stimulus-only control: match the candidate's nominal 50% crossings."""
    stem = f"nominal_vd{'m' if vd < 0 else 'p'}{abs(round(vd * 1000)):03d}"
    wave = json.loads((OUT / (stem + "_waveform.json")).read_text())
    events = {}
    time, values = wave["time"], wave["CLKB_P"]
    for name, a, b, rising in (("fall", 210e-9, 212e-9, False), ("rise", 250e-9, 251e-9, True)):
        crossings = []
        for i in range(len(time) - 1):
            if a <= time[i] <= b and ((values[i] <= .45 < values[i+1]) if rising else (values[i] >= .45 > values[i+1])):
                crossings.append(time[i] + (.45 - values[i]) * (time[i+1] - time[i]) / (values[i+1] - values[i]))
        assert len(crossings) == 1, crossings
        events[name] = crossings[0]
    delay = events["fall"] - 200e-9 - 50e-12
    width = events["rise"] - events["fall"] - 100e-12
    match = re.search(r"(?ms)^VPHIB .*?(?=^\S)", source)
    assert match and match.group().count("delay=10n") == 1 and match.group().count("width=41n") == 1
    changed = match.group().replace("delay=10n", f"delay={delay:.14g}").replace("width=41n", f"width={width:.14g}")
    return source[:match.start()] + changed + source[match.end():], events


def run(inputs, tag="nominal", maxstep="10p", reltol="1e-5", only_new=False):
    source = (OUT / "oa_netlist/input.scs").read_text()
    saved = [n for n in save_names() if not only_new or "OLD" not in n]
    variants = (("NEW", "Mmain"),) if only_new else (("OLD", "MN11"), ("NEW", "Mmain"))
    jobs = []
    for vd in inputs:
        params = f"parameters vinp_target={0.45 + vd / 2:.9g} vinn_target={0.45 - vd / 2:.9g}"
        deck, count = re.subn(r"(?m)^parameters vinp_target vinn_target\s*$", params, source)
        assert count == 1, "Expected exact OA design-variable declaration"
        if tag == "matched_reset":
            deck, _ = matched_reset(deck, vd)
        for old, new in (("reltol=1e-4", f"reltol={reltol}"), ("vabstol=1e-6", "vabstol=1e-7"),
                         ("iabstol=1e-12", "iabstol=1e-13"), ("save=allpub", "save=selected")):
            assert deck.count(old) == 1
            deck = deck.replace(old, new, 1)
        deck += f"\ntran tran stop=285n maxstep={maxstep} errpreset=conservative\n"
        if only_new:
            deck = remove_old_branch(deck)
            deck += "// Candidate-only warning diagnostic; old top-level branch omitted.\n"
        deck += "save " + " ".join(saved) + "\n"
        deck += "save " + " ".join(f"X{v}_{s}.{dev}:currents" for v, dev in variants for s in ("P", "N")) + "\n"
        name = f"{tag}_vd{'m' if vd < 0 else 'p'}{abs(round(vd * 1000)):03d}"
        path = OUT / "decks" / (name + ".scs")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(deck, encoding="utf-8")
        jobs.append((path, {}))
    sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "spectre", timeout=600,
                                    spectre_args=spectre_mode_args("spectre"))
    with (OUT / (tag + "_runner.log")).open("a", encoding="utf-8") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            results = sim.run_parallel(jobs, max_workers=3)
    for vd, (deck, _), result in zip(inputs, jobs, results):
        row = {"vdiff_v":vd, "tag":tag, "ok":result.ok, "errors":result.errors,
               "metadata":result.metadata, "candidate_only_diagnostic":only_new,
               "oa_sha256":hashlib.sha256(source.encode()).hexdigest(),
               "deck_sha256":hashlib.sha256(deck.read_bytes()).hexdigest()}
        if result.ok:
            time = signal(result.data, "time")
            waves = {n:signal(result.data, n) for n in saved}
            waves.update({f"X{v}_{s}.{dev}:1":signal(result.data, f"X{v}_{s}.{dev}:1")
                          for v, dev in variants for s in ("P", "N")})
            dump(deck.stem + "_waveform.json", {"time":time, **waves})
            at = lambda n, ns: interpolate(time, waves[n], ns * 1e-9)
            for v, _ in variants:
                delta = lambda ns: at(f"TOPP_{v}", ns) - at(f"TOPN_{v}", ns)
                row[v] = {"acquisition_error_mv":1000 * (delta(249.9) - vd),
                          "held_error_mv":1000 * (delta(270) - vd),
                          "hold_drift_260_280_mv":1000 * (delta(280) - delta(260))}
        dump(deck.stem + "_result.json", row)
        print("RESULT", deck.stem, json.dumps({k:v for k,v in row.items() if k != "metadata"}), flush=True)
        if not result.ok:
            raise RuntimeError(f"Spectre failed: {deck.stem}: {result.errors}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "create", "verify", "monitors", "run", "tight", "candidate-only", "matched-reset", "final"))
    parser.add_argument("--vdiff", type=float, nargs="+", choices=INPUTS, default=INPUTS)
    args = parser.parse_args()
    os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
    if args.action in ("run", "tight", "candidate-only", "matched-reset"):
        tag = {"run":"nominal", "tight":"tight", "candidate-only":"candidate_only", "matched-reset":"matched_reset"}[args.action]
        run(args.vdiff, tag, "5p" if args.action == "tight" else "10p",
            "2e-6" if args.action == "tight" else "1e-5", args.action == "candidate-only")
    else:
        client = VirtuosoClient.from_env(profile="t28_io")
        {"inspect":inspect, "create":create, "verify":verify_export, "monitors":add_monitors, "final":final_check}[args.action](client)


if __name__ == "__main__":
    main()
