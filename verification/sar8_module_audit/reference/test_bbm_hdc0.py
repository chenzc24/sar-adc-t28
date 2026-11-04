"""One changed-capacitor mapping and staged physical-window/reset measurement test."""
import copy,hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,ports,flatten
from bbm_hdc0_analyze import validate,VARIANT,measurements
from prepare_bbm_hdc0 import params,TARGET
from test_reference_current_analyze import raw_text
import io_cell_analyze as cell

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/real_bbm_v1';NEW=HERE/'generated/bbm_hdc0_v1'


class HDC0Test(unittest.TestCase):
    def test_only_HD_C0_multi_changed_clocks_fixed_windows_and_both_resets(self):
        def flat(path):
            d=definitions(path.read_text());return flatten(d,'sar8_realpre_unit',{p:'VDD!' if p=='VDD' else '0' if p=='VSS' else p for p in ports(d['sar8_realpre_unit'])})
        old,new=flat(OLD/'dut.scs'),flat(NEW/'dut.scs');self.assertEqual(set(old),set(new));self.assertEqual(len(new),196)
        self.assertEqual([n for n in old if old[n]!=new[n]],[TARGET]);self.assertEqual(old[TARGET]['nodes'],new[TARGET]['nodes'])
        a,b=params(old[TARGET]['parameters']),params(new[TARGET]['parameters']);self.assertEqual((a.pop('multi'),b.pop('multi')),('1','4'));self.assertEqual(a,b)
        for case in json.loads((NEW/'package_review.json').read_text())['cases']:
            folder=(ROOT/case['recipe']).parent;cfg=json.loads((folder/'measurement.json').read_text());v,i,k=validate(cfg)
            self.assertEqual((len(v),len(i),len(k)),(772,656,36));self.assertEqual(len(cfg['selected_mos_pair_screens']),738)
            self.assertEqual((folder/'test.scs').read_bytes(),(OLD/folder.name/'test.scs').read_bytes())
            self.assertEqual(case['recipe_sha256'],hashlib.sha256((folder/'recipe_proposal.json').read_bytes()).hexdigest());self.assertEqual(len(case['files']),8)
            for x in case['files']:
                data=(ROOT/x['source']).read_bytes();self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(x['bytes'],x['sha256']))
        cfg=json.loads((NEW/'ffcold/measurement.json').read_text());bad=copy.deepcopy(cfg);bad['single_component_contrast']['new_multi']=2
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(cfg);bad['selected_mos_pair_screens'][next(j for j,x in enumerate(bad['selected_mos_pair_screens']) if x['model']=='nch_mac')]['screen_v']=1.98
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for x in json.loads((NEW/'ffcold/recipe_proposal.json').read_text())['inputs']:shutil.copyfile(ROOT/x['source'],run/'inputs'/x['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            times=[0,41.5,42.9,42.995,43,43.005,43.05,43.1,43.15,43.2,43.25,43.3,43.35,43.4,43.45,43.5,44,44.2,45,46,47,47.99,47.995,48,48.005,48.05,48.1,48.15,48.2,48.25,48.3,48.35,48.4,48.45,48.5,48.6,49,49.5,50,51,51.5,52]
            for ns in times:
                values={n:0. for n in names.values()}
                def put(n,v):values[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('code',.495 if ns in [43,48] else .99 if 43<ns<48 else 0);put('vrefp',.9)
                put('xdut.h0',.99 if 43.2<=ns<48.1 else 0);put('xdut.l0',0 if 43.1<=ns<48.3 else .99)
                put('xdut.pre',.99 if 43.2<=ns<48.4 else 0);put('xdut.gpnpre',0 if 43.3<=ns<48.3 else .99)
                put('xdut.gnn0',0 if 43.25<=ns<48.5 else .99);put('xdut.gpp0',.99 if 43.15<=ns<48.4 else 0)
                put('xdut.gnp0',0 if 43.4<=ns<48.3 else .99);put('xdut.gpn0',.99 if 43.45<=ns<48.3 else 0)
                put('xdut.xbbm0.cb',0 if 43.05<=ns<48.05 else .99)
                put('xdut.xbbm0.xd_hd.rc0',.99 if 43.15<=ns<48.05 else 0);put('xdut.xbbm0.xd_hd.rc1',0 if 43.2<=ns<48.1 else .99)
                put('xdut.xbbm0.hd',.99 if 43.25<=ns<48.15 else 0)
                put('xdut.xbbm0.xd_ld.rc0',0 if 43.15<=ns<48.2 else .99);put('xdut.xbbm0.xd_ld.rc1',.99 if 43.2<=ns<48.25 else 0)
                put('xdut.xbbm0.ld',0 if 43.25<=ns<48.3 else .99)
                if ns==43.005:put('xdut.xbbm0.xd_hd.rc1',1.07)
                bn=.9 if 44.2<=ns<49 else 0.;bp=0.
                if 48.05<=ns<48.3:bn=.92;bp=-.01
                put('xdut.xcdac.bn0',bn);put('xdut.xcdac.bp0',bp)
                for b,x in cfg['terminal_current_catalog'].items():
                    if x['model'].startswith('pch') and x['port']==3 and x['node']=='VDD!':put(b.lower(),1e-6)
                code_load=next(b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node']=='CODE' and b!='VCODE:1');put(code_load,1e-6);put('vcode:1',-1e-6)
                for n,i in [('xdut.xbbm0.x004.x001.mn:1',-6e-6),('xdut.xbbm0.x004.x001.mp:1',-4e-6),('xdut.x025.mn:2',1e-6),('xdut.x025.mp:2',2e-6),('xdut.gppin:2',3e-6),('xdut.gppip:2',4e-6),
                    ('xdut.xbbm0.x002.x001.mn:1',-6e-6),('xdut.xbbm0.x002.x001.mp:1',-4e-6),('xdut.gnpan:2',1e-6),('xdut.gnpap:2',2e-6),('xdut.x008.mn:2',3e-6),('xdut.x008.mp:2',4e-6),
                    ('xdut.x025.mn:1',-1e-6),('xdut.x025.mp:1',-2e-6),('xdut.gnnan:2',1e-6),('xdut.gnnap:2',2e-6),('xdut.x008.mn:1',-1e-6),('xdut.x008.mp:1',-2e-6),('xdut.gpnan:2',1e-6),('xdut.gpnap:2',2e-6),
                    ('xdut.xcdac.xsn0.mn_low:1',2e-6),('xdut.xcdac.xsn0.mp_high:1',-1e-6),('xdut.xcdac.xsp0.mn_low:1',-3e-6),('xdut.xcdac.xsp0.mp_high:1',4e-6)]:put(n,i)
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n');(run/'spectre.out').write_text('synthetic measurement check only\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/bbm_hdc0_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements']
            self.assertEqual(r['cell_variant'],VARIANT);self.assertIsNone(r['acceptance_pass']);self.assertEqual(len(r['selected_mos_pair_extrema']),738)
            self.assertAlmostEqual(r['selected_mos_pair_extrema']['XDUT.XBBM0.XD_HD.X005.MN:gd']['max'],1.07)
            self.assertTrue(m['physical_command_phase_reference_settling']['select_high']['nodes']['xdut.xcdac.bn0']['diagnostic_established'])
            self.assertTrue(m['physical_command_phase_reference_settling']['select_high']['nodes']['xdut.xcdac.bp0']['diagnostic_established'])
            self.assertFalse(m['legacy_halfVDD_window_switching_diagnostic']['select_high']['nodes']['xdut.xcdac.bn0']['established_within_window'])
            self.assertFalse(m['physical_command_phase_reference_settling']['select_low']['nodes']['xdut.xcdac.bp0']['diagnostic_established'])
            for leg,q in m['delay_leg_reset_diagnostics'].items():
                self.assertIsNotNone(q['actual_input_falling_halfVDD_s'])
                for n,x in q['nodes'].items():self.assertTrue(x['diagnostic_reset_complete']);self.assertGreater(x['delay_from_CODE_midpoint_s'],0)
            self.assertEqual(len(m['body_forward_polarity']),246);self.assertEqual(len(m['CODE_source_and_input_load']['incident_load_branches']),8)
            self.assertGreater(m['opposed_total_reference_terminal_current']['N']['peak_min_opposed_abs_A'],0)
            self.assertLess(abs(m['CODE_source_and_input_load']['source_minus_load_work_J']),1e-23)
            self.assertTrue(all(abs(x['work_closure_residual_J'])<1e-23 for x in m['internal_driver_load_work'].values()))
            export=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');self.assertEqual((export['rows'],len(export['columns'])),(len(rows),376))
            missing=copy.deepcopy(r);missing['half_vdd_events']['xdut.gpn0']=[];mm=measurements(cell.metrics,missing,cfg,str(run/'derived'))
            self.assertEqual(mm['legacy_halfVDD_window_switching_diagnostic']['select_low']['status'],'missing_or_ambiguous_controls')


if __name__=='__main__':unittest.main()
