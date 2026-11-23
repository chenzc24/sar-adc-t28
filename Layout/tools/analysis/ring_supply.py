"""Pad-ring terms of the Stage 1 budget: reference routes, branch feeds and the shared analog bus.

Geometry comes from Layout/design/io_ring.json. Sheet resistance is the PDK tech LEF value
(tsmcn28_9lm6X1Z1URDL.tlef, RESISTANCE RPERSQ) with the temperature coefficients and the rcworst_T
thickness of RC_IRCX_CRN28HPC+_1P9M+UT-ALRDL_6X1Z1U; the LEF value is taken at 25 C. The TACVDD and
TACVSS buses of the analog pads are 33.66 and 34.22 um wide on each of M3-M7 (the narrowest strips of
PVDD3AC_V_G, PVSS3AC_V_G and PFILLER20A_G in the 9-metal tphn28hpcpgv18 LEF).

The coupled supply model is a linear circuit: node capacitance, resistors, series R-L branches and
current loads, discretized exactly per time step. AVSS of the board is the reference node."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RING = ROOT / 'Layout/design/io_ring.json'
# ohm/sq at 25 C, TC1 (1/C), TC2 (1/C^2) and the typical/rcworst_T thickness ratio.
SHEET = dict(M8=dict(ohm_sq=.022, tc1=3.649e-3, tc2=-8.535e-7, rcworst=.85 / .81634),
             M9=dict(ohm_sq=.005, tc1=4.444e-3, tc2=-1.556e-6, rcworst=3.5 / 3.34779),
             Mx=dict(ohm_sq=.428, tc1=1.937e-3, tc2=-4.641e-7, rcworst=.09 / .08447))
M8_CAP = dict(area_pf_um2=6.025e-5, edge_pf_um=9.3e-5)           # tech LEF, to substrate
BUS_WIDTH_UM = dict(vdd=5 * 33.66, vss=5 * 34.22)                 # total over M3-M7
BUS_H_PER_UM = .2e-12       # per rail; coplanar 34 um strips 2.2 um apart give about 0.41 nH/mm of loop
BUS_NODE_F = .3e-12         # bus metal and pad parasitics to substrate per pad position
CORNER_PATH_UM = 110.       # bus path through a 110 um corner cell, centreline about 55 um in
REF_ROUTE_WIDTH_UM = 4.
REF_ROUTE_H_PER_UM = .1e-9 / 92.6   # the 7 x 7 assumption (0.1 nH per rail at 92.6 um), scaled
SUPPLY_ROUTE_H_PER_UM = .5e-12      # per rail; the pair rails run 60 um apart over most of their length
SUPPLY_ROUTE_WIDTH_UM = 10.         # stated width of the AVDD/AVSS routes and feeds, M8
BULK_ESR_OHM_PER_RAIL = 2.
FEED_LIMIT_OHM = 6.


def rsh(layer, temp_c=25., rcworst=False):
    s, dt = SHEET[layer], temp_c - 25.
    return s['ohm_sq'] * (1 + s['tc1'] * dt + s['tc2'] * dt * dt) * (s['rcworst'] if rcworst else 1.)


def load_ring(path=RING):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parallel(*values):
    return 1 / sum(1 / v for v in values)


def reference_routes(ring=None):
    """Per-rail resistance, inductance and capacitance of the two pad-to-core routes in parallel."""
    ring = ring or load_ring()
    length = ring['supply_plan']['reference_route_length_um']
    w = REF_ROUTE_WIDTH_UM
    rails = {}
    for rail in ('VREFP', 'VREFN'):
        ls = (length[rail + '_a'], length[rail + '_b'])
        eq = parallel(*ls)
        rails[rail] = dict(lengths_um=ls, parallel_equivalent_um=eq,
                           ohm=dict(m8_25c=rsh('M8') * eq / w, m8_125c_rcworst=rsh('M8', 125, True) * eq / w,
                                    m8_m40c=rsh('M8', -40) * eq / w, m9_m40c=rsh('M9', -40) * eq / w),
                           cap_f=sum(l * (w * M8_CAP['area_pf_um2'] + 2 * M8_CAP['edge_pf_um']) for l in ls) * 1e-12,
                           h=REF_ROUTE_H_PER_UM * eq)
    vals = list(rails.values())
    return dict(width_um=w, layer='M8 (M9 gives the low end)', rails=rails,
                route_ohm=max(r['ohm']['m8_25c'] for r in vals),
                route_ohm_range=(min(r['ohm']['m9_m40c'] for r in vals), max(r['ohm']['m8_125c_rcworst'] for r in vals)),
                route_h=max(r['h'] for r in vals), route_f=max(r['cap_f'] for r in vals))


def bus_position(pos, pitch=60.):
    """Distance along the analog bus, which runs from right_8 over the top side to left_6."""
    side, k = pos.split('_')
    k = int(k)
    if side == 'right' and k == 8:
        return 0.
    if side == 'top':
        return CORNER_PATH_UM + 60. + pitch * k
    if side == 'left':
        return 2 * (CORNER_PATH_UM + 60.) + pitch * 8 + pitch * k
    raise ValueError('Not on the analog bus: ' + pos)


def branches(ring=None):
    ring = ring or load_ring()
    out = {}
    for name, b in ring['supply_plan']['adc_branches'].items():
        pv = [p for p, n in b['pads'].items() if n == 'AVDD'][0]
        ps = [p for p, n in b['pads'].items() if n == 'AVSS'][0]
        rv, rs_ = [r for r in b['routes'] if r.startswith('AVDD')][0], [r for r in b['routes'] if r.startswith('AVSS')][0]
        out[name] = dict(vdd_pad=pv, vss_pad=ps, bulk_f=b['pad_decap_planning_pF'] * 1e-12,
                         route_um=(b['route_length_um'][rv] - b['feed_length_um'][rv],
                                   b['route_length_um'][rs_] - b['feed_length_um'][rs_]),
                         feed_um=(b['feed_length_um'][rv], b['feed_length_um'][rs_]))
    return out


def feed_table(ring=None, width_um=SUPPLY_ROUTE_WIDTH_UM):
    """Loop resistance (VDD plus VSS path) of each branch at a stated M8 width, and the widths it needs."""
    hot = rsh('M8', 125, True)
    stack = parallel(hot, rsh('M9', 125, True))
    rows = {}
    for name, b in branches(ring).items():
        feed, full = sum(b['feed_um']), sum(b['feed_um']) + sum(b['route_um'])
        rows[name] = dict(feed_um=b['feed_um'], route_to_bulk_um=b['route_um'],
                          bulk_to_pin_ohm=dict(m8_25c=rsh('M8') * feed / width_um, m8_125c_rcworst=hot * feed / width_um),
                          pad_to_pin_ohm=dict(m8_25c=rsh('M8') * full / width_um, m8_125c_rcworst=hot * full / width_um),
                          width_for_1_ohm_bulk_to_pin_um=dict(m8=hot * feed, m8_m9_stacked=stack * feed),
                          width_for_6_ohm_pad_to_pin_um=dict(m8=hot * full / FEED_LIMIT_OHM))
    return dict(width_um=width_um, layer='M8', rows=rows,
                definition='bulk_to_pin counts against the 6 ohm limit together with the in-core strap; '
                           'pad_to_pin adds the route ahead of the bulk, which sits in series with the bonds')


def expm(m):
    s = max(0, int(np.ceil(np.log2(max(np.abs(m).sum(axis=1).max(), 1e-300)))) + 1)
    x, e, t = m / 2. ** s, np.eye(len(m)), np.eye(len(m))
    for k in range(1, 20):
        t = t @ x / k
        e = e + t
    for _ in range(s):
        e = e @ e
    return e


class Circuit:
    """Linear RLC network with current loads; every node also carries node_f to the reference node."""

    def __init__(self, node_f=10e-15):
        self.index, self.node_f = {}, node_f
        self.caps, self.res, self.ind, self.loads = [], [], [], []

    def node(self, name):
        return None if name == '0' else self.index.setdefault(name, len(self.index))

    def c(self, a, b, f):
        self.caps.append((self.node(a), self.node(b), f))

    def r(self, a, b, ohm):
        self.res.append((self.node(a), self.node(b), ohm))

    def l(self, a, b, h, ohm=0.):
        self.ind.append((self.node(a), self.node(b), h, ohm))

    def load(self, a, b, name):
        """A current drawn out of node a and returned into node b."""
        self.loads.append((self.node(a), self.node(b), name))

    def discretize(self, dt):
        n, m, k = len(self.index), len(self.ind), len(self.loads)
        cm, g = np.eye(n) * self.node_f, np.zeros((n, n))

        def stamp(mat, a, b, v):
            for i in (a, b):
                if i is not None:
                    mat[i, i] += v
            if a is not None and b is not None:
                mat[a, b] -= v
                mat[b, a] -= v
        for a, b, f in self.caps:
            stamp(cm, a, b, f)
        for a, b, ohm in self.res:
            stamp(g, a, b, 1 / ohm)
        inc, lh, lr = np.zeros((n, m)), np.zeros(m), np.zeros(m)
        for j, (a, b, h, ohm) in enumerate(self.ind):
            if a is not None:
                inc[a, j] = 1
            if b is not None:
                inc[b, j] = -1
            lh[j], lr[j] = h, ohm
        src = np.zeros((n, k))
        for j, (a, b, _) in enumerate(self.loads):
            if a is not None:
                src[a, j] = -1
            if b is not None:
                src[b, j] = 1
        ci = np.linalg.inv(cm)
        a_mat = np.zeros((n + m, n + m))
        a_mat[:n, :n], a_mat[:n, n:] = -ci @ g, -ci @ inc
        a_mat[n:, :n], a_mat[n:, n:] = inc.T / lh[:, None], -np.diag(lr / lh)
        aug = np.zeros((n + m + k, n + m + k))
        aug[:n + m, :n + m], aug[:n, n + m:] = a_mat * dt, ci @ src * dt
        e = expm(aug)
        return e[:n + m, :n + m], e[:n + m, n + m:]

    def run(self, events, dt=2e-12, tend=100e-9):
        """events: load name -> [(start_s, charge_c, width_s)] as triangular current pulses."""
        p, q = self.discretize(dt)
        t = np.arange(int(tend / dt)) * dt
        u = np.zeros((len(t), len(self.loads)))
        for j, (_, _, name) in enumerate(self.loads):
            for t0, charge, w in events.get(name, ()):
                x = t - t0
                u[:, j] += np.where((x >= 0) & (x < w), charge * 2 / w * (1 - np.abs(2 * x / w - 1)), 0.)
        um = np.vstack([.5 * (u[:-1] + u[1:]), np.zeros((1, u.shape[1]))])
        x, v = np.zeros(p.shape[0]), np.empty((len(t), len(self.index)))
        for j in range(len(t)):
            v[j] = x[:len(self.index)]
            x = p @ x + q @ um[j]
        return t, v

    def voltage(self, v, name):
        i = self.node(name)
        return np.zeros(len(v)) if i is None else v[:, i]


def chip(shared_bus=True, bus_temp_c=25., core_feed_ohm=None, width_um=SUPPLY_ROUTE_WIDTH_UM,
         pad_coupling='asymmetric', pad_coupling_f=.5e-12, trunk_coupling_f=0., system=None, ring=None,
         blocks=None, drawn=None):
    """The three AVDD/AVSS branches, their pads and bonds, the shared bus and the reference pads.

    core_feed_ohm: name -> loop resistance of the in-core strap from the boundary pins to the block
    decoupling. pad_coupling: how each reference pad's capacitance reaches the bus ('asymmetric' puts
    all of it from VREFP pads to TACVDD and from VREFN pads to TACVSS, the differential worst case).
    blocks: name -> block decoupling (default: the Stage 1 region sizes).
    drawn: name -> dict(bulk_f, esr_ohm_per_rail, pad_to_bulk_ohm, bulk_to_pin_ohm) to replace the planned bulk, its
    ESR and the 10 um M8 route model with drawn values (loop resistances, split equally between the rails)."""
    ring = ring or load_ring()
    s = system or dict(source_ohm=1., board_bypass_f=100e-9, board_esr_ohm=.01, board_esl_h=.5e-9,
                       pin_h=2e-9, pin_ohm=.2, series_ohm=15., span_cap_f=8e-12)
    br = branches(ring)
    blocks = blocks or dict(analog=9.32e-12, pair=10.07e-12, sar=8.25e-12)
    core_feed_ohm = core_feed_ohm or dict(analog=1., pair=1., sar=1.)
    ckt = Circuit()
    for rail in ('bvdd', 'bvrp', 'bvrn'):          # board AVDD and the two reference sources
        ckt.r(rail, '0', s['source_ohm'])
        ckt.l(rail, rail + '_byp', s['board_esl_h'], s['board_esr_ohm'])
        ckt.c(rail + '_byp', '0', s['board_bypass_f'])
    analog = [p for p in ring['pads'] if p.get('domain') == 'ana']
    on_bus = sorted({p['position'] for p in analog if not p['position'].startswith('top_7')}, key=bus_position)
    bonded_vdd = [p['position'] for p in analog if p['name'] == 'AVDD']
    bonded_vss = [p['position'] for p in analog if p['name'] == 'AVSS']
    if not shared_bus:                            # per-branch model: each branch keeps only its own pair
        bonded_vdd = [b['vdd_pad'] for b in br.values()]
        bonded_vss = [b['vss_pad'] for b in br.values()]
    for p in bonded_vdd:
        ckt.l('bvdd', 'vdd_' + p, s['pin_h'], s['pin_ohm'])
    for p in bonded_vss:
        ckt.l('0', 'vss_' + p, s['pin_h'], s['pin_ohm'])
    for p in on_bus:
        ckt.c('vdd_' + p, '0', BUS_NODE_F / 2)
        ckt.c('vss_' + p, '0', BUS_NODE_F / 2)
    if shared_bus:
        r_um = {rail: rsh('Mx', bus_temp_c, bus_temp_c > 100) / BUS_WIDTH_UM[rail] for rail in ('vdd', 'vss')}
        for a, b in zip(on_bus, on_bus[1:]):
            d = bus_position(b) - bus_position(a)
            for rail in ('vdd', 'vss'):
                ckt.l(rail + '_' + a, rail + '_' + b, BUS_H_PER_UM * d, r_um[rail] * d)
    route_r = rsh('M8', bus_temp_c, bus_temp_c > 100)
    for name, b in br.items():
        d = (drawn or {}).get(name)
        for i, (rail, pad) in enumerate((('vdd', b['vdd_pad']), ('vss', b['vss_pad']))):
            ln = b['route_um'][i]
            r_route = d['pad_to_bulk_ohm'] / 2 if d else route_r * ln / width_um
            ckt.l(rail + '_' + pad, 'bulk%s_%s' % (rail, name), SUPPLY_ROUTE_H_PER_UM * ln, r_route)
            ckt.c('bulk%s_%s' % (rail, name), '0', .2e-12)
            fd = b['feed_um'][i]
            r_feed = d['bulk_to_pin_ohm'] / 2 if d else route_r * fd / width_um
            ckt.l('bulk%s_%s' % (rail, name), 'c%s_%s' % (rail, name), SUPPLY_ROUTE_H_PER_UM * fd + 1e-13,
                  r_feed + core_feed_ohm[name] / 2)
        ckt.c('bulkvdd_' + name, 'besr_' + name, d['bulk_f'] if d else b['bulk_f'])
        ckt.r('besr_' + name, 'bulkvss_' + name, 2 * (d['esr_ohm_per_rail'] if d else BULK_ESR_OHM_PER_RAIL))
        ckt.c('cvdd_' + name, 'cvss_' + name, blocks[name])
        ckt.load('cvdd_' + name, 'cvss_' + name, name)
    # Reference pads: bond to the stiff source, pad capacitance to the bus, route, resistor, trunk.
    refs = reference_routes(ring)
    lengths = ring['supply_plan']['reference_route_length_um']
    tags = {'VREFP': 'p', 'VREFN': 'n'}
    seen = dict(VREFP=0, VREFN=0)
    for p in sorted((p for p in analog if p['name'] in tags), key=lambda p: bus_position(p['position'])):
        rail, pos = p['name'], p['position']
        route = '%s_%s' % (rail, 'ab'[seen[rail]])
        seen[rail] += 1
        pad, ln = 'ref_' + pos, lengths[route]
        ckt.l('bvr' + tags[rail], pad, s['pin_h'], s['pin_ohm'])
        if pad_coupling == 'asymmetric':
            ckt.c(pad, ('vdd_' if rail == 'VREFP' else 'vss_') + pos, pad_coupling_f)
        else:
            ckt.c(pad, 'vdd_' + pos, pad_coupling_f / 2)
            ckt.c(pad, 'vss_' + pos, pad_coupling_f / 2)
        ckt.c(pad, '0', ln * (REF_ROUTE_WIDTH_UM * M8_CAP['area_pf_um2'] + 2 * M8_CAP['edge_pf_um']) * 1e-12)
        ckt.l(pad, 'join_' + tags[rail], REF_ROUTE_H_PER_UM * ln, route_r * ln / REF_ROUTE_WIDTH_UM)
    for t in 'pn':
        ckt.r('join_' + t, 'trunk_' + t, s['series_ohm'])
    ckt.c('trunk_p', 'trunk_n', s['span_cap_f'])
    if trunk_coupling_f:                          # secondary ESD diodes on the trunk side, worst case
        ckt.c('trunk_p', 'cvdd_pair', trunk_coupling_f)
        ckt.c('trunk_n', 'cvss_pair', trunk_coupling_f)
    return ckt, dict(refs=refs)


def droop(ckt, t, v, name):
    return float(-(ckt.voltage(v, 'cvdd_' + name) - ckt.voltage(v, 'cvss_' + name)).min())


def at(t, y, times):
    return [float(np.interp(x, t, y)) for x in times]


def ring_checks(updates, decisions, charges, pulse=.5e-9, ring=None):
    """Own-branch droop and cross-branch coupling with and without the shared TACVDD/TACVSS bus.

    charges: branch -> (first and closing event, repeated event), already scaled for the corner.
    Every branch fires on the same update instants, the worst alignment. Feeds: 'limit' fills each
    branch to the 6 ohm loop limit with in-core strap; 'strapped' has 1 ohm of in-core strap."""
    ring = ring or load_ring()
    table = feed_table(ring)['rows']

    def events(names):
        return {n: [(u, q, pulse) for u, q in zip(updates, [charges[n][0]] + [charges[n][1]] * 7 + [charges[n][0]])]
                for n in names}

    def span_error(ckt, t, v):
        span = ckt.voltage(v, 'trunk_p') - ckt.voltage(v, 'trunk_n')
        # decision j after update j carries |trial - 128| <= 128 - 2^(6 - j)
        return max(abs(d) * (128 - 2 ** (6 - j)) / .9 for j, d in enumerate(at(t, span, decisions)))

    def block(ckt, v, name):
        return ckt.voltage(v, 'cvdd_' + name) - ckt.voltage(v, 'cvss_' + name)

    out = {}
    for config, shared, temp in (('per_branch', False, 25.), ('shared_bus_25c', True, 25.),
                                 ('shared_bus_125c_rcworst', True, 125.)):
        for feed in ('limit', 'strapped'):
            key = 'm8_125c_rcworst' if temp > 100 else 'm8_25c'
            core = {n: (FEED_LIMIT_OHM - table[n]['bulk_to_pin_ohm'][key]) if feed == 'limit' else 1. for n in charges}
            case = dict(core_feed_ohm=core)
            ckt, _ = chip(shared_bus=shared, bus_temp_c=temp, core_feed_ohm=core, ring=ring)
            t, v = ckt.run(events(charges))
            case['droop_all_firing_v'] = {n: droop(ckt, t, v, n) for n in charges}
            if shared:
                case['reference_error_lsb_asymmetric_pads_all_firing'] = span_error(ckt, t, v)
                for src in charges:
                    t, v = ckt.run(events([src]))
                    case['from_' + src] = {n: dict(peak_v=float(np.abs(block(ckt, v, n)).max()),
                                                   at_decisions_v=float(max(abs(x) for x in at(t, block(ckt, v, n), decisions))))
                                           for n in charges if n != src}
                    case['from_' + src]['reference_error_lsb_asymmetric_pads'] = span_error(ckt, t, v)
                sym, _ = chip(shared_bus=True, bus_temp_c=temp, core_feed_ohm=core, pad_coupling='symmetric', ring=ring)
                t, v = sym.run(events(charges))
                case['reference_error_lsb_symmetric_pads_all_firing'] = span_error(sym, t, v)
                sec, _ = chip(shared_bus=True, bus_temp_c=temp, core_feed_ohm=core, pad_coupling_f=0.,
                              trunk_coupling_f=.1e-12, ring=ring)
                t, v = sec.run(events(charges))
                case['reference_error_lsb_per_0p1pf_trunk_diode'] = span_error(sec, t, v)
            out['%s/%s' % (config, feed)] = case
    return out
