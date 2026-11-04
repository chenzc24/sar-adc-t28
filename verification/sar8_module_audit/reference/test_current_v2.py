"""Focused save-only reduction checks using actual local v1/v2 inputs."""
import json
from pathlib import Path
import tempfile
import unittest
import reference_current_analyze as a
from prepare_current_v2 import dependencies,filter_save_lines
from test_reference_current_analyze import raw_text

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


class SaveOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=json.loads((HERE/'generated/managed_reproduction/measurement.json').read_text())
        cls.new=json.loads((HERE/'generated/current_v2/measurement.json').read_text())
        cls.audit=json.loads((HERE/'generated/current_v2/save_audit.json').read_text())

    def test_all_mandatory_measurement_fields_preserved(self):
        for key in ['current_saves','kcl_terms','terminal_current_catalog','selected_mos_pair_screens',
            'diagnostic_voltage_columns','edge_nodes','initial_witness_v','source_peaks',
            'source_diagnostic','source_history_stop_s','diagnostic_start_s','diagnostic_stop_s','boundary_provenance']:
            self.assertEqual(self.old[key],self.new[key],key)
        names,currents,equations=a.validate_config(self.new)
        self.assertEqual((len(names),len(currents),len(equations)),(413,275,5))

    def test_actual138_voltage_dependencies_and_all_current_port_context(self):
        keep,groups,fixed=dependencies(self.old)
        self.assertEqual(len(keep),138)
        self.assertEqual(keep,{a.norm(n) for n in self.new['voltage_saves']})
        self.assertEqual(len(groups['priority_228_terminal_pair_nodes']),34)
        self.assertEqual(fixed,['vrefn_src','vrefp_src'])
        self.assertTrue(all(set(group)<=keep for group in groups.values()))

    def test_exact_non_save_bytes_preserved_and_all275_currents_kept(self):
        original=(HERE/'generated/approximate_replay/test.scs').read_bytes()
        revised=(HERE/'generated/current_v2/test.scs').read_bytes()
        strip=lambda blob:b''.join(x for x in blob.splitlines(keepends=True) if not x.startswith(b'save '))
        self.assertEqual(strip(original),strip(revised))
        commands=[a.norm(x.decode().split()[1]) for x in revised.splitlines() if x.startswith(b'save ')]
        self.assertEqual(set(commands),{a.norm(n) for n in self.new['voltage_saves']+self.new['current_saves']})
        self.assertEqual(len(commands),413)

    def test_original_recipe_budgets_and_non_test_inputs_unchanged(self):
        original=json.loads((ROOT/'management/recipes/sar8audit-ref-current-v1.yaml').read_text())
        revised=json.loads((HERE/'generated/current_v2/recipe_proposal.json').read_text())
        self.assertEqual(original['resources'],revised['resources'])
        self.assertEqual(revised['resources']['max_output_mib'],8192)
        before={x['name']:x for x in original['inputs']}
        for item in revised['inputs']:
            if item['name'] not in ['test.scs','measurement.json']:
                self.assertEqual(item,before[item['name']])

    def test_unknown_save_line_rejects_instead_of_hiding_new_measurement(self):
        cfg=self.old;keep,_,_=dependencies(cfg)
        with self.assertRaisesRegex(ValueError,'Unknown v1 save'):
            filter_save_lines(b'save mystery\n',keep,{a.norm(n) for n in cfg['current_saves']},
                              {a.norm(n) for n in cfg['voltage_saves']})

    def test_actual_v2_config_runs_complete_minimal_native_reduction(self):
        cfg=self.new
        times=sorted({0.,cfg['diagnostic_start_s'],cfg['source_history_stop_s']} |
                     {item['time_s'] for item in cfg['source_peaks']})
        names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']}
        rows=[]
        for t in times:
            values={n:0. for n in names.values()};values[names['vdd!']]=.99
            if t==0.:
                for n,v in cfg['initial_witness_v'].items():values[names[n.lower()]]=v
            for item in cfg['source_peaks']:
                if t==item['time_s']:values[names[item['fixture_node']]]=item['value_v']
            rows.append((t,values))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);raw=root/'explicitly_synthetic.tran.tran';raw.write_text(raw_text(cfg,rows))
            output=root/'out';output.mkdir()
            result=a.summarize(str(raw),cfg,a.Budget(str(output),cfg['max_total_output_bytes']))
        self.assertEqual(result['selected_current_count'],275)
        self.assertEqual(len(result['node_kcl']),5)
        self.assertEqual(len(result['native_exports'][0]['columns']),27)
        self.assertEqual(len(result['native_exports'][1]['columns']),324)
        self.assertEqual(len(result['selected_mos_pair_extrema']),228)
        self.assertEqual(len(result['initial_witness_error_v']),31)
        self.assertTrue(all(x['error_v']==0. and x['error_time_s']==0.
                            for x in result['source_peak_reproduction_diagnostic'].values()))
        self.assertIsNone(result['acceptance_pass'])


if __name__=='__main__':unittest.main()
