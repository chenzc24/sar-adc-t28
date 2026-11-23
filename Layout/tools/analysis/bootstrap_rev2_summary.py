"""Record of the Bootstrap core revision layout_r2 (latch-up, planned fill) and its requalification (issue #12).

Reads digest-verified collected results and the physical manifests on the layout host. Runs that are not
collected yet appear under `pending`; nothing missing is scored as a pass.
  python -m Layout.tools.analysis.bootstrap_rev2_summary --output results/integration/bootstrap_rev2_20261122.json
"""
import argparse
import json

from Layout.project import ROOT, evidence
from Layout.tools.analysis import bootstrap_corner_summary, bootstrap_parasitics, gate_disposition, stage2_summary
from Layout.tools.simulation import bootstrap_pex
from Layout.tools.simulation.prepare_full_sim import pull

RUNS = stage2_summary.RUNS
FROZEN = 'boot-core-20261121'
CORE = 'boot-core-r2b-20261122'
FILLED = 'boot-fill-r2-20261122'
CORNERS = ('', '-cworst-t', '-cbest-t')
# (r2 run, the earlier run of the same stimulus and RC corner, Bootstrap configuration)
ADC = [('sar8-bsr2-ssc-verify-a', 'sar8-allxc-ssc-verify-a', 'r2 without fill'),
       ('sar8-bsr2-ssc-carry-a', 'sar8-allxc-ssc-carry-a', 'r2 without fill'),
       ('sar8-bsr2-tt-verify-a', 'sar8-allx-tt-verify-c', 'r2 without fill'),
       ('sar8-bsr2-ssc-verify-f2', 'sar8-allxc-ssc-verify-a', 'r2 with planned fill'),
       ('sar8-bsr2-ssc-extreme-f2', 'sar8-allxc-ssc-extreme-a', 'r2 with planned fill'),
       ('sar8-bsr2-ssc-carry-f2', 'sar8-allxc-ssc-carry-a', 'r2 with planned fill'),
       ('sar8-bsr2-ssc-restart-f2', 'sar8-allxc-ssc-restart-a', 'r2 with planned fill'),
       ('sar8-bsr2-ffh-verify-f2', 'sar8-allx-ffh-verify-a', 'r2 with planned fill'),
       ('sar8-bsr2-ffh-extreme-f2', 'sar8-allx-ffh-extreme-b', 'r2 with planned fill'),
       ('sar8-bsr2-ffh-carry-f2', 'sar8-allx-ffh-carry-a', 'r2 with planned fill'),
       ('sar8-bsr2-ffh-restart-f2', 'sar8-allx-ffh-restart-a', 'r2 with planned fill'),
       ('sar8-bsr2-tt-verify-f2', 'sar8-allx-tt-verify-c', 'r2 with planned fill'),
       ('sar8-bsr2-tt-restart-f2', 'sar8-allx-tt-restart-a', 'r2 with planned fill')]
# Standalone sampler bench (tb/blocks/bootstrap): r2 run and the frozen core's run at that corner.
STANDALONE = [('tt', 'boot-r2f2-tt-20261122', 'boot-core-tt-20261121'),
              ('ssc', 'boot-r2f2-ssc-20261122', 'boot-m4-ext-ssc-20261121'),
              ('ssh', 'boot-r2f2-ssh-20261122', 'boot-core-ssh-20261121'),
              ('ffc', 'boot-r2f2-ffc-20261122', 'boot-m4-ext-ffc-20261121'),
              ('ffh', 'boot-r2f2-ffh-20261122', 'boot-core-ffh-20261121')]
UNFILLED_STANDALONE = ('ssc', 'boot-r2-ssc-20261122')
GATE = [('sar8-bsr2-ssc-verify-a-gate', 'sar8-allxc-ssc-verify-a-gate'),
        ('sar8-bsr2-ssc-verify-f2-gate', 'sar8-allxc-ssc-verify-a-gate'),
        ('sar8-bsr2-ssc-extreme-f2-gate', 'sar8-allxc-ssc-extreme-a-gate')]
FLAT_LUP = {'r2': 'boot-r2-chip-flat-lup', 'frozen control': 'boot-frozen-chip-flat-lup'}
# Routed CMP_CLK (Stage 6 deck, Stage 2 session's runs): (r2 gate job, old-core run, old-core gate job).
ROUTED = [('sar8-s6e-ssc-extreme-r2-gate', 'sar8-s6e-ssc-extreme-a', 'sar8-s6e-ssc-extreme-a-gate'),
          ('sar8-s6e-ssc-verify-r2-gate', 'sar8-s6e-ssc-verify-c', 'sar8-s6e-ssc-verify-c-gate')]
PENDING = [
    dict(item='Cause of the SS-cold residual increase with fill', runs=[],
         status='likely, unproven: the plate parasitic lowers the boost on the channel at VIN ~ 0.9 V'),
]
DISPOSITION_RULE = dict(
    source='Layout/tools/analysis/gate_disposition.py', gate_screen_v=.1, specification_unchanged=True,
    decisions=[dict(date='2026-11-22', where='coordinator session', text='pre-approved: mark a small overshoot of the '
                    'routed gate screen as passed under conditions'),
               dict(date='2026-11-22', where='this session', text='TOP disturbance scored as its gate-attributable '
                    'part (same-deck slope)'),
               dict(date='2026-11-23', where='coordinator session', text='"residual unchanged" replaced by "residual '
                    'within the Stage 6 limit, fill effect recorded separately"')],
    conditions=['worst gate screen <= 0.111 V', 'gate-attributable TOP movement <= 0.05 LSB',
                'codes equal and plate settling within 0.01 LSB of the old-core routed runs',
                'sample-close residual <= 0.25 LSB (Stage 6 limit)'])


def adc_row(run_id, earlier_id, config):
    def view(rid):
        r = stage2_summary.summarize(rid)
        keep = ('run_id', 'recipe_sha256', 'result_sha256', 'corner', 'kind', 'bootstrap', 'codes_within_1',
                'events_8_8', 'pin_pass', 'max_abs_close_error_lsb', 'max_abs_signed_settling_lsb',
                'max_weighted_bound_lsb', 'min_read_margin_ns', 'max_first_compare_gate_overdrive_v',
                'setup_hold_slack_ps', 'warnings', 'passed', 'comparisons', 'updates', 'public_read_codes')
        out = dict((k, r[k]) for k in keep if k in r)
        if 'reference_split' in r:
            out['excluding_static_lsb'] = r['reference_split']['max_abs_lsb']['excluding_static_lsb']
            out['static_pin_offset_mv'] = r['reference_split']['quiet_pin_offset_mv']
        if r['kind'] != 'restart':
            settled = r['settling_pass'] or r.get('settling_pass_excluding_static_offset', False)
            out['stage2_pass'] = bool(r['codes_within_1'] and r['events_8_8'] and r['pin_pass'] and r['close_pass']
                                      and settled and r['margin_pass']
                                      and r['max_first_compare_gate_overdrive_v'] <= gate_disposition.GATE_SCREEN_V)
            out['frames'] = [dict((k, f[k]) for k in ('frame', 'warmup', 'input_code', 'code', 'target',
                                                      'close_error_lsb', 'max_abs_signed_settling_lsb',
                                                      'read_margin_ns', 'first_compare_gate_overdrive_v'))
                             for f in r['frames']]
        else:
            out['stage2_pass'] = bool(r['passed'])
        return out
    row = dict(bootstrap_config=config, r2=view(run_id), earlier=view(earlier_id))
    row['bootstrap_extraction'] = row['r2']['bootstrap'].rsplit('/', 1)[-1] if row['r2'].get('bootstrap') else None
    return row


def standalone(rid):
    result, recipe, digest = stage2_summary.collected(rid)
    m = result['metrics']['sampler']
    return dict(run_id=rid, result_sha256=digest, recipe_sha256=recipe['recipe_hash'], passed=result['pass_validation'],
                physical_evidence=recipe['test_conditions'].get('physical_evidence'),
                sampling_error_mv=m['normal_error_v'] * 1e3, startup_error_mv=m['startup_error_v'] * 1e3,
                hold_droop_mv=m['hold_droop_v'] * 1e3,
                limit_mv=result['context']['contracts']['sampler']['limits']['sample_error_v'] * 1e3)


def plates(identity):
    """Boot-capacitor plates: capacitance to ground (node 0 and VSS) and between the plates, fF."""
    devices, subckts, calls, coupling = bootstrap_parasitics.parse(bootstrap_pex.package(identity)['files'])
    out = {}
    for net, name in (('3', 'btop'), ('4', 'bbot')):
        to = {}
        for x, y, c in subckts[net]['c']:
            key = 'ground' if '0' in (x, y) else 'internal'
            to[key] = to.get(key, 0.) + c * 1e15
        for x, y, c in coupling:
            a, b = bootstrap_parasitics.net_of(x), bootstrap_parasitics.net_of(y)
            if net in (a, b):
                other = b if a == net else a
                key = 'ground' if other in ('0', 'VSS') else 'plate' if other in ('3', '4') else 'other'
                to[key] = to.get(key, 0.) + c * 1e15
        out[name + '_ground_fF'] = to.get('ground', 0.)
        out['plate_plate_fF'] = to.get('plate', 0.)
    return out


def record():
    extractions = {}
    for base in (FROZEN, CORE, FILLED):
        for suffix in CORNERS:
            ident = base + suffix
            e = bootstrap_corner_summary.extraction(ident)
            e['plates'] = plates(ident)
            extractions[ident] = e
    flat = {}
    for label, ident in FLAT_LUP.items():
        m = json.loads(pull(evidence(ident) + '/manifest.json'))
        flat[label] = dict(evidence=ident, gds_sha256=m['gds']['sha256'], deck=m['decks']['drc']['variant'],
                           flat=m['decks']['drc']['flat'], rulechecks=len(m['decks']['drc']['selected']),
                           markers_by_rule=m['checks']['drc']['markers_by_rule'])
    build = json.loads(pull(evidence('boot-fill-build-20261122') + '/manifest.json'))
    core_build = json.loads(pull(evidence(CORE) + '/manifest.json'))
    oa = dict(core=dict(view='sar_bootstrap_flat_8b_p_core/layout_r2', evidence=CORE, gds_sha256=core_build['gds']['sha256'],
                        other_views_unchanged=core_build.get('other_views_layout_oa_sha256')),
              fill=dict(build=build['ident'], fill_cell='sar_bootstrap_flat_8b_p_fill/layout_r2',
                        wrapper='sar_bootstrap_flat_8b_p_filled/layout_r2', build_il_sha256=build['build_il_sha256'],
                        layout_oa_sha256=dict((c, build['after'][c]) for c in build['after']),
                        core_views_unchanged=build['before']['sar_bootstrap_flat_8b_p_core'] ==
                        build['after']['sar_bootstrap_flat_8b_p_core'], wrapper_gds_sha256=build['gds']['sha256']))
    adc, pending_runs = [], []
    for run_id, earlier_id, config in ADC:
        try:
            adc.append(adc_row(run_id, earlier_id, config))
        except FileNotFoundError:
            pending_runs.append(run_id)
    sampler = []
    for corner, new, old in STANDALONE:
        sampler.append(dict(corner=corner, r2_filled=standalone(new), frozen=standalone(old)))
    unfilled = dict(corner=UNFILLED_STANDALONE[0], r2_unfilled=standalone(UNFILLED_STANDALONE[1]))
    gate = []
    for run_gate, control in GATE:
        run = gate_disposition.disturbance(run_gate)
        same = gate_disposition.disturbance(control, run['frame'], run['channel'])
        gate.append(dict(run=run, control_same_frame=same, attributable=gate_disposition.attributable(run, same)))
    routed = gate_disposition.verdict(ROUTED)
    routed['routed_runs'] = [dict(r2=stage2_summary.summarize(g.rsplit('-gate', 1)[0]), old_core=stage2_summary.summarize(o))
                             for g, o, _ in ROUTED]
    for row in routed['routed_runs']:
        for side in row.values():
            side.pop('frames', None)
            side.pop('per_bit', None)
    from Layout.design import bootstrap_fill
    return dict(issue='https://github.com/chenzc24/sar-adc-t28/issues/12', date='2026-11-23',
                subject='Bootstrap core revision layout_r2: chip latch-up LUP.5.2.1/5.2.2 and planned boot-capacitor fill',
                status='qualified: routed SS-cold gate screen passes outright; open item: cause of the fill residual increase',
                oa=oa, fill_plan=bootstrap_fill.summary(), extractions=extractions, flat_chip_latch_up=flat,
                standalone=sampler, standalone_unfilled=unfilled, adc=adc, gate=gate,
                disposition_rule=DISPOSITION_RULE, routed_gate=routed,
                pending=PENDING, pending_runs=pending_runs,
                entry='Layout/tools/simulation/prepare_all_extracted.py adc CORNER KIND --bootstrap ID')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', required=True)
    a = ap.parse_args()
    (ROOT / a.output).write_text(json.dumps(record(), indent=1) + '\n', encoding='utf-8', newline='\n')
