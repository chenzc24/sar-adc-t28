"""One paired-history/phase probe; synthetic native data, no simulation."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

import prepare_feedback_history as b
import test_feedback as old
from test_feedback_source_reduce import load


def synthetic(cfg,early=False):
    data=old.rows(cfg);h=cfg['history_case'];r=cfg['roles'];times={t*1e9 for t,v in data}
    start=22.5 if early else 23.99;end=start+.2;mark=23.09
    times.update([23.09,23.0905,23.091]+[start+d for d in [0,.000001,.01,.02,.1,.18,.199999,.2,.201]])
    existing=dict((round(t*1e9,8),v) for t,v in data);out=[]
    # Re-evaluate ordinary digital test stimulus at all added times.
    for t in sorted(times):
        available=max(x for x in existing if x<=round(t,8))
        v=copy.deepcopy(existing[available]);q=max(0.,min(1.,(t-start)/.2))
        # Added points lie after first clock fall or in a declared invalid phase.
        v[r['clock']]=0.
        for i in range(8):v[r['clock']]=max(v[r['clock']],old.pw(t,21+5*i,23+5*i))
        v['hist_mark']=.9*max(0.,min(1.,(t-mark)/.001))
        v['bot_p']=.45+h['bottom_P_step_v']*q;v['bot_n']=.45-h['bottom_P_step_v']*q
        delta=h['nominal_diff_by_cycle_v'][0]+2*b.ALPHA*h['bottom_P_step_v']*q
        if q>=1:delta+=h['HSIGN']*3e-6  # Deliberate unnormalized actual-input deviation.
        v[r['topp']]=.45+.5*delta;v[r['topn']]=.45-.5*delta
        for n in ['comp_p','comp_n','x','y','pr','nr']:v[r[n]]=.9
        v[r['data']]=v[r['raw']]=v[r['dec']]=0.
        for i,bit in enumerate(h['expected_DATA_by_cycle']):
            at=21+5*i
            if at+.5<=t<at+2.1:
                v[r['comp_p']],v[r['comp_n']]=(.9,0.) if bit else (0.,.9)
                v[r['pr']],v[r['nr']]=v[r['comp_p']],v[r['comp_n']]
                v[r['data']]=.9*bit;v[r['raw']]=v[r['dec']]=.9
            v[cfg['data_nodes'][7-i]]=.9*bit if t>=at+1.2 else 0.
        out.append((t*1e-9,v))
    return out


class History(unittest.TestCase):
    def test_pair_charge_scope_and_phase_gate(self):
        scheme=b.OUT/'fixture_scheme.md';self.assertTrue(scheme.is_file())
        configs={};decks={}
        for name,sign,suffix in b.CASES:
            p=b.OUT/name;c=json.loads((p/'measurement.json').read_bytes());configs[name]=c
            decks[name]=(p/'test.scs').read_text(encoding='utf-8')
            m=json.loads((p/'manifest.json').read_bytes())
            proposal=json.loads((p/'recipe_proposal.json').read_bytes())
            self.assertIn('%+dLSB'%(sign*8),proposal['test_conditions']['input'])
            self.assertIn('nominal %+.2fLSB'%(-sign*.25),proposal['test_conditions']['input'])
            self.assertIn('not normalized',proposal['test_conditions']['input'])
            self.assertEqual(proposal['summary_signals'],['topp','topn','cmp_clk','phi_u','bot_p','bot_n'])
            self.assertTrue(set(proposal['summary_signals'])<=set(n.lower() for n in c['voltage_saves']))
            self.assertEqual(m['source_circuit_MOS'],1457);self.assertEqual((m['native_voltage_saves'],m['native_current_saves'],m['wave_columns']),(127,23,60))
            self.assertAlmostEqual(m['ideal_second_diff_v'],-sign*b.SMALL,delta=1e-16)
            self.assertEqual(m['ideal_second_CM_v'],.45)
            for n in m['unchanged_payloads']:self.assertEqual((p/n).read_bytes(),(b.BASE/n).read_bytes())
            self.assertEqual(next(x for x in decks[name].splitlines() if x.startswith('VSAMPLE ')),next(x for x in (b.BASE/'test.scs').read_text(encoding='utf-8').splitlines() if x.startswith('VSAMPLE ')))
            self.assertNotIn('VCMP',decks[name]);self.assertNotIn('VTOKEN',decks[name])
            self.assertIn('XHISTORY (BOT_P BOT_N HIST_MARK CMP_CLK PHI_U VDD! VCM 0)',decks[name])
            self.assertTrue(m['passive_observation_ports']['flattened_native_devices_and_loads_identical'])
            va=(p/'history_charge.va').read_text(encoding='utf-8')
            self.assertEqual(re.findall(r'V\((\w+), ref\)\s*<\+',va),['bottom_p','bottom_n','mark'])
            self.assertNotIn('timer(',va)
            oldcaps=list(b.d.instances(b.d.blocks((b.BASE/'cdac_load.scs').read_text(encoding='utf-8'))['audit_cdac_hold']))
            newcaps=list(b.d.instances(b.d.blocks((p/'cdac_load.scs').read_text(encoding='utf-8'))['audit_cdac_hold']))
            for a,z in zip(oldcaps,newcaps):self.assertEqual((a[0],a[2],a[3]),(z[0],z[2],z[3]))
            for entry in json.loads((p/'recipe_proposal.json').read_bytes())['inputs']:
                self.assertEqual(hashlib.sha256((b.ROOT/entry['source']).read_bytes()).hexdigest(),entry['sha256'])
        self.assertEqual(decks['negative_to_positive'].replace('HSIGN=-1','HSIGN=1'),decks['positive_to_negative'])
        for name,early in [('negative_to_positive',False),('positive_to_negative',False),('negative_to_positive',True)]:
            with self.subTest(case=name,early=early),tempfile.TemporaryDirectory(dir=b.HERE) as temp:
                p=b.OUT/name;c=configs[name];temp=Path(temp);(temp/'inputs').mkdir();(temp/'raw').mkdir()
                recipe=json.loads((p/'recipe_proposal.json').read_bytes())
                for item in recipe['inputs']:(temp/'inputs'/item['name']).write_bytes((p/item['name']).read_bytes())
                rows=synthetic(c,early)
                (temp/'raw/probe.tran.tran').write_text(old.psf(c,rows),encoding='ascii')
                (temp/'raw/logStatus').write_text('tran_feedback PASS\n',encoding='ascii')
                (temp/'spectre.out').write_text('save 127 (voltage)\nsave 23 (current)\nNumber of accepted tran steps = %d\n'%(len(rows)-1),encoding='ascii')
                (temp/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True))),encoding='ascii')
                load('native_support',temp/'inputs/native_support.py');load('feedback_analyze',temp/'inputs/feedback_analyze.py')
                load('history_export',temp/'inputs/history_export.py');a=load('history_probe',temp/'inputs/history_analyze.py')
                result=a.analyze(str(temp),str(temp/'derived'))
                self.assertTrue(result['protocol_eight_pass'])
                self.assertEqual(result['history_assessment_valid'],not early)
                self.assertEqual(result['history_stimulus']['phase_valid'],not early)
                second=result['history_stimulus']['second_actual_precompare']
                self.assertAlmostEqual(second['nominal_target_error_v'],c['history_case']['HSIGN']*3e-6,delta=1e-15)
                self.assertAlmostEqual(second['input_diff_v'],second['absolute_TOPP_v']-second['absolute_TOPN_v'],delta=1e-15)
                self.assertEqual(len(result['mos_pair_extrema']),990);self.assertIsNone(result['full_mos_screen_exceeded_records'])
                self.assertEqual(len(result['waveform']['columns']),60)
                self.assertTrue(result['two_full_native_passes_match'])
                self.assertLess(sum(f.stat().st_size for f in (temp/'derived').iterdir()),29*1024**2)


if __name__=='__main__':unittest.main()
