"""Stage 6 of issue #12: the all-extracted ADC with the routed top-level wiring and the Stage 1 system model.

Blocks are the frozen block extractions at the paired interconnect corner (prepare_all_extracted), with the
Bootstrap core re-extracted at that corner (TT: typical, SS: CWORST_T, FF: CBEST_T). The three not-drawn
model loads CL_COMP_P, CL_COMP_N and CL_CMP_CLK are removed. `--wiring` selects the core-level wiring:

- `lumped` (run family s6l): system-model shakedown. Each routed net's added capacitance from
  Layout/results/toplevel_route_full.json sits on its SAR-side pin; the drawn reference network (series
  resistance, CREF, CREF well junction) and the drawn decoupling sit behind the extracted feed resistances.
  No route resistance or route coupling.
- an evidence ID (run family s6e): a top-level-only extraction of sar8_adc_core/layout_route_full with the
  five block masters kept as xcells (wiring_package).

The testbench replaces the 50 ohm / 4 pF reference fixture and the ideal supply with the Stage 6 system model
of Layout/specs/constraints.json stage6_supply_model: stiff sources with 1 ohm output and the board bypass,
two bonds and pads per reference rail with the pad-to-core routes, and per supply branch (analog: comparator
and Bootstraps; pair: XREF/CDAC; SAR macro) one bond and pad per rail, the planned pad bulk and the 9 x 9 ring
feed at 125 C rcworst. The shared TACVDD/TACVSS bus is not modelled (stage6_supply_model shared_bus_check: the
per-branch model holds within 1.3 mV). VIN, SAMPLE and the D outputs keep the short-test interface.

`fft` turns a prepared Stage 6 deck into the TT transient-noise FFT (or its eight-frame pilot).

  python -m Layout.tools.simulation.prepare_stage6 adc ssc verify --wiring lumped --revision a
  python -m Layout.tools.simulation.prepare_stage6 fft sar8-s6l-tt-verify-a --pilot
"""
import argparse
import hashlib
import json
import re

from Layout.project import ROOT
from Layout.tools.simulation import bootstrap_pex
from Layout.tools.simulation import prepare_all_extracted as allx
from tools.saradc import single_edge_lpe as lpe

MODEL = json.loads((ROOT / 'Layout/specs/constraints.json').read_text(encoding='utf-8'))['stage6_supply_model']
ROUTED = json.loads((ROOT / 'Layout/results/toplevel_route_full.json').read_text(encoding='utf-8'))
CONDITIONS = json.loads((ROOT / 'specs/corners.json').read_text(encoding='utf-8'))
# Supply branches: wrapper port suffix, toplevel_route_full.json key, blocks served.
BRANCHES = (('A', 'analog', ('XCOMP', 'XBOOTN', 'XBOOTP')), ('P', 'pair', ('XCDAC',)), ('D', 'sar', ('XSAR',)))
BOND_HOT = '125C_rcworst'
# sar8-s6e-ssc-verify-a (wiring extraction with its supply meshes) peaked at 4.31 GB in the initial-condition solve and
# stopped at the 4 GiB reservation; 8 GiB keeps 1.9x headroom.
STAGE6_RSS_MIB = 8192
# Full Stage 6 on the filled core: the refilled pair (fill session, Stage 5) with its corner extractions and weights.
ROUTED_PAIR = dict(tt=('se-xref-peripheral-routed', 'xref-routedfill-tt-gain-a'),
                   # The weights of xref-routedfill-ssc-gain-cwb, rerun analysis-only after its own analysis was rejected.
                   ssc=('se-xref-peripheral-routed-cworst-t', 'xref-routedfill-ssc-gain-cwb-ana2'),
                   ffh=('se-xref-peripheral-routed-cbest-t', 'xref-routedfill-ffh-gain-cb'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rref_ohm(temperature_c):
    """PDK-model value of one 52-segment rupolym bank at TT, linear between the recorded temperatures."""
    table = sorted((float(k[:-1]), v) for k, v in ROUTED['reference']['rref']['per_rail']['VREFP']['model_ohm_tt'].items())
    for (t0, r0), (t1, r1) in zip(table, table[1:]):
        if temperature_c <= t1 or (t1, r1) == table[-1]:
            return r0 + (r1 - r0) * (temperature_c - t0) / (t1 - t0)


def star(a_b, b_c, a_c):
    """Star resistances (a, b, c) from the three pairwise extracted resistances."""
    return (a_b + a_c - b_c) / 2, (a_b + b_c - a_c) / 2, (b_c + a_c - a_b) / 2


# Drawn pad bulk of the chip sar8_adc_chip/layout_full_boot_r2 (Layout/results/chip_objects.json
# geometry.decap_<branch>.capacitance_pF, branch layout/chip-objects): the PCLAMPC_H_G clamps take part of the
# analog and SAR regions. The final Stage 6 uses these; the planned values stay in constraints.json.
DRAWN_PAD_BULK_F = dict(analog=85.1e-12, pair=112.1e-12, sar=104.5e-12)
PAD_BULK_SOURCE = dict(planned='Layout/specs/constraints.json stage6_supply_model.pad_bulk_decoupling.planned_on_9x9_ring_F',
                       drawn='Layout/results/chip_objects.json geometry.decap_{analog,pair,sar}.capacitance_pF '
                             '(chip sar8_adc_chip/layout_full_boot_r2, branch layout/chip-objects)')


def system_model(corner, pad_bulk='planned'):
    """Testbench rewrite (single_edge_lpe testbench hook), saved signals, probe map and record.
    pad_bulk: 'planned' (constraints.json) or 'drawn' (DRAWN_PAD_BULK_F, the final Stage 6)."""
    ref, pkg, bulk = MODEL['reference_source'], MODEL['package_per_pin'], MODEL['pad_bulk_decoupling']
    bulk_F = DRAWN_PAD_BULK_F if pad_bulk == 'drawn' else bulk['planned_on_9x9_ring_F']
    rail = pkg['reference_rail']
    route = rail['pad_to_core_route']
    lines = ['// Stage 6 system model: Layout/specs/constraints.json stage6_supply_model (prepare_stage6.py)']
    signals, probes = [], {}

    def ammeter(name, a, b):
        lines.append('%s (%s %s) vsource dc=0 type=dc' % (name, a, b))
        signals.append(name.lower() + ':p')
        probes[name.lower() + ':p'] = name + ':p'

    def board(tag, src, node):
        lines.extend(['RSRC_%s (%s %s) resistor r=%g' % (tag, src, node, ref['output_ohm']),
                      'RBYP_%s (%s %s_BYP1) resistor r=%g' % (tag, node, tag, ref['board_bypass_esr_ohm']),
                      'LBYP_%s (%s_BYP1 %s_BYP2) inductor l=%g' % (tag, tag, tag, ref['board_bypass_esl_H']),
                      'CBYP_%s (%s_BYP2 0) capacitor c=%g' % (tag, tag, ref['board_bypass_F'])])

    # Reference rails: two bonds and pads per rail, each pad with its own pad-to-core route (the two routes of
    # one rail in parallel make the recorded route values), joined at the core pin.
    pads = rail['pad_F'] / 2
    for rail_name, src in (('REFP', 'VREFP_SRC'), ('REFN', 'VREFN_SRC')):
        board(rail_name, src, rail_name + '_BRD')
        for k in (1, 2):
            ammeter('VA_%s%d' % (rail_name, k), rail_name + '_BRD', '%s_A%d' % (rail_name, k))
            lines.extend(['LBND_%s%d (%s_A%d %s_B%d) inductor l=%g' % (rail_name, k, rail_name, k, rail_name, k, rail['series_H']),
                          'RBND_%s%d (%s_B%d %s_PAD%d) resistor r=%g' % (rail_name, k, rail_name, k, rail_name, k, rail['series_ohm']),
                          'CPAD_%s%d (%s_PAD%d 0) capacitor c=%g' % (rail_name, k, rail_name, k, pads + route['F'] / 2),
                          'LRT_%s%d (%s_PAD%d %s_R%d) inductor l=%g' % (rail_name, k, rail_name, k, rail_name, k, 2 * route['H']),
                          'RRT_%s%d (%s_R%d %s_C) resistor r=%g' % (rail_name, k, rail_name, k, rail_name, 2 * route['ohm'])])
        ammeter('VA_%sC' % rail_name, rail_name + '_C', 'V' + rail_name)
    # Supply branches: one AVDD and one AVSS bond and pad each, the planned pad bulk, the ring feed (loop values
    # split evenly between the rails) and the core boundary pins VDD<b>/VSS<b>.
    feed = bulk['ring_feed_at_10um_M8_ohm']
    for suffix, key, _ in BRANCHES:
        vdd, vss = 'VDD' + suffix, 'VSS' + suffix
        pad_to_pin, bulk_to_pin = feed['pad_to_pin_' + BOND_HOT][key], feed['bulk_to_pin_' + BOND_HOT][key]
        board(vdd, 'VDD!', vdd + '_BRD')
        ammeter('VA_' + vdd, vdd + '_BRD', vdd + '_A')
        lines.extend(['LBND_%s (%s_A %s_B) inductor l=%g' % (vdd, vdd, vdd, pkg['series_H']),
                      'RBND_%s (%s_B %s_PAD) resistor r=%g' % (vdd, vdd, vdd, pkg['series_ohm']),
                      'CPAD_%s (%s_PAD 0) capacitor c=%g' % (vdd, vdd, pkg['pad_F']),
                      'RRG1_%s (%s_PAD %s_BULK) resistor r=%g' % (vdd, vdd, vdd, (pad_to_pin - bulk_to_pin) / 2),
                      'RRG2_%s (%s_BULK %s_CORE) resistor r=%g' % (vdd, vdd, vdd, bulk_to_pin / 2)])
        ammeter('VA_%s_C' % vdd, vdd + '_CORE', vdd)
        ammeter('VA_' + vss, vss + '_A', '0')
        lines.extend(['LBND_%s (%s_B %s_A) inductor l=%g' % (vss, vss, vss, pkg['series_H']),
                      'RBND_%s (%s_PAD %s_B) resistor r=%g' % (vss, vss, vss, pkg['series_ohm']),
                      'CPAD_%s (%s_PAD 0) capacitor c=%g' % (vss, vss, pkg['pad_F']),
                      'RRG1_%s (%s_BULK %s_PAD) resistor r=%g' % (vss, vss, vss, (pad_to_pin - bulk_to_pin) / 2),
                      'RRG2_%s (%s %s_BULK) resistor r=%g' % (vss, vss, vss, bulk_to_pin / 2),
                      'RBLK1_%s (%s_BULK %s_BLKC) resistor r=%g' % (suffix, vdd, suffix, bulk['esr_ohm_per_rail']),
                      'CBLK_%s (%s_BLKC %s_BLKS) capacitor c=%g' % (suffix, suffix, suffix, bulk_F[key]),
                      'RBLK2_%s (%s_BLKS %s_BULK) resistor r=%g' % (suffix, suffix, vss, bulk['esr_ohm_per_rail'])])
    ports = ' '.join('VDD%s VSS%s' % (s, s) for s, _, _ in BRANCHES)

    def hook(blobs, ctx):
        tb = blobs['tb.scs'].decode()
        old = 'XDUT (D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD! VINN VINP VREFN VREFP 0)'
        if tb.count(old) != 1:
            raise ValueError('Unexpected DUT instance in tb.scs')
        tb = tb.replace(old, old[:-1] + ' ' + ports + ')')
        for pattern in (r'RREFN \(VREFN_SRC VREFN\) resistor r=50', r'RREFP \(VREFP_SRC VREFP\) resistor r=50',
                        r'CREFN \(VREFN 0\) capacitor c=4p', r'CREFP \(VREFP 0\) capacitor c=4p'):
            tb, n = re.subn(r'(?m)^' + pattern + r'[ \t]*\r?\n', '', tb)
            if n != 1:
                raise ValueError('Reference fixture line not found: ' + pattern)
        blobs['tb.scs'] = (tb.rstrip('\n') + '\n' + '\n'.join(lines) + '\n').encode()
        ctx['stage6_system_model'] = dict(
            source=dict(MODEL['reference_source'], supply=MODEL['supply_source']),
            reference_rail=dict(bonds=2, series_H=rail['series_H'], series_ohm=rail['series_ohm'], pads_F=rail['pad_F'],
                                route_ohm=route['ohm'], route_H=route['H'], route_F=route['F']),
            supply=dict(bond_H=pkg['series_H'], bond_ohm=pkg['series_ohm'], pad_F=pkg['pad_F'],
                        pad_bulk_F=bulk_F, pad_bulk_basis=pad_bulk, pad_bulk_source=PAD_BULK_SOURCE[pad_bulk],
                        pad_bulk_esr_ohm_per_rail=bulk['esr_ohm_per_rail'],
                        ring_feed_loop_ohm={k: feed[k] for k in feed if k.endswith(BOND_HOT)}),
            ideal=['VIN source and 50 ohm per side at the core pins', 'SAMPLE source at the core pin',
                   'D outputs with 5 fF each at the core pins', 'shared TACVDD/TACVSS bus coupling (not modelled)',
                   'board-side ground'],
            ammeters='VA_<rail><k>: bond k current toward the die; VA_<rail>C / VA_VDD<b>_C: current into the core pin; '
                     'VA_VSS<b>: return current from the core to the board')
    return hook, signals, probes


def core_network(corner):
    """Wrapper-level lumped core wiring (wiring 'lumped'): drawn reference network, feeds, decoupling, route loads."""
    cond = CONDITIONS[corner]
    r = ROUTED['reference']
    lines = ['    // Lumped core wiring (prepare_stage6.py, wiring lumped): Layout/results/toplevel_route_full.json']
    record = {}
    for rail, tag in (('VREFP', 'P'), ('VREFN', 'N')):
        rt = r['routing'][rail]
        a, b, c = star(rt['rail_end_to_rref_ohm'], rt['rail_end_to_cref_ohm'], rt['rref_to_cref_ohm'])
        # a: RREF trunk terminal to the CREF tap; b: tap to the rail end (pair port); c: tap to CREF.
        lines.extend(['    RPAD_%s (%s %s_RR) resistor r=%g' % (tag, rail, rail, rt['pad_pin_to_rref_ohm']),
                      '    RREF%s (%s_RR %s_RT) resistor r=%g' % (tag, rail, rail, rref_ohm(cond['temperature_c'])),
                      '    RTR1_%s (%s_RT %s_TAP) resistor r=%g' % (tag, rail, rail, a),
                      '    RTR2_%s (%s_TAP %s_TRUNK) resistor r=%g' % (tag, rail, rail, b),
                      '    RCR_%s (%s_TAP CREF_%s) resistor r=%g' % (tag, rail, tag, c)])
        record[rail] = dict(pad_side_ohm=rt['pad_pin_to_rref_ohm'], rref_ohm=rref_ohm(cond['temperature_c']),
                            star_ohm=dict(rref_to_tap=a, tap_to_rail_end=b, tap_to_cref=c))
    j = r['cref_well_junction']
    lines.extend(['    CREF (CREF_P CREF_N) capacitor c=%g' % r['cref']['estimated_F'],
                  '    DCREF (VSSC VREFN_TRUNK) nwdio area=%g pj=%g' % (j['area_um2'] * 1e-12, j['perimeter_um'] * 1e-6)])
    feeds, dec = ROUTED['feeds'], ROUTED['decoupling']
    for suffix, key, _ in BRANCHES:
        vdd = feeds[key]['VDD']
        to_dec, to_blk = vdd['to_decap_ohm'], vdd['to_blocks_ohm']
        vss = (feeds[key]['VSS'] or {}).get('to_decap_ohm', to_dec)
        if to_blk >= to_dec:
            lines.extend(['    RFD_%s (VDD%s VDD%s_DEC) resistor r=%g' % (suffix, suffix, suffix, to_dec),
                          '    RFB_%s (VDD%s_DEC VDD%s_BLK) resistor r=%g' % (suffix, suffix, suffix, to_blk - to_dec)])
        else:
            lines.extend(['    RFB_%s (VDD%s VDD%s_BLK) resistor r=%g' % (suffix, suffix, suffix, to_blk),
                          '    RFD_%s (VDD%s_BLK VDD%s_DEC) resistor r=%g' % (suffix, suffix, suffix, to_dec - to_blk)])
        lines.extend(['    CDEC_%s (VDD%s_DEC VSSC) capacitor c=%g' % (suffix, suffix, dec[key]['estimated_F']),
                      '    RFS_%s (VSSC VSS%s) resistor r=%g' % (suffix, suffix, vss)])
        record[key] = dict(vdd_to_decap_ohm=to_dec, vdd_to_blocks_ohm=to_blk, vss_to_decap_ohm=vss,
                           vss_estimated=feeds[key]['VSS'] is None, decap_F=dec[key]['estimated_F'])
    lines.append('    CDEC_CMP (VDDA_BLK VSSC) capacitor c=%g' % dec['comparator_local']['estimated_F'])
    loads = {}
    for net, row in sorted(ROUTED['route_budget_nets'].items()):
        if net.startswith('TOP'):
            continue
        lines.append('    CRT_%s (%s VSSC) capacitor c=%gf' % (net, net, row['added_fF']))
        loads[net] = row['added_fF'] * 1e-15
    record.update(route_added_F=loads, top='TOP wiring ideal: the recorded added TOP capacitance is negative '
                  '(density-dependent thickness), so no TOP element is added in the lumped model')
    return lines, record


def rewrite_top(text, core_lines):
    """Branch supplies and trunk references on the block instances, model loads removed, core wiring added."""
    text, n = re.subn(r'(?m)^[ \t]*CL_(?:COMP_N|COMP_P|CMP_CLK) \([^)]*\)[^\n]*\n', '', text)
    if n != 3:
        raise ValueError('Expected the three CL_* model loads')
    m = re.search(r'(?m)^subckt sar_adc8_join_r4 ([^\n]+)$', text)
    if m[1].split() != 'D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD! VINN VINP VREFN VREFP 0'.split():
        raise ValueError('Unexpected wrapper ports')
    text = text[:m.end(1)] + ' ' + ' '.join('VDD%s VSS%s' % (s, s) for s, _, _ in BRANCHES) + text[m.end(1):]
    for suffix, _, blocks in BRANCHES:
        for inst in blocks:
            m = re.search(r'(?m)^([ \t]*' + inst + r'[ \t]+\()([^)]+)(\)[ \t]+(\S+)[ \t]*)$', text)
            if not m:
                raise ValueError('Missing block instance ' + inst)
            pins = m[2].split()
            new = {'VDD!': 'VDD%s_BLK' % suffix, '0': 'VSSC', 'VREFP': 'VREFP_TRUNK', 'VREFN': 'VREFN_TRUNK'}
            pins = [new.get(p, p) for p in pins]
            if inst.startswith('XBOOT'):
                if len(pins) != 3:
                    raise ValueError('Unexpected Bootstrap binding')
                pins += ['VDD%s_BLK' % suffix, 'VSSC']
            if 'VDD!' in pins or '0' in pins or ('VDD%s_BLK' % suffix) not in pins:
                raise ValueError('Supply binding failed on ' + inst)
            text = text[:m.start(2)] + ' '.join(pins) + text[m.end(2):]
    end = re.search(r'(?m)^ends sar_adc8_join_r4\b', text)
    return text[:end.start()] + '\n'.join(core_lines) + '\n' + text[end.start():]


# Top-level wiring extraction (Layout/tools/physical/toplevel_wiring_xcell.py). The xcells are netlisted with
# ideal internal nets; every top-level net's RC network ends on one node per xcell it reaches (the xcell pin), and
# the substrate node of all xcells is one node of the VSS network. Those nodes become ports of stage6_wiring.
WIRE = 'wire_'
# Block instance of the wrapper: (frozen block, net -> wrapper net of its pin). None keeps the net's own name.
BLOCK_PINS = {
    'XSAR': ['CMP_CLK', 'COMP_P', 'COMP_N', 'SEQ_SAMPLE', 'PRESET', 'SAMPLE', 'VDD_D']
            + ['CODE%d' % i for i in range(8)] + ['D%d' % i for i in range(8)],
    'XCOMP': ['CMP_CLK', 'COMP_P', 'COMP_N', 'TOPP', 'TOPN', 'VDD_A'],
    'XCDAC': ['TOPP', 'TOPN', 'PRESET', 'VDD_P', 'VREFP_TRUNK', 'VREFN_TRUNK'] + ['CODE%d' % i for i in range(8)],
    'XBOOTN': ['SEQ_SAMPLE', 'TOPN', 'VINN', 'VDD_A'],
    'XBOOTP': ['SEQ_SAMPLE', 'TOPP', 'VINP', 'VDD_A'],
}
# Wrapper net of each block-side pin node. The analyzers probe the SAR-side handshake, CODE, PRESET and SEQ_SAMPLE
# nets and the CDAC-side TOP nets by their schematic names, so those keep them.
PIN_NET = dict(
    XSAR=dict(VDD_D='VDDD_BLK', SAMPLE='SAMPLE_SAR', **{'D%d' % i: 'D%d_SAR' % i for i in range(8)}),
    XCOMP=dict(CMP_CLK='CMP_CLK_CMP', COMP_P='COMP_P_CMP', COMP_N='COMP_N_CMP', TOPP='TOPP_CMP', TOPN='TOPN_CMP',
               VDD_A='VDDA_BLK'),
    XCDAC=dict(PRESET='PRESET_PAIR', VDD_P='VDDP_BLK', **{'CODE%d' % i: 'CODE%d_PAIR' % i for i in range(8)}),
    XBOOTN=dict(SEQ_SAMPLE='SEQ_SAMPLE_BN', TOPN='TOPN_BS', VINN='VINN_BS', VDD_A='VDDA_BN'),
    XBOOTP=dict(SEQ_SAMPLE='SEQ_SAMPLE_BP', TOPP='TOPP_BS', VINP='VINP_BS', VDD_A='VDDA_BP'))
# Extraction ports (label nodes) and the wrapper nets they join; internal label nodes stay as probe points.
PORT_NET = dict(VDD_A='VDDA', VDD_P='VDDP', VDD_D='VDDD', VSS_A='VSSA', VREFP='VREFP', VREFN='VREFN', SAMPLE='SAMPLE',
                VINN='VINN', VINP='VINP', **{'D%d' % i: 'D%d' % i for i in range(8)})


def statements(text):
    """Spectre statements with backslash continuations joined, in order."""
    parts = []
    for line in text.splitlines():
        line = line.rstrip()
        if line.endswith('\\'):
            parts.append(line[:-1])
            continue
        parts.append(line)
        yield ' '.join(parts).strip()
        parts = []


def wrap(statement, width=150):
    out, line = [], ''
    for token in statement.split(' '):
        if line and len(line) + len(token) + 1 > width:
            out.append(line + ' \\')
            line = ' ' + token
        else:
            line = (line + ' ' + token) if line else token
    return '\n'.join(out + [line])


def wiring_package(identity):
    """stage6_wiring from the xcell extraction: xcell devices and the xcells' own well diodes removed, the xcell
    attachment nodes renamed and exported as ports. Returns files, the pin map and a record."""
    base = ROOT / 'work/layout/toplevel-wiring' / identity
    manifest = json.loads((base / 'manifest.json').read_bytes())
    if not manifest.get('done') or manifest.get('error') or manifest.get('case') != 'toplevel-wiring-xcell':
        raise ValueError('Wiring extraction incomplete: ' + identity)
    names = ['extracted.scs'] + sorted(manifest['checks']['pex']['companion_sha256'])
    raw = {}
    for n in names:
        data = (base / 'pex' / n).read_bytes()
        want = manifest['checks']['pex']['sha256'] if n == 'extracted.scs' else manifest['checks']['pex']['companion_sha256'][n]
        if sha(data) != want:
            raise ValueError('Wiring extraction file differs from its manifest: ' + n)
        raw[n] = data.decode('ascii')
    inst = re.compile(r'^(\S+)\s*\(\s*(.*?)\s*\)\s+(\S+)(.*)$')
    unescape = lambda s: s.replace('\\', '')
    # The routed core, or the filled wrapper whose flattened core instance puts a prefix on every xcell path.
    top = manifest.get('top', 'sar8_adc_core')
    xcells = {}
    pxi = 'extracted.scs.%s.pxi' % top
    found = []                        # (net, unescaped node, escaped node) of every PM_ node inside an instance
    for st in statements(raw[pxi]):
        m = inst.match(st)
        if m and m[3].startswith('PM_'):
            net = unescape(m[3]).split('%', 1)[1]
            found += [(net, unescape(node), node) for node in m[2].split() if re.match(r'^X\d+/', unescape(node))]
    # Attachment nodes lie below their xcell, so the xcell path is the leading instance(s): one level in the routed
    # core, two when every node sits under the wrapper's single core instance.
    depth = 2 if len({u.split('/', 1)[0] for _, u, _ in found}) == 1 else 1
    attach = {}                       # (net, xcell instance path) -> escaped attachment node
    for net, u, node in found:
        x = re.match(r'^((?:X\d+/){%d})' % depth, u)
        if x:
            path = x[1][:-1]
            if (net, path) in attach and attach[net, path] != node:
                raise ValueError('Two attachment nodes for %s on %s' % (net, path))
            attach[net, path] = node
    reach = {}
    for (net, x) in attach:
        reach.setdefault(x, set()).add(net)
    for x, nets in reach.items():
        if {'D0', 'CMP_CLK', 'SEQ_SAMPLE'} <= nets:
            xcells[x] = 'XSAR'
        elif {'VREFP_TRUNK', 'CODE0'} <= nets:
            xcells[x] = 'XCDAC'
        elif {'CMP_CLK', 'TOPP', 'TOPN'} <= nets and 'D0' not in nets:
            xcells[x] = 'XCOMP'
        elif 'VINN' in nets:
            xcells[x] = 'XBOOTN'
        elif 'VINP' in nets:
            xcells[x] = 'XBOOTP'
    if sorted(xcells.values()) != sorted(BLOCK_PINS):
        raise ValueError('Cannot identify the five xcell instances: %s' % xcells)
    by_block = {b: x for x, b in xcells.items()}
    substrate = [n for (net, x), n in attach.items() if net == 'VSS_A']
    if len(substrate) != 1:
        raise ValueError('Expected one substrate attachment of VSS_A')
    # Attachment ports are named A_<wrapper net> inside stage6_wiring, apart from its own label nodes.
    ports = {substrate[0]: 'A_VSSC'}     # escaped node -> wiring port name
    pins = {}
    for block, nets in BLOCK_PINS.items():
        for net in nets:
            node = attach.get((net, by_block[block]))
            if node is None:
                raise ValueError('%s does not reach %s in the extraction' % (net, block))
            port = PIN_NET[block].get(net, net)
            ports[node] = 'A_' + port
            pins[block, net] = port
    extra = [(n, x) for (n, x) in attach if (n, xcells[x]) not in {(n2, b) for b, ns in BLOCK_PINS.items() for n2 in ns}
             and n != 'VSS_A']
    if extra:
        raise ValueError('Extraction attachments without a frozen block pin: %s' % extra)
    token = re.compile(r'(?<=[\s(])(' + '|'.join(re.escape(n) for n in sorted(ports, key=len, reverse=True)) + r')(?=[\s)])')
    paths = '|'.join(r'\\?/'.join(x.split('/')) for x in xcells)   # escaped or plain separators
    skip = re.compile(r'^[XxDd]?(%s)\\?/' % paths)
    removed = {}
    files = {}
    for n in names:
        out = []
        for st in statements(raw[n]):
            m = inst.match(st)
            if m and not m[3].startswith('PM_') and skip.match(m[1]):
                removed[m[3]] = removed.get(m[3], 0) + 1
                continue
            if n == 'extracted.scs':
                head = re.match(r'subckt %s\s*\((.*)\)$' % re.escape(top), st)
                if head:
                    formal = head[1].split()
                    st = 'subckt stage6_wiring ( %s %s )' % (' '.join(formal), ' '.join(sorted(set(ports.values()))))
                elif re.match(r'ends %s\b' % re.escape(top), st):
                    st = 'ends stage6_wiring'
            st = re.sub(r'^include "(extracted\.scs[^"]*)"', lambda mm: 'include "%s%s"' % (WIRE, mm[1]), st)
            if not st.startswith('//'):
                # Drop the LOCATION comments (//x= //y=) so re-wrapping cannot comment out a token.
                st = re.sub(r'\s+//\S*', '', st)
                st = token.sub(lambda mm: ports[mm[1]], ' ' + st + ' ').strip()
            out.append(wrap(st))
        files[WIRE + n] = ('\n'.join(out) + '\n').encode('ascii')
    if any(re.search(r'(?<![\w/\\])(%s)\\?/' % paths, files[WIRE + n].decode()) for n in names if n != 'extracted.scs.pex'):
        raise ValueError('An xcell node survived the cut')
    kept = {}
    for st in statements(files[WIRE + 'extracted.scs'].decode()) :
        m = inst.match(st)
        if m:
            kept[m[3]] = kept.get(m[3], 0) + 1
    record = dict(evidence=identity, top=top, interconnect_rc=manifest['interconnect_rc'], gds_sha256=manifest['gds']['sha256'],
                  xcells={b: x for x, b in xcells.items()}, removed_xcell_elements=removed, kept_top_level_devices=kept,
                  formal_ports=formal, attachment_ports=sorted(set(ports.values())),
                  vss=('One extracted VSS network (VSS_A): the P-substrate soft-connects the three branch VSS pieces, so '
                       'the three boundary VSS pins share one port node, and every block VSS port joins the xcells\' '
                       'common substrate node (VSSC)'))
    return dict(files=files, formal=formal, pins=pins, record=record)


def rewrite_top_extracted(text, wire):
    """Frozen blocks on the wiring extraction's pin nodes, model loads removed, stage6_wiring instantiated."""
    text, n = re.subn(r'(?m)^[ \t]*CL_(?:COMP_N|COMP_P|CMP_CLK) \([^)]*\)[^\n]*\n', '', text)
    if n != 3:
        raise ValueError('Expected the three CL_* model loads')
    m = re.search(r'(?m)^subckt sar_adc8_join_r4 ([^\n]+)$', text)
    if m[1].split() != 'D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD! VINN VINP VREFN VREFP 0'.split():
        raise ValueError('Unexpected wrapper ports')
    text = text[:m.end(1)] + ' ' + ' '.join('VDD%s VSS%s' % (s, s) for s, _, _ in BRANCHES) + text[m.end(1):]
    supply = dict(XSAR='VDD_D', XCOMP='VDD_A', XCDAC='VDD_P', XBOOTN='VDD_A', XBOOTP='VDD_A')
    for block, nets in BLOCK_PINS.items():
        m = re.search(r'(?m)^([ \t]*' + block + r'[ \t]+\()([^)]+)(\)[ \t]+(\S+)[ \t]*)$', text)
        if not m:
            raise ValueError('Missing block instance ' + block)
        pins = m[2].split()
        new = {'0': 'VSSC', 'VDD!': wire['pins'][block, supply[block]],
               'VREFP': wire['pins'].get((block, 'VREFP_TRUNK')), 'VREFN': wire['pins'].get((block, 'VREFN_TRUNK'))}
        new.update({net: wire['pins'][block, net] for net in nets if not net.startswith(('VDD_', 'VREF'))})
        if block.startswith('XBOOT'):
            if len(pins) != 3:
                raise ValueError('Unexpected Bootstrap binding')
            pins += ['VDD!', '0']
        pins = [new[p] if new.get(p) else p for p in pins]
        if 'VDD!' in pins or '0' in pins:
            raise ValueError('Supply binding failed on ' + block)
        text = text[:m.start(2)] + ' '.join(pins) + text[m.end(2):]
    formal = [PORT_NET.get(p, p + '_LBL') for p in wire['formal']]
    attached = [p[2:] for p in wire['record']['attachment_ports']]
    lines = ['    // Stage 6 extracted core wiring: %s (prepare_stage6.py)' % wire['record']['evidence'],
             '    XWIRE (%s %s) stage6_wiring' % (' '.join(formal), ' '.join(attached)),
             '    // The three boundary VSS pins share the extraction\'s single VSS port (P-substrate).',
             '    RTIE_VSSP (VSSP VSSA) resistor r=1m', '    RTIE_VSSD (VSSD VSSA) resistor r=1m']
    end = re.search(r'(?m)^ends sar_adc8_join_r4\b', text)
    return text[:end.start()] + '\n'.join(wrap(l) for l in lines) + '\n' + text[end.start():]


def bootstrap_wrapper(context):
    """Bootstrap wrapper with explicit supply ports (VDD, VSS) instead of the global VDD! and 0."""
    names = {'CLKS': 'CLKS', 'VIN': 'Vin', 'VOUT': 'VOUT', 'VDD': 'VDD', 'VSS': 'VSS'}
    ports = context['bootstrap_extracted_ports']
    if sorted(ports) != sorted(names):
        raise ValueError('Unexpected extracted Bootstrap ports')
    return ('simulator lang=spectre\ninclude "boot_extracted.scs"\nsubckt %s CLKS VOUT Vin VDD VSS\n'
            'Xcore (%s) %s\nends %s\n' % (bootstrap_pex.MASTER, ' '.join(names[p] for p in ports), bootstrap_pex.CORE,
                                          bootstrap_pex.MASTER)).encode()


def prepare_adc(corner, kind, revision, wiring='lumped', pair='frozen', boot=None, pad_bulk='planned'):
    """pair: 'frozen' (the dense pair of the early pass) or 'routed' (ROUTED_PAIR, the filled core);
    boot: a Bootstrap extraction at this corner in place of the frozen one (the Bootstrap with its fill)."""
    spec = allx.CORNERS[corner]
    if lpe.CELL_RC[corner] != spec['rc'].lower():
        raise ValueError('Cell LPE and extraction corners differ')
    boot = boot or spec['boot']
    if bootstrap_pex.interconnect(boot) != spec['rc']:
        raise ValueError('Bootstrap extraction interconnect corner differs: ' + boot)
    hook, signals, probes = system_model(corner, pad_bulk)
    pair_xref, pair_gain = ROUTED_PAIR[corner] if pair == 'routed' else (spec['xref'], spec['gain'])
    xref = allx.xref_package(pair_xref, pair_gain, spec['rc'],
                             stream=ROUTED_PAIR['tt'][0] if pair == 'routed' else allx.FROZEN_XREF)
    bind = xref['bind']
    if wiring == 'lumped':
        core_lines, core_record = core_network(corner)
        rewrite = lambda text: rewrite_top(text, core_lines)
        extra_files = {}
    else:
        wire = wiring_package(wiring)
        core_record = wire['record']
        # Route RC at the paired corner (final Stage 6), or typical (labelled, early pass).
        if core_record['interconnect_rc'] not in ('typical', spec['rc']):
            raise ValueError('Wiring extraction corner %s does not pair with %s' % (core_record['interconnect_rc'], corner))
        rewrite = lambda text: rewrite_top_extracted(text, wire)
        extra_files = wire['files']

    def bind_stage6(sources):
        bind(sources)
        sources['top/adc_top.scs'] = rewrite(sources['top/adc_top.scs'].decode()).encode()
        sources['bootstrap_pex.scs'] = bootstrap_wrapper(bootstrap_pex.package(boot)['context'])
        if extra_files:
            sources.update(extra_files)
            sources['dut.scs'] = sources['dut.scs'].replace(
                b'include "top/adc_top.scs"', ('include "%sextracted.scs"\ninclude "top/adc_top.scs"' % WIRE).encode())

    # The analyzers read the plate targets at the pair's reference ports (the trunks); the core pins are kept too.
    stage6_probes = dict(probes, vrefp='XDUT.VREFP_TRUNK', vrefn='XDUT.VREFN_TRUNK', vrefp_pin='VREFP', vrefn_pin='VREFN')
    stage6_probes.update({'xdut.vdd%s_blk' % s.lower(): 'XDUT.VDD%s_BLK' % s for s, _, _ in BRANCHES})
    if wiring == 'lumped':
        stage6_probes.update({'xdut.vdd%s_dec' % s.lower(): 'XDUT.VDD%s_DEC' % s for s, _, _ in BRANCHES})
    else:
        # Block-side ends of the handshake, CODE7 and TOP routes, for the route-delay and TOP checks.
        stage6_probes.update({n.lower(): n for n in ('XDUT.CMP_CLK_CMP', 'XDUT.COMP_P_CMP', 'XDUT.COMP_N_CMP',
                                                     'XDUT.CODE7_PAIR', 'XDUT.PRESET_PAIR', 'XDUT.TOPP_CMP',
                                                     'XDUT.TOPN_CMP', 'XDUT.TOPP_BS', 'XDUT.TOPN_BS')})
    stage6_probes['xdut.vssc'] = 'XDUT.VSSC'
    filled = core_record.get('top') == 'sar8_adc_core_filled'
    view = 'sar8_adc_core_filled/layout_fill2' if filled else 'sar8_adc_core/layout_route_full'
    xref.update(bind=bind_stage6, probes=dict(xref['probes'], **stage6_probes),
                signals=xref.get('signals', []) + signals + [k for k in stage6_probes if k not in probes
                                                             and k not in ('vrefp', 'vrefn')],
                context=dict(xref['context'], stage6=dict(wiring=wiring, core=core_record, filled=filled,
                                                          pair=dict(extraction=pair_xref, weights=pair_gain),
                                                          bootstrap=boot,
                                                          model_loads_removed=['CL_COMP_P', 'CL_COMP_N', 'CL_CMP_CLK'],
                                                          routed_view='SAR_ADC_T28_LAYOUT/' + view,
                                                          routed_record='Layout/results/toplevel_route_full.json')),
                scope=xref['scope'] + '; Stage 6 %s core wiring of %s and the stage6_supply_model system model'
                % (wiring, view.split('/')[1]))
    return lpe.prepare(corner, kind, revision=revision, macro=allx.sar_macro(spec['sar'], spec['rc']), bootstrap=boot,
                       xref=xref, comparator=allx.comparator_package(spec['comparator'], spec['rc']),
                       family='s6l' if wiring == 'lumped' else 's6f' if pair == 'routed' else 's6e',
                       settling_limit=.25, rss_mib=STAGE6_RSS_MIB, testbench=hook)


RAIL_BUDGETS = ('reference_charge_per_conversion_C', 'reference_event_charge_C', 'reference_pin_peak_current_A',
                'reference_span_droop_V', 'supply_charge_per_conversion_C', 'supply_event_charge_C',
                'supply_pin_peak_current_A', 'supply_droop_V')


def prepare_rails(source_run_id, run_id=None):
    """Analysis-only rail job (measure_stage6_rails.py) on a completed Stage 6 frame run, same host as the source."""
    run_id = run_id or source_run_id + '-rails'
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    source = json.loads((lpe.RUNS / source_run_id / 'recipe.json').read_bytes())
    ctx = source['test_conditions']
    if 'stage6' not in ctx or ctx.get('kind') == 'restart':
        raise ValueError('Needs a Stage 6 frame run')
    limits = json.loads((ROOT / 'Layout/specs/constraints.json').read_text(encoding='utf-8'))['electrical_budgets']
    blobs = {'measure_stage6_rails.py': (ROOT / 'Layout/tools/analysis/measure_stage6_rails.py').read_bytes(),
             'native_stream.py': (ROOT / 'tools/saradc/measure/native_stream.py').read_bytes(),
             'stage6_budget.json': (json.dumps({k: limits[k]['limit'] for k in RAIL_BUDGETS}, indent=2) + '\n').encode()}
    dest.mkdir(parents=True)
    for name, blob in blobs.items():
        (dest / name).write_bytes(blob)
    spec = dict(schema_version=2, kind='analysis_only', source_run_id=source_run_id, run_id=run_id,
                design_id=source['design_id'], analyzer='measure_stage6_rails.py',
                inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b)) for n, b in blobs.items()],
                resources=dict(source['resources'], analysis_rss_mib=1024, analysis_wall_seconds=10800),
                spectre_args=source['spectre_args'], summary_signals=source['summary_signals'],
                expected_stop_s=source['expected_stop_s'],
                qualification_scope='Analysis-only reference and supply rail charge, peak current and droop of %s against '
                                    'the Stage 1 budget' % source_run_id,
                test_conditions=dict(ctx, rails_source_run_id=source_run_id))
    path = dest / 'recipe.json'
    path.write_text(json.dumps(spec, indent=2) + '\n')
    return path


FFT_SIGNALS = ['D%d' % i for i in range(8)] + ['SAMPLE', 'VDD!', 'VINP_SRC', 'VINN_SRC', 'VVDD:p', 'VREFHIGH:p',
                                                'VREFLOW:p', 'VSAMPLE:p']
ANALYZER_FILES = ('single_edge_lpe.py', 'single_edge_audit.py', 'register_constraints.py', 'dff.json',
                  'single_edge_restart.py')


FFT_SEGMENT_WARMUP = 8      # 800 ns: covers the slowest system-model constant (100 nF board bypass behind 1 ohm)


def segment_bounds(segment, segments):
    """First FFT frame and frame count of segment k of a 1024-frame record split into near-equal parts."""
    start, stop = 1024 * segment // segments, 1024 * (segment + 1) // segments
    return start, stop - start


def prepare_fft(source_id, pilot=False, run_id=None, threads=4, segment=None, segments=16):
    """TT transient-noise FFT on a prepared Stage 6 deck: the deck's circuit, models and system model unchanged;
    the -1 dBFS sine of tb/top/fft at bin 461 of 1024, transient noise 10 kHz (pilot 2 MHz) to 2 GHz, seed 101,
    and the single-edge frame monitor. The pilot runs eight frames; the full run 8 warm-up plus 1024 frames.

    segment k of segments: FFT frames s .. s+n-1 of the 1024 (segment_bounds), after 8 warm-up frames that are the
    record's own frames s-8 .. s-1 (the full run's 8 warm-up frames for k = 0). The input sines start with the phase
    they have at that point of the full record (the clocks repeat every 100 ns, so only the sines move); noise seed
    101 + k. Overlapping warm-up and the previous segment's last frames check the stitching (fft_stitch.py).
    The segment count is set by the free Spectre licences (6 Multi_mode tokens per 4-thread run)."""
    source = ROOT / 'work/decks' / source_id
    recipe = json.loads((source / 'recipe.yaml').read_bytes())
    ctx0 = recipe['test_conditions']
    if ctx0['corner'] != 'tt' or ctx0['kind'] == 'restart' or 'stage6' not in ctx0:
        raise ValueError('The FFT uses a TT Stage 6 deck with frame stimuli')
    blobs = {}
    for row in recipe['inputs']:
        data = (ROOT / row['source']).read_bytes()
        if sha(data) != row['sha256']:
            raise ValueError('Source deck input changed: ' + row['name'])
        blobs[row['name']] = data
    for name in ANALYZER_FILES + ('context.json', 'recipe.yaml'):
        blobs.pop(name, None)
    frames, warmup, count = (8, 0, 8) if pilot else (1032, 8, 1024)
    seed, offset_s = 101, 0.
    if segment is not None:
        if pilot or not 0 <= segment < segments or not 2 <= segments <= 64:
            raise ValueError('Segment must index the 1024-frame record')
        first, length = segment_bounds(segment, segments)
        frames, warmup, count = FFT_SEGMENT_WARMUP + length, FFT_SEGMENT_WARMUP, length
        seed, offset_s = 101 + segment, first * 100e-9
    run_id = run_id or '%s-fft%s' % (source_id, 'p' if pilot else 's%02dof%02d' % (segment, segments)
                                     if segment is not None else '1024')
    stop = 59e-9 + frames * 100e-9
    low = 2e6 if pilot else 1e4
    # Stimulus: the sine sources of the FFT testbench replace the frame-code sources.
    fft_tb = (ROOT / 'tb/top/fft/tb.scs').read_text(encoding='utf-8')
    tb = blobs['tb.scs'].decode()
    if not re.search(r'(?m)^VSAMPLE \(SAMPLE 0\) vsource type=pulse .*\bwidth=44\.9n period=100n', tb):
        raise ValueError('Expected the 45 ns sampling source')
    phases = {}
    for src in ('VVINP', 'VVINN'):
        line = re.search(r'(?m)^%s \([^\n]*type=sine[^\n]*$' % src, fft_tb)[0]
        if offset_s:
            freq = float(re.search(r'\bfreq=(\S+)', line)[1])
            phase = float(re.search(r'\bsinephase=(\S+)', line)[1])
            shifted = (phase + 360. * freq * offset_s) % 360.
            line = re.sub(r'\bsinephase=\S+', 'sinephase=%.12g' % shifted, line)
            phases[src] = shifted
        tb, n = re.subn(r'(?m)^%s \([^\n]*$' % src, lambda m: line, tb)
        if n != 1:
            raise ValueError('Missing input source ' + src)
    blobs['tb.scs'] = tb.encode()
    test = blobs['test.scs'].decode()
    test = re.sub(r'(?m)^save [^\n]*\n?', '', test)
    old = re.search(r'(?m)^tran_short tran [^\n]+$', test)[0]
    new = ('tran_short tran stop=%.12g maxstep=10p errpreset=moderate lteratio=10 strobeperiod=10p strobeoutput=strobeonly '
           'noisefmin=%.12g noisefmax=2G noiseseed=%d noisescale=1 saveclock=1800 savefile="tran_noise.state"'
           % (stop, low, seed))
    test = test.replace(old, new)
    monitor = ('ahdl_include "sar8_se_fft_monitor.va"\n'
               'XMEASURE (XDUT.SEQ_SAMPLE XDUT.CMP_CLK XDUT.PHI_U VDD! VINP_SRC VINN_SRC XDUT.TOPP XDUT.TOPN %s) '
               'sar8_se_fft_monitor time_origin=59n\n' % ' '.join('D%d' % i for i in range(8)))
    test = test.rstrip('\n') + '\n' + monitor + 'save ' + ' '.join(FFT_SIGNALS) + '\n'
    if 'section=noise_worst' not in test:
        raise ValueError('The noise model section is missing')
    blobs['test.scs'] = test.encode()
    for dest, src in (('sar8_se_fft_monitor.va', 'tb/common/veriloga/sar8_se_fft_monitor.va'),
                      ('noise_fft_reduce.py', 'tools/saradc/measure/noise_fft_reduce.py'),
                      ('dynamic_reduce.py', 'tools/saradc/measure/dynamic_reduce.py'),
                      ('native_stream.py', 'tools/saradc/measure/native_stream.py')):
        blobs[dest] = (ROOT / src).read_bytes()
    base = json.loads((ROOT / 'tb/top/fft/context.json').read_bytes())
    ctx = dict(run_id=run_id, kind='fft', label='stage6-' + ctx0['stage6']['wiring'], corner='tt', vdd=ctx0['vdd_v'],
               temperature_c=ctx0['temperature_c'], reference_v=.9, frames=frames, warmup=warmup, samples=count,
               stop_s=stop, period_s=1e-7, frame_origin_s=59e-9, pilot=pilot, frequency_hz=base['frequency_hz'],
               bin=base['bin'], amplitude_dbfs=base['amplitude_dbfs'], signals=[s.lower() for s in FFT_SIGNALS],
               noise=True, noisefmin_hz=low, noisefmax_hz=2e9, noiseseed=seed, noisescale=1,
               segment=None if segment is None else dict(
                   index=segment, segments=segments, fft_frames=[first, first + length - 1],
                   record_frame_offset=first, offset_s=offset_s, sinephase_deg=phases,
                   limitation=('Independent seed per segment: noise below about 1/(7.2 us) = 140 kHz is not continuous '
                               'across segments')),
               noise_model_section='noise_worst',
               noise_scope='All enabled device models and every extracted and system-model resistor; ideal sources noiseless',
               noise_bandwidth_convergence='not_established', mismatch=False, PEX=True, pex_modules=ctx0['pex_modules'],
               source_deck=source_id, source_recipe_inputs={r['name']: r['sha256'] for r in recipe['inputs']},
               independent_cdac_gain=ctx0['independent_cdac_gain'], weights_source=ctx0['weights_source'],
               stage6=ctx0['stage6'], stage6_system_model=ctx0['stage6_system_model'],
               monitor='sar8_se_fft_monitor: TRACK = SEQ_SAMPLE, CMP = CMP_CLK, UPDATE = PHI_U (write count = update count)',
               checkpoint_scope='Periodic save enabled; no recovery or stitched output authorized by this recipe')
    ctx['source_hashes'] = {k: sha(v) for k, v in blobs.items()}
    blobs['context.json'] = (json.dumps(ctx, indent=2) + '\n').encode()
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    out = dict(schema_version=1, run_id=run_id, design_id=recipe['design_id'] + '_fft', entry='test.scs',
               analyzer='noise_fft_reduce.py', expected_stop_s=stop,
               inputs=[dict(name=k, source=(dest / k).relative_to(ROOT).as_posix(), sha256=sha(v)) for k, v in blobs.items()],
               resources=dict(threads=threads, simulation_rss_mib=STAGE6_RSS_MIB,
                              simulation_virtual_mib=4 * STAGE6_RSS_MIB, analysis_rss_mib=512,
                              analysis_virtual_mib=2048,
                              # The pilot wrote ~7.3 MB per frame; allow 16 MiB per frame.
                              max_output_mib=1024 if pilot else 16 * frames if segment is not None else 8192,
                              # 21 min per frame at 8 threads (pilot), slower at 4: allow 1 h per segment frame.
                              simulation_wall_seconds=43200 if pilot else 3600 * frames if segment is not None else 1814400,
                              analysis_wall_seconds=1800 if pilot else 14400, queue_timeout_seconds=86400),
               spectre_args=['+preset=mx', '+mt=%d' % threads, '-preset_override', '+lqtimeout', '900'],
               summary_signals=['sample'], test_conditions=ctx,
               qualification_scope=('Stage 6 %s deck %s: ' % (ctx0['stage6']['wiring'], source_id)
                                    + ('eight-frame transient-noise pilot of the FFT protocol; not an FFT result' if pilot else
                                       'segment %s of %d of the TT 1024-point transient-noise FFT (stitched by fft_stitch.py)'
                                       % (segment, segments) if segment is not None else
                                       'TT 1024-point transient-noise FFT, single seed, unconverged noise bandwidth')))
    blobs['recipe.yaml'] = (json.dumps(out, indent=2) + '\n').encode()
    for name, data in blobs.items():
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return dest / 'recipe.yaml'


if __name__ == '__main__':
    from tools.saradc.__main__ import engine
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    a = sub.add_parser('adc')
    a.add_argument('corner', choices=allx.CORNERS)
    a.add_argument('kind', choices=lpe.CODES)
    a.add_argument('--revision', default='a')
    a.add_argument('--wiring', default='lumped', help="'lumped' or the evidence ID of the xcell wiring extraction")
    a.add_argument('--pair', choices=['frozen', 'routed'], default='frozen',
                   help="'routed': the refilled pair se-xref-peripheral-routed and its weights (filled core)")
    a.add_argument('--boot', help='Bootstrap extraction at this corner in place of the frozen one')
    a.add_argument('--pad-bulk', choices=['planned', 'drawn'], default='planned',
                   help="Pad bulk decoupling: planned (constraints.json) or drawn (chip record; final Stage 6)")
    f = sub.add_parser('fft')
    f.add_argument('source_deck', help='Prepared TT Stage 6 deck (run ID)')
    f.add_argument('--pilot', action='store_true')
    f.add_argument('--threads', type=int, default=4)
    f.add_argument('--segment', type=int, help='Segment index of the split 1024-frame record (plus 8 warm-up frames)')
    f.add_argument('--segments', type=int, default=16, help='Number of near-equal segments of the 1024 frames')
    r = sub.add_parser('rails', help='Analysis-only rail budget job on a completed Stage 6 run (same host as the source)')
    r.add_argument('source_run_id')
    for p in (a, f, r):
        p.add_argument('--submit', metavar='HOST', choices=engine().HOSTS)
    args = ap.parse_args()
    if args.action == 'fft':
        path = prepare_fft(args.source_deck, args.pilot, threads=args.threads, segment=args.segment, segments=args.segments)
    elif args.action == 'rails':
        path = prepare_rails(args.source_run_id)
    else:
        path = prepare_adc(args.corner, args.kind, args.revision, args.wiring, args.pair, args.boot, args.pad_bulk)
    print(path.relative_to(ROOT).as_posix())
    if args.submit:
        from tools.saradc.__main__ import engine
        run_id = json.loads(path.read_text())['run_id']
        print(json.dumps(dict(registration=engine().register(path.relative_to(ROOT).as_posix(), host=args.submit),
                              submission=engine().phase('analyze' if args.action == 'rails' else 'submit', run_id,
                                                        queue=True)), indent=2))
