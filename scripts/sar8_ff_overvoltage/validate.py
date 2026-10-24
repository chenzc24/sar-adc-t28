"""Focused evidence checks for the diagnosis; not electrical acceptance."""
from inventory import ROOT,OUT,VERIFY,SOURCE,NAMES,read,dump,sha
from localize import mapping
import numpy as np

def main():
    inv=read(VERIFY/'inventory.json');ev=read(VERIFY/'events.json');checks={}
    for name in NAMES:
        ctx=inv[name]['context'];d=mapping((SOURCE/name/'dut.scs').read_text())
        assert sha(SOURCE/name/'dut.scs')==ctx['DUT_sha256']
        assert sha(SOURCE/name/'test.scs')==ctx['deck_sha256']
        assert len(inv[name]['all_pair_peaks'])==2670
        for p in inv[name]['all_pair_peaks']:
            mos=d[p['instance']];nodes=dict(zip('dgsb',mos['nodes']))
            assert [nodes[t] for t in p['terminal']]==p['nodes']
            assert mos['model']==p['model']
        assert ev[name]['selected_MOS_count']==445
        assert ev[name]['netlisted_MOS_instances']==1833
        for group,e in ev[name]['events'].items():
            cache=OUT/(name+'_'+group+'.npz')
            assert sha(cache)==inv[name]['windows'][group]['cache_sha256']
            w=dict(np.load(cache));p=e['peak'];a,b=p['nodes']
            v=(w[a] if a!='0' else 0)-(w[b] if b!='0' else 0)
            idx=np.argmax(abs(v));assert abs(abs(v[idx])-p['peak_v'])<1e-12
            assert abs(w['time'][idx]*1e9-p['time_ns'])<1e-8
            assert e['supplies_v']=={'min':.99,'max':.99}
            for key in ['duration_above_limit','duration_above_limit_plus1mV']:
                assert not e[key]['truncated'] and e[key]['duration_ps']>0
        es=ev[name]['timing_events'];p=ev[name]['events']['reference']['peak']['time_ns']
        rst=lambda b:min([e['time_ns'] for e in es if e['signal']=='xdut.xref.rst'+str(b) and e['direction']=='rise'],key=lambda t:abs(t-p))
        assert rst(7)<p<rst(4)
        active=ev[name]['events']['sequencer']['peak']['time_ns']
        assert len([e for e in es if e['signal']=='xdut.phi_u' and e['direction']=='rise' and e['time_ns']<active])==4
        assert ev[name]['events']['comparator']['signed_peak_v']<0
        checks[name]=dict(pair_mapping_checks=2670,peak_windows_checked=4,constant_VDD=True,
            reference_peak_before_own_reset=True,active_at_fourth_update=True,
            comparator_Vbs_negative_because_source_positive=True)
    figures=read(VERIFY/'figures.json');assert len(figures)==4
    for f in figures.values():assert sha(ROOT/f['path'])==f['sha256']
    result=dict(status='PASS',scope='diagnostic artifact consistency, NOT circuit SOA pass',
        cases=checks,figure_hashes_checked=4,circuit_modified=False,new_simulations=0)
    dump(VERIFY/'validation.json',result);print(result)

if __name__=='__main__':main()
