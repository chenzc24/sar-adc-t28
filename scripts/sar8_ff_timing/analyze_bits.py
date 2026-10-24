"""Read-only diagnosis of recorded native bit timing, no circuit edits."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/sar8_ff_timing';VERIFY=ROOT/'verification/sar8_ff_timing'
NAMES=['w2_tt_090_27_static','w2_ff_099_m40_static','w2_ff_099_125_static']

def load(name):
    folder=ROOT/'output/sar8_main_width'/name
    source=folder/'reduced/reduced.json.gz'
    receipt=json.loads((folder/'reduced_receipt.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==receipt['compressed_sha256']
    with gzip.open(source,'rt') as f:raw=json.load(f)
    w={k:np.array(v) for k,v in raw['wave'].items()}
    report=json.loads((ROOT/'verification/sar8_main_width'/f'{name}.json').read_text())
    return w,report

def main():
    OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)
    for name in NAMES:
        cache=OUT/(name+'.npz')
        source=ROOT/'output/sar8_main_width'/name/'reduced/reduced.json.gz'
        receipt=json.loads((source.parent.parent/'reduced_receipt.json').read_text())
        assert hashlib.sha256(source.read_bytes()).hexdigest()==receipt['compressed_sha256']
        previous=VERIFY/(name+'.json')
        if cache.exists() and previous.exists():
            assert hashlib.sha256(cache.read_bytes()).hexdigest()==json.loads(previous.read_text())['cache_sha256']
        if not cache.exists():
            w,r=load(name)
            keep=(w['time']>=100e-9)&(w['time']<=180e-9)
            np.savez_compressed(cache,**{k:v[keep] for k,v in w.items()})
        w=dict(np.load(cache));t=w['time']*1e9
        r=json.loads((ROOT/'verification/sar8_main_width'/f'{name}.json').read_text());sup=r['vdd']
        def at(n,x):return float(np.interp(x,t,w[n]))
        def edges(n,up=True):
            v=w[n];h=sup/2;idx=np.flatnonzero((v[:-1]<h)&(v[1:]>=h) if up else (v[:-1]>h)&(v[1:]<=h))
            return t[idx]+(h-v[idx])*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
        cmp=edges('xdut.cmp_clk');write=edges('xdut.xctrl.phi_w');update=edges('xdut.phi_u')
        assert len(cmp)==len(write)==len(update)==8
        rows=[]
        def word(prefix,x):return sum((at(prefix+str(b),x)>sup/2)*(1<<b) for b in range(8))
        for i,(ct,wt,ut) in enumerate(zip(cmp,write,update)):
            q=word('xdut.xref.q',ct-.01)
            valid=(t>=ct)&(t<=wt)&(((w['xdut.comp_p']>.9*sup)&(w['xdut.comp_n']<.1*sup))|((w['xdut.comp_n']>.9*sup)&(w['xdut.comp_p']<.1*sup)))
            assert valid.any()
            row=dict(bit=7-i,compare_ns=float(ct),write_ns=float(wt),update_ns=float(ut),
                q_before=q,q_at_update_plus500ps=word('xdut.xref.q',ut+.5),
                top_before_mv=(at('xdut.topp',ct-.01)-at('xdut.topn',ct-.01))*1000,
                top_at_write_mv=(at('xdut.topp',wt)-at('xdut.topn',wt))*1000,
                top_cm=(at('xdut.topp',ct-.01)+at('xdut.topn',ct-.01))/2,
                comp_p_at_write=at('xdut.comp_p',wt),comp_n_at_write=at('xdut.comp_n',wt),
                code_after=word('d',wt+.15),ideal_residual_mv=1000*(-.81+(128-q)*.9/128),
                reference_p_v=at('vrefp',ct-.01),reference_n_v=at('vrefn',ct-.01),
                reference_span_v=at('vrefp',ct-.01)-at('vrefn',ct-.01),
                residual_last100ps_change_mv=1000*((at('xdut.topp',ct-.01)-at('xdut.topn',ct-.01))-(at('xdut.topp',ct-.11)-at('xdut.topn',ct-.11))),
                compare_to_write_ns=float(wt-ct),resolved_90_10_before_write_ns=float(wt-t[valid][0]))
            # Positive TOP difference maps to COMP_P high and retaining the current bit.
            row['write_matches_comparator']=bool(((row['code_after']>>(7-i))&1)==(row['comp_p_at_write']>row['comp_n_at_write']))
            assert row['write_matches_comparator']
            rows.append(row)
        assert rows[-1]['code_after']==r['frames'][1]['code']
        pp,nn=at('vrefp',130),at('vrefn',130)
        span=pp-nn
        result=dict(name=name,frame=1,code=r['frames'][1]['code'],rows=rows,
            tracking_130ns=dict(reference_p_v=pp,reference_n_v=nn,span_v=span,
                positive_source_current_ua=(.9-pp)/50*1e6,negative_return_current_ua=nn/50*1e6,
                source_current_scope='50-ohm source resistor current, NOT a specific transistor leakage measurement',
                ideal_code_using_measured_span=int(np.floor(128+128*(-.81)/span)),
                reference_p_drift_120_to_140ns_v=at('vrefp',140)-at('vrefp',120),
                reference_n_drift_120_to_140ns_v=at('vrefn',140)-at('vrefn',120)),
            original_wave_sha256=json.loads((ROOT/'output/sar8_main_width'/name/'reduced_receipt.json').read_text())['compressed_sha256'],
            cache_sha256=hashlib.sha256(cache.read_bytes()).hexdigest())
        (VERIFY/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(name,'code',result['code'],'ref span',span,'bit2',rows[5])

if __name__=='__main__':main()
