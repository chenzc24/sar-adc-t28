"""Bind the native driver/CDAC extraction to focused and full ADC fixtures."""

import argparse
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass

from Layout.design.cdac import PORTS as CDAC_PORTS
from Layout.design.reference_driver import CDAC, COMBINED, DRIVER_SOURCE
from tools.saradc import refsel
from tools.saradc.schematic import electrical_statements
from Layout.project import ROOT, evidence
from Layout.tools.simulation.prepare_full_sim import pull, sha
from tools.saradc import views
from tools.saradc.single_edge_lpe import CELL_RC
from tools.saradc.reference_short import prepare as reference_short


CDAC_CONTROL = "cdac-paired-plan-d-20261118"
LSB = 1.8 / 256
PLATFORM = ROOT / "tb/top/short/test.scs"
LICENSE_WAIT_SECONDS = "600"


@dataclass(frozen=True)
class Contact:
    node: str
    x: float
    y: float


def fetch_pex(identity):
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,55}", identity):
        raise ValueError("Invalid physical evidence identity")
    cache = ROOT / "work/layout/reference-driver/pex" / identity
    remote_path = None

    def read_native(name, digest=None):
        nonlocal remote_path
        path = cache / name
        if path.is_file():
            data = path.read_bytes()
            if (digest is not None and sha(data) == digest) or (
                name == "manifest.json" and json.loads(data).get("checks", {}).get("pex")
            ):
                return data
        for attempt in range(3):
            try:
                if remote_path is None:
                    remote_path = evidence(identity)
                data = pull(remote_path + "/" + name)
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        if digest is not None and sha(data) != digest:
            raise ValueError(f"Extracted netlist changed for {identity}: {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + f".{os.getpid()}.tmp")
        temp.write_bytes(data)
        temp.replace(path)
        return data

    manifest_blob = read_native("manifest.json")
    manifest = json.loads(manifest_blob)
    if (manifest.get("error") or manifest["checks"].get("lvs", {}).get("verdict") != "CORRECT"
        or not manifest["checks"].get("pex")):
        raise ValueError(f"Physical LVS and PEX are required for {identity}")
    if manifest.get("case") == "reference-driver":
        intent = json.loads(read_native("intent.json", manifest["input_hashes"]["intent.json"]))
        source = (ROOT / DRIVER_SOURCE).read_bytes()
        physical_source = json.loads((ROOT / 'Layout/results/single_edge_xref.json').read_text())['source']
        binding = json.loads((ROOT / 'Layout/specs/interfaces.json').read_text())['masters']['sar8i_refword']
        electrical_sha = sha('\n'.join(electrical_statements(source.decode())).encode())
        equivalent = intent['source_sha256'] == physical_source and electrical_sha == binding['physical_equivalent_statement_sha256']
        if intent['source_sha256'] != {DRIVER_SOURCE: sha(source)} and not equivalent:
            raise ValueError(f"The XREF electrical source differs from {identity}")
        if manifest["top"] != COMBINED:
            raise ValueError("The transient fixture requires the integrated XREF/CDAC extraction")
    pex = manifest["checks"]["pex"]
    digests = {"extracted.scs": pex["sha256"], **pex["companion_sha256"]}
    payload = {}
    for name, digest in digests.items():
        if not re.fullmatch(r"extracted\.scs(?:\.[A-Za-z0-9_.-]+)?", name):
            raise ValueError(f"Invalid extracted companion: {name}")
        payload[name] = read_native("pex/" + name, digest)
    payload["physical.json"] = manifest_blob
    return payload, manifest


def pin_order(source, model, expected):
    netlist = join_lines(source)
    ports = re.search(r"(?mi)^subckt\s+" + model + r"\s*\(([^)]+)\)", netlist)[1].split()
    if sorted(ports) != sorted(expected):
        raise ValueError(f"Extracted interface changed on {model}")
    return ports


def join_lines(source):
    return re.sub(r"\\[ \t]*\r?\n[ \t]*", " ", source.decode("ascii"))


def contact_net(node, device):
    # Calibre RCNAMED files use N_<net>_<layout occurrence>_<terminal>.
    match = re.match(r"^N_(.+)_" + re.escape(device[1:]) + r"_\w+$", node, re.I)
    return match[1] if match else node


def several_contacts(items, every=False):
    if every:
        return [i.node for i in items]
    positions = ((min, "x"), (max, "x"), (max, "y"))
    return sorted({method(items, key=lambda p: getattr(p, axis)).node for method, axis in positions})


def analog_nodes(source, bits, every_plate=False, every_gate=False):
    """Find real switch gates and MOM terminals from geometry and unit counts."""
    mos = defaultdict(list)
    mom = defaultdict(list)
    pattern = r"(?im)^([xX]\S*)[ \t]+\(([^)]+)\)[ \t]+(nch_mac|pch_mac|cfmom_2t)\b([^\n]*)"
    coords = r"//x=([-+\d.e]+)[ \t]+//y=([-+\d.e]+)"
    for device, terminals, model, params in re.findall(pattern, join_lines(source)):
        terms = terminals.split()
        found = re.search(coords, params)
        if not found:
            raise ValueError(f"Missing location for {device}")
        x, y = map(float, found.groups())
        side = "n" if x < 34.4 else "p"
        if model == "cfmom_2t":
            for node in terms:
                mom[side, contact_net(node, device)].append(Contact(node, x, y))
            continue
        if abs(float(re.search(r"\bl=([\de.-]+)", params)[1]) - 90e-9) > 1e-11:
            continue
        drain, gate, src, _ = terms
        d, s = contact_net(drain, device), contact_net(src, device)
        ref = "VREFN" if model == "nch_mac" else "VREFP"
        if s == ref:
            bottom = d
        elif d == ref:
            bottom = s
        else:
            raise ValueError(f"Cannot identify the reference electrode of {device}")
        mos[side, model[0], contact_net(gate, device)].append((Contact(gate, x, y), bottom))

    gates = {}
    plates = {}
    for side in "np":
        for bit in bits:
            bottoms = set()
            for polarity in "np":
                candidates = [items for (s, p, _), items in mos.items()
                              if (s, p, len(items)) == (side, polarity, 3 * (1 << bit))]
                if len(candidates) != 1:
                    raise ValueError(f"Nonunique extracted switch group for {side}/{polarity} B{bit}")
                (items,) = candidates
                gates[f"g{side}{polarity}{bit}"] = several_contacts([p for p, _ in items], every_gate)
                bottoms.update(n for _, n in items)
            if len(bottoms) != 1:
                raise ValueError(f"Switches do not share one bottom plate on {side} B{bit}")
            contacts = mom[side, bottoms.pop()]
            if len(contacts) != (1 << bit):
                raise ValueError(f"Unexpected active MOM count on {side} B{bit}: {len(contacts)}")
            plates[f"b{side}{bit}"] = several_contacts(contacts, every_plate)
    return {"gates": gates, "plates": plates}


def write_recipe(run_id, payload, context, entry, analyzer, resources, args, summary):
    dest = ROOT / "work/decks" / run_id
    dest.mkdir(parents=True, exist_ok=False)
    payload["context.json"] = (json.dumps(context, indent=2) + "\n").encode()
    for name, blob in payload.items():
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    recipe = {
        "schema_version": 1, "run_id": run_id, "design_id": "sar8_single_edge_d2_xref_layout",
        "entry": entry, "analyzer": analyzer,
        "inputs": [{"name": n, "source": (dest / n).relative_to(ROOT).as_posix(), "sha256": sha(b)}
                   for n, b in payload.items()],
        "resources": resources, "spectre_args": args, "summary_signals": summary,
        "expected_stop_s": context["expected_stop_s"], "qualification_scope": context["scope"],
        "test_conditions": context,
    }
    path = dest / "recipe.json"
    path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(ROOT)


def stimulus(prefix, pins, model, vdd, pilot):
    name = prefix + "_"
    wave = lambda net, points: "V_" + name + net + f" ({name}{net} 0) vsource type=pwl wave=[{points}]"
    mapping = {
        "TOPN": name + "topn", "TOPP": name + "topp", "VDD": name + "vdd", "VSS": "0",
        "VREFN": name + "refn", "VREFP": name + "refp", "PRESET": name + "preset",
    }
    signals = [
        f"VV_{prefix} ({name}vdd 0) vsource dc={vdd:g}",
        f"V_{prefix}_CM ({name}cm 0) vsource dc=0.45",
        wave("track", f"0 {vdd:g} 8.95n {vdd:g} 9.05n 0"),
        wave("preset", f"0 {vdd:g} 5.95n {vdd:g} 6.05n 0"),
        f"X_{prefix}_TN ({name}topn {name}cm {name}track {name}vdd 0) b_tb_switch",
        f"X_{prefix}_TP ({name}topp {name}cm {name}track {name}vdd 0) b_tb_switch",
    ]
    for ref, voltage in (("refn", 0), ("refp", .9)):
        rail = name + ref
        signals.extend([f"VS_{rail} ({rail}_src 0) vsource dc={voltage:g}",
                        f"RS_{rail} ({rail}_src {rail}) resistor r=50",
                        f"CS_{rail} ({rail} 0) capacitor c=4p"])
    bits = (7,) if pilot else tuple(range(8))
    for b in bits:
        net = f"code{b}"
        mapping[f"CODE{b}"] = name + net
        signals.append(wave(net, f"0 0 11.95n 0 12.05n {vdd:g} 24.95n {vdd:g} 25.05n 0"))
    if prefix == "control":
        # Keep the native circuitry on both sides, with the same drive/code levels.
        root = re.search(r"(?m)^subckt sar8i_refword (.+)$", (ROOT / DRIVER_SOURCE).read_text())[1].split()
        formal = {}
        for port in root:
            if port in mapping:
                formal[port] = mapping[port]
            elif port in refsel.SELECTS:
                formal[port] = name + port.lower()
            else:
                raise ValueError(f'Unbound schematic reference port {port}')
        mapping.update(formal)
        mapping.update({pin: formal[select] for pin, select in refsel.SPLIT_TO_SELECT.items()})
        signals.append("X_control_ref (" + " ".join(formal[n] for n in root) + ") sar8i_refword")
    for port in CDAC_PORTS[:32]:
        if port not in mapping:
            mapping[port] = f"{name}vdd" if port[1] == "N" else "0"
    signals.append(f"X_{prefix} (" + " ".join(mapping[n] for n in pins) + f") {model}")
    return signals


def prepare_focused(identity, run_id, corner, *, control):
    prefix = "control" if control else "post"
    payload, source_record = fetch_pex(CDAC_CONTROL if control else identity)
    manifest = (json.loads(pull(evidence(identity) + "/manifest.json")) if control else source_record)
    reference = (source_record if control else json.loads(pull(evidence(CDAC_CONTROL) + "/manifest.json")))
    if reference["gds"]["structural_sha256"][CDAC] != manifest["source_cdac_geometry_sha256"]:
        raise ValueError("The control does not contain the same CDAC geometry")
    bits = tuple(manifest["target_bits"])
    pilot = bits == (7,)
    mapping = {}
    deck = ["simulator lang=spectre", "global 0"]
    condition = json.loads((ROOT / "specs/corners.json").read_text())[corner]
    vdd = condition["vdd_v"]
    deck.extend(line.replace("ttmacro_mos_moscap", condition["mos"].lower() + "macro_mos_moscap")
                for line in PLATFORM.read_text().splitlines() if line.startswith('include "/home/process/'))
    for name, source in (("reference.scs", DRIVER_SOURCE),
                         ("library_include.scs", f"tb/common/platform/library_lpe_{CELL_RC[corner]}.scs")):
        payload[name] = (ROOT / source).read_bytes()
        deck.append(f'include "{name}"')
    payload["block_switch.va"] = (ROOT / "tb/common/veriloga/block_switch.va").read_bytes()
    deck.append('ahdl_include "block_switch.va"')
    saved = []
    model, expected = (CDAC, CDAC_PORTS) if control else (COMBINED, manifest["ports"])
    name = "extracted.scs"
    deck.append(f'include "{name}"')
    source = payload[name]
    pins = pin_order(source, model, expected)
    analog = analog_nodes(source, bits)
    mapping[prefix] = {category: {key: [f"X_{prefix}.{n}" for n in nodes] for key, nodes in group.items()}
                       for category, group in analog.items()}
    saved.extend(p for group in mapping[prefix].values() for nodes in group.values() for p in nodes)
    saved.extend(f"{prefix}_{k}" for k in ["topn", "topp", "refn", "refp", "code7", "preset"])
    saved.extend([f"VV_{prefix}:p", f"VS_{prefix}_refn:p", f"VS_{prefix}_refp:p"])
    deck.extend(stimulus(prefix, pins, model, vdd, pilot))
    settings = next(line for line in join_lines(PLATFORM.read_bytes()).splitlines() if line.startswith("simulatorOptions"))
    deck.extend([settings.replace("temp=27", f"temp={condition['temperature_c']}"), "saveOptions options save=selected",
                 "tran_drive tran stop=38n maxstep=5p errpreset=moderate lteratio=10",
                 "save " + " ".join(saved)])
    payload["test.scs"] = ("\n".join(deck) + "\n").encode()
    payload["measure_reference_driver.py"] = (ROOT / "Layout/tools/analysis/measure_reference_driver.py").read_bytes()
    payload["native_stream.py"] = (ROOT / "tools/saradc/measure/native_stream.py").read_bytes()
    context = {
        "scope": "Bipolar CODE transitions into the saved CDAC, measured at MOS gates and MOM plates.",
        "case": "focused", "physical_evidence": identity, "gds_sha256": manifest["gds"]["sha256"],
        "control_evidence": CDAC_CONTROL, "bits": bits, "probe_paths": mapping, "condition": condition,
        "expected_stop_s": 38e-9, "corner": corner, "lsb_v": LSB, "command_times_s": [12e-9, 25e-9],
    }
    resources = {
        "threads": 4, "simulation_rss_mib": 1792, "simulation_virtual_mib": 8192,
        "analysis_rss_mib": 512, "analysis_virtual_mib": 2048, "max_output_mib": 512,
        "simulation_wall_seconds": 1800, "analysis_wall_seconds": 600, "queue_timeout_seconds": 3600,
    }
    return write_recipe(run_id, payload, context, "test.scs", "measure_reference_driver.py", resources,
                        ["+preset=mx", "+mt=4", "-preset_override", "+lqtimeout", LICENSE_WAIT_SECONDS],
                        [prefix + "_topn", prefix + "_topp"])


def replace_adc(payload, pins, model):
    top = "top/adc_top.scs"
    body = payload[top].decode()
    old_cdac = re.search(r"(?m)^\s*XCDAC[ \t]+\(([^)]+)\)[ \t]+sar8j_r1_cdac[ \t]*$", body)
    actual = old_cdac[1].split()
    formals = refsel.CDAC_PORTS if len(actual) == len(refsel.CDAC_PORTS) else CDAC_PORTS
    mapping = dict(zip(formals, actual, strict=True))
    if formals == refsel.CDAC_PORTS:
        mapping.update({pin: mapping[select] for pin, select in refsel.SPLIT_TO_SELECT.items()})
    if model == COMBINED:
        xref = re.search(r"(?m)^\s*XREF[ \t]+\(([^)]+)\)[ \t]+sar8i_refword[ \t]*$", body)
        formal = re.search(r"(?m)^subckt sar8i_refword (.+)$", payload[DRIVER_SOURCE.removeprefix("design/")].decode())[1]
        mapping.update(zip(formal.split(), xref[1].split(), strict=True))
        # Older staged decks exposed the dummy RST_DONE tie through XREF.
        replacement = "\n    W_REFERENCE_RST (" + mapping["RST_DONE"] + " 0) iprobe" if 'RST_DONE' in mapping else ''
        body = body[:xref.start()] + replacement + body[xref.end():]
    body, count = re.subn(r"(?m)^[ \t]*XCDAC[ \t]+\([^)]+\)[ \t]+sar8j_r1_cdac[ \t]*$",
                          "    XCDAC (" + " ".join(mapping[n] for n in pins) + ") " + model, body)
    if count != 1:
        raise ValueError("Cannot bind the ADC CDAC instance")
    payload[top] = body.encode()
    old = b'include "xtor/cdac/cdac.scs"'
    if payload["dut.scs"].count(old) != 1:
        raise ValueError("Unexpected active DUT CDAC source")
    payload["dut.scs"] = payload["dut.scs"].replace(old, b'include "extracted.scs"')


def prepare_adc(identity, run_id, corner, *, control, codes=None):
    extracted, manifest = fetch_pex(identity)
    model = CDAC if control else COMBINED
    expected = CDAC_PORTS if control else manifest["ports"]
    if not control and manifest["target_bits"] != list(range(8)):
        raise ValueError("The full ADC fixture needs the eight-bit driver")
    source = extracted["extracted.scs"]
    pins = pin_order(source, model, expected)
    analog = analog_nodes(source, range(8))
    if codes is None:
        codes = json.loads((ROOT / "tb/top/short/context.json").read_text())["expected_codes"]
    library = (ROOT / f"tb/common/platform/library_lpe_{CELL_RC[corner]}.scs").read_bytes()
    seed = json.loads((ROOT / reference_short(
        "single_edge", corner, run_id, codes=codes, source_blobs=views.build("current", ROOT),
        cell_library=library, max_output_mib=2048,
    )).read_text())
    payload = {row["name"]: (ROOT / row["source"]).read_bytes() for row in seed["inputs"]}
    payload.update(extracted)
    replace_adc(payload, pins, model)
    context = json.loads(payload["context.json"])
    mapping = {kind: {port: ["XDUT.XCDAC." + name for name in nodes] for port, nodes in items.items()}
               for kind, items in analog.items()}
    old_gates = re.compile(r"XDUT\.G[NP][NP]\d$", re.I)
    deck = payload["test.scs"].decode().replace("reltol=1e-6", "reltol=1e-4").splitlines()
    kept = []
    edit_count = 0
    for line in deck:
        if line.startswith("save "):
            edit_count += 1
            kept.extend(name for name in line.split()[1:]
                        if not name.upper().startswith("XDUT.XCDAC.") and not old_gates.fullmatch(name))
    if edit_count != 1:
        raise ValueError("Expected one selected-signal block")
    extra = sorted({name for group in mapping.values() for nodes in group.values() for name in nodes})
    saved = kept + extra + ["VVDD:p"]
    deck = [line + " strobeperiod=10p strobeoutput=strobeonly" if line.startswith("tran_short tran ") else line
            for line in deck]
    payload["test.scs"] = ("\n".join(line for line in deck if not line.startswith("save "))
                           + "\nsave " + " ".join(saved) + "\n").encode()
    context.update(run_id=run_id, pex=True, pex_modules=["cdac"] if control else ["cdac", "xref", "interconnect"],
                   physical_evidence=identity, gds_sha256=manifest["gds"]["sha256"], probe_paths=mapping,
                   saved_step_s=10e-12, distributed_supplies=manifest.get("distributed_supplies", []),
                   scope="Current transistor ADC short fixture with " +
                   ("same-geometry CDAC PEX and schematic XREF" if control else "coupled XREF and CDAC native PEX"))
    context["required_signals"] = [s.lower() for s in kept + extra if s != "VVDD:p"]
    context["required_signals"] = [s.replace("\\", "") for s in context["required_signals"]]
    analyzer = "measure_reference_adc.py"
    payload[analyzer] = (ROOT / "Layout/tools/analysis" / analyzer).read_bytes()
    payload["measure_reference_driver.py"] = (ROOT / "Layout/tools/analysis/measure_reference_driver.py").read_bytes()
    context["source_hashes"] = {name: sha(blob) for name, blob in payload.items() if name != "context.json"}
    seed["resources"].update(simulation_rss_mib=2304, simulation_virtual_mib=10240)
    options = ["+preset=mx" if a.startswith("+preset=") else a for a in seed["spectre_args"]]
    options[options.index("+lqtimeout") + 1] = LICENSE_WAIT_SECONDS
    return write_recipe(run_id, payload, context, "test.scs", analyzer, seed["resources"],
                        options, seed["summary_signals"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence")
    parser.add_argument("run_id")
    parser.add_argument("--corner", choices=["tt", "ssc", "ssh", "ffc", "ffh"], default="tt")
    parser.add_argument("--adc", action="store_true")
    parser.add_argument("--codes", type=int, nargs="+", help="Code centers for the integrated ADC fixture")
    parser.add_argument("--control", action="store_true", help="CDAC PEX with the schematic gate driver")
    args = parser.parse_args()
    if args.corner not in CELL_RC:
        parser.error("No characterized cell RC library for the requested corner")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,55}", args.run_id):
        parser.error("Use a unique execution identity")
    if args.codes is not None and not args.adc:
        parser.error("--codes applies to the integrated ADC run")
    if args.adc:
        print(prepare_adc(args.evidence, args.run_id, args.corner, control=args.control, codes=args.codes))
    else:
        print(prepare_focused(args.evidence, args.run_id, args.corner, control=args.control))
