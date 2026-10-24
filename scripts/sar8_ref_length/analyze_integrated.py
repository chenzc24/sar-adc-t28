"""Matched five-point source, timing, code and stress comparison; never promotes OA."""
import gc
import gzip
import importlib.util
import json
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha

def compact(w,report):
    t=w['time']*1e9;sup=report['vdd']
    def at(n,x):return float(np.interp(x,t,w[n]))
    def edges(n,up=True):
        v=w[n];h=sup/2
        ix=np.flatnonzero((v[:-1]<h)&(v[1:]>=h) if up else (v[:-1]>h)&(v[1:]<=h))
        return t[ix]+(h-v[ix])*(t[ix+1]-t[ix])/(v[ix+1]-v[ix])
    ct,wt,ut=[edges(n) for n in ['xdut.cmp_clk','xdut.xctrl.phi_w','xdut.phi_u']]
    assert len(ct)==len(wt)==len(ut)==8
    def word(prefix,x):return int(sum((at(prefix+str(b),x)>sup/2)*(1<<b) for b in range(8)))
    bits=[]
    for i,(c,u) in enumerate(zip(ct,ut)):
        bits.append(dict(bit=7-i,compare_ns=float(c),update_ns=float(u),
            wait_since_last_update_ns=float(c-ut[i-1]) if i else None,
            trial_word=word('xdut.xref.q',c-.01),
            top_before_mv=(at('xdut.topp',c-.01)-at('xdut.topn',c-.01))*1000,
            span_before_mv=(at('vrefp',c-.01)-at('vrefn',c-.01))*1000))
    pp,nn=at('vrefp',130),at('vrefn',130)
    return dict(codes=[f['code'] for f in report['frames']],static_code_pass=report['static_code_pass'],
      post_startup_static_code_pass=report['post_startup_static_code_pass'],
      startup_code=report['frames'][0]['code'],startup_ideal=report['frames'][0]['allowed_ideal_codes'],
      post_startup_max_preclose_error_mv=max(abs(f['preclose_error_v'])*1000 for f in report['frames'][1:]),
      post_startup_max_held_error_mv=max(abs(f['held_error_v'])*1000 for f in report['frames'][1:]),
      timing_pass=report['all_timing_pass'],idle_pass=report['all_idle_pass'],
      preclose_errors_mv=[f['preclose_error_v']*1000 for f in report['frames']],
      held_errors_mv=[f['held_error_v']*1000 for f in report['frames']],
      net_turnoff_deltas_mv=[(f['held_error_v']-f['preclose_error_v'])*1000 for f in report['frames']],
      turnoff_scope='Held at frame+41.8ns minus sample-enable50%-0.2ns; includes settling/feedthrough/coupling, not isolated charge injection.',
      reference_span_130ns_mv=(pp-nn)*1000,reference_p_130ns_v=pp,reference_n_130ns_v=nn,
      source_p_130ns_ua=(.9-pp)/50*1e6,source_n_130ns_ua=nn/50*1e6,
      source_scope='Series-50ohm source current at130ns, not separate transistor probes. FF hot platform is steady; other PVT points can include decap charging/common-mode drift (see120to140ns drift fields).',
      reference_p_120to140ns_drift_uv=(at('vrefp',140)-at('vrefp',120))*1e6,
      reference_n_120to140ns_drift_uv=(at('vrefn',140)-at('vrefn',120))*1e6,
      sample_close_ns=float(edges('xdut.seq_sample',False)[0]),
      acquisition_ns=report['frames'][1]['acquisition_ns'],
      max_conversion_ns=max(f['conversion_ns'] for f in report['frames']),
      max_precompare_last100ps_movement_mv=max(abs(x)*1000 for f in report['frames'] for x in f['top_delta_last100ps_before_compare_v']),
      CMI=report['CMI'],stress_failure_count=report['stress_failure_count'],
      stress_failing_MOS_count=report['stress_failing_MOS_count'],stress_groups=report['groups'],
      effective_settings=report['effective_settings'],bits=bits,native_psf_sha256=report['native_psf_sha256'])

def main():
    spec=importlib.util.spec_from_file_location('pvtchecks',ROOT/'scripts/sar8_pvt_mismatch/analyze.py')
    checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
    checks.OUT=OUT;checks.VERIFY=VERIFY
    rows=[]
    for name in read(VERIFY/'integrated_setup.json')['names']:
        source=read(OUT/name/'context.json')['source_case'];cases={}
        for role,case in [('baseline',source),('candidate',name)]:
            if role=='candidate':report,raw=checks.analyze(case)
            else:
                folder=ROOT/'output/sar8_main_width'/case
                path=folder/'reduced/reduced.json.gz'
                assert sha(path)==read(folder/'reduced_receipt.json')['compressed_sha256']
                with gzip.open(path,'rt') as f:raw=json.load(f)
                report=read(ROOT/'verification/sar8_main_width'/(case+'.json'))
            t=np.array(raw['wave']['time']);mask=(t>=100e-9)&(t<200e-9)
            w={k:np.array(v)[mask] for k,v in raw['wave'].items()}
            del raw;gc.collect()
            cases[role]=compact(w,report)
            cache=OUT/(case+'.npz');np.savez_compressed(cache,**w)
            cases[role].update(case=case,cache_sha256=sha(cache))
            del w;gc.collect()
        b,c=cases['baseline'],cases['candidate']
        assert c['effective_settings']==b['effective_settings']
        cases['sample_close_change_ps']=(c['sample_close_ns']-b['sample_close_ns'])*1000
        cases['acquisition_change_ps']=(c['acquisition_ns']-b['acquisition_ns'])*1000
        rows.append(cases)
        dump(VERIFY/'integrated_comparison.json',dict(points=rows,complete=len(rows)==5,
            sampling_budget_mv=.25*1.8/256*1000,
            scope='Five static six-input PVT screens, selected2um Bootstrap; only reference-switch L30->90. No noise/mismatch/PEX/full-code/FFT. No OA update.',
            ideal_codes=[[243],[12],[127,128],[128],[127],[145]]))
        print(source,b['codes'],'->',c['codes'],'source uA',b['source_p_130ns_ua'],'->',c['source_p_130ns_ua'],flush=True)

if __name__=='__main__':main()
