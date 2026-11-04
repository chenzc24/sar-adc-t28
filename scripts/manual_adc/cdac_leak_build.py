"""Save-only replay of the FF-hot CDAC case, with all reference branch ports."""
import hashlib
import json
from pathlib import Path

R=Path(__file__).resolve().parents[2]
S=R/'verification/manual_adc/cdac_100ps_corners_v1/ffhot'
B=R/'verification/manual_adc/cdac_leak_ffhot_v1'
RUN='manual8-cdac-leak-ffhot-v1'

def main():
    B.mkdir(exist_ok=False)
    for name in ['models.scs','cdac_core.scs','wrappers.scs','manual8_sample.va','manual8_cmp.va','manual8_sar.va']:
        (B/name).write_bytes((S/name).read_bytes())
    cfg=json.loads((S/'measure.json').read_text())
    pnames=['M12','M9','M8','M6','M5','M4','M0']
    nnames=['M14','M11','M10','M7','M3','M2','M1']
    caps=['C5','C4','C7','C2','C3','C1','C0']
    branches=[];extra=[]
    for side in ['P','N']:
        prefix='XADC.X'+side+'.XD.'
        for i,(pn,nn,cap,bottom) in enumerate(zip(pnames,nnames,caps,cfg['bottom_nodes'][side])):
            dev=next(d for d in cfg['devices'] if d['path']==prefix+pn)
            branches.append(dict(side=side,bit=i+1,weight=2**i,bottom=bottom,gate=dev['terminals'][1],
                                 pmos=prefix+pn,nmos=prefix+nn,capacitor=prefix+cap))
        extra += [prefix+c+':2' for c in caps]+[prefix+'C6:1']
    extra += [d['path']+':'+str(port) for d in cfg['devices'] for port in [1,2,3,4]]
    extra=sorted(set(extra)-set(cfg['signals']))
    test=(S/'test.scs').read_text()
    (B/'test.scs').write_text(test+'save '+' '.join(extra)+'\n')
    cfg['leakage']={'run_id':RUN,'source_run_id':'manual8-cdac-s100-ffhot-v1',
                    'extra_signals':extra,'branches':branches,
                    'steady_windows_s':[[75e-9+i*100e-9,95e-9+i*100e-9] for i in range(8)],
                    'native_windows_s':[[64e-9,72e-9],[164e-9,172e-9]],
                    'positive_current':'enters numbered device port; MOS 1/2/3/4 = D/G/S/B',
                    'scope':'measurement-only replay; unchanged devices and stimuli'}
    (B/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
    recipe=json.loads((R/'management/recipes/manual8-cdac-s100-ffhot-v1.yaml').read_text())
    recipe.update(run_id=RUN,design_id='manual8_cdac_leak_ffhot_v1',analyzer='cdac_leak_reduce.py')
    for item in recipe['inputs']:
        if item['source'].startswith('verification/manual_adc/'):
            item['source']=(B/item['name']).relative_to(R).as_posix()
    recipe['inputs'].append({'source':'scripts/manual_adc/cdac_leak_reduce.py','name':'cdac_leak_reduce.py'})
    recipe['resources']['max_output_mib']=768
    recipe['test_conditions']['measurement_only']=True
    (R/'management/recipes'/(RUN+'.yaml')).write_text(json.dumps(recipe,indent=2)+'\n')
    sourcehash={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in S.iterdir() if p.name in ['test.scs','models.scs','cdac_core.scs','wrappers.scs','manual8_sample.va','manual8_cmp.va','manual8_sar.va']}
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in B.iterdir()}
    assert all(hashes[k]==h for k,h in sourcehash.items() if k!='test.scs')
    assert (B/'test.scs').read_text()==test+'save '+' '.join(extra)+'\n'
    (B/'manifest.json').write_text(json.dumps({'source_run':'manual8-cdac-s100-ffhot-v1','run_id':RUN,
        'source_hashes':sourcehash,'input_hashes':hashes,'only_netlist_change':'appended save statement',
        'extra_signal_count':len(extra),'branches':branches},indent=2)+'\n')
    print(RUN,'prepared; added',len(extra),'current signals')

if __name__=='__main__':main()
