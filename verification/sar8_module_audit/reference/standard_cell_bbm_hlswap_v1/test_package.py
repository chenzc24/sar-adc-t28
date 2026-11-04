"""H-only native pin permutation from frozen L; all-terminal phase-time test."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.path.append(str(Path(__file__).resolve().parent.parent))
from build_first_fixture import definitions, flatten
from prepare import OLD,OUT,ROOT,HERE,TOP,TARGET,candidate,VARIANT
from prepare_standard_cell_bbm import read,expanded,binding
from standard_cell_bbm_hlswap_analyze import validate, measurements,above_duration
from test_reference_current_analyze import raw_text
import io_cell_analyze as cell


class SingleHFromFrozenLTest(unittest.TestCase):
    def test_mapping_provenance_and_staged_measurement(self):
        metadata=read(OLD/'library_metadata.json')
        d,expected,library,delta=candidate()
        new,native=expanded(definitions((OUT/'dut.scs').read_text()),metadata)
        self.assertEqual(new,expected)
        old,oldnative=expanded(definitions((OLD/'dut.scs').read_text()),metadata)
        self.assertEqual(native,oldnative)
        changed=[n for n in old if new[n]!=old[n]]
        self.assertEqual(set(changed),{TARGET+'.'+m for m in ['MM4','MM9','MM1','MM2']})
        self.assertEqual(sum(new[n]==old[n] for n in old),190)
        self.assertTrue(all(new[n]==old[n] for n in old if n.startswith('XDUT.XBBM0.X004.')))
        for n in changed:
            self.assertEqual(new[n]['model'],old[n]['model'])
            self.assertEqual(new[n]['parameters'],old[n]['parameters'])
            self.assertEqual(new[n]['nodes'][::2],old[n]['nodes'][::2])
            self.assertEqual(new[n]['nodes'][3],old[n]['nodes'][3])
        olddefs=definitions((OLD/'dut.scs').read_text())
        self.assertEqual(d['sar8p_nand2'],olddefs['sar8p_nand2'])
        for c in read(OUT/'package_review.json')['cases']:
            folder=(ROOT/c['recipe']).parent
            cfg=read(folder/'measurement.json');v,i,k=validate(cfg)
            self.assertEqual((len(v),len(i),len(k)),(768,652,36))
            self.assertEqual((folder/'test.scs').read_bytes(),(OLD/'ffcold/test.scs').read_bytes())
            for f in c['files']:
                data=(ROOT/f['source']).read_bytes()
                self.assertEqual((len(data),hashlib.sha256(data).hexdigest()),(f['bytes'],f['sha256']))
        cfg=read(OUT/'ffcold/measurement.json');oldcfg=read(OLD/'ffcold/measurement.json')
        self.assertEqual([n for n in cfg['terminal_current_catalog'] if cfg['terminal_current_catalog'][n]!=oldcfg['terminal_current_catalog'][n]],
                         sorted(TARGET+'.'+m+':2' for m in ['MM4','MM9','MM1','MM2']))
        self.assertEqual(len([1 for a,b in zip(cfg['selected_mos_pair_screens'],oldcfg['selected_mos_pair_screens']) if a!=b]),12)
        self.assertEqual({n for n in cfg['kcl_terms'] if cfg['kcl_terms'][n]!=oldcfg['kcl_terms'][n]},
                         {'CODE','XDUT.XBBM0.HD'})
        bad=copy.deepcopy(cfg);bad['terminal_current_catalog'][TARGET+'.MM4:2']['node']='CODE'
        with self.assertRaises(ValueError):validate(bad)
        cfg=json.loads((OUT/'ffcold/measurement.json').read_text())
        bad=copy.deepcopy(cfg);bad['selected_mos_pair_screens'][next(j for j,x in enumerate(bad['selected_mos_pair_screens']) if x['model']=='nch_mac')]['screen_v']=1.98
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(cfg);bad['driver_source_ports']['H0']['source_port_branches'][0]='invented:1'
        with self.assertRaises(ValueError):validate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'inputs').mkdir();(run/'raw').mkdir()
            for f in json.loads((OUT/'ffcold/recipe_proposal.json').read_text())['inputs']:
                shutil.copyfile(ROOT/f['source'],run/'inputs'/f['name'])
            names={n.lower():n for n in cfg['voltage_saves']+cfg['current_saves']}
            rows=[]
            times=[0,41.5,42.9,42.995,43,43.005,43.05,43.1,43.15,43.2,43.25,43.3,43.35,43.4,43.45,43.5,44,44.2,45,46,47,47.99,47.995,48,48.005,48.05,48.1,48.15,48.2,48.25,48.3,48.35,48.4,48.45,48.5,48.6,49,49.5,50,51,51.5,52]
            for ns in times:
                values={n:0. for n in names.values()}
                def put(n,v):values[names[n]]=v
                put('vdd!',.99);put('sample',.99 if ns<41 else 0);put('code',.495 if ns in [43,48] else .99 if 43<ns<48 else 0)
                put('vrefp',.9)
                for n,a,b in [('xdut.h0',43.2,48.1),('xdut.pre',43.2,48.4),
                        ('xdut.gpn0',43.45,48.3),('xdut.gpp0',43.15,48.4)]:
                    put(n,.99 if a<=ns<b else 0)
                for n,a,b in [('xdut.l0',43.1,48.3),('xdut.gpnpre',43.3,48.3),
                        ('xdut.gnn0',43.25,48.5),('xdut.gnp0',43.4,48.3),
                        ('xdut.xbbm0.cb',43.05,48.05)]:
                    put(n,0 if a<=ns<b else .99)
                for n,a,b,high in [('xdut.xbbm0.xd_hd.rc0',43.15,48.05,True),
                    ('xdut.xbbm0.xd_hd.rc1',43.2,48.1,False),
                    ('xdut.xbbm0.hd',43.25,48.15,True),
                    ('xdut.xbbm0.xd_ld.rc0',43.15,48.2,False),
                    ('xdut.xbbm0.xd_ld.rc1',43.2,48.25,True),
                    ('xdut.xbbm0.ld',43.25,48.3,False)]:
                    put(n,.99 if (a<=ns<b)==high else 0)
                if ns==43.005:put('xdut.xbbm0.xd_hd.rc1',1.07)
                bn=.9 if 44.2<=ns<49 else 0
                bp=0
                if 48.05<=ns<48.3:bn,bp=.92,-.01
                if ns>=49:bp=.01
                put('xdut.xcdac.bn0',bn);put('xdut.xcdac.bp0',bp)
                # All source work remains balanced; exact injected currents are synthetic.
                loads=[b.lower() for b,x in cfg['terminal_current_catalog'].items()
                       if x['node']=='CODE' and b!='VCODE:1']
                put(loads[0],1e-6);put('vcode:1',-1e-6)
                for q in cfg['driver_source_ports'].values():
                    src=q['source_port_branches']
                    incident=[b.lower() for b,x in cfg['terminal_current_catalog'].items()
                              if x['node'].lower()==q['node'] and b.lower() not in src]
                    put(src[0],-3e-6);put(incident[0],3e-6)
                for b,x in cfg['terminal_current_catalog'].items():
                    if x['model'].startswith('pch') and x['port']==3 and x['node']=='VDD!':put(b.lower(),1e-6)
                for n,v in [('xdut.xcdac.xsn0.mn_low:1',2e-6),
                    ('xdut.xcdac.xsn0.mp_high:1',-1e-6),
                    ('xdut.xcdac.xsp0.mn_low:1',-3e-6),
                    ('xdut.xcdac.xsp0.mp_high:1',4e-6)]:put(n,v)
                rows.append((ns*1e-9,values))
            rows[-1]=(52e-9,rows[-1][1])
            (run/'raw/tran_cell.tran.tran').write_text(raw_text(cfg,rows))
            (run/'raw/logStatus').write_text('tran_cell PASS\n')
            (run/'spectre.out').write_text('Synthetic parser/measurement check, not physical simulation\n')
            (run/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,
                native=dict(native_analysis_pass=True,zero_error_footer=True,warning_codes=[]))))
            proc=subprocess.run([sys.executable,'-B',str(run/'inputs/standard_cell_bbm_hlswap_analyze.py'),
                '--run-dir',str(run),'--output-dir',str(run/'derived')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result=json.loads((run/'derived/result.json').read_text());m=result['cell_measurements']
            self.assertEqual(result['cell_variant'],VARIANT);self.assertIsNone(result['acceptance_pass'])
            self.assertEqual(len(result['selected_mos_pair_extrema']),738)
            self.assertAlmostEqual(result['selected_mos_pair_extrema']['XDUT.XBBM0.XD_HD.X005.XLIB.MM1:gd']['max'],1.07)
            self.assertTrue(m['physical_command_phase_reference_settling']['select_high']['nodes']['xdut.xcdac.bn0']['diagnostic_established'])
            self.assertFalse(m['legacy_halfVDD_window_switching_diagnostic']['select_high']['nodes']['xdut.xcdac.bn0']['established_within_window'])
            self.assertFalse(m['physical_command_phase_reference_settling']['select_low']['nodes']['xdut.xcdac.bp0']['diagnostic_established'])
            for q in m['delay_leg_reset_diagnostics'].values():
                for x in q['nodes'].values():self.assertTrue(x['diagnostic_reset_complete'])
            self.assertLess(abs(m['CODE_source_and_input_load']['source_minus_load_work_J']),1e-23)
            self.assertTrue(all(abs(q['work_closure_residual_J'])<1e-23 for q in m['internal_driver_load_work'].values()))
            self.assertGreater(m['reference_control_direct_VDD_energy_J']['H_driver_stdcell'],0)
            self.assertEqual(len(m['body_forward_polarity']),246)
            export=next(x for x in result['native_exports'] if x['file']=='cell.native.f64le.gz')
            self.assertEqual((export['rows'],len(export['columns'])),(len(rows),441))
            whole=m['all_terminal_native_phase_time']
            self.assertEqual(whole['raw_all_voltage_native_points'],len(rows))
            self.assertEqual(set(whole['phases']),{'full','CODE_rise','CODE_fall'})
            for name,q in whole['phases'].items():self.assertEqual(len(q['pairs']),738)
            pair=whole['phases']['full']['pairs']['XDUT.XBBM0.XD_HD.X005.XLIB.MM1:gs']
            self.assertAlmostEqual(pair['max_V'],1.07)
            self.assertGreater(pair['absolute_above_limit_duration_s'],0)
            self.assertTrue(pair['strict_native_exceed'])
            self.assertEqual(whole['NAND_native_phase_witnesses']['H']['actual_DGSB_nodes'][1],'xdut.xbbm0.hd')
            self.assertEqual(whole['NAND_native_phase_witnesses']['L']['actual_DGSB_nodes'][1],'xdut.xbbm0.ld')
            self.assertAlmostEqual(above_duration(0,0,1,2,1,0,1),.5)
            self.assertAlmostEqual(above_duration(0,0,1,2,1,.25,.75),.25)
            self.assertAlmostEqual(above_duration(0,-2,1,2,1,0,1),.5)
            missing=copy.deepcopy(result);missing['half_vdd_events']['xdut.gpn0']=[]
            mm=measurements(cell.metrics,missing,cfg,str(run/'derived'))
            self.assertEqual(mm['actual_correct_ON_settling']['select_low']['status'],'missing_or_ambiguous_controls')


if __name__=='__main__':
    unittest.main()

