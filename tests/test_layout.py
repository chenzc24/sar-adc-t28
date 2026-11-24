"""Boundary checks for the physical plan and migrated evidence resolver."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from Layout import planning, project
from Layout.tools.analysis.migration import canonical_netlist, compare_tt


class LayoutPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(project.ROOT/'design', self.root/'design')
        for name in ['design/manifest.json', 'design/floorplan.json', 'design/io_ring.json',
                     'specs/interfaces.json', 'specs/constraints.json']:
            dest = self.root/'Layout'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project.ROOT/'Layout'/name, dest)
        (self.root/'Layout/results').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def mutate(self, name, fn):
        p = self.root/'Layout'/name
        data = json.loads(p.read_text(encoding='utf-8')); fn(data)
        p.write_text(json.dumps(data), encoding='utf-8')

    def test_actual_plan_and_area_projection(self):
        result = planning.check(self.root)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['area']['core_allocation'], 13542)
        self.assertEqual(result["area"]["die_area"], 892*892)   # the re-tiled TSMC seal ring (io_ring.json seal_ring)
        self.assertEqual(result['io_ring'], {'pads': 36, 'routes': 34})
        planning.render(self.root)
        self.assertFalse(planning.check(self.root)['planning_projection_stale'])
        self.assertEqual(planning.check(self.root)['qualification_applicability'], 'unmeasured')

    def test_port_order_and_duplicate_placement_are_rejected(self):
        def reverse(data):
            data['masters']['sar8j_r1_cdac']['ports'].reverse()
        self.mutate('specs/interfaces.json', reverse)
        self.assertFalse(planning.check(self.root)['valid'])
        self.mutate('design/floorplan.json', lambda d: d['blocks'].append(copy.deepcopy(d['blocks'][0])))
        errors = planning.check(self.root)['errors']
        self.assertTrue(any('Overlapping' in e for e in errors))
        self.assertIn('Floorplan must allocate each drawn top instance exactly once', errors)

    def test_not_drawn_instances_stay_out_of_the_floorplan(self):
        not_drawn = json.loads((self.root/'Layout/specs/interfaces.json').read_text(encoding='utf-8'))['not_drawn_instances']
        self.assertEqual(sorted(not_drawn), ['CL_CMP_CLK', 'CL_COMP_N', 'CL_COMP_P'])
        self.mutate('design/floorplan.json', lambda d: d['blocks'][0]['instances'].append('CL_COMP_N'))
        self.assertIn('Floorplan must allocate each drawn top instance exactly once', planning.check(self.root)['errors'])
        self.mutate('specs/interfaces.json', lambda d: d['not_drawn_instances'].update(CL_UNKNOWN={}))
        self.assertIn('Not-drawn instances must be top instances', planning.check(self.root)['errors'])

    def test_planned_route_faults_are_rejected(self):
        p = self.root/'Layout/design/floorplan.json'; original = p.read_text(encoding='utf-8')
        self.assertEqual(planning.check(self.root)['routing']['matched_wire_um'], {'COMP_P': 57.045, 'COMP_N': 57.045})
        def onto_outp_track(d):
            for point in d['planned_paths']['OUTN']['points_um'][1:3]: point[1] = 73.8
        point = lambda name, i, axis, value: lambda d: d['planned_paths'][name]['points_um'][i].__setitem__(axis, value)
        cases = [(onto_outp_track, 'share a track'),
                 (lambda d: d['crossings'].pop(0), 'Undeclared crossing'),
                 (lambda d: d['over_block'].pop(), 'without a declaration'),
                 (point('TOPP_to_sampler', 2, 0, 59.0), 'Mirrored paths differ'),
                 (point('SEQ_SAMPLE_to_XBOOTP', -1, 1, 76.0), 'not anchored'),
                 (lambda d: d['planned_paths'].pop('OUTP_clk_balance'), 'Matched nets differ'),
                 (lambda d: d['planned_paths'].pop('D3'), 'Pin has no planned path: SAR.D3'),
                 (lambda d: d['planned_paths']['CMP_CLK'].__setitem__('manhattan_length_um', 50), 'Recorded length')]
        for change, message in cases:
            p.write_text(original, encoding='utf-8')
            self.mutate('design/floorplan.json', change)
            errors = planning.check(self.root)['errors']
            self.assertTrue(any(message in e for e in errors), (message, errors))

    def test_io_ring_faults_are_rejected(self):
        p = self.root/'Layout/design/io_ring.json'; original = p.read_text(encoding='utf-8')
        region = lambda d, name: next(g for g in d['reserved_regions'] if g['id'] == name)
        pad = lambda pos, key, value: lambda d: next(q for q in d['pads'] if q['position'] == pos).__setitem__(key, value)
        def shift(name, value, *points):
            def change(d):
                for i, axis in points: d['routes'][name]['points_um'][i][axis] = value
            return change
        cases = [(lambda d: region(d, 'dvdd_decap')['bbox'][1].__setitem__(1, 374.0), 'DVDD misses its decoupling dvdd_decap'),
                 (lambda d: region(d, 'adc_guard_ring').__setitem__('cross_min_layer', 'M7'), 'VINN crosses adc_guard_ring below M7'),
                 (lambda d: d['routes']['ADC_D0'].__setitem__('net', 'D0'), 'uses the bonded pad net D0'),
                 (shift('SAMPLE', 522.0, (2, 1), (3, 1)), 'SAMPLE (digital_signal) enters sar_feed_channel'),
                 (shift('VINP', 575.0, (1, 1), (2, 1)), 'not mirror images: VINN/VINP'),
                 (lambda d: d['routes']['SAMPLE'].__setitem__('layers', ['M7', 'M8']), 'SAMPLE crosses core_vss_ring on its layer M7'),
                 (pad('top_8', 'device', 'PVSS1AC'), 'Analog corner between top_8 and left_0 needs a bonded PVSS3AC'),
                 (pad('bottom_8', 'device', 'PVDD2DGZ'), 'Digital corner between bottom_8 and right_0 needs a bonded PVSS2DGZ'),
                 (pad('left_6', 'device', 'PVSS1AC'), 'Analog pad beside the power cut at left_6/left_7 must be PVDD3AC/PVSS3AC'),
                 (pad('left_5', 'device', 'PVDD1AC'), 'Analog domain ana needs at least 3 bonded PVDD3AC, has 2'),
                 (pad('top_7', 'device', 'PVSS3AC'), 'Analog domain ana needs at least 1 bonded PVSS2AC, has 0'),
                 (pad('bottom_3', 'device', 'PVDD2POC'), 'Digital domain dig needs one and only one PVDD2POC, has 2'),
                 (pad('right_6', 'device', 'PVDD2DGZ'), 'Digital domain dig needs at least 3 bonded PVDD1DGZ, has 2'),
                 (pad('top_7', 'name', 'ESD'), "Cells supplying the global VSS bus carry different names: ['ESD', 'VSS']"),
                 (pad('right_8', 'domain', 'dig'), 'Corner between right_8 and top_0 joins two domains'),
                 (lambda d: [q.__setitem__('device', 'PDDW16SDGZ') for q in d['pads'] if q.get('direction') == 'output'],
                  'Digital domain dig needs at least 4 bonded VDDPST cells for simultaneous switching (DF sum 3.843), has 2'),
                 (pad('right_3', 'device', 'PDDW08SDGZ'), 'Digital I/O cell PDDW08SDGZ has no driving factor in sso'),
                 (lambda d: d['routes'].pop('AVSS_guard'), 'Pad has 0 IO routes: left_0'),
                 (lambda d: region(d, 'pair_pad_decap')['bbox'][0].__setitem__(0, 112.0), 'VREFN_b enters pair_pad_decap')]
        for change, message in cases:
            p.write_text(original, encoding='utf-8')
            self.mutate('design/io_ring.json', change)
            errors = planning.check(self.root)['errors']
            self.assertTrue(any(message in e for e in errors), (message, errors))
        p.write_text(original, encoding='utf-8')
        self.mutate('design/floorplan.json', lambda d: d['pins_um']['ADC.VREFP@a'].__setitem__(1, 68.0))
        self.assertIn('ADC pin differs between floorplan and IO ring: ADC.VREFP@a', planning.check(self.root)['errors'])
        p.unlink()
        self.assertIn('Missing IO ring plan: Layout/design/io_ring.json', planning.check(self.root)['errors'])

    def test_io_ring_change_makes_the_projection_stale(self):
        planning.render(self.root)
        self.mutate('design/io_ring.json', lambda d: d.__setitem__('status', 'edited'))
        self.assertTrue(planning.check(self.root)['planning_projection_stale'])

    def test_new_render_cannot_refresh_old_qualification(self):
        planning.render(self.root)
        p = self.root/'Layout/results/current.json'; data = json.loads(p.read_text())
        data['signoff'] = True
        data['qualification_inputs_sha256'] = data['planning_inputs_sha256']
        p.write_text(json.dumps(data))
        self.mutate('design/floorplan.json', lambda d: d['blocks'][0]['origin'].__setitem__(0, d['blocks'][0]['origin'][0] + 1))
        self.assertTrue(planning.check(self.root)['planning_projection_stale'])
        planning.render(self.root)
        self.assertTrue(json.loads(p.read_text())['signoff'])
        self.assertEqual(planning.check(self.root)['qualification_applicability'], 'stale')

    def test_current_schematic_cannot_inherit_another_layout(self):
        manifest = self.root/'design/manifest.json'
        data = json.loads(manifest.read_text())
        data['design_id'] += '_new_schematic'
        manifest.write_text(json.dumps(data))
        result = planning.check(self.root)
        self.assertFalse(result['valid'])
        self.assertIn('Physical plan is bound to a different electrical design', result['errors'])

    def test_changed_electrical_source_is_not_rebound_silently(self):
        with (self.root/'design/top/adc_top.scs').open('a') as f:f.write('\n// changed\n')
        self.assertFalse(planning.check(self.root)['valid'])


class EvidenceResolutionTests(unittest.TestCase):
    def test_legacy_read_and_ambiguous_rejection(self):
        config = {'host':'test', 'remote_root':'/owned/layout', 'legacy_root':'/owned/legacy'}
        with patch.object(project, 'config', return_value=config), patch.object(project.subprocess, 'check_output') as run:
            run.return_value = b'/owned/legacy/evidence/case-a\n'
            self.assertEqual(project.evidence('case-a'), '/owned/legacy/evidence/case-a')
            run.return_value = b'/owned/legacy/evidence/case-a\n/owned/layout/evidence/case-a\n'
            with self.assertRaises(ValueError):project.evidence('case-a')
            with self.assertRaises(ValueError):project.evidence('../case-a')


class MigrationMeasurementTests(unittest.TestCase):
    def test_normalization_keeps_electrical_changes(self):
        first=b'// generated\r\nc1 (n 0) capacitor c=1f\r\n'
        self.assertEqual(canonical_netlist(first),canonical_netlist(b'\nc1 (n 0) capacitor c=1f\n'))
        self.assertNotEqual(canonical_netlist(first),canonical_netlist(b'c1 (n 0) capacitor c=2f\n'))

    def test_failure_preserved_but_changed_timing_fails_migration(self):
        frame={'frame':0,'expected_code':12,'code_90':0,'counts':{'write':8},'timing_pass':True,
               'sample_edges_pass':True,'observer_crosscheck':True,'event_order_pass':True,
               'issues':[{'reason':'center_code'}],'conversion_ns':28.0,
               'sample_close_events':[{'signal':'close','rising':False,'time_s':100e-9}]}
        before={'context':{'prelayout_design_id':'test','expected_codes':[12]},'frames':[frame]}
        after=copy.deepcopy(before)
        self.assertTrue(compare_tt(before,after,10e-12)['pass'])
        after['frames'][0]['conversion_ns']+=0.02
        self.assertFalse(compare_tt(before,after,10e-12)['pass'])

    def test_changed_edge_count_fails(self):
        frame={'frame':0,'expected_code':0,'code_90':0,'counts':{},'timing_pass':True,
               'sample_edges_pass':True,'observer_crosscheck':True,'event_order_pass':True,
               'issues':[],'conversion_ns':28.0,'sample_close_events':[]}
        before={'context':{'prelayout_design_id':'test','expected_codes':[0]},'frames':[frame]}
        after=copy.deepcopy(before)
        after['frames'][0]['sample_close_events']=[{'signal':'close','rising':False,'time_s':100e-9}]
        self.assertFalse(compare_tt(before,after,10e-12)['pass'])


if __name__ == '__main__':unittest.main()
