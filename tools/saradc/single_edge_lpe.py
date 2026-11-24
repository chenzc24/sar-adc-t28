"""Prepare the per-bit-tap single-edge SAR with foundry cell LPE and a 510-terminal extracted CDAC."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from . import reference_short as short
from .refsel import shared_pex_wrapper, split_cdac
from .schematic import electrical_statements
from .single_edge import CP_HIGH_PS, use_restart

ROOT = short.ROOT
RUNS = ROOT / 'work/output/managed_execution/runs'
SOURCE = 'sar-acq-q6-xrc-s10-ssc-20261119c'
CWORST = ROOT / 'work/layout/cdac-cworst'
CDAC_FILES = ['cdac_pex_wrapper.scs', 'cdac_xrc.scs', 'cdac_xrc.scs.pex', 'cdac_xrc.scs.sar8j_r1_cdac.pxi']
CELL_RC = {'tt': 'typical', 'ssc': 'cworst_t', 'ssh': 'cworst_t', 'ffc': 'cbest_t', 'ffh': 'cbest_t'}
# DEL250 stages before the comparison of bits 6, 5, 4, 3, 2 and 1-0. Bit 7 follows sampling directly.
TAPS = (11, 9, 7, 6, 5, 4)
# (select register, trial bit whose commit sets it, commit index within the frame)
SELECTS = ((9, 6, 1), (7, 5, 2), (6, 4, 3), (5, 3, 4), (4, 2, 5))
CODES = {'scan': [255, 0, 85, 170], 'verify': [255, 255, 0, 128, 85, 170, 127, 1],
         'boundary': [63, 64, 63, 64], 'reversal': [255, 255, 0, 128],
         # Full-scale reversals, low-to-mid steps and a final input 0.01 LSB above mid-scale.
         'extreme': [0, 255, 0, 128, 12, 127, 255, 128], 'restart': [255, 85, 170],
         # Alternating 0x7F/0x80 frames: every 0x7F result is followed by the full-word preset carry to 0x80.
         'carry': [127, 127, 128, 127, 128, 127, 128, 127],
         'smoke': [0, 255]}
CTRL = 'xtor/sar/single_edge.scs'
WINDOW = 'xdut.xctrl.xtim.xwindow.'
PROBES = ['xdut.xctrl.xtim.' + s for s in ('phase_request', 'delivered', 'ready', 'set', 'clr_n', 'sn_d')]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def set_window(source, taps=TAPS):
    """Rewrite the delay chain and the priority multiplexers for the given taps."""
    taps = tuple(taps)
    if len(taps) != 6 or any(a < b for a, b in zip(taps, taps[1:])) or taps[-1] < 1 or taps[0] > 32:
        raise ValueError('Expected six nonincreasing taps between 1 and 32')
    lines = ['XDEL%d (%s T%d VDD VSS) DEL250D1BWP12T30P140' % (i, 'PHASE_REQUEST' if i == 1 else 'T%d' % (i-1), i)
             for i in range(1, taps[0]+1)]
    upstream = 'T%d' % taps[0]
    for (name, _, _), tap in zip(SELECTS, taps[1:]):
        out = 'DELIVERED' if name == SELECTS[-1][0] else 'W%d' % name
        lines.append('XTAP%d (%s T%d SEL%d %s VDD VSS) MUX2D1BWP12T30P140' % (name, upstream, tap, name, out))
        upstream = out
    newline = b'\r\n' if b'\r\n' in source else b'\n'
    pattern = rb'(?m)^XDEL1 \(PHASE_REQUEST[^\r\n]*(?:\r?\nXDEL\d+ [^\r\n]*)*(?:\r?\nXTAP\d+ [^\r\n]*){5}'
    source, count = re.subn(pattern, newline.join(s.encode() for s in lines), source)
    if count != 1:
        raise ValueError('Expected one delay chain and five tap multiplexers')
    return source


def selectors(taps=TAPS):
    rows, upstream = [], WINDOW + 't%d' % taps[0]
    for (name, trial, index), tap in zip(SELECTS, taps[1:]):
        rows.append(dict(name='sel%d' % name, q='xdut.xctrl.sel%d' % name, trial='xdut.xctrl.trial%d' % trial,
                         commit_index=index, inputs=[upstream, WINDOW + 't%d' % tap]))
        upstream = WINDOW + 'w%d' % name
    return rows


def retained_inputs(folder, names):
    files = {f['name']: f['sha256'] for f in json.loads((folder / 'recipe.json').read_bytes())['files']}
    out = {}
    for n in names:
        out[n] = (folder / 'inputs' / n).read_bytes()
        if digest(out[n]) != files[n]:
            raise ValueError('Archived input digest differs for ' + n)
    return out


def simulation_of(run_id):
    """The simulation behind a weight result: itself, or the source of an analysis-only rerun of its analyzer."""
    recipe = json.loads((RUNS / run_id / 'recipe.json').read_bytes())
    return recipe.get('test_conditions', {}).get('reanalysis_source_run_id') or run_id


def measured_weights(run_id, gds):
    root = RUNS / run_id
    physical = json.loads(retained_inputs(RUNS / simulation_of(run_id), ['physical.json'])['physical.json'])
    if physical['gds']['sha256'] != gds:
        raise ValueError('Independent CDAC weights use a different layout: ' + run_id)
    data = (root / 'collected/derived/result.json').read_bytes()
    receipt = json.loads((root / 'collected/collection_receipt.json').read_bytes())
    if not any(f['name'] == 'derived/result.json' and f['sha256'] == digest(data) for f in receipt['files']):
        raise ValueError('Independent CDAC weights do not match their receipt: ' + run_id)
    return json.loads(data)['post']['metrics']['effective_weights_v'], digest(data)


def cdac_bundle(view, corner):
    archive = retained_inputs(RUNS / SOURCE, CDAC_FILES + ['context.json', 'test.scs', 'xtor/cdac/cdac.scs'])
    control = json.loads(archive['context.json'])
    gds = control['cdac_physical_gds_sha256']
    groups = control['cdac_plate_nodes']
    saves = [line for line in archive['test.scs'].splitlines() if line.startswith(b'save XDUT.XCDAC.XPEX.')]
    if view == 'nominal':
        files = {n: archive[n] for n in CDAC_FILES}
        weights_id = 'cdac-stacked-mx-20261118' if corner == 'tt' else 'cdac-stacked-mx-%s-20261118' % corner
        source = SOURCE
    elif view == 'cworst':
        # Same GDS and LVS reference re-extracted with the CWORST_T xRC rules (work/layout/cdac-cworst).
        package = json.loads((CWORST / 'package.json').read_text())
        if package['gds_sha256'] != gds or package['interconnect_rc']['corner'] != 'cworst_T':
            raise ValueError('CWORST package uses a different CDAC layout or corner')
        if package['plate_names_match'] != {'n': True, 'p': True}:
            raise ValueError('CWORST plate terminals need a name map')
        files = {n: (CWORST / 'package' / n).read_bytes() for n in CDAC_FILES}
        for n, data in files.items():
            if digest(data) != package['package'][n]:
                raise ValueError('Packaged CWORST file differs from package.json: ' + n)
        if corner not in ('ssc', 'ffc'):
            raise ValueError('CWORST CDAC weights exist for the cold corners only')
        weights_id = 'cdac-stacked-cw-%s-20261120' % corner
        source = package['evidence']
    else:
        raise ValueError('Unknown CDAC view')
    names = [s.decode().replace('\\', '').lower() for line in saves for s in line.split()[1:]]
    flat = [s for side in ('n', 'p') for group in groups[side] for s in group]
    if sorted(names) != sorted(flat) or len(set(names)) != 510:
        raise ValueError('Expected all 510 physical capacitor terminals')
    if any([len(g) for g in groups[side]] != [1 << i for i in range(8)] for side in ('n', 'p')):
        raise ValueError('Unexpected terminal grouping')
    weights, weights_sha = measured_weights(weights_id, gds)
    return dict(view=view, files=files, groups=groups, saves=saves, gds=gds, source=source,
                schematic=archive['xtor/cdac/cdac.scs'], weights=weights, weights_id=weights_id,
                weights_sha=weights_sha)


def prepare(corner, kind, cdac='nominal', revision='a', taps=TAPS, seed=None, macro=None, bootstrap=None,
            xref=None, comparator=None, family=None, settling_limit=.25, rss_mib=3584, testbench=None):
    """macro: extracted SAR macro from Layout.tools.simulation.prepare_sar_se (files, top, probe, record).
    bootstrap: physical ID of a verified Bootstrap core extraction that replaces both channels.
    xref: coupled XREF/CDAC extraction from Layout.tools.simulation.prepare_all_extracted.xref_package; it
    replaces both XCDAC and XREF, and its standalone weights replace the CDAC bundle (cdac is then ignored).
    comparator: comparator extraction from prepare_all_extracted.comparator_package.
    family: run-ID family that replaces the default sebit/sepl label scheme.
    testbench: callable(blobs, ctx) that edits the generated testbench files after the stimulus is set
    (Layout/tools/simulation/prepare_stage6.py: reference and supply system model)."""
    taps = tuple(taps)
    boot = None
    if bootstrap is not None:
        from Layout.tools.simulation import bootstrap_pex
        boot = bootstrap_pex.package(bootstrap)
    if corner not in CELL_RC or kind not in CODES:
        raise ValueError('Unknown corner or stimulus')
    if seed is not None and (corner not in ('ssc', 'ffc') or kind == 'restart'):
        raise ValueError('Local mismatch is prepared for the cold corners only')
    if macro is not None and taps != TAPS:
        raise ValueError('The extracted macro fixes the delay taps')
    rc = CELL_RC[corner]
    tag = '' if taps == TAPS else '-t%d' % taps[0] if len(set(taps)) == 1 else '-t' + 'x'.join(map(str, taps))
    if family is None:
        family = 'sepl' if macro else 'sebit'
        label = ({'nominal': 'nom', 'cworst': 'cw'}[cdac] + '-' + kind + tag + ('-bootx' if boot else '')
                 + ('-s%d' % seed if seed is not None else ''))
    else:
        label = kind + tag + ('-s%d' % seed if seed is not None else '')
    rid = 'sar8-%s-%s-%s-%s' % (family, corner, label, revision)
    dest = ROOT / 'work/decks' / rid
    bundle = xref['bundle'] if xref else cdac_bundle(cdac, corner)
    dut = (ROOT / 'design/dut.scs').read_bytes()
    sources = {name: (ROOT / 'design' / name).read_bytes()
               for name in re.findall(r'^include "([^"]+)"', dut.decode(), re.M)}
    if not xref:
        cdac = split_cdac(sources['xtor/cdac/cdac.scs'].decode())
        if electrical_statements(cdac) != electrical_statements(bundle['schematic'].decode()):
            raise ValueError('Schematic CDAC identity differs from extraction control')
    sources[CTRL] = set_window(sources[CTRL], taps)
    if dut.count(b'"xtor/cdac/cdac.scs"') != 1:
        raise ValueError('Expected one CDAC include')
    sources['dut.scs'] = dut if xref else dut.replace(b'"xtor/cdac/cdac.scs"', b'"cdac_pex_wrapper.scs"')
    sources.update(bundle['files'])
    if not xref:
        wrapper = sources['cdac_pex_wrapper.scs'].decode()
        sources['cdac_pex_wrapper.scs'] = shared_pex_wrapper(wrapper).encode()
    if boot:
        sources['dut.scs'] = bootstrap_pex.use(sources['dut.scs'])
        sources.update(boot['files'])
    if macro is not None:
        # The extracted macro replaces the five SAR-group instances of the top.
        top_include = b'include "top/adc_top.scs"'
        if sources['dut.scs'].count(top_include) != 1:
            raise ValueError('Expected one top include')
        sources['dut.scs'] = sources['dut.scs'].replace(top_include, b'include "%s"\n' % macro['entry'].encode() + top_include)
        sources['top/adc_top.scs'] = macro['top']
        sources.update(macro['files'])
    if xref:
        # One coupled extraction replaces XCDAC and XREF in the (possibly macro-bound) top.
        xref['bind'](sources)
    if comparator:
        sources['dut.scs'] = comparator['use'](sources['dut.scs'])
        sources.update(comparator['files'])
    library = (ROOT / ('tb/common/platform/library_lpe_%s.scs' % rc)).read_bytes()
    template = ROOT / short.prepare('single_edge', corner, '%s-%s-%s' % (family, label, revision),
                                    codes=CODES[kind], source_blobs=sources, cell_library=library,
                                    extracted_gate_probes=bool(xref))
    recipe = json.loads(template.read_bytes())
    blobs = {f['name']: (ROOT / f['source']).read_bytes() for f in recipe['inputs']}
    ctx = json.loads(blobs['context.json'])
    weights = bundle['weights']
    gain = sum(weights) / (ctx['lsb_v'] * 255)
    coords = None
    if kind == 'boundary':
        coords = [63, 64] + [127.5 + gain * (x - 127.5) for x in (63, 64)]
    elif kind == 'extreme':
        coords = CODES[kind][:-1] + [127.51]
    if coords:
        tb = blobs['tb.scs'].decode()
        for node, sign in (('P', 1), ('N', -1)):
            line = 'VVIN'+node+' (VIN'+node+'_SRC 0) vsource type=pwl wave=['+short.stimulus(coords, sign)+']'
            tb, count = re.subn(r'(?m)^VVIN'+node+r' .*$', line, tb)
            if count != 1:
                raise ValueError('Missing differential input')
        blobs['tb.scs'] = tb.encode()
        ctx['input_code_coordinates'] = coords
    if kind == 'restart':
        use_restart(blobs, ctx, recipe)
    if testbench:
        testbench(blobs, ctx)
    group_names =[s for side in ('n', 'p') for group in bundle['groups'][side] for s in group]
    sel = selectors(taps)
    signals = [s for s in ctx['required_signals'] if not s.startswith('xdut.xcdac.')]
    if boot:
        signals = [s for s in signals if s not in bootstrap_pex.INTERNAL]
    extra = [r['q'] for r in sel] + [r['trial'] for r in sel] + [n for r in sel for n in r['inputs']] + PROBES
    if xref:
        extra += xref.get('signals', [])
    signals += [s for s in dict.fromkeys(extra) if s not in signals]
    ctx['required_signals'] = signals + ([] if kind == 'restart' else group_names)

    # A probe returns the exact, case-sensitive node to save, or None for an unchanged net.
    def probe(s):
        if boot and s in boot['probes']:
            return boot['probes'][s]
        if xref and s in xref['probes']:
            return xref['probes'][s]
        return macro['probe'](s) if macro else None
    probes = [probe(s) for s in signals]
    saved = [p or s.upper() for s, p in zip(signals, probes)]
    if len(set(saved)) != len(saved):
        raise ValueError('Two schematic probes map to one saved node')
    if any(probes):
        ctx['signal_aliases'] = {p.replace('\\', '').lower(): s for s, p in zip(signals, probes) if p}
    deck, count = re.subn(rb'(?m)^save [^\r\n]+', b'save ' + ' '.join(saved).encode(), blobs['test.scs'])
    if count != 1:
        raise ValueError('Expected one save statement')
    deck, count = re.subn(rb'(?m)^(tran_short tran [^\r\n]+)', rb'\1 strobeperiod=5p strobeoutput=strobeonly', deck)
    if count != 1:
        raise ValueError('Missing unique transient')
    if seed is not None:
        mos = ctx['mos']
        text = deck.decode()
        for old, new in (('section='+mos.lower()+'macro_mos_moscap', 'section='+mos+'GlobalCorner_LocalMC_MOS_MOSCAP'),
                         ('section=tt_mom', 'section=TTGlobalCorner_LocalMC_MOM')):
            if old not in text:
                raise ValueError('Missing model section ' + old)
            text = text.replace(old, new)
        mc = ('mc montecarlo numruns=1 seed=%d variations=mismatch dut=[XDUT] sampling=standard '
              'donominal=no savemismatchparams=yes mismatchparamfile="mismatch.params" '
              'mismatchscalarfile="mismatch.values" savefamilyplots=yes savedatainseparatedir=yes {\n')
        text = re.sub(r'(?m)^(tran_short tran .*)$', lambda m: mc % seed + m[1] + '\n}', text)
        deck = text.encode()
        ctx.update(seed=seed, statistical_mode='fixed process, whole-DUT local mismatch',
                   mos_section=mos+'GlobalCorner_LocalMC_MOS_MOSCAP',
                   passive_sections=['TTGlobalCorner_LocalMC_MOM' if s == 'tt_mom' else s
                                     for s in ctx['passive_sections']])
    blobs['test.scs'] = deck + (b'' if kind == 'restart' else b'\n' + b'\n'.join(bundle['saves'])) + b'\n'
    ctx.update(run_id=rid, kind=kind, taps=list(taps), selectors=sel, pex=True, pex_modules=['cdac'], cell_lpe=rc,
               cdac_view=bundle['view'], cdac_source=bundle['source'], cdac_physical_gds_sha256=bundle['gds'],
               cdac_plate_nodes=bundle['groups'], cdac_weights_v=weights, independent_cdac_gain=gain,
               weights_source=bundle['weights_id'], weights_result_sha256=bundle['weights_sha'],
               current_signals=[], mismatch=seed is not None, settling_limit_lsb=settling_limit, settling_target_lsb=.125,
               first_compare_gate_limit_v=.1,
               # A repeated first code makes frame 0 a warm-up frame: it starts from the DC solution.
               warmup_frames=1 if len(CODES[kind]) > 1 and CODES[kind][0] == CODES[kind][1] else 0)
    if xref:
        ctx.update(xref['context'], pex_modules=ctx['pex_modules'] + ['xref'])
    if macro:
        ctx.update(pex_modules=ctx['pex_modules'] + ['sar'], sar_macro=macro['record'])
    if boot:
        ctx.update(boot['context'], pex_modules=ctx['pex_modules'] + ['bootstrap'])
    if comparator:
        ctx.update(comparator['context'], pex_modules=ctx['pex_modules'] + ['comparator'])
    if kind == 'restart':
        blobs['single_edge_restart.py'] = (ROOT / 'tools/saradc/measure/single_edge_restart.py').read_bytes()
        analyzer = 'single_edge_restart.py'
    else:
        blobs['single_edge_lpe.py'] = (ROOT / 'tools/saradc/measure/single_edge_lpe.py').read_bytes()
        blobs['single_edge_audit.py'] = (ROOT / 'tools/saradc/measure/single_edge_audit.py').read_bytes()
        blobs['register_constraints.py'] = (ROOT / 'Layout/tools/analysis/register_constraints.py').read_bytes()
        blobs['dff.json'] = (RUNS / 'sar-qlpe-dff-ccs-five-20261119a/collected/derived/result.json').read_bytes()
        ctx['min_cp_high_ps'] = CP_HIGH_PS[corner]
        analyzer = 'single_edge_lpe.py'
    ctx['source_hashes'] = {k: digest(v) for k, v in blobs.items() if k != 'context.json'}
    blobs['context.json'] = (json.dumps(ctx, indent=2) + '\n').encode()
    recipe['resources'].update(simulation_rss_mib=rss_mib, simulation_virtual_mib=max(16384, 4 * rss_mib),
                               analysis_rss_mib=1024, analysis_wall_seconds=10800,
                               max_output_mib=2048 + 1200 * ctx['frames'])
    recipe['spectre_args'][recipe['spectre_args'].index('+lqtimeout') + 1] = '900'
    view = xref['scope'] if xref else '%s extracted CDAC' % cdac
    scope = ('%s cell LPE, %s, ideal SAR inter-cell wiring, 45 ns sampling' % (rc, view) if not macro else
             'extracted SAR macro %s (%s interconnect), %s cell LPE for the remaining cells, %s, 45 ns sampling'
             % (macro['record']['physical_id'], macro['record'].get('interconnect_rc', 'typical'), rc, view))
    if boot:
        scope += ', extracted Bootstrap %s on both channels' % bootstrap
    if comparator:
        scope += ', ' + comparator['scope']
    recipe.update(run_id=rid, design_id='sar8_single_edge_bitwise_' + ('sar_macro_xrc' if macro else 'cell_lpe_cdac_xrc')
                  + ('_xref_xrc' if xref else '') + ('_boot_xrc' if boot else '') + ('_comp_xrc' if comparator else ''),
                  analyzer=analyzer, qualification_scope=scope,
                  test_conditions=ctx, inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(),
                                                    sha256=digest(b)) for n, b in blobs.items()])
    blobs['recipe.yaml'] = (json.dumps(recipe, indent=2) + '\n').encode()
    for n, b in blobs.items():
        path = dest / n
        if path.exists() and path.read_bytes() != b:
            raise ValueError('Frozen path differs: ' + str(path))
    for n, b in blobs.items():
        path = dest / n
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b)
    return dest / 'recipe.yaml'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corner', choices=CELL_RC)
    p.add_argument('kind', choices=CODES)
    p.add_argument('--cdac', choices=['nominal', 'cworst'], default='nominal')
    p.add_argument('--revision', default='a')
    p.add_argument('--taps', type=lambda s: tuple(int(x) for x in s.split(',')), default=TAPS)
    p.add_argument('--seed', type=int)
    p.add_argument('--bootstrap', metavar='PHYSICAL_ID', help='Replace both Bootstrap channels with this core extraction')
    a = p.parse_args()
    print(prepare(a.corner, a.kind, a.cdac, a.revision, a.taps, a.seed, bootstrap=a.bootstrap))
