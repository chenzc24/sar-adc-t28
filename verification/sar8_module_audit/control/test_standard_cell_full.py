"""Focused storage-migration invariants and native observer failure paths."""
import copy
import gzip
import json
from pathlib import Path
import struct
import tempfile
import unittest

import prepare_standard_cell_full as prepare
import standard_cell_full_analyze as analyze


class StandardStorageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe=prepare.read(prepare.OUT/'library_probe.json')
        cls.original,cls.mapping=prepare.source()
        cls.candidate,cls.pairs,cls.changed=prepare.candidate(cls.original)
        cls.bench,cls.observers,cls.boundaries,cls.loadcount=prepare.loaded_fixture(cls.candidate,cls.mapping,cls.probe)

    def test_actual_library_state_contract_and_complete_migration(self):
        truth=prepare.library_truth(self.probe)
        self.assertEqual(len(truth['ideal_rising_transfer']),8)
        self.assertFalse(truth['dynamic_native_timing_verified'])
        self.assertEqual(len(self.probe['cells'][prepare.FF]['MOS']),28)
        manifest=prepare.migration_manifest(self.original,self.candidate,self.pairs,self.changed,self.mapping,self.probe)
        self.assertEqual(len(manifest['ordinary_reference_pairs']),96)
        self.assertEqual(len(manifest['retained_custom_core_MOS']),60)
        self.assertTrue(manifest['reference_Rgate_and_real_CDAC_retained'])
        self.assertEqual(manifest['fitted_equivalent_load_capacitors_added'],0)
        # Pin/model compatibility is checked on every project and foundry call.
        cells=prepare.base.cells(self.candidate)
        for block in cells.values():
            for item in prepare.base.parts(block).values():
                if item['model'] in cells:
                    self.assertEqual(len(item['nodes']),len(prepare.header(cells[item['model']])))
                elif item['model'] in self.probe['cells']:
                    self.assertEqual(len(item['nodes']),len(self.probe['cells'][item['model']]['pins']))
        self.assertNotIn('EXTERNAL_FOUNDRY_PARAMETERS',self.candidate)
        self.assertFalse(any(p['model'] in ['nch_mac','pch_mac']
                            for k in ['sar8p_inv','sar8p_nand2','sar8p_clkbuf','sar8p_dffr']
                            for p in prepare.base.parts(cells[k]).values()))

    def test_all26_native_immediate_fanouts_and_corner_inputs(self):
        full,_=prepare.expand_library(self.candidate,'sar_adc8_join_r4',self.probe,
             {k:k for k in prepare.header(prepare.base.cells(self.candidate)['sar_adc8_join_r4'])})
        root=dict(VDD='VDD!',VSS='0',**{k:k for k in ['SR_R','SR_S','FF_CK','FF_D','FF_RST','CONTEXT']})
        bench,_=prepare.expand_library(self.bench,'sar8audit_std_storage',self.probe,root)
        units={u['instance']:u for u in self.mapping['units']}
        for observer in self.observers:
            path=observer['source_instance'];node=units[path]['ports']['Q'];q=observer['Q']
            expected=sum(v['model'].startswith(('nch_','pch_')) and v['nodes'][1]==node
                         and not p.startswith(path+'.') for p,v in full.items())
            actual=sum(v['model'].startswith(('nch_','pch_')) and v['nodes'][1]==q
                       and not p.startswith('XDUT.X'+observer['name']+'.') for p,v in bench.items())
            self.assertEqual(actual,expected,(path,actual,expected))
        self.assertEqual(len(self.observers),26)
        self.assertEqual(sum(o['kind']=='SR' for o in self.observers),2)
        self.assertEqual(sum(o['kind']=='DFF' for o in self.observers),24)
        self.assertEqual(self.loadcount,76)
        self.assertNotIn('vsource',self.bench)
        for vdd in [.99,.81]:
            cfg=prepare.measurement(self.bench,self.observers,self.probe,vdd)
            self.assertEqual(len(cfg['stress_voltage_pairs']),6*len(cfg['observed_mos']))
            for mos in cfg['observed_mos']:
                self.assertTrue(all(mos+':'+str(i) in cfg['current_saves'] for i in range(1,5)))
            self.assertEqual(cfg['critical_kcl_nodes'],[])
            self.assertTrue(cfg['kcl_terms']) # all full-history residuals retained
            for p in prepare.ff_phases():
                self.assertEqual(p['Q'],0 if p['RST'] else p['Q'])
            values=[float(line.split()[1]) for line in prepare.pwl(prepare.ff_phases(),'D',vdd).splitlines()]
            self.assertEqual(set(values),{0.,vdd})

    def synthetic_table(self,folder,damage=False,missing_hold=False):
        # Minimal independent SR+FF observers use actual phase contracts.
        obs=[dict(name='S',source_instance='SOURCE.SR',kind='SR',Q='Q',QB='QB',R='R',S='S'),
             dict(name='F',source_instance='SOURCE.FF',kind='DFF',Q='FQ',CK='CK',D='D',RST='RST',CDN='CDN')]
        spec=dict(observers=obs,SR_phases=prepare.sr_phases(),DFF_phases=prepare.ff_phases(),
                  hold_rail_low=.1,hold_rail_high=.9,collection_cap_bytes=30*1024**2,
                  user_collection_cap_bytes=32*1024**2,final_state_reserve_bytes=256*1024)
        cfg=dict(storage=spec,source_history_stop_s=prepare.STOP)
        names=['time','vdd!','q','qb','r','s','fq','ck','d','rst','cdn']
        (folder/'peak.columns.json').write_text(json.dumps(dict(names=names)))
        times=sorted(set([i*.1e-9 for i in range(201)]+[i*1e-9+.02e-9 for i in range(1,20)]))
        pack=struct.Struct('<'+'d'*len(names))
        with (folder/'peak.native.bin').open('wb') as f:
            for at in times:
                # A short20ps input/output propagation interval with both native endpoints.
                index=max(0,min(19,int((at-.01e-9)/1e-9)))
                ph=spec['DFF_phases'][index];sr=spec['SR_phases'][min(index,10)]
                if missing_hold and 2.35e-9<=at<=2.95e-9:continue
                q=sr['Q'];fq=ph['Q']
                if damage and 3.5e-9<=at<=3.6e-9:fq=0
                row=[at,.99,q*.99,sr['QB']*.99,sr['R']*.99,sr['S']*.99,
                     fq*.99,ph['CK']*.99,ph['D']*.99,ph['RST']*.99,(1-ph['RST'])*.99]
                f.write(pack.pack(*row))
        return cfg

    def test_native_observer_hold_error_missing_hold_and_required_column(self):
        with tempfile.TemporaryDirectory(prefix='_std_storage_',dir=prepare.OWN) as t:
            out=Path(t);cfg=self.synthetic_table(out)
            result=analyze.observe_history(str(out),cfg)
            self.assertTrue(result['stable_hold_observation_pass'])
            self.assertTrue(result['clean_expected_Q_edge_patterns'])
            cfg=self.synthetic_table(out,damage=True)
            failed=analyze.observe_history(str(out),cfg)
            self.assertFalse(failed['stable_hold_observation_pass'])
            self.assertFalse(failed['clean_expected_Q_edge_patterns'])
            cfg=self.synthetic_table(out,missing_hold=True)
            unknown=analyze.observe_history(str(out),cfg)
            self.assertIsNone(unknown['stable_hold_observation_pass'])
            header=json.loads((out/'peak.columns.json').read_bytes());header['names'].remove('q')
            (out/'peak.columns.json').write_text(json.dumps(header))
            with self.assertRaisesRegex(ValueError,'column missing'):analyze.observe_history(str(out),cfg)

    def test_lossless_history_and_whole_collection_cap(self):
        with tempfile.TemporaryDirectory(prefix='_std_budget_',dir=prepare.OWN) as t:
            run=Path(t);out=run/'derived';out.mkdir();raw=run/'raw';raw.mkdir()
            cfg=self.synthetic_table(out);original=(out/'peak.native.bin').read_bytes()
            (raw/'original_psf').write_bytes(b'ORIGINAL_RAW')
            proof=analyze.compress_history(str(out))
            self.assertTrue(proof['decompressed_bytes_and_SHA_match'])
            self.assertEqual(gzip.open(out/'peak.native.bin.gz','rb').read(),original)
            self.assertEqual((raw/'original_psf').read_bytes(),b'ORIGINAL_RAW')
            self.assertFalse((out/'peak.native.bin').exists())
            for p in ['simulation.state.json','analysis.state.json','simulation.admission.json',
                      'analysis.admission.json','source_provenance.json']:(run/p).write_text('{}')
            (raw/'logStatus').write_text('tran_first PASS\n');(run/'spectre.out').write_text('SYNTHETIC\n')
            good=analyze.collection_budget(str(run),str(out),cfg,pending_result_bytes=8*1024**2)
            self.assertLess(good['projected_bytes'],30*1024**2)
            with (run/'spectre.out').open('wb') as f:f.truncate(31*1024**2)
            with self.assertRaisesRegex(ValueError,'exceeds30MiB'):
                analyze.collection_budget(str(run),str(out),cfg,8*1024**2)


if __name__=='__main__':unittest.main()
