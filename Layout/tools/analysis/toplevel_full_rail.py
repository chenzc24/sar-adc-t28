"""Stage 1 rail budget rerun with the drawn values of layout_route_full (Stage 4b).

Reuses the models of rail_budget.py (reference loop, tolerance box, per-branch supply droop) and ring_supply.py
(coupled pad ring) with their inputs replaced:
- supply: the drawn decoupling per branch and the in-core feed loop (VDD pin-to-decap extracted plus the VSS
  estimate, 25 C) raised 25 % for 125 C rcworst; the comparator strips keep the Stage 1 30 ohm strap basis.
- reference: the drawn CREF and series resistance (RREF plus in-core routing), with the rail_budget tolerance box
  (series x0.8-1.2, CREF x0.75-1.25 around the drawn value, 0.5-1.5 nH per rail, the 9 x 9 route range) at every
  corner; optional extra CREF values for the sensitivity.
The calibration (charge per toggled unit) comes from Layout/results/rail_budget.json, since the measured runs it
was fitted to are not part of this checkout. Writes a JSON file for toplevel_full_record.py.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json

from Layout.project import ROOT
from Layout.tools.analysis import rail_budget as rb
from Layout.tools.analysis import ring_supply as rs

HOT = 1.25          # 125 C rcworst on the in-core metal
BRANCHES = dict(    # event and repeated charge as in rail_budget.main
    analog=dict(event_c=.454e-12, repeat_c=.025e-12, stage1_feed=12., ring='analog', groups=('DA_west', 'DA_slot', 'DA_east')),
    pair=dict(event_c=.48e-12, repeat_c=.25e-12, stage1_feed=12., ring='pair', groups=('DP_S', 'DP_E', 'DP_SE', 'DP_C')),
    sar=dict(event_c=.31e-12, repeat_c=.31e-12, stage1_feed=5., ring='sar', groups=('DS_S', 'DS_N')),
    comparator_local=dict(event_c=.025e-12, repeat_c=.025e-12, stage1_feed=30., ring=None, groups=('DC_W', 'DC_E')))


def gamma():
    return json.loads((ROOT / 'Layout/results/rail_budget.json').read_text())['reference_model']['gamma_c_per_toggled_unit']


def reference(cref, series):
    g, out = gamma(), {}
    for corner, (cmp_s, wr_s) in rb.CORNERS.items():
        nominal = rb.reference_check(rb.loop(series, cref), g, cmp_s, wr_s)
        worst, peaks = dict(decision_error_lsb=0.), dict(span_droop_v=0., pin_peak_a=0.)
        for fr, fc, lh, ro in itertools.product(rb.TOLERANCE['series'] + (1.,), rb.TOLERANCE['cap'] + (1.,),
                                                rb.TOLERANCE['pin_h'] + (rb.SYSTEM['pin_h'],),
                                                rb.TOLERANCE['route_ohm'] + (rb.SYSTEM['route_ohm'],)):
            r = rb.reference_check(rb.loop(series * fr, cref * fc, pin_h=lh, route_ohm=ro), g, cmp_s, wr_s,
                                   codes=range(0, 256, 5))
            peaks = {k: max(v, r[k]) for k, v in peaks.items()}
            if r['decision_error_lsb'] > worst['decision_error_lsb']:
                worst = dict(r, series_ohm=series * fr, span_cap_f=cref * fc, pin_h=lh, route_ohm=ro)
        out[corner] = dict(nominal=nominal, box=dict(worst, box_max_span_droop_v=peaks['span_droop_v'],
                                                     box_max_pin_peak_a=peaks['pin_peak_a']))
    return dict(cref_f=cref, series_ohm=series, gamma=g, corners=out)


def supply(caps, loops):
    k, ring = rb.CORNER_CHARGE, rs.load_ring()
    table = rs.feed_table(ring)['rows']
    out = {}
    for name, b in BRANCHES.items():
        pulse = .2e-9 if b['event_c'] < .1e-12 else .5e-9
        q = (b['event_c'] * k, b['repeat_c'] * k)
        cap = caps[name]
        row = dict(cap_f=cap, in_core_loop_ohm_25c=loops[name])
        row['core_alone'] = [dict(feed_ohm=r * HOT, **rb.supply_check(*q, cap, r * HOT, pulse=pulse)) for r in loops[name]]
        row['core_alone_stage1_feed'] = dict(feed_ohm=b['stage1_feed'], **rb.supply_check(*q, cap, b['stage1_feed'], pulse=pulse))
        if b['ring']:
            bulk = ring['supply_plan']['adc_branches'][b['ring']]['pad_decap_planning_pF'] * 1e-12
            ring_r = table[b['ring']]['bulk_to_pin_ohm']['m8_125c_rcworst']
            row['with_pad_bulk'] = [dict(feed_ohm=ring_r + r * HOT, **rb.supply_check(*q, cap, ring_r + r * HOT, pulse=pulse,
                                                                                     bulk=True, bulk_f=bulk))
                                    for r in loops[name]]
        out[name] = row
    # Coupled ring, shared bus at 125 C rcworst, all branches firing on the same FF-cold updates.
    updates, _ = rb.schedule(*rb.CORNERS['ffc'])
    names = ('analog', 'pair', 'sar')
    charges = {BRANCHES[n]['ring']: (BRANCHES[n]['event_c'] * k, BRANCHES[n]['repeat_c'] * k) for n in names}
    events = {n: [(u, qq, .5e-9) for u, qq in zip(updates, [c[0]] + [c[1]] * 7 + [c[0]])] for n, c in charges.items()}
    coupled = []
    for idx in (0, -1):
        core = {BRANCHES[n]['ring']: loops[n][idx] * HOT for n in names}
        ckt, _ = rs.chip(shared_bus=True, bus_temp_c=125., core_feed_ohm=core, ring=ring,
                         blocks={BRANCHES[n]['ring']: caps[n] for n in names})
        t, v = ckt.run(events)
        coupled.append(dict(core_feed_ohm=core, droop_all_firing_v={n: rs.droop(ckt, t, v, n) for n in charges}))
    out['coupled_shared_bus_125c_rcworst'] = coupled
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--content', required=True, help='content.json of the build (array summary)')
    ap.add_argument('--series-ohm', type=float, required=True, help='drawn RREF plus in-core routing, per rail')
    ap.add_argument('--loop', nargs='+', required=True, help='branch=ohm[,ohm] in-core VDD+VSS loop at 25 C')
    ap.add_argument('--sweep-pf', type=float, nargs='*', default=[], help='extra CREF values for the sensitivity')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    summary = json.loads((ROOT / a.content).read_bytes())['summary']
    area = lambda names: sum(summary[n]['gate_um2'] for n in names if n in summary)
    caps = {n: round(area(b['groups']) * 19e-15, 15) for n, b in BRANCHES.items()}
    cref = round(area(('DR_W', 'DR_C', 'DR_SE')) * 19e-15, 15)
    loops = {k: [float(x) for x in v.split(',')] for k, v in (s.split('=') for s in a.loop)}
    loops['comparator_local'] = [30. / HOT]
    with ProcessPoolExecutor() as pool:
        jobs = {pf: pool.submit(reference, pf * 1e-12, a.series_ohm) for pf in a.sweep_pf}
        drawn = pool.submit(reference, cref, a.series_ohm)
        result = dict(supply=supply(caps, loops), reference=drawn.result())
        sweep = {}
        for pf, job in jobs.items():
            r = job.result()['corners']
            sweep[f'{pf:g}pF'] = dict(box=round(max(c['box']['decision_error_lsb'] for c in r.values()), 4),
                                      droop=round(max(c['box']['box_max_span_droop_v'] for c in r.values()), 4),
                                      pin=round(max(c['box']['box_max_pin_peak_a'] for c in r.values()), 5))
        result['cref_sweep'] = sweep
    (ROOT / a.out).write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(dict(cref_pf=cref * 1e12, reference={k: round(v['box']['decision_error_lsb'], 4)
                                                         for k, v in result['reference']['corners'].items()},
                          sweep=sweep), indent=1))


if __name__ == '__main__':
    main()
