"""Timing check of the chip output register sar8_out_reg on the Stage 2 all-extracted ADC.

The base deck is `prepare_all_extracted adc CORNER verify` (every frozen block extraction at the paired
interconnect corner), prepared under a scratch revision and compared input by input with the registered
Stage 2 run of that corner. This entry adds design/chip/output_register.scs unchanged as XOREG: D0-D7 on the
ADC's D0-D7, CK on SAMPLE (the source that drives the ADC's SAMPLE pin), VDD on its own ideal DVDD source at
the corner supply (SUP), VSS on the shared ground, and 150 fF on each Q (the M5/M6 route to the pad I pin).
The standard cells come from the deck's library_include.scs, the foundry cell LPE at the paired corner that
the SAR macro leaves already use. The transient runs to 870 ns so that the SAMPLE edge at 860 ns captures
frame 7. The frozen single_edge_lpe analyzer scores the ADC codes; `timing` prepares the analysis-only job
measure_output_register.py (capture, setup, hold, clock-to-Q, DFQD1 CCS limits); `record` writes
Layout/results/output_register_timing.json from the collected runs.

  python -m Layout.tools.simulation.prepare_output_register adc ssc --revision a --submit thu-wei
  python -m Layout.tools.simulation.prepare_output_register timing sar8-oreg-ssc-a --submit thu-wei
  python -m Layout.tools.simulation.prepare_output_register record sar8-oreg-ssc-a sar8-oreg-ffh-a
"""
import argparse
import json
import re

from Layout.project import ROOT
from Layout.tools.simulation import prepare_all_extracted as pae
from Layout.tools.simulation.prepare_full_sim import sha
from tools.saradc import single_edge_lpe as lpe

REGISTER = 'design/chip/output_register.scs'
BITS = range(8)
# Long M5/M6 route from the register to the PRUW08SDGZ I pin.
Q_LOAD_F = 150e-15
# 11 ns past the 859 ns Stage 2 stop: the 860.05 ns SAMPLE edge captures frame 7, its D clear and Q settle.
STOP_S = 870e-9
# Stage 2 transient peaks were 2.36-2.38 GB. At FF hot the fallback DC solve (try_fast_op failed, as in
# sar8-allx-ffh-verify-a, where it took 25 s) ran longer with the register: sar8-oreg-ffh-b stopped at its
# 3072 MiB reservation at 3.2 GB, and sar8-oreg-ffh-c was still solving at 3.73 GB after 8.5 min.
SIMULATION_RSS_MIB = pae.SIMULATION_RSS_MIB
STAGE2 = {'tt': 'sar8-allx-tt-verify-c', 'ssc': 'sar8-allx-ssc-verify-a', 'ffh': 'sar8-allx-ffh-verify-a'}
ANALYZER = 'measure_output_register.py'
RECORD = 'Layout/results/output_register_timing.json'


def probes():
    """(saved node, analyzer name) of every register probe; the ADC D_i and SAMPLE are already saved."""
    rows = [('XOREG.DD%d' % i, 'xoreg.dd%d' % i) for i in BITS] + [('XOREG.QI%d' % i, 'xoreg.qi%d' % i) for i in BITS]
    return rows + [('Q%d' % i, 'q%d' % i) for i in BITS] + [('DVDD', 'dvdd')]


def bench():
    lines = ['// Chip output register on the ADC outputs (Layout/tools/simulation/prepare_output_register.py).',
             '// CK is the SAMPLE source node itself; DVDD is a separate ideal pad supply at the ADC supply value.',
             'simulator lang=spectre',
             'XOREG (%s %s SAMPLE DVDD 0) sar8_out_reg' % (' '.join('D%d' % i for i in BITS),
                                                         ' '.join('Q%d' % i for i in BITS)),
             'VDVDD (DVDD 0) vsource dc=SUP type=dc']
    lines += ['CQ%d (Q%d 0) capacitor c=%gf' % (i, i, Q_LOAD_F * 1e15) for i in BITS]
    lines.append('save ' + ' '.join(node for node, _ in probes()))
    return ('\n'.join(lines) + '\n').encode()


def stage2_identity(corner, blobs):
    """Input-by-input digest comparison of the rebuilt base deck with the registered Stage 2 run."""
    run = STAGE2[corner]
    old = {f['name']: f['sha256'] for f in json.loads((lpe.RUNS / run / 'recipe.json').read_bytes())['files']
           if f['name'] != 'native_summary.py'}
    new = {n: sha(b) for n, b in blobs.items()}
    return dict(run_id=run, identical=sorted(n for n in new if old.get(n) == new[n]),
                differs=sorted(n for n in new if n in old and old[n] != new[n]),
                only_rebuilt=sorted(set(new) - set(old)), only_stage2=sorted(set(old) - set(new)))


def prepare_adc(corner, revision, rss_mib=SIMULATION_RSS_MIB):
    run_id = 'sar8-oreg-%s-%s' % (corner, revision)
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', run_id):
        raise ValueError('Invalid revision')
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    base_path = pae.prepare_adc(corner, 'verify', 'oregbase-' + revision)
    base = json.loads(base_path.read_bytes())
    blobs = {f['name']: (ROOT / f['source']).read_bytes() for f in base['inputs']}
    identity = stage2_identity(corner, blobs)
    deck = blobs['test.scs'].decode()
    deck, count = re.subn(r'(?m)^include "tb\.scs"$',
                          'include "tb.scs"\ninclude "output_register.scs"\ninclude "output_register_tb.scs"', deck)
    if count != 1:
        raise ValueError('Expected one testbench include')
    deck, count = re.subn(r'(?m)^(tran_short tran stop=)\S+', r'\g<1>%.4g' % STOP_S, deck)
    if count != 1:
        raise ValueError('Expected one transient stop')
    if re.search(r'(?mi)^\S+ \((?:[^)]*\s)?(?:Q[0-7]|DVDD)[\s)]', deck + blobs['tb.scs'].decode()):
        raise ValueError('Register net names already used in the deck')
    source = (ROOT / REGISTER).read_bytes()
    blobs.update({'test.scs': deck.encode(), 'output_register.scs': source, 'output_register_tb.scs': bench()})
    ctx = json.loads(blobs['context.json'])
    if ctx['expected_stop_s'] >= STOP_S or ctx['frame_origin_s'] + ctx['frames'] * ctx['period_s'] > STOP_S - 10e-9:
        raise ValueError('Unexpected Stage 2 frame timing')
    names = [n for _, n in probes()]
    ctx.update(run_id=run_id, expected_stop_s=STOP_S,
               required_signals=ctx['required_signals'] + [n for n in names if n not in ctx['required_signals']],
               output_register=dict(
                   source=REGISTER, source_sha256=sha(source), subckt='sar8_out_reg', instance='XOREG',
                   cells=dict(delay='DEL250D1BWP12T30P140', flop='DFQD1BWP12T30P140', buffer='BUFFD4BWP12T30P140'),
                   cell_netlist='library_include.scs (foundry cell LPE %s, as for the SAR macro leaves)' % ctx['cell_lpe'],
                   connections=dict(D='D0-D7, the ADC outputs', CK='SAMPLE, the ideal source of the ADC SAMPLE pin',
                                    VDD='DVDD, separate ideal source dc=SUP (%g V)' % ctx['vdd_v'], VSS='0, shared ground'),
                   q_load_F=Q_LOAD_F, q_load_basis='long M5/M6 route from the register to the pad I pin',
                   probes=dict(adc_d=['d%d' % i for i in BITS], dd=['xoreg.dd%d' % i for i in BITS],
                               qi=['xoreg.qi%d' % i for i in BITS], q=['q%d' % i for i in BITS],
                               ck='sample', supply='dvdd'),
                   ck_probe='The register CK is the SAMPLE node (ideal route), so CK at the register is read at sample.',
                   stage2_stop_s=json.loads(blobs['context.json'])['expected_stop_s'], stop_s=STOP_S,
                   base_deck=dict(run_id=base['run_id'], recipe=base_path.relative_to(ROOT).as_posix(),
                                  recipe_sha256=sha(base_path.read_bytes())),
                   stage2_identity=identity))
    ctx['source_hashes'] = {k: sha(v) for k, v in blobs.items() if k != 'context.json'}
    blobs['context.json'] = (json.dumps(ctx, indent=2) + '\n').encode()
    recipe = dict(base)
    recipe['resources'] = dict(base['resources'], simulation_rss_mib=rss_mib, simulation_virtual_mib=max(16384, 4 * rss_mib))
    recipe.update(run_id=run_id, design_id=base['design_id'] + '_oreg', expected_stop_s=STOP_S, test_conditions=ctx,
                  qualification_scope=base['qualification_scope'] + (
                      '; chip output register sar8_out_reg (%s) on D0-D7, CK on SAMPLE, DVDD at the corner supply, '
                      '%g fF per Q, ideal wiring to the ADC, transient to %g ns' % (REGISTER, Q_LOAD_F * 1e15, STOP_S * 1e9)),
                  inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b)) for n, b in blobs.items()])
    dest.mkdir(parents=True)
    for n, b in blobs.items():
        (dest / n).parent.mkdir(parents=True, exist_ok=True)
        (dest / n).write_bytes(b)
    path = dest / 'recipe.yaml'
    path.write_text(json.dumps(recipe, indent=2) + '\n')
    return path


def prepare_timing(source_run_id, run_id=None):
    """Analysis-only register timing job on a completed prepare_output_register run."""
    run_id = run_id or source_run_id + '-timing'
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', run_id):
        raise ValueError('Invalid run ID')
    dest = ROOT / 'work/decks' / run_id
    if dest.exists():
        raise ValueError('Execution identity already prepared')
    source = json.loads((lpe.RUNS / source_run_id / 'recipe.json').read_bytes())
    if 'output_register' not in source['test_conditions']:
        raise ValueError('Not an output-register run: ' + source_run_id)
    blobs = {ANALYZER: (ROOT / 'Layout/tools/analysis' / ANALYZER).read_bytes(),
             'register_constraints.py': (ROOT / 'Layout/tools/analysis/register_constraints.py').read_bytes(),
             'native_stream.py': (ROOT / 'tools/saradc/measure/native_stream.py').read_bytes()}
    dest.mkdir(parents=True)
    for name, blob in blobs.items():
        (dest / name).write_bytes(blob)
    scope = ('Analysis-only timing of the chip output register in %s: capture of every settled code, setup and hold at '
             'the DFQD1 D pins and hold at the ADC outputs against the DFQD1 CCS constraints, clock-to-Q at %g fF'
             % (source_run_id, Q_LOAD_F * 1e15))
    spec = dict(schema_version=2, kind='analysis_only', source_run_id=source_run_id, run_id=run_id,
                design_id=source['design_id'], analyzer=ANALYZER,
                inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(b)) for n, b in blobs.items()],
                resources=dict(source['resources'], analysis_rss_mib=1024, analysis_wall_seconds=10800),
                spectre_args=source['spectre_args'], summary_signals=source['summary_signals'],
                expected_stop_s=source['expected_stop_s'], qualification_scope=scope,
                test_conditions=dict(source['test_conditions'], timing_source_run_id=source_run_id))
    path = dest / 'recipe.json'
    path.write_text(json.dumps(spec, indent=2) + '\n')
    return path


def collected(run_id):
    """Derived result of a collected run, checked against its collection receipt."""
    root = lpe.RUNS / run_id / 'collected'
    data = (root / 'derived/result.json').read_bytes()
    receipt = json.loads((root / 'collection_receipt.json').read_bytes())
    if not any(f['name'] == 'derived/result.json' and f['sha256'] == sha(data) for f in receipt['files']):
        raise ValueError('Collected result differs from its receipt: ' + run_id)
    return json.loads(data), sha(data)


def corner_record(run_id, timing_id):
    recipe = json.loads((lpe.RUNS / run_id / 'recipe.json').read_bytes())
    ctx = recipe['test_conditions']
    status = json.loads((lpe.RUNS / run_id / 'status.json').read_bytes())
    adc, adc_sha = collected(run_id)
    timing, timing_sha = collected(timing_id)
    frames = {f['frame']: f for f in adc['frames']}
    checks = []
    for e in timing['edges']:
        j = e['captured_frame']
        if j < 0 or j not in frames:
            continue
        f = frames[j]
        checks.append(dict(edge_ns=e['ck_ns'], frame=j, warmup=e['warmup'], q_word=e['q_word_after'],
                           d_word_at_edge=e['d_word_at_edge'], code90=f['code90'], code98=f['code98'],
                           decision_word=f['decision_word'], adc_frame_pass=f['pass'],
                           match=e['q_word_after'] == e['d_word_at_edge'] == f['code90'] == f['code98'] == f['decision_word']))
    scored = [c for c in checks if not c['warmup']]
    sim = status.get('simulation', {})
    return dict(
        corner=ctx['corner'], mos=ctx['mos'], vdd_v=ctx['vdd_v'], temperature_c=ctx['temperature_c'],
        cell_lpe=ctx['cell_lpe'], run_id=run_id, timing_run_id=timing_id,
        host=re.search(r'(?m)^remote_host: (\S+)', (ROOT / 'work/state/runs' / (run_id + '.yaml')).read_text())[1],
        recipe_hash=status['registered']['recipe_hash'], design_id=recipe['design_id'], source_commit=recipe['source_commit'],
        deck=dict(inputs={f['name']: f['sha256'] for f in recipe['files']
                          if f['name'] in ('test.scs', 'tb.scs', 'output_register.scs', 'output_register_tb.scs',
                                           'library_include.scs', 'dut.scs', 'context.json')},
                  base_deck=ctx['output_register']['base_deck'], stage2_identity=ctx['output_register']['stage2_identity']),
        simulation=dict(elapsed_s=sim.get('elapsed_seconds'), peak_rss_bytes=sim.get('peak_rss_bytes'),
                        output_bytes=sim.get('output_bytes')),
        adc_result_sha256=adc_sha, timing_result_sha256=timing_sha,
        adc=dict(all_pass=adc['all_pass'], min_margin_ns=adc['min_margin_ns'], warnings=adc['warnings'],
                 frames=[{'frame': f['frame'], 'warmup': f['warmup'], 'code90': f['code90'], 'pass': f['pass']}
                         for f in adc['frames']]),
        capture=dict(checks=checks, scored=len(scored), all_match=bool(scored) and all(c['match'] for c in scored),
                     analyzer_capture_pass=timing['summary']['capture_pass'],
                     frame7_captured=any(c['frame'] == 7 for c in scored)),
        worst=timing['summary']['worst'], liberty=timing.get('liberty'), liberty_error=timing.get('liberty_error'),
        q_glitches=timing['summary']['unexpected_q_transitions'])


def record(run_ids):
    rows = [corner_record(r, r + '-timing') for r in run_ids]
    result = dict(
        title='Chip output register sar8_out_reg timing on the Stage 2 all-extracted ADC',
        register=dict(source=REGISTER, source_sha256=sha((ROOT / REGISTER).read_bytes()), q_load_F=Q_LOAD_F),
        corners=rows,
        limitations=[
            'SAMPLE is an ideal pulse source (100 ps edges) that drives both the ADC and the eight CP pins; the chip '
            'SAMPLE_CORE pad buffer, its slew and its CK load are not modelled.',
            'Wiring between the ADC outputs and the register, and the CK route, are ideal; the register cells are the '
            'foundry cell LPE netlists without top-level extraction.',
            'DVDD is a separate ideal source at the ADC supply value and shares the ideal ground; no supply noise, IR '
            'drop or DVDD/VDD offset.',
            'Each Q load is a lumped 150 fF capacitor for the M5/M6 route; the PRUW08SDGZ I-pin input load and route '
            'resistance are not modelled.',
            'Deterministic runs at two corners (SS cold, FF hot); no mismatch or noise.',
            'Hold at the ADC outputs (without the delay cell) is scored against the same DFQD1 hold table at the ADC D '
            'slew, as if D drove the flop directly.'])
    path = ROOT / RECORD
    path.write_text(json.dumps(result, indent=2) + '\n')
    return path


if __name__ == '__main__':
    from tools.saradc.__main__ import engine
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='action', required=True)
    a = sub.add_parser('adc')
    a.add_argument('corner', choices=sorted(STAGE2))
    a.add_argument('--revision', default='a')
    a.add_argument('--rss-mib', type=int, default=SIMULATION_RSS_MIB, help='Simulation RSS reservation (MiB)')
    t = sub.add_parser('timing', help='Analysis-only register timing job on a completed run (same host as the source)')
    t.add_argument('source_run_id')
    t.add_argument('--run-id')
    r = sub.add_parser('record', help='Write the results record from collected runs and their -timing jobs')
    r.add_argument('run_ids', nargs='+')
    for p in (a, t):
        # An analysis-only job (timing) must run on its source run's host, where the raw waveform is.
        p.add_argument('--submit', metavar='HOST', choices=engine().HOSTS,
                       help='Register the recipe on this managed host and queue its simulation or analysis')
    args = ap.parse_args()
    if args.action == 'record':
        print(record(args.run_ids).relative_to(ROOT).as_posix())
        raise SystemExit
    path = prepare_adc(args.corner, args.revision, args.rss_mib) if args.action == 'adc' else \
        prepare_timing(args.source_run_id, args.run_id)
    print(path.relative_to(ROOT).as_posix())
    if args.submit:
        run_id = json.loads(path.read_text())['run_id']
        print(json.dumps(dict(registration=engine().register(path.relative_to(ROOT).as_posix(), host=args.submit),
                              submission=engine().phase('analyze' if args.action == 'timing' else 'submit', run_id,
                                                        queue=True)), indent=2))
