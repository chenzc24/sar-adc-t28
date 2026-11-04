import json
import unittest

import prepare_power_on as p
import review_power_on as r


class PowerOnDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = p.payloads()
        cls.mapping = json.loads(cls.outputs['common/mapping.json'])
        cls.control = cls.outputs['dc_core/test.scs'].decode()
        cls.ramp = cls.outputs['ramp_core/test.scs'].decode()

    def test_pair_only_changes_core_supply(self):
        changes = [(a, b) for a, b in zip(self.control.splitlines(), self.ramp.splitlines()) if a != b]
        self.assertEqual(len(self.control.splitlines()), len(self.ramp.splitlines()))
        self.assertEqual(changes, [('VVDD (VDD! 0) vsource dc=SUP type=dc',
            'VVDD (VDD! 0) vsource type=pwl wave=[0n 0 31.1n 0 41.1n SUP]')])

    def test_formal_clock_and_steady_sources_unchanged(self):
        original = (p.HERE / 'cold_controls/longcold/test.scs').read_text()
        get = lambda text, label: next(line for line in text.splitlines() if line.startswith(label + ' '))
        for label in ['VSAMPLE', 'VCMP_RESET', 'XF', 'RINP', 'RINN', 'RREFP', 'RREFN', 'CREFP', 'CREFN']:
            self.assertEqual(get(original, label), get(self.ramp, label))
        for label in ['VVINP', 'VVINN']:
            self.assertEqual(get(original, label).split('100.2n', 1)[1],
                             get(self.ramp, label).split('100.2n', 1)[1])
        self.assertIn('parameters SUP=0.81', self.ramp)
        self.assertIn('temp=-40', self.ramp)
        self.assertNotIn('nodeset', self.ramp)
        self.assertNotIn('skipdc', self.ramp)
        self.assertFalse(any(line.startswith(('ic ', 'initial ')) for line in self.ramp.splitlines()))

    def test_shared_ramps_and_metadata_limits(self):
        m = json.loads(self.outputs['manifest.json'])
        self.assertFalse(m['POR_implemented'])
        self.assertFalse(m['native_compile_or_simulation_done'])
        self.assertEqual(m['supply_operating_contract_v'], [.81, .99])
        self.assertIsNone(m['startup_error_limit_v'])
        self.assertIsNone(m['first_valid_sample_latency_requirement_ns'])
        self.assertEqual(self.mapping['stop_s'], 260e-9)
        self.assertEqual(self.mapping['energy_bins_s'], [[0, 100e-9], [100e-9, 200e-9]])
        self.assertFalse(self.mapping['native_energy_after200ns_available'])
        self.assertLess(m['compact_binary_upper_bound_bytes'] + m['collection_reserve_bytes'], 40 * 1024**2)
        selected = set((p.HERE / 'stream_package/common/selected.txt').read_text().splitlines())
        self.assertTrue(set(self.mapping['branch_signal_map'].values()) <= selected)

    def test_ambiguous_label_rejected_and_reproducible(self):
        for text in ['x\n', 'VVDD x\nVVDD y\n']:
            with self.assertRaises(AssertionError):
                p.replace_line(text, 'VVDD', 'VVDD new')
        self.assertEqual(self.outputs, p.payloads())

    def measurements(self, events=None, moving_source=False):
        n = self.mapping['signal_map']
        if events is None:
            events = [(103.32e-9, 1), (141.16e-9, 0), (203.32e-9, 1), (241.16e-9, 0)]
        def at(name, t):
            source_p = .045 if t < 200e-9 else .45
            source_n = .855 if t < 200e-9 else .45
            error = .001 if t < 141.16e-9 else .0013
            if name == n['top_p']:
                return source_p + error / 2
            if name == n['top_n']:
                return source_n - error / 2
            if name == n['vin_p_source']:
                return source_p + (.020 if moving_source and t >= 141.2e-9 else 0)
            if name == n['vin_n_source']:
                return source_n
            if name in [n['vdd'], n['boot_p_btop'], n['boot_n_btop']]:
                return .81
            return 0
        return r.summarize({n['seq_sample']: events}, at, self.mapping)

    def test_two_distinct_frames_and_raw_increments(self):
        result = self.measurements()
        first, second = result['frames']
        self.assertTrue(first['sampling_window_evaluable'])
        self.assertTrue(second['sampling_window_evaluable'])
        self.assertAlmostEqual(first['preclose_error_mv'], 1)
        self.assertAlmostEqual(first['held_error_at_nominal_edge_mv'], 1.3)
        self.assertAlmostEqual(first['net_turnoff_voltage_change_mv'], .3)
        self.assertAlmostEqual(first['actual_acquisition_ns'], 37.84)
        self.assertAlmostEqual(second['held_time_ns'], 241.8)
        self.assertIsNone(result['startup_accuracy_pass'])
        self.assertFalse(result['POR_qualified'])

    def test_missing_or_multiple_edges_never_imply_valid_acquisition(self):
        for events in [[(141.16e-9, 0)],
                       [(103e-9, 1), (104e-9, 1), (141.16e-9, 0)],
                       [(103e-9, 1), (140e-9, 0), (141e-9, 0)]]:
            first = self.measurements(events)['frames'][0]
            self.assertFalse(first['sampling_window_evaluable'])
            self.assertIsNone(first['actual_acquisition_ns'])
            self.assertIsNone(first['held_error_at_nominal_edge_mv'])

    def test_late_close_keeps_fixed_held_time_and_source_motion_visible(self):
        first = self.measurements([(103e-9, 1), (142e-9, 0)])['frames'][0]
        self.assertFalse(first['sampling_window_evaluable'])
        self.assertEqual(first['held_time_ns'], 141.8)
        self.assertIsNone(first['net_turnoff_voltage_change_mv'])
        first = self.measurements(moving_source=True)['frames'][0]
        self.assertAlmostEqual(first['source_endpoint_motion_mv'], 20)
        self.assertAlmostEqual(first['held_error_at_nominal_edge_mv'], 1.3)
        self.assertAlmostEqual(first['raw_held_vs_current_source_mv'], -18.7)
        self.assertFalse(first['pure_channel_injection_measured'])


if __name__ == '__main__':
    unittest.main()
