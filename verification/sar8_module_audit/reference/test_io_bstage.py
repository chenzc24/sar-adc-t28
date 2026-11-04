"""One focused B-substitution and actual staged-analyzer interface check."""
import hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,ports,flatten
from io_bstage_analyze import validate
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE/'generated/io_cell_v1';NEW=HERE/'generated/io_bstage_v1'


class BStagePackageTest(unittest.TestCase):
    def test_exact_two_instances_IO_parameters_screen_mapping_and_staged_analysis(self):
        defs=definitions((OLD/'io_dut.scs').read_text());pins=ports(defs['sar8_refcell_unit']);binding={n:n for n in pins};binding.update(VDD='VDD!',VSS='0')
        before=flatten(defs,'sar8_refcell_unit',binding)
        after=flatten(definitions((NEW/'dut.scs').read_text()),'sar8_refcell_unit',binding)
        self.assertEqual(set(before),set(after));self.assertEqual({n for n in before if before[n]!=after[n]},{'XDUT.GNNBN','XDUT.GNNBP'})
        for polarity in ['N','P']:
            b=after['XDUT.GNNB'+polarity];c=before['XDUT.GNNC'+polarity]
            self.assertEqual((b['model'],b['parameters']),(c['model'],c['parameters']))
            self.assertEqual(b['nodes'],before['XDUT.GNNB'+polarity]['nodes'])
            self.assertIn('l=150n',b['parameters']);self.assertIn('w=320n',b['parameters'])
        receipt=json.loads((NEW/'package_review.json').read_text());self.assertEqual(len(receipt['cases']),2)
        for case in receipt['cases']:
            folder=ROOT/case['recipe'];self.assertEqual(hashlib.sha256(folder.read_bytes()).hexdigest(),case['recipe_sha256'])
            cfg=json.loads((folder.parent/'measurement.json').read_text());selected,currents,eq=validate(cfg)
            old=json.loads((OLD/('io_'+folder.parent.name)/'measurement.json').read_text())
            self.assertEqual((folder.parent/'test.scs').read_bytes(),(OLD/('io_'+folder.parent.name)/'test.scs').read_bytes())
            self.assertEqual((len(selected),len(currents),len(eq)),(540,447,7));self.assertEqual(cfg['kcl_terms'],old['kcl_terms'])
            prev={p['instance']+':'+p['terminal']:p for p in old['selected_mos_pair_screens']}
            now={p['instance']+':'+p['terminal']:p for p in cfg['selected_mos_pair_screens']}
            self.assertEqual(len(now),450)
            for name,p in now.items():
                if p['instance'] in ['XDUT.GNNBN','XDUT.GNNBP']:
                    self.assertEqual(p['screen_v'],1.98);self.assertEqual(p['model'],after[p['instance']]['model']);self.assertEqual(p['nodes'],prev[name]['nodes'])
                else:self.assertEqual(p,prev[name])
            for item in case['files']:
                data=(ROOT/item['source']).read_bytes();self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(item['bytes'],item['sha256']))
        # Synthetic current/edge records check packaging and measurement math only.
        folder=NEW/'ffcold';cfg=json.loads((folder/'measurement.json').read_text());recipe=json.loads((folder/'recipe_proposal.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for item in recipe['inputs']:shutil.copyfile(ROOT/item['source'],run/'inputs'/item['name'])
            times=[0,41.5,42.5,42.99,43,43.05,43.1,43.2,44.2,45,46,47,47.99,48,48.05,48.1,48.2,48.3,50,51.5,52]
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[];supply=cfg['supply_V']
            for ns in times:
                y={n:0. for n in names.values()}
                def put(n,value):y[names[n]]=value
                put('vdd!',supply);put('sample',supply if ns<41 else 0);put('vrefp',.9)
                put('pre',supply if 43<=ns<48 else 0);put('xdut.gnna',0 if 43.05<=ns<48.05 else supply)
                put('xdut.gnnb',supply if 43.1<=ns<48.1 else 0);put('xdut.gnndrv',0 if 43.2<=ns<48.2 else supply)
                put('xdut.gnn0',0 if 43.2<=ns<48.2 else supply)
                put('xdut.xcdac.bn0',.9 if 44.2<=ns<48.3 else 0);put('xdut.xcdac.bp0',0 if 44.2<=ns<48.3 else .9)
                for stage,current in [('a',1e-6),('b',2e-6),('c',3e-6)]:put('xdut.gnn'+stage+'p:3',current)
                gate=1e-7 if 42.99<=ns<43.2 else (-1e-7 if 47.99<=ns<48.2 else 0)
                put('xdut.gnnbn:2',gate);put('xdut.gnnbp:2',gate);put('vvdd:1',-6e-6)
                rows.append((ns*1e-9,y))
            rows[-1]=(52e-9,rows[-1][1]);(run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows))
            (run/'raw/logStatus').write_text('tran_cell PASS\n');(run/'spectre.out').write_text('synthetic interface test only\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            process=subprocess.run([sys.executable,'-B',str(run/'inputs/io_bstage_analyze.py'),'--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(process.returncode,0,process.stderr);r=json.loads((run/'derived/result.json').read_text());m=r['cell_measurements']
            self.assertIsNone(r['acceptance_pass']);self.assertEqual(r['selected_current_count'],447);self.assertEqual(len(r['selected_mos_pair_extrema']),450)
            self.assertNotIn('upstream_core_direct_VDD_terminal_energy_J',m)
            for label,current in [('upstream_A_core',1e-6),('test_B_IO',2e-6),('downstream_C_IO',3e-6)]:
                self.assertAlmostEqual(m[label+'_direct_VDD_terminal_energy_J'],supply*current*52e-9,places=24)
            self.assertGreater(m['B_input_load_current']['max_A'],0);self.assertLess(m['B_input_load_current']['min_A'],0)
            self.assertAlmostEqual(m['upstream_stage_delays']['disable_low']['A_to_B_s'],50e-12,places=20)
            self.assertEqual(next(e for e in r['native_exports'] if e['file']=='cell.native.f64le.gz')['rows'],len(rows))


if __name__=='__main__':unittest.main()
