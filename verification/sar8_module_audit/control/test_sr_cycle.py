"""One focused paired-SR contract, boundary, fanout and observation check."""
import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_sr_cycle as prepare
import sr_cycle_analyze as analyze

OWN,ROOT=prepare.OWN,prepare.ROOT
P=prepare.P


class SRCycleTest(unittest.TestCase):
    def test_native_projection_and_actual_collection_budget(self):
        """Maximum64MiB analysis table +8MiB result, no circuit simulation."""
        m=json.loads((prepare.OUT/'q_upper/measurement.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='_srcycle_budget_',dir=OWN) as temp:
            run=Path(temp).resolve();self.assertTrue(run.is_relative_to(OWN))
            out=run/'derived';out.mkdir();raw=run/'raw';raw.mkdir()
            psf=raw/'retained_full_psf';psf.write_bytes(b'ORIGINAL_PSF_MUST_REMAIN')
            psf_hash=hashlib.sha256(psf.read_bytes()).hexdigest()
            for name in ['simulation.state.json','analysis.state.json','simulation.admission.json',
                         'analysis.admission.json','source_provenance.json']:
                (run/name).write_bytes(b'{}\n')
            (run/'spectre.out').write_bytes(b'SYNTHETIC_BUDGET_LOG\n');(raw/'logStatus').write_bytes(b'tran_first PASS\n')
            names=['time']+[s.lower() for s in m['diagnostic_voltage_columns']+m['diagnostic_current_columns']]+['kcl:'+s.lower() for s in m['critical_kcl_nodes']]
            units=['s']+['V']*len(m['diagnostic_voltage_columns'])+['A']*(len(m['diagnostic_current_columns'])+len(m['critical_kcl_nodes']))
            (out/'peak.columns.json').write_text(json.dumps(dict(names=names,units=units)))
            keep=['time']+[s.lower() for s in m['voltage_saves']]+[s.lower() for s in m['cycle']['final_wave_current_columns']]
            keep+=['kcl:'+s.lower() for s in m['cycle']['final_wave_KCL_nodes']]
            indices=[names.index(n) for n in keep]
            rows=m['max_derived_binary_bytes']//(8*len(names));middle=rows//2
            ordinary=[0.]*len(names)
            for j,n in enumerate(m['voltage_saves']):ordinary[names.index(n.lower())]=.1+j*.001
            ordinary[names.index('vdd!')]=.99
            peak=list(ordinary);peak[names.index((P+'XCLOCK.QB').lower())]=1.2
            full_tail={False:struct.pack('<'+'d'*(len(names)-1),*ordinary[1:]),True:struct.pack('<'+'d'*(len(names)-1),*peak[1:])}
            compact_tail={False:struct.pack('<'+'d'*(len(keep)-1),*[ordinary[j] for j in indices[1:]]),
                          True:struct.pack('<'+'d'*(len(keep)-1),*[peak[j] for j in indices[1:]])}
            expected=hashlib.sha256();time_hash=hashlib.sha256()
            with (out/'peak.native.bin').open('wb') as handle:
                for i in range(rows):
                    at=i*prepare.STOP/(rows-1);t=struct.pack('<d',at);mark=(i==middle)
                    handle.write(t+full_tail[mark]);expected.update(t+compact_tail[mark]);time_hash.update(t)
            def voltage(row,node):return 0. if node=='0' else row[names.index(node.lower())]
            stress={}
            for label,pair in m['stress_voltage_pairs'].items():
                a=abs(voltage(ordinary,pair['positive_node'])-voltage(ordinary,pair['negative_node']))
                b=abs(voltage(peak,pair['positive_node'])-voltage(peak,pair['negative_node']))
                stress[label]=dict(max_abs_v=max(a,b),max_abs_time_s=middle*prepare.STOP/(rows-1) if b>a else 0.)
            result=dict(budget_fixture_only=True,full_history_voltage_stress=stress,padding='')
            digest_before=hashlib.sha256(json.dumps(stress,sort_keys=True).encode()).hexdigest()
            projected=analyze.project_native_wave(str(out),m)
            self.assertEqual((projected['native_rows'],projected['exported_columns']),(rows,96))
            self.assertEqual(projected['time_sha256'],time_hash.hexdigest())
            actual=hashlib.sha256()
            with (out/'peak.native.bin').open('rb') as handle:
                for block in iter(lambda:handle.read(1024*1024),b''):actual.update(block)
            self.assertEqual(actual.hexdigest(),expected.hexdigest())
            header=json.loads((out/'peak.columns.json').read_bytes())
            self.assertTrue(set(s.lower() for s in m['voltage_saves']).issubset(header['names']))
            self.assertEqual(len(result['full_history_voltage_stress']),606)
            self.assertEqual(hashlib.sha256(json.dumps(stress,sort_keys=True).encode()).hexdigest(),digest_before)
            self.assertEqual(hashlib.sha256(psf.read_bytes()).hexdigest(),psf_hash)
            text=json.dumps(result,indent=2,sort_keys=True)+'\n';result['padding']='x'*(8*1024**2-len(text.encode()))
            text=json.dumps(result,indent=2,sort_keys=True)+'\n';self.assertEqual(len(text.encode()),8*1024**2)
            (out/'result.json').write_text(text,encoding='utf-8')
            budget=analyze.collection_budget(str(run),str(out),m)
            self.assertLessEqual(budget['projected_collection_bytes'],30*1024**2)
            self.assertLess(budget['projected_collection_bytes'],32*1024**2)
            self.assertEqual(set(q.name for q in out.iterdir()),{'peak.native.bin','peak.columns.json','result.json'})
            with (run/'spectre.out').open('ab') as handle:handle.write(b'x'*(3*1024**2))
            with self.assertRaises(ValueError):analyze.collection_budget(str(run),str(out),m)
            validation=dict(synthetic_budget_test_not_simulation=True,analysis_table_bytes=rows*len(names)*8,
                native_rows=rows,analysis_columns=len(names),final_columns=len(keep),
                final_wave_bytes=projected['exported_bytes'],result_metadata_bytes=8*1024**2,
                actual_collection_bytes=budget['existing_plus_pending_result_bytes'],
                final_state_reserve_bytes=budget['final_state_growth_reserve_bytes'],
                guarded_collection_bytes=budget['projected_collection_bytes'],limit_bytes=30*1024**2,
                every_native_time_and_all66_voltages_byte_exact=True,all606_global_extrema_unchanged=True,
                raw_PSF_unchanged=True,oversized_log_rejected=True)
            prepare.base.write_json(prepare.OUT/'budget_validation.json',validation)
            print(json.dumps(validation,sort_keys=True))

    def test_paired_truth_fanout_and_complete_cycle_observer(self):
        contract=json.loads((prepare.OUT/'contract.json').read_bytes());truth=contract['original']['truth_rows']
        solutions={(r['R'],r['S']):{(s['Q'],s['QB']) for s in r['stable_solutions']} for r in truth}
        self.assertEqual(solutions,{(0,0):{(0,1),(1,0)},(0,1):{(1,0)},(1,0):{(0,1)},(1,1):{(0,1)}})
        self.assertEqual(len(contract['phases']),10)
        leaves={};measurements={}
        for tag,(folder,sr,run) in prepare.CASES.items():
            dest=prepare.OUT/tag;recipe=json.loads((dest/'recipe.suggested.yaml').read_bytes())
            freeze=json.loads((dest/'freeze.json').read_bytes())
            self.assertEqual(prepare.base.digest((dest/'recipe.suggested.yaml').read_bytes()),freeze['recipe_sha256'])
            for item in recipe['inputs']:
                self.assertEqual(prepare.base.digest((ROOT/item['source']).read_bytes()),item['sha256'])
            probe=json.loads((ROOT/next(i['source'] for i in recipe['inputs'] if i['name']=='probe_metadata.json')).read_bytes())
            old,_=prepare.mapping.expand_eighteen((OWN/folder/'dut.scs').read_text(),probe)
            new,library=prepare.mapping.expand_eighteen((dest/'dut.scs').read_text(),probe);leaves[tag]=new
            m=json.loads((dest/'measurement.json').read_bytes());measurements[tag]=m
            self.assertEqual((len(m['voltage_saves']),len(m['current_saves']),len(m['critical_kcl_nodes']),len(m['stress_voltage_pairs'])),(66,439,65,606))
            self.assertEqual(len(library),18)
            for node in [P+'CLOCK_RESET',P+'CLOCK_SET',P+'CLOCK_Q',P+'XCLOCK.QB','XDUT.CMP_CLK']:
                oldports={(p,port) for p,v in old.items() for port,n in enumerate(v['nodes'],1) if n==node}
                newports={(p,port) for p,v in new.items() for port,n in enumerate(v['nodes'],1) if n==node}
                self.assertEqual(oldports,newports)
            for node,terms in m['kcl_terms'].items():
                self.assertEqual(set(terms),{p for p,c in m['terminal_current_catalog'].items() if c['node']==node})
            for path in m['cycle']['core_bias_mos']:
                for port in range(1,5):self.assertIn(path+':'+str(port),m['diagnostic_current_columns'])
            self.assertEqual((len(m['cycle']['energy_groups']['supply']),len(m['cycle']['energy_groups']['commands']),len(m['cycle']['energy_groups']['background'])),(1,4,11))
            self.assertEqual(set(m['source_power_ports']),{p for labels in m['cycle']['energy_groups'].values() for p in labels})
            for path,item in new.items():
                if item['model']=='vsource':
                    self.assertNotIn(item['nodes'][0],[P+'CLOCK_Q',P+'XCLOCK.QB',P+'XCLOCK.X003.MID'])
            self.assertFalse({(P+'CLOCK_Q').lower(),(P+'XCLOCK.QB').lower(),(P+'XCLOCK.X003.MID').lower()} & set(m['expected_initial_state']['values_v']))
        a,b=leaves.values();self.assertEqual(a.keys(),b.keys())
        self.assertEqual({p for p in a if a[p]!=b[p]},{P+'XCLOCK.X003.MN0',P+'XCLOCK.X003.MN1'})
        for p in a:
            if a[p]!=b[p]:
                expected=dict(a[p]);expected['nodes']=list(a[p]['nodes']);expected['nodes'][1]=b[p]['nodes'][1]
                self.assertEqual(expected,b[p])
        for f in sorted((prepare.OUT/'rb_upper/pwl').glob('*.pwl')):
            self.assertEqual(f.read_bytes(),(prepare.OUT/'q_upper/pwl'/f.name).read_bytes())
        m=measurements['q_upper'];phases=m['cycle']['phases']
        with tempfile.TemporaryDirectory(prefix='_srcycle_test_',dir=OWN) as temp:
            out=Path(temp).resolve();self.assertTrue(out.is_relative_to(OWN))
            names=['time']+[s.lower() for s in m['diagnostic_voltage_columns']+m['diagnostic_current_columns']]+['kcl:'+s.lower() for s in m['critical_kcl_nodes']]
            (out/'peak.columns.json').write_text(json.dumps(dict(names=names)))
            times={0.,prepare.STOP}
            for ph in phases:
                times.update([ph['start_s']+.45e-9,ph['start_s']+.85e-9])
                if ph['index']:
                    times.update(ph['start_s']+v*1e-12 for v in [-12,-10,-8,-5,-3,-1,0,2,4,5,7,9,10,12,15,20])
            def wave(at,key,delay=0.):
                prev=phases[0][key]
                for ph in phases[1:]:
                    start=ph['start_s']+delay-10e-12;stop=start+20e-12;target=ph[key]
                    if at<=start:return prev*.99
                    if at<stop:return (prev+(target-prev)*(at-start)/(stop-start))*.99
                    prev=target
                return prev*.99
            data=[]
            for at in sorted(times):
                v=dict.fromkeys(names,0.);v['time']=at;v['vdd!']=.99;v['vvdd:1']=-10e-6
                v[(P+'CLOCK_RESET').lower()]=wave(at,'R',2e-12)
                v[(P+'CLOCK_SET').lower()]=wave(at,'S',2e-12)
                v[(P+'CLOCK_Q').lower()]=wave(at,'Q',7e-12)
                v[(P+'XCLOCK.QB').lower()]=wave(at,'QB',9e-12)
                v[(P+'XCLOCK.RB').lower()]=.99-wave(at,'R',4e-12)
                v['xdut.cmp_clk']=wave(at,'Q',12e-12)
                v[(P+'CYCLE_RESET_A').lower()]=wave(at,'R')
                v[(P+'CYCLE_SET_A').lower()]=wave(at,'S');v[(P+'CYCLE_SET_B').lower()]=.99
                data.append(v)
            def save(rows):
                (out/'peak.native.bin').write_bytes(b''.join(struct.pack('<'+'d'*len(names),*(v[n] for n in names)) for v in rows))
            save(data);got=analyze.inspect_cycle(str(out),m)
            self.assertTrue(got['functional_observation_pass'])
            for i in [2,4,6,7]:
                self.assertAlmostEqual(got['phases'][i]['delays_s']['actual_input_to_Q'],5e-12,delta=1e-22)
                self.assertAlmostEqual(got['phases'][i]['delays_s']['actual_input_to_QB'],7e-12,delta=1e-22)
            phase=got['phases'][3]
            self.assertAlmostEqual(phase['source_work_groups_j']['supply']['VDD'],.99*10e-6*(phase['last_native_s']-phase['first_native_s']),delta=1e-26)
            damaged=[dict(v) for v in data]
            point=next(v for v in damaged if abs(v['time']-3.45e-9)<1e-22);point[(P+'CLOCK_Q').lower()]=0.
            save(damaged);bad=analyze.inspect_cycle(str(out),m)
            self.assertFalse(bad['functional_observation_pass']);self.assertGreater(bad['phases'][3]['hold_Q_mismatches'],0)
            save([v for v in data if not 9.4e-9<=v['time']<=9.9e-9])
            unknown=analyze.inspect_cycle(str(out),m)
            self.assertIsNone(unknown['phases'][9]['functional_observation_pass']);self.assertIsNone(unknown['functional_observation_pass'])
            missing=(P+'XCLOCK.X003.MN0:2').lower()
            (out/'peak.columns.json').write_text(json.dumps(dict(names=[n for n in names if n!=missing])))
            with self.assertRaises(ValueError):analyze.inspect_cycle(str(out),m)


if __name__=='__main__':unittest.main(verbosity=2)
