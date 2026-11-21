"""Validate the current physical plan against electrical sources; render its review view."""
import hashlib
import html
import itertools
import json
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
    hashes = dependencies(root)
    saved_path = root / 'Layout/results/current.json'
    saved = read('Layout/results/current.json') if saved_path.exists() else {}
    stale = saved.get('planning_inputs_sha256') != hashes
    evidence_inputs = saved.get('qualification_inputs_sha256')
    core_area = (boundary[2]-boundary[0])*(boundary[3]-boundary[1])
    rows = [{'block': b['id'], 'width_um': b['size'][0], 'height_um': b['size'][1],
             'area_um2': round(b['size'][0]*b['size'][1], 4), 'basis': b['basis'],
             'uncertainty': b['uncertainty']} for b in blocks]
    return {'valid': not errors, 'errors': errors, 'planning_projection_stale': stale,
            'qualification_applicability': ('unmeasured' if not evidence_inputs else
                                           'matching_recorded_inputs' if evidence_inputs == hashes else 'stale'),
            'live_oa_identity': 'not_queried_by_local_check; verify with native stream before claiming applicability',
            'routing': routing,
            'planning_inputs_sha256': hashes, 'area': {'units': 'um2', 'blocks': rows,
            'core_allocation': core_area, 'block_allocation': round(sum(b['area_um2'] for b in rows), 4),
            'routing_power_isolation_boundary_reserve': round(core_area-sum(b['area_um2'] for b in rows), 4),
            'die_area': None, 'io_area': None, 'status': 'coarse_allocation_not_final_area'},
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
                   planning={'view': 'floorplan.svg', 'area': 'area.json', 'status': 'coarse_plan_unimplemented',
                             'unresolved_budgets': report['unresolved_budgets']}, signoff=False)
    write_json(current_path, current)
    return {'view': str(target), 'area': str(root/'Layout/results/area.json'), 'signoff': False}
