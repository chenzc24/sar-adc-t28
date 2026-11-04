"""Boundary/measurement contract checks. Synthetic traces are not circuit evidence."""
import copy,hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_candidate import OWN,BASE,ROOT,REF,candidate,read,expand
from interface_analyze import validate
from build_first_fixture import definitions
from test_reference_current_analyze import raw_text


class HDInterfaceTest(unittest.TestCase):
    def test_frozen_boundary_and_exact_physical_map(self):
        d,flat,lib,meta,delta=candidate();out=OWN/'candidate'
        actual,native=expand(definitions((out/'dut.scs').read_text()),meta)
        self.assertEqual(actual,flat);self.assertEqual(native,lib)
        self.assertEqual(len(delta['removed']),4);self.assertEqual(len(delta['added']),8)
        self.assertEqual(set(delta['changed']),{'XDUT.XBBM0.XD_HD.MP_CLEAR'})
        strip=lambda s:'\n'.join(l for l in s.splitlines() if not l.startswith('save '))
        self.assertEqual(strip((out/'ffcold/test.scs').read_text()),strip((BASE/'ffcold/test.scs').read_text()))
        c=read(out/'package_review.json')['cases'][0]
        for f in c['files']:
            b=(ROOT/f['source']).read_bytes();self.assertEqual((len(b),hashlib.sha256(b).hexdigest()),(f['bytes'],f['sha256']))
        cfg=read(out/'ffcold/measurement.json');validate(cfg)
        self.assertNotIn('baseline_equivalent_terminal_groups',cfg)
        self.assertNotIn('single_HD_X005_native_drive',cfg)
        bad=copy.deepcopy(cfg);bad['selected_mos_pair_screens'][0]['screen_v']=9.
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(cfg);bad['terminal_current_catalog']['XDUT.XBBM0.XD_HD.X005.MN_IO:2']['node']='CODE'
        with self.assertRaises(ValueError):validate(bad)

    def test_native_parser_incidence_and_reset_contract(self):
        out=OWN/'candidate';cfg=read(out/'ffcold/measurement.json')
        times=[0,41.5,42.5,42.995,43,43.005,43.05,43.2,43.4,44,45,46,47,47.99,47.995,48,48.005,48.05,48.3,49,50,51.5,52]
        names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
        for ns in times:
            v={n:0. for n in names.values()}
            def put(n,x):v[names[n]]=x
            put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('vrefp',.9)
            put('code',.495 if ns in [43,48] else .99 if 43<ns<48 else 0)
            high=43.2<=ns<48.3
            put('xdut.xbbm0.xd_hd.hd_raw',.99 if high else 0)
            put('xdut.xbbm0.hd',.7425 if high else .2475)
            put('xdut.xbbm0.x002.n',0 if high else .99)
            put('xdut.xbbm0.xd_hd.rc0',.99 if 43.05<=ns<48.05 else 0)
            put('xdut.xbbm0.xd_hd.rc1',0 if 43.2<=ns<48.3 else .99)
            if ns==43.005:put('xdut.xbbm0.xd_hd.rc1',1.04)
            put('xdut.xbbm0.xd_ld.rc0',0 if 43.2<=ns<48.3 else .99)
            put('xdut.xbbm0.xd_ld.rc1',.99 if 43.2<=ns<48.3 else 0)
            put('xdut.xbbm0.ld',0 if 43.2<=ns<48.3 else .99)
            for n,a,b in [('xdut.h0',43.4,48.05),('xdut.pre',43.4,48.3),('xdut.gpn0',43.4,48.05),('xdut.gpp0',43.05,48.3)]:put(n,.99 if a<=ns<b else 0)
            for n,a,b in [('xdut.l0',43.05,48.3),('xdut.xbbm0.cb',43.05,48.05),('xdut.gnn0',43.2,48.3),('xdut.gnp0',43.4,48.05)]:put(n,0 if a<=ns<b else .99)
            put('xdut.xcdac.bn0',.9 if 44<=ns<49 else 0);put('xdut.xcdac.bp0',.9 if ns>=49 else 0)
            # Intentionally synthetic current incidence identities, not IV physics.
            for n,x in [('xdut.xbbm0.xd_hd.mp_clear:1',-6e-6),('xdut.xbbm0.xd_hd.c1:1',2e-6),
                ('xdut.xbbm0.xd_hd.r1:2',1e-6),('xdut.xbbm0.xd_hd.x005.mn_io:2',1e-6),
                ('xdut.xbbm0.xd_hd.x005.mp_io:2',2e-6),('xdut.xbbm0.xd_hd.x005.mn_io:1',3e-6),
                ('xdut.xbbm0.xd_hd.r_guard:1',-3e-6),('xdut.xbbm0.xd_hd.r_guard:2',3e-6),
                ('xdut.xbbm0.xd_hd.c_guard:1',2e-6),('xdut.xbbm0.x002.x000.xlib.mm4:2',-5e-6),('vvdd:1',-20e-6)]:put(n,x)
            rows.append((ns*1e-9,v))
        rows[-1]=(52e-9,rows[-1][1])
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for f in read(out/'ffcold/recipe_proposal.json')['inputs']:shutil.copyfile(ROOT/f['source'],run/'inputs'/f['name'])
            (run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n')
            (run/'spectre.out').write_text('SYNTHETIC CONTRACT CHECK; NOT SPECTRE OR PHYSICAL RESULT\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            p=subprocess.run([sys.executable,'-B',str(run/'inputs/interface_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            r=read(run/'derived/result.json');m=r['cell_measurements'];q=m['interface_measurements']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual(len(r['selected_mos_pair_extrema']),738)
            self.assertFalse(m['original_full_swing_HD_reset_contract']['diagnostic_reset_complete'])
            self.assertEqual(m['original_full_swing_HD_reset_contract']['target_V'],0.)
            self.assertNotIn('xdut.xbbm0.hd',m['delay_leg_reset_diagnostics']['HD']['nodes'])
            self.assertTrue(all(x['diagnostic_reset_complete'] for x in q['HD_RC_reset_nodes'].values()))
            for n in cfg['interface_nodes']:
                self.assertLess(q['nodes'][n]['phases']['full']['max_KCL_A'],1e-20)
            gate=q['nodes']['xdut.xbbm0.hd']['phases']['CODE_fall']
            self.assertAlmostEqual(gate['signed_charge_C']['xdut.xbbm0.x002.x000.xlib.mm4:2'],-5e-6*(52e-9-47.995e-9),delta=1e-27)
            self.assertEqual(q['static_windows']['high']['HD_min_V'],.7425)
            self.assertEqual(q['static_windows']['low_after']['HD_max_V'],.2475)
            self.assertFalse(q['static_windows']['high']['original_full_swing_HD_1percent_met'])
            self.assertFalse(q['static_windows']['low_after']['original_full_swing_HD_1percent_met'])
            self.assertEqual(q['static_windows']['high']['NAND_N_max_V'],0.)
            self.assertAlmostEqual(q['static_windows']['high']['total_mean_VDD_current_A'],20e-6)
            self.assertIn('unknown',q['static_windows']['high']['library_VIH_VIL_qualification'])
            self.assertEqual(len(m['all_terminal_native_phase_time']['phases']['full']['pairs']),738)


if __name__=='__main__':unittest.main()
