"""All-frame native checks plus complementary hold and all-bit reset measurements."""
import gc
import importlib.util
import numpy as np
from control import ROOT,OUT,VERIFY,read,dump,sha

spec=importlib.util.spec_from_file_location('gate_pvt_checks',ROOT/'scripts/sar8_pvt_mismatch/analyze.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
checks.OUT=OUT;checks.VERIFY=VERIFY
LSB=1.8/256

def analyze(name):
    report,raw=checks.analyze(name);ctx=read(OUT/name/'context.json')
    w={k:np.asarray(v) for k,v in raw['wave'].items()};t=w['time']*1e9
    def at(n,x):return float(np.interp(x,t,w[n]))
    def edges(n,level=.495,up=True):
        y=w[n];ids=np.flatnonzero((y[:-1]<level)&(y[1:]>=level) if up else (y[:-1]>level)&(y[1:]<=level))
        return t[ids]+(level-y[ids])*(t[ids+1]-t[ids])/(y[ids+1]-y[ids])
    def nextedge(n,start,up=True):return float(next(e for e in edges(n,up=up) if e>start))
    rst=nextedge('xdut.xref.rst7',141);nxt=nextedge('xdut.seq_sample',200)
    region=(t>=rst)&(t<=nxt-.02);tt=t[region]
    p,n=w['vrefp'],w['vrefn'];ratio=(w['xdut.xcdac.bn7']-n)/(p-n)
    def levelcross(y,lev):
        ids=np.flatnonzero((y[:-1]<lev)&(y[1:]>=lev))
        return float(tt[ids[0]]+(lev-y[ids[0]])*(tt[ids[0]+1]-tt[ids[0]])/(y[ids[0]+1]-y[ids[0]])) if len(ids) else None
    t10=levelcross(ratio[region],.1);t90=levelcross(ratio[region],.9)
    errors=[]
    for b in range(8):
        for side in ['p','n']:
            high=(side=='n' and b==7) or (side=='p' and b!=7)
            errors.append(abs(w[f'xdut.xcdac.b{side}{b}']-(p if high else n)))
    worst=np.max(errors,axis=0)
    def settle(y):
        yy=y[region];bad=np.flatnonzero(yy>.25*LSB)
        if not len(bad):return float(tt[0])
        idx=bad[-1]
        if idx==len(tt)-1:return None
        return float(tt[idx]+(.25*LSB-yy[idx])*(tt[idx+1]-tt[idx])/(yy[idx+1]-yy[idx]))
    done=settle(worst);done7=settle(abs(w['xdut.xcdac.bn7']-p))
    idle_index=np.flatnonzero(region)[np.argmax(w['xdut.gnn4'][region])]
    own_reset=nextedge('xdut.xref.rst4',rst)
    same_event=(t>=rst)&(t<own_reset-.01)
    index=np.flatnonzero(same_event)[np.argmax(w['xdut.gnn4'][same_event])]
    gpeak=float(w['xdut.gnn4'][index]);gp_t=float(t[index])
    mask=(t>=140)&(t<205);cache=OUT/(name+'_window.npz')
    np.savez_compressed(cache,**{k:v[mask] for k,v in w.items()})
    outside=[];currents=[];overlap=[];wrong=[];late=[];details=[]
    last_reset=nextedge('xdut.xref.rst0',rst)
    # XREF uses SAMPLE_INT, which precedes the actual Bootstrap SEQ_SAMPLE.
    # The helper must release at this request, not remain on until Bootstrap opens.
    request=edges('xdut.sample_int',level=.099)
    request_end=float(next(x for x in request if x>last_reset))
    settled_idle=(t>last_reset+1)&(t<request_end-.02)
    nonidle=(w['xdut.sample_int']>.98)|((w['xdut.preset']<.1)&(w['xdut.active']>.98))
    all_late_masks=[]
    for frame in report['frames']:
        start=frame['last_reset_ns']+1
        future=request[request>start]
        stop=float(future[0]-.02) if len(future) else float(t[-1]-.02)
        all_late_masks.append((t>start)&(t<stop))
    all_late=np.logical_or.reduce(all_late_masks)
    all_late_enabled=[]
    for b in range(8):
        for tag in ['gnn','gnp','gpn','gpp']:
            gate=w[f'xdut.{tag}{b}'];prefix=f'xdut.xref.xdrv{b}.'
            hi=w[prefix+'enh_'+tag];lo=w[prefix+'enl_'+tag];cmd=w[prefix+tag+'b']
            cur=ctx['hold_unit_conductance']*2**b*(hi*(gate-w['vdd!'])+lo*gate)
            currents.append(float(max(abs(cur)))*1e6)
            outside.append(float(max(np.maximum(hi,lo)[nonidle])))
            overlap.append(float(max(np.minimum(hi,lo))))
            late.append(float(min((hi+lo)[settled_idle])))
            all_late_enabled.append(float(min((hi+lo)[all_late])))
            # Exclude 30ps around fast command transitions (5ps enable slew).
            safe=np.ones(len(t),dtype=bool)
            ce=edges(prefix+tag+'b').tolist()+edges(prefix+tag+'b',up=False).tolist()
            for ct in ce:safe &= abs(t-ct)>.03
            bad=((hi>.999)&(cmd>.2))|((lo>.999)&(cmd<.79))
            wrong.append(int(np.sum(bad&safe)))
            details.append(dict(gate=tag+str(b),max_current_ua=currents[-1],
              late_idle_min_enable=late[-1],wrong_command_samples=wrong[-1]))
    # Measure signed rail excursions for every reset, not only bit7/GNN4.
    reset_events=[]
    for b in reversed(range(8)):
        rt=nextedge(f'xdut.xref.rst{b}',141)
        stop=nextedge(f'xdut.xref.rst{b-1}',rt) if b else nxt-.02
        mm=(t>=rt)&(t<stop)
        gates=[(f'{g}{i}',w[f'xdut.{g}{i}']) for i in range(8) for g in ['gnn','gnp','gpn','gpp']]
        high=max((float(max(v[mm]-w['vdd!'][mm]))*1000,k) for k,v in gates)
        low=min((float(min(v[mm]))*1000,k) for k,v in gates)
        reset_events.append(dict(bit=b,start_ns=rt,stop_ns=stop,high_overshoot_mv=high[0],
          high_gate=high[1],low_undershoot_mv=low[0],low_gate=low[1]))
    gp=w['xdut.gnp7']/w['vdd!']
    def down(lev):
        ids=np.flatnonzero((gp[:-1]>lev)&(gp[1:]<=lev)&(t[:-1]>rst))
        i=ids[0];return float(t[i]+(lev-gp[i])*(t[i+1]-t[i])/(gp[i+1]-gp[i]))
    gate_fall=(down(.1)-down(.9))*1000
    peak=report['groups']['reference'];pt=peak['time_ns']
    peak_state={k:at(k,pt) for k in ['xdut.sample_int','xdut.active','xdut.preset']+[f'xdut.xref.rst{b}' for b in range(8)]}
    mask=abs(t-pt)<2
    peakcache=OUT/(name+'_peak.npz')
    np.savez_compressed(peakcache,**{k:v[mask] for k,v in w.items()})
    phases={'sample':w['xdut.sample_int']>.495,
            'conversion':(w['xdut.sample_int']<=.495)&(w['xdut.active']>.495),
            'idle':(w['xdut.sample_int']<=.495)&(w['xdut.preset']>.495)}
    phase_peaks={}
    for phase,pm in phases.items():
        candidates=[];ii=np.flatnonzero(pm)
        for pair in raw['stress']:
            if pair['group']!='reference':continue
            a,b=pair['nodes'];v=(w[a] if a!='0' else 0)-(w[b] if b!='0' else 0)
            j=ii[np.argmax(abs(v[pm]))]
            candidates.append(dict(instance=pair['instance'],terminal=pair['terminal'],peak_v=float(abs(v[j])),
              signed_v=float(v[j]),time_ns=float(t[j]),nodes=pair['nodes']))
        phase_peaks[phase]=max(candidates,key=lambda p:p['peak_v'])
    gate_rail_peaks={}
    for phase,pm in phases.items():
        candidates=[];ii=np.flatnonzero(pm)
        for b in range(8):
            for g in ['gnn','gnp','gpn','gpp']:
                gate=w[f'xdut.{g}{b}'];delta=gate-w['vdd!']
                hi=ii[np.argmax(delta[pm])];lo=ii[np.argmin(gate[pm])]
                candidates.append(dict(gate=g+str(b),high_mv=float(delta[hi]*1000),high_ns=float(t[hi]),
                  low_mv=float(gate[lo]*1000),low_ns=float(t[lo])))
        gate_rail_peaks[phase]=dict(high=max(candidates,key=lambda r:r['high_mv']),low=min(candidates,key=lambda r:r['low_mv']))
    idlept=phase_peaks['idle']['time_ns'];mask=abs(t-idlept)<2
    idlecache=OUT/(name+'_idle_peak.npz')
    np.savez_compressed(idlecache,**{k:v[mask] for k,v in w.items()})
    metrics=dict(name=name,variant=ctx['variant'],temperature_c=ctx['temperature_c'],
      codes=[f['code'] for f in report['frames']],all_codes_pass=report['static_code_pass'],
      post_startup_codes_pass=report['post_startup_static_code_pass'],
      timing_pass=report['all_timing_pass'],idle_pass=report['all_idle_pass'],CMI=report['CMI'],
      reference_peak=report['groups']['reference'],all_groups=report['groups'],
      same_event_gnn4_peak_v=gpeak,same_event_gnn4_peak_time_ns=gp_t,
      same_event_end_before_rst4_ns=own_reset-.01,
      idle_gnn4_peak_v=float(w['xdut.gnn4'][idle_index]),idle_gnn4_peak_time_ns=float(t[idle_index]),
      rst7_ns=rst,next_sample_open_ns=nxt,bn7_10to90_ps=(t90-t10)*1000 if t90 is not None and t10 is not None else None,
      bn7_settled_ns=done7,all_bottoms_settled_ns=done,
      all_bottoms_settle_after_rst7_ns=done-rst if done else None,
      reset_margin_to_sample_ns=nxt-done if done else None,
      max_bottom_error_before_sample_mv=float(worst[np.argmin(abs(t-(nxt-.02)))])*1000,
      sample_rises_ns=edges('xdut.seq_sample').tolist(),sample_falls_ns=edges('xdut.seq_sample',up=False).tolist(),
      acquisition_ns=[f['acquisition_ns'] for f in report['frames']],
      preclose_errors_mv=[f['preclose_error_v']*1000 for f in report['frames']],
      held_errors_mv=[f['held_error_v']*1000 for f in report['frames']],
      precompare_last100ps_max_movement_mv=max(abs(x)*1000 for f in report['frames'] for x in f['top_delta_last100ps_before_compare_v']),
      reference_p_idle_max_source_current_ua=float(np.max(abs((.9-p[region])/50)))*1e6,
      reference_n_idle_max_source_current_ua=float(np.max(abs(n[region]/50)))*1e6,
      max_helper_branch_current_ua=max(currents),max_hold_enable_when_sample_high=max(outside),
      max_high_low_enable_overlap=max(overlap),wrong_command_samples=sum(wrong),
      min_late_idle_enable=min(late),helper_details=details,reset_events=reset_events,
      min_all_frames_late_idle_enable=min(all_late_enabled),phase_reference_peaks=phase_peaks,
      phase_gate_rail_peaks=gate_rail_peaks,idle_peak_cache_sha256=sha(idlecache),
      hold_release_sample_request_ns=request_end,
      gnp7_fall_90to10_ps=gate_fall,stress_failure_count=report['stress_failure_count'],
      worst_reference_phase_probes=peak_state,peak_cache_sha256=sha(peakcache),
      effective_settings=report['effective_settings'],cache_sha256=sha(cache),native_psf_sha256=raw['native_psf_sha256'],
      settling_definition='Frame1 idle: all16 bottoms within0.25LSB of actual assigned VREF rail and remain until next sample minus20ps; bit7 N->high/P->low, other bits opposite. Not just RST_DONE.',
      coverage='2670 pairs on445 selected MOS; other blocks and unsaved MOS not fully qualified; helper has ideal supplies/control.',
      current_definition='50ohm reference-source current includes decap charging; helper branch current computed from verified VA conductance equation.')
    dump(VERIFY/(name+'_metrics.json'),metrics)
    print('METRICS',name,'codes',metrics['codes'],'ref',metrics['reference_peak']['peak_v'],'GNN4',gpeak,'settle',done,'margin',metrics['reset_margin_to_sample_ns'],flush=True)
    del raw,w;gc.collect();return metrics

def combine():
    setup=read(VERIFY/'setup.json');rows={}
    for name in setup['names']:
        path=VERIFY/(name+'_metrics.json')
        if path.exists():rows[name]=read(path)
    for name,m in rows.items():
        base=rows.get('null_ff_'+('125' if m['temperature_c']==125 else 'm40'))
        if base:
            for k in ['sample_rises_ns','sample_falls_ns']:
                assert len(m[k])==len(base[k]);m[k+'_max_delta_ps']=float(np.max(abs(np.array(m[k])-base[k])))*1000
            m['code_changes_vs_null']=[i for i,(x,y) in enumerate(zip(m['codes'],base['codes'])) if x!=y]
            m['reference_peak_change_mv']=(m['reference_peak']['peak_v']-base['reference_peak']['peak_v'])*1000
    dump(VERIFY/'comparison.json',dict(complete=len(rows)==len(setup['names']),cases=rows,limit_v=.99,settling_band_mv=.25*LSB*1000,
      phase_definition='sample: SAMPLE_INT>0.495; conversion: SAMPLE_INT<=0.495 and ACTIVE>0.495; idle: SAMPLE_INT<=0.495 and PRESET>0.495. SAMPLE_INT is request, not Bootstrap SEQ_SAMPLE. Actual sample edges/margins use SEQ_SAMPLE.',
      null_comparison_bound='Peak20uV, held-error10uV, sample edges0.1ps vs original native source; instrumented null has additional cross breakpoints. Not a simulator accuracy claim.'))

if __name__=='__main__':
    import sys
    for name in sys.argv[1:]:analyze(name)
    combine()
