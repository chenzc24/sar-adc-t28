"""Rail charge analyzer and Stage 1 budget model checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/saradc/measure'))
import rail_charge
from Layout.tools.analysis import rail_budget


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
        # Two pads per rail to ground, seen in series around the VREFP-VREFN loop.
        self.assertAlmostEqual(n['cpad'], s['pads_per_rail'] * s['pad_f'] / 2)
        self.assertAlmostEqual(n['cpad'], .5e-12)
        self.assertAlmostEqual(n['ron'], 2 * (15. + s['route_ohm']), places=2)
        self.assertAlmostEqual(n['l2'], 2 * (s['pin_h'] + s['route_h']))

    def test_pad_bulk_lowers_supply_droop(self):
        bare = rail_budget.supply_check(.6e-12, .3e-12, 10e-12, 6.)
        bulk = rail_budget.supply_check(.6e-12, .3e-12, 10e-12, 6., bulk=True)
        self.assertLess(bulk['droop_v'], bare['droop_v'])
        self.assertLess(bulk['pin_peak_a'], bare['pin_peak_a'])

    def test_ideal_charge_is_positive_and_bounded(self):
        total = [sum(e['charge_c'] for e in rail_budget.ideal_events(c)) for c in range(256)]
        self.assertTrue(all(q > 0 for q in total))
        # No conversion can draw more than charging the whole 2 x 1.025 pF array by the full span twice.
        self.assertLess(max(total), 2 * 2 * 256 * rail_budget.CU * rail_budget.VR)


if __name__ == '__main__':
    unittest.main()
