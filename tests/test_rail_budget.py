"""Rail charge analyzer and Stage 1 budget model checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/saradc/measure'))
import rail_charge
from Layout.tools.analysis import rail_budget, ring_supply


def native(path, rows):
    lines = ['HEADER', 'TYPE', 'SWEEP', '"time" "sweep"', 'TRACE'] + ['"%s" "V"' % n for n in rows[0][1]] + ['VALUE']
    for t, values in rows:
        lines.append('"time" %.9e' % t)
        lines += ['"%s" %.9g' % kv for kv in values.items()]
    path.write_text('\n'.join(lines + ['END']) + '\n')


class RailCharge(unittest.TestCase):
    def test_frame_and_window_charge_of_constant_currents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src/inputs').mkdir(parents=True)
            (root / 'src/raw').mkdir()
            (root / 'run/inputs').mkdir(parents=True)
            (root / 'src/inputs/context.json').write_text(json.dumps(dict(
                run_id='src', frame_origin_s=0., period_s=100e-9, frames=2, expected_codes=[1, 2])))
            (root / 'run/inputs/rail_charge_context.json').write_text(json.dumps(dict(
                run_id='ana', source_run_id='src', reference_series_ohm=50., reference_bypass_f=4e-12,
                vrefp_v=.9, vrefn_v=0., first_steady_frame=1, windows_s=[1e-9])))
            rows = []
            for k in range(2001):
                t = k * .1e-9
                rows.append((t, {'VDD!': .9, 'SAMPLE': .9 if t % 100e-9 < 45e-9 else 0.,
                                 'VREFP': .89, 'VREFN': .001, 'VVDD:p': -1e-3}))
            native(root / 'src/raw/x.tran.tran', rows)
            rail_charge.measure(str(root / 'run'), str(root / 'src'), str(root / 'out'))
            frame = json.loads((root / 'out/result.json').read_text())['frames'][1]
        self.assertAlmostEqual(frame['charge_c']['vdd'], 100e-12, delta=1e-15)
        self.assertAlmostEqual(frame['die_charge_c']['vrefp'], 20e-12, delta=1e-15)
        self.assertAlmostEqual(frame['die_charge_c']['vrefn'], -2e-12, delta=1e-15)
        self.assertAlmostEqual(frame['sampling_charge_c']['vdd'], 45e-12, delta=.2e-12)
        self.assertAlmostEqual(frame['window_charge_c']['1e-09']['vrefp']['charge_c'], .2e-12, delta=1e-16)


class BudgetModel(unittest.TestCase):
    def test_trajectory_has_eight_commits_and_closing_preset(self):
        for code in (0, 6, 127, 128, 249, 255):
            words = rail_budget.trajectory(code)
            self.assertEqual(len(words), 9)
            self.assertEqual(words[7], code)
            self.assertEqual(words[8], rail_budget.PRESET)

    def test_full_reversal_toggles_every_unit_twice(self):
        # 0x7F reaches its final word through B7 clear and B6..B0 set, then PRESET flips all 255 units.
        self.assertEqual(sum(e['units'] for e in rail_budget.ideal_events(127)), 510)
        self.assertEqual(sum(e['units'] for e in rail_budget.ideal_events(128)), 254)

    def test_reference_loop_counts_both_pads_and_the_route(self):
        s = rail_budget.SYSTEM
        n = rail_budget.loop(15., 8e-12)
        # Two pads and the route capacitance per rail to ground, seen in series around the loop.
        self.assertAlmostEqual(n['cpad'], (s['pads_per_rail'] * s['pad_f'] + s['route_f']) / 2)
        self.assertGreater(s['route_f'], 0)
        self.assertAlmostEqual(n['ron'], 2 * (15. + s['route_ohm']), places=2)
        self.assertAlmostEqual(n['l2'], 2 * (s['pin_h'] + s['route_h']))

    def test_reference_route_resistance_follows_the_ring_lengths(self):
        ring = ring_supply.load_ring()
        length = ring['supply_plan']['reference_route_length_um']
        rail = ring_supply.reference_routes(ring)['rails']['VREFN']
        a, b = length['VREFN_a'], length['VREFN_b']
        # Two 4 um M8 routes in parallel at 0.022 ohm/sq.
        self.assertAlmostEqual(rail['ohm']['m8_25c'], .022 * (a / 4) * (b / 4) / ((a + b) / 4), places=6)
        lo, hi = rail_budget.TOLERANCE['route_ohm']
        self.assertLess(lo, rail_budget.SYSTEM['route_ohm'])
        self.assertLess(rail_budget.SYSTEM['route_ohm'], hi)

    def test_sheet_resistance_temperature_and_corner(self):
        self.assertAlmostEqual(ring_supply.rsh('M8'), .022)
        self.assertGreater(ring_supply.rsh('M8', 125, True), 1.3 * .022)
        self.assertLess(ring_supply.rsh('M9', -40), .005)

    def test_circuit_engine_reproduces_the_loop_model(self):
        k = rail_budget.CORNER_CHARGE
        updates, _ = rail_budget.schedule(2.14e-9, .83e-9)
        charges = [.48e-12 * k] + [.25e-12 * k] * 7 + [.48e-12 * k]
        c = ring_supply.Circuit()
        c.r('board', '0', 1.)
        c.l('board', 'byp', .5e-9, .01)
        c.c('byp', '0', 100e-9)
        c.l('board', 'pv', 2e-9, .2)
        c.l('0', 'ps', 2e-9, .2)
        c.c('pv', 'esr', 100e-12)
        c.r('esr', 'ps', 4.)
        c.l('pv', 'cv', 1e-13, 3.)
        c.l('ps', 'cs', 1e-13, 3.)
        c.c('cv', 'cs', 10.07e-12)
        c.load('cv', 'cs', 'pair')
        t, v = c.run({'pair': [(u, q, .5e-9) for u, q in zip(updates, charges)]})
        engine = -(c.voltage(v, 'cv') - c.voltage(v, 'cs')).min()
        loop = rail_budget.supply_check(.48e-12 * k, .25e-12 * k, 10.07e-12, 6., bulk=True, bulk_f=100e-12)['droop_v']
        self.assertAlmostEqual(engine, loop, delta=.02 * loop)

    def test_bus_runs_from_right_8_over_the_top_to_left_6(self):
        order = ['right_8', 'top_0', 'top_8', 'left_0', 'left_6']
        self.assertEqual(order, sorted(order, key=ring_supply.bus_position))
        self.assertEqual(ring_supply.bus_position('top_4') - ring_supply.bus_position('top_1'), 180.)

    def test_pad_bulk_lowers_supply_droop(self):
        bare = rail_budget.supply_check(.6e-12, .3e-12, 10e-12, 6.)
        bulk = rail_budget.supply_check(.6e-12, .3e-12, 10e-12, 6., bulk=True)
        self.assertLess(bulk['droop_v'], bare['droop_v'])
        self.assertLess(bulk['pin_peak_a'], bare['pin_peak_a'])

    def test_drawn_chip_feeds_add_the_in_core_loop(self):
        from Layout.tools.analysis import drawn_chip_rail
        inp = drawn_chip_rail.inputs()
        self.assertAlmostEqual(inp['drawn']['analog']['bulk_f'], 92.9e-12)
        feeds = drawn_chip_rail.feeds(inp)
        loop = inp['stage4b']['supply']['branches']['analog']['in_core_loop_ohm_125c'][0]
        row = feeds['analog']['rows'][0]
        self.assertAlmostEqual(row['from_pad_decap_ohm'], inp['drawn']['analog']['bulk_to_pin_ohm'] + loop)
        self.assertGreater(row['from_pad_ohm'], row['from_pad_decap_ohm'])

    def test_ideal_charge_is_positive_and_bounded(self):
        total = [sum(e['charge_c'] for e in rail_budget.ideal_events(c)) for c in range(256)]
        self.assertTrue(all(q > 0 for q in total))
        # No conversion can draw more than charging the whole 2 x 1.025 pF array by the full span twice.
        self.assertLess(max(total), 2 * 2 * 256 * rail_budget.CU * rail_budget.VR)


if __name__ == '__main__':
    unittest.main()
