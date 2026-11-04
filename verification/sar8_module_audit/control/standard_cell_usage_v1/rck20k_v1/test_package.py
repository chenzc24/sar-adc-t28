"""Exact electrical delta and one synthetic gzip/edge pipeline; no simulation."""
from pathlib import Path
import copy
import gzip
import importlib.util
import json
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
USAGE=HERE.parent
OWN=USAGE.parent
ROOT=OWN.parents[2]
for p in [OWN,USAGE/'recovery_v1',HERE]:sys.path.insert(0,str(p))
import prepare_first_event as base
from review_standard_cell_storage_v2 import identity,record
import fast_gzip_analyze as fast
import storage_gzip as history
import usage_gzip as usage
import transition_observe as extension


def read(p):return json.loads(p.read_bytes())


class CandidatePreparation(unittest.TestCase):
    def test_one_resistor_only_and_frozen_input_reuse(self):
        source=record('sar8audit-ctrl-usage-rck2k-ff-v1')
        files={x['name']:ROOT/x['source'] for x in source['recipe']['files']}
        old=files['dut.scs'].read_text();new=(HERE/'dut.scs').read_text()
        self.assertEqual(old.replace('resistor r=2000\n','resistor r=20000\n'),new)
        self.assertEqual(old.count('resistor r=2000\n'),1)
        self.assertEqual(identity(HERE/'test.scs'),identity(files['test.scs']))
        cfg=read(HERE/'measurement.json');original=read(files['measurement.json'])
        restored=copy.deepcopy(cfg);restored['usage']['case']='rck2k';self.assertEqual(restored,original)
        manifest=read(HERE/'manifest.json');prior=read(USAGE/'manifest.json')['cases']['rck2k']['physical_leaves']
        self.assertEqual(set(manifest['physical_leaves']),set(prior))
        changed=[n for n in prior if prior[n]!=manifest['physical_leaves'][n]]
        self.assertEqual(changed,['XDUT.RCK'])
        self.assertEqual(manifest['physical_leaves']['XDUT.RCK'],dict(prior['XDUT.RCK'],parameters='r=20000'))
        for node,terms in cfg['kcl_terms'].items():
            expected={path.lower()+':'+str(i+1) for path,item in manifest['physical_leaves'].items() for i,n in enumerate(item['nodes']) if n==node}
            self.assertEqual(set(terms),expected)
            self.assertLessEqual(expected,{p.lower() for p in cfg['current_saves']})
        recipe=read(HERE/'recipe.suggested.yaml');freeze=read(HERE/'freeze.json')
        self.assertEqual(identity(HERE/'recipe.suggested.yaml'),freeze['proposed_recipe_file'])
        self.assertEqual(identity(HERE/'manifest.json'),freeze['manifest'])
        for item in recipe['inputs']:
            self.assertEqual(identity(ROOT/item['source'])['sha256'],item['sha256'])
        shared=['pwl/ff_ck.pwl','pwl/ff_d.pwl','pwl/ff_rst.pwl','pwl/context.pwl','external_library.json','full_gate_analyze.py','standard_cell_full_analyze.py']
        rfiles={i['name']:i for i in recipe['inputs']}
        for n in shared:self.assertEqual(rfiles[n]['sha256'],identity(files[n])['sha256'])
        config=read(HERE/'extension_config.json');normalized=read(USAGE/'characterization/liberty_v2/attribute_recovery/normalized_coordinate.json')
        for pin in ['CP','D','CDN']:
            for edge in ['rise','fall']:
                entry=config['input_basis'][pin][edge];basis=normalized['edge_ranges']['baseline'][pin][edge]
                self.assertEqual(entry['threshold_pct'],basis['raw_threshold_pct'])
                self.assertEqual(entry['slew_derate_from_library'],basis['explicit_derate'])
                self.assertEqual(entry['transition_axis_s'],normalized['declared_input_transition_axis_range_s'])
        self.assertIn('native.summarize(raw[0],cfg,output)',(HERE/'analyze.py').read_text())
        self.assertIn('history.verify_compressed(output,cfg,result)',(HERE/'analyze.py').read_text())

    def test_native_gzip_and_nonlinear_threshold_extension(self):
        cfg=read(HERE/'measurement.json');config=read(HERE/'extension_config.json')
        rail=cfg['usage']['vdd_v']
        nonlinear=[(t*1e-12,v*rail) for t,v in [(0.,0.),(1.,.1),(2.,.3),(5.,.7),(9.,.9),(10.,1.)]]
        event=extension.extended_edges(nonlinear,1,rail,config['input_basis']['CP'])[0]
        self.assertAlmostEqual(event['slew_30_70_s']/1e-12,3.)
        self.assertAlmostEqual(event['library_coordinate_s']/1e-12,6.)
        self.assertAlmostEqual(event['slew_10_90_s']/1e-12,8.)
        self.assertNotEqual(event['slew_10_90_s'],event['library_coordinate_s'])
        self.assertEqual(event['crossings']['0.3']['native_bracket_s'],[1e-12,2e-12])
        selected=sorted({fast.norm(n) for n in cfg['voltage_saves']+cfg['current_saves']})
        currents={fast.norm(n) for n in cfg['current_saves']}
        samples=[(0.,1.),(4.99e-9,1.),(5e-9,1.)]+[(5e-9+t*1e-12,1.-v) for t,v in [(1.,.1),(2.,.3),(5.,.7),(9.,.9),(10.,1.)]]+[(6e-9,0.),(20e-9,0.)]
        with tempfile.TemporaryDirectory(prefix='_synthetic_',dir=HERE) as tmp:
            root=Path(tmp);raw=root/'synthetic.tran.tran';out=root/'derived';out.mkdir()
            with raw.open('w',encoding='ascii',newline='\n') as f:
                f.write('HEADER\nTYPE\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n')
                for n in selected:f.write('"'+n+'" FLOAT DOUBLE\n')
                f.write('VALUE\n')
                for t,level in samples:
                    f.write('"time" %.17g\n'%t)
                    for n in selected:
                        value=0. if n in currents else .2
                        if n=='vdd!':value=rail
                        if n in ['xdut.u19_ck','xdut.u19_d','xdut.xu19.rn','xdut.xu19.xff.clkbb','xdut.xu19.xff.mq']:value=level*rail
                        if n=='xdut.xu19.xff.clkb':value=(1.-level)*rail
                        if n=='xdut.xu19.xff.mq_x':value=.99
                        if n=='xdut.xu19.xff.net176':value=-.12 if 5e-9<t<6e-9 else 0.
                        if n=='xdut.xu19.xff.mm64:3':value=1e-6
                        if n=='xdut.xu19.xff.mm65:1':value=-1e-6
                        f.write('"%s" %.17g\n'%(n,value))
                f.write('END\n')
            before=identity(raw)
            result=fast.summarize(str(raw),cfg,str(out))
            result['storage_observations']=history.observe_history(str(out),cfg)
            result['usage_observations']=usage.usage_observations(str(out),cfg)
            observed=extension.observe(str(out),cfg,config,result)
            proof=history.verify_compressed(str(out),cfg,result)
            self.assertTrue(proof['decompressed_bytes_and_SHA_match'])
            self.assertFalse((out/'peak.native.bin').exists())
            self.assertEqual(len(result['full_history_voltage_stress']),348)
            self.assertEqual(len(result['node_kcl']),6)
            self.assertAlmostEqual(result['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS']['max_abs_v'],1.11)
            self.assertEqual(result['node_kcl']['xdut.xu19.xff.net176']['max_abs_a'],0.)
            self.assertEqual(observed['native_projected_rows'],len(samples))
            self.assertEqual(observed['focus_edges']['CP']['status'],'one_native_focus_event')
            self.assertTrue(observed['reference_contrasts']['baseline']['focus_edges']['CP']['actual_event_shift_s']!=0)
            self.assertFalse(observed['reference_contrasts']['baseline']['focus_edges']['CP']['waveform_shift_applied'])
            self.assertIsNone(observed['whole_ADC_qualified'])
            self.assertIsNone(observed['actual_ranges']['clkb']['rise']['library_coordinate_s'])
            self.assertEqual(before,identity(raw))
        print('SYNTHETIC_ONLY: gzip/348pairs/sixKCL/storage and nonlinear30/70/.5 validated; no transistor result')


if __name__=='__main__':unittest.main()
