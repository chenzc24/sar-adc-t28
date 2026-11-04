"""Source-derived timing and explicit reset/write boundaries, synthetic only."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

import prepare_kickback_actual_timing as p
from prepare_kickback_savefix import validate_saves
import test_kickback as synthetic


def clock_points(text):
    tokens=re.search(r'(?m)^VCMP_CLK \(CMP_CLK 0\) vsource type=pwl wave=\[([^\]]+)\]$',text)[1].split()
    return [(float(tokens[i][:-1]),tokens[i+1] if tokens[i+1]=='SUP' else float(tokens[i+1]))
            for i in range(0,len(tokens),2)]


def halves(points):
    found=[]
    for (t0,v0),(t1,v1) in zip(points,points[1:]):
        v0=.9 if v0=='SUP' else v0;v1=.9 if v1=='SUP' else v1
        if v0<.45<=v1 or v0>.45>=v1:found.append((int(v1>v0),(t0+(.45-v0)*(t1-t0)/(v1-v0))*1e-9))
    return found


class ActualClock(unittest.TestCase):
    def test_shortest_complete_native_pair_is_replayed_without_mixed_extrema(self):
        e=p.source_evidence();best=e['selected_shortest_rise_interval'];pairs=e['adjacent_pairs']
        self.assertEqual(len(pairs),14)
        self.assertEqual((best['frame'],best['from_bit'],best['to_bit']),(1,6,5))
        self.assertEqual(best,min(pairs,key=lambda v:v['rise_interval_s']))
        self.assertNotEqual(best,e['minimum_low_different_pair'])
        hh=halves(clock_points((p.DEST/'test.scs').read_text()))[:4]
        self.assertEqual([up for up,at in hh],[1,0,1,0])
        measured=[hh[1][1]-hh[0][1],hh[2][1]-hh[1][1],hh[3][1]-hh[2][1],hh[2][1]-hh[0][1]]
        for actual,key in zip(measured,['high1_s','low_s','high2_s','rise_interval_s']):
            self.assertAlmostEqual(actual,best[key],delta=1e-20)

    def test_hardware_other_sources_targets_and_budget_unchanged(self):
        old=(p.SOURCE/'test.scs').read_text();new=(p.DEST/'test.scs').read_text()
        self.assertEqual([s for s in old.splitlines() if not s.startswith('VCMP_CLK ')],
                         [s for s in new.splitlines() if not s.startswith('VCMP_CLK ')])
        self.assertEqual([(t,v) for t,v in clock_points(old) if t>=100],[(t,v) for t,v in clock_points(new) if t>=100])
        for name in ['cells.scs','cdac_load.scs','initializer.va']:self.assertEqual((p.SOURCE/name).read_bytes(),(p.DEST/name).read_bytes())
        oldcfg=json.loads((p.SOURCE/'measurement.json').read_bytes());cfg=json.loads((p.DEST/'measurement.json').read_bytes())
        self.assertEqual([v['target_diff_v'] for v in oldcfg['cycles']],[v['target_diff_v'] for v in cfg['cycles']])
        self.assertEqual(cfg['cycles'][1]['release_end_s'],cfg['cycles'][0]['release_end_s'])
        for name,h in cfg['required_input_sha256'].items():self.assertEqual(p.sha((p.DEST/name).read_bytes()),h)
        self.assertEqual(validate_saves(p.DEST,cfg)['resolved_requests'],81)
        a=json.loads((p.SOURCE/'recipe_proposal.json').read_bytes());b=json.loads((p.DEST/'recipe_proposal.json').read_bytes())
        self.assertEqual(a['resources'],b['resources']);self.assertEqual(a['spectre_args'],b['spectre_args']);self.assertEqual(a['expected_stop_s'],b['expected_stop_s'])

    def test_late_resolution_late_D0_and_unassigned_writes_cannot_fake_success(self):
        spec=importlib.util.spec_from_file_location('actual_measurement',p.DEST/'kickback_analyze.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cfg=json.loads((p.DEST/'measurement.json').read_bytes());first=cfg['cycles'][0]
        times={0.,18e-9,18.1e-9,22e-9,39.9e-9,40e-9,40.1e-9,260e-9}
        for c in cfg['cycles']:
            times.update([c['release_start_s'],c['release_end_s']+1e-15,c['start_s'],c['start_s']+.05e-9,c['start_s']+.1e-9,
                c['clock_fall_start_s']-.01e-9,c['clock_fall_start_s'],
                c['clock_fall_start_s']+.02e-9,c['clock_fall_start_s']+.04e-9,
                c['clock_fall_end_s'],c['clock_fall_end_s']+.1e-9])
        points=clock_points((p.DEST/'test.scs').read_text())
        # CINIT waveform is unchanged from hold2; read its literal source.
        tokens=re.search(r'(?m)^VINIT \(CINIT 0\) vsource type=pwl wave=\[([^\]]+)\]$',(p.DEST/'test.scs').read_text())[1].split()
        init=[(float(tokens[i][:-1]),tokens[i+1] if tokens[i+1]=='SUP' else float(tokens[i+1])) for i in range(0,len(tokens),2)]
        rows=[]
        for t in sorted(times):
            v={n:.45 for n in cfg['voltage_saves']};v.update({n:0. for n in cfg['current_saves']})
            v.update({'vdd!':.9,'cmp_clk':synthetic.interp(points,t*1e9),'cinit':synthetic.interp(init,t*1e9),'vvdd:1':-1e-6})
            for arm in cfg['arms'].values():
                v[arm['comp_p']]=.9;v[arm['comp_n']]=.9;v[arm['data']]=0.;v[arm['write']]=0.
                v[arm['d0']]=.9 if t>=22e-9 else 0.
            active=cfg['arms']['evaluate']
            # Deliberate unresolved-before-reset/late-output and stale-D0 fixtures.
            if first['clock_fall_start_s']+.02e-9<=t<first['clock_fall_end_s']:
                v[active['comp_n']]=.1
            if first['clock_fall_start_s']+.04e-9<=t<first['clock_fall_end_s'] or 40e-9<=t<40.1e-9:
                v[active['write']]=.9
            rows.append((t,v))
        with tempfile.TemporaryDirectory(prefix='_actual_interval_',dir=p.HERE) as folder:
            root=Path(folder);self.assertTrue(root.resolve().is_relative_to(p.HERE.resolve()))
            raw=root/'synthetic.tran.tran';raw.write_text(synthetic.psf(cfg,rows,sparse=True,group=True))
            result=module.reduce(str(raw),cfg,module.Output(str(root/'derived'),cfg['max_output_bytes']))
            c0,c1=result['cycles'][:2]
            self.assertIsNone(c0['raw_resolution'])
            self.assertEqual(c0['pre_fall']['D0_v'],0.)
            self.assertEqual(c0['writes'][0]['phase'],'clock_fall')
            self.assertTrue(c0['missing_write_before_reset']);self.assertFalse(c0['nominal_polarity_written_before_reset'])
            self.assertEqual(c1['late_D0_bit'],1)
            self.assertTrue(c1['missing_write_before_reset']);self.assertFalse(c1['nominal_polarity_written_before_reset'])
            self.assertEqual(len(result['unassigned_write_events']),1)
            self.assertIsNone(result['acceptance_pass'])


if __name__=='__main__':unittest.main(verbosity=2)
