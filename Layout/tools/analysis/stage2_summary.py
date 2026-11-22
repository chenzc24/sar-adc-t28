"""Reduce collected Stage 2 runs (issue #12) to the record under results/integration.

Reads only digest-verified collected analyzer results. Each frame keeps its measured code, gain-corrected
target, acquisition residual at sample close, plate settling at every decision, event counts and read margin;
each run keeps the per-bit timing that sets the route budgets.
  python -m Layout.tools.analysis.stage2_summary RUN_ID [RUN_ID ...] --output results/integration/NAME.json
"""
import argparse
import hashlib
import json

from Layout.project import ROOT

RUNS = ROOT / 'work/output/managed_execution/runs'
# Stage 2 column of issue #12.
CLOSE_LIMIT_LSB = .15
SETTLING_LIMIT_LSB = .15
SSC_MARGIN_NS = 5.


def collected(run_id):
    root = RUNS / run_id
    data = (root / 'collected/derived/result.json').read_bytes()
    receipt = json.loads((root / 'collected/collection_receipt.json').read_bytes())
    if not any(f['name'] == 'derived/result.json' and f['sha256'] == hashlib.sha256(data).hexdigest()
               for f in receipt['files']):
        raise ValueError('Collected result does not match its receipt: ' + run_id)
    recipe = json.loads((root / 'recipe.json').read_bytes())
    recipe['recipe_hash'] = json.loads((root / 'registration.json').read_bytes())['recipe_hash']
    return json.loads(data), recipe, hashlib.sha256(data).hexdigest()


def frame_row(f):
    bits, writes = f['bits'], f['writes']
    close = f['track'][1]['close_error_lsb'] if len(f['track']) == 2 else None
    bound = [b['bottom']['weighted_bound_lsb'] if b['bottom'] else None for b in bits]
    return dict(frame=f['frame'], warmup=f['warmup'], input_code=f['input_code_coordinate'], code=f['code90'],
                code98=f['code98'], target=f['gain_expected'],
                code_error=None if f['code90'] is None else f['code90'] - f['gain_expected'],
                compares=len(bits), updates=len(writes), close_error_lsb=close,
                max_abs_signed_settling_lsb=f['max_abs_signed_settling_lsb'],
                max_weighted_bound_lsb=max(x for x in bound if x is not None) if any(x is not None for x in bound) else None,
                read_margin_ns=f['margin_ns'], first_compare_gate_overdrive_v=bits[0]['first_compare']['gate_overdrive_v']
                if bits else None,
                # Per decision: compare edge, window since the previous update, signed settling, comparator+SAR latency.
                decisions=[dict(bit=b['bit'], cmp_ns=b['cmp_ns'], window_ns=b['window_ns'], signed_lsb=b['signed_lsb'],
                                weighted_bound_lsb=bound[j], top_diff_mv=b['top_diff_v'] * 1e3,
                                compare_to_update_ns=writes[j]['ns'] - b['cmp_ns'] if j < len(writes) else None)
                           for j, b in enumerate(bits)],
                passed=f['pass'], digital_pass=f['digital_pass'], analog_code_pass=f['analog_code_pass'],
                settling_pass=f['settling_pass'], track_pass=f['track_pass'], control_pass=f['control_pass'],
                handoff_pass=f['handoff']['passed'], first_compare_pass=f['first_compare_pass'])


def summarize(run_id):
    result, recipe, digest = collected(run_id)
    ctx = recipe['test_conditions']
    row = dict(run_id=run_id, recipe_sha256=recipe.get('recipe_hash'), result_sha256=digest, corner=ctx['corner'],
               kind=ctx['kind'], condition=dict(mos=ctx['mos'], vdd_v=ctx['vdd_v'], temperature_c=ctx['temperature_c']),
               cell_lpe=ctx['cell_lpe'], pex_modules=ctx['pex_modules'], k=ctx['independent_cdac_gain'],
               weights_source=ctx['weights_source'], xref=ctx.get('xref_physical_evidence'),
               comparator=ctx.get('comparator_pex', {}).get('physical_evidence'),
               sar_macro=ctx.get('sar_macro', {}).get('physical_id'), bootstrap=ctx.get('bootstrap_physical_evidence'),
               route_check=ctx.get('route_check') or ctx.get('route_budget_check'))
    if ctx['kind'] == 'restart':
        row.update(passed=result['pass_restart'], comparisons=result['comparisons'], updates=result['writes'],
                   public_read_codes=result['public_read_codes'], expected_reads=ctx.get('restart_plan'),
                   no_new_compare_or_write_during_track=result['no_new_compare_or_write_during_track'],
                   stable=result['stable'])
        return row
    frames = [frame_row(f) for f in result['frames']]
    scored = [f for f in frames if not f['warmup']]
    close = [abs(f['close_error_lsb']) for f in scored if f['close_error_lsb'] is not None]
    signed = [f['max_abs_signed_settling_lsb'] for f in scored if f['max_abs_signed_settling_lsb'] is not None]
    bound = [f['max_weighted_bound_lsb'] for f in scored if f['max_weighted_bound_lsb'] is not None]
    by_bit = {}
    for f in scored:
        for d in f['decisions']:
            b = by_bit.setdefault(d['bit'], dict(min_window_ns=None, max_compare_to_update_ns=None, max_abs_signed_lsb=0.))
            if d['window_ns'] is not None:
                b['min_window_ns'] = d['window_ns'] if b['min_window_ns'] is None else min(b['min_window_ns'], d['window_ns'])
            if d['compare_to_update_ns'] is not None:
                b['max_compare_to_update_ns'] = max(b['max_compare_to_update_ns'] or 0., d['compare_to_update_ns'])
            b['max_abs_signed_lsb'] = max(b['max_abs_signed_lsb'], abs(d['signed_lsb']))
    row.update(
        analyzer_all_pass=result['all_pass'], frames=frames,
        codes_within_1=all(f['code_error'] is not None and abs(f['code_error']) <= 1 for f in scored),
        events_8_8=all(f['compares'] == f['updates'] == 8 for f in scored),
        register_writes=result.get('ccs', {}).get('observation_counts', {}).get('writes'),
        register_pins=len(result.get('register_pins', [])), pin_pass=result.get('pin_pass'),
        setup_hold_slack_ps={k: v.get('slack_ps') for k, v in result.get('ccs', {}).get('minimum_slack', {}).items()},
        max_abs_close_error_lsb=max(close) if close else None, close_pass=bool(close) and max(close) <= CLOSE_LIMIT_LSB,
        max_abs_signed_settling_lsb=max(signed) if signed else None,
        max_weighted_bound_lsb=max(bound) if bound else None,
        settling_pass=bool(signed) and max(signed) <= SETTLING_LIMIT_LSB and max(bound) <= SETTLING_LIMIT_LSB,
        min_read_margin_ns=result['min_margin_ns'],
        margin_pass=result['min_margin_ns'] is not None and (ctx['corner'] != 'ssc' or result['min_margin_ns'] >= SSC_MARGIN_NS),
        max_first_compare_gate_overdrive_v=result['max_first_compare_gate_overdrive_v'],
        clock_high_at_opening=result['clock_high_at_opening'], pulse_ps=result['pulse_ps'],
        close_to_first_commit_min_ns=result['close_to_first_commit_min_ns'],
        last_commit_to_next_open_min_ns=result['last_commit_to_next_open_min_ns'],
        per_bit=dict(sorted(by_bit.items(), reverse=True)), warnings=result['warnings'])
    split_id = run_id + '-split'
    if (RUNS / split_id / 'collected/derived/result.json').exists():
        # measure_reference_split.py: the static reference-pin offset is reported apart from plate settling.
        split, split_recipe, split_digest = collected(split_id)
        if split['run_id'] != run_id:
            raise ValueError('Split result belongs to another run: ' + split_id)
        row['reference_split'] = dict(
            run_id=split_id, recipe_sha256=split_recipe['recipe_hash'], result_sha256=split_digest,
            quiet_ns=split['quiet_ns'], quiet_pin_offset_mv=dict(vrefn=max(split['quiet_pin_offset_mv']['vrefn'], key=abs),
                                                                 vrefp=max(split['quiet_pin_offset_mv']['vrefp'], key=abs)),
            max_abs_lsb=split['max_abs'],
            plate_settling_pass=split['max_abs']['pin_lsb'] <= SETTLING_LIMIT_LSB,
            excluding_static_pass=split['max_abs']['excluding_static_lsb'] <= SETTLING_LIMIT_LSB)
        row['settling_pass_excluding_static_offset'] = bool(
            row['reference_split']['excluding_static_pass'] and row['max_weighted_bound_lsb'] <= SETTLING_LIMIT_LSB)
    return row


ROUTED_MARGIN_NS = 1.
ROUTED_SETTLING_LIMIT_LSB = .25
# Stage 2 runs with ideal top-level wiring, per corner (Layout/tools/simulation/prepare_all_extracted.py).
STAGE2 = {
    'tt': ['sar8-allx-tt-verify-c', 'sar8-allx-tt-extreme-a', 'sar8-allx-tt-carry-a', 'sar8-allx-tt-restart-a'],
    'ssc': ['sar8-allx-ssc-verify-a', 'sar8-allx-ssc-extreme-b', 'sar8-allx-ssc-carry-a', 'sar8-allx-ssc-restart-a'],
    'ffh': ['sar8-allx-ffh-verify-a', 'sar8-allx-ffh-extreme-b', 'sar8-allx-ffh-carry-a', 'sar8-allx-ffh-restart-a'],
}
GAIN = {'tt': 'xref-fill-tt-after-dense', 'ssc': 'xref-dense-ssc-gain-cw', 'ffh': 'xref-dense-ffh-gain-cb'}
# RC route checks and the Stage 2 run of the same corner and stimulus they are compared with.
ROUTE_CHECKS = [('sar8-allxr-ssc-verify-s1', 'sar8-allx-ssc-verify-a'),
                ('sar8-allxr-ssc-verify-a', 'sar8-allx-ssc-verify-a'),
                ('sar8-allxr-ffh-verify-a', 'sar8-allx-ffh-verify-a')]
# Ideal-delay checks: kept as diagnostics only.
IDEAL_DELAY_DIAGNOSTICS = ['sar8-allxb-ssc-verify-a', 'sar8-allxb-ffh-verify-a']
NOT_STARTED = {
    'sar8-allx-tt-verify-a': 'thu-wei admission blocked on cpu_load; replaced by sar8-allx-tt-verify-b',
    'sar8-allx-tt-verify-b': 'thu-sui admission blocked on disk_headroom; replaced by sar8-allx-tt-verify-c',
    'sar8-allx-ssc-extreme-a': 'thu-song user cgroup headroom below the 6 GiB reservation; replaced by -b (4 GiB)',
    'sar8-allx-ffh-extreme-a': 'thu-song user cgroup headroom below the 6 GiB reservation; replaced by -b (4 GiB)',
}


def gain(run_id):
    """Standalone XREF/CDAC weights of one extraction at one MOS corner (k, gain error, linearity, settling)."""
    result, recipe, digest = collected(run_id)
    m = result['post']['metrics']
    ctx = recipe['test_conditions']
    return dict(run_id=run_id, recipe_sha256=recipe['recipe_hash'], result_sha256=digest,
                physical_evidence=ctx['physical_evidence'].rsplit('/', 1)[-1], condition=ctx.get('condition'),
                k=result['gain_ratio'], gain_error=result['gain_error'], dnl_abs_max_lsb=result['dnl_abs_max'],
                inl_abs_max_lsb=result['inl_abs_max'], plateaus_stable=result['all_plateaus_stable'],
                weights_v=m['effective_weights_v'], settle_to_quarter_lsb_s=m['settle_to_quarter_lsb_s'][:8],
                reference_min_max_v=m['reference_min_max_v'])


def route_delays(run_id):
    """measure_route_delay.py result of a route check: worst one-way delay and edges per route."""
    routes_id = run_id + '-routes'
    if not (RUNS / routes_id / 'collected/derived/result.json').exists():
        return None
    result, recipe, digest = collected(routes_id)
    if result['run_id'] != run_id:
        raise ValueError('Route result belongs to another run: ' + routes_id)
    return dict(run_id=routes_id, recipe_sha256=recipe['recipe_hash'], result_sha256=digest,
                max_handshake_one_way_ps=result['max_handshake_one_way_ps'], max_code_bus_ps=result['max_code_bus_ps'],
                routes=[dict(name=r['name'], length_um=r['length_um'], r_ohm=r['r_ohm'], c_F=r['c_F'],
                             max_delay_ps=r['max_delay_ps'], edges=r['driver_edges'],
                             unpaired_driver_edges=r['unpaired_driver_edges'],
                             driver_transition_median_ps=(r['driver_transition'] or {}).get('median_ps'),
                             receiver_transition_median_ps=(r['receiver_transition'] or {}).get('median_ps'))
                        for r in result['routes']])


def latency_by_input(check, control):
    """Added compare-to-update time of a route check over its control, binned by |TOPP - TOPN| at the compare."""
    a, _, _ = collected(control)
    b, _, _ = collected(check)
    rows = []
    for fa, fb in zip(a['frames'], b['frames']):
        for j, (x, y) in enumerate(zip(fa['bits'], fb['bits'])):
            rows.append((abs(y['top_diff_v']) * 1e3,
                         (fb['writes'][j]['ns'] - y['cmp_ns']) - (fa['writes'][j]['ns'] - x['cmp_ns'])))
    bins = []
    for lo, hi in ((0, 5), (5, 60), (60, 300), (300, 1000)):
        sel = [d for v, d in rows if lo <= v < hi]
        if sel:
            bins.append(dict(top_diff_mv=[lo, hi], decisions=len(sel), mean_added_ns=sum(sel) / len(sel),
                             max_added_ns=max(sel)))
    return bins


def route_check_row(check, control):
    r, c = summarize(check), summarize(control)
    out = dict(run_id=check, control=control, corner=r['corner'], kind=r['kind'], route_check=r['route_check'],
               analyzer_all_pass=r['analyzer_all_pass'], codes_within_1=r['codes_within_1'], events_8_8=r['events_8_8'],
               pin_pass=r['pin_pass'], min_read_margin_ns=r['min_read_margin_ns'],
               control_min_read_margin_ns=c['min_read_margin_ns'],
               read_margin_cost_ns=c['min_read_margin_ns'] - r['min_read_margin_ns'],
               max_abs_close_error_lsb=r['max_abs_close_error_lsb'],
               control_max_abs_close_error_lsb=c['max_abs_close_error_lsb'],
               max_abs_signed_settling_lsb=r['max_abs_signed_settling_lsb'],
               control_max_abs_signed_settling_lsb=c['max_abs_signed_settling_lsb'],
               max_weighted_bound_lsb=r['max_weighted_bound_lsb'],
               max_first_compare_gate_overdrive_v=r['max_first_compare_gate_overdrive_v'],
               setup_hold_slack_ps=r['setup_hold_slack_ps'], added_latency_by_input=latency_by_input(check, control),
               delays=route_delays(check), frames=r['frames'],
               routed_limits_pass=bool(r['codes_within_1'] and r['events_8_8'] and r['pin_pass']
                                       and r['min_read_margin_ns'] > ROUTED_MARGIN_NS
                                       and r['max_abs_close_error_lsb'] <= ROUTED_SETTLING_LIMIT_LSB
                                       and r['max_abs_signed_settling_lsb'] <= ROUTED_SETTLING_LIMIT_LSB))
    for key in ('reference_split',):
        if key in r:
            out[key], out['control_' + key] = r[key], c.get(key)
    return out


def budgets(checks, diagnostics, gains, code_bus_limit_s=100e-12, gain_share=.008):
    """Route budgets from the measured route checks (issue #12 Stage 4).

    Handshake: the comparator outputs are the StrongARM latch nodes, so route capacitance on COMP_P/COMP_N slows
    regeneration; the wire delay itself is tens of ps. The budget is the verified SS-cold check with the most
    load that still leaves the routed-design margin, stated as both its measured one-way delay and its loads.
    CODE bus: at FF hot, the decision error rises with the CODE/PRESET delay; the slope comes from the RC check
    (measured delay, with the reference split) and the ideal-delay diagnostic (nominal rails only).
    TOP: gain_share of C_eff (specs/arch.json gain_error_allocation.top_level_top_wiring_and_device_layout), with
    C_eff from the fixed TOP load and gain error of the filled extraction; verified in every route check."""
    ssc = sorted([c for c in checks if c['corner'] == 'ssc'], key=lambda c: c['route_check']['scale'])
    passing = [c for c in ssc if c['routed_limits_pass']]
    chosen = passing[-1]
    rc = chosen['route_check']
    # Recipe test conditions pass through YAML, which can return exponent-only floats as strings.
    load = {r['name']: float(r['c_F']) for r in rc['routes']}
    cost_per_scale = [c['read_margin_cost_ns'] / float(c['route_check']['scale']) for c in ssc]
    slope = sum(cost_per_scale) / len(cost_per_scale)
    handshake = dict(
        limit_one_way_s=None if not chosen['delays'] else
        1e-12 * 5 * int(-(-chosen['delays']['max_handshake_one_way_ps'] // 5)),
        verified_run=chosen['run_id'], verified_scale=rc['scale'],
        load_limit_F=dict(COMP_P=load['COMP_P'], COMP_N=load['COMP_N'], CMP_CLK=load['CMP_CLK']),
        measured_one_way_ps=chosen['delays'] and chosen['delays']['max_handshake_one_way_ps'],
        ssc_read_margin_ns=dict(control=chosen['control_min_read_margin_ns'], routed=chosen['min_read_margin_ns'],
                                routed_limit=ROUTED_MARGIN_NS),
        margin_cost_ns_per_planned_length=slope,
        scale_at_routed_limit=(chosen['control_min_read_margin_ns'] - ROUTED_MARGIN_NS) / slope,
        checks=[dict(run_id=c['run_id'], scale=float(c['route_check']['scale']),
                     comp_out_load_F=float(next(r['c_F'] for r in c['route_check']['routes'] if r['name'] == 'COMP_P')),
                     margin_ns=c['min_read_margin_ns'], cost_ns=c['read_margin_cost_ns'],
                     routed_limits_pass=c['routed_limits_pass']) for c in ssc])
    ffh = [c for c in checks if c['corner'] == 'ffh'][0]
    split, base = ffh['reference_split']['max_abs_lsb'], ffh['control_reference_split']['max_abs_lsb']
    delay_ps = ffh['delays']['max_code_bus_ps']
    diag = [d for d in diagnostics if d['corner'] == 'ffh'][0]
    diag_ps = float(diag['route_check']['gate_s']) * 1e12
    slopes = dict(excluding_static_lsb_per_ps=(split['excluding_static_lsb'] - base['excluding_static_lsb']) / delay_ps,
                  nominal_lsb_per_ps=(split['nominal_lsb'] - base['nominal_lsb']) / delay_ps,
                  nominal_ideal_delay_lsb_per_ps=(diag['max_abs_signed_settling_lsb'] - base['nominal_lsb']) / diag_ps)
    limit_ps = code_bus_limit_s * 1e12
    code_bus = dict(
        limit_s=code_bus_limit_s, scope='One-way CODE0-7/PRESET route from the SAR macro pins to the XREF pins',
        ffh_control=dict(nominal_lsb=base['nominal_lsb'], excluding_static_lsb=base['excluding_static_lsb'],
                         static_lsb=base['static_lsb']),
        ffh_rc_check=dict(run_id=ffh['run_id'], measured_max_delay_ps=delay_ps, nominal_lsb=split['nominal_lsb'],
                          excluding_static_lsb=split['excluding_static_lsb']),
        ffh_ideal_delay_diagnostic=dict(run_id=diag['run_id'], delay_ps=diag_ps, nominal_lsb=diag['max_abs_signed_settling_lsb']),
        slopes=slopes,
        predicted_at_limit=dict(
            nominal_lsb=base['nominal_lsb'] + limit_ps * max(slopes['nominal_lsb_per_ps'], slopes['nominal_ideal_delay_lsb_per_ps']),
            excluding_static_lsb=base['excluding_static_lsb'] + limit_ps * slopes['excluding_static_lsb_per_ps'],
            routed_limit_lsb=ROUTED_SETTLING_LIMIT_LSB, stage2_limit_lsb=SETTLING_LIMIT_LSB))
    tt = gains['tt']
    fixed_F = 52.11476730310019e-15  # TOPP fixed load of se-xref-peripheral-dense (Layout/results/single_edge_xref_filled.json)
    c_eff = fixed_F / tt['gain_error']
    top = dict(limit_F=round(gain_share * c_eff * 1e17) / 1e17, gain_share=gain_share, c_eff_F=c_eff,
               c_eff_basis='fixed TOPP load 52.11 fF / TT gain error %.4f of %s' % (tt['gain_error'], tt['run_id']),
               verified=[dict(run_id=c['run_id'], top_F=float(c['route_check']['top_F']),
                              sampler_route_r_ohm=float(c['route_check']['top_sampler_r_ohm']), codes_within_1=c['codes_within_1'],
                              close_error_lsb=c['max_abs_close_error_lsb'],
                              control_close_error_lsb=c['control_max_abs_close_error_lsb']) for c in checks])
    return dict(sar_handshake_route_delay_s=handshake, reference_gate_route_delay_s=code_bus,
                comparator_input_route_capacitance_F=top)


def record():
    runs = {corner: [summarize(r) for r in ids] for corner, ids in STAGE2.items()}
    gains = {corner: gain(r) for corner, r in GAIN.items()}
    checks = [route_check_row(c, b) for c, b in ROUTE_CHECKS]
    diagnostics = []
    for rid in IDEAL_DELAY_DIAGNOSTICS:
        r = summarize(rid)
        diagnostics.append(dict(run_id=rid, corner=r['corner'], route_check=r['route_check'],
                                min_read_margin_ns=r['min_read_margin_ns'],
                                max_abs_signed_settling_lsb=r['max_abs_signed_settling_lsb'],
                                status='diagnostic only: the Verilog-A absdelay element draws no input current, so it '
                                       'removes each receiver load from its driver (comparator latch outputs, SAR clock '
                                       'driver, SAR CODE drivers)'))
    verdict = {}
    for corner, rows in runs.items():
        scored = [r for r in rows if r['kind'] != 'restart']
        restart = [r for r in rows if r['kind'] == 'restart']
        settling = all(r['settling_pass'] or r.get('settling_pass_excluding_static_offset') for r in scored)
        verdict[corner] = dict(
            codes_within_1=all(r['codes_within_1'] for r in scored), events_8_8=all(r['events_8_8'] for r in scored),
            register_pins=all(r['pin_pass'] for r in scored),
            max_abs_close_error_lsb=max(r['max_abs_close_error_lsb'] for r in scored),
            close_pass=all(r['close_pass'] for r in scored),
            max_abs_signed_settling_lsb=max(r['max_abs_signed_settling_lsb'] for r in scored),
            max_weighted_bound_lsb=max(r['max_weighted_bound_lsb'] for r in scored),
            max_excluding_static_lsb=max([r['reference_split']['max_abs_lsb']['excluding_static_lsb']
                                          for r in scored if 'reference_split' in r] or [None]),
            settling_pass=settling, static_offset_reported_separately=any('reference_split' in r for r in scored),
            min_read_margin_ns=min(r['min_read_margin_ns'] for r in scored),
            margin_pass=all(r['margin_pass'] for r in scored),
            max_first_compare_gate_overdrive_v=max(r['max_first_compare_gate_overdrive_v'] for r in scored),
            restart_pass=all(r['passed'] for r in restart))
        v = verdict[corner]
        v['all_pass'] = bool(v['codes_within_1'] and v['events_8_8'] and v['register_pins'] and v['close_pass']
                             and settling and v['margin_pass'] and v['restart_pass']
                             and v['max_first_compare_gate_overdrive_v'] <= .1)
    assembly = {}
    for corner, rows in runs.items():
        ctx = json.loads((RUNS / STAGE2[corner][0] / 'recipe.json').read_bytes())['test_conditions']
        assembly[corner] = dict(
            cell_lpe=ctx['cell_lpe'], xref=ctx['xref_physical_evidence'], xref_extracted_sha256=ctx['xref_extracted_sha256'],
            comparator=ctx['comparator_pex']['physical_evidence'],
            comparator_extracted_sha256=ctx['comparator_pex']['extracted_original_sha256']['extracted.scs'],
            sar_macro=ctx['sar_macro']['physical_id'], sar_macro_interconnect=ctx['sar_macro']['interconnect_rc'],
            sar_macro_extracted_sha256=ctx['sar_macro']['extracted_sha256'],
            sar_macro_structural_sha256=ctx['sar_macro']['structural_sha256'],
            bootstrap=ctx['bootstrap_physical_evidence'].rsplit('/', 1)[-1],
            bootstrap_extracted_sha256=ctx['bootstrap_extracted_original_sha256']['extracted.scs'],
            k=ctx['independent_cdac_gain'], weights_source=ctx['weights_source'])
    return dict(
        issue='https://github.com/chenzc24/sar-adc-t28/issues/12', stage='Stage 2: all-extracted closed-loop ADC, ideal top-level wiring',
        date='2026-11-22', entry='Layout/tools/simulation/prepare_all_extracted.py',
        limits=dict(codes='gain-corrected target +/-1 code, k from the standalone XREF/CDAC of the same extraction and MOS corner',
                    close_error_lsb=CLOSE_LIMIT_LSB, plate_settling_lsb=SETTLING_LIMIT_LSB, ssc_read_margin_ns=SSC_MARGIN_NS,
                    events='8 compares and 8 updates per frame; restart passes', bootstrap_gate_screen_v=.1,
                    routed_design=dict(read_margin_ns=ROUTED_MARGIN_NS, settling_lsb=ROUTED_SETTLING_LIMIT_LSB)),
        assembly=assembly, gains=gains, verdict=verdict, runs=runs, route_checks=checks,
        ideal_delay_diagnostics=diagnostics, not_started=NOT_STARTED,
        budgets=budgets(checks, diagnostics, gains))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_ids', nargs='*', help='Summarize these runs; without IDs, assemble the full Stage 2 record')
    ap.add_argument('--output')
    a = ap.parse_args()
    data = [summarize(r) for r in a.run_ids] if a.run_ids else record()
    text = json.dumps(data, indent=1) + '\n'
    if a.output:
        (ROOT / a.output).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / a.output).write_text(text, encoding='utf-8', newline='\n')
    else:
        print(text)
