"""Supply-aware checks from complete native timing samples and all-sample stress."""
import gzip
import json
import re
import numpy as np
from flow import ROOT, OUT, VERIFY, read, dump, sha

def analyze(name):
    folder=OUT/name;ctx=read(folder/'context.json')
    if ctx.get('kind')=='stress_window':return analyze_window(name)
    receipt=read(folder/'reduced_receipt.json')
    assert sha(folder/'reduced/reduced.json.gz')==receipt['compressed_sha256']
    with gzip.open(folder/'reduced/reduced.json.gz','rt') as f:r=json.load(f)
    log=(folder/'reduced/spectre.out').read_text();status=(folder/'reduced/logStatus').read_text()
    assert 'spectre completes with 0 errors' in log and re.search(r'tran_perf\s+PASS',status)
    w={k:np.array(v) for k,v in r['wave'].items()}; t=w['time']*1e9
    sup=ctx.get('vdd',.9); vh=sup/2
    def v(n):return w[n.lower()]
    def edges(n,up=True):
        x=v(n); idx=np.flatnonzero((x[:-1]<vh)&(x[1:]>=vh) if up else (x[:-1]>vh)&(x[1:]<=vh))
        return t[idx]+(vh-x[idx])*(t[idx+1]-t[idx])/(x[idx+1]-x[idx])
    rows=[[float(s) for s in m.split(',')] for m in re.findall(r'R4MEAS,([^\r\n]+)',log)]
    assert [int(r[0]) for r in rows]==list(range(int(ctx['stop_ns']//100)))
    clocks=['XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK']
    ev={n:dict(rise=edges(n),fall=edges(n,False)) for n in clocks+['XDUT.SEQ_SAMPLE','XDUT.SAMPLE_INT']+[f'XDUT.XREF.RST{i}' for i in range(8)]}
    frames=[]
    for row in rows:
        i=int(row[0]);lo=i*100;hi=lo+100;code=int(row[1])
        counts=[int(np.sum((ev[n]['rise']>=lo)&(ev[n]['rise']<hi))) for n in clocks]
        decoded=int(sum((np.interp(hi-2,t,v(f'D{b}'))>vh)*(1<<b) for b in range(8)))
        assert decoded==code
        cap=ev[clocks[-1]]['fall'];cap=cap[(cap>lo+41)&(cap<hi)]
        resets=[ev[f'XDUT.XREF.RST{b}']['rise'] for b in range(8)]
        resets=[x[(x>lo+41)&(x<hi)] for x in resets]
        ordered=all(len(x)==1 for x in resets) and bool(np.all(np.diff([x[0] for x in reversed(resets)])>0))
        first=float(resets[7][0]) if len(resets[7]) else None
        last=float(resets[0][-1]) if len(resets[0]) else None
        nextopen=ev['XDUT.SEQ_SAMPLE']['rise'];nextopen=nextopen[nextopen>hi]
        capok=bool(len(cap) and first is not None and first>cap[-1])
        mask=(t>=(first if first is not None else hi-10))&(t<hi-.05)
        stable=bool(mask.any()) and all(np.all((v(f'D{b}')[mask]>vh)==bool(code&(1<<b))) for b in range(8))
        seqfalls=ev['XDUT.SEQ_SAMPLE']['fall']; close=seqfalls[(seqfalls>=lo)&(seqfalls<hi)]
        starts=ev['XDUT.SEQ_SAMPLE']['rise'];starts=starts[(starts>=lo)&(starts<hi)]
        duration=float(close[0]-starts[0]) if len(close) and len(starts) else None
        compares=ev[clocks[0]]['rise'];compares=compares[(compares>=lo)&(compares<hi)]
        acquire_at=float(starts[0]) if len(starts) else lo
        refword=int(sum((np.interp(acquire_at,t,v(f'XDUT.XREF.Q{b}'))>vh)*(1<<b) for b in range(8)))
        phase_mask=(t>=lo)&(t<hi)
        overlap=int(sum(np.sum((v(f'XDUT.XREF.H{b}')[phase_mask]>vh)&(v(f'XDUT.XREF.L{b}')[phase_mask]>vh)) for b in range(8)))
        settle=[]
        for ct in compares:
            # Physical TOP movement over the last 100 ps before comparison, not reset TOP at 98 ns.
            dt=v('XDUT.TOPP')-v('XDUT.TOPN')
            settle.append(float(np.interp(ct-.01,t,dt)-np.interp(ct-.11,t,dt)))
        frames.append(dict(frame=i,code=code,counts=counts,monitor_valid=bool(row[7]),
            conversion_ns=row[-1]*1e9,timing_pass=bool(row[7] and counts==[8,8,8,16] and row[-1]<60e-9),
            first_reset_ns=first,last_reset_ns=last,reset_order_pass=ordered,
            reset_after_capture=capok,held_output_pass=stable,acquisition_ns=duration,
            acquisition_reference_word=refword,HL_overlap_native_samples=overlap,
            bootstrap_off_before_compare=bool(len(close) and len(compares) and close[0]<compares[0]),
            reset_before_next_open=(bool(last<nextopen[0]) if last is not None and len(nextopen) else None),
            source_at_sample_v=row[10],top_delta_last100ps_before_compare_v=settle))
        if ctx.get('kind')=='static':
            target=ctx['input_diff_v'][i]
            ideal=int(np.clip(np.floor((target+.9)/(1.8/256)),0,255))
            allowed=[127,128] if target==0 else [ideal]
            frames[-1].update(target_v=target,allowed_ideal_codes=allowed,
                code_error_vs_ideal=code-ideal,static_code_pass=code in allowed,
                held_observation_ns=i*100+41.8,held_observation_before_first_compare=bool(len(compares) and compares[0]>i*100+41.8),
                held_diff_v=row[11],held_error_v=row[11]-target,
                midpoint_reconstruction_error_lsb=((code+.5)*(1.8/256)-.9-target)/(1.8/256))
            if len(close):
                at=float(close[0]-.2)
                top=float(np.interp(at,t,v('XDUT.TOPP')-v('XDUT.TOPN')))
                frames[-1].update(preclose_time_ns=at,preclose_diff_v=top,preclose_error_v=top-target,
                    main_vgs_preclose_v={side:float(np.interp(at,t,v('XDUT.XBOOT'+side+'.G')-v('VIN'+side))) for side in ['P','N']},
                    top_minus_input_preclose_v={side:float(np.interp(at,t,v('XDUT.TOP'+side)-v('VIN'+side))) for side in ['P','N']})
    groups={g:max((x for x in r['stress'] if x['group']==g),key=lambda x:x['peak_v']) for g in {x['group'] for x in r['stress']}}
    warning_codes=sorted(set(re.findall(r'WARNING \(([^)]+)\)',log)))
    settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1] for k in ['maxstep','reltol','abstol(V)','abstol(I)','method','temp','tnom']}
    result=dict(name=name,corner=ctx.get('corner','tt'),vdd=sup,temperature_c=ctx.get('temperature_c',27),
        frames=frames,all_timing_pass=all(x['timing_pass'] for x in frames),
        all_idle_pass=all(x['reset_order_pass'] and x['reset_after_capture'] and x['held_output_pass']
            and x['acquisition_reference_word']==128 and x['HL_overlap_native_samples']==0
            and x['bootstrap_off_before_compare'] and x['reset_before_next_open'] is not False for x in frames),
        groups=groups,stress_failures=sorted([s for s in r['stress'] if s['exceed']],key=lambda s:s['peak_v']/s['limit_v'],reverse=True)[:20],
        stress_failure_count=sum(s['exceed'] for s in r['stress']),
        stress_failing_MOS_count=len({s['instance'] for s in r['stress'] if s['exceed']}),
        stress_detail_scope='Worst 20 failing terminal pairs here; all 2670 pairs retained in reduced raw evidence',
        warning_codes=warning_codes,CMI=any(x.startswith('CMI-') for x in warning_codes),
        CMI_or_suppression_lines=[s.strip() for s in log.splitlines() if 'CMI-' in s or 'suppress' in s.lower()],
        suppressed_warning_total=int((re.findall(r'(\d+) warnings suppressed',log) or ['0'])[-1]),
        suppression_scope='Native all-warning summary, not an exact count of CMI events or affected devices',
        effective_settings=settings,native_points=r['native_points'],native_psf_sha256=r['native_psf_sha256'],
        native_psf_bytes=r['native_psf_bytes'],DUT_sha256=ctx['DUT_sha256'])
    result['static_code_pass']=all(f['static_code_pass'] for f in frames) if ctx.get('kind')=='static' else None
    result['post_startup_static_code_pass']=all(f['static_code_pass'] for f in frames[1:]) if ctx.get('kind')=='static' else None
    dump(VERIFY/(name+'.json'),result)
    print(name, 'codes', [x['code'] for x in frames], 'timing',result['all_timing_pass'],'idle',result['all_idle_pass'], 'CMI',result['CMI'], 'stress failing pairs',result['stress_failure_count'])
    return result,r

def analyze_window(name):
    folder=OUT/name;ctx=read(folder/'context.json');receipt=read(folder/'reduced_receipt.json')
    assert sha(folder/'reduced/reduced.json.gz')==receipt['compressed_sha256']
    with gzip.open(folder/'reduced/reduced.json.gz','rt') as f:r=json.load(f)
    log=(folder/'reduced/spectre.out').read_text();status=(folder/'reduced/logStatus').read_text()
    assert 'spectre completes with 0 errors' in log and re.search(r'tran_perf\s+PASS',status)
    original=read(VERIFY/(ctx['accuracy_crosscheck_of']+'.json'))
    baseline=max((s for g,s in original['groups'].items() if g!='bootstrap'),key=lambda s:s['peak_v'])
    assert baseline['time_ns']<ctx['stop_ns']
    target=next(s for s in r['stress'] if s['instance']==baseline['instance'] and s['terminal']==baseline['terminal'])
    settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1] for k in ['maxstep','reltol','abstol(V)','abstol(I)','method','temp']}
    result=dict(name=name,stop_ns=ctx['stop_ns'],native_exit=receipt['native_exit'],native_analysis_pass=True,
        scope=ctx['qualification'],whole_frame_qualification=False,selected_MOS_count=len(ctx['stress_devices']),
        effective_settings=settings,native_psf_sha256=r['native_psf_sha256'],native_psf_bytes=r['native_psf_bytes'],
        native_points=r['native_points'],CMI='WARNING (CMI-' in log,
        comparison=dict(CX=baseline,refined=target,delta_peak_mv=(target['peak_v']-baseline['peak_v'])*1e3),
        stress=r['stress'],DUT_sha256=ctx['DUT_sha256'])
    dump(VERIFY/(name+'.json'),result)
    print(name,settings,'core peak',target['peak_v'],'CMI',result['CMI'])
    return result,r

def gate():
    a,aw=analyze('tt_smoke_400');b,bw=analyze('tt_independent_400')
    assert read(VERIFY/'activation.json')['pass_activation']
    assert all(x['all_timing_pass'] and x['all_idle_pass'] and not x['CMI'] and not x['stress_failures'] for x in [a,b])
    assert [f['code'] for f in a['frames']]==[f['code'] for f in b['frames']]
    previous=read(ROOT/'output/sar8_r4_idle/idle_4600/analysis.json')
    assert [f['code'] for f in a['frames']]==[f['code'] for f in previous['frames'][:4]]
    # Same physical quantities at fixed pre-comparison held phase, all four frames.
    delta=[]
    for i in range(4):
        vals=[]
        for x in (aw,bw):
            w=x['wave'];t=np.array(w['time'])*1e9
            vals.append(np.interp(i*100+41.8,t,np.array(w['xdut.topp'])-np.array(w['xdut.topn'])))
        delta.append(float(vals[1]-vals[0]))
    assert max(abs(x) for x in delta)<.02*1.8/256,delta
    dump(VERIFY/'gate.json',dict(pass_preflight=True,nominal_equal_codes=True,held_delta_v=delta,
        criterion='4 frames, same code and timing; <0.02 LSB held difference; local native MOS/MOM activation plus repeat seed',
        limitation='Independent-unit integrated nominal check only. Statistical ADC not qualified.'))

if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['gate']:gate()
    else:
        for name in sys.argv[1:]:analyze(name)
