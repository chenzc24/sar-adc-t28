"""One focused topology/runtime contract check; synthetic data are not Spectre."""
import copy,hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from prepare import OLD,OWN,ROOT,candidate,read,expanded
from build_first_fixture import definitions
from gnn_analyze import validate
from test_reference_current_analyze import raw_text


class GNNIO1PackageTest(unittest.TestCase):
    def test_single_factor_and_actual_runtime_contract(self):
        d,expected,lib,meta,delta=candidate();out=OWN/'candidate'
        actual,native=expanded(definitions((out/'dut.scs').read_text()),meta)
        self.assertEqual(actual,expected);self.assertEqual(native,lib)
        self.assertEqual(len(delta['removed']),4);self.assertEqual(set(delta['changed']),{'XDUT.GNNCN','XDUT.GNNCP'})
        self.assertEqual(len(delta['Rgate_leaves_unchanged']),10)
        strip=lambda p:'\n'.join(l for l in p.read_text().splitlines() if not l.startswith('save '))
        self.assertEqual(strip(out/'sscold/test.scs'),strip(OLD/'sscold/test.scs'))
        case=read(out/'package_review.json')['cases'][0]
        for f in case['files']:
            b=(ROOT/f['source']).read_bytes();self.assertEqual((len(b),hashlib.sha256(b).hexdigest()),(f['bytes'],f['sha256']))
        cfg=read(out/'sscold/measurement.json');validate(cfg)
        self.assertEqual((len(cfg['voltage_saves']),len(cfg['current_saves']),len(cfg['selected_mos_pair_screens'])),(114,636,714))
        for p in cfg['static_windows']:self.assertFalse(set(p['expected_logic'])&{'xdut.gnna','xdut.gnnb'})
        bad=copy.deepcopy(cfg);bad['terminal_current_catalog']['XDUT.GNNCN:2']['node']='CODE'
        with self.assertRaises(ValueError):validate(bad)
        names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
        times=[0,41.5,42.5,42.99,42.995,43,43.005,43.02,43.05,43.15,43.2,43.25,43.3,43.4,43.6,44,45,46,47,47.99,47.995,48,48.005,48.02,48.05,48.15,48.2,48.25,48.3,48.4,48.6,49,50,51.5,52]
        for ns in times:
            values={n:0. for n in names.values()}
            def put(n,v):values[names[n]]=v
            put('vdd!',.81);put('sample',.81 if ns<41 else 0);put('vrefp',.9)
            put('code',.405 if ns in [43,48] else .81 if 43<ns<48 else 0)
            put('xdut.l0',0 if 43.02<=ns<48.2 else .81)
            put('xdut.pre',.81 if 43.05<=ns<48.25 else 0)
            put('xdut.gnndrv',0 if 43.15<=ns<48.3 else .81)
            put('xdut.gnn0',0 if 43.2<=ns<48.4 else .81)
            for n,a,b in [('xdut.h0',43.2,48.02),('xdut.gpn0',43.25,48.05),('xdut.gpp0',43.05,48.3),('xdut.gppdrv',43.05,48.3),('xdut.xbbm0.hd',43.3,48.15),('xdut.xbbm0.xd_ld.rc1',43.25,48.2),('xdut.xbbm0.xd_hd.rc0',43.15,48.02)]:put(n,.81 if a<=ns<b else 0)
            for n,a,b in [('xdut.gnp0',43.25,48.05),('xdut.xbbm0.ld',43.25,48.3),('xdut.xbbm0.cb',43.02,48.02),('xdut.xbbm0.xd_ld.rc0',43.15,48.15),('xdut.xbbm0.xd_hd.rc1',43.25,48.05)]:put(n,0 if a<=ns<b else .81)
            put('xdut.xcdac.bn0',.9 if 43.6<=ns<48.4 else 0)
            put('xdut.xcdac.bp0',0 if 43.6<=ns<49 else .9)
            # Exact terminal/bottom incidences for parser testing, no IV model.
            for side,parts,cap in [('n',[(6,-.6,-5,-.4),(-7,-.2,7.5,-.3)],1),('p',[(1,-.3,-.01,-.69),(-5,-.2,5.5,-.3)],4)]:
                for dev,ports in zip(['mn_low','mp_high'],parts):
                    for j,x in enumerate(ports,1):put('xdut.xcdac.xs'+side+'0.'+dev+':'+str(j),x*1e-6)
                put('xdut.xcdac.cmom'+side+'0:2',cap*1e-6)
            for n,x in [('xdut.gnncn:2',1e-6),('xdut.gnncp:2',2e-6),('xdut.x025.xlib.mm1:1',-2e-6),('xdut.x025.xlib.mm0:1',-1e-6)]:put(n,x)
            rows.append((ns*1e-9,values))
        rows[-1]=(52e-9,rows[-1][1])
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for f in read(out/'sscold/recipe_proposal.json')['inputs']:shutil.copyfile(ROOT/f['source'],run/'inputs'/f['name'])
            (run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n')
            (run/'spectre.out').write_text('SYNTHETIC PARSER/MEASUREMENT CONTRACT CHECK; NOT A CIRCUIT SIMULATION\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            p=subprocess.run([sys.executable,'-B',str(run/'inputs/gnn_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            r=read(run/'derived/result.json');m=r['cell_measurements'];q=m['GNN_single_IO_actual_measurements']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual(len(r['selected_mos_pair_extrema']),714)
            self.assertFalse(m['removed_A_B_stage_measurements']['applicable']);self.assertNotIn('GNN_AB_IO_direct_VDD_energy_J',m)
            self.assertEqual(q['PRE_load_and_internal_work']['actual_PRE_load_ports'],['xdut.gnncn:2','xdut.gnncp:2'])
            self.assertLess(q['PRE_load_and_internal_work']['max_PRE_KCL_A'],1e-20)
            self.assertLess(abs(q['PRE_load_and_internal_work']['internal_work_closure_residual_J']),1e-24)
            for phase in ['select_high','select_low']:
                x=q['reference_port_phases'][phase]
                self.assertAlmostEqual(x['source_exchange']['N']['peak_A'],5e-6,delta=1e-18)
                self.assertAlmostEqual(x['source_exchange']['P']['peak_A'],.01e-6,delta=1e-18)
                self.assertAlmostEqual(x['opposed_D']['N']['peak_A'],6e-6,delta=1e-18)
                self.assertAlmostEqual(x['source_exchange']['N']['peak']['devices']['mn_low']['DGSB_current_A']['S'],-5e-6,delta=1e-18)
            self.assertEqual(set(q['actual_final_IO_and_X025_terminal_peaks']),{'XDUT.GNNCN','XDUT.GNNCP','XDUT.X025.XLIB.MM1','XDUT.X025.XLIB.MM0'})
            self.assertTrue(all(x['coincident'] is not None for x in q['actual_final_IO_and_X025_terminal_peaks'].values()))
            self.assertIsNone(q['channel_overlap_duration_s']);self.assertFalse(q['startup_history']['physical_supply_ramp_startup_qualified'])
            self.assertEqual(len(m['all_terminal_native_phase_time']['phases']['full']['pairs']),714)
            native=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz')
            self.assertEqual(len(native['columns']),421);self.assertFalse(set(native['columns'])&{'xdut.gnna','xdut.gnnb'})


if __name__=='__main__':unittest.main()
