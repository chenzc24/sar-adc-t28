"""One minimal A mapping / PRE-work / body-polarity interface test."""
import copy,hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,ports,flatten
from io_astage_analyze import validate
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/io_bstage_v1';NEW=HERE/'generated/io_astage_v1'


class AStageMappingTest(unittest.TestCase):
    def test_A_only_full_IO_mapping_PRE_work_and_signed_junctions(self):
        defs=definitions((OLD/'dut.scs').read_text());pins=ports(defs['sar8_refcell_unit']);binding={n:n for n in pins};binding.update(VDD='VDD!',VSS='0')
        before=flatten(defs,'sar8_refcell_unit',binding);after=flatten(definitions((NEW/'dut.scs').read_text()),'sar8_refcell_unit',binding)
        self.assertEqual({n for n in before if before[n]!=after[n]},{'XDUT.GNNAN','XDUT.GNNAP'})
        for t in ['N','P']:
            self.assertEqual((after['XDUT.GNNA'+t]['model'],after['XDUT.GNNA'+t]['parameters']),
                             (before['XDUT.GNNC'+t]['model'],before['XDUT.GNNC'+t]['parameters']))
            self.assertEqual(after['XDUT.GNNA'+t]['nodes'],before['XDUT.GNNA'+t]['nodes'])
        receipt=json.loads((NEW/'package_review.json').read_text());self.assertEqual(len(receipt['cases']),2)
        for case in receipt['cases']:
            path=ROOT/case['recipe'];folder=path.parent;cfg=json.loads((folder/'measurement.json').read_text());old=json.loads((OLD/folder.name/'measurement.json').read_text())
            self.assertEqual((folder/'test.scs').read_bytes(),(OLD/folder.name/'test.scs').read_bytes());self.assertEqual(len(validate(cfg)[0]),540)
            self.assertEqual(cfg['kcl_terms'],old['kcl_terms']);self.assertEqual(len(cfg['selected_mos_pair_screens']),450)
            prev={p['instance']+':'+p['terminal']:p for p in old['selected_mos_pair_screens']}
            for p in cfg['selected_mos_pair_screens']:
                if p['instance'] in ['XDUT.GNNAN','XDUT.GNNAP']:self.assertEqual((p['model'],p['screen_v']),(after[p['instance']]['model'],1.98))
                else:self.assertEqual(p,prev[p['instance']+':'+p['terminal']])
            for x in case['files']:
                data=(ROOT/x['source']).read_bytes();self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(x['bytes'],x['sha256']))
        boundary=json.loads((HERE/'pre_driver_boundary.json').read_text())
        self.assertEqual(boundary['original_driver_instance'],'XDUT.XREF.XDRV0.X025');self.assertEqual(len(boundary['PRE_node_incident_ports']),4)
        self.assertEqual(len(boundary['upstream_incident_ports']),6)
        folder=NEW/'ffcold';cfg=json.loads((folder/'measurement.json').read_text());bad=copy.deepcopy(cfg)
        next(p for p in bad['selected_mos_pair_screens'] if p['instance']=='XDUT.GNNAN')['screen_v']=.99
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir();recipe=json.loads((folder/'recipe_proposal.json').read_text())
            for x in recipe['inputs']:shutil.copyfile(ROOT/x['source'],run/'inputs'/x['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            for ns in [0,41.5,42.5,42.99,43,43.05,43.1,43.2,44.2,45,46,46.99,46.999,47.99,48,48.05,48.1,48.2,48.3,50,51.5,52]:
                y={n:0. for n in names.values()}
                def put(n,v):y[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('vrefp',.9)
                put('pre',.99 if 43<=ns<48 else 0);put('xdut.gnna',0 if 43.05<=ns<48.05 else .99)
                if ns==43.05:put('xdut.gnna',-.05)
                if ns==48.05:put('xdut.gnna',1.05)
                put('xdut.gnnb',.99 if 43.1<=ns<48.1 else 0);put('xdut.gnndrv',0 if 43.2<=ns<48.2 else .99)
                put('xdut.gnn0',0 if 43.2<=ns<48.2 else .99)
                if ns==48.2:put('xdut.gnn0',-.12)
                put('xdut.xcdac.bn0',.9 if 44.2<=ns<48.3 else 0);put('xdut.xcdac.bp0',0 if 44.2<=ns<48.3 else .9)
                put('xdut.gnnan:2',1e-6);put('xdut.gnnap:2',2e-6);put('vpre:1',-3e-6)
                put('xdut.gnnan:4',2e-9);put('xdut.gnnap:4',-3e-9)
                rows.append((ns*1e-9,y))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows))
            (run/'raw/logStatus').write_text('tran_cell PASS\n');(run/'spectre.out').write_text('synthetic measurement mapping only\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/io_astage_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual(r['selected_current_count'],447);self.assertEqual(len(r['selected_mos_pair_extrema']),450)
            self.assertNotIn('upstream_A_core_direct_VDD_terminal_energy_J',m);self.assertIn('upstream_A_IO_direct_VDD_terminal_energy_J',m)
            self.assertAlmostEqual(m['ideal_PRE_source_work']['net_delivered_J'],.99*3e-6*5e-9,places=24)
            self.assertLess(abs(m['ideal_PRE_source_work']['source_work_minus_A_gate_work_J']),1e-25)
            self.assertLess(m['ideal_PRE_source_work']['max_PRE_node_KCL_A'],1e-20)
            self.assertAlmostEqual(m['PRE_A_gate_load']['full_signed_charge_C'],3e-6*52e-9,places=24)
            j={x['pair']:x for x in m['junction_forward_polarity_and_body_current']};self.assertEqual(len(j),150)
            self.assertAlmostEqual(j['XDUT.GNNAN:bd']['positive_forward_polarity_peak_V'],.05)
            self.assertAlmostEqual(j['XDUT.GNNAP:bd']['positive_forward_polarity_peak_V'],.06)
            self.assertEqual(j['XDUT.GNNAN:bd']['body_current_at_polarity_peak_A'],2e-9)
            self.assertEqual(j['XDUT.GNNAP:bd']['body_current_at_polarity_peak_A'],-3e-9)
            self.assertAlmostEqual(m['supply_rail_excursions']['xdut.gnn0']['below_ground_V'],.12)
            self.assertTrue(all(x['PRE_to_GNN0_s'] is not None for x in m['complete_chain_delays'].values()))
            self.assertTrue(all(x['remained_inside_from_native_s'] is not None for phase in m['correct_ON_settling'].values() for x in phase.values()))


if __name__=='__main__':unittest.main()
