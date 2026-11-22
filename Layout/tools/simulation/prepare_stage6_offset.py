"""Comparator offset shift from the routed top-level wiring (Stage 6 of issue #12).

The comparator v8 extraction (with VDD/VSS RC) at the corner's interconnect corner is wired through the
top-level wiring extraction (prepare_stage6.wiring_package): CMP_CLK from the SAR-side pin, COMP_P/COMP_N to
symmetric standard-cell receivers at the SAR-side pins, TOPP/TOPN from the CDAC-side pins, supply through the
analog VDD and the VSS networks. A deterministic binary search (tb/common/veriloga/comp_search.va, 16 steps over
+/-8 mV, 0.24 uV resolution, 5 ns clock period) finds the trip point. Variants:
  extracted  the wiring as extracted
  symmetric  the CMP_CLK-COMP_P and CMP_CLK-COMP_N coupling capacitors scaled to their mean (no clock mismatch)
  none       comparator alone, ideal wiring (its own systematic offset)
The offset shift from the CLK coupling mismatch is extracted - symmetric; the whole routed wiring's is
extracted - none. The clock edge is 150 ps (TT) / 180 ps (SS) / 120 ps (FF), the measured SAR clock driver
transitions of the Stage 2 route checks.
  python -m Layout.tools.simulation.prepare_stage6_offset ssc extracted --wiring adc-core-guard-wire-xtr2
"""
import argparse
import json
import re

from Layout.project import ROOT
from Layout.tools.simulation import prepare_all_extracted as allx
from Layout.tools.simulation import prepare_stage6 as s6
from Layout.tools.simulation.prepare_full_sim import sha
from tools.saradc import single_edge_lpe as lpe

EDGE_PS = dict(tt=150, ssc=180, ffh=120)
RANGE_V, STEPS = .008, 16
PLATFORM = ROOT / 'tb/top/short/test.scs'


def symmetric_pxi(pxi):
    """Scale the CMP_CLK-COMP_P and CMP_CLK-COMP_N coupling capacitors to their common mean."""
    def net(node):
        for name in ('CMP_CLK', 'COMP_P', 'COMP_N'):
            if node.startswith('N_%s_' % name) or node in ('A_' + name, 'A_%s_CMP' % name):
                return name
        return None
    out, groups = [], {}
    for st in s6.statements(pxi.decode()):
        m = re.match(r'^(cc_\d+) \( (\S+) (\S+) \) capacitor c=([\d.eE+-]+)(f?)$', st)
        if m and {net(m[2]), net(m[3])} in ({'CMP_CLK', 'COMP_P'}, {'CMP_CLK', 'COMP_N'}):
            side = ({net(m[2]), net(m[3])} - {'CMP_CLK'}).pop()
            groups.setdefault(side, []).append(len(out))
            out.append([m[1], m[2], m[3], float(m[4]) * (1e-15 if m[5] else 1.)])
        else:
            out.append(st)
    if sorted(groups) != ['COMP_N', 'COMP_P']:
        raise ValueError('Expected CMP_CLK coupling to both comparator outputs')
    total = {side: sum(out[i][3] for i in idx) for side, idx in groups.items()}
    mean = sum(total.values()) / 2
    for side, idx in groups.items():
        for i in idx:
            name, a, b, c = out[i]
            out[i] = '%s ( %s %s ) capacitor c=%.6g' % (name, a, b, c * mean / total[side])
    return ('\n'.join(s6.wrap(x) for x in out) + '\n').encode(), {'CMP_CLK-' + k: v for k, v in total.items()}, mean


def prepare(corner, variant, wiring, run_id=None):
    if variant not in ('extracted', 'symmetric', 'none'):
        raise ValueError('Unknown variant')
    spec = allx.CORNERS[corner]
    cond = s6.CONDITIONS[corner]
    run_id = run_id or 'comp-s6-offset-%s-%s' % (corner, variant)
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    comp = allx.comparator_package(spec['comparator'], spec['rc'])
    blobs = dict(comp['files'])
    record = dict(comparator=comp['context'], corner=corner, condition=cond, variant=variant, clock_edge_ps=EDGE_PS[corner],
                  search=dict(range_v=RANGE_V, steps=STEPS, resolution_v=2 * RANGE_V / 2 ** STEPS))
    vdd = '%g' % cond['vdd_v']
    lines = ['simulator lang=spectre', 'global 0', 'parameters SUP=%s' % vdd]
    lines += [l.replace('section=ttmacro_mos_moscap', 'section=%smacro_mos_moscap' % cond['mos'].lower())
              for l in PLATFORM.read_text().splitlines() if l.startswith('include "/home/process/')]
    lines += ['simulatorOptions options temp=%d tnom=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13 method=trap maxwarns=5 '
              'maxnotes=5' % cond['temperature_c'], 'saveOptions options save=selected', 'include "library_include.scs"',
              'include "comparator_pex.scs"', 'ahdl_include "comp_search.va"',
              'subckt rx_buf A VDD VSS Y', '    X0 (A N VDD VSS) INVD1BWP12T30P140', '    X1 (N Y VDD VSS) INVD1BWP12T30P140',
              'ends rx_buf', 'VVDD (SUP 0) vsource dc=SUP',
              'VCLOCK (CLKS 0) vsource type=pulse val0=0 val1=SUP delay=2n rise=%dp fall=%dp width=1.95n period=5n'
              % (EDGE_PS[corner], EDGE_PS[corner]),
              'XSEARCH (VINP VINN OP ON PR NR CLKC SUP 0) sar8_mc_comp_search range_v=%g steps=%d' % (RANGE_V, STEPS)]
    if variant == 'none':
        lines += ['XCMP (CLKS ON OP SUP VINN VINP 0) sar_strongarm_t28', 'XRXN (ON SUP 0 NR) rx_buf',
                  'XRXP (OP SUP 0 PR) rx_buf', 'RCLKC (CLKS CLKC) resistor r=1m']
    else:
        wire = s6.wiring_package(wiring)
        files = dict(wire['files'])
        if variant == 'symmetric':
            files[s6.WIRE + 'extracted.scs.sar8_adc_core.pxi'], record['clk_coupling_F'], record['clk_coupling_mean_F'] = \
                symmetric_pxi(files[s6.WIRE + 'extracted.scs.sar8_adc_core.pxi'])
        blobs.update(files)
        # Wiring ports: supplies and the reference rails at their DC values, static nets grounded.
        # Boundary ports at their DC values; internal label nodes stay floating (they lie on the routes).
        formal = {'VDD_A': 'SUP', 'VDD_P': 'SUP', 'VDD_D': 'SUP', 'VREFP': 'VREFP', 'VSS_A': '0', 'VREFN': '0',
                  'SAMPLE': '0', 'VINN': '0', 'VINP': '0', **{'D%d' % i: '0' for i in range(8)}}
        # Block-side pins: the comparator's and the receivers' nets, static nets grounded, the rest floating.
        attach = {'CMP_CLK': 'CLKS', 'CMP_CLK_CMP': 'CLKC', 'COMP_P_CMP': 'OP', 'COMP_N_CMP': 'ON', 'COMP_P': 'OPR',
                  'COMP_N': 'ONR', 'TOPP': 'VINP', 'TOPN': 'VINN', 'TOPP_CMP': 'VINP_C', 'TOPN_CMP': 'VINN_C',
                  'VDDA_BLK': 'VDDC', 'VSSC': 'VSSC', 'VDDA_BN': 'SUP', 'VDDA_BP': 'SUP', 'VDDP_BLK': 'SUP', 'VDDD_BLK': 'SUP'}
        static = re.compile(r'^(CODE\d|PRESET|SEQ_SAMPLE|D\d_SAR|SAMPLE_SAR|VIN[NP]_BS)')
        ports = [formal.get(p, 'L_' + p) for p in wire['formal']]
        att = [attach.get(p[2:], '0' if static.match(p[2:]) else 'F_' + p[2:]) for p in wire['record']['attachment_ports']]
        record['floating_pins'] = [a for a in att if a.startswith('F_')]
        lines += ['VVREFP (VREFP 0) vsource dc=0.9',
                  'XWIRE (%s %s) stage6_wiring' % (' '.join(ports), ' '.join(att)),
                  'XCMP (CLKC ON OP VDDC VINN_C VINP_C VSSC) sar_strongarm_t28',
                  'XRXN (ONR SUP 0 NR) rx_buf', 'XRXP (OPR SUP 0 PR) rx_buf']
        lines.insert(lines.index('include "comparator_pex.scs"'), 'include "%sextracted.scs"' % s6.WIRE)
        record['wiring'] = wire['record']['evidence']
    stop = (STEPS + 11) * 5e-9 + 4e-9
    lines += ['comp_tran tran stop=%gn maxstep=5p errpreset=conservative' % (stop * 1e9),
              'save OP ON PR NR CLKC VINP VINN']
    blobs['test.scs'] = ('\n'.join(lines) + '\n').encode()
    blobs['comp_search.va'] = (ROOT / 'tb/common/veriloga/comp_search.va').read_bytes()
    blobs['library_include.scs'] = (ROOT / ('tb/common/platform/library_lpe_%s.scs' % lpe.CELL_RC[corner])).read_bytes()
    blobs['measure_comp_offset.py'] = (ROOT / 'Layout/tools/analysis/measure_comp_offset.py').read_bytes()
    blobs['native_stream.py'] = (ROOT / 'tools/saradc/measure/native_stream.py').read_bytes()
    ctx = dict(run_id=run_id, corner=corner, stop_s=stop, steps=STEPS, range_v=RANGE_V, offset_fixture=record)
    blobs['context.json'] = (json.dumps(ctx, indent=2) + '\n').encode()
    dest.mkdir(parents=True)
    for name, data in blobs.items():
        (dest / name).write_bytes(data)
    recipe = dict(schema_version=1, run_id=run_id, design_id='sar8_comparator_v8_stage6_wiring_offset', entry='test.scs',
                  analyzer='measure_comp_offset.py', expected_stop_s=stop,
                  inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b)) for n, b in blobs.items()],
                  resources=dict(threads=4, simulation_rss_mib=2048, simulation_virtual_mib=8192, analysis_rss_mib=256,
                                 analysis_virtual_mib=1024, max_output_mib=512, simulation_wall_seconds=7200,
                                 analysis_wall_seconds=600, queue_timeout_seconds=86400),
                  spectre_args=['+preset=mx', '+mt=4', '-preset_override', '+lqtimeout', '900'], summary_signals=['op', 'on'],
                  qualification_scope='Comparator trip point with the routed top-level wiring, variant %s, %s' % (variant, corner),
                  test_conditions=ctx)
    path = dest / 'recipe.json'
    path.write_text(json.dumps(recipe, indent=2) + '\n')
    return path


if __name__ == '__main__':
    from tools.saradc.__main__ import engine
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('corner', choices=allx.CORNERS)
    ap.add_argument('variant', choices=['extracted', 'symmetric', 'none'])
    ap.add_argument('--wiring', default='adc-core-guard-wire-xtr2')
    ap.add_argument('--submit', metavar='HOST', choices=engine().HOSTS)
    a = ap.parse_args()
    path = prepare(a.corner, a.variant, a.wiring)
    print(path.relative_to(ROOT).as_posix())
    if a.submit:
        from tools.saradc.__main__ import engine
        rid = json.loads(path.read_text())['run_id']
        print(json.dumps(dict(registration=engine().register(path.relative_to(ROOT).as_posix(), host=a.submit),
                              submission=engine().phase('submit', rid, queue=True)), indent=2))
