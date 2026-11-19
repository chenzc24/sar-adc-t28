"""Read-only V4 benchmark: measured GDS geometry + attributed prior signoff/TT evidence.

Uses LayoutML's actual centroid function, not its built-in scenario scorecard.
Device roles and internal net anchors are explicitly mapped from the frozen generator;
this is not a general device extractor or a replacement for LVS. No OA writes/reruns.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import klayout.db as k

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'work/layout/comparator-redesign/official-v4.gds'
EVIDENCE = ROOT / 'Layout/results/comparator.json'
ENGINE = ROOT / 'work/layout/layoutml-v3-preview/LayoutML/explorations/AG-analog-matching-invariants/matching_engine.py'
OUT = ROOT / 'Layout/results/comparator_benchmark.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    assert evidence['physical_evidence'] == 'comp-v4-20261117-pex'
    assert sha(SOURCE) == evidence['gds_sha256']
    assert sha(ROOT / 'Layout/design/comparator.il') == evidence['generator_sha256']
    spec = importlib.util.spec_from_file_location('layoutml_matching', ENGINE)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    layout = k.Layout()
    layout.read(str(SOURCE))
    cell = layout.cell('sar_strongarm_t28_core')
    assert cell is not None and layout.dbu == 0.001
    dbu = layout.dbu
    mirror = k.Trans(2, True, 0, 0)  # reflect x -> -x
    assert mirror.trans(k.Point(123, 456)) == k.Point(-123, 456)

    def region(layer, datatype=0):
        index = layout.find_layer(layer, datatype)
        assert index is not None, (layer, datatype)
        return k.Region(cell.begin_shapes_rec(index)).merged()

    def rect_tuple(box):
        return (box.left, box.bottom, box.right, box.top)

    gates = region(6) & region(17)
    boxes = [p.bbox() for p in gates.each_merged()]
    assert len(boxes) == 14 and all(b.width() == 30 and b.height() == 500 for b in boxes)
    # Row order and roles: frozen comparator.il, independently LVS CORRECT.
    rows = [
        (250, ['RSTY', 'PLATN', 'RSTN', 'RSTP', 'PLATP', 'RSTX']),
        (-1050, ['LATN', 'INP', 'INN', 'LATP']),
        (-1890, ['INP', 'TL', 'TL', 'INN']),
    ]
    devices = {}
    for y, roles in rows:
        selected = sorted([b for b in boxes if b.center().y == y], key=lambda b: b.center().x)
        assert len(selected) == len(roles)
        for role, box in zip(roles, selected):
            devices.setdefault(role, []).append(rect_tuple(box))
    pairs = [('INP', 'INN'), ('LATN', 'LATP'), ('PLATN', 'PLATP'), ('RSTY', 'RSTX'), ('RSTN', 'RSTP')]
    matching = []
    for a, b in pairs:
        ra = k.Region([k.Box(*v) for v in devices[a]])
        rb = k.Region([k.Box(*v) for v in devices[b]])
        result = engine.check_sym_centroid_1d_2d({a: devices[a], b: devices[b]})
        matching.append(dict(pair=[a, b], fingers_each=len(devices[a]),
                             mirror_xor_um2=(ra.transformed(mirror) ^ rb).area() * dbu**2,
                             layoutml_common_centroid=result,
                             centroid_separation_um=[result['dx_dbu'] * dbu, result['dy_dbu'] * dbu]))

    # Metal-only connectivity through actual V1/V2 cuts. Labels/role anchors name
    # connected components; diffusion, gate/CO and device extraction remain LVS's job.
    metals = {layer: [k.Region(p) for p in region(layer).each_merged()] for layer in (31, 32, 33)}
    nodes = [(layer, poly) for layer, polys in metals.items() for poly in polys]
    parent = list(range(len(nodes)))

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def join(a, b):
        parent[find(a)] = find(b)

    via_hits = []
    for via, lower, upper in [(51, 31, 32), (52, 32, 33)]:
        for p in region(via).each_merged():
            cut = k.Region(p)
            hits = [i for i, (layer, poly) in enumerate(nodes) if layer in (lower, upper) and not (poly & cut).is_empty()]
            assert {nodes[i][0] for i in hits} == {lower, upper}, 'Via lacks landing metal'
            for i in hits[1:]:
                join(hits[0], i)
            via_hits.append((via, hits[0]))

    anchors = {name: (int(port['layer'][1:]) + 30, *[round(v / dbu) for v in port['center_um']])
               for name, port in evidence['ports'].items()}
    anchors.update(Y=(33, -390, 440), X=(33, 390, 440), TAIL=(32, 0, -1245))
    roots = {}
    for name, (layer, x, y) in anchors.items():
        point_box = k.Region(k.Box(x-1, y-1, x+1, y+1))
        hits = [i for i, (li, poly) in enumerate(nodes) if li == layer and not (poly & point_box).is_empty()]
        assert len(hits) == 1, (name, hits)
        roots[name] = find(hits[0])
    assert len(set(roots.values())) == 10, 'Distinct named metal networks were shorted'
    net_regions = {name: {li: k.Region() for li in (31, 32, 33)} for name in roots}
    for name, root in roots.items():
        for i, (li, poly) in enumerate(nodes):
            if find(i) == root:
                net_regions[name][li] += poly
    routes = []
    for a, b in [('VINP', 'VINN'), ('OUTP', 'OUTN'), ('Y', 'X')]:
        routes.append(dict(pair=[a, b], layers={f'M{li-30}': dict(
            area_a_um2=net_regions[a][li].area()*dbu**2,
            area_b_um2=net_regions[b][li].area()*dbu**2,
            mirror_xor_um2=(net_regions[a][li].transformed(mirror) ^ net_regions[b][li]).area()*dbu**2)
            for li in (31, 32, 33)},
            via_counts={name: {f'V{li-50}': sum(1 for via, i in via_hits if via == li and find(i) == roots[name])
                               for li in (51, 52)} for name in (a, b)}))

    # Boundary/dummy symmetry is only a geometric screen, not a foundry LDE model.
    environment = {f'{li}/{dt}': (region(li, dt).transformed(mirror) ^ region(li, dt)).area()*dbu**2
                   for li, dt in [(6, 0), (17, 0), (17, 7), (25, 0), (26, 0), (3, 0)]}
    # Extract actual OD ring holes and check gate footprints lie inside the cavities.
    cavities = []
    for p in region(6).each_merged():
        for h in range(p.holes()):
            cavities.append(k.Region(k.Polygon(list(p.each_point_hole(h)))))
    enclosure = k.Region()
    for cavity in cavities:
        enclosure += cavity
    outside_gate_area = (gates - enclosure).area() * dbu**2

    caps = evidence['grounded_interconnect_capacitance_fF']
    cap_pairs = []
    for a, b in [('VINP', 'VINN'), ('OUTP', 'OUTN'), ('Y', 'X')]:
        delta = abs(caps[a]-caps[b])
        cap_pairs.append(dict(pair=[a,b], a_fF=caps[a], b_fF=caps[b], delta_fF=delta,
                              imbalance_percent_of_mean=100*delta/((caps[a]+caps[b])/2)))
    independent = next(x for x in evidence['independent'] if x['run_id'] == 'comp-v4-tt-20261117')
    result = dict(
        schema='saradc-comparator-benchmark/1', frozen_run=evidence['physical_evidence'],
        method='Real frozen GDS measurement plus explicitly attributed prior Calibre/TT evidence; not the upstream canned scorecard',
        inputs={str(p.relative_to(ROOT)): sha(p) for p in [SOURCE, EVIDENCE, ENGINE, ROOT/'Layout/design/comparator.il', Path(__file__)]},
        dbu_um=dbu, bbox_dbu=rect_tuple(cell.bbox()), area_um2=cell.bbox().area()*dbu**2,
        aspect_ratio_height_over_width=cell.bbox().height()/cell.bbox().width(),
        gate_finger_count=len(boxes), device_assignment_source='Frozen generator row mapping, validated against actual OD intersection PO; not inferred from GDS names',
        device_gate_boxes_dbu=devices, matching=matching,
        common_centroid_verdict='Not common-centroid; mirror-symmetric design. Report gradient exposure, not automatic rejection without a centroid requirement.',
        feol_and_dummy_marker_mirror_xor_um2=environment,
        dummy_scope='Geometric symmetry only; dummy adequacy, full local context/LDE, well noise isolation and substrate coupling not qualified',
        ring_cavity_count=len(cavities), gate_area_outside_ring_cavities_um2=outside_gate_area,
        route_connectivity_scope='M1-M3 through V1/V2 only; terminal anchors from frozen generator/manifest; not independent LVS',
        unnamed_metal_components=len({find(i) for i in range(len(nodes))}-set(roots.values())),
        routes=routes, grounded_capacitance_pairs=cap_pairs,
        capacitance_scope=evidence['capacitance_scope'],
        mirror_coupling_difference_fF=evidence['largest_mirror_coupling_mismatch_fF'],
        prior_physical_checks=dict(drc=evidence['drc'], lvs=evidence['lvs'], pex=evidence['pex']),
        prior_tt_independent=independent,
        prior_tt_integrated_summary={key:evidence['integrated'][key] for key in ['run_id','result_sha256','scope','all_code_pass','pass_function_timing','all_screens_pass']},
        prior_tt_max_conversion_ns=max(f['conversion_ns'] for f in evidence['integrated']['frames']),
        unqualified=evidence['limitations'],
        no_aggregate_score_reason='No calibrated quality weights, accepted parasitic/matching limits, or independent layout corpus. Hard checks and descriptive metrics remain separate.',
        layoutml_roundtrip_evidence='Layout/experiment/info form/geometry_diff.json; prior 8-layer XOR failure is a conversion issue, not a V4 physical defect',
    )
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:result[key] for key in ['area_um2','matching','feol_and_dummy_marker_mirror_xor_um2','ring_cavity_count','gate_area_outside_ring_cavities_um2','unnamed_metal_components','routes','grounded_capacitance_pairs']}, indent=2))


if __name__ == '__main__':
    main()
