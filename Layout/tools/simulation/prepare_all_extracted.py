"""Stage 2 of issue #12: the closed-loop ADC with every frozen block extraction and ideal top-level wiring.

The frozen views are Layout/results/current.json integration.freeze. Each MOS corner uses the paired
interconnect corner (TT: typical, SS: CWORST_T, FF: CBEST_T) for the coupled XREF/CDAC extraction of the
filled stream se-xref-peripheral-dense, the comparator v8 extraction with VDD/VSS RC, the SAR macro
sar8_se_core/layout_r3 and the foundry cell LPE of the remaining cells. The Bootstrap core
boot-core-20261121 is its typical extraction at every corner; --corner-bootstrap uses its re-extraction at the
paired interconnect corner instead (Layout/tools/physical/bootstrap_rc_corner.py, run family allxc). --bootstrap
ID requalifies a revised core: its typical extraction at TT and its paired re-extractions ID-cworst-t and
ID-cbest-t at SS cold and FF hot (run family bs<revision>, for example bsr2 for view layout_r2). Wiring
between blocks is ideal.

The deck, stimuli and analyzer are tools.saradc.single_edge_lpe. Gain-corrected code targets and signed
plate settling use the standalone weights of the same XREF/CDAC extraction at the same MOS corner; `gain`
prepares those standalone runs from the frozen TT weight run xref-fill-tt-after-dense.

  python -m Layout.tools.simulation.prepare_all_extracted gain ssc
  python -m Layout.tools.simulation.prepare_all_extracted adc tt verify --revision a
  python -m Layout.tools.simulation.prepare_all_extracted adc ssc verify --corner-bootstrap
  python -m Layout.tools.simulation.prepare_all_extracted adc ssc verify --bootstrap boot-core-r2b-20261122
  python -m Layout.tools.simulation.prepare_all_extracted gate RUN_ID --submit SAME_HOST
"""
import argparse
import json
import re

from Layout.design.reference_driver import COMBINED, DRIVER_SOURCE
from Layout.project import ROOT, evidence
from Layout.tools.simulation import bootstrap_pex, prepare_sar_se
from Layout.tools.simulation.prepare_full_sim import pull, sha
from Layout.tools.simulation.prepare_reference_driver import analog_nodes, fetch_pex, pin_order, replace_adc
from tools.saradc import single_edge_lpe as lpe

FROZEN_XREF = 'se-xref-peripheral-dense'
BOOTSTRAP = 'boot-core-20261121'
TT_GAIN = 'xref-fill-tt-after-dense'
CORNERS = {
    'tt': dict(rc='typical', xref=FROZEN_XREF, gain=TT_GAIN,
               comparator='comp-v8-20261120-pex-typical-supplies', sar='sar-se-r3-lib', boot=BOOTSTRAP),
    'ssc': dict(rc='cworst_T', xref=FROZEN_XREF + '-cworst-t', gain='xref-dense-ssc-gain-cw',
                comparator='comp-v8-20261120-pex-cworst-t-supplies', sar='sar-se-r3-cw', boot=BOOTSTRAP + '-cworst-t'),
    'ffh': dict(rc='cbest_T', xref=FROZEN_XREF + '-cbest-t', gain='xref-dense-ffh-gain-cb',
                comparator='comp-v8-20261120-pex-cbest-t-supplies', sar='sar-se-r3-cb', boot=BOOTSTRAP + '-cbest-t'),
}
XREF_DRC = {'M9.DN.3', 'M8.DN.1', 'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1', 'DIODMY_L:WARNING'}
COMPARATOR_DRC = {'OD.DN.3', 'PO.DN.3', 'PO.DN.3.1', 'DIODMY_L:WARNING', 'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1'}
COMPARATOR_PORTS = ['CLK', 'OUTN', 'OUTP', 'VDD', 'VINN', 'VINP', 'VSS']
# Stage 2 pass limits (issue #12): acquisition residual and plate settling at each decision.
SETTLING_LIMIT_LSB = .15
# Earlier extracted ADC runs stopped at a 2.5 GB limit. The first all-extracted batch (revision a) reserved
# 6 GiB and peaked at 2.19 GB; 4 GiB keeps 1.8x headroom and still admits under the thu-song user cgroup,
# whose usage includes the page cache of written waveforms.
SIMULATION_RSS_MIB = 4096
BUDGET_RSS_MIB = 4096
# Route check for the Stage 4 budgets. Each top-level route is a distributed RC between the real driver and
# the real receiver, so every driver keeps its load; an ideal delay element would isolate both sides and
# hide the load (the comparator ran faster with its outputs unloaded in sar8-allxb-ssc-verify-a).
# Planned centreline lengths: Layout/design/floorplan.json planned_paths on branch layout/toplevel-floorplan
# (93646b1, not merged). COMP_P/COMP_N include their riser and clock-balance jogs.
PLANNED_ROUTE_UM = dict(CMP_CLK=55.555, COMP_P=57.045, COMP_N=57.045, PRESET=66.8,
                        TOP_SAMPLER=20.615, TOP_COMPARATOR=3.64, **{'CODE%d' % i: 58.96 + .98 * i for i in range(8)})
# The SAR macro's routed 1x-metal nets fit 0.086-0.089 fF/um (ground plus coupling counted once, all three
# interconnect corners). 0.2 fF/um covers VSS-shielded corridor tracks and switching neighbours. The resistance
# fit is unstable (2-38 ohm/um with vias and contacts mixed in); 20 ohm/um is taken from its upper range.
WIRE_C_F_PER_UM = .2e-15
WIRE_R_OHM_PER_UM = 20.
ROUTE_SEGMENTS = 4
# Proposed comparator_input_route_capacitance_F: 0.8 % of C_eff (specs/arch.json gain_error_allocation).
TOP_ROUTE_F = 9.8e-15
# (route, driver-side net, receiver-side net); the SAR-side nets keep the analyzer's probe names.
DIGITAL_ROUTES = ([('CMP_CLK', 'CMP_CLK', 'CMP_CLK_RT'), ('COMP_P', 'COMP_P_RT', 'COMP_P'), ('COMP_N', 'COMP_N_RT', 'COMP_N')]
                  + [(n, n, n + '_RT') for n in ['CODE%d' % i for i in range(8)] + ['PRESET']])


def route_check(scale, top_F=TOP_ROUTE_F):
    routes = [dict(name=name, driver=drv, receiver=rcv, length_um=scale * PLANNED_ROUTE_UM[name],
                   r_ohm=scale * PLANNED_ROUTE_UM[name] * WIRE_R_OHM_PER_UM,
                   c_F=scale * PLANNED_ROUTE_UM[name] * WIRE_C_F_PER_UM) for name, drv, rcv in DIGITAL_ROUTES]
    return dict(scale=scale, wire_c_F_per_um=WIRE_C_F_PER_UM, wire_r_ohm_per_um=WIRE_R_OHM_PER_UM,
                segments=ROUTE_SEGMENTS, routes=routes, top_F=top_F,
                top_sampler_r_ohm=scale * PLANNED_ROUTE_UM['TOP_SAMPLER'] * WIRE_R_OHM_PER_UM,
                planned_lengths='Layout/design/floorplan.json planned_paths, branch layout/toplevel-floorplan 93646b1',
                method=('%d-segment RC ladder per digital route between its real driver and receiver; TOP: %.1f fF to '
                        'ground on each CDAC TOP net and the scaled sampler-route resistance between the Bootstrap '
                        'output and TOP; the 3.6 um comparator TOP branch is left ideal' % (ROUTE_SEGMENTS, top_F * 1e15)))


def apply_routes(top, check):
    """Insert the route RC networks into the bound top (bytes)."""
    text = top.decode()

    def rebind(name, mapping):
        nonlocal text
        m = re.search(r'(?m)^([ \t]*' + name + r'[ \t]+\()([^)]+)(\)[ \t]+\S+[ \t]*)$', text)
        if not m:
            raise ValueError('Missing top instance ' + name)
        pins = m[2].split()
        if not set(mapping) <= set(pins):
            raise ValueError('Unexpected binding of ' + name)
        text = text[:m.start(2)] + ' '.join(mapping.get(p, p) for p in pins) + text[m.end(2):]

    rebind('XCOMP', {'CMP_CLK': 'CMP_CLK_RT', 'COMP_N': 'COMP_N_RT', 'COMP_P': 'COMP_P_RT'})
    rebind('XCDAC', {n: n + '_RT' for n in ['CODE%d' % i for i in range(8)] + ['PRESET']})
    rebind('XBOOTP', {'TOPP': 'TOPP_BS'})
    rebind('XBOOTN', {'TOPN': 'TOPN_BS'})
    n = check['segments']
    rows = []
    for r in check['routes']:
        nodes = [r['driver']] + ['%s_W%d' % (r['name'], k) for k in range(1, n)] + [r['receiver']]
        rows += ['    RRT_%s_%d (%s %s) resistor r=%.6g' % (r['name'], k, nodes[k], nodes[k + 1], r['r_ohm'] / n)
                 for k in range(n)]
        rows += ['    CRT_%s_%d (%s 0) capacitor c=%.6gf' % (r['name'], k, nodes[k],
                                                             r['c_F'] / (2 * n if k in (0, n) else n) * 1e15)
                 for k in range(n + 1)]
    for side in 'PN':
        rows += ['    RRT_TOP%s (TOP%s_BS TOP%s) resistor r=%.6g' % (side, side, side, check['top_sampler_r_ohm']),
                 '    CRT_TOP%s (TOP%s 0) capacitor c=%.6gf' % (side, side, check['top_F'] * 1e15)]
    end = re.search(r'(?m)^ends sar_adc8_join_r4\b', text)
    return (text[:end.start()] + '\n'.join(rows) + '\n' + text[end.start():]).encode()


def prefixed(files, prefix):
    """Rename an xRC file set and its include statements so two extractions can share one deck."""
    out = {}
    for name, data in files.items():
        text, count = re.subn(rb'(?m)^(include ")(extracted\.scs[^"]*")', rb'\1' + prefix.encode() + rb'\2', data)
        out[prefix + name] = text
    return out


def xref_package(identity, gain_run, rc, routes=None):
    """The coupled XREF/CDAC extraction bound in place of XCDAC and XREF, with its standalone weights.
    routes: optional route check (route_check) applied to the bound top."""
    payload, manifest = fetch_pex(identity)
    frozen = manifest if identity == FROZEN_XREF else fetch_pex(FROZEN_XREF)[1]
    if manifest['top'] != COMBINED or manifest['target_bits'] != list(range(8)):
        raise ValueError('Expected the eight-bit coupled XREF/CDAC extraction')
    if manifest['gds']['sha256'] != frozen['gds']['sha256']:
        raise ValueError('Extraction is not of the frozen filled stream ' + FROZEN_XREF)
    if manifest.get('interconnect_rc', 'typical') != rc:
        raise ValueError('Extraction interconnect corner differs: %s' % manifest.get('interconnect_rc'))
    if set(manifest['checks']['drc']['markers_by_rule']) - XREF_DRC:
        raise ValueError('Unexpected XREF/CDAC DRC markers')
    if manifest['distributed_supplies'] != frozen['distributed_supplies']:
        raise ValueError('Supply extraction differs from the frozen stream')
    source = payload['extracted.scs']
    pins = pin_order(source, COMBINED, manifest['ports'])
    analog = analog_nodes(source, range(8), every_plate=True)
    plates = {side: [analog['plates']['b%s%d' % (side, bit)] for bit in range(8)] for side in 'np'}
    groups = {side: [[('xdut.xcdac.' + n).replace('\\', '').lower() for n in nodes] for nodes in plates[side]]
              for side in 'np'}
    if len({s for side in 'np' for g in groups[side] for s in g}) != 510:
        raise ValueError('Expected all 510 physical capacitor terminals')
    saves = [('save ' + ' '.join('XDUT.XCDAC.' + n for n in nodes)).encode() for side in 'np' for nodes in plates[side]]
    # The schematic gate nets are internal to the coupled extraction; read each at one switch-gate contact.
    probes = {'xdut.' + key: 'XDUT.XCDAC.' + nodes[0] for key, nodes in analog['gates'].items()}
    gain_inputs = lpe.retained_inputs(lpe.RUNS / gain_run, ['physical.json', 'extracted.scs'])
    if json.loads(gain_inputs['physical.json']).get('id') != identity or \
            sha(gain_inputs['extracted.scs']) != manifest['checks']['pex']['sha256']:
        raise ValueError('Standalone weights %s use a different extraction' % gain_run)
    weights, weights_sha = lpe.measured_weights(gain_run, manifest['gds']['sha256'])
    files = prefixed({n: b for n, b in payload.items() if n.startswith('extracted.scs')}, 'xref_')
    files['xref_physical.json'] = payload['physical.json']
    reference = DRIVER_SOURCE.removeprefix('design/')

    def bind(sources):
        staged = {k: sources[k] for k in ('top/adc_top.scs', reference, 'dut.scs')}
        replace_adc(staged, pins, COMBINED)
        dut = staged['dut.scs'].replace(b'include "extracted.scs"', b'include "xref_extracted.scs"')
        top = staged['top/adc_top.scs']
        if routes:
            top = apply_routes(top, routes)
        sources.update({'top/adc_top.scs': top, 'dut.scs': dut})

    bundle = dict(view='xref-' + rc.lower().replace('_t', ''), files=files, groups=groups, saves=saves,
                  gds=manifest['gds']['sha256'], source=identity, schematic=None, weights=weights,
                  weights_id=gain_run, weights_sha=weights_sha)
    context = dict(xref_physical_evidence=identity, xref_interconnect_rc=rc, xref_filled_stream=FROZEN_XREF,
                   xref_extracted_sha256=manifest['checks']['pex']['sha256'], xref_ports=pins,
                   xref_gate_probes=probes, xref_distributed_supplies=manifest['distributed_supplies'])
    scope = 'coupled XREF/CDAC extraction %s (%s, filled stream %s)' % (identity, rc, FROZEN_XREF)
    signals = []
    if routes:
        context['route_check'] = routes
        # Both ends of every route, for measure_route_delay.py.
        signals = [('xdut.' + n).lower() for r in routes['routes'] for n in (r['driver'], r['receiver'])]
        signals += ['xdut.topp_bs', 'xdut.topn_bs']
        scope += ('; route check: %g x planned floorplan lengths at %.2f fF/um and %g ohm/um, %.1f fF per TOP net'
                  % (routes['scale'], routes['wire_c_F_per_um'] * 1e15, routes['wire_r_ohm_per_um'], routes['top_F'] * 1e15))
    return dict(bundle=bundle, bind=bind, probes=probes, context=context, scope=scope, signals=signals)


def comparator_package(identity, rc):
    """The comparator v8 extraction with distributed VDD/VSS behind the schematic positional interface."""
    remote = evidence(identity)
    raw = pull(remote + '/manifest.json')
    manifest = json.loads(raw)
    checks = manifest['checks']
    if manifest['case'] != 'comparator' or manifest.get('error') or checks['lvs']['verdict'] != 'CORRECT':
        raise ValueError('Need completed comparator physical evidence')
    if set(checks['drc']['markers_by_rule']) - COMPARATOR_DRC:
        raise ValueError('Unresolved comparator DRC')
    corner = manifest['interconnect_rc']
    if (corner if rc == 'typical' else corner['corner']) != ('typical (lab deck)' if rc == 'typical' else rc):
        raise ValueError('Comparator interconnect corner differs')
    if manifest['derived_from']['distributed_supplies'] != ['VDD', 'VSS']:
        raise ValueError('Expected the comparator extraction with VDD/VSS RC')
    source_hash = sha((ROOT / 'design/xtor/comparator/comparator.scs').read_bytes())
    if ('* Electrical source SHA256 ' + source_hash).encode() not in pull(remote + '/reference.cdl'):
        raise ValueError('Physical reference belongs to a different comparator source')
    originals = {'extracted.scs': checks['pex']['sha256'], **checks['pex']['companion_sha256']}
    files = {}
    for name, digest in originals.items():
        if not re.fullmatch(r'extracted\.scs(?:\.[A-Za-z0-9_.-]+)?', name):
            raise ValueError('Unexpected extraction filename')
        files[name] = pull(remote + '/pex/' + name)
        if sha(files[name]) != digest:
            raise ValueError('Comparator extraction differs from its manifest: ' + name)
    top = manifest['top']
    joined = re.sub(r'\\\s*\n\s*', ' ', files['extracted.scs'].decode())
    pins = re.search(r'(?mi)^subckt\s+' + re.escape(top) + r'\s*\(([^)]+)\)', joined)[1].split()
    if sorted(pins) != sorted(COMPARATOR_PORTS):
        raise ValueError('Unexpected extracted comparator ports')
    renamed, count = re.subn(r'(?m)^(subckt|ends)\s+' + re.escape(top) + r'\b', r'\1 comparator_extracted',
                             files['extracted.scs'].decode())
    if count != 2:
        raise ValueError('Unexpected extracted definition count')
    files['extracted.scs'] = renamed.encode()
    files = prefixed(files, 'cmp_')
    files['comparator_pex.scs'] = ('simulator lang=spectre\ninclude "cmp_extracted.scs"\n'
                                   'subckt sar_strongarm_t28 (' + ' '.join(COMPARATOR_PORTS) + ')\n'
                                   'XPEX (' + ' '.join(pins) + ') comparator_extracted\n'
                                   'ends sar_strongarm_t28\n').encode()
    files['comparator_physical.json'] = raw

    def use(dut):
        old = b'include "xtor/comparator/comparator.scs"'
        if dut.count(old) != 1:
            raise ValueError('Expected one schematic comparator include')
        return dut.replace(old, b'include "comparator_pex.scs"')

    context = dict(comparator_pex=dict(physical_evidence=identity, interconnect_rc=rc, gds_sha256=manifest['gds']['sha256'],
                                       extracted_original_sha256=originals, extracted_ports=pins,
                                       distributed_supplies=['VDD', 'VSS']))
    scope = 'comparator v8 extraction %s (%s, VDD/VSS RC)' % (identity, rc)
    return dict(files=files, use=use, context=context, scope=scope)


def sar_macro(identity, rc):
    package = prepare_sar_se.macro(identity)
    if package['record']['interconnect_rc'] != rc:
        raise ValueError('SAR macro interconnect corner differs: ' + package['record']['interconnect_rc'])
    return package


def prepare_adc(corner, kind, revision, route_scale=None, corner_bootstrap=False, bootstrap=None):
    """route_scale: route check at this multiple of the planned floorplan lengths (run family allxr, scored
    against the routed-design limits of issue #12, Stage 6 column).
    corner_bootstrap: the Bootstrap core extraction at the paired interconnect corner (run family allxc).
    bootstrap: physical ID of a revised core's typical extraction; the paired re-extraction replaces it at SS
    cold and FF hot (run family bs<revision>)."""
    spec = CORNERS[corner]
    if lpe.CELL_RC[corner] != spec['rc'].lower():
        raise ValueError('Cell LPE and extraction corners differ')
    if route_scale and (corner_bootstrap or bootstrap):
        raise ValueError('Route checks use the Stage 2 Bootstrap; run them separately')
    if bootstrap and corner_bootstrap:
        raise ValueError('--bootstrap already pairs the interconnect corner')
    family = 'allxr' if route_scale else 'allxc' if corner_bootstrap else 'allx'
    if bootstrap:
        revision_view = bootstrap_pex.view(bootstrap)
        if not re.fullmatch(r'layout_r\d{1,2}', revision_view):
            raise ValueError('--bootstrap needs a revision view layout_r<N>, not ' + revision_view)
        boot = bootstrap if corner == 'tt' else bootstrap + '-' + spec['rc'].lower().replace('_', '-')
        if bootstrap_pex.view(boot) != revision_view:
            raise ValueError('Corner extraction belongs to another view: ' + boot)
        family = 'bs' + revision_view.split('_', 1)[1]
    else:
        boot = spec['boot'] if corner_bootstrap else BOOTSTRAP
    if bootstrap_pex.interconnect(boot) != (spec['rc'] if corner_bootstrap or bootstrap else 'typical'):
        raise ValueError('Bootstrap extraction interconnect corner differs: ' + boot)
    routes = route_check(route_scale) if route_scale else None
    return lpe.prepare(corner, kind, revision=revision, macro=sar_macro(spec['sar'], spec['rc']), bootstrap=boot,
                       xref=xref_package(spec['xref'], spec['gain'], spec['rc'], routes),
                       comparator=comparator_package(spec['comparator'], spec['rc']),
                       family=family,
                       settling_limit=.25 if routes else SETTLING_LIMIT_LSB,
                       rss_mib=BUDGET_RSS_MIB if routes else SIMULATION_RSS_MIB)


def prepare_gain(corner, run_id=None):
    """Standalone eight-bit weights of the corner XREF/CDAC extraction at that MOS corner.

    The frozen TT weight run supplies the fixture and analyzer bytes. Only the extraction, MOS section,
    temperature, supply and the logic levels of the CODE, PRESET and track commands change; the references
    stay at 0 and 0.9 V behind the same 50 ohm / 4 pF fixture."""
    spec = CORNERS[corner]
    run_id = run_id or spec['gain']
    if corner == 'tt' or not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', run_id):
        raise ValueError('TT weights exist; select ssc or ffh and a valid run ID')
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    template = json.loads((lpe.RUNS / TT_GAIN / 'recipe.json').read_bytes())
    names = [f['name'] for f in template['files'] if f['source'].startswith('work/decks/')]
    blobs = lpe.retained_inputs(lpe.RUNS / TT_GAIN, names)
    payload, manifest = fetch_pex(spec['xref'])
    if manifest.get('interconnect_rc') != spec['rc'] or manifest['top'] != COMBINED:
        raise ValueError('Unexpected corner extraction')
    old = sorted(n for n in blobs if n.startswith('extracted.scs'))
    if old != sorted(n for n in payload if n.startswith('extracted.scs')):
        raise ValueError('Extracted file set differs from the TT weight run')
    blobs.update({n: payload[n] for n in old}, **{'physical.json': payload['physical.json']})
    condition = json.loads((ROOT / 'specs/corners.json').read_text(encoding='utf-8'))[corner]
    vdd = '%g' % condition['vdd_v']
    deck = blobs['test.scs'].decode()

    def swap(text, pattern, new, count):
        text, n = re.subn(pattern, new, text)
        if n != count:
            raise ValueError('Unexpected fixture text: ' + pattern)
        return text

    deck = swap(deck, r'section=ttmacro_mos_moscap\b', 'section=%smacro_mos_moscap' % condition['mos'].lower(), 1)
    deck = swap(deck, r'\btemp=27 tnom=27\b', 'temp=%d tnom=27' % condition['temperature_c'], 1)
    deck = swap(deck, r'(?m)^(VV_post \(post_vdd 0\) vsource dc=)0\.9$', r'\g<1>' + vdd, 1)
    lines = []
    for line in deck.splitlines(keepends=True):
        if line.startswith(('V_post_code', 'V_post_track', 'V_post_preset')):
            line = swap(line, r'(?<![\d.])0\.9(?![\d])', vdd, len(re.findall(r'(?<![\d.])0\.9(?![\d])', line)))
        lines.append(line)
    deck = ''.join(lines)
    if not re.search(r'(?m)^VS_post_refp \(post_refp_src 0\) vsource dc=0\.9$', deck) or \
            re.search(r'(?<![\d.])0\.9(?![\d])', ''.join(l for l in lines if l.startswith(('V_post_code', 'V_post_track')))):
        raise ValueError('Reference or command levels not as intended')
    blobs['test.scs'] = deck.encode()
    blobs['library_include.scs'] = (ROOT / ('tb/common/platform/library_lpe_%s.scs' % lpe.CELL_RC[corner])).read_bytes()
    context = json.loads(blobs['context.json'])
    scope = ('Standalone coupled XREF/CDAC at %s %s V %d C with the %s extraction %s. Zero, eight one-hot commands, '
             'full scale, zero. 19 ns plateaus; project CDAC measurement; fixture and analyzer of %s.'
             % (condition['mos'], vdd, condition['temperature_c'], spec['rc'], spec['xref'], TT_GAIN))
    context.update(run_id=run_id, corner=corner, condition=condition, physical_evidence=spec['xref'],
                   gds_sha256=manifest['gds']['sha256'], interconnect_rc=spec['rc'], scope=scope,
                   template_run=TT_GAIN, reference_v=[0, .9])
    blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
    dest.mkdir(parents=True)
    for name, blob in blobs.items():
        (dest / name).write_bytes(blob)
    recipe = {k: template[k] for k in ('schema_version', 'design_id', 'entry', 'analyzer', 'resources', 'spectre_args',
                                       'summary_signals', 'expected_stop_s')}
    recipe.update(run_id=run_id, qualification_scope=scope, test_conditions=context,
                  inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b)) for n, b in blobs.items()])
    path = dest / 'recipe.json'
    path.write_text(json.dumps(recipe, indent=2) + '\n')
    return path


ANALYSES = {
    'split': ('measure_reference_split.py',
              'Analysis-only split of the signed plate error of %s at each decision into plate settling against the '
              'instantaneous reference pins, the static pin offset measured 88 ns into each frame, and dynamic '
              'reference recovery'),
    'routes': ('measure_route_delay.py',
               'Analysis-only 50 %% delay and receiver transition of every top-level route of the route check %s'),
    'gate': ('measure_bootstrap_gate.py',
             'Analysis-only main-switch gate discharge of both Bootstrap channels after every sample close of %s: '
             'onset, fall rate, overdrive at the first comparator clock and at fixed delays, settled hold level'),
}


def prepare_analysis(kind, source_run_id, run_id=None):
    """Analysis-only job (ANALYSES) on the waveform of a completed all-extracted ADC run."""
    analyzer, scope = ANALYSES[kind]
    run_id = run_id or source_run_id + '-' + kind
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', run_id):
        raise ValueError('Invalid run ID')
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    source = json.loads((lpe.RUNS / source_run_id / 'recipe.json').read_bytes())
    if source['test_conditions'].get('kind') == 'restart':
        raise ValueError('The restart stimulus has no per-frame decision record')
    if kind == 'routes' and 'route_check' not in source['test_conditions']:
        raise ValueError('Not a route-check run: ' + source_run_id)
    dest.mkdir(parents=True)
    blobs = {analyzer: (ROOT / 'Layout/tools/analysis' / analyzer).read_bytes(),
             'native_stream.py': (ROOT / 'tools/saradc/measure/native_stream.py').read_bytes()}
    for name, blob in blobs.items():
        (dest / name).write_bytes(blob)
    scope = scope % source_run_id
    spec = dict(schema_version=2, kind='analysis_only', source_run_id=source_run_id, run_id=run_id,
                design_id=source['design_id'], analyzer=analyzer,
                inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b)) for n, b in blobs.items()],
                resources=dict(source['resources'], analysis_rss_mib=1024, analysis_wall_seconds=10800),
                spectre_args=source['spectre_args'], summary_signals=source['summary_signals'],
                expected_stop_s=source['expected_stop_s'], qualification_scope=scope,
                test_conditions=dict(source['test_conditions'], split_source_run_id=source_run_id))
    path = dest / 'recipe.json'
    path.write_text(json.dumps(spec, indent=2) + '\n')
    return path


if __name__ == '__main__':
    from tools.saradc.__main__ import engine
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    g = sub.add_parser('gain')
    g.add_argument('corner', choices=['ssc', 'ffh'])
    g.add_argument('--run-id')
    a = sub.add_parser('adc')
    a.add_argument('corner', choices=CORNERS)
    a.add_argument('kind', choices=lpe.CODES)
    a.add_argument('--revision', default='a')
    a.add_argument('--route-scale', type=float, metavar='SCALE',
                   help='Route check: RC routes at SCALE x the planned floorplan lengths, TOP_ROUTE_F per TOP net')
    a.add_argument('--corner-bootstrap', action='store_true',
                   help='Bootstrap core extraction at the paired interconnect corner (run family allxc)')
    a.add_argument('--bootstrap', metavar='PHYSICAL_ID',
                   help='Revised Bootstrap core (typical extraction ID); paired corner re-extraction at ssc/ffh')
    analyses = []
    for kind in ANALYSES:
        r = sub.add_parser(kind, help='Analysis-only %s job on a completed run (same host as the source)' % kind)
        r.add_argument('source_run_id')
        r.add_argument('--run-id')
        analyses.append(r)
    for p in [g, a] + analyses:
        p.add_argument('--submit', metavar='HOST', choices=engine().HOSTS,
                       help='Register the recipe on this managed host and queue its simulation or analysis')
    args = ap.parse_args()
    if args.action == 'gain':
        path = prepare_gain(args.corner, args.run_id)
    elif args.action in ANALYSES:
        path = prepare_analysis(args.action, args.source_run_id, args.run_id)
    else:
        path = prepare_adc(args.corner, args.kind, args.revision, args.route_scale, args.corner_bootstrap,
                           args.bootstrap)
    print(path.relative_to(ROOT).as_posix())
    if args.submit:
        run_id = json.loads(path.read_text())['run_id']
        # An analysis-only job starts its analysis; the others queue a simulation.
        print(json.dumps(dict(registration=engine().register(path.relative_to(ROOT).as_posix(), host=args.submit),
                              submission=engine().phase('analyze' if args.action in ANALYSES else 'submit', run_id,
                                                        queue=True)), indent=2))
