"""Functional module interfaces, real substitution and current/frozen packaging."""
import importlib
import json
import math
import re
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from design.behav.python import AdcSpec,AnalogConfig,SarAdcModel
from design.behav.python.sampler import Sampler
from design.behav.python.cdac import Cdac
from design.behav.python.comparator import Comparator,Decision
from design.behav.python.reference import ReferenceControl
from tools.saradc import views
from tools.saradc import modular

entry=importlib.import_module('tools.saradc.__main__')


class ModuleChecks(unittest.TestCase):
    def setUp(self):
        self.spec=AdcSpec.load();self.analog=AnalogConfig();self.timing=self.spec.timing

    def test_sampler_finite_acquisition_and_frame_capture(self):
        s=Sampler(AnalogConfig(gain=.99,sampling_offset_v=.001),tau_s=1e-9)
        self.assertAlmostEqual(s.acquire(1,1e-9),1-math.exp(-1))
        self.assertEqual(s.acquire(1,0,initial_v=.25),.25)
        self.assertAlmostEqual(s.capture(.2,random.Random(1)),.199)
        with self.assertRaises(ValueError):s.acquire(.1,-1)

    def test_cdac_weight_endpoints_and_finite_step(self):
        c=Cdac(self.spec,AnalogConfig(dac_tau_s=2e-9))
        self.assertAlmostEqual(c.threshold(0),-.9)
        self.assertAlmostEqual(c.threshold(255),.9-self.spec.lsb)
        c.reset(0)
        self.assertAlmostEqual(c.evaluate(192,2e-9),.45*(1-math.exp(-1)))
        c.reset(0)
        self.assertAlmostEqual(c.evaluate(128,2e-9),0)

    def test_comparator_offset_sign_delay_and_stall(self):
        c=Comparator(self.spec,AnalogConfig(comparator_offset_v=.01),dict(self.timing,comparator_tau_s=80e-12))
        far=c.decide(.1,0,7,random.Random(1));near=c.decide(.011,0,7,random.Random(1))
        self.assertTrue(far.high);self.assertGreater(near.delay_s,far.delay_s)
        self.assertFalse(c.decide(.005,0,7,random.Random(1)).high)
        stuck=Comparator(self.spec,AnalogConfig(stuck_bit=3),self.timing)
        self.assertIsNone(stuck.decide(.1,0,3,random.Random(1)).delay_s)

    def test_reference_all_bits_break_before_make_and_precharge(self):
        r=ReferenceControl(self.timing)
        self.assertEqual(r.precharge_word,128)
        for old,new in [(0,255),(255,0),(128,64)]:
            for t in [0,50e-12,100e-12,1e-9]:
                for gnn,gnp,gpn,gpp in r.gates(old,new,t):
                    self.assertFalse(gnn and not gnp)
                    self.assertFalse(gpn and not gpp)
        first,second=r.captures(1e-9)
        self.assertLess(first,second);self.assertLess(second,r.next_compare(second))

    def test_top_uses_injected_comparator_and_resets_cdac_between_frames(self):
        class AlwaysLow:
            def decide(self,*args):return Decision(False,1e-10,0)
        m=SarAdcModel(comparator=AlwaysLow())
        self.assertEqual(m.convert(.8).code,0)
        m=SarAdcModel(analog=AnalogConfig(dac_tau_s=2e-9))
        first=m.convert(.123)
        m.convert(-.8)
        self.assertEqual(m.convert(.123),first)

    def test_current_and_frozen_views_are_explicit_and_separate(self):
        cur=views.build();old=views.build('frozen-b')
        self.assertIn('top/adc_top.scs',cur)
        self.assertNotIn('top/adc_top.scs',old)
        self.assertEqual(old['dut.scs'],(views.ROOT/'design/frozen/b/dut.scs').read_bytes())
        self.assertEqual(views.resolve('comparator_xtor')['comparator'],'xtor')
        self.assertEqual(views.resolve('comparator_xtor')['cdac'],'va')

    def test_all_mixed_profiles_bind_real_functional_modules(self):
        for name in ['behavioral','comparator_xtor','cdac_xtor','sampler_xtor','control_xtor']:
            blobs=views.build(name);top=blobs['top/adc_top.scs'].decode()
            for key,row in views.registry()['modules'].items():
                target=row['va'] if views.resolve(name)[key]=='va' else row['master']
                self.assertIn(target,top)
            self.assertIn('sampler.va',blobs)
            self.assertIn(b'ahdl_include "sampler.va"',blobs['dut.scs'])

    def test_electrical_leaf_ports_match_the_B_interfaces(self):
        manifest=json.loads((entry.ROOT/'design/manifest.json').read_text())['subcircuits']
        for key,row in views.registry()['modules'].items():
            if key=='sampler':continue  # Explicit three-to-five pin wrapper.
            text=(entry.ROOT/'design/behav/veriloga'/row['file']).read_text()
            pins=re.search(r'module '+row['va']+r'\(([^)]+)\)',text).group(1).split(',')
            self.assertEqual(pins,manifest[row['master']]['ports'])

    def test_edited_current_leaf_is_packaged_without_changing_frozen_regression(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for folder in ['design','specs','tb','tools','results']:
                shutil.copytree(entry.ROOT/folder,root/folder,ignore=shutil.ignore_patterns('__pycache__'))
            leaf=root/'design/xtor/comparator/comparator.scs'
            leaf.write_bytes(leaf.read_bytes().replace(b'w=500n',b'w=510n',1)+b'\n// Current-design packaging sentinel\n')
            with patch.object(entry,'ROOT',root):
                self.assertFalse(entry.check()['matches_frozen_b'])
                current=json.loads((root/entry.prepare('tt_short',run_id='test-default-current')).read_text())
                frozen=json.loads((root/entry.prepare('tt_short',run_id='test-frozen',view='frozen-b')).read_text())
                paths={r['name']:r['source'] for r in current['inputs']}
                self.assertIn(b'packaging sentinel',(root/paths['xtor/comparator/comparator.scs']).read_bytes())
                self.assertNotIn('xtor/comparator/comparator.scs',{r['name'] for r in frozen['inputs']})
                cap=root/'design/xtor/cdac/cdac.scs'
                cap.write_bytes(cap.read_bytes().replace(b'cfmom_2t nr=8 lr=2u',b'cfmom_2t nr=8 lr=2.1u'))
                char=entry.prepare('mc_cdac_tt',run_id='test-current-cap')
                self.assertEqual((root/char).with_name('test.scs').read_text().count('lr=2.1u'),18)
                old=entry.prepare('mc_cdac_tt',run_id='test-frozen-cap',view='frozen-b')
                self.assertNotIn('lr=2.1u',(root/old).with_name('test.scs').read_text())
                mixed=json.loads((root/entry.prepare('tt_short',run_id='test-mixed',view='cdac_xtor')).read_text())
                self.assertEqual(mixed['analyzer'],'analyze_modules.py')
                with self.assertRaisesRegex(ValueError,'Mixed views'):
                    entry.prepare('mc_cold_ss',run_id='test-invalid-mc',view='behavioral')

    def test_follow_only_analyzes_a_completed_simulation_then_collects(self):
        states=iter([('queued','not_started'),('running','not_started'),('complete','not_started'),('complete','running'),('complete','complete')])
        fake=Mock()
        def phase(action,run_id,queue=False):
            if action=='status':
                sim,ana=next(states)
                return dict(simulation=dict(status=sim),analysis=dict(status=ana))
            self.assertEqual(action,'analyze');self.assertTrue(queue)
            return dict(accepted=True)
        fake.phase.side_effect=phase
        with tempfile.TemporaryDirectory() as d,patch.object(modular,'ROOT',Path(d)),patch.object(entry,'engine',return_value=fake),patch('tools.saradc.behavioral.collect',return_value={'pass':True}) as collect:
            self.assertEqual(modular.follow('test-follow',poll_s=0,wait_s=5),{'pass':True})
        self.assertEqual(sum(c.args[0]=='analyze' for c in fake.phase.call_args_list),1)
        collect.assert_called_once_with('test-follow')

    def test_follow_retains_native_failure_without_retrying(self):
        fake=Mock();fake.phase.return_value=dict(simulation=dict(status='limit_exceeded'),analysis=dict(status='not_started'))
        with tempfile.TemporaryDirectory() as d,patch.object(modular,'ROOT',Path(d)),patch.object(entry,'engine',return_value=fake),patch('tools.saradc.behavioral.collect') as collect:
            with self.assertRaises(RuntimeError):modular.follow('test-failed',poll_s=0,wait_s=5)
        collect.assert_not_called()
        self.assertEqual(fake.phase.call_count,1)


if __name__=='__main__':unittest.main()
