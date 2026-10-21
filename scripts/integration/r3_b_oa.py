"""Bounded adoption of the already verified reference-gate B into Virtuoso."""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
from pathlib import Path
import pickle
import re

import join_r3 as r3
from freeze_r0 import object_digest, schematic_surface, number_or_expression as num

ROOT = r3.ROOT
OUT = ROOT / "output/r3_b_oa"
LIB, TOP, TB = r3.LIB, r3.TOP, r3.TB
OLD = r3.GATE
NEW = "sar8j_aligned_refgate_b"
SOURCE = ROOT / "models/veriloga/r3_refgate_events/b3/sar8j_aligned_refgate.va"
VA = ROOT / "models/veriloga/sar8_join_b/sar8j_aligned_refgate_b.va"


def dump(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def cdf(c, cell):
    return c.fetch(f'cdfGetBaseCellCDF(ddGetObj("{LIB}" "{cell}"))~>parameters',
                   ["name", "type", "defValue", "value", "callback"])


def normalized(data, new=False):
    data = json.loads(json.dumps(data))
    data["instances"].sort(key=lambda p: p["name"])
    for p in data["instances"]:
        if new and re.fullmatch(r"XG[PN][0-7]", p["name"]):
            assert p["cell"] == NEW
            p["cell"] = OLD
    for v in data["nets"].values():
        v["connections"].sort()
    return data


def inspect(c):
    assert not (OUT / "before.json").exists(), "Preflight is immutable"
    info = c.library.get(LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert info.technology_library == "tsmcN28"
    windows = c.list_windows()
    assert not any(any(f"{LIB} {n} " in w["name"] for n in (TOP, TB, OLD, NEW))
                   for w in windows), "Target GUI-open; inspect ownership first"
    assert not r3.r1.exists(c, NEW), "Unowned B cell already exists"
    manifest = r3.r1.read_json(ROOT / "verification/integration/join_r3_results.json")
    for name, expected in manifest["OA_surface_sha256"].items():
        data = c.schematic.read(LIB, name, include_positions=True, param_filters=None)
        assert object_digest(schematic_surface(data)) == expected, name
        dump(f"before/{name}.json", data)
    hashes = r3.r1.read_json(ROOT / "verification/integration/join_r0_sources.json")
    native = {n: v["surface_sha256"] for n, v in hashes["live_readback"]["cells"].items()}
    for filename in ("join_r1_results.json", "join_r2_results.json"):
        obj = r3.r1.read_json(ROOT / f"verification/integration/{filename}")
        native.update(obj.get("new_OA_schematic_surface_sha256", obj.get("OA_surface_sha256", {})))
    for name, expected in native.items():
        data = c.schematic.read(LIB, name, include_positions=False, param_filters=None)
        assert object_digest(schematic_surface(data)) == expected, name
    dump("dependencies.json", native)
    dump("old_cdf.json", cdf(c, OLD))
    dump("old_symbol.json", c.symbol.read_ports(LIB, OLD))
    remote = f"{info.path}/{OLD}/veriloga/veriloga.va"
    target = OUT / "old_remote.va"
    target.parent.mkdir(parents=True, exist_ok=True)
    result = c.download_file(remote, target)
    assert result.ok, result.errors
    assert r3.r1.sha(target) == manifest["exact_gate_VA_sha256"][OLD]
    locks = c.ssh_runner.run_command(
        f'find {info.path}/{TOP} {info.path}/{TB} {info.path}/{OLD} -name "*.cdslck*" -print')
    dump("lock_probe.json", dict(returncode=locks.returncode, stdout=locks.stdout, stderr=locks.stderr))
    assert locks.returncode == 0, locks.stderr
    # Historical symbols and the read-only TB are cached by the existing CIW.
    # Do not unlock or edit those dependencies. Only the writable top schematic
    # must be free; NEW was already required not to exist.
    assert not any(f"/{TOP}/schematic/" in line for line in locks.stdout.splitlines()), \
        "Writable target schematic is locked"
    dump("before.json", dict(library=dataclasses.asdict(info), windows=windows,
                              native_surfaces_checked=len(native), old_va_sha256=r3.r1.sha(target)))
    print("PREFLIGHT_OK", len(native), flush=True)


def export(c, tag):
    target = OUT / "exports" / tag
    assert not (target / "input.scs").exists(), "Use a fresh tag"
    result = c.schematic.export_netlist(LIB, TB, target, simulator="spectre", timeout=300)
    dump(f"exports/{tag}/receipt.json", result)
    assert Path(result["input_file"]).exists()
    print("EXPORTED", result["input_file"], flush=True)


def docs(c):
    # The bridge More Info downloader mishandles POSIX paths on Windows. Read
    # the exact installed HTML mapped by its downloaded official TGF index.
    from virtuoso_bridge.virtuoso.skill_finder.more_info import html_to_plain_text, extract_topic_from_html
    for name, filename in (("dbSetInstHeaderMasterName", "instance.html"),
                           ("dbCopyCellView", "cvio.html")):
        remote = "/home/cadence/ic618/IC618Hotfix4/doc/skdfref/" + filename
        result = c.ssh_runner.run_command("cat " + remote, timeout=30)
        assert result.returncode == 0, result.stderr
        section = extract_topic_from_html(result.stdout, name)
        assert section, name
        plain = html_to_plain_text(section)
        dump(f"api_docs/{name}.json", dict(path=remote, topic=name, plain_text=plain))
        print(plain, flush=True)


def adopt(c):
    assert (OUT / "before.json").exists() and (OUT / "exports/before/input.scs").exists()
    assert not r3.r1.exists(c, NEW), "Do not overwrite an existing B cell"
    assert VA.read_text() == SOURCE.read_text().replace(f"module {OLD}(", f"module {NEW}(", 1)
    assert normalized(c.schematic.read(LIB, TOP, include_positions=True, param_filters=None)) == \
        normalized(load(f"before/{TOP}.json")), "R3 changed after preflight"
    assert len(c.list_windows()) == 1, "Inspect newly opened windows before editing"
    # Exact symbol copy retains existing electrical pin locations and wire routes.
    r3.r1.skill(c, f'let((src dst) src=dbOpenCellViewByType("{LIB}" "{OLD}" "symbol" "" "r") '
                  f'dst=dbCopyCellView(src "{LIB}" "{NEW}" "symbol") '
                  'unless(dst error("B symbol copy failed")) dbSave(dst) dbClose(dst))')
    dump("owned.json", dict(cell=NEW, source_sha256=r3.r1.sha(SOURCE)))
    r3.r1.skill(c, f'schViewToView("{LIB}" "{NEW}" "{LIB}" "{NEW}" "symbol" "veriloga" '
                  '"schSymbolToPinList" "ahdlPinListToveriloga")')
    remote = f'/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{NEW}/veriloga/veriloga.va'
    result = c.upload_file(VA, remote)
    assert result.ok, result.errors
    r3.r1.skill(c, f'ahdlUpdateViewInfo("{LIB}" ?cell "{NEW}" ?view "veriloga")')
    # Preserve the old exposed timing CDF defaults; instance overrides stay untouched.
    for p in load("old_cdf.json"):
        assert p["name"] in ("initial_high", "restore_guard_s", "edge_s") and not p["callback"], p
        name, default = p["name"], p["defValue"]
        r3.r1.skill(c, f'let((d) d=cdfGetBaseCellCDF(ddGetObj("{LIB}" "{NEW}")) '
                      f'unless(d d=cdfCreateBaseCellCDF(ddGetObj("{LIB}" "{NEW}"))) '
                      f'unless(cdfFindParamByName(d "{name}") cdfCreateParam(d ?name "{name}" '
                      f'?prompt "{name}" ?type "string" ?defValue "{default}" '
                      '?parseAsNumber "yes" ?parseAsCEL "yes")) cdfSaveCDF(d))')
    assert c.symbol.read_ports(LIB, NEW) == load("old_symbol.json"), "Symbol ports moved"
    assert cdf(c, NEW) == load("old_cdf.json"), "CDF changed"
    before = load(f"before/{TOP}.json")
    gates = [p for p in before["instances"] if p["cell"] == OLD]
    assert {p["name"] for p in gates} == {f"XG{s}{b}" for s in "PN" for b in range(8)}
    with c.schematic.modify(LIB, TOP, timeout=90) as sch:
        sch.add('let((is h) is=setof(i cv~>instances i~>cellName=="' + OLD + '") '
                'unless(length(is)==16 error("Expected 16 old gates")) '
                'h=car(is)~>instHeader '
                f'unless(dbSetInstHeaderMasterName(h "{LIB}" "{NEW}" "symbol") '
                'error("Gate master binding failed")))')
    print("B_BOUND_TO_R3", flush=True)


def validate(c):
    after = c.schematic.read(LIB, TOP, include_positions=True, param_filters=None)
    dump(f"after/{TOP}.json", after)
    assert normalized(after, new=True) == normalized(load(f"before/{TOP}.json"))
    tb = c.schematic.read(LIB, TB, include_positions=True, param_filters=None)
    assert normalized(tb) == normalized(load(f"before/{TB}.json"))
    for name, expected in load("dependencies.json").items():
        data = c.schematic.read(LIB, name, include_positions=False, param_filters=None)
        assert object_digest(schematic_surface(data)) == expected, name
    old_path = OUT / "old_after.va"
    new_path = OUT / "b_remote.va"
    base = "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    for cell, path in ((OLD, old_path), (NEW, new_path)):
        result = c.download_file(f"{base}/{cell}/veriloga/veriloga.va", path)
        assert result.ok, result.errors
    assert r3.r1.sha(old_path) == load("before.json")["old_va_sha256"]
    assert r3.r1.sha(new_path) == r3.r1.sha(VA)
    a = (OUT / "exports/before/input.scs").read_text()
    b = (OUT / "exports/after/input.scs").read_text()
    ab, bb = r3.r1.blocks(a), r3.r1.blocks(b.replace(NEW, OLD))
    assert set(ab) == set(bb)
    assert all(ab[n] == bb[n] for n in ab if n != TOP), "Native subcircuit differs"
    assert r3.old.canonical_top(ab[TOP]) == r3.old.canonical_top(bb[TOP]), \
        "Top-level electrical statements differ"
    def electrical(text):
        # Changing an instance header reorders its instances in the exporter.
        # Compare the top separately by named statement, not serialization order.
        text = re.sub(rf"(?ms)^subckt {TOP} .*?^ends {TOP}", "TOP_CHECKED_SEPARATELY", text)
        text = re.sub(r"(?m)^ahdl_include .*\n?", "", text)
        return " ".join(line.split("//", 1)[0].strip() for line in text.splitlines()
                        if line.split("//", 1)[0].strip())
    assert electrical(a) == electrical(b.replace(NEW, OLD)), "Testbench/options changed"
    gates = [p for p in after["instances"] if p["cell"] == NEW]
    for p in gates:
        assert num(p["params"]["restore_guard_s"]) == num("100p")
        assert num(p["params"]["edge_s"]) == num("50p")
    marks = c.fetch(f'dbOpenCellViewByType("{LIB}" "{TOP}" "schematic" "" "r")~>markers',
                    ["objType", "severity", "bBox"])
    assert not marks, marks
    dump("validation.json", dict(top=TOP, testbench=TB, versioned_gate=NEW,
        only_16_ideal_gate_master_bindings_changed=True, exact_other_OA_fields_preserved=True,
        all_native_netlist_subcircuits_identical=True, native_dependencies_unchanged=True,
        top_electrical_statements_equal_ignoring_serialization_order=True,
        top_serialization_order_changed=ab[TOP] != bb[TOP],
        original_shared_gate_unchanged=True, symbol_pins_and_CDF_equal=True,
        testbench_sources_and_simulator_options_unchanged=True,
        markers=marks, before_netlist_sha256=r3.r1.sha(OUT / "exports/before/input.scs"),
        after_netlist_sha256=r3.r1.sha(OUT / "exports/after/input.scs"),
        verified_B_source_sha256=r3.r1.sha(SOURCE), adopted_VA_sha256=r3.r1.sha(VA),
        new_full_campaign_launched=False))
    print("OA_AND_NATIVE_NETLIST_IDENTITY_PASS", flush=True)


def smoke(c):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    assert load("validation.json")["all_native_netlist_subcircuits_identical"]
    original = ROOT / "output/r3_refgate_events/unit_b3"
    text = (original / "decks/unit_b3.scs").read_text()
    text = text.replace(OLD, NEW).replace(f'ahdl_include "{NEW}.va"',
                                         'ahdl_include "b_remote.va"')
    deck = OUT / "unit_import.scs"
    assert not deck.exists(), "Immutable import smoke"
    deck.write_text(text, encoding="utf-8")
    va = OUT / "b_remote.va"
    assert r3.r1.sha(va) == r3.r1.sha(VA)
    with (OUT / "unit_runner.log").open("w", encoding="utf-8") as log, \
            contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "spectre",
            timeout=600, spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "60"])
        result = sim.run_simulation(deck, dict(include_files=[str(va)], spectre_args=["+mt=4"]))
    dump("unit_result.json", dict(ok=result.ok, errors=result.errors,
        warnings=result.warnings, metadata=result.metadata, deck_sha256=r3.r1.sha(deck)))
    assert result.ok, result.errors
    old_receipt = json.loads((original / "waveform_receipt.json").read_text())
    assert r3.r1.sha(original / "waveform.pickle") == old_receipt["sha256"]
    with (original / "waveform.pickle").open("rb") as stream:
        previous = pickle.load(stream)
    current = {str(k).strip('"').replace("\\", "").lower(): v for k, v in result.data.items()
               if isinstance(v, list) and str(k).lower() != "units"}
    assert current == previous, "Imported model unit waveform differs from verified b3"
    dump("unit_validation.json", dict(result_ok=True,
        all_saved_waveforms_and_timepoints_exactly_equal_verified_B=True,
        points=len(current["time"]), signals=len(current)-1,
        midpoint_samples=96, conversion_request_samples=96,
        reference_waveform_sha256=old_receipt["sha256"],
        precision_same_as_verified_unit=True, full_ADC_simulation=False,
        timings=result.metadata.get("timings", {})))
    print("IMPORTED_B_NATIVE_UNIT_EXACT_MATCH", flush=True)


def curate(c):
    del c
    report = dict(baseline="R3_with_verified_B_reference_events",
        library=LIB, top=TOP, testbench=TB, qualified=False,
        source_fix_commit="39a2ee2", adoption=load("validation.json"),
        import_unit=load("unit_validation.json"),
        import_unit_warnings=load("unit_result.json")["warnings"],
        source_text_LF_sha256={str(p.relative_to(ROOT)).replace("\\", "/"):
            hashlib.sha256(p.read_text().encode("utf-8")).hexdigest() for p in (SOURCE, VA)},
        unchanged_next_ADC_run_precision=dict(simulator="Spectre21.1_APS", threads=4,
            maxstep_ps=10, errpreset="conservative", reltol_requested=1e-5,
            reltol_previously_reported_effective=1e-6, vabstol=1e-8, iabstol=1e-13,
            method="gear2only", corner="tt", supply_v=.9, temperature_c=27,
            transient_noise=False, mismatch=False),
        current_OA_12_frame_replay_performed=False,
        full_static_or_dynamic_restarted=False,
        limits="Imported unit exactly matches verified B; current OA top has not been rerun for full ADC performance. "
               "Gate serialization order changed during master binding; replay the original history first.")
    path = ROOT / "verification/integration/r3_b_oa_results.json"
    assert not path.exists(), "Curated receipt is immutable"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("CURATED", path, flush=True)


def check(c):
    del c
    receipt = json.loads((ROOT / "verification/integration/r3_b_oa_results.json").read_text())
    assert VA.read_text() == SOURCE.read_text().replace(f"module {OLD}(", f"module {NEW}(", 1)
    for path, expected in receipt["source_text_LF_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_text().encode("utf-8")).hexdigest() == expected
    assert receipt["adoption"] == load("validation.json")
    assert receipt["import_unit"] == load("unit_validation.json")
    assert receipt["import_unit"]["all_saved_waveforms_and_timepoints_exactly_equal_verified_B"]
    assert not receipt["current_OA_12_frame_replay_performed"]
    print("LOCAL_SOURCE_AND_RECEIPT_CHECK_PASS", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["warm", "inspect", "docs", "adopt", "export", "validate", "smoke", "curate", "check"])
    parser.add_argument("--tag", default="before")
    args = parser.parse_args()
    if args.action == "warm":
        from virtuoso_bridge.transport.tunnel import SSHClient

        ssh = SSHClient.from_env(keep_remote_files=True, profile="t28_io")
        try:
            ssh.warm(timeout=20)
            print("TUNNEL_WARMED", flush=True)
        finally:
            ssh.close()
        return
    if args.action in ("check", "curate"):
        globals()[args.action](None)
        return
    from virtuoso_bridge import VirtuosoClient
    c = VirtuosoClient.from_env(profile="t28_io", timeout=30, log_to_ciw=False)
    if args.action == "export":
        export(c, args.tag)
    else:
        globals()[args.action](c)


if __name__ == "__main__":
    main()
