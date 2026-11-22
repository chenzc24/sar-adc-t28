"""Stage 5 fill of the routed ADC core by owner (chenzc24/sar-adc-t28#12, Layout/specs/fill-policy.md).

Every fill pass runs the installed foundry OD/PO and metal utilities (Layout/tools/physical/toplevel_fill_physical.py)
on a seed stream built here with gdstk. A seed carries the context the fill must respect; only the generated fill is
kept. Passes, in the order of the fill-policy plan:

1. `pair-seed`: the XREF/CDAC pair refill. The accepted seed stream se-xref-peripheral-seed, plus the routed core's
   geometry around the pair outline in the pair frame (cell ACF1_PAIR_CONTEXT) and DMnEXCL over every top-level metal
   shape inside the outline, i.e. the route entries (ACF1_PAIR_ENTRY_BLOCK). `fill` runs the utilities inside the
   pair's native boundary and `pair` merges that fill into the unmodified seed and repeats DRC, LVS and xRC.
2. `boot-seed`: one Bootstrap fill cell, generated inside the XBOOTP outline of the core frame. The XBOOTN
   neighbourhood is added mirrored about the axis x 46.115, so the same cell placed MY at x 92.23 also fits XBOOTN.
3. `core-seed`: the routed core with the pair and Bootstrap fill in place and the exclusion cell; the utilities fill
   the core outline outside the exclusions.
4. `library`: the fill hierarchy sar8_adc_core_fill1 (masters sar8_adc_core_fill1_*, children ACF1xx_<hash>) in the
   core frame. `build` streams it into OA and creates the wrapper sar8_adc_core_filled/<view>: XCORE (the routed core
   view, read only), FILL and copies of the core's top-level texts, so extraction names the same nets.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shlex

from Layout.design import toplevel_full_routes, toplevel_routes
from Layout.design.toplevel_route import CADENCE, IDENTITY, STANDARD_LIBRARY, sk, ssh
from Layout.project import ROOT, config, write_json

WORK = ROOT / "work/layout/toplevel-fill"
PHYSICAL = ROOT / "Layout/tools/physical"
FLOORPLAN = ROOT / "Layout/design/floorplan.json"
CORE, CORE_VIEW, CORE_STREAM = "sar8_adc_core", "layout_route_full", "adc-core-full-p2h-chk"
WRAPPER, REVISION = "sar8_adc_core_filled", "fill1"
FILL_TOP = "sar8_adc_core_" + REVISION
PREFIX = "ACF1"


def use_revision(n):
    """Fill revision n: hierarchy sar8_adc_core_fill<n>, children ACF<n>*, wrapper view layout_fill<n>. A new core view
    gets a new revision, so no OA name is ever reused."""
    global REVISION, FILL_TOP, PREFIX
    REVISION, FILL_TOP, PREFIX = f"fill{n}", f"sar8_adc_core_fill{n}", f"ACF{n}"
OWNER = "Layout/design/toplevel_fill.py"
PAIR, PAIR_SEED = "sar8_cdac_with_xref", "se-xref-peripheral-seed"
PAIR_T = (11.715, 42.465)                       # pair native origin in the core (floorplan native_origin_translation)
PAIR_NATIVE = (-1.715, -32.465, 70.515, 25.86)  # pair stream boundary, as in se-xref-peripheral-dense-fill
CORE_BOX = (0.0, 0.0, 122.0, 111.0)
AXIS = 46.115
BLOCK_MASTERS = (PAIR, "sar_strongarm_t28_core", "sar_bootstrap_flat_8b_p_core", "sar8_se_core")
METAL = {n: [(30 + n, 0), (130 + n, 0)] for n in range(1, 8)}
METAL.update({8: [(38, 40), (138, 0)], 9: [(39, 60), (139, 0)]})
LAYER_OF = {lt: n for n, lts in METAL.items() for lt in lts}
EXCL = {n: (150, n) for n in range(1, 10)}
ODBLK, POBLK = (150, 20), (150, 21)
PR_BOUNDARY = 108
ALL = tuple(range(1, 10)) + ("OD", "PO")
CONTEXT_MARGIN = 2.0   # neighbourhood copied into a seed around its fill boundary
ENTRY_MARGIN = 1.0     # DMnEXCL around a top-level metal shape inside the pair outline
ROUTE_MARGIN = 1.0     # DMnEXCL around the comparator channel group and the VIN trunks, layer +-1
CHANNEL_NETS = ("COMP_P", "COMP_N", "CMP_CLK", "SEQ_SAMPLE", "VSS_SHIELD")
REGIONS_ALL = ("top_fill_exclusion_tee", "top_fill_exclusion_inputs", "top_fill_exclusion_n_drop",
               "top_fill_exclusion_p_drop", "comparator_keepout", "comparator_decap_west", "comparator_decap_east")


def gds():
    import gdstk
    return gdstk


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def plan():
    fp = json.loads(FLOORPLAN.read_text(encoding="utf-8"))
    boxes = {b["id"]: (b["origin"][0], b["origin"][1], b["origin"][0] + b["size"][0], b["origin"][1] + b["size"][1])
             for b in fp["blocks"]}
    boxes.update({r["id"]: tuple(r["bbox"][0] + r["bbox"][1]) for r in fp["reserved_regions"]})
    return boxes


def bloat(box, d):
    return (box[0] - d, box[1] - d, box[2] + d, box[3] + d)


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def clip(box, window):
    out = (max(box[0], window[0]), max(box[1], window[1]), min(box[2], window[2]), min(box[3], window[3]))
    return out if out[0] < out[2] and out[1] < out[3] else None


def pair_box():
    b = plan()
    return (min(b["cdac"][0], b["reference"][0]), min(b["cdac"][1], b["reference"][1]),
            max(b["cdac"][2], b["reference"][2]), max(b["cdac"][3], b["reference"][3]))


def read_stream(path, top):
    lib = gds().read_gds(str(path))
    cells = {c.name: c for c in lib.cells}
    if top not in cells:
        raise ValueError(f"{path} has no {top}")
    return lib, cells[top]


def context(top, window, skip=(PAIR,)):
    """Flattened geometry of top without the skipped block instances, clipped to window, by (layer, datatype)."""
    g = gds()
    tmp = g.Cell("ACF1_TMP")
    tmp.add(*top.polygons, *top.paths)
    tmp.add(*[r for r in top.references if r.cell.name not in skip])
    by_layer = {}
    for p in tmp.get_polygons(include_paths=True):
        if p.layer == PR_BOUNDARY:
            continue   # the job's boundary variables, not a copied prBoundary, bound each pass
        (x0, y0), (x1, y1) = p.bounding_box()
        if overlap((x0, y0, x1, y1), window):
            by_layer.setdefault((p.layer, p.datatype), []).append(p)
    rect = g.rectangle(window[:2], window[2:])
    out = []
    for (layer, datatype), polys in sorted(by_layer.items()):
        out += g.boolean(polys, rect, "and", layer=layer, datatype=datatype)
    return out


def exclusion_rects(boxes_by_layers):
    """[(box, layers)] -> gdstk rectangles on DMnEXCL / ODBLK / POBLK."""
    g = gds()
    out = []
    for box, layers in boxes_by_layers:
        for n in layers:
            lt = ODBLK if n == "OD" else POBLK if n == "PO" else EXCL[n]
            out.append(g.rectangle(box[:2], box[2:], layer=lt[0], datatype=lt[1]))
    return out


def adjacent(n):
    return tuple(k for k in (n - 1, n, n + 1) if 1 <= k <= 9)


def route_exclusions():
    """DMnEXCL boxes (core frame) around the comparator channel group and the VIN trunks, on their layer +-1."""
    out = []
    for r in toplevel_routes.build().rects:
        if r.net in CHANNEL_NETS and r.layer.startswith("M"):
            out.append((bloat((r.x0, r.y0, r.x1, r.y1), ROUTE_MARGIN), adjacent(int(r.layer[1:]))))
    for r in toplevel_full_routes.build().rects:
        if r["net"] in ("VINN", "VINP") and r["layer"].startswith("M"):
            out.append((bloat(tuple(r["box"]), ROUTE_MARGIN), adjacent(int(r["layer"][1:]))))
    return out


def region_exclusions():
    """Regions the top-level utility pass must leave alone (fill-policy owner table), core frame."""
    b = plan()
    out = [(pair_box(), ALL), (b["bootstrap_n"], ALL), (b["bootstrap_p"], ALL)]
    out += [(b[k], ALL) for k in REGIONS_ALL]
    out.append((b["sar"], tuple(range(1, 7)) + ("OD", "PO")))   # the macro owns OD/PO and M1-M6
    return out


def mirror(polys):
    for p in polys:
        p.mirror((AXIS, 0), (AXIS, 1))
    return polys


def import_fill(lib, path, old_top, new_top, prefix):
    """Add the fill hierarchy under old_top of a stream to lib, renamed: top -> new_top, others -> prefix + hash."""
    src = gds().read_gds(str(path))
    cells = {c.name: c for c in src.cells}
    if old_top not in cells:
        tops = [c for c in cells if c.endswith(("_DM", "_DODDPO"))]
        if len(tops) != 1:
            raise ValueError(f"No fill top in {path}: {sorted(cells)}")
        old_top = tops[0]
    keep = [cells[old_top]] + list(cells[old_top].dependencies(True))
    taken = {c.name for c in lib.cells}
    for c in keep:
        c.name = new_top if c is cells[old_top] else prefix + sha(c.name.encode())[:18]
        if c.name in taken:
            raise ValueError("Fill cell name collision: " + c.name)
    lib.add(*keep)
    return cells[old_top]


def save(lib, folder, name="seed.gds"):
    folder.mkdir(parents=True, exist_ok=True)
    lib.write_gds(str(folder / name))
    return sha((folder / name).read_bytes())


def pair_seed(identity, core_gds, seed_gds):
    g = gds()
    _, core = read_stream(core_gds, CORE)
    lib, top = read_stream(seed_gds, PAIR)
    box = pair_box()
    dx, dy = -PAIR_T[0], -PAIR_T[1]
    ctx = context(core, bloat(box, CONTEXT_MARGIN))
    for p in ctx:
        p.translate(dx, dy)
    entries = []
    for p in core.polygons:
        n = LAYER_OF.get((p.layer, p.datatype))
        (x0, y0), (x1, y1) = p.bounding_box()
        if n and overlap((x0, y0, x1, y1), box):
            b = clip(bloat((x0, y0, x1, y1), ENTRY_MARGIN), box)
            entries.append(((b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy), (n,)))
    cctx, cblk = g.Cell("ACF1_PAIR_CONTEXT"), g.Cell("ACF1_PAIR_ENTRY_BLOCK")
    cctx.add(*ctx)
    cblk.add(*exclusion_rects(entries))
    lib.add(cctx, cblk)
    top.add(g.Reference(cctx), g.Reference(cblk))
    out = WORK / identity
    digest = save(lib, out)
    summary = dict(identity=identity, seed=dict(path=str(seed_gds), sha256=sha(Path(seed_gds).read_bytes())),
                   core=dict(path=str(core_gds), sha256=sha(Path(core_gds).read_bytes())), seed_gds_sha256=digest,
                   pair_outline_core_um=box, translation_um=PAIR_T, bounds_native_um=PAIR_NATIVE,
                   context_polygons=len(ctx), entry_blocks_by_layer={f"M{n}": sum(1 for _, (k,) in entries if k == n)
                                                                     for n in range(1, 10)},
                   entry_margin_um=ENTRY_MARGIN)
    write_json(out / "seed.json", summary)
    return summary


def boot_seed(identity, core_gds):
    g = gds()
    lib, top = read_stream(core_gds, CORE)
    b = plan()
    n_box, p_box = b["bootstrap_n"], b["bootstrap_p"]
    if abs((n_box[0] + p_box[2]) / 2 - AXIS) > 1e-6:
        raise ValueError("The Bootstrap outlines are not mirror images about the axis")
    mirrored = mirror(context(top, bloat(n_box, CONTEXT_MARGIN), skip=(PAIR,)))
    rects = route_exclusions()
    excl = exclusion_rects(rects) + mirror(exclusion_rects(rects))
    cm, ce = g.Cell("ACF1_BOOT_MIRROR"), g.Cell("ACF1_BOOT_BLOCK")
    cm.add(*mirrored)
    ce.add(*excl)
    lib.add(cm, ce)
    top.add(g.Reference(cm), g.Reference(ce))
    out = WORK / identity
    digest = save(lib, out)
    summary = dict(identity=identity, core=dict(path=str(core_gds), sha256=sha(Path(core_gds).read_bytes())),
                   seed_gds_sha256=digest, bounds_core_um=p_box, mirrored_from_um=bloat(n_box, CONTEXT_MARGIN),
                   mirrored_polygons=len(mirrored), exclusion_rects=len(excl), placement=dict(XBOOTP="R0 (0, 0)",
                                                                                          XBOOTN=f"MY ({2 * AXIS:g}, 0)"))
    write_json(out / "seed.json", summary)
    return summary


def place_fill(lib, top, pair_stream, boot_fill):
    """Pair fill at the pair origin, Bootstrap fill twice (R0 and MY about the axis), into lib/top."""
    g = gds()
    names = {}
    for old, new, pre in (("sar8_cdac_fill_odpo", "pair_odpo", "PO"), ("sar8_cdac_fill_metal", "pair_metal", "PM"),
                          ("XREF_OD_DENSITY_ROW", "pair_odrow", "PR")):
        c = import_fill(lib, pair_stream, old, f"{FILL_TOP}_{new}", PREFIX + pre + "_")
        top.add(g.Reference(c, PAIR_T))
        names[new] = c.name
    if boot_fill:
        for kind, pre in (("ODPO", "BO"), ("metal", "BM")):
            c = import_fill(lib, boot_fill / kind / "fill.gds", CORE if kind == "ODPO" else CORE + "_DM",
                            f"{FILL_TOP}_boot_{kind.lower()}", PREFIX + pre + "_")
            top.add(g.Reference(c), g.Reference(c, (2 * AXIS, 0), rotation=3.141592653589793, x_reflection=True))
            names["boot_" + kind.lower()] = c.name
    return names


def core_seed(identity, core_gds, pair_stream, boot_fill):
    g = gds()
    lib, top = read_stream(core_gds, CORE)
    names = place_fill(lib, top, pair_stream, boot_fill)
    rects = region_exclusions() + route_exclusions()
    ce = g.Cell("ACF1_CORE_BLOCK")
    ce.add(*exclusion_rects(rects))
    lib.add(ce)
    top.add(g.Reference(ce))
    out = WORK / identity
    digest = save(lib, out)
    summary = dict(identity=identity, core=dict(path=str(core_gds), sha256=sha(Path(core_gds).read_bytes())),
                   pair_stream_sha256=sha(Path(pair_stream).read_bytes()), boot_fill=str(boot_fill),
                   seed_gds_sha256=digest, bounds_core_um=CORE_BOX, fill_cells=names,
                   exclusions=[dict(box=[round(v, 4) for v in box], layers=[str(n) for n in layers])
                               for box, layers in rects])
    write_json(out / "seed.json", summary)
    return summary


def library(identity, pair_stream, boot_fill, core_fill):
    """The fill hierarchy FILL_TOP in the core frame: pair, Bootstrap (R0 and MY) and core fill, and the exclusions."""
    g = gds()
    lib = g.Library(unit=1e-6, precision=1e-9)
    top = g.Cell(FILL_TOP)
    lib.add(top)
    names = place_fill(lib, top, pair_stream, boot_fill)
    for kind, pre in (("ODPO", "CO"), ("metal", "CM")):
        c = import_fill(lib, core_fill / kind / "fill.gds", CORE if kind == "ODPO" else CORE + "_DM",
                        f"{FILL_TOP}_core_{kind.lower()}", PREFIX + pre + "_")
        top.add(g.Reference(c))
        names["core_" + kind.lower()] = c.name
    excl = g.Cell(f"{FILL_TOP}_excl")
    excl.add(*exclusion_rects(region_exclusions() + route_exclusions()))
    lib.add(excl)
    top.add(g.Reference(excl))
    names["excl"] = excl.name
    out = WORK / identity
    digest = save(lib, out, "fill_library.gds")
    cells = sorted(c.name for c in lib.cells)
    if not all(c == FILL_TOP or c.startswith((FILL_TOP + "_", PREFIX)) for c in cells):
        raise ValueError("Unexpected cell name in the fill library")
    per_layer = {}
    for p in top.get_polygons():
        k = f"{p.layer}/{p.datatype}"
        per_layer[k] = per_layer.get(k, 0) + p.area()
    summary = dict(identity=identity, library_gds_sha256=digest, top=FILL_TOP, masters=names, cells=len(cells),
                   area_um2_by_layer={k: round(v, 3) for k, v in sorted(per_layer.items())},
                   inputs=dict(pair_stream_sha256=sha(Path(pair_stream).read_bytes()), boot_fill=str(boot_fill),
                               core_fill=str(core_fill)))
    write_json(out / "library.json", summary)
    (out / "cells.txt").write_text("\n".join(cells) + "\n")
    return summary


def fill_layer(p):
    """Layer key of a fill or drawn polygon: metal number, 'OD' or 'PO'; None for markers and blocks."""
    if p.layer in (6, 17):
        return "OD" if p.layer == 6 else "PO"
    if 31 <= p.layer <= 39:
        return p.layer - 30
    return None


def verify(library_id, pair_seed_id, core_gds=None):
    """Geometric checks of the assembled fill hierarchy against the routed core and its own exclusions.

    - fill overlaps no drawn shape of the same layer (OD, PO, M1-M9 drawing and pin purposes) anywhere;
    - the core pass leaves every exclusion box empty on its layers;
    - the pair fill leaves its entry blocks empty, the Bootstrap fill (both placements) the route exclusions;
    - fill of different owners does not overlap on a layer."""
    g = gds()
    core_gds = core_gds or WORK / "inputs/core_route_full.gds"
    lib, top = read_stream(WORK / library_id / "fill_library.gds", FILL_TOP)
    groups = {}
    for r in top.references:
        tmp = g.Cell("T")
        tmp.add(g.Reference(r.cell, r.origin, r.rotation, r.magnification, r.x_reflection))
        owner = r.cell.name[len(FILL_TOP) + 1:].split("_")[0]
        if owner == "excl":
            continue
        for p in tmp.get_polygons():
            k = fill_layer(p)
            if k is not None:
                groups.setdefault(owner, {}).setdefault(k, []).append(p)
    _, core = read_stream(core_gds, CORE)
    drawn = {}
    for p in core.get_polygons():
        dummy = p.datatype in (1, 7, 41, 61) and p.layer < 100
        k = "OD" if (p.layer, p.datatype) == (6, 0) else "PO" if (p.layer, p.datatype) == (17, 0) else \
            None if dummy or p.layer in (6, 17) else LAYER_OF.get((p.layer, p.datatype))
        if k is not None:
            drawn.setdefault(k, []).append(p)

    def area(a, b):
        return round(sum(q.area() for q in g.boolean(a, b, "and")), 6) if a and b else 0.0

    def boxes_on(rects, k):
        return [g.rectangle(b[:2], b[2:]) for b, layers in rects if k in layers]

    out = dict(library=library_id, fill_polygons={o: sum(len(v) for v in d.values()) for o, d in groups.items()},
               overlap_with_drawn_um2={}, core_fill_in_exclusions_um2={}, pair_fill_in_entry_blocks_um2={},
               boot_fill_in_route_exclusions_um2={}, overlap_between_owners_um2={})
    for o, d in groups.items():
        out["overlap_with_drawn_um2"][o] = {str(k): area(v, drawn.get(k, [])) for k, v in d.items()}
    rects = region_exclusions() + route_exclusions()
    out["core_fill_in_exclusions_um2"] = {str(k): area(v, boxes_on(rects, k)) for k, v in groups["core"].items()}
    _, seed_top = read_stream(WORK / pair_seed_id / "seed.gds", PAIR)
    blk = next(r.cell for r in seed_top.references if r.cell.name == "ACF1_PAIR_ENTRY_BLOCK")
    entries = {}
    for p in blk.polygons:
        q = p.copy()
        q.translate(*PAIR_T)
        entries.setdefault(p.datatype, []).append(q)
    out["pair_fill_in_entry_blocks_um2"] = {str(k): area(groups["pair"].get(k, []), v) for k, v in entries.items()}
    routes = route_exclusions()
    out["boot_fill_in_route_exclusions_um2"] = {
        str(k): area(v, boxes_on(routes, k) + mirror(boxes_on(routes, k))) for k, v in groups["boot"].items()}
    owners = sorted(groups)
    for i, a in enumerate(owners):
        for b in owners[i + 1:]:
            out["overlap_between_owners_um2"][f"{a}/{b}"] = {
                str(k): area(groups[a][k], groups[b][k]) for k in groups[a] if k in groups[b]}
    values = [v for key in ("overlap_with_drawn_um2", "overlap_between_owners_um2") for d in out[key].values()
              for v in d.values()]
    values += [v for key in ("core_fill_in_exclusions_um2", "pair_fill_in_entry_blocks_um2",
                             "boot_fill_in_route_exclusions_um2") for v in out[key].values()]
    out["pass"] = max(values) == 0
    write_json(WORK / library_id / "verify.json", out)
    return out


def wrapper_gds(identity, library_id, core_gds):
    """The wrapper as a stream, without OA: the core stream, the fill library and a top WRAPPER with XCORE, FILL and
    copies of the core's top-level texts. Revision 1 showed that the OA wrapper streams out to this geometry."""
    g = gds()
    lib, core = read_stream(core_gds, CORE)
    fill_lib, fill = read_stream(WORK / library_id / "fill_library.gds", FILL_TOP)
    taken = {c.name for c in lib.cells}
    cells = [fill] + list(fill.dependencies(True))
    if taken & {c.name for c in cells} or WRAPPER in taken:
        raise ValueError("Cell name collision between the core stream and the fill library")
    lib.add(*cells)
    top = g.Cell(WRAPPER)
    top.add(g.Reference(core), g.Reference(fill))
    top.add(*[g.Label(l.text, l.origin, l.anchor, l.rotation, l.magnification, l.x_reflection, l.layer, l.texttype)
              for l in core.labels])
    lib.add(top)
    out = WORK / identity
    digest = save(lib, out, "wrapper.gds")
    summary = dict(identity=identity, wrapper=WRAPPER, core_gds_sha256=sha(Path(core_gds).read_bytes()),
                   library=library_id, labels=len(core.labels), gds_sha256=digest)
    write_json(out / "wrapper.json", summary)
    return summary


def launch(identity, files, arguments, timeout=180):
    """Create the evidence directory, upload files and start the remote driver in the background."""
    if not IDENTITY.fullmatch(identity):
        raise ValueError("Invalid identity")
    cfg = config()
    q = shlex.quote
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, blob in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(blob).decode("ascii"), "B64"]
    script += ["sha256sum " + " ".join(files),
               "nohup " + " ".join(q(a) for a in arguments) + " > driver.log 2>&1 < /dev/null &", "echo PID=$!"]
    text = ssh("\n".join(script), timeout=timeout).decode("utf-8", "replace")
    receipt = dict(identity=identity, host=cfg["host"], evidence=evidence, arguments=arguments,
                   uploaded_sha256={n: sha(b) for n, b in files.items()}, stdout=text.splitlines())
    write_json(WORK / identity / "launch.json", receipt)
    return receipt


def drivers():
    return {n: (PHYSICAL / n).read_bytes() for n in ("toplevel_fill_physical.py", "fill_cdac.py", "run_physical.py",
                                                     "apply_fill.py", "workspace.py")}


def run_fill(identity, seed, top, bounds, turbo=4, seconds=1800, tcd=True):
    cfg = config()
    files = drivers()
    files["seed.gds"] = Path(seed).read_bytes()
    return launch(identity, files, ["python", "-u", "toplevel_fill_physical.py", "fill", identity, "--seed", "seed.gds",
                                    "--top", top, "--bounds", *[f"{v:g}" for v in bounds],
                                    "--lock", cfg["legacy_root"] + "/layout.lock", "--turbo", str(turbo),
                                    "--seconds", str(seconds)] + ([] if tcd else ["--no-tcd"]))


def run_pair(identity, fill):
    cfg = config()
    return launch(identity, drivers(), ["python", "-u", "toplevel_fill_physical.py", "pair", identity, "--fill", fill,
                                        "--evidence-root", cfg["remote_root"] + "/evidence"])


def fetch(identity, paths):
    cfg = config()
    base = f"{cfg['remote_root']}/evidence/{identity}"
    dest = WORK / "evidence" / identity
    out = []
    for rel in paths:
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError("Unsafe path " + rel)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(ssh(f"cat {shlex.quote(base + '/' + rel)}", timeout=600))
        out.append(str(target))
    return out


def status(identity):
    cfg = config()
    base = shlex.quote(f"{cfg['remote_root']}/evidence/{identity}")
    text = ssh(f"cd {base}; ls; for f in fill_manifest.json status.json manifest.json error.json; do "
               f"test -f $f && {{ echo \"== $f\"; head -c 6000 $f; echo; }}; done; echo '== driver.log'; tail -n 8 driver.log",
               timeout=60).decode("utf-8", "replace")
    return text


def build(identity, library_id, core_view=CORE_VIEW, view=None, expect_core_oa=None):
    """Stream the fill library into OA and create the wrapper WRAPPER/<view>, under the layout lock.

    Nothing existing is overwritten: every cell of the library and the wrapper view must be new. The core views
    are opened read only and their layout.oa digests are compared before and after."""
    view = view or "layout_" + REVISION
    out = WORK / library_id
    cells = (out / "cells.txt").read_text().split()
    blob = (out / "fill_library.gds").read_bytes()
    if sha(blob) != json.loads((out / "library.json").read_text())["library_gds_sha256"]:
        raise ValueError("Fill library differs from its record")
    cfg = config()
    q = shlex.quote
    lib = sk(cfg["library"])
    skill = "\n".join([
        'procedure(acfNeed(ok message) unless(ok error("%s\\n" message)))',
        "procedure(acfBuild()",
        " let((dd core fill cv inst n)",
        f"  dd=ddGetObj({lib})",
        f"  acfNeed(dd && dd~>readPath=={sk(cfg['library_path'])} \"Wrong layout library\")",
        f"  acfNeed(!ddGetObj({lib} {sk(WRAPPER)} {sk(view)}) \"Wrapper view exists\")",
        f"  core=dbOpenCellViewByType({lib} {sk(CORE)} {sk(core_view)} \"maskLayout\" \"r\")",
        "  acfNeed(core \"Missing core view\")",
        f"  fill=dbOpenCellViewByType({lib} {sk(FILL_TOP)} \"layout\" \"maskLayout\" \"r\")",
        "  acfNeed(fill \"Missing fill hierarchy\")",
        f"  cv=dbOpenCellViewByType({lib} {sk(WRAPPER)} {sk(view)} \"maskLayout\" \"w\")",
        "  acfNeed(cv \"Cannot create the wrapper\")",
        '  inst=dbCreateInst(cv core "XCORE" 0:0 "R0") acfNeed(inst "Cannot place XCORE")',
        '  inst=dbCreateInst(cv fill "FILL" 0:0 "R0") acfNeed(inst "Cannot place FILL")',
        "  n=0",
        '  foreach(s core~>shapes when(s~>objType=="label"',
        "   acfNeed(dbCreateLabel(cv s~>lpp s~>xy s~>theLabel s~>justify s~>orient s~>font s~>height) \"Cannot copy a text\")",
        "   n=n+1))",
        f'  dbReplaceProp(cv "generatorOwner" "string" {sk(OWNER)})',
        f'  dbReplaceProp(cv "coreView" "string" {sk(core_view)})',
        f'  dbReplaceProp(cv "fillLibrarySha256" "string" {sk(sha(blob))})',
        '  acfNeed(dbSave(cv) "Cannot save the wrapper")',
        '  printf("FILL_WRAPPER_OK instances=%d labels=%d bBox=%L\\n" length(cv~>instances) n cv~>bBox)',
        "  dbClose(cv) dbClose(fill) dbClose(core) t))",
        "if(errset(acfBuild() t) then exit(0) else exit(1))"]) + "\n"
    files = {"fill_library.gds": blob, "build.il": skill.encode("ascii"),
             "cells.txt": ("\n".join(cells) + "\n").encode("ascii")}
    evidence = f"{cfg['remote_root']}/evidence/{identity}"
    lib_path = cfg["library_path"]
    guarded = " ".join(q(f"{lib_path}/{CORE}/{v}/layout.oa") for v in ("layout_place", "layout_route_int", core_view))
    script = ["set -eu", "umask 077", f"test \"$(hostname -s)\" = {q(cfg['host'])}",
              f"test ! -e {q(evidence)} && test ! -e {q(cfg['legacy_root'] + '/evidence/' + identity)}",
              f"exec 9>>{q(cfg['legacy_root'] + '/layout.lock')}", "flock -w 600 9 || { echo LAYOUT_LOCK_BUSY; exit 3; }",
              f"if find {q(lib_path + '/' + CORE)} -name '*.cdslck*' | grep -q .; then echo EDIT_LOCK_PRESENT; exit 4; fi",
              f"mkdir {q(evidence)}", f"cd {q(evidence)}"]
    for name, b in files.items():
        script += [f"base64 -d > {name} <<'B64'", base64.b64encode(b).decode("ascii"), "B64"]
    script += [f"while read c; do test ! -e {q(lib_path)}/\"$c\" || {{ echo CELL_EXISTS $c; exit 6; }}; done < cells.txt",
               f"test ! -e {q(lib_path + '/' + WRAPPER + '/' + view)} || {{ echo WRAPPER_EXISTS; exit 6; }}",
               f"cp {q(cfg['remote_root'] + '/runtime/cds.lib')} cds.lib",
               f"grep -q -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' cds.lib || "
               f"grep -m1 -E '^DEFINE[[:space:]]+{STANDARD_LIBRARY}[[:space:]]' /home/dmanager/shared_lib/TSMC28/cds.lib >> cds.lib",
               f"before=$(sha256sum {guarded} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_BEFORE=$before"]
    if expect_core_oa:
        script.append(f"test \"$(sha256sum {q(lib_path + '/' + CORE + '/' + core_view + '/layout.oa')} | cut -d' ' -f1)\" = "
                      f"{q(expect_core_oa)} || {{ echo CORE_OA_DIFFERS_FROM_STREAM; exit 7; }}")
    pdk = "/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/tsmcN28"
    strmin = (f"source {CADENCE}; exec strmin -library {cfg['library']} -strmFile fill_library.gds -topCell {FILL_TOP} "
              f"-view layout -attachTechFileOfLib tsmcN28 -layerMap {pdk}/tsmcN28.layermap -writeMode noOverwrite "
              "-logFile strmin.log")
    script += ["rc=0", f"timeout -k 10 600 tcsh -fc {q(strmin)} > strmin.console 2>&1 < /dev/null || rc=$?",
               "grep -E \"Translation completed|ERROR\" strmin.log | tail -n 5 || true",
               "test $rc = 0 || { echo STRMIN_FAILED=$rc; exit 8; }",
               f"timeout -k 10 600 tcsh -fc {q('source ' + CADENCE + '; exec virtuoso -nograph -nocdsinit -log build.log -restore build.il')}"
               " > oa.console 2>&1 < /dev/null || rc=$?",
               f"after=$(sha256sum {guarded} | cut -d' ' -f1 | tr '\\n' ' ')", "echo GUARDED_AFTER=$after",
               "test \"$before\" = \"$after\" || { echo READ_ONLY_VIEW_CHANGED; rc=5; }",
               f"sha256sum {q(lib_path + '/' + WRAPPER + '/' + view + '/layout.oa')} {q(lib_path + '/' + FILL_TOP + '/layout/layout.oa')} || true",
               "grep -E '^FILL_WRAPPER_OK|\\*Error\\*' oa.console || true", "echo EXIT=$rc", "exit $rc"]
    run = ssh("\n".join(script), timeout=1500)
    text = run.decode("utf-8", "replace")
    receipt = dict(identity=identity, library=library_id, wrapper=f"{WRAPPER}/{view}", core_view=core_view,
                   stdout=text.splitlines(), ok="FILL_WRAPPER_OK" in text and "EXIT=0" in text)
    write_json(WORK / identity / "build.json", receipt)
    if not receipt["ok"]:
        raise RuntimeError("Build failed; see " + str(WORK / identity / "build.json"))
    return receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--revision", type=int, default=1, help="fill revision (1: layout_route_full, 2: layout_route_guard)")
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("pair-seed")
    a.add_argument("identity")
    a.add_argument("--core-gds", default=str(WORK / "inputs/core_route_full.gds"))
    a.add_argument("--seed-gds", default=str(WORK / "inputs/pair_seed.gds"))
    a = sub.add_parser("boot-seed")
    a.add_argument("identity")
    a.add_argument("--core-gds", default=str(WORK / "inputs/core_route_full.gds"))
    a = sub.add_parser("core-seed")
    a.add_argument("identity")
    a.add_argument("--core-gds", default=str(WORK / "inputs/core_route_full.gds"))
    a.add_argument("--pair-stream", required=True, help="fixture.gds of the refilled pair evidence")
    a.add_argument("--boot-fill", required=True, help="fetched evidence folder of the Bootstrap fill pass")
    a = sub.add_parser("library")
    a.add_argument("identity")
    a.add_argument("--pair-stream", required=True)
    a.add_argument("--boot-fill", required=True)
    a.add_argument("--core-fill", required=True)
    a = sub.add_parser("wrapper-gds")
    a.add_argument("identity")
    a.add_argument("--library", required=True)
    a.add_argument("--core-gds", required=True)
    a = sub.add_parser("verify")
    a.add_argument("library")
    a.add_argument("--pair-seed", default="se-xref-peripheral-routed-fill")
    a.add_argument("--core-gds")
    a = sub.add_parser("fill")
    a.add_argument("identity")
    a.add_argument("--seed", required=True)
    a.add_argument("--top", required=True)
    a.add_argument("--bounds", type=float, nargs=4, required=True)
    a.add_argument("--turbo", type=int, default=4)
    a.add_argument("--no-tcd", action="store_true", help="no dummy TCD patterns (the core pass)")
    a = sub.add_parser("pair")
    a.add_argument("identity")
    a.add_argument("--fill", required=True)
    a = sub.add_parser("build")
    a.add_argument("identity")
    a.add_argument("--library", required=True)
    a.add_argument("--core-view", default=CORE_VIEW)
    a.add_argument("--view")
    a.add_argument("--expect-core-oa")
    a = sub.add_parser("status")
    a.add_argument("identity")
    a = sub.add_parser("fetch")
    a.add_argument("identity")
    a.add_argument("paths", nargs="+")
    args = ap.parse_args()
    use_revision(args.revision)
    if args.action == "pair-seed":
        r = pair_seed(args.identity, args.core_gds, args.seed_gds)
    elif args.action == "boot-seed":
        r = boot_seed(args.identity, args.core_gds)
    elif args.action == "core-seed":
        r = core_seed(args.identity, args.core_gds, args.pair_stream, Path(args.boot_fill))
    elif args.action == "library":
        r = library(args.identity, args.pair_stream, Path(args.boot_fill), Path(args.core_fill))
    elif args.action == "wrapper-gds":
        r = wrapper_gds(args.identity, args.library, args.core_gds)
    elif args.action == "verify":
        r = verify(args.library, args.pair_seed, args.core_gds)
    elif args.action == "fill":
        r = run_fill(args.identity, args.seed, args.top, args.bounds, args.turbo, tcd=not args.no_tcd)
    elif args.action == "pair":
        r = run_pair(args.identity, args.fill)
    elif args.action == "build":
        r = build(args.identity, args.library, args.core_view, args.view, args.expect_core_oa)
    elif args.action == "status":
        print(status(args.identity))
        return
    else:
        r = fetch(args.identity, args.paths)
    print(json.dumps(r, indent=1)[:4000])


if __name__ == "__main__":
    main()
