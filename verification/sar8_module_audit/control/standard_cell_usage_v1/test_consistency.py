"""Two focused deterministic checks; synthetic data is never simulator evidence."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
OWN=HERE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(OWN))
import prepare_first_event as base
import prepare_standard_cell_full as full
spec=importlib.util.spec_from_file_location('usage_fast',OWN/'standard_cell_storage_fastanalysis_v1/fast_gate_analyze.py')
fast=importlib.util.module_from_spec(spec);spec.loader.exec_module(fast)
sys.modules['fast_gate_analyze']=fast
import usage_analyze as usage


class Consistency(unittest.TestCase):
    def test_exact_connectivity_and_measurement_delta(self):
        manifest=json.loads((HERE/'manifest.json').read_bytes())
        a,b=[manifest['cases'][x]['physical_leaves'] for x in ['baseline','rck2k']]
        added=set(b)-set(a)
        self.assertEqual(added,{'XDUT.RCK'})
        self.assertEqual(b['XDUT.RCK'],dict(model='resistor',nodes=['XDUT.U19_CK_DRV','XDUT.U19_CK'],parameters='r=2000'))
        for name,value in a.items():
            actual=dict(b[name]);actual['nodes']=[x.replace('XDUT.U19_CK_DRV','XDUT.U19_CK') for x in actual['nodes']]
            self.assertEqual(value,actual,name)
        probe=json.loads((OWN/'standard_cell_full_v1/library_probe.json').read_bytes())
        old,lib=full.expand_library((OWN/'standard_cell_full_v1/storage_dut.scs').read_text(),
            'sar8audit_std_storage',probe,dict(VDD='VDD!',VSS='0',**{n:n for n in ['SR_R','SR_S','FF_CK','FF_D','FF_RST','CONTEXT']}))
        self.assertTrue(all(v==old[k] for k,v in a.items()))
        original_blocks=base.cells((OWN/'standard_cell_full_v1/full_adc/dut.scs').read_text())
        for label in ['baseline','rck2k']:
            folder=HERE/label
            text=(folder/'test.scs').read_text()
            self.assertEqual(text.count('simulatorOptions options '),1)
            self.assertIn('tran_first tran stop=20n maxstep=10p',text)
            for name,block in base.cells((folder/'dut.scs').read_text()).items():
                if name!='sar8audit_std_usage':self.assertEqual(block,original_blocks[name])
            cfg=json.loads((folder/'measurement.json').read_bytes())
            fullcat=manifest['cases'][label]['physical_leaves']
            for node,terms in cfg['kcl_terms'].items():
                expected={path.lower()+':'+str(i+1) for path,part in fullcat.items() for i,n in enumerate(part['nodes']) if n==node}
                self.assertEqual(set(terms),expected)
                self.assertTrue(expected<={p.lower() for p in cfg['current_saves']})
            for device in ['MM64','MM65','MM66']:
                self.assertTrue(all('XDUT.XU19.XFF.'+device+':'+str(i) in cfg['current_saves'] for i in range(1,5)))
            recipe=json.loads((folder/'recipe.suggested.yaml').read_bytes())
            files={x['name']:x for x in recipe['inputs']}
            for item in files.values():
                self.assertEqual(hashlib.sha256((ROOT/item['source']).read_bytes()).hexdigest(),item['sha256'])
            self.assertEqual(set(re.findall(r'file="([^"]+)"',text)),{n for n in files if n.startswith('pwl/')})
        for name in ['ff_ck','ff_d','ff_rst','context']:
            ra=json.loads((HERE/'baseline/recipe.suggested.yaml').read_bytes())
            rb=json.loads((HERE/'rck2k/recipe.suggested.yaml').read_bytes())
            byname=lambda r:{x['name']:x['sha256'] for x in r['inputs']}
            self.assertEqual(byname(ra)['pwl/'+name+'.pwl'],byname(rb)['pwl/'+name+'.pwl'])

    def test_native_joint_arithmetic_and_current_visibility(self):
        cfg=json.loads((HERE/'rck2k/measurement.json').read_bytes())
        selected=sorted({fast.norm(n) for n in cfg['voltage_saves']+cfg['current_saves']})
        currents={fast.norm(n) for n in cfg['current_saves']}
        times=[0.,5.02e-9,5.03e-9,6.02e-9,20e-9]
        d=[.2,.85,.99,1.,.2];s=[0.,-.15,-.12,0.,0.]
        with tempfile.TemporaryDirectory(prefix='_consistency_',dir=HERE) as tmp:
            root=Path(tmp);raw=root/'synthetic.tran.tran';out=root/'out';out.mkdir()
            with raw.open('w',encoding='ascii',newline='\n') as f:
                f.write('HEADER\nTYPE\nSWEEP\n"time" FLOAT DOUBLE\nTRACE\n')
                for n in selected:f.write('"'+n+'" FLOAT DOUBLE\n')
                f.write('VALUE\n')
                for k,t in enumerate(times):
                    f.write('"time" %.17g\n'%t)
                    for n in selected:
                        value=0. if n in currents else .2
                        if n=='vdd!':value=.99
                        if n=='xdut.xu19.xff.mq_x':value=d[k]
                        if n=='xdut.xu19.xff.net176':value=s[k]
                        if n=='xdut.xu19.xff.mm64:3':value=1e-6
                        if n=='xdut.xu19.xff.mm65:1':value=-1e-6
                        if n=='xdut.xu19.xff.mm64:2':value=1e-4
                        f.write('"%s" %.17g\n'%(n,value))
                f.write('END\n')
            result=fast.summarize(str(raw),cfg,str(out))
            pair=result['full_history_voltage_stress']['XDUT.XU19.XFF.MM64_VDS']
            self.assertAlmostEqual(pair['max_abs_v'],1.11,places=14)
            self.assertEqual(pair['max_abs_time_s'],5.03e-9)
            self.assertEqual(result['node_kcl']['xdut.xu19.xff.net176']['max_abs_a'],0.)
            self.assertAlmostEqual(result['node_kcl']['xdut.xu19.xff.clkbb']['max_abs_a'],1e-4)
            self.assertEqual(usage.usage_observations(str(out),cfg)['pin_waveform_rows'],5)
        edge=usage.pin_edges([(0.,0.),(1e-12,.1),(9e-12,.9),(10e-12,1.)],1,1.)[0]
        self.assertAlmostEqual(edge['slew_10_90_s']/1e-12,8.)
        self.assertEqual(edge['native_bracket_s'],[1e-12,9e-12])
        print('SYNTHETIC_ONLY: simultaneous stress and signed current sums verified; no circuit outcome claimed')


if __name__=='__main__':unittest.main()
