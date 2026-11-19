"""Map receiver gates and local supply diffusions to specific distributed xRC terminals."""

import math
import re

from Layout.design.sar_timing import SUFFIX, WIDTH
from Layout.tools.analysis.check_sar_timing import readback

RECEIVERS = {
    "ACTIVE": ("XIDLE__XN__XLIB", "I"),
    "SAR_PHI_W": ("XCTRL__XTIM__X016__XLIB", "I"),
    "SAR_PR": ("XCTRL__XTIM__X006__X000__XLIB", "A1"),
    "SAR_NR": ("XCTRL__XTIM__X006__X000__XLIB", "A2"),
}


def probes(extraction, spice, oa, distributed_supplies=False, *, register_data=False):
    _, placed, wiring, _, _ = readback(oa)
    masters = {}
    for sub, body in re.findall(
        r"(?ims)^\.subckt\s+(\S+)[^\n]*\n(.*?)^\.ends\b", spice.read_text()
    ):
        devices = []
        for line in body.splitlines():
            if not line.startswith("M"):
                continue
            q = line.split()
            props = dict(t.split("=", 1) for t in q[6:] if "=" in t)
            if "$X" in props and "$Y" in props:
                devices.append(
                    (
                        q[0],
                        q[2],
                        q[5].lower(),
                        float(props["$X"]) * 1e-4,
                        float(props["$Y"]) * 1e-4,
                        float(props["W"]) * 1e6,
                        (q[1], q[3]),
                    )
                )
        masters[sub] = devices
    flat = re.sub(r"\\\s*\n\s*", " ", extraction.read_text())
    trans = []
    for line in flat.splitlines():
        match = re.match(
            r"(\S+)\s*\(\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\)\s+(nch_mac|pch_mac)\s+",
            line,
            re.IGNORECASE,
        )
        loc = re.search(r"//x=([\deE.+-]+)\s+//y=([\deE.+-]+)", line)
        if match and loc:
            trans.append(
                (
                    match[1],
                    match[3],
                    match[6].lower(),
                    float(loc[1]),
                    float(loc[2]),
                    (match[2], match[4]),
                )
            )
    targets = dict(RECEIVERS)
    if "XCTRL__XTIM__XD_RAW_D__XD1" in placed:
        targets.update(LATCH_Q=("XCTRL__XTIM__XCLOCK__X003__XLIB", "A2"),
                       LATCH_QB=("XCTRL__XTIM__XCLOCK__X002__XLIB", "A2"))
    if register_data:
        targets.update(IDLE_GUARD=("XIDLE__XP__X001__XLIB", "I"),
                       QUIET_REQ=("XCTRL__XTIM__XD_QUIET_D__XD1", "I"),
                       QUIET_DONE=("XCTRL__XTIM__X022__X000__XLIB", "I"))
    for bit in range(8):
        targets["WRITE_AT_D" + str(bit)] = (f"XCTRL__XBIT{bit}__XSTORE__XFF", "CP")
        if register_data:
            targets["DATA_AT_D" + str(bit)] = (f"XCTRL__XBIT{bit}__XSTORE__XFF", "D")
            targets["CDN_AT_D" + str(bit)] = (f"XCTRL__XBIT{bit}__XSTORE__XFF", "CDN")
    if distributed_supplies:
        supply_cells = {f"BIT{i}": f"XCTRL__XBIT{i}__XSTORE__XFF" for i in range(8)}
        for branch, prefix in {"QUIET":"XCTRL__XTIM__XD_QUIET_D", "WRITE":"XCTRL__XTIM__XD_WRITE_D",
                               "RAW":"XCTRL__XTIM__XD_RAW_D", "SAMPLE":"XSEQ__XD", "GUARD":"XIDLE__XD"}.items():
            if prefix+"__XD1" in placed:
                stages = [int(m[1]) for name in placed if (m := re.fullmatch(re.escape(prefix)+r"__XD(\d+)",name))]
                supply_cells[branch+"0"] = prefix+"__XD1"
                supply_cells[branch+"1"] = prefix+f"__XQUAL{max(stages)}__X001__XLIB"
            elif branch in ("QUIET","WRITE","RAW"):
                for stage, detector in enumerate(("X002", "X005")):
                    supply_cells[f"{branch}{stage}"] = f"{prefix}__{detector}__XLIB"
        for site, instance in supply_cells.items():
            for rail in ("VDD", "VSS"):
                targets[f"{rail}_AT_{site}"] = (instance, rail)
    out = {}
    for alias, (name, term) in targets.items():
        _, master, orient, (x, y), _ = placed[name]
        expected = wiring[name][term]
        matched = []
        supply = term in ("VDD", "VSS")
        xsign = -1 if orient in ("MY", "R180") else 1
        ysign = -1 if orient in ("MX", "R180") else 1
        if master not in masters and supply:
            # Calibre can flatten a single DEL occurrence. Use its nonoverlapping
            # LEF site and the rail identity at the extracted diffusion itself.
            site_width = WIDTH[master.removesuffix(SUFFIX)] * 0.14
            for dev, _, model, tx, ty, diffusions in trans:
                if 0 < xsign*(tx-x) < site_width and 0 < ysign*(ty-y) < 1.20:
                    matched.extend((0, dev, node, model, tx, ty) for node in diffusions
                                   if node.startswith("N_" + term + "_"))
        for local, gate, model, dx, dy, width, diffusions in masters.get(master, []):
            if term not in (diffusions if supply else (gate,)):
                continue
            px, py = x + xsign*dx, y + ysign*dy
            viable = [
                (math.hypot(tx - px, ty - py), dev, physical_pin, tx, ty)
                for dev, node, tm, tx, ty, sd in trans
                if tm == model
                and dev.endswith("/" + local)
                and abs(tx - px) < 0.025
                and abs(ty - py) < 0.025
                for physical_pin in (sd if supply else (node,))
                if not supply or physical_pin.startswith("N_" + term + "_")
            ]
            if len(viable) != 1:
                continue
            dist, mdev, node, tx, ty = viable[0]
            matched.append((dist, mdev, node, model, tx, ty))
        if not matched:
            raise ValueError(f"No physical transistor matches {alias} at {name}.{term}")
        roots = {q[2].split("_", 2)[1] for q in matched if q[2].startswith("N_")}
        if len(roots) != 1:
            raise ValueError(f"Terminal matches disagree for {alias}: {roots}")
        if supply and roots != {expected}:
            raise ValueError(
                f"Supply terminal {alias} resolves to {roots}, expected {expected}"
            )
        if supply:
            preferred = "pch_mac" if term == "VDD" else "nch_mac"
            # Choose the same transistor within a master at every placement. Matching
            # roundoff in absolute coordinates must not select another diffusion.
            chosen = min(
                matched,
                key=lambda q: (
                    q[3] != preferred,
                    round(xsign * (q[4] - x), 3),
                    round(ysign * (q[5] - y), 3),
                    q[1],
                ),
            )
        else:
            chosen = min(matched, key=lambda q: (q[3] != "nch_mac", q[0], q[1]))
        out[alias] = {
            "source_net": expected,
            "instance": name,
            "terminal": term,
            "pex_node": chosen[2],
            "pex_device": chosen[1],
            "xy_um": list(chosen[4:]),
            (
                "matched_diffusion_terminals" if supply else "matched_gate_terminals"
            ): len(matched),
            "pex_net": next(iter(roots)),
        }
        if master not in masters:
            out[alias]["coordinate_scope"] = "Flattened diffusion strictly inside the transformed standard-cell site"
        if supply:
            out[alias]["master_xy_um"] = [
                round(xsign * (chosen[4] - x), 3),
                round(ysign * (chosen[5] - y), 3),
            ]
    if (
        len(
            {
                v["pex_net"]
                for k, v in out.items()
                if k.startswith("WRITE_AT_") or k == "SAR_PHI_W"
            }
        )
        != 1
    ):
        raise ValueError("Write receiver gates do not share the extracted clock net")
    if register_data:
        data = [out["DATA_AT_D" + str(i)] for i in range(8)]
        if any(v["source_net"] != f"XCTRL__XBIT{i}__RESET_D" for i,v in enumerate(data)):
            raise ValueError("The bit-register D binding differs from the controller")
        data_roots = {v["pex_net"] for v in data}
        if len(data_roots) != 8 or out["SAR_PHI_W"]["pex_net"] in data_roots:
            raise ValueError("The extracted D terminals are not eight independent register inputs")
        reset = [out["CDN_AT_D" + str(i)] for i in range(8)]
        if any(v["source_net"] != f"XCTRL__XBIT{i}__XSTORE__RN" for i, v in enumerate(reset)):
            raise ValueError("The register's conditional timing arc requires its own CDN terminal")
        if len({v["pex_net"] for v in reset} | data_roots | {out["SAR_PHI_W"]["pex_net"]}) != 17:
            raise ValueError("Data, clock and local register reset do not resolve independently")
    return out
