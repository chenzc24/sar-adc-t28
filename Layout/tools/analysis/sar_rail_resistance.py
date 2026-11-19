"""Solve the extracted passive rail network between the macro pin and each observed MOS terminal."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu

from Layout.tools.analysis.sar_timing_probes import probes


def joined(path):
    return re.sub(r"\\[ \t]*\r?\n[ \t]*", " ", path.read_text())


def rail_resistance(folder, core):
    manifest = json.loads((folder / "manifest.json").read_text())
    root = folder if (folder / "extracted.scs").is_file() else folder / "pex"
    main = root / "extracted.scs"
    coordinates = folder / "layout.sp"
    if not coordinates.is_file():
        coordinates = folder / "lvs" / "svdb" / (manifest["top"] + ".sp")
    measured = probes(main, coordinates, core / "sar-readback.txt", True)
    models = joined(root / "extracted.scs.pex")
    circuits = joined(root / ("extracted.scs." + manifest["top"] + ".pxi"))
    values = {}
    for rail in ("VDD", "VSS"):
        pattern = (
            r"(?im)^subckt (PM_\S+%"
            + rail
            + r")\s*\(([^)]*)\)[^\n]*\n([\s\S]*?)^ends\b"
        )
        name, formals, body = re.search(pattern, models).groups()
        instance = re.search(
            r"(?im)^x_\S+\s*\(([^)]*)\)\s*" + re.escape(name) + r"[ \t]*$", circuits
        )
        ports = dict(zip(instance[1].split(), formals.split(), strict=True))
        pad = ports[rail]
        edges = [
            (a, b, float(r))
            for a, b, r in re.findall(
                r"(?im)^r\S+\s*\(\s*(\S+)\s+(\S+)\s*\)\s+resistor\s+r=([^\s]+)", body
            )
        ]
        if not edges or any(v <= 0 for _, _, v in edges):
            raise ValueError("Invalid extracted resistor network for " + rail)
        index = {
            n: i for i, n in enumerate(sorted({v for a, b, _ in edges for v in (a, b)}))
        }
        i = np.array([index[a] for a, _, _ in edges])
        j = np.array([index[b] for _, b, _ in edges])
        g = np.array([1.0 / r for _, _, r in edges])
        laplacian = coo_matrix(
            (np.r_[g, g, -g, -g], (np.r_[i, j, i, j], np.r_[i, j, j, i])),
            shape=(len(index), len(index)),
        ).tocsc()
        _, components = connected_components(laplacian, directed=False)
        pad_i = index[pad]
        keep = np.flatnonzero(
            (components == components[pad_i]) & (np.arange(len(index)) != pad_i)
        )
        equation = {node: i for i, node in enumerate(keep)}
        solver = splu(laplacian[keep][:, keep])
        for alias, probe in measured.items():
            if probe["terminal"] != rail:
                continue
            k = index[ports[probe["pex_node"]]]
            if k == pad_i:
                resistance = 0.0
            else:
                if k not in equation:
                    raise ValueError("Disconnected rail terminal " + alias)
                source = np.zeros(len(keep))
                source[equation[k]] = 1.0
                resistance = solver.solve(source)[equation[k]]
            values[alias] = {
                "resistance_ohm": round(float(resistance), 4),
                "instance": probe["instance"],
                "terminal": probe["pex_node"],
                "xy_um": probe["xy_um"],
            }
    return {
        "extraction": manifest["id"],
        "gds_sha256": manifest["gds"]["sha256"],
        "method": "DC equivalent from macro pad to one extracted diffusion terminal. Other device loads are open.",
        "measurements": values,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extraction", type=Path)
    parser.add_argument("core", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = rail_resistance(args.extraction, args.core)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
