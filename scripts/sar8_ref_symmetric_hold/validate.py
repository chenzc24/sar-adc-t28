"""Evidence acceptance; does not equate correct codes with SOA acceptance."""
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha

def main():
    c=read(VERIFY/'comparison.json');assert c['complete'] and len(c['cases'])==4
    assert read(VERIFY/'source_validation.json')['status']=='PASS'
    assert read(VERIFY/'remote_receipts.json')['all_match']
    helper=ROOT/'scripts/sar8_ref_symmetric_hold/diagnostic.va'
    for name,m in c['cases'].items():
        ctx=read(OUT/name/'context.json')
        assert sha(helper)==ctx['helper_sha256']
        assert sha(OUT/name/'dut.scs')==ctx['DUT_sha256']
        assert sha(OUT/name/'test.scs')==ctx['deck_sha256']
        assert sha(OUT/name/'r4_perf_monitor.va')==ctx['monitor_sha256']
        assert m['codes']==[243,12,127,128,127,145]
        assert m['all_codes_pass'] and m['timing_pass'] and m['idle_pass']
        assert m['max_hold_enable_when_sample_high']==0
        assert m['max_high_low_enable_overlap']==0
        assert m['wrong_command_samples']==0
        assert m['min_all_frames_late_idle_enable']>.999
        assert m['sample_rises_ns_max_delta_ps']<.1 and m['sample_falls_ns_max_delta_ps']<.1
        assert m['reset_margin_to_sample_ns']>24
        assert m['max_bottom_error_before_sample_mv']<1.7578125
        assert sha(OUT/(name+'_window.npz'))==m['cache_sha256']
        assert sha(OUT/(name+'_peak.npz'))==m['peak_cache_sha256']
        base=c['cases']['null_ff_'+('125' if m['temperature_c']==125 else 'm40')]
        assert m['effective_settings']==base['effective_settings']
        w=dict(np.load(OUT/(name+'_window.npz')));t=w['time']*1e9
        # Explicit post-RST4 continuity while RST3..0 reset, not just late static hold.
        t4=next(e['start_ns'] for e in m['reset_events'] if e['bit']==4)
        t0=next(e['start_ns'] for e in m['reset_events'] if e['bit']==0)
        mask=(t>t4+.02)&(t<t0+.5)
        assert min(w['xdut.xref.xdrv4.enh_gnn'][mask])>.999
        assert min(w['xdut.xref.xdrv4.enl_gpp'][mask])>.999
    for row in read(VERIFY/'null_comparison.json')['cases']:
        assert row['codes_old']==row['codes_null']
        # Instrumented null adds crossing breakpoints: bound observed numerical
        # differences to20uV (well below CX's100uV relative scale at1V).
        assert abs(row['reference_peak_delta_mv'])<.02
        assert row['held_error_max_delta_mv']<.01
        assert max(row['timing_deltas'].values())<.1
    for row in read(VERIFY/'figures.json').values():assert sha(ROOT/row['path'])==row['sha256']
    result=dict(status='PASS',native_cases=4,correct_codes=24,native_MOS_unchanged=1833,
      phase_and_hold_checks=True,sample_edges_within_0p1ps_of_null=True,
      circuit_reference_SOA_pass={n:not m['reference_peak']['exceed'] for n,m in c['cases'].items()},
      scope='Diagnostic evidence acceptance only; no baseline promotion or real keeper qualification')
    dump(VERIFY/'validation.json',result);print(result)

if __name__=='__main__':main()
