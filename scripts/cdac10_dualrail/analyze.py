"""Code, ideal charge baselines, and all 144 reference/driver MOS stress pairs."""
import json
import re
from pathlib import Path
import numpy as np
from common import OUT,LSB,LIMIT,load,dump
from run import blocks

def instances(text):
    found={}
    for line in text.replace('\\\n',' ').splitlines():
        m=re.match(r'\s*(\w+)\s+\(([^)]*)\)\s+(\w+)\b',line)
        if m: found[m[1]]=(m[2].split(),m[3])
    return found

def data(name):
    result=load(f'runs/{name}_result.json');assert result['ok'],result
    case=load(f'cases/{name}.json')
    raw=load(f'runs/{name}_waveform.json')
    # Native export also emits scalar/model info, which are not waveforms.
    wave={k:np.asarray(v,dtype=float) for k,v in raw.items() if k!='units' and isinstance(v,list)}
    t=wave['time'];assert np.isfinite(t).all() and np.all(np.diff(t)>0)
    assert all(np.isfinite(x).all() and len(x)==len(t) for x in wave.values())
    if not case['strobe']:assert t[-1]>=case['stop_ns']*1e-9-1e-15,(name,t[-1])
    return result,case,wave

def analyze(name):
    result,case,w=data(name);ns=w['time']*1e9;sup=case['parameters']['SUP'];lsb=2*sup/1024
    code=sum((w[f'dout<{b}>']>sup/2).astype(int)*(1<<b) for b in range(10))
    log=(Path(result['metadata']['output_dir']).parent/'spectre.out').read_text(errors='replace')
    row={'name':name,'ok':True,'printed_cmi':len(re.findall(r'WARNING \(CMI-',log)),
         'suppressed_warnings':sum(map(int,re.findall(r'(\d+) warnings suppressed',log))),
         'lte_relaxations':log.count('WARNING (SPECTRE-16780)'),
         'supply_v':sup,'corner':case['corner'],'temperature_c':case['temperature_c']}
    if case['strobe']:
        if 'static' in name:
            sel=(ns>=493-1e-5)&(ns<102793-1e-5)
            got=code[sel];expected=np.arange(1024)
            assert len(got)==1024,(len(got),ns[sel][:2],ns[sel][-2:])
            row.update(samples=1024,center_code_errors=int(np.count_nonzero(got-expected)),max_center_error_codes=int(np.max(abs(got-expected))),
                       center_codes_monotonic=bool(np.all(np.diff(got)>=0)))
            dump('metrics/static_codes.json',{'expected':expected.tolist(),'actual':got.tolist()})
        else:
            sel=(ns>=493-1e-5)&(ns<26000)
            got=code[sel];assert len(got)==256,len(got)
            a=got-got.mean();p=abs(np.fft.rfft(a))**2;p[0]=0;k=int(np.argmax(p))
            fundamental=p[k];rest=p.sum()-fundamental;sndr=10*np.log10(fundamental/rest)
            row.update(samples=256,fundamental_bin=k,sndr_db=float(sndr),enob_bits=float((sndr-1.76)/6.02),
                       scope='deterministic native CDAC/Bootstrap plus ideal sign comparator; not complete ADC noise/offset performance')
        dump(f'metrics/{name}.json',row);return row
    cycle=int((case['stop_ns']-99)//100)
    at=lambda key,t:float(np.interp(t,ns,w[key]))
    frame=100*cycle
    vin=at('vinp_src',frame+41.05)-at('vinn_src',frame+41.05)
    expected_code=int(np.clip(np.floor((vin+sup)/lsb),0,1023))
    got=sum((at(f'dout<{b}>',frame+93)>sup/2)*(1<<b) for b in range(10))
    comp=[]
    for j in range(10):
        instant=frame+45.9+5*j
        dac=sum(((at(f'pl<{b}>',instant)>sup/2)-(at(f'nl<{b}>',instant)>sup/2))*(1<<b) for b in range(9))*sup/512
        actual=at('topp',instant)-at('topn',instant)
        cm=(at('topp',instant)+at('topn',instant))/2
        ideal_cm=sup/2-sup*sum(1<<b for b in range(9-j,9))/1024
        comp.append(dict(time_ns=instant,actual_v=actual,ideal_v=vin-dac,error_mv=(actual-vin+dac)*1000,cm_v=cm,ideal_cm_v=ideal_cm))
    row.update(code=int(got),expected_code=expected_code,code_error=int(got-expected_code),vin_v=vin,
               compare_raw_max_mv=max(abs(x['error_mv']) for x in comp),first_hold_error_mv=comp[0]['error_mv'],
               switching_delta_max_mv=max(abs(x['error_mv']-comp[0]['error_mv']) for x in comp),comparisons=comp,
               final_compare_cm_v=comp[-1]['cm_v'],acquisition_error_mv=(at('topp',frame+40.9)-at('topn',frame+40.9)-vin)*1000)
    text=(OUT/f'decks/{name}.scs').read_text();sub=blocks(text)
    cdac_nodes,cdac_master=instances(text)['XCDAC'];body=sub[cdac_master]
    ports=body.replace('\\\n',' ').splitlines()[0].split()[2:]
    assert len(ports)==len(cdac_nodes);parent=dict(zip(ports,cdac_nodes))
    zero=np.zeros_like(ns)
    def voltage(n):
        n=n.lower().replace('\\','')
        if n=='0':return zero
        assert n in w,n
        return w[n]
    if case.get('oa_tag')=='sample_reset':reset=(ns%100>=2.9)&(ns%100<=12)
    else:reset=(ns%100>=93.9)&(ns%100<=99)
    post=ns>=100
    worst={k:{'value_v':-1} for k in ['all','post_startup','reset']};count=0
    for leaf,(nodes,master) in instances(body).items():
        if not leaf.startswith('XS'):continue
        lb=sub[master];lp=lb.replace('\\\n',' ').splitlines()[0].split()[2:]
        mapping=dict(zip(lp,nodes,strict=True))
        def resolve(n):
            if n in mapping:
                pn=mapping[n];return parent.get(pn,'XCDAC.'+pn)
            return f'XCDAC.{leaf}.{n}'
        for dev,(nets,model) in instances(lb).items():
            if not model.startswith(('pch_','nch_')):continue
            count+=1;d,g,s,b=[voltage(resolve(n)) for n in nets]
            pairs={'vds':d-s,'vgs':g-s,'vgd':g-d,'vbs':b-s,'vbd':b-d}
            for term,v in pairs.items():
                for label,mask in [('all',np.ones_like(ns,dtype=bool)),('post_startup',post),('reset',reset)]:
                    ids=np.flatnonzero(mask)
                    if not len(ids):continue
                    idx=ids[np.argmax(abs(v[ids]))]
                    if abs(v[idx])>worst[label]['value_v']:
                        worst[label]=dict(value_v=float(abs(v[idx])),signed_v=float(v[idx]),instance=f'XCDAC.{leaf}.{dev}',terminal=term,time_ns=float(ns[idx]))
    assert count==144,count
    row.update(reference_driver_mos_count=count,stress=worst,
               reference_core_screen_pass=worst['all']['value_v']<=.990001,
               reset_bottom_error_mv=max(abs(at(f'xcdac.b{s}{b}',frame+(35 if case.get('oa_tag')=='sample_reset' else 99))-at('vrefp',frame+(35 if case.get('oa_tag')=='sample_reset' else 99)))*1000 for s in 'pn' for b in range(9)))
    dump(f'metrics/{name}.json',row);return row

if __name__=='__main__':
    rows=[]
    for p in sorted((OUT/'runs').glob('*_result.json')):
        name=p.stem.removesuffix('_result')
        status=load(f'runs/{name}_result.json')
        row=analyze(name) if status['ok'] else {'name':name,'ok':False,'errors':status['errors']}
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ['comparisons']},default=str),flush=True)
    dump('metrics/summary.json',rows)
