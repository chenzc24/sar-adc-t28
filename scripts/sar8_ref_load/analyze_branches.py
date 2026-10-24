"""Resolve reference loading by terminal-current KCL, not inferred source drops alone."""
import re
import numpy as np
from control import ROOT,OUT,VERIFY,NAMES,read,dump,sha,wf
from native import load

def main():
    summary={}
    for name in NAMES:
        folder=OUT/name;raw=folder/'native/test.raw/tran_perf.tran.tran'
        receipt=read(folder/'receipt.json')
        hashes={k.replace('\\','/'):v for k,v in receipt['native_files'].items()}
        assert sha(raw)==hashes['test.raw/tran_perf.tran.tran']
        log=(folder/'native/spectre.out').read_text();status=(folder/'native/test.raw/logStatus').read_text()
        assert 'spectre completes with 0 errors' in log and re.search(r'tran_perf\s+PASS',status)
        w=load(raw);t=w['time']*1e9
        assert t[-1]>=180-1e-5 and np.all(np.diff(t)>0)
        assert all(len(v)==len(t) and np.all(np.isfinite(v)) for v in w.values())
        np.savez_compressed(folder/'wave.npz',**w)
        def at(n,ns=130):return float(np.interp(ns,t,w[n.lower()]))
        vp,vn=at('VREFP'),at('VREFN');branches=[]
        for side in ['P','N']:
            for b in range(8):
                path=f'XDUT.XCDAC.XS{side}{b}'
                bot=at(f'XDUT.XCDAC.B{side}{b}');gn=at(f'XDUT.G{side}N{b}');gp=at(f'XDUT.G{side}P{b}')
                pm=[at(path+'.MP_HIGH:'+str(i)) for i in range(1,5)]
                nm=[at(path+'.MN_LOW:'+str(i)) for i in range(1,5)]
                cap=at(f'XDUT.XCDAC.CMOM{side}{b}:2')
                off='MN_LOW' if gn<.495 and gp<.495 else ('MP_HIGH' if gn>.495 and gp>.495 else 'both_or_partial')
                branches.append(dict(side=side,bit=b,instance=path,parallel_units=3*2**b,
                    bottom_v=bot,gn_v=gn,gp_v=gp,off_device=off,
                    nm_vgs_v=gn-vn,nm_vds_v=bot-vn,nm_vbs_v=-vn,
                    pm_vsg_v=vp-gp,pm_vsd_v=vp-bot,pm_body_v=.99,
                    pm_dgsb_ua=[x*1e6 for x in pm],nm_dgsb_ua=[x*1e6 for x in nm],
                    high_rail_load_ua=pm[2]*1e6,low_rail_return_ua=-nm[2]*1e6,
                    bottom_kcl_na=(pm[0]+nm[0]+cap)*1e9,
                    pm_kcl_na=sum(pm)*1e9,nm_kcl_na=sum(nm)*1e9))
        ph=sum(x['high_rail_load_ua'] for x in branches);nl=sum(x['low_rail_return_ua'] for x in branches)
        ip=(.9-vp)/50*1e6;inn=vn/50*1e6
        otherp=(at('CREFP:1')+at('XDUT.XCDAC.CMOMP8:2'))*1e6
        othern=(at('CREFN:1')+at('XDUT.XCDAC.CMOMN8:2'))*1e6
        result=dict(name=name,at_ns=130,native_points=len(t),psf_sha256=sha(raw),
            reference_p_v=vp,reference_n_v=vn,span_v=vp-vn,source_current_p_ua=ip,return_current_n_ua=inn,
            sum_switch_p_source_ua=ph,sum_switch_n_return_ua=nl,
            other_high_load_ua=otherp,other_low_load_ua=othern,
            high_rail_kcl_na=(ip-ph-otherp)*1000,low_rail_kcl_na=(-inn+nl-othern)*1000,
            source_p_measured_ua=-at('VREFHIGH:p')*1e6,source_n_measured_ua=at('VREFLOW:p')*1e6,
            branches=branches,CMI='WARNING (CMI-' in log,
            settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1]
                      for k in ['maxstep','reltol','abstol(V)','abstol(I)','method','temp']})
        assert abs(result['high_rail_kcl_na'])<1 and abs(result['low_rail_kcl_na'])<1
        assert max(abs(x[k]) for x in branches for k in ['bottom_kcl_na','pm_kcl_na','nm_kcl_na'])<1
        assert abs(ip-result['source_p_measured_ua'])<.001
        assert abs(inn-result['source_n_measured_ua'])<.001
        dump(VERIFY/(name+'.json'),result);summary[name]=result
        print(name,'source uA',ip,inn,'rail KCL nA',result['high_rail_kcl_na'],result['low_rail_kcl_na'])
        for x in sorted(branches,key=lambda x:x['high_rail_load_ua'],reverse=True)[:5]:print(x)
    baseline=read(ROOT/'verification/sar8_ff_counterfactual/comparison.json')['cases']['w2_ff_099_125_static']
    assert abs(summary[NAMES[0]]['span_v']-baseline['reference_span_130ns_v'])<1e-5

if __name__=='__main__':main()
