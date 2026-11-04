"""One restoration/shared-load/no-forcing/native-measurement mapping test."""
import hashlib,json,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,instances,ports,flatten
from real_pre_analyze import validate
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/io_astage_v1';NEW=HERE/'generated/real_pre_v1'


class RealPREMappingTest(unittest.TestCase):
    def test_restored_native_driver_shared_load_no_forcing_and_measurements(self):
        old=definitions((OLD/'dut.scs').read_text());new=definitions((NEW/'dut.scs').read_text());native=definitions((ROOT/'output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs').read_text())
        def flat(defs,master):return flatten(defs,master,{p:'VDD!' if p=='VDD' else '0' if p=='VSS' else p for p in ports(defs[master])})
        a,b=flat(old,'sar8_refcell_unit'),flat(new,'sar8_realpre_unit');mapping={'PRE':'XDUT.PRE','GPPDRV':'XDUT.GPPDRV'}
        for n,d in a.items():self.assertEqual(b[n],dict(d,nodes=[mapping.get(x,x) for x in d['nodes']]))
        self.assertEqual(len(b)-len(a),8);self.assertEqual(new['sar8p_inv'],native['sar8p_inv'])
        rows={n:(nodes,m,' '.join(p.split())) for n,nodes,m,p in instances(native['sar8p_refdrv_b0'])}
        for n in ['GPPAN','GPPAP','GPPBN','GPPBP','GPPCN','GPPCP']:
            args,m,p=rows[n];self.assertEqual(b['XDUT.'+n]['model'],m);self.assertEqual(b['XDUT.'+n]['parameters'],p)
        l0={n+':'+str(j) for n,d in b.items() for j,node in enumerate(d['nodes'],1) if node=='L0'}
        self.assertEqual(l0,{'XDUT.X025.MN:2','XDUT.X025.MP:2','XDUT.GPPAN:2','XDUT.GPPAP:2'})
        self.assertEqual(b['XDUT.GPPCN']['nodes'][0],'XDUT.GPPDRV');self.assertEqual(b['XDUT.RGPP0']['nodes'][0],'XDUT.GPPDRV')
        receipt=json.loads((NEW/'package_review.json').read_text());self.assertEqual(len(receipt['cases']),2)
        for case in receipt['cases']:
            folder=(ROOT/case['recipe']).parent;cfg=json.loads((folder/'measurement.json').read_text());sel,cur,kcl=validate(cfg)
            self.assertEqual((len(sel),len(cur),len(kcl)),(574,478,14));self.assertEqual(len(cfg['selected_mos_pair_screens']),498)
            text=(folder/'test.scs').read_text();self.assertNotIn('VPRE (',text);self.assertNotIn('VGPP (',text);self.assertIn('VL0 (L0 0)',text)
            src={m[1]:(m[2].split()[0],m[3]) for m in re.finditer(r'(?m)^(\w+) \(([^)]*)\) (vsource) ',text)}
            self.assertFalse(any(node in ['PRE','XDUT.PRE','GPPDRV','XDUT.GPPDRV'] for node,_ in src.values()))
            for n in ['VSAMPLE','VGNP','VGPN','VVINN','VVINP','VREFLOW','VREFHIGH','RREFN','RREFP','RINN','RINP','CREFN','CREFP','simulatorOptions']:
                self.assertEqual(re.search(r'(?m)^'+n+r' .+$',text)[0],re.search(r'(?m)^'+n+r' .+$',(OLD/folder.name/'test.scs').read_text())[0])
            self.assertTrue(all(p['screen_v']==.99 for p in cfg['selected_mos_pair_screens'] if p['instance'].startswith('XDUT.X025.') or re.fullmatch('XDUT.GPP[ABC][NP]',p['instance'])))
            for item in case['files']:
                data=(ROOT/item['source']).read_bytes();self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(item['bytes'],item['sha256']))
        folder=NEW/'ffcold';cfg=json.loads((folder/'measurement.json').read_text());recipe=json.loads((folder/'recipe_proposal.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for x in recipe['inputs']:shutil.copyfile(ROOT/x['source'],run/'inputs'/x['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            times=[0,41.5,42.5,42.99,43,43.02,43.04,43.06,43.08,43.10,43.15,43.2,44,44.2,45,46,46.99,47,47.2,47.99,48,48.02,48.04,48.06,48.08,48.10,48.15,48.2,48.3,50,51.5,52]
            for ns in times:
                values={n:0. for n in names.values()}
                def put(n,v):values[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('l0',0 if 43<=ns<48 else .99);put('vrefp',.9)
                put('xdut.pre',.99 if 43.02<=ns<48.02 else 0)
                if ns==43.02:put('xdut.pre',1.05)
                if ns==48.02:put('xdut.pre',-.03)
                put('xdut.gnna',0 if 43.04<=ns<48.04 else .99);put('xdut.gnnb',.99 if 43.06<=ns<48.06 else 0)
                put('xdut.gnndrv',0 if 43.08<=ns<48.08 else .99);put('xdut.gnn0',0 if 43.10<=ns<48.10 else .99)
                for n,a,z,high in [('xdut.gppa',43.02,48.02,True),('xdut.gppb',43.04,48.04,False),('xdut.gppdrv',43.06,48.06,True),('xdut.gpp0',43.08,48.08,True)]:put(n,.99 if ((a<=ns<z)==high) else 0)
                put('xdut.gnp0',0 if 44<=ns<47 else .99);put('xdut.gpn0',.99 if 44<=ns<47 else 0)
                put('xdut.xcdac.bn0',.9 if 44.2<=ns<48.3 else 0);put('xdut.xcdac.bp0',0 if 44.2<=ns<48.3 else .9)
                for n,i in [('xdut.x025.mn:2',1e-6),('xdut.x025.mp:2',2e-6),('xdut.gppan:2',3e-6),('xdut.gppap:2',4e-6),('vl0:1',-10e-6),
                    ('xdut.gnnan:2',1e-6),('xdut.gnnap:2',2e-6),('xdut.x025.mn:1',-1e-6),('xdut.x025.mp:1',-2e-6),('xdut.x025.mn:4',2e-9),
                    ('xdut.xcdac.xsn0.mn_low:1',2e-6),('xdut.xcdac.xsn0.mp_high:1',-1e-6),('xdut.xcdac.xsp0.mn_low:1',-3e-6),('xdut.xcdac.xsp0.mp_high:1',4e-6)]:put(n,i)
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n')
            (run/'spectre.out').write_text('synthetic interface test only\n');(run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/real_pre_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements'];work=m['source_and_internal_work']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual((r['selected_current_count'],len(r['selected_mos_pair_extrema'])),(478,498))
            self.assertAlmostEqual(r['selected_mos_pair_extrema']['XDUT.X025.MN:ds']['max'],1.05)
            self.assertAlmostEqual(work['L0_net_delivered_J'],.99*10e-6*47e-9,places=23)
            self.assertLess(abs(work['source_minus_L0_load_work_J']),1e-24);self.assertLess(abs(work['X025_to_A_internal_work_residual_J']),1e-24)
            self.assertEqual(len(m['body_forward_polarity']),166);self.assertAlmostEqual(m['supply_rail_excursions']['xdut.pre']['below_ground_V'],.03)
            self.assertAlmostEqual(m['actual_stage_timing']['disable_low']['GNN_after_GPP_control_skew_s'],20e-12,places=20)
            self.assertEqual(m['opposed_reference_terminal_current']['N']['peak_min_opposed_abs_A'],1e-6)
            self.assertTrue(all(x['remained_inside_from_native_s'] is not None for phase in m['correct_ON_settling'].values() for x in phase.values()))
            primary=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');self.assertEqual((primary['rows'],len(primary['columns'])),(len(rows),152))


if __name__=='__main__':unittest.main()
