"""Focused structure and streaming-protocol probes; no Spectre or remote use."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import build_feedback_fixture as b

P=b.OUT
spec=importlib.util.spec_from_file_location('native_support',P/'native_support.py')
support=importlib.util.module_from_spec(spec);sys.modules['native_support']=support;spec.loader.exec_module(support)
spec=importlib.util.spec_from_file_location('feedback_probe',P/'feedback_analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def cfg():return json.loads((P/'measurement.json').read_bytes())


def pw(t,start,end):
    if t<=start or t>=end+.1:return 0.
    if t<start+.1:return .9*(t-start)/.1
    if t<=end:return .9
    return .9*(end+.1-t)/.1


def rows(c,missing=()):
    times={0.,18.,18.1,20.,20.1,99.,100.}
    for i in range(8):
        base=21.+5*i
        times.update(base+x for x in [0,.05,.1,.5,1,1.05,1.1,1.2,1.5,1.55,1.6,1.7,1.75,1.8,1.9,2,2.05,2.1,2.2,2.3,2.4,2.5,3.9])
    r=c['roles'];names=[support.norm(n) for n in c['voltage_saves']+c['current_saves']]
    result=[]
    for t in sorted(times):
        v=dict.fromkeys(names,0.);v[r['rail']]=.9;v[r['topp']]=.45087890625;v[r['topn']]=.44912109375
        v[r['sample']]=.9 if t<=20 else max(0.,.9*(20.1-t)/.1)
        v[r['init']]=.9 if t<=18 else max(0.,.9*(18.1-t)/.1)
        for name in ['comp_p','comp_n','x','y','pr','nr']:v[r[name]]=.9
        advanced=sum(t>=21+5*i+1.7 for i in range(8));token=7-advanced
        if token>=0:v[c['tokens'][token]]=.9
        for i in range(8):
            base=21+5*i
            if base<t<base+2.1:
                v[r['clock']]=pw(t,base,base+2)
                if t>=base+.5:
                    v[r['comp_n']]=v[r['nr']]=0.;v[r['raw']]=v[r['dec']]=v[r['data']]=.9
            if i not in missing:v[r['write']]=max(v[r['write']],pw(t,base+1,base+2.2))
            v[r['update']]=max(v[r['update']],pw(t,base+1.5,base+2.4))
            v[r['clock_reset']]=max(v[r['clock_reset']],pw(t,base+1.75,base+2.5))
            if i not in missing and t>=base+1.2:v[c['data_nodes'][7-i]]=.9
        for n,d in zip(c['ref_q_nodes'],c['data_nodes']):v[n]=v[d]
        v['vvdd:1']=-1e-6
        result.append((t*1e-9,v))
    return result


def psf(c,data,truncate=False):
    names=[support.norm(n) for n in c['voltage_saves']+c['current_saves']]
    alias=c['roles']['clock'];lines=['HEADER','SWEEP','"time" "sweep" FLOAT DOUBLE','TRACE']
    for n in names:
        if n==alias:lines+=['"%s" GROUP 1'%n,'"clock_native" FLOAT DOUBLE']
        else:lines.append('"%s" FLOAT DOUBLE'%n)
    lines.append('VALUE');last={}
    for t,v in data:
        lines.append('"time" %.17g'%t)
        for n in names:
            if last.get(n)==v[n]:continue
            lines.append('"%s" %.17g'%('clock_native' if n==alias else n,v[n]))
        last=v
    if not truncate:lines+=['END','']
    return '\n'.join(lines)


class Feedback(unittest.TestCase):
    def test_native_core_loads_cut_and_exact_saves(self):
        m=json.loads((P/'manifest.json').read_bytes());c=cfg();deck=(P/'test.scs').read_text(encoding='utf-8')
        self.assertEqual((m['core_MOS'],m['reference_receive_MOS'],m['total_MOS']),(783,674,1457))
        self.assertEqual(len(m['physical_cut']),32)
        for cut in m['physical_cut'].values():
            self.assertEqual(len(cut['retained_native_drains']),2)
            self.assertEqual(len(cut['removed_downstream_gate_terminals']),2)
        self.assertEqual(len(c['mos_pairs']),1457*6)
        self.assertEqual(len(m['CDAC_instances']),18)
        self.assertNotIn('VCMP',deck);self.assertNotIn('VTOKEN',deck)
        self.assertEqual(sum(line.startswith('COUT') for line in deck.splitlines()),8)
        self.assertEqual([line[5:] for line in deck.splitlines() if line.startswith('save ')],c['voltage_saves']+c['current_saves'])
        native=b.d.blocks(b.SOURCE.read_text(encoding='utf-8'));defs=b.d.blocks((P/'cells.scs').read_text(encoding='utf-8'))
        for n,h in m['unchanged_native_subcircuits'].items():
            self.assertEqual(b.sha(native[n].encode()),h);self.assertEqual(defs[n],native[n])
        for n,h in m['input_hashes'].items():self.assertEqual(b.sha((P/n).read_bytes()),h)
        self.assertLessEqual(c['max_output_bytes'],29*1024**2)

    def run_reduce(self,c,data,truncate=False,managed=False):
        with tempfile.TemporaryDirectory(dir=b.HERE) as temp:
            temp=Path(temp)
            if managed:
                (temp/'inputs').mkdir();(temp/'raw').mkdir()
                for n in c['required_input_sha256']:(temp/'inputs'/n).write_bytes((P/n).read_bytes())
                (temp/'inputs/measurement.json').write_text(json.dumps(c),encoding='ascii')
                (temp/'simulation.state.json').write_text(json.dumps(dict(status='complete',exit_code=0,native=dict(native_analysis_pass=True,zero_error_footer=True))),encoding='ascii')
                (temp/'raw/logStatus').write_text('tran_feedback PASS\n',encoding='ascii')
                (temp/'spectre.out').write_text('save %d (voltage)\nsave %d (current)\nNumber of accepted tran steps = %d\n'%(len(c['voltage_saves']),len(c['current_saves']),len(data)-1),encoding='ascii')
                native=temp/'raw/probe.tran.tran';native.write_text(psf(c,data,truncate),encoding='ascii')
                result=a.analyze(str(temp),str(temp/'derived'))
                self.assertEqual(json.loads((temp/'derived/result.json').read_bytes())['native_points'],len(data))
                self.assertLess(sum(p.stat().st_size for p in (temp/'derived').iterdir()),c['max_output_bytes'])
            else:
                native=temp/'tran.tran';native.write_text(psf(c,data,truncate),encoding='ascii')
                out=support.Output(str(temp/'derived'),c['max_output_bytes'])
                result=a.reduce(str(native),c,out)
            wave=gzip.decompress((temp/'derived/wave.native.f64le.gz').read_bytes())
            self.assertEqual(hashlib.sha256(wave).hexdigest(),result['waveform']['uncompressed_sha256'])
            self.assertEqual(len(wave),len(data)*8*len(result['waveform']['columns']))
            return result

    def test_eight_token_stream_sparse_group_and_all_mos_screens(self):
        c=cfg();data=rows(c)
        # A late, otherwise unused core node excursion must still be screened.
        node=c['mos_pairs'][0]['nodes'][0]
        for t,v in data:
            if t==99e-9:v[node]=2.1
        result=self.run_reduce(c,data,managed=True)
        self.assertTrue(result['protocol_eight_pass']);self.assertEqual(result['token_sequence'],list(range(7,-1,-1)))
        self.assertEqual(result['event_counts'],dict(clock=8,clock_fall=8,write=8,update=8,reset=8))
        self.assertEqual(len(result['mos_pair_extrema']),8742)
        self.assertGreater(result['mos_screen_exceeded_records'],0)
        self.assertTrue(all(x['first_reset_ready_native'] is not None for x in result['cycles']))
        self.assertEqual(result['cycles'][-1]['stored_bit_after_recovery'],1)

    def test_missing_write_never_becomes_empty_list_success(self):
        c=cfg()
        result=self.run_reduce(c,rows(c,missing=(4,)))
        self.assertFalse(result['protocol_eight_pass']);self.assertFalse(result['cycles'][4]['protocol_pass'])
        self.assertEqual(result['cycles'][4]['write_count'],0)
        self.assertFalse(result['cycles'][4]['stored_bit_matches_positive_input'])
        self.assertEqual(result['cycles'][4]['token_bit'],3)

    def test_truncated_native_history_fails(self):
        c=cfg()
        with self.assertRaisesRegex(ValueError,'Missing native END'):
            self.run_reduce(c,rows(c),truncate=True)


if __name__=='__main__':unittest.main()
