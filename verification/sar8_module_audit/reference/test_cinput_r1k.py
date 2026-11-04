"""One-component topology and actual six-node analyzer interface checks."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from build_first_fixture import definitions,flatten,TOP
from reference_cinput_analyze import validate_candidate,NEW_GATE
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];DIR=HERE/'generated/cinput_r1k_v1'


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads((DIR/'measurement.json').read_text())

    def test_exactly_two_gate_rewires_and_one_ideal_resistor_other_primitives_unchanged(self):
        bind=json.loads((HERE/'generated/first_reproduction/source_map.json').read_text())['replay_port_binding']
        before=flatten(definitions((HERE/'generated/approximate_replay/dut.scs').read_text()),TOP,bind)
        after=flatten(definitions((DIR/'dut.scs').read_text()),TOP,bind)
        changed=[n for n in before if before[n]!=after.get(n)]
        self.assertEqual(set(changed),{'XDUT.XREF.XDRV0.GNNCN','XDUT.XREF.XDRV0.GNNCP'})
        for n in changed:
            expected=copy.deepcopy(before[n]);expected['nodes'][1]='XDUT.XREF.XDRV0.GNN_CG'
            self.assertEqual(expected,after[n])
        self.assertEqual(set(after)-set(before),{'XDUT.XREF.XDRV0.R_CIN'})
        self.assertEqual(after['XDUT.XREF.XDRV0.R_CIN']['parameters'],'r=1k')
        strip=lambda blob:b''.join(x for x in blob.splitlines(keepends=True) if not x.startswith(b'save '))
        self.assertEqual(strip((DIR/'test.scs').read_bytes()),strip((HERE/'generated/current_v2/test.scs').read_bytes()))

    def test_actual_measurement277_currents_six_complete_nodes_and_updated_stress_pairs(self):
        selected,currents,equations=validate_candidate(self.cfg)
        old=json.loads((HERE/'generated/current_v2/measurement.json').read_text())
        self.assertEqual((len(selected),len(currents),len(equations)),(416,277,6))
        self.assertTrue({n.lower() for n in old['current_saves']}<=set(currents))
        self.assertEqual(len(equations[NEW_GATE]),3)
        self.assertEqual(len({n for terms in equations.values() for n in terms}),17)
        self.assertEqual(len(self.cfg['selected_mos_pair_screens']),228)
        for pair in self.cfg['selected_mos_pair_screens']:
            if pair['instance'].endswith(('GNNCN','GNNCP')):
                self.assertNotIn('XDUT.XREF.XDRV0.GNNB',pair['nodes'])

    def test_actual_package_synthetic_CLI_extra_KCL_load_and_energy_fields(self):
        # Synthetic native rows test software interfaces, not candidate efficacy.
        cfg=self.cfg
        with tempfile.TemporaryDirectory() as folder:
            run=Path(folder);(run/'inputs').mkdir();(run/'raw').mkdir()
            recipe=json.loads((DIR/'recipe_proposal.json').read_text())
            for item in recipe['inputs']:shutil.copyfile(ROOT/item['source'],run/'inputs'/item['name'])
            command=cfg['experiment']['load_diagnostic']['independent_command_time_s']
            times=sorted({0.,cfg['diagnostic_start_s'],command,65.45e-9,cfg['source_history_stop_s']} |
                         {p['time_s'] for p in cfg['source_peaks']})
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']}
            rows=[]
            for t in times:
                values={n:0. for n in names.values()};values[names['vdd!']]=.99
                values[names['vrefp']]=.9;values[names['vvdd:1']]=-1e-6
                values[names['xdut.xcdac.bn0']]=.9 if t>=command else 0.
                values[names['xdut.xcdac.bp0']]=0. if t>=command else .9
                if not t:
                    for n,v in cfg['initial_witness_v'].items():values[names[n.lower()]]=v
                for p in cfg['source_peaks']:
                    if t==p['time_s']:values[names[p['fixture_node']]]=p['value_v']
                rows.append((t,values))
            (run/'raw/tran_repro.tran.tran').write_text(raw_text(cfg,rows))
            (run/'raw/logStatus').write_text('tran_repro PASS\n')
            (run/'spectre.out').write_text('synthetic only\nspectre completes with0 errors\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/reference_cinput_analyze.py'),
                '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result=json.loads((run/'derived/result.json').read_text())
            self.assertEqual(result['selected_current_count'],277)
            self.assertEqual(len(result['node_kcl']),6)
            self.assertEqual([len(x['columns']) for x in result['native_exports']],[24,68])
            for n in ['xdut.xcdac.bn0','xdut.xcdac.bp0']:
                entry=result['additional_measurements']['load_settling']['nodes'][n]
                self.assertEqual(entry['final_error_V'],0.)
                self.assertEqual(entry['remained_within_tolerance_from_native_s'],command)
            self.assertAlmostEqual(result['additional_measurements']['supply_energy']['delivered_J'],.99e-6*cfg['source_history_stop_s'])
            self.assertIsNone(result['acceptance_pass'])
            self.assertFalse(list((run/'inputs').rglob('*.pyc')))


if __name__=='__main__':unittest.main()
