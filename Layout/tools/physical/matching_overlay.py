"""Scratch stream with the MOS-matching CAD markers on the comparator, for the matching-rule check (MATCH.WARN.1).

The chip DRC flags MATCH.WARN.1 because no MATCHING (205;8), ANARRAY_H (255;20) or ANARRAY_M (255;21) marker exists, so
the deck never checks PO.DN.16, PO.R.28, AN.R.79.2m or AN.R.80.2m. This copies a chip stream and adds the markers in
the comparator master sar_strongarm_t28_core only (its frame; Layout/design/comparator.il), so the check runs in the
chip context without touching any OA view or frozen stream.

Marker class: ANARRAY_H (DRM T-N28-CL-DR-002 v2.3, 8.3.2.3.1.1: high matching, "MOS array with mismatch within SPICE").
The comparator's offset is reported from native PDK Monte Carlo, i.e. at SPICE mismatch, which the DRM covers only for
high-matching arrays. The marker covers a whole MOS array, edge at the centreline between the outermost active gate
and its identical dummy (SR_DPO) or at the well-strap centreline (8.3.2.3.1.1, Figure 8.3.2.3.1.1). The matched pairs
share diffusion and interleave, so the arrays are the unit:
- N array (rows N1/N2 inside the P+ ring): input pair MNINP/MNINN (two fingers each, cross-placed), NMOS latch
  MNLATN/MNLATP, and the tail MNTAIL between the input fingers. Active gates at x +/-0.065, +/-0.195; dummies at
  +/-0.325, so x +/-0.26; y at the P+ ring centrelines -2.53 / -0.67.
- P array (row P inside the N+ ring): PMOS latch MPLATN/MPLATP and the reset pairs MPRSTN/MPRSTP, MPRSTX/MPRSTY.
  Active gates at x up to +/-0.325; dummies at +/-0.455, so x +/-0.39; y at the N+ ring centrelines -0.44 / 0.76.
"""
import argparse
import hashlib
import json
from pathlib import Path

MASTER = "sar_strongarm_t28_core"
LAYERS = {"MATCHING": (205, 8), "ANARRAY_H": (255, 20), "ANARRAY_M": (255, 21)}
ARRAYS = {   # comparator frame, um
    "N": dict(box=(-0.26, -2.53, 0.26, -0.67),
              devices=["MNINP_1", "MNINP_2", "MNINN_1", "MNINN_2", "MNLATN", "MNLATP", "MNTAIL_1", "MNTAIL_2"],
              groups={"input pair": ["MNINP", "MNINN"], "NMOS latch": ["MNLATN", "MNLATP"], "tail (in the array)": ["MNTAIL"]}),
    "P": dict(box=(-0.39, -0.44, 0.39, 0.76),
              devices=["MPRSTY", "MPLATN", "MPRSTN", "MPRSTP", "MPLATP", "MPRSTX"],
              groups={"PMOS latch": ["MPLATN", "MPLATP"], "output reset": ["MPRSTN", "MPRSTP"],
                      "internal-node reset": ["MPRSTX", "MPRSTY"]}),
}


def overlay(src, out, marker="ANARRAY_H"):
    import gdstk
    lib = gdstk.read_gds(str(src))
    cells = {c.name: c for c in lib.cells}
    comp = cells[MASTER]
    layer, datatype = LAYERS[marker]
    if any((p.layer, p.datatype) in LAYERS.values() for c in lib.cells for p in c.polygons):
        raise ValueError("The source stream already has matching markers")
    for a in ARRAYS.values():
        x0, y0, x1, y1 = a["box"]
        comp.add(gdstk.rectangle((x0, y0), (x1, y1), layer=layer, datatype=datatype))
    lib.write_gds(str(out))
    # Only the comparator master may change, and only by the markers.
    new = gdstk.read_gds(str(out))
    def shapes(c, skip=()):
        return sorted((p.layer, p.datatype, tuple(map(tuple, p.points.round(4).tolist()))) for p in c.polygons
                      if (p.layer, p.datatype) not in skip)
    old = {c.name: c for c in gdstk.read_gds(str(src)).cells}
    for c in new.cells:
        o = old[c.name]
        skip = LAYERS.values() if c.name == MASTER else ()
        if shapes(c, skip) != shapes(o) or sorted(r.cell_name for r in c.references) != sorted(r.cell_name for r in o.references):
            raise ValueError("Overlay changed more than the comparator markers: " + c.name)
    added = [p for p in new[MASTER].polygons if (p.layer, p.datatype) == (layer, datatype)]
    if len(added) != len(ARRAYS) or set(c.name for c in new.cells) != set(old):
        raise ValueError("Unexpected overlay result")
    return dict(source=str(src), source_sha256=hashlib.sha256(Path(src).read_bytes()).hexdigest(),
                out=str(out), out_sha256=hashlib.sha256(Path(out).read_bytes()).hexdigest(), master=MASTER,
                marker=marker, layer=[layer, datatype], arrays=ARRAYS)


CHECKS = ("PO.DN.16", "PO.R.28", "AN.R.79.2m", "AN.R.80.2m", "MATCH.WARN.1")


def record(identity, src, out_gds, marker="ANARRAY_H", out="Layout/results/chip_matching.json"):
    """Layout/results/chip_matching.json from a fetched run (work/layout/chip-objects/IDENTITY): per selected check
    its result count (DRC.rep), and per AN.R.79.2m / AN.R.80.2m result the OD/PO densities inside the array and in its
    6 um halo (the rule's DFM report), with the array each result falls on (die um)."""
    import re
    from Layout.design.chip_objects import WORK
    from Layout.project import ROOT, write_json
    base = WORK / identity
    manifest = json.loads((base / "manifest.json").read_bytes())
    rep = (base / "drc/DRC.rep").read_text(encoding="latin1")
    counts = {c: int(m[1]) for c in CHECKS for m in [re.search(r"(?m)^RULECHECK %s \.+ TOTAL Result Count = (\d+)" % re.escape(c), rep)] if m}
    if set(counts) != set(CHECKS):
        raise ValueError("Not every matching check ran: %s" % counts)
    results = []
    for rule in ("AN.R.79.2m", "AN.R.80.2m"):
        path = base / "drc" / (rule + ".rep")
        if not path.exists():
            continue
        text = path.read_text(encoding="latin1")
        kind = None
        for block in re.split(r"(?m)^(?=IL: |p \d+ \d+)", text):
            m = re.match(r"IL: \S+::(\S+)", block)
            if m:
                kind = m[1]
                continue
            if not block.startswith("p "):
                continue
            props = dict(re.findall(r"(?m)^(\w+_DN_\w+) (\S+)$", block))
            pts = [tuple(int(v) / 1000 for v in l.split()) for l in block.splitlines()[1:] if re.fullmatch(r"-?\d+ -?\d+", l.strip())]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            results.append(dict(rule=rule, kind=kind, bbox_die_um=[min(xs), min(ys), max(xs), max(ys)],
                                **{k: float(v) for k, v in props.items()}))
    placement = [410.0, 521.61]   # sar_strongarm_t28_core in the chip: mirrored in x (x_reflection + 180 deg)
    for r in results:
        cy = (r["bbox_die_um"][1] + r["bbox_die_um"][3]) / 2 - placement[1]
        r["array"] = next(k for k, a in ARRAYS.items() if a["box"][1] <= cy <= a["box"][3])
    rec = dict(schema_version=1, tool="Layout/tools/physical/matching_overlay.py", run=identity, host="thu-wei",
               chip_view="SAR_ADC_T28_LAYOUT/sar8_adc_chip/layout_full_fill5_r5_seal (scratch overlay; no OA change)",
               source_stream=str(src), source_stream_sha256=hashlib.sha256(Path(src).read_bytes()).hexdigest(),
               overlay_stream_sha256=hashlib.sha256(Path(out_gds).read_bytes()).hexdigest(),
               deck="drc_rule_T28_chip (FULL_CHIP, WITH_SEALRING), hierarchical, SELECT CHECK " + ", ".join(CHECKS),
               selected=manifest["decks"]["drc"].get("selected"), marker=marker, marker_layer=list(LAYERS[marker]),
               master=MASTER, arrays=ARRAYS, result_counts=counts, results=results)
    write_json(ROOT / out, rec)
    return rec


# The user's decision on the ANARRAY_H result (coordinator chat, 2026-11-23) and the accepted deviation.
DECISION = dict(
    date="2026-11-23", answer="Add markers, write waiver", option="A",
    marker="MATCHING (205;8), normal matching, permanent in the sign-off stream (chip top cell)",
    basis="DRM T-N28-CL-DR-002 v2.3 8.3.2.3.1.1: normal matching (MATCHING) for two simple identical transistors; "
          "high (ANARRAY_H) is 'mismatch within SPICE', medium (ANARRAY_M) 2x SPICE. In the chip deck MATCHING switches "
          "on PO.DN.16, PO.R.28 and AN.R.78.1m and clears MATCH.WARN.1; AN.R.79.x / 80.x read only ANARRAY_H / ANARRAY_M.",
    rejected="Option B (identical-dummy ring, N/P array split, comparator re-layout for ANARRAY_H)",
    high_matching_evidence=dict(run="chip-match-h1",
                                result="AN.R.79.2m on OD density: N array 0.348, P array 0.257 against 0.10",
                                expected_also="AN.R.79.5m (one MOS type per array and its 6 um halo; the P row is "
                                              "0.23 um from the N array), not run"),
    accepted_risk=dict(
        statement="MATCH.WARN.1: MOSFET matching may degrade at least 3x when the high/medium array rules are not met. "
                  "The rule specifies no upper bound on mismatch.",
        offset_mc="Layout/results/comparator.md v8 extracted, 200 seeds: sigma 12.05 mV, range -34.7 to +34.1 mV",
        at_3x="about +/-104 mV by scaling the 200-seed sample extrema; sensitivity example only",
        consequence="The ADC is uncalibrated. Correction range, resolution and qualification remain open in docs/specification.md and issue #12."),
)
# Every chip-deck check that reads MATCHING. CSR.R.1:MATCHING (no MATCHING in the corner triangles) sits under
# #IFNDEF WITH_SEALRING, so it does not run on a chip with its seal ring; the markers are about 400 um from any corner.
MATCH_SET = ("PO.DN.16", "PO.R.28", "AN.R.78.1m", "MATCH.WARN.1", "G.1:MATCHING", "G.2:MATCHING", "G.3:MATCHING")


def decision(view, chk, flat, vcs, ref_chk, ref_flat, out="Layout/results/chip_matching.json"):
    """Add the decision and the sign-off view's checks to chip_matching.json: every MATCHING-enabled check of the full
    chip DRC (it must run and be 0) and the DRC by rule, flat LUP/ESD, LVS and ERC against the reference view."""
    import re
    from Layout.design.chip_objects import WORK as OBJ
    from Layout.design.toplevel_route import WORK as EV
    from Layout.project import ROOT, write_json
    rep = (EV / chk / "drc/DRC.rep").read_text(encoding="latin1")
    counts = {c: int(m[1]) for c in MATCH_SET
              for m in [re.search(r"(?m)^RULECHECK %s \.+ TOTAL Result Count = (\d+)" % re.escape(c), rep)] if m}
    new, old = (json.loads((EV / i / "manifest.json").read_bytes()) for i in (chk, ref_chk))
    a, b = old["checks"]["drc"]["markers_by_rule"], new["checks"]["drc"]["markers_by_rule"]
    fa, fb = (json.loads((OBJ / i / "manifest.json").read_bytes())["checks"]["drc"]["markers_by_rule"] for i in (ref_flat, flat))
    v = json.loads((OBJ / vcs / "manifest.json").read_bytes())["checks"]["lvs"]["verdict"]
    path = ROOT / out
    rec = json.loads(path.read_bytes())
    rec["decision"] = DECISION
    rec["sign_off"] = dict(
        view=f"SAR_ADC_T28_LAYOUT/sar8_adc_chip/{view}", built_by="Layout/design/chip_matching_marker.py",
        markers="two MATCHING rectangles in the chip top cell over the comparator's N and P arrays (OA PMET_CUT/drawing1 "
                "= GDS 205;8); the comparator, the cores and their streams are unchanged",
        lvs_xrc="calibre.lvs and calibre.rcx map no 205;8 (only 205;6 PMET), so device recognition and extraction "
                "do not change",
        checks=dict(drc=chk, flat_lup_esd=flat, supply_only_lvs=vcs, reference=dict(drc=ref_chk, flat_lup_esd=ref_flat)),
        matching_checks=counts, all_matching_checks_ran=set(counts) == set(MATCH_SET),
        drc_markers=sum(b.values()), reference_drc_markers=sum(a.values()),
        drc_changed_rules={r: [a.get(r, 0), b.get(r, 0)] for r in sorted(set(a) | set(b)) if a.get(r, 0) != b.get(r, 0)},
        lvs=new["checks"]["lvs"].get("verdict"), supply_only_lvs=v,
        erc_equal=new["checks"]["lvs"].get("erc_results_by_check") == old["checks"]["lvs"].get("erc_results_by_check"),
        erc=new["checks"]["lvs"].get("erc_results_by_check"), flat_lup_esd=fb, flat_equal=fa == fb)
    write_json(path, rec)
    return rec["sign_off"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    a = sub.add_parser("decision")
    for k in ("view", "chk", "flat", "vcs", "ref_chk", "ref_flat"):
        a.add_argument(k)
    a = sub.add_parser("overlay")
    a.add_argument("src")
    a.add_argument("out")
    a.add_argument("--marker", choices=sorted(LAYERS), default="ANARRAY_H")
    a = sub.add_parser("record")
    a.add_argument("identity")
    a.add_argument("src")
    a.add_argument("out_gds")
    a.add_argument("--marker", choices=sorted(LAYERS), default="ANARRAY_H")
    a = ap.parse_args()
    if a.action == "overlay":
        print(json.dumps(overlay(a.src, a.out, a.marker), indent=1))
    elif a.action == "decision":
        print(json.dumps(decision(a.view, a.chk, a.flat, a.vcs, a.ref_chk, a.ref_flat), indent=1))
    else:
        r = record(a.identity, a.src, a.out_gds, a.marker)
        print(json.dumps(dict(counts=r["result_counts"], results=r["results"]), indent=1))


if __name__ == "__main__":
    main()
