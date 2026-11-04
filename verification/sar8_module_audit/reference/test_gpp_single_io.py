"""One focused driver-block mapping and staged native-measurement check."""
import copy,hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,ports,flatten
from gpp_single_io_analyze import validate
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/real_pre_v1';NEW=HERE/'generated/gpp_single_io_v1'


class SingleIOGPPTest(unittest.TestCase):
    def test_one_block_change_core_X025_retained_and_measurement_mapping(self):
        def flat(path):
            d=definitions(path.read_text());pins=ports(d['sar8_realpre_unit']);return flatten(d,'sar8_realpre_unit',{n:'VDD!' if n=='VDD' else '0' if n=='VSS' else n for n in pins})
        old,new=flat(OLD/'dut.scs'),flat(NEW/'dut.scs')
        self.assertEqual(set(old)-set(new),{'XDUT.GPP'+s+t for s in ['A','B','C'] for t in ['N','P']})
        self.assertEqual(set(new)-set(old),{'XDUT.GPPIN','XDUT.GPPIP'})
        self.assertEqual(len(set(old)&set(new)),140)
        for n in set(old)&set(new):self.assertEqual(old[n],new[n])
        for name,template,rail in [('GPPIN','GNNCN','0'),('GPPIP','GNNCP','VDD!')]:
            a,b=new['XDUT.'+name],old['XDUT.'+template]
            self.assertEqual((a['model'],a['parameters']),(b['model'],b['parameters']))
            self.assertEqual(a['nodes'],['XDUT.GPPDRV','L0',rail,rail])
        l0={n+':'+str(j) for n,d in new.items() for j,node in enumerate(d['nodes'],1) if node=='L0'}
        self.assertEqual(l0,{'XDUT.X025.MN:2','XDUT.X025.MP:2','XDUT.GPPIN:2','XDUT.GPPIP:2'})
        receipt=json.loads((NEW/'package_review.json').read_text());self.assertEqual(len(receipt['cases']),2)
        for case in receipt['cases']:
            folder=(ROOT/case['recipe']).parent;cfg=json.loads((folder/'measurement.json').read_text());sel,cur,kcl=validate(cfg)
            self.assertEqual((len(sel),len(cur),len(kcl)),(556,462,12));self.assertEqual(len(cfg['selected_mos_pair_screens']),474)
            def prefix(p):return '\n'.join(x for x in p.read_text().splitlines() if not x.startswith('save '))
            self.assertEqual(prefix(folder/'test.scs'),prefix(OLD/folder.name/'test.scs'))
            self.assertFalse({'xdut.gppa','xdut.gppb'}&set(cfg['diagnostic_voltage_columns']))
            self.assertEqual({p['screen_v'] for p in cfg['selected_mos_pair_screens'] if p['instance'].startswith('XDUT.X025.')},{.99})
            self.assertEqual({p['screen_v'] for p in cfg['selected_mos_pair_screens'] if p['instance'] in ['XDUT.GPPIN','XDUT.GPPIP']},{1.98})
            for x in case['files']:
                data=(ROOT/x['source']).read_bytes();self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(x['bytes'],x['sha256']))
        folder=NEW/'ffcold';cfg=json.loads((folder/'measurement.json').read_text());bad=copy.deepcopy(cfg)
        next(x for x in bad['selected_mos_pair_screens'] if x['instance']=='XDUT.X025.MN')['screen_v']=1.98
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir();recipe=json.loads((folder/'recipe_proposal.json').read_text())
            for x in recipe['inputs']:shutil.copyfile(ROOT/x['source'],run/'inputs'/x['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            times=[0,41.5,42.5,42.99,43,43.02,43.04,43.06,43.08,43.10,43.2,44,44.2,45,46,46.99,47,47.2,47.99,48,48.02,48.04,48.06,48.08,48.10,48.2,48.3,50,51.5,52]
            for ns in times:
                values={n:0. for n in names.values()}
                def put(n,v):values[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('l0',0 if 43<=ns<48 else .99);put('vrefp',.9)
                put('xdut.pre',.99 if 43.02<=ns<48.02 else 0)
                if ns==43.02:put('xdut.pre',1.05)
                if ns==48.02:put('xdut.pre',-.03)
                put('xdut.gnna',0 if 43.04<=ns<48.04 else .99);put('xdut.gnnb',.99 if 43.06<=ns<48.06 else 0)
                put('xdut.gnndrv',0 if 43.08<=ns<48.08 else .99);put('xdut.gnn0',0 if 43.10<=ns<48.10 else .99)
                put('xdut.gppdrv',.99 if 43.06<=ns<48.06 else 0);put('xdut.gpp0',.99 if 43.08<=ns<48.08 else 0)
                put('xdut.gnp0',0 if 44<=ns<47 else .99);put('xdut.gpn0',.99 if 44<=ns<47 else 0)
                put('xdut.xcdac.bn0',.9 if 44.2<=ns<48.3 else 0);put('xdut.xcdac.bp0',0 if 44.2<=ns<48.3 else .9)
                for n,i in [('xdut.x025.mn:2',1e-6),('xdut.x025.mp:2',2e-6),('xdut.gppin:2',3e-6),('xdut.gppip:2',4e-6),('vl0:1',-10e-6),
                    ('xdut.gnnan:2',1e-6),('xdut.gnnap:2',2e-6),('xdut.x025.mn:1',-1e-6),('xdut.x025.mp:1',-2e-6),('xdut.x025.mn:4',2e-9),('xdut.gppip:3',5e-6),
                    ('xdut.xcdac.xsn0.mn_low:1',2e-6),('xdut.xcdac.xsn0.mp_high:1',-1e-6),('xdut.xcdac.xsp0.mn_low:1',-3e-6),('xdut.xcdac.xsp0.mp_high:1',4e-6)]:put(n,i)
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n')
            (run/'spectre.out').write_text('synthetic mapping fixture only\n');(run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/gpp_single_io_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements'];work=m['source_and_internal_work']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual((r['selected_current_count'],len(r['selected_mos_pair_extrema'])),(462,474))
            self.assertAlmostEqual(r['selected_mos_pair_extrema']['XDUT.X025.MN:ds']['max'],1.05)
            self.assertEqual(set(m['restored_stage_direct_VDD_energy_J']),{'GNN_A','GNN_B','GNN_C','GPP_single_IO','X025'})
            self.assertAlmostEqual(m['restored_stage_direct_VDD_energy_J']['GPP_single_IO'],.99*5e-6*52e-9,places=24)
            self.assertAlmostEqual(work['L0_net_delivered_J'],.99*10e-6*47e-9,places=23)
            self.assertLess(abs(work['source_minus_L0_load_work_J']),1e-24);self.assertLess(abs(work['X025_to_A_internal_work_residual_J']),1e-24)
            self.assertEqual(len(m['body_forward_polarity']),158);self.assertAlmostEqual(m['supply_rail_excursions']['xdut.pre']['below_ground_V'],.03)
            self.assertAlmostEqual(m['actual_stage_timing']['disable_low']['GNN_after_GPP_control_skew_s'],20e-12,places=20)
            self.assertTrue(all(x['remained_inside_from_native_s'] is not None for phase in m['correct_ON_settling'].values() for x in phase.values()))
            primary=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');self.assertEqual((primary['rows'],len(primary['columns'])),(len(rows),132))


if __name__=='__main__':unittest.main()
