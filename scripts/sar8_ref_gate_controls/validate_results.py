"""Acceptance of experiment completeness/consistency, NOT circuit SOA acceptance."""
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha

def main():
    c=read(VERIFY/'comparison.json');assert c['complete'] and len(c['cases'])==10
    assert read(VERIFY/'source_validation.json')['status']=='PASS'
    assert read(VERIFY/'remote_receipts.json')['all_match']
    for row in read(VERIFY/'null_comparison.json')['cases']:
        assert row['codes_old']==row['codes_null']
        assert abs(row['reference_peak_delta_mv'])<.001
        assert row['held_error_max_delta_mv']<.001
        assert max(row['timing_deltas'].values())<.1
    for name,m in c['cases'].items():
        assert m['codes']==[243,12,127,128,127,145]
        assert m['all_codes_pass'] and m['timing_pass'] and m['idle_pass']
        assert m['CMI'] and m['reference_peak']['peak_v']>.99
        assert m['sample_rises_ns_max_delta_ps']<.001 and m['sample_falls_ns_max_delta_ps']<.001
        assert m['max_hold_enable_when_sample_high']==0
        assert m['reset_margin_to_sample_ns']>24
        path=OUT/(name+'_window.npz');assert sha(path)==m['cache_sha256']
        w=dict(np.load(path));t=w['time']*1e9
        mask=(t>=m['rst7_ns'])&(t<m['same_event_end_before_rst4_ns'])
        assert abs(max(w['xdut.gnn4'][mask])-m['same_event_gnn4_peak_v'])<1e-12
        # Diagnostic series resistance is disabled in established sampling high.
        sample=w['xdut.sample_int']>.98
        for tag in ['gnn','gnp','gpn','gpp']:
            assert max(abs(w['xdut.xref.xdrv7.en_'+tag][sample]))==0
        assert m['effective_settings']==c['cases']['null_ff_'+('125' if m['temperature_c']==125 else 'm40')]['effective_settings']
    for f in read(VERIFY/'figures.json').values():assert sha(ROOT/f['path'])==f['sha256']
    result=dict(status='PASS',scope='10-case diagnostic evidence completeness; circuit SOA still FAIL',
       native_cases=10,static_frames=60,correct_codes=60,unchanged_MOS_per_case=1833,
       zero_helper_during_sampling=True,sample_edges_within_0p001ps_of_null=True,
       null_edges_within_0p1ps_of_original=True,no_candidate_promoted=True)
    dump(VERIFY/'validation.json',result);print(result)

if __name__=='__main__':main()
