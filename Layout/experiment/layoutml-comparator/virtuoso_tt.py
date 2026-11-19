"""Bind the experimental xRC to the already measured comparator TT fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from virtuoso_metrics import TOP, checked_measurements


ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "work/layout"
PHYSICAL = RUNS / "layoutml-clean-comparator/native"
SCHEMATIC = "comp-pre-tt-20261116"
PORTS = "CLK OUTN OUTP VDD VINN VINP VSS".split()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(run_id, physical_id, xrc_id, threshold=False):
    for name in (run_id, physical_id, xrc_id):
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,55}", name):
            raise ValueError("Invalid run identity")
    physical = PHYSICAL / physical_id
    xrc = PHYSICAL / xrc_id
    measured = checked_measurements(physical, xrc)
    if measured["lvs"] != "CORRECT":
        raise ValueError("LVS did not match the frozen comparator")
    recipe = json.loads((RUNS / SCHEMATIC / "recipe.json").read_bytes())
    blobs = {}
    for row in recipe["inputs"]:
        data = (ROOT / row["source"]).read_bytes()
        if sha(data) != row["sha256"]:
            raise ValueError("Reference test input changed: " + row["name"])
        blobs[row["name"]] = data
    if measured["source"]["electrical_sha256"] != sha(blobs["xtor/comparator/comparator.scs"]):
        raise ValueError("Mismatched electrical source")
    for name in measured["extracted_hashes"]:
        blobs[name] = (xrc / "pex" / name).read_bytes()
    extract = blobs["extracted.scs"].decode().replace("\\\n", " ")
    pins = re.findall(r"(?mi)^subckt\s+" + TOP + r"\s*\(([^)]+)\)", extract)
    if len(pins) != 1 or sorted(pins[0].split()) != sorted(PORTS):
        raise ValueError("Unexpected xRC top ports")
    binding = " ".join(pins[0].split())
    blobs["comparator_pex.scs"] = (
        'simulator lang=spectre\ninclude "extracted.scs"\n'
        f'subckt sar_strongarm_t28 ({" ".join(PORTS)})\n'
        f'XPEX ({binding}) {TOP}\nends sar_strongarm_t28\n'
    ).encode()
    needle = b'include "xtor/comparator/comparator.scs"'
    if blobs["dut.scs"].count(needle) != 1:
        raise ValueError("Comparator DUT inclusion changed")
    blobs["dut.scs"] = blobs["dut.scs"].replace(needle, b'include "comparator_pex.scs"')
    blobs["comparator_physical.json"] = (physical / "manifest.json").read_bytes()
    blobs["comparator_xrc.json"] = (xrc / "manifest.json").read_bytes()
    scope = "Experimental native StrongARM pre-fill xRC; matched TT signed decisions, reset and kickback."
    local_markers = set(measured["markers"]) - {"DIODMY_L:WARNING", "IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1"}
    if local_markers:
        scope += " Historical OA geometry has local DRC errors. Diagnostic comparison only."
    context = json.loads(blobs["context.json"])
    if threshold:
        levels = list(range(-1000,1001,50))
        # The warm-up is separate; repeat the two endpoints across the turn so
        # each sweep has its own complete monotonic list and normal clock reset.
        microvolts = [-1500] + levels + levels[::-1]
        volts = [v*1e-6 for v in microvolts]
        knots = []
        for i,v in enumerate(volts):
            knots.append(f"{10*i}n {0.45+v:.9f}")
            if i+1<len(volts):
                knots.append(f"{10*i+9.9:.1f}n {0.45+v:.9f}")
        deck,n = re.subn(rb"(?m)^VCP [^\r\n]+",
                         ("VCP (c_p 0) vsource type=pwl wave=["+" ".join(knots)+"]").encode(),
                         blobs["comparator_fixture.scs"])
        if n!=1:
            raise ValueError("Expected a single comparator differential stimulus")
        blobs["comparator_fixture.scs"] = deck
        stop_ns=10*len(volts)+5
        if blobs["test.scs"].count(b"stop=105n")!=1:
            raise ValueError("Fixture stop time changed")
        blobs["test.scs"]=blobs["test.scs"].replace(b"stop=105n",f"stop={stop_ns}n".encode())
        old = b"if 'comparator' in modules:requests += [14.5e-9,19e-9]+[(9+10*i)*1e-9 for i in range(10)]"
        if blobs["analyze_blocks.py"].count(old)!=1:
            raise ValueError("Comparator probe-time request changed")
        blobs["analyze_blocks.py"]=blobs["analyze_blocks.py"].replace(
            old,old.replace(b"range(10)",b"range(len(context['comparator_inputs_v']))"))
        recipe["expected_stop_s"]=stop_ns*1e-9
        context["comparator_inputs_v"]=volts
        context["threshold_sweeps_uV"]={"conditioning":microvolts[0],"rising":levels,"falling":levels[::-1]}
        scope="Native xRC TT deterministic trip-point bracket. Opposite 50 uV sweeps with a clock reset every 10 ns."
        context["contracts"]["comparator"]["stimulus"]=scope
    context.update(run_id=run_id, physical_evidence=physical_id, xrc_evidence=xrc_id,
                   schematic_fixture=SCHEMATIC, pex=True, gds_sha256=measured["gds_sha256"],
                   physical_drc=measured["markers"],
                   extracted_original_sha256=measured["extracted_hashes"], extracted_ports=binding.split(),
                   qualification_scope=scope)
    context["source_hashes"].update({n: sha(v) for n, v in blobs.items() if n != "context.json"})
    blobs["context.json"] = (json.dumps(context, indent=2) + "\n").encode()
    dest = RUNS / run_id
    dest.mkdir()
    for name, data in blobs.items():
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    recipe.update(run_id=run_id, design_id="sar_strongarm_native_experiment", qualification_scope=scope,
                  test_conditions=context,
                  inputs=[dict(name=n, source=(dest/n).relative_to(ROOT).as_posix(), sha256=sha(v))
                          for n, v in blobs.items()])
    path = dest / "recipe.json"
    path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("physical")
    parser.add_argument("xrc")
    parser.add_argument("--threshold",action="store_true")
    args = parser.parse_args()
    print(prepare(args.run, args.physical, args.xrc, threshold=args.threshold))
