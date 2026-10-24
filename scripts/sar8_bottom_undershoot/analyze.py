"""Read-only native waveform attribution; no circuit modifications or new runs."""
from pathlib import Path
import gzip,json,hashlib,sys,importlib.util,gc
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/sar8_ref_symmetric_hold'
OUT=ROOT/'output/sar8_bottom_undershoot';OUT.mkdir(exist_ok=True)
VERIFY=ROOT/'verification/sar8_bottom_undershoot';VERIFY.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
sys.path.insert(0,str(ROOT/'scripts/sar8_ff_overvoltage'))
spec=importlib.util.spec_from_file_location('bottom_mapping',ROOT/'scripts/sar8_ff_overvoltage/localize.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def measure(name,w,devices,phase,side,start,stop):
    t=w['time']*1e9;bottom=f'xdut.xcdac.b{side}7';gn=f'xdut.g{side}n7';gp=f'xdut.g{side}p7'
    m=(t>start)&(t<stop);ids=np.flatnonzero(m);imin=ids[np.argmin(w[bottom][m])];tp=float(t[imin])
    def at(n,x):return float(np.interp(x,t,w[n]))
    def crossing(n,lev,up,lo,hi):
        y=w[n];ii=np.flatnonzero(((y[:-1]<lev)&(y[1:]>=lev) if up else (y[:-1]>lev)&(y[1:]<=lev)))
        ts=t[ii]+(lev-y[ii])*(t[ii+1]-t[ii])/(y[ii+1]-y[ii]);ts=ts[(ts>=lo)&(ts<=hi)]
        assert len(ts), (name,phase,n,lev,lo,hi)
        return float(ts[0])
    n99=crossing(gn,.99*.99,False,tp-.6,tp)
    p99=crossing(gp,.99*.99,False,tp-.6,tp)
    n90=crossing(gn,.99*.9,False,tp-.6,tp)
    p90=crossing(gp,.99*.9,False,tp-.6,tp)
    zero=crossing(bottom,0,True,tp,tp+.3)
    # Positive low-reference current convention: ideal0V source -> local VREFN.
    rn=-(w['vrefn']/50)
    local= w[bottom]-w['vrefn']
    index=np.flatnonzero((t>=n99)&(t<=tp))
    nr=index[np.argmin(w['vrefn'][index])]
    branch=f'XDUT.XCDAC.XS{side.upper()}7'
    expected={branch+'.MN_LOW':[bottom,gn,'vrefn','0'],branch+'.MP_HIGH':[bottom,gp,'vrefp','vdd!']}
    for key,nodes in expected.items():assert devices[key]['nodes']==nodes
    samples=[]
    signals=[bottom,'vrefn','vrefp',gn,gp,'xdut.top'+side,'xdut.xref.h7','xdut.xref.l7','xdut.xref.rst7',
      'xdut.xref.rst6','xdut.phi_u','xdut.active','xdut.preset','xdut.seq_sample']
    for stage,x in [('before',n99-.03),('n_gate_99pct',n99),('before_p_gate',p99-.005),('p_gate_99pct',p99),('bottom_min',tp),('bottom_recovers_zero',zero)]:
        samples.append(dict(stage=stage,time_ns=x,values={n:at(n,x) for n in signals}))
    cmd='xdut.xref.rst7' if phase=='idle' else 'xdut.phi_u'
    command=crossing(cmd,.495,True,tp-.7,tp)
    allgates=[f'xdut.g{s}{k}{b}' for s in ['p','n'] for k in ['n','p'] for b in range(7)]
    changes={n:float(max(w[n][index])-min(w[n][index])) for n in allgates}
    vdd=w['vdd!'][imin];vb=w[bottom][imin]
    data=dict(name=name,phase=phase,side=side,frame=int(tp//100),
      input_diff_v=read(SOURCE/name/'context.json')['input_diff_v'][int(tp//100)],
      branch=branch,devices={k:devices[k] for k in expected},bottom=bottom,gate_n=gn,gate_p=gp,
      command=cmd,command_rise_ns=command,n_gate_start99_ns=n99,p_gate_start99_ns=p99,
      n_gate90_ns=n90,p_gate90_ns=p90,bottom_min_ns=tp,bottom_zero_ns=zero,
      gate_start_gap_ps=(p99-n99)*1000,min_after_nstart_ps=(tp-n99)*1000,
      bottom_min_mv=float(vb)*1000,reference_n_at_bottom_min_mv=at('vrefn',tp)*1000,
      local_bottom_minus_reference_at_min_mv=float(local[imin])*1000,
      reference_p_at_bottom_min_v=at('vrefp',tp),body_drain_abs_v=float(abs(vdd-vb)),
      reference_n_min_mv=float(w['vrefn'][nr])*1000,reference_n_min_ns=float(t[nr]),
      before_p_bottom_mv=at(bottom,p99-.005)*1000,before_p_reference_n_mv=at('vrefn',p99-.005)*1000,
      n_gate_at_min_v=at(gn,tp),p_gate_at_min_v=at(gp,tp),
      low_source_current_at_min_ua=float(rn[imin])*1e6,
      other_bit_gate_max_range_v=max(changes.values()),other_bit_gate_ranges=changes,
      peak_native_step_ps=float((t[imin+1]-t[imin-1])*500),samples=samples,
      timing_marker_note='99%/90% of0.99V are waveform markers, NOT transistor Vth or proof of conduction cutoff',
      decomposition_note='Vbottom=VREFN+(Vbottom-VREFN) is a voltage identity, not causal charge/current apportionment')
    prefix=f'xdut.xref.xdrv7.'
    data['keeper_at_min']={k:at(prefix+k,tp) for k in ['enh_g'+side+'n','enl_g'+side+'n','enh_g'+side+'p','enl_g'+side+'p']}
    data['keeper_before_nstart']={k:at(prefix+k,n99-.03) for k in data['keeper_at_min']}
    keep=(t>=tp-.7)&(t<=tp+.5)
    cache=OUT/(name+'_'+phase+'.npz');np.savez_compressed(cache,**{k:v[keep] for k,v in w.items()})
    data['cache_sha256']=sha(cache)
    return data

def main():
    rows={};provenance={}
    for corner in ['m40','125']:
        for variant in ['null','symmetric25']:
            name=f'{variant}_ff_{corner}';src=SOURCE/name;ctx=read(src/'context.json')
            assert sha(src/'dut.scs')==ctx['DUT_sha256']
            assert sha(src/'test.scs')==ctx['deck_sha256']
            compressed=src/'reduced/reduced.json.gz'
            assert sha(compressed)==read(src/'reduced_receipt.json')['compressed_sha256']
            with gzip.open(compressed,'rt') as f:r=json.load(f)
            w={k:np.array(v) for k,v in r['wave'].items()}
            devices=mod.mapping((src/'dut.scs').read_text())
            current_saves=[x for x in ctx['saved_signals'] if ':' in x]
            provenance[name]=dict(source=str(src.relative_to(ROOT)),DUT_sha256=ctx['DUT_sha256'],
              deck_sha256=ctx['deck_sha256'],reduced_sha256=sha(compressed),native_psf_sha256=r['native_psf_sha256'],
              saved_current_signals=current_saves,reference_switch_currents_saved=any('.XCDAC.XS' in s for s in current_saves))
            for phase,side,start,stop in [('conversion','p',141,146),('idle','n',471 if corner=='m40' else 274,474 if corner=='m40' else 277)]:
                event=measure(name,w,devices,phase,side,start,stop)
                rows[name+'_'+phase]=event
                print(name,phase,round(event['bottom_min_ns'],6),round(event['bottom_min_mv'],4),'VREFN',round(event['reference_n_at_bottom_min_mv'],4),'preP',round(event['before_p_bottom_mv'],4),flush=True)
            del r,w;gc.collect()
    dump(VERIFY/'events.json',rows);dump(VERIFY/'provenance.json',provenance)

if __name__=='__main__':main()
