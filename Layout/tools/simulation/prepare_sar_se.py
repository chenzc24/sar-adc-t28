"""Prepare a closed-loop ADC run with the extracted single-edge SAR macro.

The macro's xRC netlist replaces the five SAR-group instances of the top. Everything else
is the single_edge_lpe deck: extracted CDAC, cell LPE for the remaining standard cells and
the same analyzer. Internal SAR probes are saved at their extracted source-named nets and
read back under their schematic names.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

from Layout.design.sar_single_edge import CORE, GROUP, PORT_ORDER, electrical, flat_net
from Layout.project import ROOT, config, evidence
from tools.saradc import single_edge_lpe

ENTRY = "sar_se_xrc.scs"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(identity):
    """Copy the verified extraction of a physical run and check its recorded digests."""
    remote = evidence(identity)
    host = config()["host"]
    manifest = json.loads(subprocess.check_output(["ssh", host, "cat " + shlex.quote(remote + "/manifest.json")], timeout=60))
    if manifest.get("error") or manifest.get("case") != "sar-se":
        raise ValueError("Physical run did not complete: " + str(manifest.get("error")))
    checks = manifest["checks"]
    if checks.get("lvs", {}).get("verdict") != "CORRECT" or "pex" not in checks:
        raise ValueError("Extraction requires a CORRECT LVS and a completed PEX")
    if manifest["decks"]["pex"].get("netlist_names") != "SOURCENAMES":
        raise ValueError("The probes need a source-named extraction")
    local = ROOT / "work/layout/sar-se/pex" / identity
    local.mkdir(parents=True, exist_ok=True)
    expected = {"extracted.scs": checks["pex"]["sha256"], **checks["pex"]["companion_sha256"]}
    for name, digest in expected.items():
        path = local / name
        if not path.exists():
            subprocess.check_call(["scp", "-q", f"{host}:{remote}/pex/{name}", str(path)], timeout=600)
        if sha(path.read_bytes()) != digest:
            raise ValueError("Extracted file differs from its manifest: " + name)
    return manifest, {name: (local / name).read_bytes() for name in expected}


def rename(files):
    """Give the extraction stable package names and fix its internal includes."""
    out = {}
    for name, data in files.items():
        out[ENTRY + name[len("extracted.scs"):]] = data.replace(b"extracted.scs", ENTRY.encode())
    return out


def macro_ports(netlist):
    text = re.sub(rb"\\\r?\n", b" ", netlist).decode("ascii", "replace")
    m = re.search(r"(?im)^subckt\s+" + CORE + r"\s*\(([^)]*)\)", text)
    if not m:
        raise ValueError("Extracted netlist lacks the macro subckt")
    return m[1].split()


def receiver_gates(pxi):
    """Source-named net -> {receiving instance: gate node}; each net is a distributed RC instance."""
    text = re.sub(rb"\\\r?\n", b" ", pxi).decode("ascii", "replace")
    gates = {}
    for m in re.finditer(r"(?m)^x_PM_" + CORE + r"\\%(\S+)\s*\(([^)]*)\)", text):
        net = m[1]
        found = {}
        for node in m[2].split():
            g = re.fullmatch(r"N_" + re.escape(net) + r"_(X\S+?)\\/MM\d+_g", node)
            if g:
                found.setdefault(g[1], node)
        gates[net] = found
    return gates


def top_with_macro(ports):
    """Remove the SAR-group instances from the top and instantiate the extracted macro."""
    source = (ROOT / "design/top/adc_top.scs").read_text(encoding="utf-8")
    lines, out, removed = source.splitlines(keepends=True), [], []
    i = 0
    while i < len(lines):
        stmt = [lines[i]]
        while stmt[-1].rstrip("\r\n").endswith("\\") and i + 1 < len(lines):
            i += 1
            stmt.append(lines[i])
        first = stmt[0].split()
        if first and first[0] in GROUP and "(" in stmt[0]:
            removed.append(first[0])
        else:
            out.extend(stmt)
        i += 1
    if sorted(removed) != sorted(GROUP):
        raise ValueError("Top instances differ from the macro group: " + str(removed))
    nets = {"VDD": "VDD!", "VSS": "0"}
    if sorted(p.upper() for p in ports) != sorted(list(PORT_ORDER) + ["VDD", "VSS"]):
        raise ValueError("Extracted macro ports differ: " + str(ports))
    call = f"XSAR ({' '.join(nets.get(p.upper(), p.upper()) for p in ports)}) {CORE}\n"
    text = "".join(out)
    end = re.search(r"(?m)^ends sar_adc8_join_r4\b", text)
    return (text[:end.start()] + call + text[end.start():]).encode("utf-8")


def macro(identity):
    manifest, files = fetch(identity)
    files = rename(files)
    ports = macro_ports(files[ENTRY])
    gates = receiver_gates(files[ENTRY + "." + CORE + ".pxi"])
    cells, public, _ = electrical()
    internal = {n for c in cells.values() for n in c["pins"].values() if "__" not in n} - set(public) - {"VDD", "VSS"}
    chosen = {}

    def probe(signal):
        """Internal SAR nets are read at the gate of a receiving cell inside the probe's own block.

        Tap and select nets are read at the delay-window multiplexers that consume them."""
        parts = signal.split(".")
        if parts[0] != "xdut":
            return None
        if len(parts) == 2:
            name, block = parts[1].upper(), ""
            if name not in internal:
                return None
        elif parts[1].upper() in GROUP:
            name, block = flat_net(signal), "__".join(parts[1:-1]).upper()
        else:
            return None
        receivers = gates.get(name)
        if not receivers:
            raise ValueError(f"Extracted macro has no receiving gate on {name} for {signal}")
        ranked = sorted(receivers, key=lambda inst: ("__XTAP" not in inst, not inst.startswith("X" + block), inst))
        chosen[signal] = dict(net=name, receiver=ranked[0][1:], node=receivers[ranked[0]])
        return "XDUT.XSAR." + receivers[ranked[0]]

    convert = json.loads((ROOT / "work/layout/sar-se" / manifest["staging"].rsplit("/", 1)[1].removeprefix("sar-se-")
                          / "convert.json").read_text())
    record = dict(physical_id=identity, master=CORE, oa_view=manifest["oa_view"], library=manifest["library"],
                  gds_sha256=manifest["gds"]["sha256"], structural_sha256=manifest["gds"]["structural_sha256"],
                  lvs=manifest["checks"]["lvs"]["verdict"], drc_blocking=manifest["checks"]["drc"]["blocking"],
                  extracted_sha256=manifest["checks"]["pex"]["sha256"], def_sha256=convert["def_sha256"],
                  ports=ports, internal_nets=sorted(internal), probes=chosen,
                  probe_rule="internal SAR nets read at the gate node of one receiving cell in the extracted RC network")
    return dict(entry=ENTRY, files=files, top=top_with_macro(ports), probe=probe, record=record)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("physical_id")
    ap.add_argument("corner", choices=single_edge_lpe.CELL_RC)
    ap.add_argument("kind", choices=single_edge_lpe.CODES)
    ap.add_argument("--cdac", choices=["nominal", "cworst"], default="nominal")
    ap.add_argument("--revision", default="a")
    a = ap.parse_args()
    print(single_edge_lpe.prepare(a.corner, a.kind, a.cdac, a.revision, macro=macro(a.physical_id)))
