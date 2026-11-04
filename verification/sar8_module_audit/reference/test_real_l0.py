"""One focused original-driver/fanout and executable native-measurement check."""
import copy,hashlib,json,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,ports,flatten
from prepare_real_l0 import original_boundary
from real_l0_analyze import validate
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/gpp_single_io_v1';NEW=HERE/'generated/real_l0_v1'


class RealL0Test(unittest.TestCase):
    def test_exact_stage_all_fanout_unaligned_command_and_native_measurement(self):
        def flat(path):
            d=definitions(path.read_text());return flatten(d,'sar8_realpre_unit',{n:'VDD!' if n=='VDD' else '0' if n=='VSS' else n for n in ports(d['sar8_realpre_unit'])})
        before,after=flat(OLD/'dut.scs'),flat(NEW/'dut.scs');self.assertEqual(set(after)-set(before),{'XDUT.L0SRC.MN','XDUT.L0SRC.MP'})
        self.assertEqual(len(before),142)
        for n,x in before.items():self.assertEqual(after[n],dict(x,nodes=['XDUT.L0' if p=='L0' else p for p in x['nodes']]))
        for kind in ['MN','MP']:
            x,y=after['XDUT.L0SRC.'+kind],before['XDUT.X025.'+kind]
            self.assertEqual((x['model'],x['parameters']),(y['model'],y['parameters']))
            self.assertEqual(x['nodes'][:2],['XDUT.L0','L0N'])
        proof,_=original_boundary();self.assertEqual(json.loads((NEW/'l0_boundary.json').read_text()),proof)
        self.assertEqual(len(proof['original_output_incident_ports']),6);self.assertEqual(len(proof['original_input_incident_ports']),5)
        incidence={n+':'+str(j) for n,x in after.items() for j,node in enumerate(x['nodes'],1) if node=='XDUT.L0'}
        self.assertEqual(incidence,{'XDUT.L0SRC.MN:1','XDUT.L0SRC.MP:1','XDUT.X025.MN:2','XDUT.X025.MP:2','XDUT.GPPIN:2','XDUT.GPPIP:2'})
        for case in json.loads((NEW/'package_review.json').read_text())['cases']:
            folder=(ROOT/case['recipe']).parent;cfg=json.loads((folder/'measurement.json').read_text());v,i,k=validate(cfg)
            self.assertEqual((len(v),len(i),len(k)),(565,470,13));self.assertEqual(len(cfg['selected_mos_pair_screens']),486)
            self.assertEqual(len(k['xdut.l0']),6);self.assertEqual(len(k['l0n']),3)
            def static(p):return [x for x in p.read_text().splitlines() if not x.startswith(('save ','XDUT ','VL0 ' ,'VL0N '))]
            self.assertEqual(static(folder/'test.scs'),static(OLD/folder.name/'test.scs'))
            def wave(p,stem):return [float(x) for x in re.search(r'(?m)^'+stem+r'.*wave=\[(.*?)\]',p.read_text())[1].split()]
            a,b=wave(OLD/folder.name/'test.scs','VL0 '),wave(folder/'test.scs','VL0N ')
            self.assertEqual(a[::2],b[::2])
            for x,y in zip(a[1::2],b[1::2]):self.assertAlmostEqual(x+y,cfg['supply_V'],places=15)
            self.assertEqual({q['screen_v'] for q in cfg['selected_mos_pair_screens'] if '.L0SRC.' in q['instance'] or '.X025.' in q['instance']},{.99})
            self.assertEqual(case['recipe_sha256'],hashlib.sha256((folder/'recipe_proposal.json').read_bytes()).hexdigest())
            for x in case['files']:
                data=(ROOT/x['source']).read_bytes();self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(x['bytes'],x['sha256']))
        cfg=json.loads((NEW/'ffcold/measurement.json').read_text());bad=copy.deepcopy(cfg)
        next(x for x in bad['selected_mos_pair_screens'] if '.L0SRC.' in x['instance'])['screen_v']=1.98
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(cfg);bad['source_current']='vl0:1'
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir();recipe=json.loads((NEW/'ffcold/recipe_proposal.json').read_text())
            for x in recipe['inputs']:shutil.copyfile(ROOT/x['source'],run/'inputs'/x['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            times=[0,41.5,42.5,42.99,43,43.02,43.04,43.06,43.08,43.1,43.12,43.14,43.16,43.2,44,44.2,45,46,46.99,47,47.2,47.99,48,48.02,48.04,48.06,48.08,48.1,48.12,48.14,48.16,48.2,48.3,50,51.5,52]
            for ns in times:
                values={n:0. for n in names.values()}
                def put(n,v):values[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('l0n',.99 if 43<=ns<48 else 0)
                put('xdut.l0',0 if 43.02<=ns<48.02 else .99)
                if ns==42.99:put('xdut.l0',1.07)
                if ns==48.02:put('xdut.l0',-.02)
                put('vrefp',.9);put('xdut.pre',.99 if 43.04<=ns<48.04 else 0)
                if ns==43.04:put('xdut.pre',1.05)
                if ns==48.04:put('xdut.pre',-.03)
                put('xdut.gnna',0 if 43.06<=ns<48.06 else .99);put('xdut.gnnb',.99 if 43.08<=ns<48.08 else 0)
                put('xdut.gnndrv',0 if 43.10<=ns<48.10 else .99);put('xdut.gnn0',0 if 43.12<=ns<48.12 else .99)
                put('xdut.gppdrv',.99 if 43.08<=ns<48.08 else 0);put('xdut.gpp0',.99 if 43.10<=ns<48.10 else 0)
                put('xdut.gnp0',0 if 44<=ns<47 else .99);put('xdut.gpn0',.99 if 44<=ns<47 else 0)
                put('xdut.xcdac.bn0',.9 if 44.2<=ns<48.3 else 0);put('xdut.xcdac.bp0',0 if 44.2<=ns<48.3 else .9)
                for n,i in [('xdut.x025.mn:2',1e-6),('xdut.x025.mp:2',2e-6),('xdut.gppin:2',3e-6),('xdut.gppip:2',4e-6),
                    ('xdut.l0src.mn:1',-6e-6),('xdut.l0src.mp:1',-4e-6),('xdut.l0src.mn:2',1e-6),('xdut.l0src.mp:2',2e-6),('vl0n:1',-3e-6),('xdut.l0src.mp:3',5e-6),
                    ('xdut.gnnan:2',1e-6),('xdut.gnnap:2',2e-6),('xdut.x025.mn:1',-1e-6),('xdut.x025.mp:1',-2e-6),('xdut.l0src.mn:4',2e-9),('xdut.gppip:3',4e-6),
                    ('xdut.xcdac.xsn0.mn_low:1',2e-6),('xdut.xcdac.xsn0.mp_high:1',-1e-6),('xdut.xcdac.xsp0.mn_low:1',-3e-6),('xdut.xcdac.xsp0.mp_high:1',4e-6)]:put(n,i)
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows));(run/'raw/logStatus').write_text('tran_cell PASS\n')
            (run/'spectre.out').write_text('synthetic mapping fixture only\n');(run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/real_l0_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements'];work=m['source_and_internal_work']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual((r['selected_current_count'],len(r['selected_mos_pair_extrema'])),(470,486))
            self.assertAlmostEqual(r['selected_mos_pair_extrema']['XDUT.L0SRC.MN:ds']['max'],1.07)
            self.assertAlmostEqual(r['selected_mos_pair_extrema']['XDUT.X025.MN:ds']['max'],1.05)
            self.assertAlmostEqual(m['restored_stage_direct_VDD_energy_J']['L0_original_core_driver'],.99*5e-6*52e-9,places=24)
            self.assertLess(abs(work['N_source_minus_gate_work_J']),1e-24);self.assertLess(abs(work['source_minus_L0_load_work_J']),1e-24)
            self.assertGreater(work['N_source_net_delivered_J'],0);self.assertGreater(work['L0_net_delivered_J'],work['N_source_net_delivered_J'])
            self.assertLess(abs(work['X025_to_A_internal_work_residual_J']),1e-24)
            self.assertEqual(len(m['body_forward_polarity']),162);self.assertAlmostEqual(m['supply_rail_excursions']['xdut.l0']['below_ground_V'],.02)
            self.assertGreater(m['actual_stage_timing']['enable_low']['N_to_L0_s'],0)
            self.assertEqual(m['real_PRE_and_L0_loads']['N_input_gates']['gate_port_branches'],['xdut.l0src.mn:2','xdut.l0src.mp:2'])
            self.assertTrue(all(x['remained_inside_from_native_s'] is not None for phase in m['correct_ON_settling'].values() for x in phase.values()))
            native=next(x for x in r['native_exports'] if x['file']=='cell.native.f64le.gz');self.assertEqual((native['rows'],len(native['columns'])),(len(rows),142))


if __name__=='__main__':unittest.main()
