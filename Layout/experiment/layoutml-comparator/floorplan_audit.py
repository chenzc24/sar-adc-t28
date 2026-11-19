"""Measure the compiled StrongARM floorplan in nm, independently of its renderer."""
from collections import defaultdict
from heapq import heappop, heappush
from math import hypot


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def distance(a, b):
    return hypot(max(a[0]-b[2], b[0]-a[2], 0), max(a[1]-b[3], b[1]-a[3], 0))


def union_area(rects):
    """Integrate the union of rectangles, counting a metal pad or elbow only once."""
    xs = sorted({x for b in rects for x in (b[0], b[2])})
    area = 0
    for lo, hi in zip(xs, xs[1:]):
        spans = sorted((b[1], b[3]) for b in rects if b[0] <= lo and hi <= b[2])
        end = None
        for y, yy in spans:
            area += (hi-lo) * (yy-y if end is None else max(0, yy-max(end, y)))
            end = yy if end is None else max(end, yy)
    return area


def well_components(rects):
    groups = []
    for rect in rects:
        joined, separate = [rect], []
        for group in groups:
            if any(distance(rect, other) == 0 for other in group):
                joined.extend(group)
            else:
                separate.append(group)
        groups = separate + [joined]
    return groups


def physical(ast, layers, bbox):
    from meso_compiler import transform_local_box
    wells = well_components(layers['nwell'])
    summaries = [{'pmos': [], 'body_taps': []} for _ in wells]
    substrate_taps, n_active, bad_wells, active = [], [], [], []
    for pc in ast['pcells']:
        entry = ast['_storeObj']['realizations'][pc['realization']]
        primitive = entry['layers_dbu_nm']
        kind = 'diff' if pc['devices'] else 'tap'
        r = transform_local_box(primitive[kind][0], *pc['atNm'], pc['orient'])
        active.append((pc['id'], r))
        names = [s.split()[1] for s in pc['devices']]
        pmos = bool(names and pc['devices'][0].split()[2] == 'pch_mac')
        body = entry['ports_local_nm'][0]['net'] if not names else None
        ids = [i for i, well in enumerate(wells) if any(overlaps(r, b) for b in well)]
        if pmos or body == 'VDD':
            inside = (len(ids) == 1 and
                      any(b[0] <= r[0] and b[1] <= r[1] and b[2] >= r[2] and b[3] >= r[3]
                          for b in wells[ids[0]]))
            if not inside:
                bad_wells.append(pc['id'])
            else:
                summaries[ids[0]]['pmos' if pmos else 'body_taps'].extend(names or [pc['id']])
        else:
            if ids:
                bad_wells.append(pc['id'])
            if names:
                n_active.append((pc['id'], r))
            else:
                substrate_taps.append(r)
    for i,w in enumerate(wells):
        summaries[i]['box_nm'] = [min(b[0] for b in w),min(b[1] for b in w),
                                  max(b[2] for b in w),max(b[3] for b in w)]
    area = (bbox[2]-bbox[0])*(bbox[3]-bbox[1])
    metals = {m:union_area(layers[m]) for m in ('met1','met2','met3')}
    return {
        'metal_union_nm2': metals,
        'metal_bbox_coverage_pct': {m:round(v*100/area,3) for m,v in metals.items()},
        'opposite_implant_overlaps':sum(overlaps(a,b) for a in layers['nsdm'] for b in layers['psdm']),
        'foreign_active_overlaps':[[p,q] for i,(p,a) in enumerate(active) for q,b in active[:i] if overlaps(a,b)],
        'dummy_crossings_over_active_or_tap':sum(overlaps(a,b) for a in layers['poly_dummy'] for _,b in active),
        'well_assignment_errors':bad_wells, 'well_components':summaries,
        'min_nmos_active_to_nwell_nm':round(min(distance(r,b) for _,r in n_active for w in wells for b in w),2),
        'nearest_substrate_tap_edge_distance_by_nmos_bank_nm':{
            name:round(min(distance(r,t) for t in substrate_taps),2) for name,r in n_active}}


def centre(rect):
    return ((rect[0]+rect[2])//2, (rect[1]+rect[3])//2)


def measure_decision(route, pin, starts):
    """Shortest metal-centreline paths, with each physical cut counted separately."""
    tracks, nodes, links = [], defaultdict(set), defaultdict(list)
    def point(layer, xy):
        p = (layer, *xy)
        nodes[layer].add(p)
        return p
    def edge(a,b,length,cuts):
        links[a].append((b,length,cuts))
        links[b].append((a,length,cuts))
    for path in route['paths']:
        for a,b in zip(path['ptsNm'],path['ptsNm'][1:]):
            tracks.append((path['layer'],point(path['layer'],a),point(path['layer'],b)))
    for via in route['vias']:
        a,b = via['metalLayers']
        xy = centre(via['bBox'])
        edge(point(a,xy),point(b,xy),0,1)
    target = point(pin['layer'],centre(pin['box']))
    for p in starts.values():
        point(p[0], p[1:])
    # Add crossings even when neither path declares an endpoint at the junction.
    for l,a,b in tracks:
        if a[1] != b[1]:
            continue
        for ll,c,d in tracks:
            if l==ll and c[2]==d[2] and min(a[2],b[2])<=c[2]<=max(a[2],b[2]) and min(c[1],d[1])<=a[1]<=max(c[1],d[1]):
                point(l,(a[1],c[2]))
    for l,a,b in tracks:
        points = sorted(p for p in nodes[l] if min(a[1],b[1])<=p[1]<=max(a[1],b[1])
                        and min(a[2],b[2])<=p[2]<=max(a[2],b[2]))
        for p,q in zip(points,points[1:]):
            edge(p,q,abs(p[1]-q[1])+abs(p[2]-q[2]),0)
    costs = {target:(0,0)}
    prev = {}
    todo = [(0,0,target)]
    while todo:
        length,cuts,p = heappop(todo)
        if (length,cuts) != costs[p]:
            continue
        for q,w,v in links[p]:
            alt = length+w,cuts+v
            if q not in costs or alt < costs[q]:
                costs[q] = alt
                prev[q] = p,w
                heappush(todo,(*alt,q))
    result = {}
    for label,p in starts.items():
        if p not in costs:
            continue
        lengths = defaultdict(int)
        length,cuts = costs[p]
        while p != target:
            nxt,w = prev[p]
            if w:
                lengths[p[0]] += w
            p = nxt
        result[label] = {'centreline_nm':length,'cuts':cuts,'per_layer_nm':dict(lengths)}
    return result


def decision_access(ast, ports):
    result = {}
    for net in ('OUTP','OUTN'):
        route = next(r for r in ast['routes'] if r['net']==net)
        pin = next(p for p in ast['cellPorts'] if p['name']==net)
        starts = {}
        for pc in ast['pcells']:
            for i,device in enumerate(pc['devices']):
                name = device.split()[1]
                if not name.startswith(('MNLAT','MPLAT')):
                    continue
                kind = name[1]
                gate, pad = ports[pc['id'],f'G_{i+1}']
                if gate==net:
                    starts[kind+'_gate_M1'] = ('met1',*centre(pad))
                for idx in (i,i+1):
                    sd, pad = ports[pc['id'],f'SD_{idx}']
                    if sd!=net:
                        continue
                    hits=[centre(v['bBox']) for v in route['vias'] if v['mBot']==1 and
                          pad[0]<=centre(v['bBox'])[0]<=pad[2] and pad[1]<=centre(v['bBox'])[1]<=pad[3]]
                    if len(hits)==1:
                        starts[kind+'_drain_V1'] = ('met1',*hits[0])
        result[net]=measure_decision(route,pin,starts)
    return result
