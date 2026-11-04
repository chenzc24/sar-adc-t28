"""One minimal mapping/current-coverage/loading check; no Spectre invocation."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_standard_cell_live as prepare
import standard_cell_live_analyze as analyze

OWN,ROOT=prepare.OWN,prepare.ROOT


class LIVEStageTest(unittest.TestCase):
    def test_exact_stage_mapping_and_native_port_coverage(self):
        package=OWN/'standard_cell_live_v1';recipe=json.loads((package/'recipe.suggested.yaml').read_bytes())
        freeze=json.loads((package/'freeze.json').read_bytes())
        self.assertEqual(prepare.base.digest((package/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
        for folder in [package,prepare.SRC]:
            for item in json.loads((folder/'recipe.suggested.yaml').read_bytes())['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
        probe=json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
        text=(package/'dut.scs').read_text();oldtext=(prepare.SRC/'dut.scs').read_text()
        self.assertEqual(text,prepare.replace_live(oldtext))
        self.assertEqual(prepare.base.cells(text)['sar8p_inv'],prepare.base.cells(oldtext)['sar8p_inv'])
        old,_=prepare.standard.expanded_leaves(oldtext,probe);new,library=prepare.expand_twelve(text,probe)
        retired={k for k in old if k.startswith(prepare.STAGE+'.')}
        self.assertEqual(len(retired),7);self.assertEqual(set(old)-set(new),retired)
        self.assertEqual(len(set(new)-set(old)),6)
        for k in set(old)-retired:self.assertEqual(old[k],new[k])
        p=prepare.P;s=prepare.STAGE
        self.assertEqual(new[s+'.X000.MM4']['nodes'],[s+'.N',p+'SN',s+'.X000.net10','0'])
        self.assertEqual(new[s+'.X000.MM9']['nodes'],[s+'.X000.net10','XDUT.ACTIVE','0','0'])
        self.assertEqual(new[s+'.X001.MM1']['nodes'],[p+'LIVE',s+'.N','0','0'])
        self.assertEqual(new[s+'.X001.MM0']['nodes'],[p+'LIVE',s+'.N','VDD!','VDD!'])
        m=json.loads((package/'measurement.json').read_bytes())
        self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(62,436,61,609))
        self.assertNotIn(s+'.X000.MID',m['voltage_saves']);self.assertIn(s+'.X000.net10',m['voltage_saves'])
        self.assertNotIn(s+'.X000.CMID:1',m['current_saves'])
        self.assertEqual(len(library),12)
        for item in library.values():
            for port in item['requested_numeric_terminal_currents']:self.assertIn(port,m['terminal_current_catalog'])
        self.assertTrue(all(v['limit_abs_v']==.99 for v in m['stress_voltage_pairs'].values()))
        for path in (prepare.SRC/'pwl').glob('*.pwl'):self.assertEqual((package/'pwl'/path.name).read_bytes(),path.read_bytes())
        strip=lambda t:''.join(x for x in t.splitlines(True) if not x.startswith('save '))
        self.assertEqual(strip((package/'test.scs').read_text()),strip((prepare.SRC/'test.scs').read_text()))
        with tempfile.TemporaryDirectory(prefix='_live_stage_check_',dir=OWN) as folder:
            output=Path(folder).resolve();self.assertTrue(output.is_relative_to(OWN))
            names=['time']+sorted({x.lower() for x in m['voltage_saves']+m['current_saves']})
            (output/'peak.columns.json').write_text(json.dumps(dict(names=names)))
            times=[40.8e-9,41e-9,41.1e-9,m['source_history_stop_s']]
            blobs=[]
            for i,t in enumerate(times):
                v=dict.fromkeys(names,0.);v['time']=t;v['vdd!']=.99;v['xdut.active']=.99
                v[(p+'SN').lower()]=.99 if i>=2 else 0.;v[(s+'.N').lower()]=0. if i>=2 else .99
                if i in [1,2]:
                    for label,amps in [('SN',(5e-6,3e-6)),('ACTIVE',(-2e-6,-1e-6)),('INTERNAL_N',(-4e-6,-6e-6))]:
                        spec=m['standard_cell_live_experiment']['load_observers'][label]
                        v[spec['ports']['NM_gate'].lower()]=amps[0];v[spec['ports']['PM_gate'].lower()]=amps[1]
                    v[(p+'X000.MP:1').lower()]=-8e-6
                    v['xdut.vreplay_active:1']=3e-6
                    v[(s+'.X000.MM4:1').lower()]=10e-6
                blobs.append(struct.pack('<'+'d'*len(names),*(v[n] for n in names)))
            (output/'peak.native.bin').write_bytes(b''.join(blobs))
            observed=analyze.load_observations(str(output),m)
            self.assertEqual(set(observed),{'SN','ACTIVE','INTERNAL_N'})
            expected=5e-6*(times[2]-times[1])+.5*5e-6*(times[3]-times[2])
            self.assertAlmostEqual(observed['SN']['event_exchange']['into_gate_devices_c']['NM_gate'],expected,delta=1e-27)
            self.assertTrue(all(o['native_KCL_max_a']<1e-18 for o in observed.values()))
            self.assertEqual(len(observed['SN']['rising_halfrail_s']),1)
            missing=m['standard_cell_live_experiment']['load_observers']['SN']['ports']['NM_gate'].lower()
            (output/'peak.columns.json').write_text(json.dumps(dict(names=[n for n in names if n!=missing])))
            with self.assertRaises(ValueError):analyze.load_observations(str(output),m)
        result=dict(full_history_source_energy={k:dict(net_delivered_j=1e-15) for k in m['source_power_ports']})
        result['full_history_source_energy']['RINPUT_PLUS']['net_delivered_j']=-.3e-15
        result['full_history_source_energy']['RINPUT_MINUS']['net_delivered_j']=.1e-15
        analyze.separate_energy(result,m)
        self.assertEqual(len(result['full_history_source_energy']),5)
        self.assertEqual(len(result['full_history_boundary_source_energy']),7)
        self.assertAlmostEqual(result['full_history_resistor_energy']['absorbed_j'],.2e-15,delta=1e-28)
        self.assertAlmostEqual(result['fixture_all_twelve_sources_net_work_j'],12e-15,delta=1e-28)


if __name__=='__main__':unittest.main(verbosity=2)
