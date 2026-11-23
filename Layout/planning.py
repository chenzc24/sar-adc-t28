"""Validate the current physical plan against electrical sources; render its review view."""
import hashlib
import html
import itertools
import json
import math
from pathlib import Path

from Layout.project import ROOT, write_json

EPS = 1e-6


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def horizontal(s):
    return abs(s[0][1] - s[1][1]) < EPS


def on_segment(p, s):
    (x0, y0), (x1, y1) = s
    return min(x0, x1) - EPS <= p[0] <= max(x0, x1) + EPS and min(y0, y1) - EPS <= p[1] <= max(y0, y1) + EPS


def crossing(s, t):
    """Point where a horizontal and a vertical segment cross inside both, else None."""
    if horizontal(s) == horizontal(t):
        return None
    h, v = (s, t) if horizontal(s) else (t, s)
    x, y = v[0][0], h[0][1]
    if (min(h[0][0], h[1][0]) + EPS < x < max(h[0][0], h[1][0]) - EPS
            and min(v[0][1], v[1][1]) + EPS < y < max(v[0][1], v[1][1]) - EPS):
        return (round(x, 3), round(y, 3))


def shared(s, t):
    """Length two segments share on one centreline."""
    k = 1 if horizontal(s) else 0
    if horizontal(s) != horizontal(t) or abs(s[0][k] - t[0][k]) > EPS:
        return 0
    a, b = sorted((s[0][1-k], s[1][1-k])), sorted((t[0][1-k], t[1][1-k]))
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def enters(s, box):
    """True if the segment runs a positive length inside the open box."""
    k = 1 if horizontal(s) else 0
    lo, hi = sorted((s[0][1-k], s[1][1-k]))
    return box[k] < s[0][k] < box[k+2] and min(hi, box[3-k]) - max(lo, box[1-k]) > EPS


def touches(s, t):
    """True if two Manhattan segments meet or cross anywhere, ends included."""
    return all(max(min(s[0][k], s[1][k]), min(t[0][k], t[1][k])) <= min(max(s[0][k], s[1][k]), max(t[0][k], t[1][k])) + EPS
               for k in (0, 1))


def edges(bbox):
    (x0, y0), (x1, y1) = bbox
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return list(zip(c, c[1:] + c[:1]))


LAYER = {f'M{i}': i for i in range(1, 11)}
DIGITAL = {'digital_signal', 'digital_supply'}


def io_ring(plan, ring):
    """Chip-level checks of the IO ring plan (die coordinates) and its agreement with the floorplan."""
    errors, place = [], ring['adc_placement']
    pads = {p['position']: p for p in ring['pads']}
    regions = {r['id']: r for r in ring['reserved_regions']}
    paths, rules = ring['routes'], ring.get('route_rules', {})
    ox, oy = place['origin_um']
    close = lambda p, q: q is not None and abs(p[0]-q[0]) < 1e-3 and abs(p[1]-q[1]) < 1e-3
    left, bottom, right, top = plan['core_bbox']
    if not all(close(a, b) for a, b in zip(place['bbox_um'], [[left+ox, bottom+oy], [right+ox, top+oy]])):
        errors.append('IO ring places a different core outline')
    die = [v - o for v, o in zip(ring['die_bbox'], (ox, oy, ox, oy))]
    if plan.get('die_bbox') is None or any(abs(a-b) > 1e-3 for a, b in zip(plan['die_bbox'], die)):
        errors.append('Floorplan die_bbox differs from the IO ring plan')
    core = {k[4:]: xy for k, xy in plan['pins_um'].items() if k.startswith('ADC.')}
    for name in sorted(set(core) ^ set(place['pins_um'])):
        errors.append('ADC pin in only one of floorplan and IO ring: ADC.' + name)
    for name in sorted(set(core) & set(place['pins_um'])):
        if not close([core[name][0]+ox, core[name][1]+oy], place['pins_um'][name]):
            errors.append('ADC pin differs between floorplan and IO ring: ADC.' + name)
    if len(pads) != len(ring['pads']) or len(pads) != 2*(ring['ring']['width']+ring['ring']['height']):
        errors.append('IO ring needs one pad per ring position')

    def anchored(point, ref):
        """A route end sits on a pad's core pin, an ADC pin, or a region edge (the guard ring's centreline)."""
        if ref in pads:
            return close(point, pads[ref]['core_pin_um'])
        if ref.startswith('ADC.'):
            return close(point, place['pins_um'].get(ref[4:]))
        return ref in regions and any(
            on_segment(point, e) for e in edges(regions[ref].get('centerline') or regions[ref]['bbox']))
    segs = {k: list(zip(r['points_um'], r['points_um'][1:])) for k, r in paths.items()}
    (ax0, ay0), (ax1, ay1) = ring['ring_opening']
    adc = (*place['bbox_um'][0], *place['bbox_um'][1])
    for k, r in paths.items():
        if any((abs(a[0]-b[0]) > EPS) == (abs(a[1]-b[1]) > EPS) for a, b in segs[k]):
            errors.append('IO route is not Manhattan or repeats a point: ' + k)
        if abs(sum(abs(a[0]-b[0]) + abs(a[1]-b[1]) for a, b in segs[k]) - r['manhattan_length_um']) > 1e-3:
            errors.append('Recorded IO route length differs from the points: ' + k)
        for end, ref in ((r['points_um'][0], r['from']), (r['points_um'][-1], r['to'])):
            if not anchored(end, ref):
                errors.append(f'IO route end is not on {ref}: {k}')
            if ref in pads and pads[ref]['core_net'] != r['net']:
                errors.append(f'IO route net differs from the core net of pad {ref}: {k}')
        on_pad = [pads[ref]['core_pin_um'] for ref in (r['from'], r['to']) if ref in pads]  # pins sit inside the pad cell
        if not all(ax0-EPS <= x <= ax1+EPS and ay0-EPS <= y <= ay1+EPS for x, y in r['points_um']
                   if not any(close((x, y), q) for q in on_pad)):
            errors.append('IO route leaves the ring opening: ' + k)
        if any(enters(s, adc) for s in segs[k]):
            errors.append('IO route runs over the ADC core: ' + k)
        low = min(LAYER[m] for m in r['layers'])
        for g in regions.values():
            inside = any(enters(s, (*g['bbox'][0], *g['bbox'][1])) for s in segs[k])
            if inside and g.get('admits') and (r['class'] in DIGITAL) != (g['admits'] == 'digital'):
                errors.append(f'IO route {k} ({r["class"]}) enters {g["id"]}')
            if g['kind'] == 'decap' and inside and r['branch'] != g['branch']:
                errors.append(f'IO route {k} enters {g["id"]} of the {g["branch"]} branch')
            if g['kind'] == 'decap' and not inside and r['branch'] == g['branch'] and r['class'].endswith('_supply'):
                errors.append(f'IO supply route {k} misses its decoupling {g["id"]}')
            if 'cross_min_layer' in g and r['to'] != g['id'] and low < LAYER[g['cross_min_layer']] and any(
                    touches(s, e) for s in segs[k] for e in edges(g.get('centerline') or g['bbox'])):
                errors.append(f'IO route {k} crosses {g["id"]} below {g["cross_min_layer"]}')
            if 'ring_layer' in g and g['id'] not in (r['from'], r['to']) and g['ring_layer'] in r['layers'] and any(
                    touches(s, e) for s in segs[k] for e in edges(g['centerline'])):
                errors.append(f'IO route {k} crosses {g["id"]} on its layer {g["ring_layer"]}')
    for a, b in itertools.combinations(paths, 2):
        if any(touches(s, t) for s, t in itertools.product(segs[a], segs[b])):
            errors.append(f'IO routes touch: {a}/{b}')
    axis = rules.get('axis_die_x_um')
    for a, b in rules.get('mirrored_routes', []):
        pa, pb = paths[a]['points_um'], paths[b]['points_um']
        if len(pa) != len(pb) or not all(close([2*axis-x, y], q) for (x, y), q in zip(pa, pb)):
            errors.append(f'IO routes are not mirror images: {a}/{b}')
    refs = [r[end] for r in paths.values() for end in ('from', 'to')]
    for name in place['pins_um']:
        if refs.count('ADC.' + name) != 1:
            errors.append(f'ADC pin has {refs.count("ADC." + name)} IO routes: ADC.{name}')
    for position, p in pads.items():
        if refs.count(position) != (1 if p['core_net'] else 0):
            errors.append(f'Pad has {refs.count(position)} IO routes: {position} {p["name"]}')
        if (p['core_net'] is None) != (p['core_pin_um'] is None):
            errors.append('Pad core net and core pin disagree: ' + position)
    bonded = {p['name'] for p in pads.values() if 'direction' in p}  # digital I/O cells
    errors += [f'IO route {k} uses the bonded pad net {r["net"]}' for k, r in paths.items() if r['net'] in bonded]
    errors += pad_ring_rules(ring)
    return list(dict.fromkeys(errors)), {'pads': len(pads), 'routes': len(paths)}


ANALOG_CELLS = {'PDB3AC', 'PVDD3AC', 'PVSS3AC', 'PVDD1AC', 'PVSS1AC', 'PVSS2AC',
                'PVDD3A', 'PVSS3A', 'PVDD1A', 'PVSS1A', 'PVSS2A'}


def pad_ring_rules(ring):
    """Supply-cell rules of the TSMC N28 I/O application note (v1.4; sections cited) on the pad sequence."""
    errors, n = [], {'left': ring['ring']['height'], 'right': ring['ring']['height'],
                     'top': ring['ring']['width'], 'bottom': ring['ring']['width']}
    order = [f'{s}_{i}' for s in ('left', 'bottom', 'right', 'top') for i in range(n[s])]  # counterclockwise
    pads = {p['position']: p for p in ring['pads']}
    if sorted(order) != sorted(pads):
        return ['IO ring pads do not fill the ring positions']
    cell = lambda q: pads[q]['device']
    dom = [pads[q]['domain'] for q in order]
    for d in set(dom):  # one contiguous block per domain, the ring wrapping around
        if sum(dom[i] == d and dom[i-1] != d for i in range(len(order))) > 1:
            errors.append(f'IO ring domain {d} is split into more than one block')
    ends = {f'left_{n["left"]-1}', f'bottom_{n["bottom"]-1}', f'right_{n["right"]-1}', f'top_{n["top"]-1}'}
    for i, q in enumerate(order):
        a, b = order[i-1], q
        if a in ends:  # the corner cell sits between a and b (6.2, 9.8.2, 10.9)
            if dom[i-1] != dom[i]:
                errors.append(f'Corner between {a} and {b} joins two domains')
            elif cell(a) in ANALOG_CELLS:
                need = {'PVSS3AC', 'PVSS3A'}
                if not {cell(a), cell(b)} <= need:
                    errors.append(f'Analog corner between {a} and {b} needs a bonded PVSS3AC on both sides')
            elif not {cell(a), cell(b)} <= {'PVSS2DGZ', 'PVSS3DGZ'}:
                errors.append(f'Digital corner between {a} and {b} needs a bonded PVSS2DGZ on both sides')
        elif dom[i-1] != dom[i]:  # power cut between domains (9.8.3)
            for q2 in (a, b):
                if cell(q2) in ANALOG_CELLS and cell(q2) not in {'PVDD3AC', 'PVSS3AC', 'PVDD3A', 'PVSS3A'}:
                    errors.append(f'Analog pad beside the power cut at {a}/{b} must be PVDD3AC/PVSS3AC: {q2}')
    for d in sorted(set(dom)):
        cells = [cell(q) for q in order if pads[q]['domain'] == d]
        count = lambda *c: sum(x in c for x in cells)
        if set(cells) & {'PDB3AC', 'PVDD3AC', 'PVSS3AC', 'PVDD1AC', 'PVSS1AC'}:  # core-voltage analog (10.6, 9.7)
            for c, k in (('PVDD3AC', 3), ('PVSS3AC', 1), ('PVSS2AC', 1)):
                if count(c) < k:
                    errors.append(f'Analog domain {d} needs at least {k} bonded {c}, has {count(c)}')
            if count('PVSS2A'):
                errors.append(f'Analog domain {d} mixes PVSS2A with core-voltage cells')
            for name in {pads[q]['name'] for q in order if pads[q]['domain'] == d and cell(q) == 'PVDD1AC'}:
                if sum(pads[q]['name'] == name and cell(q) == 'PVDD1AC' for q in order) < 3:
                    errors.append(f'PVDD1AC net {name} needs at least 3 bonded cells')
        elif not set(cells) & ANALOG_CELLS:  # digital (3.4, 8.6, checklist 7-12)
            if count('PVDD2POC') != 1:
                errors.append(f'Digital domain {d} needs one and only one PVDD2POC, has {count("PVDD2POC")}')
            for cs, k, what in ((('PVDD1DGZ',), 3, 'PVDD1DGZ'), (('PVDD2DGZ', 'PVDD2POC'), 2, 'VDDPST cells'),
                                (('PVSS1DGZ', 'PVSS3DGZ'), 1, 'PVSS1DGZ'), (('PVSS2DGZ', 'PVSS3DGZ'), 1, 'PVSS2DGZ')):
                if count(*cs) < k:
                    errors.append(f'Digital domain {d} needs at least {k} bonded {what}, has {count(*cs)}')
            # Simultaneous switching (7.3, checklist 19-20): every I/O cell counted as an output, databook DF in ring['sso'].
            df = ring.get('sso', {}).get('driving_factor', {})
            io = [cell(q) for q in order if pads[q]['domain'] == d and 'direction' in pads[q]]
            for c in sorted(set(io) - set(df)):
                errors.append(f'Digital I/O cell {c} has no driving factor in sso')
            sdf = sum(df.get(c, 0) for c in io)
            for cs, k, what in ((('PVSS2DGZ', 'PVSS3DGZ'), math.ceil(round(sdf, 6)), 'VSSPST cells'),
                                (('PVDD2DGZ', 'PVDD2POC'), math.ceil(round(sdf / 1.1, 6)), 'VDDPST cells')):
                if count(*cs) < k:
                    errors.append(f'Digital domain {d} needs at least {k} bonded {what} for simultaneous switching '
                                  f'(DF sum {sdf:.3f}), has {count(*cs)}')
    vss = {pads[q]['name'] for q in order if cell(q) in {'PVSS1DGZ', 'PVSS3DGZ', 'PVSS2AC', 'PVSS2A'}}
    if len(vss) > 1:  # the global ESD bus carries one label (2.2)
        errors.append(f'Cells supplying the global VSS bus carry different names: {sorted(vss)}')
    return errors


def pin_net(name, interfaces):
    """Net of INST.PORT[@access] from the electrical port order; SAR macro and ADC edge pins use the net name."""
    inst, port = name.split('.', 1)
    port = port.split('@')[0]
    if inst not in interfaces['top_instances']:
        return port
    entry = interfaces['top_instances'][inst]
    ports = [p.upper() for p in interfaces['masters'][entry['master']]['ports']]
    return entry['nodes'][ports.index(port.upper())]


def routes(plan, interfaces):
    """Plan-view checks of the planned centrelines; layer, width and spacing stay with the routing review."""
    paths, rules = plan.get('planned_paths', {}), plan.get('routing_rules', {})
    errors, pins = [], {}
    for name, xy in plan.get('pins_um', {}).items():
        try:
            pins[name] = (pin_net(name, interfaces), xy)
        except (KeyError, ValueError):
            errors.append('Unknown pin: ' + name)
    net = {name: route['net'] for name, route in paths.items()}
    segs = {name: list(zip(route['points_um'], route['points_um'][1:])) for name, route in paths.items()}
    for name, route in paths.items():
        if any((abs(a[0]-b[0]) > EPS) == (abs(a[1]-b[1]) > EPS) for a, b in segs[name]):
            errors.append('Planned path is not Manhattan or repeats a point: ' + name)
        if abs(sum(abs(a[0]-b[0]) + abs(a[1]-b[1]) for a, b in segs[name]) - route['manhattan_length_um']) > 1e-3:
            errors.append('Recorded length differs from the points: ' + name)
        # Each end lands on a pin of the same net or on another path of that net; a dummy stub only at its start.
        points = route['points_um']
        for end in points[:1] if route.get('dummy') else [points[0], points[-1]]:
            if not (any(n == net[name] and abs(xy[0]-end[0]) < 1e-3 and abs(xy[1]-end[1]) < 1e-3 for n, xy in pins.values())
                    or any(o != name and net[o] == net[name] and any(on_segment(end, s) for s in segs[o]) for o in paths)):
                errors.append(f'Planned path end is not anchored: {name} at {end}')
    for pin, (n, xy) in sorted(pins.items()):
        if pin not in plan.get('unrouted_pins', {}) and not any(
                net[p] == n and any(on_segment(xy, s) for s in segs[p]) for p in paths):
            errors.append('Pin has no planned path: ' + pin)
    found = set()
    for a, b in itertools.combinations(paths, 2):
        if net[a] == net[b]:
            continue
        for s, t in itertools.product(segs[a], segs[b]):
            if shared(s, t) > EPS:
                errors.append(f'Planned paths share a track: {a}/{b}')
            point = crossing(s, t)
            if point:
                found.add((tuple(sorted((net[a], net[b]))), point))
        for p, q in ((a, b), (b, a)):
            if any(on_segment(v, s) for v in paths[p]['points_um'] for s in segs[q]):
                errors.append(f'Planned path touches another net: {p}/{q}')
    # Region tracks drawn over an x range (the output-channel VSS shields) cross planned paths as well.
    for region in plan.get('reserved_regions', []):
        for track in region.get('tracks', []):
            if 'x_um' not in track:
                continue
            seg = ((track['x_um'][0], track['y_um']), (track['x_um'][1], track['y_um']))
            for p in paths:
                if net[p] == track['net']:
                    continue
                for s in segs[p]:
                    point = crossing(seg, s)
                    if point:
                        found.add((tuple(sorted((track['net'], net[p]))), point))
    declared = {(tuple(sorted(c['nets'])), tuple(round(v, 3) for v in c['at_um'])) for c in plan.get('crossings', [])}
    errors += [f'Undeclared crossing {n[0]}/{n[1]} at {list(p)}' for n, p in sorted(found - declared)]
    errors += [f'Declared crossing is not in the paths: {n[0]}/{n[1]} at {list(p)}' for n, p in sorted(declared - found)]
    margin = rules.get('pin_access_margin_um', 0.3)
    allowed = {(o['path'], o['block']) for o in plan.get('over_block', [])}
    for b in plan['blocks']:
        (x, y), (w, h) = b['origin'], b['size']
        box = (x+margin, y+margin, x+w-margin, y+h-margin) if min(w, h) > 2*margin else (x, y, x+w, y+h)
        for name in paths:
            hit = any(enters(s, box) for s in segs[name])
            if hit != ((name, b['id']) in allowed):
                errors.append(f'Planned path enters block {b["id"]} without a declaration: {name}' if hit else
                              f'Declared block crossing is not in the paths: {name}/{b["id"]}')
    axis = rules.get('symmetry_axis_x_um')
    for a, b in rules.get('mirrored_paths', []):
        mirror = [[2*axis - x, y] for x, y in paths[a]['points_um']]
        if len(mirror) != len(paths[b]['points_um']) or any(
                abs(p[0]-q[0]) > 1e-3 or abs(p[1]-q[1]) > 1e-3 for p, q in zip(mirror, paths[b]['points_um'])):
            errors.append(f'Mirrored paths differ: {a}/{b}')
    wire = {}
    for name, route in paths.items():
        wire[net[name]] = wire.get(net[name], 0) + route['manhattan_length_um']
    for group in rules.get('matched_nets', []):
        lengths = [wire.get(n, 0) for n in group['nets']]
        if max(lengths) - min(lengths) > group['tolerance_um']:
            errors.append('Matched nets differ in wire length: ' + '/'.join(group['nets']))
    summary = {'planned_paths': len(paths), 'crossings': len(found),
               'matched_wire_um': {n: round(wire.get(n, 0), 4) for g in rules.get('matched_nets', []) for n in g['nets']}}
    return list(dict.fromkeys(errors)), summary


def dependencies(root=ROOT):
    names = ['design/manifest.json', 'design/top/adc_top.scs',
             'Layout/design/manifest.json', 'Layout/design/floorplan.json',
             'Layout/specs/interfaces.json', 'Layout/specs/constraints.json']
    ring = json.loads((root / 'Layout/design/floorplan.json').read_text(encoding='utf-8')).get('io_ring')
    if ring and (root / ring['plan']).exists():
        names.append(ring['plan'])
    design = json.loads((root / 'design/manifest.json').read_text())
    names += sorted({'design/' + entry['file'] for entry in design['subcircuits'].values()})
    return {name: digest(root / name) for name in names}


def check(root=ROOT):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding='utf-8'))
    design = read('design/manifest.json')
    physical = read('Layout/design/manifest.json')
    plan = read('Layout/design/floorplan.json')
    interfaces = read('Layout/specs/interfaces.json')
    constraints = read('Layout/specs/constraints.json')
    errors = []
    if physical['electrical_design_id'] != design['design_id']:
        errors.append('Physical plan is bound to a different electrical design')
    for name, expected in physical['electrical_sources_sha256'].items():
        if digest(root / name) != expected:
            errors.append('Changed electrical source: ' + name)
    for master, entry in interfaces['masters'].items():
        actual = design['subcircuits'].get(master)
        if not actual or entry['ports'] != actual['ports']:
            errors.append('Port order/membership changed: ' + master)
    if plan['units'] != 'um' or constraints['units'] != 'um':
        errors.append('Coordinates must use um')
    boundary = plan['core_bbox']
    blocks = plan['blocks']
    if len({b['id'] for b in blocks}) != len(blocks):
        errors.append('Duplicate placement identity')
    for i, b in enumerate(blocks):
        x, y = b['origin']; w, h = b['size']
        if w <= 0 or h <= 0 or b['orientation'] != 'R0':
            errors.append('Invalid dimensions or unsupported orientation: ' + b['id'])
        if not (boundary[0] <= x < x+w <= boundary[2] and boundary[1] <= y < y+h <= boundary[3]):
            errors.append('Outside core allocation: ' + b['id'])
        if b['basis'] not in ['measured_oa_bbox', 'space_reservation']:
            errors.append('Unspecified area basis: ' + b['id'])
        if b['basis'] == 'measured_oa_bbox' and not b.get('evidence'):
            errors.append('Missing measured area evidence: ' + b['id'])
        for other in blocks[:i]:
            a, c = other['origin']; d, e = other['size']
            if min(x+w, a+d) > max(x, a) and min(y+h, c+e) > max(y, c):
                errors.append('Overlapping blocks: ' + b['id'] + '/' + other['id'])
    planned_instances = [inst for b in blocks for inst in b['instances']]
    # Electrical-only instances (model loads) stay in the netlist but are never drawn.
    not_drawn = interfaces.get('not_drawn_instances', {})
    if set(not_drawn) - set(interfaces['top_instances']):
        errors.append('Not-drawn instances must be top instances')
    expected_instances = [name for name in interfaces['top_instances'] if name not in not_drawn]
    if sorted(planned_instances) != sorted(expected_instances):
        errors.append('Floorplan must allocate each drawn top instance exactly once')
    for name, route in interfaces['routes'].items():
        if route['from'] not in expected_instances or route['to'] not in expected_instances:
            errors.append('Unknown route endpoint: ' + name)
    route_errors, routing = routes(plan, interfaces)
    errors += route_errors
    ring, ring_summary = None, None
    if plan.get('io_ring'):
        if (root / plan['io_ring']['plan']).exists():
            ring = read(plan['io_ring']['plan'])
            ring_errors, ring_summary = io_ring(plan, ring)
            errors += ring_errors
        else:
            errors.append('Missing IO ring plan: ' + plan['io_ring']['plan'])
    hashes = dependencies(root)
    saved_path = root / 'Layout/results/current.json'
    saved = read('Layout/results/current.json') if saved_path.exists() else {}
    stale = saved.get('planning_inputs_sha256') != hashes
    evidence_inputs = saved.get('qualification_inputs_sha256')
    core_area = (boundary[2]-boundary[0])*(boundary[3]-boundary[1])
    die = plan.get('die_bbox')
    die_area = round((die[2]-die[0])*(die[3]-die[1]), 4) if die else None
    opening = ring['ring_opening'] if ring else None
    io_area = round(die_area-(opening[1][0]-opening[0][0])*(opening[1][1]-opening[0][1]), 4) if ring and die else None
    rows = [{'block': b['id'], 'width_um': b['size'][0], 'height_um': b['size'][1],
             'area_um2': round(b['size'][0]*b['size'][1], 4), 'basis': b['basis'],
             'uncertainty': b['uncertainty']} for b in blocks]
    return {'valid': not errors, 'errors': errors, 'planning_projection_stale': stale,
            'qualification_applicability': ('unmeasured' if not evidence_inputs else
                                           'matching_recorded_inputs' if evidence_inputs == hashes else 'stale'),
            'live_oa_identity': 'not_queried_by_local_check; verify with native stream before claiming applicability',
            'routing': routing, 'io_ring': ring_summary,
            'planning_inputs_sha256': hashes, 'area': {'units': 'um2', 'blocks': rows,
            'core_allocation': core_area, 'block_allocation': round(sum(b['area_um2'] for b in rows), 4),
            'routing_power_isolation_boundary_reserve': round(core_area-sum(b['area_um2'] for b in rows), 4),
            'die_area': die_area, 'io_area': io_area, 'status': 'coarse_allocation_not_final_area'},
            'unresolved_budgets': [key for key, val in constraints['electrical_budgets'].items() if val['limit'] is None],
            'signoff': False}


def render(root=ROOT):
    root = Path(root)
    report = check(root)
    if not report['valid']:
        raise ValueError('; '.join(report['errors']))
    plan = json.loads((root/'Layout/design/floorplan.json').read_text())
    left, bottom, right, top = plan['core_bbox']
    cw, ch = right-left, top-bottom
    vw, vh = cw+44, ch+69.5
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw*4}" height="{vh*4}" viewBox="0 0 {vw} {vh}">',
             f'<rect width="{vw}" height="{vh}" fill="#f8fafc"/>',
             '<g font-family="Arial,sans-serif" fill="#102a43">',
             '<text x="12" y="12" font-size="6">SAR8 / coarse floorplan</text>',
             '<text x="12" y="20" font-size="3.5">Allocation only; no OA placement or routing change</text>',
             f'<rect x="12" y="28" width="{cw}" height="{ch}" fill="#e8eef3" stroke="#536878" stroke-width="0.5"/>']
    for b in plan['blocks']:
        x, y = b['origin']; w, h = b['size']; sx, sy = x-left+12, 28+top-y-h
        color = '#b7ddd4' if b['basis'] == 'measured_oa_bbox' else '#d5ddf4'
        font = 2.5 if w < 30 else 3.5
        parts += [f'<rect x="{sx}" y="{sy}" width="{w}" height="{h}" fill="{color}" stroke="#38556b" stroke-width="0.5"/>',
                  f'<text x="{sx+w/2}" y="{sy+h/2-1}" font-size="{font}" text-anchor="middle">{html.escape(b["label"])}</text>',
                  f'<text x="{sx+w/2}" y="{sy+h/2+4}" font-size="{min(font,3)}" text-anchor="middle">{w} x {h} um</text>']
    # Reserved regions (dashed) and planned centerlines are review aids, not routed geometry.
    strokes = {'decap': '#15803d', 'fill_exclusion': '#b91c1c', 'keepout': '#7f1d1d', 'guard': '#7c3aed'}
    for region in plan.get('reserved_regions', []):
        (x0, y0), (x1, y1) = region['bbox']
        parts.append(f'<rect x="{x0-left+12}" y="{28+top-y1}" width="{x1-x0}" height="{y1-y0}" fill="none" '
                     f'stroke="{strokes.get(region.get("kind"), "#9a6b00")}" stroke-width="0.3" stroke-dasharray="1,0.6"/>')
    for name, route in plan.get('planned_paths', {}).items():
        color = ('#c2410c' if route.get('net') in ('TOPN', 'TOPP') else '#6b7280' if route.get('dummy') else
                 '#0e7490' if route.get('net') in ('VINN', 'VINP') else '#1d4ed8')
        points = ' '.join(f'{x-left+12},{28+top-y}' for x, y in route['points_um'])
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="0.25"/>')
    for c in plan.get('crossings', []):
        parts.append(f'<circle cx="{c["at_um"][0]-left+12}" cy="{28+top-c["at_um"][1]}" r="0.35" fill="none" '
                     'stroke="#111827" stroke-width="0.12"/>')
    parts += [f'<text x="12" y="{ch+37}" font-size="4">Core allocation: {cw} x {ch} um ({cw*ch/1e6:.5f} mm2)</text>',
              f'<text x="12" y="{ch+44}" font-size="3.5">Green: measured outlines. Dashed: channels (brown), decoupling (green),</text>',
              f'<text x="12" y="{ch+51}" font-size="3.5">fill exclusion (red), keep-out (dark red), guard ring (purple).</text>',
              f'<text x="12" y="{ch+58}" font-size="3.5">Lines: TOP (orange), VIN (teal), signals (blue), balance stubs (grey).</text>',
              f'<text x="12" y="{ch+65}" font-size="3.5">Circles: declared crossings. Die / IO / extracted budgets: not finalized.</text>',
              '</g></svg>']
    target = root/'Layout/results/floorplan.svg'
    target.write_text('\n'.join(parts)+'\n', encoding='utf-8')
    write_json(root/'Layout/results/area.json', report['area'])
    current_path = root/'Layout/results/current.json'
    current = json.loads(current_path.read_text()) if current_path.exists() else {}
    current.update(planning_inputs_sha256=report['planning_inputs_sha256'],
                   planning={'view': 'floorplan.svg', 'area': 'area.json', 'status': 'floorplan_projection',
                             'unresolved_budgets': report['unresolved_budgets']}, signoff=False)
    write_json(current_path, current)
    return {'view': str(target), 'area': str(root/'Layout/results/area.json'), 'signoff': False}
