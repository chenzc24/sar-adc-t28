"""One full-BBM mapping and staged measurement check, including missing edges."""
import copy,hashlib,json,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,ports,flatten
from prepare_real_bbm import inventory
from real_bbm_analyze import validate,measurements
import io_cell_analyze as cell
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/real_l0_v1';NEW=HERE/'generated/real_bbm_v1'


class RealBBMTest(unittest.TestCase):
    def test_complete_original_bbm_high_driver_mapping_and_native_missing_nonsettling(self):
        def flat(p):
            d=definitions(p.read_text());return flatten(d,'sar8_realpre_unit',{n:'VDD!' if n=='VDD' else '0' if n=='VSS' else n for n in ports(d['sar8_realpre_unit'])})
        old,new=flat(OLD/'dut.scs'),flat(NEW/'dut.scs');self.assertEqual(len(new),196)
        for n,x in old.items():
            if '.L0SRC.' in n:continue
            self.assertEqual(new[n],dict(x,nodes=[{'GNPDRV':'XDUT.GNPDRV','GPNDRV':'XDUT.GPNDRV'}.get(p,p) for p in x['nodes']]))
        native,_,proof=inventory();self.assertEqual(proof,json.loads((NEW/'bbm_boundary.json').read_text()))
        bbm=flatten(native,'sar8p_nonoverlap',{'CODE':'CODE','H':'XDUT.H0','L':'XDUT.L0','VDD':'VDD!','VSS':'0'},prefix='XDUT.XBBM0')
        self.assertEqual({n:x for n,x in new.items() if n.startswith('XDUT.XBBM0.')},bbm);self.assertEqual(len(bbm),40)
        orig_driver=flatten(native,'sar8p_refdrv_b0',{'GNN':'XDUT.GNN0','GNP':'XDUT.GNP0','GPN':'XDUT.GPN0','GPP':'XDUT.GPP0','H':'XDUT.H0','L':'XDUT.L0','VDD':'VDD!','VSS':'0'})
        high={n:x for n,x in orig_driver.items() if re.fullmatch(r'XDUT.G(?:NP|PN)[ABC][NP]',n) or n.startswith('XDUT.X008.')}
        self.assertEqual(len(high),14)
        for n,x in high.items():self.assertEqual(new[n],x)
        for kind in ['MN','MP']:
            x=old['XDUT.L0SRC.'+kind];self.assertEqual(new['XDUT.XBBM0.X004.X001.'+kind],dict(x,nodes=['XDUT.XBBM0.X004.N' if p=='L0N' else p for p in x['nodes']]))
        for case in json.loads((NEW/'package_review.json').read_text())['cases']:
            folder=(ROOT/case['recipe']).parent;cfg=json.loads((folder/'measurement.json').read_text());v,i,k=validate(cfg)
            self.assertEqual((len(v),len(i),len(k)),(772,656,36));self.assertEqual(len(cfg['selected_mos_pair_screens']),738)
            self.assertEqual(len(k['code']),9);self.assertEqual(len(k['xdut.h0']),6);self.assertEqual(len(k['xdut.l0']),6)
            def prefix(p):return [x for x in p.read_text().splitlines() if not x.startswith(('save ','XDUT ','VL0N ','VCODE ','VGNP ','VGPN '))]
            self.assertEqual(prefix(folder/'test.scs'),prefix(OLD/folder.name/'test.scs'))
            def wave(p,n):return re.search(r'(?m)^'+n+r'.*wave=\[(.*?)\]',p.read_text())[1]
            self.assertEqual(wave(folder/'test.scs','VCODE '),wave(OLD/folder.name/'test.scs','VL0N '))
            self.assertFalse(any(x.startswith(('VL0N ','VGNP ','VGPN ')) for x in (folder/'test.scs').read_text().splitlines()))
            self.assertEqual(case['recipe_sha256'],hashlib.sha256((folder/'recipe_proposal.json').read_bytes()).hexdigest())
            for x in case['files']:
                b=(ROOT/x['source']).read_bytes();self.assertEqual((len(b),hashlib.sha256(b).hexdigest()),(x['bytes'],x['sha256']))
        cfg=json.loads((NEW/'ffcold/measurement.json').read_text());bad=copy.deepcopy(cfg)
        next(x for x in bad['selected_mos_pair_screens'] if x['instance'].startswith('XDUT.XBBM0.'))['screen_v']=1.98
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for x in json.loads((NEW/'ffcold/recipe_proposal.json').read_text())['inputs']:shutil.copyfile(ROOT/x['source'],run/'inputs'/x['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            times=[0,41.5,42.9,42.995,43,43.005,43.05,43.1,43.15,43.2,43.25,43.3,43.35,43.4,43.45,43.5,43.6,44,44.2,45,46,47,47.9,47.995,48,48.005,48.05,48.1,48.15,48.2,48.25,48.3,48.35,48.4,48.45,48.5,48.6,49,49.5,50,51,51.5,52]
            code_loads=[b.lower() for b,x in cfg['terminal_current_catalog'].items() if x['node']=='CODE' and b!='VCODE:1']
            for ns in times:
                values={n:0. for n in names.values()}
                def put(n,v):values[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('code',.495 if ns in [43,48] else .99 if 43<ns<48 else 0);put('vrefp',.9)
                put('xdut.h0',.99 if 43.2<=ns<48.2 else 0);put('xdut.l0',0 if 43.1<=ns<48.3 else .99)
                put('xdut.pre',.99 if 43.2<=ns<48.4 else 0);put('xdut.gpnpre',0 if 43.3<=ns<48.3 else .99)
                put('xdut.gnna',0 if 43.3<=ns<48.45 else .99);put('xdut.gnnb',.99 if 43.35<=ns<48.5 else 0);put('xdut.gnndrv',0 if 43.4<=ns<48.55 else .99)
                put('xdut.gnn0',0 if 43.25<=ns<48.5 else .99);put('xdut.gpp0',.99 if 43.15<=ns<48.4 else 0)
                put('xdut.gnp0',0 if 43.4<=ns<48.3 else .99);put('xdut.gpn0',.99 if 43.45<=ns<48.25 else 0)
                put('xdut.gnpdrv',0 if 43.35<=ns<48.25 else .99);put('xdut.gpndrv',.99 if 43.4<=ns<48.2 else 0)
                put('xdut.gppdrv',.99 if 43.1<=ns<48.35 else 0)
                put('xdut.xcdac.bn0',.9 if ns>=44.2 else 0);put('xdut.xcdac.bp0',0 if 44.2<=ns<49 else .9)
                if ns==43.2:put('xdut.xbbm0.x004.n',1.07)
                for b,x in cfg['terminal_current_catalog'].items():
                    if x['model'].startswith('pch') and x['port']==3 and x['node']=='VDD!':put(b.lower(),1e-6)
                for j,b in enumerate(code_loads,1):put(b,j*1e-6)
                put('vcode:1',-sum(range(1,len(code_loads)+1))*1e-6)
                for n,i in [('xdut.xbbm0.x004.x001.mn:1',-6e-6),('xdut.xbbm0.x004.x001.mp:1',-4e-6),('xdut.x025.mn:2',1e-6),('xdut.x025.mp:2',2e-6),('xdut.gppin:2',3e-6),('xdut.gppip:2',4e-6),
                    ('xdut.xbbm0.x002.x001.mn:1',-6e-6),('xdut.xbbm0.x002.x001.mp:1',-4e-6),('xdut.gnpan:2',1e-6),('xdut.gnpap:2',2e-6),('xdut.x008.mn:2',3e-6),('xdut.x008.mp:2',4e-6),
                    ('xdut.x025.mn:1',-1e-6),('xdut.x025.mp:1',-2e-6),('xdut.gnnan:2',1e-6),('xdut.gnnap:2',2e-6),
                    ('xdut.x008.mn:1',-1e-6),('xdut.x008.mp:1',-2e-6),('xdut.gpnan:2',1e-6),('xdut.gpnap:2',2e-6),
                    ('xdut.xcdac.xsn0.mn_low:1',2e-6),('xdut.xcdac.xsn0.mp_high:1',-1e-6),('xdut.xcdac.xsp0.mn_low:1',-3e-6),('xdut.xcdac.xsp0.mp_high:1',4e-6)]:put(n,i)
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n');(run/'spectre.out').write_text('synthetic native measurement test only\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/real_bbm_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual((r['selected_current_count'],len(r['selected_mos_pair_extrema'])),(656,738))
            self.assertIn('all36 declared KCL nodes',r['waveform_note'])
            self.assertAlmostEqual(r['selected_mos_pair_extrema']['XDUT.XBBM0.X004.X000.MN0:ds']['max'],1.07)
            self.assertEqual(len(m['body_forward_polarity']),246);self.assertEqual(m['actual_correct_ON_settling']['select_low']['status'],'observed_window')
            self.assertFalse(m['actual_correct_ON_settling']['select_low']['nodes']['xdut.xcdac.bn0']['established_within_window'])
            self.assertTrue(m['actual_correct_ON_settling']['select_high']['nodes']['xdut.xcdac.bn0']['established_within_window'])
            self.assertAlmostEqual(m['reference_control_direct_VDD_energy_J']['BBM'],15*.99*1e-6*52e-9,places=23)
            self.assertLess(abs(m['CODE_source_and_input_load']['source_minus_load_work_J']),1e-23)
            self.assertTrue(all(abs(x['work_closure_residual_J'])<1e-23 for x in m['internal_driver_load_work'].values()))
            self.assertGreater(m['opposed_total_reference_terminal_current']['N']['peak_min_opposed_abs_A'],0)
            self.assertEqual(m['sampled_HL_mutual_exclusion']['HL_both_above_halfVDD_duration_s'],0.)
            export=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');self.assertEqual((export['rows'],len(export['columns'])),(len(rows),376))
            missing=copy.deepcopy(r);missing['half_vdd_events']['xdut.gpn0']=[];mm=measurements(cell.metrics,missing,cfg,str(run/'derived'))
            self.assertIn('xdut.gpn0',mm['actual_control_events']['select_low']['missing_or_ambiguous_nodes'])
            self.assertEqual(mm['actual_correct_ON_settling']['select_low']['status'],'missing_or_ambiguous_controls')
            self.assertIsNone(mm['actual_correct_ON_settling']['select_low']['nodes']['xdut.xcdac.bn0']['established_within_window'])


if __name__=='__main__':unittest.main()
