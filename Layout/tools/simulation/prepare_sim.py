"""Bind a finished physical evidence directory to the fixed managed fixture."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from Layout.project import config,evidence


ROOT = Path(__file__).resolve().parents[3]
LAYOUT = ROOT / "Layout"


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def pull(host, path):
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", path) or ".." in path.split("/"):
        raise ValueError("Unsupported evidence path")
    data = subprocess.check_output(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host,
         "bash -c 'test \"$(stat -c %s {0})\" -le 1048576 && cat {0}'".format(path)],
        timeout=20,
    )
    if not data:
        raise ValueError("Empty remote evidence: " + path)
    return data


def header(netlist, top):
    # Both the extracted pin order and the exact emitted subcircuit name are
    # authoritative. Do not infer the positional order from the layout labels.
    match = re.search(
        r"(?im)^\s*subckt[ \t]+(" + re.escape(top) + r")[ \t]+([^\r\n]+)", netlist)
    if not match:
        raise ValueError("Missing extracted Spectre subcircuit " + top)
    pins = match[2].strip().strip("()").split()
    if sorted(pin.upper() for pin in pins) != ["B0", "B1", "TOP"]:
        raise ValueError("Unexpected PEX pins: " + repr(pins))
    return match[1], [pin.upper() for pin in pins]


def coupling(extracted):
    def group(node):
        match = re.match(r"(?:N_)?(TOP|B0|B1)(?:_|$)", node, flags=re.I)
        return match[1].upper() if match else None

    pairs = {}
    for name, blob in extracted.items():
        if not name.endswith(".pxi"):
            continue
        for a, b, value in re.findall(
            r"(?mi)^\s*cc_\d+\s*\(\s*(\S+)\s+(\S+)\s*\)\s*capacitor\s+c=(\S+)",
            blob.decode("ascii"),
        ):
            ends = (group(a), group(b))
            if not all(ends) or ends[0] == ends[1]:
                raise ValueError("Unclassified coupling element: " + repr((a, b)))
            scale = {"a": 1e-18, "f": 1e-15, "p": 1e-12}.get(value[-1])
            cap = float(value[:-1]) * scale if scale else float(value)
            label = ":".join(sorted(ends))
            data = pairs.setdefault(label, {"elements": 0, "sum_f": 0})
            data["elements"] += 1
            data["sum_f"] += cap
    if not all(pairs.get(pair, {}).get("sum_f", 0) > 0 for pair in ("B0:TOP", "B1:TOP")):
        raise ValueError("PEX does not contain the expected top-to-bottom coupling")
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_id")
    parser.add_argument("run_id")
    parser.add_argument("--host", default=None)
    args = parser.parse_args()
    for value in (args.evidence_id, args.run_id):
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,55}", value):
            parser.error("Use a lowercase stable identity")
    args.host=args.host or config()['host']
    if args.host!=config()['host']:raise ValueError('Evidence must use the configured layout host')
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", args.host):
        parser.error("Use the configured SSH alias")

    base = evidence(args.evidence_id)
    native = json.loads(pull(args.host, base + "/manifest.json"))
    if native["case"] not in {"baseline", "reroute"} or native.get("error"):
        raise ValueError("Need a successful ratio extraction")
    if native["checks"]["lvs"]["verdict"] != "CORRECT":
        raise ValueError("Source layout did not match the independent reference")
    if native["decks"]["pex"]["support"].get("mom_runset", {}).get("mom_device_exclusions") != 7:
        raise ValueError("Source is missing the installed runset's MOM-device capacitance exclusions")
    raw = pull(args.host, base + "/pex/extracted.scs")
    if digest(raw) != native["checks"]["pex"]["sha256"]:
        raise ValueError("PEX identity differs from the extraction receipt")
    netlist = raw.decode("ascii")
    top, pins = header(netlist, native["top"])
    if len(re.findall(r"(?mi)^\s*\S+\s*\([^\n()]+\)\s*cfmom_2t\b", netlist)) != 3:
        raise ValueError("Expected three native MOM models in the extracted circuit")
    extracted = {"extracted.scs": raw}
    pending = [raw]
    while pending:
        for name in re.findall(rb'(?mi)^\s*include\s+"([^"\r\n]+)"', pending.pop()):
            name = name.decode("ascii")
            if not re.fullmatch(r"extracted\.scs\.[A-Za-z0-9_.-]+", name):
                raise ValueError("Unreviewed PEX dependency " + name)
            if name not in extracted:
                companion = pull(args.host, base + "/pex/" + name)
                expected = native["checks"]["pex"].get("companion_sha256", {}).get(name)
                if expected and digest(companion) != expected:
                    raise ValueError("PEX companion identity differs: " + name)
                extracted[name] = companion
                pending.append(companion)

    fixture = (LAYOUT / "tb/mom_fixture.scs").read_text(encoding="ascii")
    for placeholder, mapping in (
        ("@PEX_Q_INSTANCE@", {"TOP": "QPOST", "B0": "QXB0", "B1": "QXB1"}),
        ("@PEX_F_INSTANCE@", {"TOP": "FPOST", "B0": "FXB0", "B1": "FXB1"}),
    ):
        fixture = fixture.replace(placeholder, "(" + " ".join(mapping[p] for p in pins) + ") " + top)
    payload = {
        **extracted,
        "test.scs": fixture.encode("ascii"),
        "measure.py": (LAYOUT / "tools/analysis/measure.py").read_bytes(),
        "native_stream.py": (ROOT / "tools/saradc/measure/native_stream.py").read_bytes(),
    }
    dest = ROOT / "work/layout" / args.run_id
    spec = {
        "run_id": args.run_id, "design_id": "sar8_b_mom_layout_pilot",
        "entry": "test.scs", "analyzer": "measure.py",
        "summary_signals": ["qpre", "qpost", "fpre", "fpost", "cm"],
        "expected_stop_s": 9e-9, "oa_parity": "pilot_fixture_only",
        "qualification_scope": "TT MOM fixture pre/post PEX; no ADC qualification",
        "test_conditions": {
            "physical_evidence": base, "gds_sha256": native["gds"]["sha256"],
            "cdl_sha256": native["source_sha256"]["reference.cdl"],
            "extracted_sha256": {name: digest(data) for name, data in extracted.items()},
            "b1_extension_um": native["b1_extension_um"], "native_pex_pins": pins,
            "extracted_coupling": coupling(extracted),
            "temperature_c": 27, "drive_ohm": 2000, "top_load_f": 4e-15,
            "top_initial_v": 0.45,
        },
        "inputs": [{"name": name, "source": (dest / name).relative_to(ROOT).as_posix()}
                   for name in sorted(payload)],
        "resources": {
            "threads": 1, "simulation_rss_mib": 1024, "simulation_virtual_mib": 8192,
            "analysis_rss_mib": 256, "analysis_virtual_mib": 1024, "max_output_mib": 32,
            "simulation_wall_seconds": 120, "analysis_wall_seconds": 90,
            "queue_timeout_seconds": 3600,
        },
    }
    payload["recipe.json"] = (json.dumps(spec, indent=2, sort_keys=True) + "\n").encode("ascii")
    dest.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        (dest / name).write_bytes(data)
    print((dest / "recipe.json").relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
