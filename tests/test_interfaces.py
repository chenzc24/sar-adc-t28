"""Public candidate, composition, and independent measurement behavior."""
import json
import re
from pathlib import Path
import shutil
import tempfile
import unittest
from itertools import product
from unittest.mock import patch
from tools.saradc import blocks,candidates,views
from tools.saradc import schematic
from tools.saradc.measure.analyze_blocks import analyze

ROOT=Path(__file__).resolve().parents[1]


class Interfaces(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for folder in ['design','specs','tb','tools']:
            shutil.copytree(ROOT/folder,self.root/folder,ignore=shutil.ignore_patterns('__pycache__'))

    def test_registering_and_explicitly_using_a_candidate_keeps_default(self):
        original=self.root/'design/xtor/comparator/comparator.scs'
        alternate=original.with_name('wide.scs')
        alternate.write_text(original.read_text().replace('w=1u','w=2u'))
        candidates.add('comparator','wide',alternate.relative_to(self.root).as_posix(),self.root)
        self.assertEqual(candidates.read(self.root)['modules']['comparator']['selected'],'b')
        before=views.build('current',self.root)['xtor/comparator/comparator.scs']
        selected=views.build('current',self.root,{'comparator':'wide'})['xtor/comparator/comparator.scs']
        self.assertEqual(before,original.read_bytes())
        self.assertEqual(selected,alternate.read_bytes())
        with self.assertRaisesRegex(ValueError,'VA module'):
            views.build(['current','comparator=va'],self.root,{'comparator':'wide'})

    def test_candidate_cannot_reorder_ports_or_import_external_models(self):
        p=self.root/'design/xtor/comparator/bad.scs'
        text=(p.with_name('comparator.scs')).read_text()
        p.write_text(text.replace('CLK OUTN OUTP','CLK OUTP OUTN',1))
        with self.assertRaisesRegex(ValueError,'interface'):
            candidates.add('comparator','bad',p.relative_to(self.root).as_posix(),self.root)
        p.write_text(text+'\ninclude "secret-model.scs"\n')
        with self.assertRaisesRegex(ValueError,'external'):
            candidates.add('comparator','bad',p.relative_to(self.root).as_posix(),self.root)

    def test_views_can_mix_reference_and_timing_inside_native_sar(self):
        profile=['current','reference=va','timing=va','comparator=va']
        blob=views.build(profile,self.root)
        self.assertRegex(blob['top/adc_top.scs'].decode(),r'\)\s+b_reference')
        self.assertRegex(blob['xtor/sar/sar.scs'].decode(),r'\)\s+b_sar8p_delay_write')
        self.assertRegex(blob['top/adc_top.scs'].decode(),r'\)\s+sar8i_ctrl')
        with self.assertRaisesRegex(ValueError,'Frozen B'):
            views.build(['frozen-b','comparator=va'],self.root)

    def test_all_64_module_combinations_resolve_and_unknown_candidate_dependency_fails(self):
        for choices in product(['xtor','va'],repeat=6):
            blobs=views.build([m+'='+v for m,v in zip(views.MODULES,choices)],self.root)
            top=blobs['top/adc_top.scs'].decode()
            expected=[('XBOOTN','sar_bootstrap_flat_8b_p','b_sampler_bridge'),
                      ('XCDAC','sar8j_r1_cdac','b_cdac'),('XCOMP','sar_strongarm_t28','b_comparator'),
                      ('XCTRL','sar8i_ctrl','b_sar'),('XREF','sar8i_refword','b_reference'),
                      ('XSEQ','sar8r_edge','b_sar8r_edge')]
            for view,(instance,physical,behavioral) in zip(choices,expected):
                call=re.search(r'(?m)^\s*'+instance+r'\s+\([^)]*\)\s+(\S+)',top)
                self.assertIsNotNone(call)
                self.assertEqual(call.group(1),physical if view=='xtor' else behavioral)
        path=self.root/'design/xtor/comparator/undefined.scs'
        path.write_text(path.with_name('comparator.scs').read_text().replace('nch_mac','undefined_device'))
        candidates.add('comparator','undefined',path.relative_to(self.root).as_posix(),self.root)
        with self.assertRaisesRegex(ValueError,'Unresolved candidate dependency'):
            views.build('current',self.root,{'comparator':'undefined'})

    def test_analysis_only_follow_collects_without_trying_to_simulate(self):
        from tools.saradc import __main__ as entry
        fake=unittest.mock.Mock()
        fake.phase.return_value={'simulation':{'status':'not_applicable'},'analysis':{'status':'complete'}}
        with patch.object(entry,'engine',return_value=fake),patch.object(blocks,'collect',return_value={'done':True}):
            self.assertEqual(blocks.follow('analysis-only'),{'done':True})
        fake.phase.assert_called_once_with('status','analysis-only')

    def test_analysis_only_collection_retains_the_completed_source_warnings(self):
        from tools.saradc import __main__ as entry
        folder=self.root/'work/output/managed_execution/runs/analysis/collected'
        (folder/'derived').mkdir(parents=True)
        (folder/'derived/result.json').write_text(json.dumps({'analysis_complete':True,'pass_validation':True,'failures':[]}))
        source=self.root/'work/output/managed_execution/runs/native/collected'
        source.mkdir(parents=True)
        (source/'spectre.out').write_text('WARNING (CMI-2751): native terminal warning\noriginal text\n')
        fake=unittest.mock.Mock();fake.collect.return_value={'local_path':folder.relative_to(self.root).as_posix()}
        fake.recipe.return_value={'source':{'run_id':'native'}}
        with patch.object(entry,'engine',return_value=fake):result=blocks.collect('analysis',self.root)
        warnings=(self.root/result['path']/'warnings.txt').read_text()
        self.assertIn('Native log source: native',warnings)
        self.assertIn('CMI-2751',warnings)
        fake.collect.assert_called_once_with('analysis')

    def test_schematic_has_all_native_levels_and_real_fixtures_without_work_history(self):
        levels,ports,origin,hashes=schematic.sources(self.root)
        self.assertFalse((self.root/'work').exists())
        native=[n for n in levels if origin[n].startswith(('design/xtor','design/top'))]
        self.assertEqual(len(native),49)
        self.assertIn('tb_reference',levels)
        self.assertIn('XRLOAD',levels['tb_reference'])
        self.assertIn('tb_sar_stalled_top',levels)
        self.assertFalse(any(p.startswith('work/') for p in hashes))
        for name in native:
            annotated,count=schematic.annotate(name,levels[name],ports)
            self.assertEqual(schematic.electrical_statements(annotated),schematic.electrical_statements(levels[name]))
            self.assertGreater(count,0)

    def test_independent_package_has_real_cdac_load_and_frozen_input_identity(self):
        recipe=blocks.prepare('test-independent',root=self.root)
        data=json.loads((self.root/recipe).read_text());folder=(self.root/recipe).parent
        self.assertIn('XRLOAD', (folder/'reference_fixture.scs').read_text())
        self.assertIn('sar8j_r1_cdac',(folder/'reference_fixture.scs').read_text())
        self.assertEqual(set(data['test_conditions']['modules']),set(views.MODULES))
        for row in data['inputs']:
            self.assertEqual(blocks.digest((self.root/row['source']).read_bytes()),row['sha256'])
        with self.assertRaisesRegex(ValueError,'identity'):
            blocks.prepare('test-independent',root=self.root)

    def test_missing_traces_are_invalid_and_logic_overlap_is_not_hidden(self):
        required=['r_'+g+str(k) for g in ['gnn','gnp','gpn','gpp'] for k in range(8)]
        context={'modules':['reference'],'required_signals':required,'reference_words':[0]*6}
        with self.assertRaisesRegex(ValueError,'Missing required'):
            analyze(context,lambda:iter([(0,{})]),{})
        good={s:(.9 if s.startswith(('r_gnn','r_gnp')) else 0.) for s in required}
        bad=dict(good);bad['r_gnp0']=0.
        result=analyze(context,lambda:iter([(0,good),(60e-9,good),(70e-9,bad),(80e-9,good),(665e-9,good)]),{})
        self.assertGreater(result['metrics']['reference']['logic_overlap_duration_s'],0)
        self.assertEqual(result['diagnostics'][0]['first']['bit'],0)
        self.assertFalse(result['pass_validation'])


if __name__=='__main__':unittest.main()
