"""Validate the current physical plan against electrical sources; render its review view."""
import hashlib
import html
import json
from pathlib import Path

from Layout.project import ROOT, write_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="930" viewBox="0 0 {cw+44} {ch+62.5}">',
             '<rect width="220" height="232.5" fill="#f8fafc"/>',
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
    parts += [f'<text x="12" y="{ch+37}" font-size="4">Core allocation: {cw} x {ch} um ({cw*ch/1e6:.5f} mm2)</text>',
              '<text x="12" y="214" font-size="3.5">Green shows measured outlines. Blue shows reserved areas.</text>',
              '<text x="12" y="221" font-size="3.5">Grey: routing / supplies / isolation / boundary allowance.</text>',
              '<text x="12" y="228" font-size="3.5">Die / IO / guard rings / extracted budgets: not finalized.</text>', '</g></svg>']
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
