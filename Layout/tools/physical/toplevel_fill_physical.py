"""Stage 5 fill runs of the ADC core (Layout/specs/fill-policy.md), inside one evidence directory (Python 2).

The launcher (Layout/design/toplevel_fill.py) uploads this file with fill_cdac.py, run_physical.py and workspace.py.

- `fill`: the installed foundry OD/PO and metal fill utilities (fill_cdac.native_job, the same private job edits as
  every module fill) on an uploaded seed stream, filling inside --bounds only. The seed carries the context the fill
  must respect (neighbouring geometry, DMnEXCL/ODBLK/POBLK blocks); only the generated fill is used afterwards.
- `pair`: merges such a fill of the XREF/CDAC pair into the accepted seed stream se-xref-peripheral-seed, exactly as
  se-xref-peripheral-dense was assembled (fill masters sar8_cdac_fill_odpo/metal at the origin of the pair top), then
  runs DRC, LVS and coupled xRC with the pair's decks and writes a manifest in the format of the reference-driver
  evidence, so the existing PEX fetch and the standalone weight fixture accept it.
"""
from __future__ import print_function

import argparse
import fcntl
import json
import os
from os.path import basename, isfile, join
import re
import struct
import sys
import time

sys.path.insert(0, os.getcwd())
import fill_cdac  # noqa: E402
import run_physical as rp  # noqa: E402
import apply_fill as merge  # noqa: E402

PAIR_TOP = "sar8_cdac_with_xref"
FILL_PARTS = (("ODPO", "sar8_cdac_fill_odpo", "CDFO_"), ("metal", "sar8_cdac_fill_metal", "CDFM_"))


def unit(data):
    """GDS real8 to float; stream units may differ in their last representation bits."""
    import binascii
    head = ord(data[0:1])
    return 16.0 ** ((head & 127) - 64) * int(binascii.hexlify(data[1:]), 16) / 2.0 ** 56


def save(path, record):
    with open(path + ".next", "w") as f:
        json.dump(record, f, indent=2, sort_keys=True)
    os.rename(path + ".next", path)


def run_fill(args, out):
    if basename(args.seed) != args.seed or not isfile(join(out, args.seed)):
        raise ValueError("The seed must be uploaded into the evidence directory")
    x0, y0, x1, y1 = args.bounds
    if not (x0 < x1 and y0 < y1):
        raise ValueError("Invalid fill boundary")
    boundary = dict(xLB=x0, yLB=y0, xRT=x1, yRT=y1)
    seed = join(out, args.seed)
    identity = rp.gds_identity(seed)
    if args.top not in identity["structural_sha256"]:
        raise ValueError("The seed has no " + args.top)
    record = dict(identity=args.identity, top=args.top, boundary_um=boundary, seed_gds_sha256=identity["sha256"],
                  core_dummy_od_width_um=0.1, core_only_clearance=False, mos_dummy_od_length_um=0.3,
                  dummy_tcd=not args.no_tcd,
                  fill_geometry_customized=False, physical_signoff=False, steps={},
                  driver_sha256=dict((n, rp.sha(rp.raw(join(out, n))))
                                     for n in ("toplevel_fill_physical.py", "fill_cdac.py", "run_physical.py", "apply_fill.py")))
    path = join(out, "fill_manifest.json")
    save(path, record)
    with open(args.lock, "a") as lock:
        # The utilities share the layout host with the OA flows; queue behind them like fill_cdac --wait-for-lock.
        fcntl.flock(lock, fcntl.LOCK_EX)
        for kind in ("ODPO", "metal"):
            work = join(out, kind)
            os.mkdir(work)
            os.symlink("../" + args.seed, join(work, "source.gds"))
            source, text = fill_cdac.native_job(kind, args.top, boundary, tcd=not args.no_tcd)
            rp.put(join(work, "fill.svrf"), text.encode("latin1") if not isinstance(text, bytes) else text)
            step = record["steps"][kind] = dict(source=source, source_sha256=rp.sha(rp.raw(source)),
                                                job_sha256=rp.sha(rp.raw(join(work, "fill.svrf"))), status="running",
                                                started=time.time())
            save(path, record)
            rc = rp.tool(rp.CALIBRE, ["calibre", "-drc", "-hier", "-turbo", str(args.turbo), "-nowait", "fill.svrf"],
                         work, join(work, "fill.console"), args.seconds)
            step.update(returncode=rc, status="exited", finished=time.time())
            save(path, record)
            if rc:
                raise RuntimeError("Native %s fill failed; evidence preserved" % kind)
            result = join(work, "fill.gds")
            if not isfile(result):
                raise ValueError("No generated fill GDS")
            ident = rp.gds_identity(result)
            step.update(gds_sha256=ident["sha256"], bytes=os.path.getsize(result), cells=sorted(ident["labels"]))
            save(path, record)
    if rp.sha(rp.raw(seed)) != identity["sha256"]:
        raise RuntimeError("Seed changed during fill")
    record["generation_complete"] = True
    save(path, record)


def run_pair(args, out):
    """Combined pair stream with the new fill, then DRC, LVS and xRC (the se-xref-peripheral-dense procedure)."""
    seed_dir = join(args.evidence_root, args.seed_evidence)
    fill_dir = join(args.evidence_root, args.fill)
    full_dir = join(args.evidence_root, "se-xref-full-b")
    m = json.load(open(join(seed_dir, "manifest.json")))
    if m["top"] != PAIR_TOP or m["active_step"] != "complete" or m["checks"]["lvs"]["verdict"] != "CORRECT":
        raise ValueError("Need the accepted pair seed")
    seed_gds = join(seed_dir, "fixture.gds")
    if rp.sha(rp.raw(seed_gds)) != m["gds"]["sha256"]:
        raise ValueError("Seed identity changed")
    fm = json.load(open(join(fill_dir, "fill_manifest.json")))
    if not fm.get("generation_complete") or fm["top"] != PAIR_TOP:
        raise ValueError("Need a complete pair fill")
    status = dict(identity=args.identity, source=args.seed_evidence, fill_evidence=args.fill, stages={}, phases={})
    spath = join(out, "status.json")
    save(spath, status)
    parts, units = {}, None
    for kind, cell, prefix in FILL_PARTS:
        path = join(fill_dir, kind, "fill.gds")
        if rp.sha(rp.raw(path)) != fm["steps"][kind]["gds_sha256"]:
            raise ValueError("Fill output changed: " + kind)
        names = rp.gds_identity(path)["labels"]
        src = PAIR_TOP if kind == "ODPO" else PAIR_TOP + "_DM"
        if src not in names:
            candidates = [n for n in names if n.endswith("_DODDPO") or n.endswith("_DM")]
            if len(candidates) != 1:
                raise ValueError("Unexpected fill top: %r" % candidates)
            src = candidates[0]
        mapped = join(out, kind + ".gds")
        merge.namespaced(path, mapped, src, cell, prefix)
        records, active = [], False
        for t, b in merge.records(rp.raw(mapped)):
            if t == 3:
                units = units or b[-8:]
                if units != b[-8:]:
                    raise ValueError("Inconsistent fill units")
            if t == 5:
                active = True
            if active:
                records.append(b)
            if t == 7:
                active = False
        if not records:
            raise ValueError("Empty fill part " + kind)
        parts[cell] = b"".join(records)
    combined, name = [], None
    for t, b in merge.records(rp.raw(seed_gds)):
        if t == 3 and abs(unit(b[-8:]) / unit(units) - 1) > 1e-14:
            raise ValueError("Units differ between seed and fill")
        if t == 6:
            name = b[4:].rstrip(b"\0").decode("ascii")
        if t == 7 and name == PAIR_TOP:
            for cell in sorted(parts):
                combined.extend([merge.gds_record(10, 0), merge.gds_record(18, 6, cell.encode("ascii")),
                                 merge.gds_record(16, 3, struct.pack(">ii", 0, 0)), merge.gds_record(17, 0)])
        if t == 4:
            combined.extend(parts[cell] for cell in sorted(parts))
        combined.append(b)
    gds = join(out, "fixture.gds")
    rp.put(gds, b"".join(combined))
    after = rp.gds_identity(gds, tuple(parts))
    if after["structural_sha256"][PAIR_TOP] != m["gds"]["structural_sha256"][PAIR_TOP] or \
            sorted(after["labels"][PAIR_TOP]) != sorted(m["gds"]["labels"][PAIR_TOP]):
        raise RuntimeError("Functional geometry changed")
    full = json.load(open(join(full_dir, "manifest.json")))
    functional = rp.gds_identity(gds, tuple(parts) + ("XREF_OD_DENSITY_ROW",))["structural_sha256"][PAIR_TOP]
    if functional != full["gds"]["structural_sha256"][PAIR_TOP]:
        raise RuntimeError("Pair geometry differs from se-xref-full-b")
    rp.put(join(out, "reference.cdl"), rp.raw(join(seed_dir, "reference.cdl")))
    rp.put(join(out, "intent.json"), rp.raw(join(seed_dir, "intent.json")))
    if rp.sha(rp.raw(join(out, "intent.json"))) != m["input_hashes"]["intent.json"] or \
            rp.sha(rp.raw(join(out, "reference.cdl"))) != m["reference_sha256"]:
        raise ValueError("Seed inputs changed")
    decks, checks = {}, {}

    def launch(phase, command, work, limit):
        status["phases"][phase] = dict(started=time.time())
        save(spath, status)
        rc = rp.tool(rp.CALIBRE, command, work, join(out, phase + ".console"), limit)
        status["phases"][phase].update(returncode=rc, finished=time.time())
        save(spath, status)
        if rc:
            raise RuntimeError("%s failed: %d" % (phase, rc))

    for kind in ("drc", "lvs", "pex"):
        work = join(out, kind)
        os.mkdir(work)
        os.symlink("../fixture.gds", join(work, "fixture.gds"))
        decks[kind] = rp.prepare_deck(work, kind, PAIR_TOP)
        if kind == "pex":
            deck = join(work, "pex.svrf")
            data, count = re.subn(br"(?m)^(FLATTEN CELL [^\n]+)$", br"\1 XREF_OD_DENSITY_ROW", rp.raw(deck))
            if count != 1:
                raise ValueError("Expected one FLATTEN CELL statement")
            rp.put(deck, data)
            decks[kind]["job_sha256"] = rp.sha(data)
            decks[kind]["support"]["density_row_flattened"] = "XREF_OD_DENSITY_ROW"
        if kind == "drc":
            launch("drc", ["calibre", "-drc", "-hier", "-turbo", "4", "-nowait", "drc.svrf"], work, 600)
            rules = rp.drc_rules(join(work, "DRC_RES.db"))
            checks["drc"] = dict(markers_by_rule=rules, markers=sum(rules.values()))
        elif kind == "lvs":
            launch("lvs", ["calibre", "-lvs", "-hier", "-turbo", "4", "-nowait", "lvs.svrf"], work, 600)
            text = rp.read(join(work, "lvs.rep"))
            ok = re.search(r"(?m)^\s+CORRECT\s+" + PAIR_TOP + r"\s+" + PAIR_TOP + r"\s*$", text)
            checks["lvs"] = dict(verdict="CORRECT" if ok else "NOT_CORRECT")
            if not ok:
                raise RuntimeError("Combined LVS mismatch")
        else:
            launch("phdb", ["calibre", "-xrc", "-phdb", "-turbo", "4", "-nowait", "pex.svrf"], work, 600)
            launch("rcc", ["calibre", "-xrc", "-pdb", "-rcc", "-turbo", "4", "-nowait", "pex.svrf"], work, 3600)
            launch("format", ["calibre", "-xrc", "-fmt", "-all", "-nowait", "pex.svrf"], work, 600)
            files = dict((n, rp.sha(rp.raw(join(work, n)))) for n in os.listdir(work) if n.startswith("extracted.scs"))
            checks["pex"] = dict(sha256=files.pop("extracted.scs"), companion_sha256=files)
    old, new = [], []
    for folder, sink in ((join(full_dir, "pex"), old), (join(out, "pex"), new)):
        lines = rp.raw(join(folder, "pex.svrf")).splitlines(True)
        rule = [line for line in lines if line.startswith(b"FLATTEN CELL ")]
        if len(rule) != 1:
            raise ValueError("Expected one FLATTEN CELL statement")
        sink.append([line for line in lines if line != rule[0]])
        sink.append(set(rule[0].decode("ascii").split()[2:]))
    if old[0] != new[0] or not old[1] < new[1]:
        raise RuntimeError("The PEX deck differs from se-xref-full-b beyond the flattened fill masters")
    for kind in ("drc", "lvs"):
        if decks[kind]["job_sha256"] != full["decks"][kind]["job_sha256"]:
            raise RuntimeError("The %s deck differs from se-xref-full-b" % kind)
    rec = dict(m, id=args.identity, stream_source="se-xref-full-b", fill_evidence=args.fill,
               fill_seed_gds_sha256=fm["seed_gds_sha256"], active_step="complete", gds=rp.gds_identity(gds),
               decks=decks, checks=checks, comparison_functional_sha256=functional,
               pex_new_fill_masters_flattened=sorted(new[1] - old[1]))
    save(join(out, "manifest.json"), rec)
    status["phase"] = "complete"
    save(spath, status)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="mode")
    f = sub.add_parser("fill")
    f.add_argument("identity")
    f.add_argument("--seed", required=True)
    f.add_argument("--top", required=True)
    f.add_argument("--bounds", type=float, nargs=4, required=True)
    f.add_argument("--lock", required=True)
    f.add_argument("--turbo", type=int, default=4)
    f.add_argument("--seconds", type=int, default=1800)
    f.add_argument("--no-tcd", action="store_true", help="leave out the optional dummy TCD patterns")
    p = sub.add_parser("pair")
    p.add_argument("identity")
    p.add_argument("--fill", required=True)
    p.add_argument("--seed-evidence", default="se-xref-peripheral-seed")
    p.add_argument("--evidence-root", required=True)
    args = ap.parse_args()
    out = os.getcwd()
    if basename(out) != args.identity:
        raise ValueError("Run inside the evidence directory of " + args.identity)
    try:
        (run_fill if args.mode == "fill" else run_pair)(args, out)
    except Exception as exc:
        save(join(out, "error.json"), dict(error=str(exc)))
        raise


if __name__ == "__main__":
    main()
