"""Loaded-cell geometry/topology and real generated measurement interfaces."""
import collections,hashlib,json,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from build_first_fixture import definitions,flatten
from io_cell_analyze import validate
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];DIR=HERE/'generated/io_cell_v1'


class CellPackageTests(unittest.TestCase):
    def test_only_final_pair_changes_to_exact_native_accepted_IO_geometry(self):
        pins=['PRE','SAMPLE','CMP_CLK','GNPDRV','GPNDRV','GPPDRV','VINN','VINP','VREFN','VREFP','VDD','VSS']
        binding={n:n for n in pins};binding['VDD']='VDD!';binding['VSS']='0'
        before=flatten(definitions((DIR/'core_dut.scs').read_text()),'sar8_refcell_unit',binding)
        after=flatten(definitions((DIR/'io_dut.scs').read_text()),'sar8_refcell_unit',binding)
        self.assertEqual(set(before),set(after))
        changes={n for n in before if before[n]!=after[n]}
        self.assertEqual(changes,{'XDUT.GNNCN','XDUT.GNNCP'})
        native=(ROOT/'output/sar8_physical_repair/sar8fix-ioscreen-sscold/dut.scs').read_text()
        for name,template in [('GNNCN','F18IN'),('GNNCP','F18IP')]:
            m=re.search(r'(?m)^'+template+r' \([^)]*\) (\w+) (.+)$',native)
            row=after['XDUT.'+name]
            self.assertEqual(row['model'],m[1]);self.assertEqual(row['parameters'],' '.join(m[2].split()))
            self.assertIn('l=150n',row['parameters']);self.assertIn('w=320n',row['parameters'])
        self.assertEqual(sum(d['model']=='rupolym' for d in before.values()),40)
        self.assertTrue(all(d['model'] in ['nch_18_mac','pch_18_mac'] for n,d in after.items() if '.XCDAC.' in n and d['model'].startswith(('nch_','pch_'))))
        for circuit in [before,after]:
            incidence=collections.Counter(node for d in circuit.values() for node in d['nodes'])
            self.assertEqual({n for n,count in incidence.items() if count==1 and n not in binding.values()},set())

    def test_paired_corner_stimuli_identical_and_all_native_saves_catalogued(self):
        receipt=json.loads((DIR/'package_review.json').read_text())
        self.assertEqual(len(receipt['cases']),4)
        for case in receipt['cases']:
            self.assertEqual(case['staged_bytes'],sum(x['bytes'] for x in case['files']))
            for item in case['files']:
                data=(ROOT/item['source']).read_bytes()
                self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(item['bytes'],item['sha256']))
        for tag,supply in [('ffcold',.99),('sscold',.81)]:
            self.assertEqual((DIR/('core_'+tag)/'test.scs').read_bytes(),(DIR/('io_'+tag)/'test.scs').read_bytes())
            for family in ['core','io']:
                cfg=json.loads((DIR/(family+'_'+tag)/'measurement.json').read_text())
                selected,currents,eq=validate(cfg)
                self.assertEqual((len(selected),len(currents),len(eq)),(540,447,7))
                self.assertEqual(len(cfg['selected_mos_pair_screens']),450)
                self.assertEqual(cfg['supply_V'],supply);self.assertEqual(cfg['source_peaks'],[])
                self.assertTrue(cfg['stimulus_contract']['corner_normalized_0_VDD'])
                self.assertEqual(cfg['stimulus_contract']['sampling_source'],
                    'VSAMPLE (SAMPLE 0) vsource type=pulse val0=SUP val1=0 delay=41n rise=100p fall=100p width=59.9n period=100n')
                text=(DIR/(family+'_'+tag)/'test.scs').read_text()
                commands={n.lower() for n in re.findall(r'(?m)^save (\S+)$',text)}
                self.assertEqual(commands,set(selected))

    def test_actual_SS_IO_package_CLI_delay_static_and_full_native_history(self):
        # Explicitly synthetic samples validate the analyzer; no simulator or
        # claim about IO-cell operation is involved in this test.
        path=DIR/'io_sscold';cfg=json.loads((path/'measurement.json').read_text());supply=cfg['supply_V']
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder);(run/'inputs').mkdir();(run/'raw').mkdir()
            recipe=json.loads((path/'recipe_proposal.json').read_text())
            for item in recipe['inputs']:shutil.copyfile(ROOT/item['source'],run/'inputs'/item['name'])
            times=[0,41.5,42.5,43.0,43.05,43.10,43.20,44.0,44.2,45,46,47,48,48.05,48.10,48.20,48.3,50,51.5,52]
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']};rows=[]
            for ns in times:
                values={n:0. for n in names.values()};values[names['vdd!']]=supply
                values[names['sample']]=supply if ns<41 else 0
                values[names['pre']]=supply if 43<=ns<48 else 0
                values[names['vrefp']]=.9;values[names['vvdd:1']]=-1e-6
                values[names['xdut.gnna']]=supply if ns<43 or ns>=48 else 0
                values[names['xdut.gnnb']]=supply if 43.05<=ns<48.05 else 0
                values[names['xdut.gnndrv']]=supply if ns<43.10 or ns>=48.10 else 0
                values[names['xdut.gnn0']]=supply if ns<43.20 or ns>=48.20 else 0
                values[names['xdut.xcdac.bn0']]=.9 if 44.2<=ns<48.3 else 0
                values[names['xdut.xcdac.bp0']]=0 if 44.2<=ns<48.3 else .9
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1])
            (run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows))
            (run/'raw/logStatus').write_text('tran_cell    PASS\n')
            (run/'spectre.out').write_text('synthetic software fixture only\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            result=subprocess.run([sys.executable,'-B',str(run/'inputs/io_cell_analyze.py'),
                '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            r=json.loads((run/'derived/result.json').read_text())
            self.assertIsNone(r['acceptance_pass']);self.assertEqual(r['selected_current_count'],447)
            self.assertEqual(len(r['selected_mos_pair_extrema']),450)
            self.assertEqual(r['source_peak_reproduction_diagnostic'],{})
            primary=next(e for e in r['native_exports'] if e['file']=='cell.native.f64le.gz')
            self.assertEqual(primary['rows'],len(rows));self.assertEqual(len(primary['columns']),94)
            for event in ['disable_low','enable_low']:
                self.assertAlmostEqual(r['cell_measurements']['local_inverter_delays'][event]['B_to_C_s'],50e-12,places=20)
            for p in r['cell_measurements']['static_plateaus'].values():
                self.assertEqual(max(p['logic_rail_max_deviation_V'].values()),0.)
            self.assertFalse(list((run/'inputs').rglob('*.pyc')))


if __name__=='__main__':unittest.main()
