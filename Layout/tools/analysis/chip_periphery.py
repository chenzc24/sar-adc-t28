"""Periphery extraction of the chip sar8_adc_chip for the Stage 6 supply-model check (constraints.json
stage6_supply_model) and the Stage 2 pad-path netlists.

launch: the chip stream (the check run's fixture.gds) goes through Layout/tools/physical/toplevel_wiring_xcell.py
with every master that is not chip-level wiring kept as an xcell: the ADC core, the output register, the pad decaps,
the PCLAMPC_H_G clamps, every IO-library cell of the ring and the seal ring. The netlist then holds the chip-level
wiring as RC networks ending on the xcell pins: the pad-to-core routes, the supply trunks and their via stacks, the
PAD60GU bond-pad metal, the clamp bars, the core VSS ring and the guard ring, with their mutual coupling. The pad
cells' devices (ESD diodes, drivers) are not extracted here: the pad netlists use the IO library's foundry SPICE,
the netlist the chip LVS compares against. AVDD and VDD, which the installed deck keeps ideal, are extracted too.
"""
import argparse
import base64
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from Layout.project import ROOT, config, write_json

TOP = "sar8_adc_chip"
WORK = ROOT / "work/layout/chip-periphery"
SUPPLIES = ("VDD", "AVDD")
# Masters kept as xcells besides the IO-library cells of the ring.
XCELLS = ["sar8_adc_core_filled", "sar8_out_reg", "sar8_decap_analog", "sar8_decap_pair", "sar8_decap_sar",
          "sar8_decap_dvdd", "PCLAMPC_H_G", "N28_TSMC_SRDMB_Mu"]
WIRING = ("PAD60GU", "M3_M2_CDNS_")      # ring children that are metal only: extracted


def xcells(gds, flatten=()):
    """The xcell list for the stream; flatten: masters to extract with their devices and metal instead (e.g. the
    PCLAMPC_H_G clamps, whose terminal strips an xcell would tie into one ideal node)."""
    return [c for c in all_xcells(gds) if c not in flatten]


def all_xcells(gds):
    import gdstk
    lib = gdstk.read_gds(str(gds))
    cells = {c.name: c for c in lib.cells}
    ring = sorted({r.cell.name for r in cells["sar8_io_ring"].references})
    io = [c for c in ring if not c.startswith(WIRING)]
    if not all(re.fullmatch(r"P[A-Z0-9_]+_G", c) for c in io):
        raise ValueError("Unexpected ring children: %s" % io)
    out = io + XCELLS
    missing = [c for c in out if c not in cells]
    if missing:
        raise ValueError("Stream lacks %s" % missing)
    return out


def launch(identity, gds, source_evidence, flatten=()):
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,55}", identity):
        raise ValueError("Invalid identity")
    if not set(flatten) <= set(XCELLS):
        raise ValueError("Only the listed object masters can be flattened")
    dest = WORK / identity
    dest.mkdir(parents=True, exist_ok=False)
    cells = xcells(gds, flatten)
    driver = ROOT / "Layout/tools/physical/toplevel_wiring_xcell.py"
    files = {"toplevel_wiring_xcell.py": driver.read_bytes(), "candidate.gds": Path(gds).read_bytes(),
             "xcells.txt": ("\n".join(cells) + "\n").encode(), "top.txt": (TOP + "\n").encode(),
             "supplies.txt": ("\n".join(SUPPLIES) + "\n").encode(),
             "source.json": (json.dumps(dict(source_evidence=source_evidence,
                                             source_gds_sha256=hashlib.sha256(Path(gds).read_bytes()).hexdigest()),
                                        indent=2) + "\n").encode()}
    cfg = config()
    blobs = {n: base64.b64encode(b).decode() for n, b in files.items()}
    code = """import os,sys,subprocess,base64
runtime=RUNTIME
os.chdir(runtime);sys.path.insert(0,runtime)
import workspace
out=workspace.evidence(IDENT,create=True)
for name,value in FILES.items():
    with os.fdopen(os.open(out+'/'+name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(base64.b64decode(value))
compile(open(out+'/toplevel_wiring_xcell.py').read(),'toplevel_wiring_xcell.py','exec')
log=os.fdopen(os.open(out+'/driver.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb')
print(subprocess.Popen(['python','-u','toplevel_wiring_xcell.py'],cwd=out,stdout=log,stderr=log,stdin=open(os.devnull),preexec_fn=os.setsid,close_fds=True).pid)
""".replace("RUNTIME", repr(cfg["remote_root"] + "/runtime")).replace("IDENT", repr(identity)).replace("FILES", repr(blobs))
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", cfg["host"], "python -"],
                       input=code.encode(), capture_output=True, timeout=300)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace")[-800:])
    receipt = dict(identity=identity, host=cfg["host"], pid=int(p.stdout.decode().strip()), source_evidence=source_evidence,
                   xcells=cells, supplies=list(SUPPLIES),
                   uploaded_sha256={n: hashlib.sha256(b).hexdigest() for n, b in files.items()})
    (dest / "launch.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def fetch(identity):
    """The finished extraction's manifest, netlist files (gzip over ssh, checked against the manifest) and the uploaded
    stream into work/layout/chip-periphery/IDENTITY."""
    import gzip
    import shlex
    cfg = config()
    base = f"{cfg['remote_root']}/evidence/{identity}"
    dest = WORK / identity
    ssh = lambda cmd: subprocess.run(["ssh", "-o", "BatchMode=yes", cfg["host"], cmd], capture_output=True,
                                     timeout=1800, check=True).stdout
    manifest = json.loads(ssh(f"cat {shlex.quote(base + '/manifest.json')}"))
    if not manifest.get("done") or manifest.get("error"):
        raise ValueError("Extraction not finished: " + identity)
    (dest / "pex").mkdir(parents=True, exist_ok=True)
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    want = dict([("extracted.scs", manifest["checks"]["pex"]["sha256"])] +
                list(manifest["checks"]["pex"]["companion_sha256"].items()))
    for name, digest in want.items():
        blob = gzip.decompress(ssh(f"gzip -c {shlex.quote(base + '/pex/' + name)}"))
        if hashlib.sha256(blob).hexdigest() != digest:
            raise ValueError("Fetched file differs from the manifest: " + name)
        (dest / "pex" / name).write_bytes(blob)
    gds = ssh(f"cat {shlex.quote(base + '/candidate.gds')}")
    if hashlib.sha256(gds).hexdigest() != manifest["gds"]["sha256"]:
        raise ValueError("Fetched stream differs from the manifest")
    (dest / "candidate.gds").write_bytes(gds)
    return dest


SI = {"a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9}


def value(text):
    m = re.fullmatch(r"([-+0-9.eE]+)(meg|[afpnumkg])?", text, re.I)
    return float(m[1]) * SI.get((m[2] or "").lower(), 1.0)


def statements(text):
    """Spectre statements with backslash continuations joined; escapes removed."""
    parts = []
    for line in text.splitlines():
        line = line.rstrip()
        if line.endswith("\\"):
            parts.append(line[:-1])
            continue
        parts.append(line)
        yield " ".join(parts).replace("\\", "").strip()
        parts = []


def read_netlist(base, wanted=None):
    """The xcell extraction in base (extracted.scs, .pex, .pxi): per net its RC body (resistors, capacitors to node 0)
    with the formal ports bound to the top-level nodes, and every top-level device (the xcells' own devices on ideal
    internal nets) with its nodes, model, parameters and location. wanted: net names to keep (None keeps all)."""
    nets, cur = {}, None
    elem = re.compile(r"^(\S+) \( *(\S+) (\S+) *\) (resistor|capacitor) [rc]=(\S+)")
    for st in statements((base / "extracted.scs.pex").read_text(encoding="ascii")):
        if st.startswith("subckt "):
            m = re.match(r"subckt PM_[^%]+%(\S+) \( (.*) \)$", st)
            cur = dict(formal=m[2].split(), r=[], c=[]) if wanted is None or m[1] in wanted else None
            if cur is not None:
                nets[m[1]] = cur
        elif st.startswith("ends"):
            cur = None
        elif cur is not None:
            m = elem.match(st)
            if m:
                (cur["r"] if m[4] == "resistor" else cur["c"]).append((m[2], m[3], value(m[5])))
    pxi = next(base.glob("extracted.scs.*.pxi"))
    for st in statements(pxi.read_text(encoding="ascii")):
        m = re.match(r"^x_PM_[^%]+%(\S+) \( (.*) \) +PM_", st)
        if m and m[1] in nets:
            actual = m[2].split()
            if len(actual) != len(nets[m[1]]["formal"]):
                raise ValueError("Port count differs for " + m[1])
            nets[m[1]]["bind"] = dict(zip(nets[m[1]]["formal"], actual))
    devices = []
    dev = re.compile(r"^(\S+) \( (.*?) \) (\S+)(.*?)(?: //x=(\S+) //y=(\S+))?$")
    for st in statements((base / "extracted.scs").read_text(encoding="ascii")):
        if not st or st.startswith(("//", "subckt", "ends", "simulator", "include", "x_PM_")):
            continue
        m = dev.match(st)
        if m and m[5]:
            params = dict(re.findall(r"(\w+)=(\S+)", m[4]))
            devices.append(dict(name=m[1], nodes=m[2].split(), model=m[3], params=params,
                                xy=(float(m[5]), float(m[6]))))
    return nets, devices


def locator(devices):
    """Where the xcell an attachment node belongs to lies: the bounding box of the top-level devices under the longest
    instance path prefix of the node that has any (the xcells' own devices and well diodes carry LOCATION)."""
    import numpy as np
    by = {}
    for d in devices:
        path = d["name"][1:].split("/")
        for k in range(1, len(path)):
            by.setdefault("/".join(path[:k]), []).append(d["xy"])
    by = {k: np.array(v) for k, v in by.items()}

    def where(node):
        path = node.split(":")[0].split("/")
        for k in range(len(path) - 1, 0, -1):
            xy = by.get("/".join(path[:k]))
            if xy is not None:
                return tuple(float(v) for v in (*xy.min(0), *xy.max(0)))
        return None
    return where


def classify(box, ring):
    """Owner of an attachment from its device box (die um): the ADC core, a reserved region (register, clamps, decaps)
    or the pad position whose cell holds it."""
    if box is None:
        return None
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    (ax0, ay0), (ax1, ay1) = ring["adc_placement"]["bbox_um"]
    if ax0 <= cx <= ax1 and ay0 <= cy <= ay1:
        return "core"
    # Clamps first: the analog clamp region lies inside the analog decap's bounding box.
    for kind in ("clamp", "digital", "decap"):
        for r in ring["reserved_regions"]:
            b = r.get("bbox")
            if b and r.get("kind") == kind and b[0][0] <= cx <= b[1][0] and b[0][1] <= cy <= b[1][1]:
                return r["id"]
    (ox0, oy0), (ox1, oy1) = ring["ring_opening"]
    if ox0 <= cx <= ox1 and oy0 <= cy <= oy1:
        return "opening"
    best = min(ring["pads"], key=lambda p: abs(p["bond_pad_center_um"][0] - cx) + abs(p["bond_pad_center_um"][1] - cy))
    return best["position"]


class Network:
    """The resistor graph of one extracted net (its formal nodes; node 0 is the ground of the capacitors)."""

    def __init__(self, net):
        import numpy as np
        names = sorted({a for a, b, _ in net["r"]} | {b for a, b, _ in net["r"]} | {a for a, _, _ in net["c"]}
                       | set(net["formal"]) - {"0"})
        self.index = {n: k for k, n in enumerate(names)}
        self.n = len(names)
        self.i = np.array([self.index[a] for a, _, _ in net["r"]], dtype=np.int64)
        self.j = np.array([self.index[b] for _, b, _ in net["r"]], dtype=np.int64)
        self.g = 1.0 / np.maximum(np.array([r for _, _, r in net["r"]]), 1e-9)
        self.cap = np.zeros(self.n)
        for a, b, c in net["c"]:
            if b != "0":
                raise ValueError("Coupling capacitor in a net body")
            self.cap[self.index[a]] += c

    def resistance(self, a, b):
        """Two-point resistance between node sets a and b (each shorted), the other nodes floating."""
        a = [self.index[x] for x in a]
        x = self._solve(a, [self.index[v] for v in b], {a[0]: 1.0})
        return float(x[a[0]])

    def distributed(self, a, sinks):
        """Resistance from node set a (shorted) to current sinks spread over nodes in proportion to their weights
        (sinks: formal node -> weight): unit current out at the sinks, a at 0 V; the power-weighted mean drop."""
        a = [self.index[x] for x in a]
        total = sum(sinks.values())
        share = {}
        for f, w in sinks.items():
            share[self.index[f]] = share.get(self.index[f], 0.0) + w / total
        x = self._solve([a[0]], a, {k: -v for k, v in share.items()})
        return float(-sum(v * x[k] for k, v in share.items()))

    def _solve(self, merged, fixed, injection, tol=1e-12, limit=200000):
        """Node voltages for current injection {node: A} with the nodes in fixed shorted at 0 V (merged: nodes shorted
        to merged[0]), Jacobi-preconditioned conjugate gradients on the Laplacian."""
        import numpy as np
        merge = np.arange(self.n)
        merge[merged] = merged[0]
        merge[fixed] = fixed[0]
        i, j = merge[self.i], merge[self.j]
        keep = i != j
        i, j, g = i[keep], j[keep], self.g[keep]
        n = self.n
        deg = np.bincount(i, g, n) + np.bincount(j, g, n)
        free = np.ones(n, bool)
        free[fixed[0]] = False
        free &= deg > 0

        def mv(x):
            y = deg * x - np.bincount(i, g * x[j], n) - np.bincount(j, g * x[i], n)
            return np.where(free, y, 0.0)
        rhs = np.zeros(n)
        for k, v in injection.items():
            rhs[merge[k]] += v
        rhs[~free] = 0.0
        x = np.zeros(n)
        r = rhs.copy()
        pre = np.where(free, 1.0 / np.where(deg > 0, deg, 1.0), 0.0)
        z = pre * r
        p = z.copy()
        rz = r @ z
        for k in range(limit):
            q = mv(p)
            pq = p @ q
            if not pq > 0:
                raise ValueError("The two node sets are not connected")
            alpha = rz / pq
            x += alpha * p
            r -= alpha * q
            if np.sqrt(r @ r) < tol:
                break
            z = pre * r
            rz_new = r @ z
            p = z + rz_new / rz * p
            rz = rz_new
        else:
            raise RuntimeError("No convergence")
        return x[merge]

    def split(self, cut):
        """Pieces of the net left when the formal nodes in cut are removed: per piece its capacitance (F), its nodes
        and the cut nodes it touches. The capacitance on a cut node itself goes to no piece."""
        cutset = {self.index[x]: x for x in cut}
        parent = list(range(self.n))

        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u
        for a, b in zip(self.i.tolist(), self.j.tolist()):
            if a in cutset or b in cutset:
                continue
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        pieces = {}
        for u in range(self.n):
            if u not in cutset:
                p = pieces.setdefault(find(u), dict(f=0.0, nodes=set(), touches=set()))
                p["f"] += float(self.cap[u])
                p["nodes"].add(u)
        for a, b in zip(self.i.tolist(), self.j.tolist()):
            for c, o in ((a, b), (b, a)):
                if c in cutset and o not in cutset:
                    pieces[find(o)]["touches"].add(cutset[c])
        return list(pieces.values()), sum(float(self.cap[u]) for u in cutset)


# Junction diode model cards of the PDB3AC ESD diodes (PDK models/spectre/cln28ull_1d8_elk_v1d8_3.scs, ndio_18 and
# pdio_18, TT: cj_d_18 = cjsw_d_18 = 1, SS/FF 1.07/0.93): area F/m2, sidewall F/m, built-in V, grading.
DIODE = dict(ndio_18=dict(cj=1.4562e-3, cjsw=1.0211e-10, pb=0.5, php=0.6, mj=0.24, mjsw=0.085),
             pdio_18=dict(cj=1.318e-3, cjsw=8.1e-11, pb=0.743, php=0.2085, mj=0.3181, mjsw=0.0428))
SUPPLY_V = dict(AVDD=0.9, TACVDD=0.9, AVSS=0.0, TACVSS=0.0, VSS=0.0)


def junction_f(spice_body, node_v):
    """Junction capacitance of the diodes of one pad subcircuit (its LVS/foundry SPICE) at the given node voltages:
    C = area * cj / (1 + Vr/pb)^mj + pj * cjsw / (1 + Vr/php)^mjsw per diode, Vr = V(cathode) - V(anode)."""
    total = 0.0
    for line in spice_body.splitlines():
        t = line.split()
        if not t or t[0][:1].upper() != "D":
            continue
        anode, cathode, model = t[1], t[2], t[3]
        p = dict(kv.split("=") for kv in t[4:] if "=" in kv)
        m = DIODE[model]
        vr = max(node_v[cathode] - node_v[anode], 0.0)
        total += float(p.get("m", 1)) * (float(p["area"]) * m["cj"] / (1 + vr / m["pb"]) ** m["mj"]
                                         + float(p["pj"]) * m["cjsw"] / (1 + vr / m["php"]) ** m["mjsw"])
    return total


def partial_h(length_um, width_um, thickness_um):
    """Partial self-inductance of a straight rectangular bar (Grover), H; the routes' L is not extracted."""
    l, s = length_um * 1e-6, (width_um + thickness_um) * 1e-6
    return 2e-7 * l * (math.log(2 * l / s) + 0.5 + 0.2235 * s / l)


def pad_bodies():
    """The pad subcircuits of the IO library SPICE fetched into work/ (the netlist the chip LVS includes)."""
    text = (WORK / "io_spice/io_library.spi").read_text(encoding="latin1")
    return {m.group(1): m.group(0) for m in re.finditer(r"(?ims)^\.subckt[ \t]+(\S+).*?^\.ends[^\n]*", text)}


def ring_cells(gds):
    """Pad position -> IO cell of the ring in the chip stream (by the reference that holds the pad's core pin)."""
    import gdstk
    ring = json.loads((ROOT / "Layout/design/io_ring.json").read_bytes())
    lib = gdstk.read_gds(str(gds))
    refs = [r for r in next(c for c in lib.cells if c.name == "sar8_io_ring").references
            if r.cell.name.startswith("P") and not r.cell.name.startswith(("PFILLER", "PCORNER", "PRCUT", "PAD60"))]
    side_point = dict(left=lambda x, y: (55.0, y), right=lambda x, y: (705.0, y), top=lambda x, y: (x, 705.0),
                      bottom=lambda x, y: (x, 55.0))
    out = {}
    for p in ring["pads"]:
        px, py = side_point[p["position"].split("_")[0]](*p["bond_pad_center_um"])
        hits = [r.cell.name for r in refs if r.bounding_box()[0][0] <= px <= r.bounding_box()[1][0]
                and r.bounding_box()[0][1] <= py <= r.bounding_box()[1][1]]
        if len(hits) == 1:
            out[p["position"]] = hits[0]
    return out


class Extraction:
    """The parsed chip periphery extraction with the owner of every attachment node."""

    def __init__(self, identity):
        self.base = WORK / identity
        self.manifest = json.loads((self.base / "manifest.json").read_bytes())
        if not self.manifest.get("done") or self.manifest.get("error"):
            raise ValueError("Extraction incomplete: " + identity)
        for name, digest in [("extracted.scs", self.manifest["checks"]["pex"]["sha256"])] + \
                sorted(self.manifest["checks"]["pex"]["companion_sha256"].items()):
            if hashlib.sha256((self.base / "pex" / name).read_bytes()).hexdigest() != digest:
                raise ValueError("Extraction file differs from its manifest: " + name)
        self.ring = json.loads((ROOT / "Layout/design/io_ring.json").read_bytes())
        self.nets, self.devices = read_netlist(self.base / "pex")
        where = locator(self.devices)
        self.att = {}
        for name, n in self.nets.items():
            self.att[name] = {f: (a, "label" if not a.startswith("X") else classify(where(a), self.ring))
                              for f, a in n["bind"].items() if f != "0" and not a.startswith("N_")}
        self._net = {}

    def network(self, name):
        if name not in self._net:
            self._net[name] = Network(self.nets[name])
        return self._net[name]

    def nodes(self, name, owner):
        out = [f for f, (_, o) in self.att[name].items() if o == owner]
        if not out:
            raise ValueError(f"{name}: nothing on {owner}; attachments {self.att[name]}")
        return out

    def r(self, name, a, b):
        return self.network(name).resistance(self.nodes(name, a) if isinstance(a, str) else a,
                                             self.nodes(name, b) if isinstance(b, str) else b)

    def split(self, name, cut):
        """Pieces of the net between the cut attachments: per piece its capacitance (F), the owners of the attachments
        it holds and the owners of the cut attachments it touches."""
        net = self.network(name)
        pieces, on_cut = net.split(cut)
        owner = {net.index[f]: o for f, (_, o) in self.att[name].items()}
        for p in pieces:
            p["owners"] = {owner[u] for u in p["nodes"] if u in owner}
            p["touches"] = {self.att[name][f][1] for f in p.pop("touches")}
            del p["nodes"]
        return pieces, on_cut

    def total_f(self, name):
        return float(self.network(name).cap.sum())


MOS_PINS = dict(d=0, g=1, s=2, b=3)


def register_bit(devices, net, prefix, targets):
    """Bit of an output-register input net: the xcell devices sit on the top-level net names, so follow the register's
    transistors (instance path prefix) from the net (gate to drain/source, and across drain/source) without crossing
    the supply and clock nets, to the net of a Q output (targets: net -> bit)."""
    mos = [d for d in devices if len(d["nodes"]) == 4 and d["name"][1:].startswith(prefix + "/")]
    stop = {"DVDD", "VSS", "SAMPLE_CORE"}
    by_node = {}
    for d in mos:
        for n in d["nodes"][:3]:
            by_node.setdefault(n, []).append(d)
    seen, todo = set(), [net]
    while todo:
        n = todo.pop()
        if n in seen or n in stop:
            continue
        seen.add(n)
        if n in targets:
            return targets[n]
        for d in by_node.get(n, []):
            dn, gn, sn = d["nodes"][:3]
            todo += [dn, sn] if n == gn else [sn if n == dn else dn]
    raise ValueError("No register output reached from " + net)


def bond_and_route(x, net, pad, far):
    """Pad-cell attachment to the far end (route R), bond label to the pad-cell attachment (bond-pad metal R), and the
    wiring capacitance on the bond side and the route side of the pad-cell attachment."""
    pads = x.nodes(net, pad)
    pieces, on_cut = x.split(net, pads)
    bond = sum(p["f"] for p in pieces if "label" in p["owners"])
    route = sum(p["f"] for p in pieces if "label" not in p["owners"])
    labels = x.nodes(net, "label")
    return dict(route_ohm=x.r(net, pad, far) if far != "label" else None,
                bond_ohm=x.network(net).resistance(labels, pads),
                bond_pad_metal_f=bond, route_f=route, on_pad_node_f=on_cut, total_wiring_f=x.total_f(net))


def analyze(identity):
    """Comparison of the extraction with constraints.json stage6_supply_model and the hand ring-feed model."""
    from Layout.tools.analysis import ring_supply as rs
    from Layout.tools.analysis.chip_objects_record import FEED_FROM_PORT, FEED_SEGMENTS, ring_feed
    x = Extraction(identity)
    ring = x.ring
    model = json.loads((ROOT / "Layout/specs/constraints.json").read_bytes())["stage6_supply_model"]
    cells = ring_cells(x.base / "candidate.gds") if (x.base / "candidate.gds").exists() else {}
    bodies = pad_bodies()
    routes = ring["routes"]
    # Reference routes: both pads of one rail on one extracted net; the core node splits the two routes.
    ref = {}
    for rail in ("VREFP", "VREFN"):
        vr = dict(SUPPLY_V, AIO=0.9 if rail == "VREFP" else 0.0)
        per = {}
        pads = {routes[k]["from"]: k for k in (rail + "_a", rail + "_b")}
        allpads = [f for p in pads for f in x.nodes(rail, p)]
        pieces, on_cut = x.split(rail, allpads + x.nodes(rail, "core"))
        for pos, key in sorted(pads.items(), key=lambda kv: kv[1]):
            cell = cells[pos]
            per[key] = dict(
                pad=pos, cell=cell, length_um=routes[key]["manhattan_length_um"],
                route_ohm=x.network(rail).resistance(x.nodes(rail, pos), x.nodes(rail, "core")),
                route_f=sum(p["f"] for p in pieces if p["touches"] == {pos, "core"}),
                bond_pad_metal_f=sum(p["f"] for p in pieces if p["touches"] == {pos} and "label" in p["owners"]),
                pad_cell_junction_f=junction_f(bodies[cell], vr),
                route_h_estimate=partial_h(routes[key]["manhattan_length_um"], 4.0, 0.85))
        unassigned = [p for p in pieces if p["touches"] not in [{pos, "core"} for pos in pads] + [{pos} for pos in pads]]
        both = x.network(rail).resistance(allpads, x.nodes(rail, "core"))
        a, b = per[rail + "_a"], per[rail + "_b"]
        ref[rail] = dict(routes=per, parallel_route_ohm=both,
                         parallel_route_h_estimate=a["route_h_estimate"] * b["route_h_estimate"]
                         / (a["route_h_estimate"] + b["route_h_estimate"]),
                         bond_pad_metal_f=a["bond_pad_metal_f"] + b["bond_pad_metal_f"], route_f=a["route_f"] + b["route_f"],
                         on_attachment_nodes_f=on_cut, other_f=sum(p["f"] for p in unassigned),
                         pad_cell_junction_f=a["pad_cell_junction_f"] + b["pad_cell_junction_f"],
                         total_wiring_f=x.total_f(rail), node_v=vr["AIO"])
    hand = rs.reference_routes(ring)
    # VIN path.
    vin = {}
    for net in ("VINP", "VINN"):
        pos = routes[net]["from"]
        cell = cells.get(pos, "PDB3AC_V_G")
        d = bond_and_route(x, net, pos, "core")
        d.update(pad=pos, cell=cell, length_um=routes[net]["manhattan_length_um"],
                 pad_cell_junction_f={f"{v} V": junction_f(bodies[cell], dict(SUPPLY_V, AIO=v)) for v in (0.0, 0.45, 0.9)},
                 route_h_estimate=partial_h(routes[net]["manhattan_length_um"], 1.0, 0.09))
        vin[net] = d
    # Supply branches: AVDD on its own net per branch, AVSS on one net (the guard ring joins the branches).
    avdd = {}
    for name in [n for n in x.nets if n.startswith("AVDD_CORE")]:
        pad = next(o for _, o in x.att[name].values() if o and re.match(r"(top|left|right|bottom)_\d", o))
        avdd[pad] = name
    branch_pads = {b: (routes["AVDD_" + b]["from"], routes["AVSS_" + b]["from"]) for b in ("analog", "pair", "sar")}
    decap = {"analog": "analog_pad_decap", "pair": "pair_pad_decap", "sar": "sar_pad_decap"}
    clamp = {"analog": "pclampc_analog", "pair": "pclampc_pair", "sar": "pclampc_sar"}
    feeds = {}
    hand_feed = ring_feed()
    for b, (pd, ps) in branch_pads.items():
        r = {}
        for rail, net, pad in (("AVDD", avdd[pd], pd), ("AVSS", "AVSS_CORE", ps)):
            pp, bp, pb = x.r(net, pad, "core"), x.r(net, decap[b], "core"), x.r(net, pad, decap[b])
            # Star of the three: pad -- J -- pin with the decap port on J (Layout/tools/simulation/prepare_stage6.star).
            r_pad, r_bulk, r_pin = (pb + pp - bp) / 2, (pb + bp - pp) / 2, (pp + bp - pb) / 2
            r[rail] = dict(net=net, pad=pad, pad_to_pin_ohm=pp, bulk_to_pin_ohm=bp, pad_to_bulk_ohm=pb,
                           star_ohm=dict(pad=r_pad, decap=r_bulk, pin=r_pin), pad_to_clamp_ohm=x.r(net, pad, clamp[b]))
        hand25 = {k: sum(rs.rsh(l, 25, False) * ln / w for l, ln, w in segs) for k, segs in FEED_SEGMENTS[b].items()}
        bulk25 = {k: sum(rs.rsh(l, 25, False) * ln / w for l, ln, w in segs) for k, segs in FEED_FROM_PORT[b].items()}
        scale = {k: rs.rsh(segs[0][0], 125, True) / rs.rsh(segs[0][0], 25, False) for k, segs in FEED_SEGMENTS[b].items()}
        feeds[b] = dict(rails=r,
                        loop_pad_to_pin_ohm=r["AVDD"]["pad_to_pin_ohm"] + r["AVSS"]["pad_to_pin_ohm"],
                        loop_bulk_to_pin_ohm=r["AVDD"]["bulk_to_pin_ohm"] + r["AVSS"]["bulk_to_pin_ohm"],
                        loop_pad_to_pin_ohm_125c_rcworst_scaled=sum(r[k]["pad_to_pin_ohm"] * scale[k] for k in r),
                        loop_bulk_to_pin_ohm_125c_rcworst_scaled=sum(r[k]["bulk_to_pin_ohm"] * scale[k] for k in r),
                        hand_25c=dict(pad_to_pin_ohm=sum(hand25.values()), bulk_to_pin_ohm=sum(bulk25.values())),
                        hand_125c_rcworst=dict(pad_to_pin_ohm=hand_feed[b]["pad_to_pin_ohm"],
                                               bulk_to_pin_ohm=hand_feed[b]["bulk_to_pin_ohm"]))
    # Output path.
    out = {}
    for k in range(8):
        pos = routes[f"D{k}"]["to"]
        pad = bond_and_route(x, f"D{k}", pos, "label")
        core = dict(route_ohm=x.r(f"D{k}_CORE", "output_register", pos), total_wiring_f=x.total_f(f"D{k}_CORE"))
        out[f"D{k}"] = dict(pad=pos, cell=cells.get(pos), pad_net=pad, register_to_pad=core)
    adc = {}
    for name in [n for n in x.nets if n.isdigit()]:
        o = {v for _, v in x.att[name].values()}
        if o == {"core", "output_register"}:
            # The unnamed core-to-register nets: the bit is the register output its D input reaches.
            prefix = x.att[name][x.nodes(name, "output_register")[0]][0].split("/")[0]
            bit = register_bit(x.devices, name, prefix, {f"D{k}_CORE": k for k in range(8)})
            adc[f"ADC_D{bit}"] = dict(net=name, route_ohm=x.r(name, "core", "output_register"),
                                      total_wiring_f=x.total_f(name))
    if sorted(adc) != [f"ADC_D{k}" for k in range(8)]:
        raise ValueError("Cannot map the ADC_D nets: %s" % sorted(adc))
    # Register supplies: the DVDD pads' ring node (the pads' VDD pins, ideal inside the IO cells) over the drawn DVDD
    # route, and VSS from the ring node over VSS_register and the core VSS ring.
    net = "DVDD"
    ringnode = [f for f, (a, o) in x.att[net].items() if re.match(r"(top|left|right|bottom)_\d", o or "")
                and not a.endswith(":g") and a.startswith("X")]
    reg, dec = x.nodes(net, "output_register"), x.nodes(net, "dvdd_decap")
    pr, dr, pd_ = (x.network(net).resistance(ringnode, reg), x.network(net).resistance(dec, reg),
                   x.network(net).resistance(ringnode, dec))
    supply = dict(DVDD=dict(ring_nodes=[x.att[net][f][0] for f in ringnode], ring_to_register_ohm=pr,
                            decap_to_register_ohm=dr, ring_to_decap_ohm=pd_,
                            star_ohm=dict(ring=(pd_ + pr - dr) / 2, decap=(pd_ + dr - pr) / 2, register=(pr + dr - pd_) / 2),
                            total_wiring_f=x.total_f(net)),
                  VSS=dict(note="Not resolved: the extraction joins the VSS of every xcell (pads, register, core) at one "
                                "substrate node, so the VSS_register route ends on the same node as the VSS pads.",
                           attachments=sorted({o for _, o in x.att["VSS"].values()})))
    pos = routes["SAMPLE"]["from"]
    sample = dict(pad=pos, cell=cells.get(pos), pad_net=bond_and_route(x, "SAMPLE", pos, "label"),
                  pad_to_core_ohm=x.r("SAMPLE_CORE", pos, "core"),
                  pad_to_register_ohm=x.r("SAMPLE_CORE", pos, "output_register"),
                  total_wiring_f=x.total_f("SAMPLE_CORE"))
    return dict(x=x, reference=ref, reference_model=dict(route=model["package_per_pin"]["reference_rail"]["pad_to_core_route"],
                                                         pad_F=model["package_per_pin"]["pad_F"], hand=hand),
                vin=vin, feeds=feeds, output=out, adc_d=adc, sample=sample, register_supply=supply, pad_cells=cells)


def clamp_bus(identity):
    """ESD bus from each analog pad to its PCLAMPC_H_G (app note Table 10.1: at most 1 ohm), on an extraction with the
    clamps flattened (launch --flatten PCLAMPC_H_G), so the bars, the clamp's M3 terminal strips and its devices are
    in the network. Per rail: to the clamp's device terminals shorted (pin), and with the clamp current drawn by its
    transistors in proportion to their width (distributed; includes the clamp's own metal down to each finger)."""
    x = Extraction(identity)
    routes = x.ring["routes"]
    dev = {d["name"][1:]: d for d in x.devices}
    avdd = {}
    for name in [n for n in x.nets if n.startswith("AVDD_CORE")]:
        pad = next((o for _, o in x.att[name].values() if o and re.match(r"(top|left|right)_\d", o)), None)
        if pad:
            avdd[pad] = name
    # A flattened device's terminal on an extracted net is a port node N_<net>_<device path>_<pin> of the net body.
    term = re.compile(r"^N_.*?_((?:X\d+/)+[A-Za-z]+\d+)_([a-z]+)$")
    out = {}
    for b in ("analog", "pair", "sar"):
        out[b] = {}
        for rail, pad in (("AVDD", routes["AVDD_" + b]["from"]), ("AVSS", routes["AVSS_" + b]["from"])):
            net = avdd[pad] if rail == "AVDD" else "AVSS_CORE"
            sinks = {}
            for f, a in x.nets[net]["bind"].items():
                m = term.match(a)
                d = dev.get(m[1]) if m and m[2] in ("d", "s") else None
                if d and len(d["nodes"]) == 4 and "w" in d["params"] and \
                        classify((*d["xy"], *d["xy"]), x.ring) == f"pclampc_{b}":
                    p = d["params"]
                    sinks[f] = value(p["w"]) * float(p.get("nf", 1)) * float(p.get("m", 1))
            nw = x.network(net)
            pads = x.nodes(net, pad)
            weighted = {f: w for f, w in sinks.items() if w > 0}
            out[b][rail] = dict(net=net, pad=pad, clamp_terminals=len(sinks), weighted_transistors=len(weighted),
                                pin_ohm=nw.resistance(pads, list(sinks)),
                                distributed_ohm=nw.distributed(pads, weighted) if weighted else None)
    return out


def rc_subckt(x, net, name, ports):
    """Spectre subcircuit of one extracted net body: ports [(port, owner)] bind the formal nodes of that owner's
    attachments (several attachments of one owner join on its port); node 0 becomes SUB; the rest stay local."""
    n = x.nets[net]
    bind = {}
    for port, owner in ports:
        for f in x.nodes(net, owner):
            bind[f] = port
    m = lambda v: "SUB" if v == "0" else bind.get(v, "n" + v)
    out = [f"subckt {name} ({' '.join(p for p, _ in ports)} SUB)"]
    out += [f"r{k} ({m(a)} {m(b)}) resistor r={max(r, 1e-6):.6g}" for k, (a, b, r) in enumerate(n["r"])]
    out += [f"c{k} ({m(a)} {m(b)}) capacitor c={c:.6g}" for k, (a, b, c) in enumerate(n["c"])]
    out.append(f"ends {name}")
    return "\n".join(out)


def stage2_netlists(identity, res, dest):
    """Two Spectre netlists for Stage 2 from the extraction and the analysis: the VIN path (PDB3AC pad cells and the
    two pad-to-core routes) and the output path (register, D0-D7 and SAMPLE pad cells, their routes and supplies)."""
    from Layout.design.chip_objects import IO_SPICE, io_library
    x = res["x"]
    cells = res["pad_cells"]
    obj = json.loads((ROOT / "Layout/results/chip_objects.json").read_bytes())
    dec = obj["geometry_r2"]["decap_dvdd"]
    esr = sum(v["total_ohm"] for k, v in dec["esr_upper_bound_per_rail"].items() if "#" not in k and "parallel" not in k)
    spice = IO_SPICE.format(lib=io_library())
    head = (f"// From the xcell extraction {identity} of {x.manifest['top']} (stream sha256 {x.manifest['gds']['sha256']}),\n"
            f"// Calibre xRC typical, 25 C, coupling capacitance grounded; Layout/tools/analysis/chip_periphery.py.\n"
            f"// Pad cells: the IO library SPICE the chip LVS compares against (devices incl. ESD diodes, no parasitics).\n"
            "simulator lang=spice\n"
            f'.include "{spice}"\n'
            "simulator lang=spectre\n")
    dest.mkdir(parents=True, exist_ok=True)
    vin = [head, "// VIN path: bond-pad metal, PDB3AC (AIO TACVDD TACVSS VSS) and the M5/M6 route to the core VIN pin.",
           "// Ports: VINP_BOND/VINN_BOND bond-pad nodes (package here), VINP/VINN core pins, AVDD/AVSS the pads'",
           "// TACVDD/TACVSS bus, VSS, SUB the extraction ground (tie to AVSS/VSS).",
           "subckt sar8_vin_path (VINP_BOND VINN_BOND VINP VINN AVDD AVSS VSS SUB)"]
    for net in ("VINP", "VINN"):
        pos = res["vin"][net]["pad"]
        vin += [f"XPAD_{net} ({net}_AIO AVDD AVSS VSS) {cells[pos]}",
                f"XRC_{net} ({net}_BOND {net}_AIO {net} SUB) rc_{net.lower()}"]
    vin.append("ends sar8_vin_path")
    for net in ("VINP", "VINN"):
        vin.append(rc_subckt(x, net, f"rc_{net.lower()}", [("BOND", "label"), ("AIO", res["vin"][net]["pad"]),
                                                            ("CORE", "core")]))
    (dest / "sar8_vin_path.scs").write_text("\n".join(vin) + "\n", encoding="ascii", newline="\n")
    sup = res["register_supply"]["DVDD"]["star_ohm"]
    o = [head, '// Output register: design/chip/output_register.scs (include it; its standard cells as in its timing runs).',
         "// Output path: ADC_D0-7 core pins -> register -> D0_CORE-D7_CORE -> PRUW08SDGZ -> bond pads D0-D7;",
         "// SAMPLE bond pad -> PDDW16SDGZ -> SAMPLE_CORE -> core SAMPLE pin and register CK.",
         "// Ports: ADC_D0-7 and SAMPLE_ADC the core pins; D0_BOND-D7_BOND, SAMPLE_BOND bond-pad nodes (package and",
         "// board here, sar8_output_board); DVDD VSS VDDIO VSSIO POC the ring buses (ideal inside the pad cells;",
         "// POC low in normal operation); SUB the extraction ground (tie to VSS).",
         "subckt sar8_output_path (" + " ".join([f"ADC_D{k}" for k in range(8)] + ["SAMPLE_ADC"]
                                                + [f"D{k}_BOND" for k in range(8)]
                                                + ["SAMPLE_BOND", "DVDD", "VSS", "VDDIO", "VSSIO", "POC", "SUB"]) + ")"]
    for k in range(8):
        o.append(f"XADC{k} (ADC_D{k} D{k}_REG SUB) rc_adc_d{k}")
    o.append("XOREG (" + " ".join([f"D{k}_REG" for k in range(8)] + [f"Q{k}" for k in range(8)]
                                   + ["CK_REG", "DVDD_REG", "VSS"]) + ") sar8_out_reg")
    o += [f"// Register DVDD: the DVDD pads' bus over the drawn 4 um M6 route (extracted star; the DVDD decap on the",
          f"// junction: {dec['capacitance_pF']} pF nmoscap as an ideal capacitor with its {esr:.2f} ohm drawn ESR model).",
          f"// Register VSS: ideal (the extraction joins every xcell's VSS at one substrate node).",
          f"RDVDD_RING (DVDD DVDD_J) resistor r={sup['ring']:.4g}",
          f"RDVDD_REG (DVDD_J DVDD_REG) resistor r={sup['register']:.4g}",
          f"RDVDD_DEC (DVDD_J DVDD_DEC) resistor r={max(sup['decap'], 0) + esr:.4g}",
          f"CDVDD_DEC (DVDD_DEC VSS) capacitor c={dec['capacitance_pF']}p"]
    for k in range(8):
        pos = res["output"][f"D{k}"]["pad"]
        # PRUW08SDGZ pins: C I OEN PAD POC REN VDD VDDPST VSS VSSPST (io_ring.json: OEN=VSS, REN=DVDD, C open)
        o += [f"XD{k}CORE (Q{k} D{k}_I SUB) rc_d{k}_core",
              f"XPAD_D{k} (D{k}_C_OPEN D{k}_I VSS D{k}_PAD POC DVDD DVDD VDDIO VSS VSSIO) {cells[pos]}",
              f"XD{k}PAD (D{k}_PAD D{k}_BOND SUB) rc_d{k}_pad"]
    spos = res["sample"]["pad"]
    # PDDW16SDGZ: C=SAMPLE_CORE, I=VSS, OEN=DVDD, REN=VSS
    o += ["XSAMPLE_CORE (SAMPLE_C SAMPLE_ADC CK_REG SUB) rc_sample_core",
          f"XPAD_SAMPLE (SAMPLE_C VSS DVDD SAMPLE_PAD POC VSS DVDD VDDIO VSS VSSIO) {cells[spos]}",
          "XSAMPLE_PAD (SAMPLE_PAD SAMPLE_BOND SUB) rc_sample_pad",
          "ends sar8_output_path"]
    for k in range(8):
        pos = res["output"][f"D{k}"]["pad"]
        o.append(rc_subckt(x, res["adc_d"][f"ADC_D{k}"]["net"], f"rc_adc_d{k}", [("CORE", "core"), ("D", "output_register")]))
        o.append(rc_subckt(x, f"D{k}_CORE", f"rc_d{k}_core", [("Q", "output_register"), ("I", pos)]))
        o.append(rc_subckt(x, f"D{k}", f"rc_d{k}_pad", [("PAD", pos), ("BOND", "label")]))
    o.append(rc_subckt(x, "SAMPLE_CORE", "rc_sample_core", [("PADC", spos), ("CORE", "core"), ("CK", "output_register")]))
    o.append(rc_subckt(x, "SAMPLE", "rc_sample_pad", [("PAD", spos), ("BOND", "label")]))
    pk = json.loads((ROOT / "Layout/specs/constraints.json").read_bytes())["stage6_supply_model"]["package_per_pin"]
    o += ["// Package and board (stated load; change the parameters): per pad the constraints.json package_per_pin",
          f"// series {pk['series_ohm']} ohm + {pk['series_H'] * 1e9:g} nH, then cload to the board ground. SAMPLE_SRC drives SAMPLE.",
          "subckt sar8_output_board (" + " ".join([f"D{k}_BOND" for k in range(8)]
                                                  + [f"D{k}_BOARD" for k in range(8)]
                                                  + ["SAMPLE_BOND", "SAMPLE_SRC", "GND_BOARD"]) + ")",
          f"parameters cload=15p rpkg={pk['series_ohm']} lpkg={pk['series_H']:g}"]
    for k in range(8):
        o += [f"RPKG{k} (D{k}_BOND D{k}_PK) resistor r=rpkg", f"LPKG{k} (D{k}_PK D{k}_BOARD) inductor l=lpkg",
              f"CLOAD{k} (D{k}_BOARD GND_BOARD) capacitor c=cload"]
    o += ["RPKGS (SAMPLE_SRC SAMPLE_PK) resistor r=rpkg", "LPKGS (SAMPLE_PK SAMPLE_BOND) inductor l=lpkg",
          "ends sar8_output_board"]
    (dest / "sar8_output_path.scs").write_text("\n".join(o) + "\n", encoding="ascii", newline="\n")
    return {n: hashlib.sha256((dest / n).read_bytes()).hexdigest() for n in ("sar8_vin_path.scs", "sar8_output_path.scs")}


def rounded(o):
    if isinstance(o, dict):
        return {k: rounded(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [rounded(v) for v in o]
    if isinstance(o, float):
        return float("%.4g" % o)
    return o


def report(identity, out="Layout/results/chip_periphery.json"):
    """Layout/results/chip_periphery.json and the Stage 2 netlists (work/, with the extraction)."""
    res = analyze(identity)
    x = res["x"]
    nets = stage2_netlists(identity, res, WORK / identity / "stage2")
    launch_receipt = json.loads((WORK / identity / "launch.json").read_bytes())
    record = dict(
        schema_version=1, tool="Layout/tools/analysis/chip_periphery.py",
        chip_view="SAR_ADC_T28_LAYOUT/sar8_adc_chip/layout_full_fill5_r3_seal",
        extraction=dict(identity=identity, host=launch_receipt["host"], source_evidence=launch_receipt["source_evidence"],
                        stream_sha256=x.manifest["gds"]["sha256"], netlist_sha256=x.manifest["checks"]["pex"]["sha256"],
                        rules="installed Calibre xRC deck (rcx/calibre.rcx), typical, 25 C; -rcc with the coupling "
                              "capacitance grounded in the netlist",
                        xcells=launch_receipt["xcells"], extracted_supplies=launch_receipt["supplies"],
                        not_extracted="inductance (xRC gives R and C); the xcells' insides (pad cells, core, register, "
                                      "decaps, clamps: ideal nets); fill (the chip margin and pad decap areas have none "
                                      "yet, so wiring C will rise)"),
        reference=res["reference"], reference_model=res["reference_model"], vin=res["vin"], supply_feeds=res["feeds"],
        output=res["output"], adc_d=res["adc_d"], sample=res["sample"], register_supply=res["register_supply"],
        pad_cells=res["pad_cells"],
        pad_cell_capacitance_basis="Junction capacitance of the pad cell's diodes in its LVS netlist (IO library SPICE: "
                                   "area, pj) with the PDK ndio_18/pdio_18 model cards at TT (chip_periphery.DIODE) at "
                                   "the node voltage, AVDD 0.9 V; no internal wiring of the cell",
        stage2_netlists=dict(path=f"work/layout/chip-periphery/{identity}/stage2", sha256=nets))
    write_json(ROOT / out, rounded(record))
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("launch")
    a.add_argument("identity")
    a.add_argument("gds", help="the chip stream (a chip check run's fixture.gds)")
    a.add_argument("--source-evidence", required=True, help="the check run the stream comes from")
    a.add_argument("--flatten", nargs="*", default=[], help="object masters to extract instead of keeping as xcells")
    a = sub.add_parser("fetch", help="copy a finished extraction into work/layout/chip-periphery/IDENTITY")
    a.add_argument("identity")
    a = sub.add_parser("report", help="analyse a fetched extraction (work/layout/chip-periphery/IDENTITY)")
    a.add_argument("identity")
    a = sub.add_parser("clamp-bus", help="pad-to-clamp resistance on a fetched extraction with the clamps flattened")
    a.add_argument("identity")
    a.add_argument("--record", metavar="VIEW", help="add the result for chip view VIEW to Layout/results/chip_periphery.json")
    a = ap.parse_args()
    if a.action == "launch":
        print(json.dumps(launch(a.identity, a.gds, a.source_evidence, tuple(a.flatten)), indent=2))
    elif a.action == "fetch":
        print(fetch(a.identity))
    elif a.action == "clamp-bus":
        r = rounded(clamp_bus(a.identity))
        if a.record:
            path = ROOT / "Layout/results/chip_periphery.json"
            rec = json.loads(path.read_bytes())
            bus = rec.setdefault("clamp_bus", dict(
                limit_ohm=1.0, rule="TSMC N28 IO app note Table 10.1: bus resistance from the 3AC pad cells to the "
                                    "clamp's supply pair",
                basis="Calibre xRC typical, 25 C, with PCLAMPC_H_G flattened (chip_periphery.clamp_bus); pin = to the "
                      "clamp's transistor terminals shorted, distributed = the clamp current drawn by its transistors "
                      "in proportion to their width",
                views={}))
            bus["views"][a.record] = dict(extraction=a.identity, rails=r,
                                          worst_distributed_ohm=max(v["distributed_ohm"] for b in r.values() for v in b.values()))
            write_json(path, rec)
        print(json.dumps(r, indent=1))
    else:
        r = report(a.identity)
        print(json.dumps(rounded(dict(reference={k: v["parallel_route_ohm"] for k, v in r["reference"].items()},
                                      feeds={k: (v["loop_pad_to_pin_ohm"], v["loop_bulk_to_pin_ohm"])
                                             for k, v in r["supply_feeds"].items()},
                                      netlists=r["stage2_netlists"])), indent=1))


if __name__ == "__main__":
    main()
