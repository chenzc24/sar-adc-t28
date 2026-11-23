"""Stage 1 rail budget on the drawn chip: the checks the chip rail recheck (#43) leaves out.

Layout/tools/analysis/chip_rail_recheck.py reruns the per-branch and shared-bus supply droop with the drawn pad
decoupling of sar8_adc_chip/layout_full_fill5_r3. This adds, with the same inputs (chip_rail_recheck.drawn_bulk,
the Stage 4b in-core values) and the same models and corners (#27):
- each feed loop, pad decap to block decap and from the pad, against the 6 ohm limit;
- the analog droop against pad bulk, at the drawn feed and at the 6 ohm limit;
- the coupled ring without the shared bus, the cross-branch coupling, and the reference error the bus couples in
  through the reference pads;
- the reference loop with the drawn network, nominal and over the tolerance box, which has no pad-decap term.
rail_budget.main writes the result into Layout/results/rail_budget.json (drawn_chip).
"""
import json

from Layout.project import ROOT
from Layout.tools.analysis import rail_budget as rb
from Layout.tools.analysis import ring_supply as rs
from Layout.tools.analysis.chip_rail_recheck import BRANCH, drawn_bulk
from Layout.tools.analysis.toplevel_full_rail import BRANCHES

STAGE6_PAD_BULK_F = 85.1e-12          # analog pad bulk of the conservative Stage 6 decks
PLAN_PAD_BULK_F = 114.2e-12           # analog pad bulk planned on the 9 x 9 ring


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def inputs():
    stage4b = read('Layout/results/toplevel_route_full.json')['rail_budget']
    return dict(drawn=drawn_bulk(read('Layout/results/chip_objects.json')), stage4b=stage4b)


def charge(name, k=rb.CORNER_CHARGE):
    b = BRANCHES[name]
    return (b['event_c'] * k, b['repeat_c'] * k), (.2e-9 if b['event_c'] < .1e-12 else .5e-9)


def feeds(inp):
    out = {}
    for name in BRANCH:
        d, s4 = inp['drawn'][name], inp['stage4b']['supply']['branches'][name]
        rows = [dict(in_core_loop_ohm=loop, from_pad_decap_ohm=d['bulk_to_pin_ohm'] + loop,
                     from_pad_ohm=d['pad_to_bulk_ohm'] + d['bulk_to_pin_ohm'] + loop)
                for loop in s4['in_core_loop_ohm_125c']]
        out[name] = dict(rows=rows, core_alone_droop_v=s4['core_alone_droop_V'],
                         pass_=all(r['from_pad_decap_ohm'] <= rb.PAD_BULK['max_feed_ohm'] for r in rows))
    return out


def analog_sweep(inp):
    """Analog droop against pad bulk with the drawn ESR, at the drawn feed and at the 6 ohm limit."""
    q, pulse = charge('analog')
    d, s4 = inp['drawn']['analog'], inp['stage4b']['supply']['branches']['analog']
    feed = d['bulk_to_pin_ohm'] + max(s4['in_core_loop_ohm_125c'])
    out = dict(no_pad_bulk=dict(bulk_f=0., drawn_feed_v=s4['core_alone_droop_V']))
    for label, cap in (('stage6_deck', STAGE6_PAD_BULK_F), ('drawn', d['bulk_f']),
                       ('stage1_recommendation', rb.PAD_BULK['cap_f']), ('plan', PLAN_PAD_BULK_F)):
        out[label] = dict(bulk_f=cap)
        for key, ohm in (('drawn_feed_v', feed), ('feed_limit_v', rb.PAD_BULK['max_feed_ohm'])):
            out[label][key] = rb.supply_check(*q, s4['cap_F'], ohm, pulse=pulse, bulk=True, bulk_f=cap,
                                              bulk_esr_ohm_per_rail=d['esr_ohm_per_rail'])['droop_v']
    return out


def coupled(inp):
    """Coupled ring with and without the shared bus (125 C rcworst), largest in-core loop estimate."""
    updates, decisions = rb.schedule(*rb.CORNERS['ffc'])
    branches = inp['stage4b']['supply']['branches']
    charges = {n: charge(n)[0] for n in BRANCH}

    def events(sources):
        return {n: [(u, q, .5e-9) for u, q in zip(updates, [charges[n][0]] + [charges[n][1]] * 7 + [charges[n][0]])]
                for n in sources}

    def span_error(ckt, t, v):
        span = ckt.voltage(v, 'trunk_p') - ckt.voltage(v, 'trunk_n')
        return max(abs(d) * (128 - 2 ** (6 - j)) / .9 for j, d in enumerate(rs.at(t, span, decisions)))

    ref = inp['stage4b']['reference']
    system = dict(source_ohm=1., board_bypass_f=100e-9, board_esr_ohm=.01, board_esl_h=.5e-9, pin_h=2e-9, pin_ohm=.2,
                  series_ohm=ref['series_ohm'], span_cap_f=ref['cref_F'])
    core_feed = {n: max(branches[n]['in_core_loop_ohm_125c']) for n in BRANCH}
    kw = dict(bus_temp_c=125., core_feed_ohm=core_feed, system=system, drawn=inp['drawn'],
              blocks={n: branches[n]['cap_F'] for n in BRANCH})
    out = {}
    for case, shared in (('per_branch_125c_rcworst', False), ('shared_bus_125c_rcworst', True)):
        ckt, _ = rs.chip(shared_bus=shared, **kw)
        t, v = ckt.run(events(BRANCH))
        row = dict(core_feed_ohm=core_feed, droop_all_firing_v={n: rs.droop(ckt, t, v, n) for n in BRANCH})
        if shared:
            row['reference_error_lsb_asymmetric_pads'] = span_error(ckt, t, v)
            for src in BRANCH:
                t, v = ckt.run(events([src]))
                row['from_' + src] = {n: float(abs(ckt.voltage(v, 'cvdd_' + n) - ckt.voltage(v, 'cvss_' + n)).max())
                                      for n in BRANCH if n != src}
        out[case] = row
    return out


def reference(inp, box=False, gamma=None):
    """The reference loop has no pad-decap term; rerun the drawn network to show it is unchanged."""
    g = gamma or read('Layout/results/rail_budget.json')['reference_model']['gamma_c_per_toggled_unit']
    ref = inp['stage4b']['reference']
    out = dict(cref_f=ref['cref_F'], series_ohm=ref['series_ohm'],
               stage4b={c: dict(nominal=v['nominal_decision_error_LSB'], box=v['box_decision_error_LSB'])
                        for c, v in ref['corners'].items()},
               nominal={c: rb.reference_check(rb.loop(ref['series_ohm'], ref['cref_F']), g, cmp_s, wr_s)['decision_error_lsb']
                        for c, (cmp_s, wr_s) in rb.CORNERS.items()})
    if box:
        from Layout.tools.analysis import toplevel_full_rail
        corners = toplevel_full_rail.reference(ref['cref_F'], ref['series_ohm'])['corners']
        out['box'] = {c: dict(decision_error_lsb=v['box']['decision_error_lsb'], span_droop_v=v['box']['box_max_span_droop_v'],
                              pin_peak_a=v['box']['box_max_pin_peak_a']) for c, v in corners.items()}
    return out


def check(box=False, gamma=None):
    inp = inputs()
    feed = feeds(inp)
    ring = coupled(inp)
    sweep = analog_sweep(inp)
    worst = max([f['core_alone_droop_v'] for f in feed.values()] +
                [x for c in ring.values() for x in c['droop_all_firing_v'].values()] +
                [sweep['drawn'][k] for k in ('drawn_feed_v', 'feed_limit_v')])
    return dict(
        record='Stage 1 rail budget on the drawn chip sar8_adc_chip/layout_full_fill5_r3; '
               'the droop with the drawn pad bulk is Layout/results/chip_rail_recheck.json (#43)',
        inputs=dict(drawn=inp['drawn'], in_core='Layout/results/toplevel_route_full.json rail_budget (Stage 4b)',
                    pad='Layout/results/chip_objects.json via chip_rail_recheck.drawn_bulk'),
        corner_charge_allowance=rb.CORNER_CHARGE, timing='FF-cold update schedule',
        supply_limit_v=.045, feed_limit_ohm=rb.PAD_BULK['max_feed_ohm'],
        feeds=feed, analog_pad_bulk_sweep=sweep, coupled_ring=ring, reference=reference(inp, box, gamma),
        verdict=dict(supply_droop_pass=worst <= .045, worst_droop_v=worst, feeds_pass=all(f['pass_'] for f in feed.values())),
        not_modelled='DVDD (output register) has no Stage 1 budget; its 52.4 pF pad decap is recorded only.')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--box', action='store_true', help='also rerun the drawn reference tolerance box (slow)')
    print(json.dumps(check(p.parse_args().box), indent=1, default=str))
