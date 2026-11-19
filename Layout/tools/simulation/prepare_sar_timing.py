"""Bind an extracted SAR macro and its LVS reference to the integrated ADC testbench."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from Layout.design.sar_timing import CORE, active_sources, electrical, released_sources
from Layout.project import ROOT
from Layout.tools.analysis.sar_timing_probes import probes
from tools.saradc.reference_short import prepare as base_recipe
from tools.saradc.quiet_delay import REFERENCE as STD_DELAY_REFERENCE, source_for_stages


QUIET_VARIANT = re.compile(r"design/xtor/clock/delays_std_q([569])(?:_del(200))?(?:_s(075|200))?\.scs")


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def bind_extracted_macro(source, terminals, master):
    for name in ("XCTRL", "XSEQ", "XIDLE", "XSAMPLE"):
        source, count = re.subn(r"(?m)^[ \t]*" + name + r"[ \t]*\([^\n]+\)[ \t]+\w+[ \t]*$", "", source)
        if count != 1:
            raise ValueError("Unexpected instance " + name)
    actual = " ".join(terminals)
    call = "    XSAR_PHY (" + actual + ") " + master
    source, count = re.subn(r"(?m)^ends sar_adc8_join_r4[ \t]*$", call + "\nends sar_adc8_join_r4", source)
    calls = re.findall(r"(?m)^\s*XSAR_PHY\s+\(([^)\n]*)\)\s+(\w+)\s*$", source)
    if count != 1 or calls != [(actual, master)]:
        raise ValueError("Generated ADC does not instantiate the verified extracted master exactly once")
    return source


def quiet_eco(source, length):
    """Change the two quiet-delay resistor lengths while preserving all other source bytes."""
    if not re.fullmatch(r"\d+(?:\.\d+)?u", length):
        raise ValueError("Expected a resistor length in micrometres")
    pattern = rb"(?ms)^subckt sar8p_delay_quiet\b.*?^ends sar8p_delay_quiet\b"
    (section,) = re.finditer(pattern, source)
    body, count = re.subn(
        rb"(?m)^(R[01] [^\r\n]+? rupolym l=)[^ ]+( w=1u )",
        lambda m: m[1] + length.encode("ascii") + m[2],
        section[0],
    )
    if count != 2:
        raise ValueError("The quiet-delay electrical reference has changed")
    return source[: section.start()] + body + source[section.end() :]


def prepare(xrc, seed, run_id, corner, core=None, quiet_length=None, *, standard_delays=None, long_run=False,
            quiet_stages=None, external_cell_rc=None, quiet_final_ps=None, sample_delay_ps=None):
    manifest = json.loads((xrc / "manifest.json").read_text(encoding="utf-8"))
    assert not manifest.get("error") and manifest["checks"]["lvs"]["verdict"] == "CORRECT"
    saved = json.loads((seed / "sar-physical.json").read_text(encoding="utf-8"))
    assert saved["gds_sha256"] == manifest["gds"]["sha256"]
    extracted_master = manifest["top"]
    if extracted_master not in (CORE, "sar8_sar_timing") or extracted_master != saved["cell"]:
        raise ValueError("Unexpected SAR macro or wrapper")
    probe_source = seed
    if extracted_master != CORE:
        if core is None:
            raise ValueError("The filled wrapper requires its functional core readback")
        child = json.loads((core / "sar-physical.json").read_text(encoding="utf-8"))
        if child["cell"] != CORE or child["geometry_sha256"] != manifest["gds"]["structural_sha256"][CORE]:
            raise ValueError("The core instance in the extracted wrapper differs from the supplied core")
        probe_source = core
    reference = xrc / "reference.cdl"
    recorded = {}
    if reference.is_file() and not quiet_length:
        if sha(reference.read_bytes()) != manifest["reference_sha256"]:
            raise ValueError("LVS reference digest differs from the native receipt")
        recorded = dict(
            re.findall(
                r"(?m)^\* (design/\S+) SHA256 ([a-f0-9]{64})$",
                reference.read_text(encoding="ascii", errors="replace"),
            )
        )
    source_stages = quiet_stages
    if standard_delays is None:
        standard_delays = quiet_stages is not None or any(
            path == "design/" + STD_DELAY_REFERENCE or QUIET_VARIANT.fullmatch(path) for path in recorded
        )
    if quiet_length is not None and standard_delays:
        raise ValueError("A resistor length applies only to the RC macro")
    if (quiet_stages is not None or quiet_final_ps is not None or sample_delay_ps is not None) and not standard_delays:
        raise ValueError("DEL candidates apply to the standard-cell macro")
    if standard_delays:
        delay_names = list(recorded) if recorded else ["design/" + key for key in active_sources()]
        variants = [m for file in delay_names if (m := QUIET_VARIANT.fullmatch(file))]
        if len(variants)>1:
            raise ValueError("Ambiguous delay sources in the frozen electrical reference")
        if variants:
            if quiet_stages is None:
                quiet_stages = source_stages = int(variants[0][1])
            if quiet_final_ps is None:
                quiet_final_ps = int(variants[0][2] or 250)
            if sample_delay_ps is None and variants[0][3]:
                sample_delay_ps = int(variants[0][3])
        elif quiet_stages is None:
            source_stages = 9
    quiet_final_ps = 250 if quiet_final_ps is None else quiet_final_ps
    timing = dict(quiet_stages=source_stages, quiet_final_ps=quiet_final_ps, sample_delay_ps=sample_delay_ps)
    devices, ports, source_inputs = electrical(standard_delays=standard_delays, static_latch=standard_delays, **timing)
    if reference.is_file() and not quiet_length and recorded != source_inputs:
        raise ValueError("LVS reference is bound to a different electrical design")
    expected = json.loads((ROOT / "tb/top/short/context.json").read_text(encoding="utf-8"))[
        "expected_codes"
    ]
    sources = active_sources(static_latch=True, **timing) if standard_delays else released_sources()
    if long_run and not standard_delays:
        raise ValueError("Select the standard-delay campaign for the continuous regression")
    if standard_delays:
        campaign = json.loads((ROOT/"results/design/sar_std_delay_20261119.json").read_text())
        vectors = campaign["long_run"] if long_run else campaign["pvt"][corner]
        common = {k:v for k,v in campaign["source_sha256"].items() if k not in
                  ("dut.scs", "xtor/sar/reset_data_or_std_delay.scs")}
        if quiet_stages is not None:
            baseline = (ROOT/"design"/STD_DELAY_REFERENCE).read_bytes()
            if sha(baseline) != common.pop(STD_DELAY_REFERENCE):
                raise ValueError("The standard delay calibration reference changed")
            selected_name, selected_blob = source_for_stages(baseline, quiet_stages, quiet_final_ps,
                                                             sample_delay_ps=sample_delay_ps)
            if sources[selected_name] != selected_blob:
                raise ValueError("QUIET chain differs from the selected electrical ECO")
        if vectors["corner"] != corner or any(sha(sources[k]) != v for k,v in common.items()):
            raise ValueError("Analog circuits, standard delays or corner differ from the comparison campaign")
        expected = vectors["expected_codes"]
    revision = "sar-layout-" + sha(json.dumps(source_inputs, sort_keys=True).encode())[:12] + ("-long" if long_run else "")
    cell_library = None
    if quiet_stages is not None:
        cell_rc = external_cell_rc or manifest.get("interconnect_rc", {}).get("corner", "typical")
        if cell_rc not in ("typical", "cworst_T", "cbest_T"):
            raise ValueError("No installed external-cell LPE wrapper for " + cell_rc)
        cell_library = (ROOT/"tb/common/platform"/("library_lpe_" + cell_rc.lower() + ".scs")).read_bytes()
        revision += "-lpe"
        if cell_rc != "typical":
            revision += "-" + cell_rc.lower().replace("_", "-")
    elif external_cell_rc is not None:
        raise ValueError("External-cell RC selection requires the LPE-calibrated standard-delay design")
    original_path = ROOT / base_recipe("current", corner, revision, codes=expected,
                                        max_output_mib=8192 if standard_delays else 2400, source_blobs=sources,
                                        cell_library=cell_library)
    recipe = json.loads(original_path.read_text(encoding="utf-8"))
    blobs = {row["name"]: (ROOT / row["source"]).read_bytes() for row in recipe["inputs"]}
    if quiet_length:
        name = "xtor/clock/delays_quiet8p5.scs"
        blobs[name] = quiet_eco(blobs[name], quiet_length)
        source_inputs["design/" + name] = sha(blobs[name])
    outputs = manifest["checks"]["pex"]
    netlists = xrc if (xrc / "extracted.scs").is_file() else xrc / "pex"
    for name, digest in {"extracted.scs": outputs["sha256"], **outputs["companion_sha256"]}.items():
        blob = (netlists / name).read_bytes()
        if sha(blob) != digest:
            raise ValueError("Extraction digest differs: " + name)
        blobs[name] = blob
    coordinates = xrc / "layout.sp"
    if not coordinates.is_file():
        coordinates = xrc / "lvs/svdb" / (extracted_master + ".sp")
    rail_counts = outputs.get("distributed_rail_resistors")
    has_rails = rail_counts is not None
    if has_rails and (set(rail_counts) != {"VDD", "VSS"} or min(rail_counts.values()) <= 0):
        raise ValueError("Distributed supply qualification requires both extracted resistor networks")
    measurement = probes(netlists / "extracted.scs", coordinates, probe_source / "sar-readback.txt", has_rails,
                         register_data=quiet_stages is not None)
    # Additional testbench ports expose existing distributed gate nodes. No devices or wires
    # are added to the extracted circuit, and the stored extraction is left byte-identical.
    text = blobs["extracted.scs"].decode()
    dimensions = re.findall(r"\)\s+rupolym\s+l=([\d.eE+\-]+)\s+w=([\d.eE+\-]+)", text.replace("\\\n", " "))
    measured = sorted(
        (round(float(length) * 1e6, 5), round(float(width) * 1e6, 5)) for length, width in dimensions
    )
    expected_dimensions = []
    for path, device in devices.items():
        if device.master == "rupolym":
            length = device.parameters["l"]
            if quiet_length and path in ("XCTRL/XTIM/XD_QUIET_D/R0", "XCTRL/XTIM/XD_QUIET_D/R1"):
                length = quiet_length
            expected_dimensions.append(
                (float(length.removesuffix("u")), float(device.parameters["w"].removesuffix("u")))
            )
    if measured != sorted(expected_dimensions):
        raise ValueError("Extracted resistor dimensions differ from the selected electrical reference")
    m = re.search(r"(?im)^(subckt\s+" + re.escape(extracted_master) + r"\s*\()([^)]*)(\))", text)
    actual = re.sub(r"\\\s*\n", " ", m[2]).split()
    if set(actual) != set(ports) or len(actual) != len(ports):
        raise ValueError("Extracted port set differs from the active four-block interface")
    internal = [r["pex_node"] for r in measurement.values()]
    assert len(set(internal)) == len(internal)
    blobs["extracted.scs"] = (
        text[: m.start(3)] + " " + " ".join(internal) + " " + text[m.start(3) :]
    ).encode()
    physical = ["VDD!" if n == "VDD" else "0" if n == "VSS" else n for n in actual]
    blobs["top/adc_top.scs"] = bind_extracted_macro(
        blobs["top/adc_top.scs"].decode(), physical + list(measurement), extracted_master
    ).encode()
    blobs["dut.scs"] += b'\ninclude "extracted.scs"\n'
    deck = blobs["test.scs"].decode()
    if standard_delays:
        deck,count = re.subn(r"(?m)^(tran_short tran .*)$",r"\1 strobeperiod=5p strobeoutput=strobeonly",deck)
        if count != 1:
            raise ValueError("Missing transient analysis")
    for old, new in {
        "XCTRL.PHI_W": "SAR_PHI_W",
        "XCTRL.XTIM.PR": "SAR_PR",
        "XCTRL.XTIM.NR": "SAR_NR",
    }.items():
        deck = deck.replace("XDUT." + old, "XDUT." + new)
    deck += "\nsave " + " ".join("XDUT.WRITE_AT_D" + str(i) for i in range(8)) + "\n"
    rail_aliases = [alias for alias in measurement if alias.startswith(("VDD_AT_", "VSS_AT_"))]
    if standard_delays:
        deck += "save XDUT.LATCH_Q XDUT.LATCH_QB\n"
    if quiet_stages is not None:
        deck += "save " + " ".join("XDUT." + family + str(i) for family in ("DATA_AT_D", "CDN_AT_D") for i in range(8)) + "\n"
        deck += "save XDUT.IDLE_GUARD XDUT.QUIET_REQ XDUT.QUIET_DONE\n"
    if rail_aliases:
        deck += "save " + " ".join("XDUT." + alias for alias in rail_aliases) + "\n"
    blobs["test.scs"] = deck.encode()
    blobs["measure_sar_timing.py"] = (ROOT / "Layout/tools/simulation/measure_sar_timing.py").read_bytes()
    if quiet_stages is not None:
        blobs["measure_register_windows.py"] = (ROOT/"Layout/tools/simulation/measure_register_windows.py").read_bytes()
    ctx = json.loads(blobs["context.json"])
    ctx.update(
        run_id=run_id,
        pex=True,
        physical_id=manifest["id"],
        gds_sha256=manifest["gds"]["sha256"],
        electrical_inputs=source_inputs,
        extracted_receiver_map=measurement,
        qualification_scope="SAR-only coupled xRC with the current transistor-level ADC. Eight physical bit-clock taps; other functional blocks schematic.",
    )
    ctx["required_signals"] += ["xdut.write_at_d" + str(i) for i in range(8)]
    if quiet_stages is not None:
        ctx["required_signals"] += ["xdut." + family + str(i) for family in ("data_at_d", "cdn_at_d") for i in range(8)]
        ctx["required_signals"] += ["xdut.idle_guard", "xdut.quiet_req", "xdut.quiet_done"]
        ctx.update(quiet_stages=quiet_stages, standard_cell_parasitics="flat xRC inside SAR, lpe_" + cell_rc + " elsewhere",
                   signal_mom_on_qb=False, register_receivers=[
                       dict(d="xdut.data_at_d"+str(i), cp="xdut.write_at_d"+str(i),
                            cdn="xdut.cdn_at_d"+str(i)) for i in range(8)],
                   phase_observers={k:"xdut."+k for k in ("sample_int","seq_sample","active","preset")})
        ctx["phase_observers"].update(idle_d="xdut.idle_guard", quiet="xdut.quiet_req", quiet_d="xdut.quiet_done")
        if quiet_final_ps != 250:
            ctx["quiet_last_cell"] = "DEL%dD1BWP12T30P140" % quiet_final_ps
        if sample_delay_ps is not None:
            ctx["sample_delay_ps"] = sample_delay_ps
        if cell_rc != "typical" and "interconnect_rc" in manifest:
            ctx["interconnect_rc"] = manifest["interconnect_rc"]
    if rail_aliases:
        ctx["supply_probe_sites"] = sorted(alias[7:] for alias in rail_aliases if alias.startswith("VDD_AT_"))
        ctx["required_signals"] += ["xdut." + alias.lower() for alias in rail_aliases]
    if quiet_length:
        ctx["physical_eco"] = dict(
            instances=["XCTRL/XTIM/XD_QUIET_D/R0", "XCTRL/XTIM/XD_QUIET_D/R1"],
            length=quiet_length,
            width="1u",
            lvs_reference_sha256=manifest["reference_sha256"],
        )
    ctx["source_hashes"] = {n: sha(b) for n, b in blobs.items() if n != "context.json"}
    blobs["context.json"] = (json.dumps(ctx, indent=2) + "\n").encode()
    dest = ROOT / "work/layout" / run_id
    dest.mkdir(exist_ok=True)
    for name, blob in blobs.items():
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != blob:
            raise ValueError("Prepared identity differs at " + name)
        target.write_bytes(blob)
    recipe.update(
        run_id=run_id,
        design_id=extracted_master,
        analyzer="measure_register_windows.py" if quiet_stages is not None else "measure_sar_timing.py",
        test_conditions=ctx,
        qualification_scope=ctx["qualification_scope"],
        inputs=[
            dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b))
            for n, b in blobs.items()
        ],
    )
    recipe["resources"]["simulation_rss_mib"] = 2800
    if standard_delays:
        recipe["spectre_args"][recipe["spectre_args"].index("+lqtimeout")+1] = "900"
        recipe["resources"].update(simulation_wall_seconds=21600, analysis_wall_seconds=10800)
    if quiet_stages is not None and long_run:
        recipe["resources"].update(simulation_wall_seconds=86400, analysis_wall_seconds=21600, max_output_mib=24576)
    path = dest / "recipe.json"
    path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("extraction", type=Path)
    ap.add_argument("native", type=Path)
    ap.add_argument("run_id")
    ap.add_argument("--corner", choices=("tt", "ssc", "ssh", "ffc", "ffh"), default="tt")
    ap.add_argument(
        "--core", type=Path, help="Matching native functional core when the extraction is a filled wrapper"
    )
    ap.add_argument("--quiet-length", help="Bind a pre-adoption resistor ECO to its matching LVS source")
    ap.add_argument("--standard-delays", action="store_true", default=None,
                    help="Use standard delays explicitly for checkpoints without a recorded LVS source")
    ap.add_argument("--long", action="store_true", help="Use the original continuous 64-frame vector sequence at its recorded corner")
    ap.add_argument("--quiet-stages",type=int,choices=(5,6,9),help="Bind the specified LPE calibration candidate")
    ap.add_argument("--quiet-final-ps",type=int,choices=(200,250),help="Check the final QUIET cell against the frozen LVS reference")
    ap.add_argument("--sample-delay-ps",type=int,choices=(75,200),help="Check the qualified sample tap against the frozen LVS reference")
    ap.add_argument("--external-cell-rc",choices=("typical","cworst_T","cbest_T"),
                    help="Override the RC model of cells outside the extracted SAR for a controlled comparison")
    a = ap.parse_args()
    print(prepare(a.extraction, a.native, a.run_id, a.corner, a.core, a.quiet_length,
                  standard_delays=a.standard_delays,long_run=a.long,quiet_stages=a.quiet_stages,external_cell_rc=a.external_cell_rc,
                  quiet_final_ps=a.quiet_final_ps,sample_delay_ps=a.sample_delay_ps))
