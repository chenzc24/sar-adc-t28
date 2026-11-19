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
        for name in ['design/manifest.json', 'design/floorplan.json',
                     'specs/interfaces.json', 'specs/constraints.json']:
            dest = self.root/'Layout'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project.ROOT/'Layout'/name, dest)
        # Exercise the released physical plan with the electrical manifest it actually used.
        physical = json.loads((self.root/'Layout/design/manifest.json').read_text())
        current = self.root/'design/manifest.json'
        expected = physical['electrical_sources_sha256']['design/manifest.json']
        if planning.digest(current) != expected:
            released = next(path for path in (self.root/'design/frozen').glob('*/manifest.json')
                            if planning.digest(path) == expected)
            shutil.copyfile(released, current)
            shutil.copyfile(released.with_name('dut.scs'), self.root/'design/dut.scs')
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
        self.assertEqual(result['area']['core_allocation'], 29920)
        self.assertIsNone(result['area']['die_area'])
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

    def test_new_render_cannot_refresh_old_qualification(self):
        planning.render(self.root)
        p = self.root/'Layout/results/current.json'; data = json.loads(p.read_text())
        data['qualification_inputs_sha256'] = data['planning_inputs_sha256']
        p.write_text(json.dumps(data))
        self.mutate('design/floorplan.json', lambda d: d['blocks'][0]['origin'].__setitem__(0, 21))
        self.assertTrue(planning.check(self.root)['planning_projection_stale'])
        planning.render(self.root)
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
