"""Structural and synthetic measurement checks; never execute Spectre."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
import unittest

import build_kickback_fixture as b
import kickback_analyze as a

OWN=Path(__file__).resolve().parent
PACKAGE=OWN/'generated/kickback_v1'


def read_cfg():
    return json.loads((PACKAGE/'measurement.json').read_bytes())


def interp(points,t):
    points=[(x,.9 if y=='SUP' else y) for x,y in points]
    if t<=points[0][0]:return points[0][1]
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        if t<=x1:return y0+(y1-y0)*(t-x0)/(x1-x0)
    return points[-1][1]


def samples(cfg):
    times={0.,260.}
    for at in b.STARTS:
        times.update(at+x for x in [-8.,-7.9,-2.,-1.9,-1.,0.,.05,.1,1.,1.5,2.,2.1,2.5,2.6,3.,12.,12.05,12.1])
    stim=b.d.stimulus_points()
    tokens=b.init_wave().split();init=[(float(tokens[i][:-1]),tokens[i+1] if tokens[i+1]=='SUP' else float(tokens[i+1])) for i in range(0,len(tokens),2)]
    names=cfg['voltage_saves']+cfg['current_saves'];rows=[]
    for ns in sorted(times):
        v=dict((n,.45) for n in cfg['voltage_saves']);v.update((n,0.) for n in cfg['current_saves'])
        v.update({'vdd!':.9,'vcm':.45,'vrefn':0.,'vrefp':.9,'vvdd:1':-1e-6,
                  'cmp_clk':interp(stim['CMP_CLK'],ns),'cinit':interp(init,ns),
                  'prep':interp(stim['TOPP'],ns),'pren':interp(stim['TOPN'],ns)})
        active=None
        for at,sign in zip(b.STARTS,b.SIGNS):
            if at<=ns<=at+12.1:active=(at,sign)
        for arm_name,arm in cfg['arms'].items():
            v[arm['topp']],v[arm['topn']]=v['prep'],v['pren']
            v[arm['comp_p']],v[arm['comp_n']]=.9,.9
            v[arm['prefix'].lower()+'.xcomp.x']=.9
            v[arm['prefix'].lower()+'.xcomp.y']=.9
            v[arm['data']],v[arm['write']]=0.,0.
            stored=0
            for at,sign in zip(b.STARTS,b.SIGNS):
                if ns>=at+3:stored=int(sign>0)
            v[arm['d0']]=.9*stored if arm_name=='evaluate' else 0.
            if arm_name=='evaluate' and active is not None:
                at,sign=active
                v[arm['gate_p']],v[arm['gate_n']]=-1e-6,1e-6
                if ns>=at+1:
                    v[arm['topp']]+=.0004
                    # This creates known +0.4mV differential, +0.2mV CM motion.
                if ns>=at+1.5:
                    v[arm['comp_p']],v[arm['comp_n']]=(.9,0.) if sign>0 else (0.,.9)
                    v[arm['data']]=.9*int(sign>0)
                if at+2<=ns<=at+2.1:v[arm['write']]=.9*(ns-at-2)/.1
                elif at+2.1<ns<=at+2.5:v[arm['write']]=.9
                elif at+2.5<ns<=at+2.6:v[arm['write']]=.9*(at+2.6-ns)/.1
        for node,terms in cfg['kcl_terms'].items():
            caps=[n for n in terms if cfg['terminal_catalog'][n]['model']=='cfmom_2t']
            other=sum(v[n] for n in terms if n not in caps)
            for n in caps:v[n]=-other/len(caps)
        assert set(names)<=set(v)
        rows.append((ns*1e-9,v))
    return rows


def psf(cfg,rows,sparse=False,group=False):
    names=cfg['voltage_saves']+cfg['current_saves'];alias=cfg['arms']['evaluate']['gate_p']
    lines=['HEADER','SWEEP','"time" "sweep" FLOAT DOUBLE','TRACE']
    for n in names:
        if group and n==alias:lines+=['"%s" GROUP 1'%n,'"probe_input_gate" FLOAT DOUBLE']
        else:lines+=['"%s" FLOAT DOUBLE'%n]
    lines.append('VALUE');old={}
    for t,v in rows:
        lines.append('"time" %.17g'%t)
        for n in names:
            if sparse and old.get(n)==v[n]:continue
            lines.append('"%s" %.17g'%('probe_input_gate' if group and n==alias else n,v[n]))
        old=v
    return '\n'.join(lines+['END',''])


class Package(unittest.TestCase):
    def test_exact_frozen_D2_and_physical_cap_parameters(self):
        manifest=json.loads((PACKAGE/'manifest.json').read_bytes())
        self.assertEqual((PACKAGE/'cells.scs').read_bytes(),(b.D2/'cells.scs').read_bytes())
        source=b.ROOT/manifest['source_DUT']['path']
        cap,identity=b.cap_load(b.d.blocks(source.read_text()))
        self.assertEqual((PACKAGE/'cdac_load.scs').read_text(),cap)
        self.assertEqual(len(identity),18)
        self.assertEqual(manifest['native_MOS'],934)
        self.assertEqual(manifest['selected_MOS_pairs'],228)
        for n,h in read_cfg()['required_input_sha256'].items():
            self.assertEqual(hashlib.sha256((PACKAGE/n).read_bytes()).hexdigest(),h)

    def test_original_clock_no_direct_input_voltage_clamp(self):
        text=(PACKAGE/'test.scs').read_text()
        old=(b.D2/'tt.scs').read_text()
        original=next(n for n in old.splitlines() if n.startswith('VCMP_CLK '))
        self.assertIn(original,text)
        self.assertNotIn('VTOPP (',text);self.assertNotIn('VTOPN (',text)
        self.assertNotRegex(text,r'(?m)^V\w* \(TOP[PN]_[AB] 0\)')
        self.assertEqual(text.count('cmp_charge_initializer ron=10'),4)
        self.assertNotIn('sar8i_refword',text)
        for c in read_cfg()['cycles']:
            self.assertAlmostEqual(c['start_s']-c['release_end_s'],1.9e-9)
        for node,terms in read_cfg()['kcl_terms'].items():self.assertEqual(len(terms),11)


class Measurement(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='_synthetic_kb_',dir=OWN)
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.cfg=read_cfg();self.rows=samples(self.cfg)

    def reduce(self,text=None,cfg=None):
        raw=self.root/'native.tran.tran';raw.write_text(psf(self.cfg,self.rows) if text is None else text)
        out=a.Output(str(self.root/'derived'),(cfg or self.cfg)['max_output_bytes'])
        return a.reduce(str(raw),cfg or self.cfg,out)

    def test_actual_generated_config_six_writes_and_paired_excursions(self):
        result=self.reduce()
        self.assertIsNone(result['acceptance_pass'])
        self.assertEqual(result['last_native_time_s'],self.rows[-1][0])
        self.assertEqual(len(result['cycles']),6)
        for c in result['cycles']:
            self.assertEqual(len(c['writes']),1)
            self.assertEqual(c['DATA_matches_nominal_at_each_write'],[True])
            self.assertTrue(c['late_D0_matches_nominal'])
            self.assertAlmostEqual(c['pre_compare_target_error_v'],0.)
            self.assertAlmostEqual(c['input_excursions']['evaluate_minus_reset_diff_v']['max'],.0004)
            self.assertAlmostEqual(c['input_excursions']['evaluate_minus_reset_cm_v']['max'],.0002)
            self.assertTrue(c['pre_compare']['reset_all_above_90pct']['evaluate'])
            self.assertAlmostEqual(c['after_release']['init_control_v'],0.,places=12)
            expected=-(c['phase_last_native_s']-c['phase_first_native_s'])*1e-6
            self.assertAlmostEqual(c['gate_charge_C'][self.cfg['arms']['evaluate']['gate_p']],expected,places=25)
        self.assertLess(max(x['max_abs_a'] for x in result['node_kcl'].values()),1e-18)
        w=result['waveform'];blob=gzip.decompress((self.root/'derived'/w['file']).read_bytes())
        self.assertEqual(hashlib.sha256(blob).hexdigest(),w['uncompressed_sha256'])
        width=len(w['columns']);last=struct.unpack('<'+'d'*width,blob[-width*8:])
        self.assertEqual(last[0],self.rows[-1][0])

    def test_sparse_and_current_group_keep_native_peak_and_integral(self):
        result=self.reduce(psf(self.cfg,self.rows,sparse=True,group=True))
        self.assertGreater(result['held_sparse_values'],0)
        n=self.cfg['arms']['evaluate']['gate_p']
        self.assertEqual(result['native_trace_binding'][n],'probe_input_gate')
        self.assertAlmostEqual(result['cycles'][0]['input_excursions']['evaluate_minus_reset_diff_v']['max'],.0004)

    def test_missing_current_initial_value_rejects(self):
        text=psf(self.cfg,self.rows);name=self.cfg['current_saves'][0]
        value='"%s" %.17g\n'%(name,self.rows[0][1][name])
        self.assertIn(value,text)
        with self.assertRaisesRegex(ValueError,'Uninitialized'):self.reduce(text.replace(value,'',1))

    def test_missing_END_rejects_without_result(self):
        with self.assertRaisesRegex(ValueError,'END'):self.reduce(psf(self.cfg,self.rows).replace('END\n',''))
        self.assertFalse((self.root/'derived/result.json').exists())

    def test_initializer_on_during_evaluation_rejects(self):
        rows=copy.deepcopy(self.rows)
        for t,v in rows:
            if 21e-9<=t<=22e-9:v['cinit']=.1
        with self.assertRaisesRegex(ValueError,'Initializer still active'):self.reduce(psf(self.cfg,rows))

    def test_output_budget_is_hard(self):
        cfg=copy.deepcopy(self.cfg);cfg['max_output_bytes']=32
        with self.assertRaisesRegex(ValueError,'cap exceeded'):self.reduce(cfg=cfg)

    def test_managed_result_last_preserves_CMI_and_real_package_hashes(self):
        run=self.root/'run';(run/'inputs').mkdir(parents=True);(run/'raw').mkdir()
        for name in self.cfg['required_input_sha256']:
            shutil.copyfile(PACKAGE/name,run/'inputs'/name)
        (run/'inputs/measurement.json').write_text(json.dumps(self.cfg))
        (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
            native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=['CMI-2204']))))
        (run/'raw/logStatus').write_text('tran_kickback PASS\n')
        (run/'raw/synthetic.tran.tran').write_text(psf(self.cfg,self.rows,sparse=True,group=True))
        (run/'spectre.out').write_text('WARNING (CMI-2204): synthetic only\nspectre completes with 0 errors\n')
        result=a.analyze(str(run),str(run/'derived'))
        self.assertEqual(result['native_warning_codes'],['CMI-2204'])
        self.assertIsNone(result['acceptance_pass'])
        self.assertEqual((run/'spectre.out').read_bytes(),(run/'derived/spectre.original.log').read_bytes())
        before=(run/'derived/result.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Fresh derived'):a.analyze(str(run),str(run/'derived'))
        self.assertEqual(before,(run/'derived/result.json').read_bytes())


if __name__=='__main__':unittest.main(verbosity=2)
