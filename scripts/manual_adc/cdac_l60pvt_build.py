"""Frozen L60 corners, ideal logic follows VDD; input/reference remain 0..0.9V."""
import ast
import copy
import hashlib
import json
from pathlib import Path

R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc/cdac_l60pvt_v1'
S=R/'verification/manual_adc/cdac_nlength_v1/l60'
CASES=[('ss090cold','ss',.90,-40),('ss081cold','ss',.81,-40),('ff099cold','ff',.99,-40),('ff099hot','ff',.99,125)]
SCOPE='L60 native reference MOS / ideal caps and surrounding blocks; fixed0..0.9V input/reference, logic and PMOS body follow VDD; short PVT screen only.'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def analyzers():
    p=R/'scripts/manual_adc/cdac_edge_reduce.py';old=p.read_text()
    edge=old.replace('def signature(v):','TH=.45\nLOGIC_V=.9\n\ndef signature(v):')
    edge=edge.replace('>=.45','>=TH').replace('>.45','>TH').replace('<.45','<TH').replace('(.45-','(TH-').replace('else .45','else TH')
    edge=edge.replace('level=.009 if vx[k]>vp[k] else .891','level=.01*LOGIC_V if vx[k]>vp[k] else .99*LOGIC_V')
    edge=edge.replace('    p=argparse.ArgumentParser();','    global TH,LOGIC_V\n    p=argparse.ArgumentParser();',1)
    token="state=json.load(open(src+'/simulation.state.json'))"
    edge=edge.replace(token,"LOGIC_V=cfg['logic_vdd_V'];TH=.5*LOGIC_V\n    "+token)
    # All source hardcoded0.45 thresholds replaced; .5 remains normalized sample fraction.
    assert edge.count('.45')==1
    edgepath=R/'scripts/manual_adc/cdac_l60pvt_edge_reduce.py';edgepath.write_text(edge)
    leak=(R/'scripts/manual_adc/cdac_leak_reduce.py').read_text()
    leak=leak.replace('import cdac_edge_reduce','import cdac_l60pvt_edge_reduce as cdac_edge_reduce')
    leak=leak.replace("result=json.load(open(a.output_dir+'/result.json'))","result=json.load(open(a.output_dir+'/result.json'))\n    TH=.5*cfg['logic_vdd_V']")
    leak=leak.replace('<.45','<TH').replace('>=.45','>=TH').replace('(.45-','(TH-')
    assert '.45' not in leak
    needle="devices=cfg['devices'];branches=ex['branches'];windows=ex['steady_windows_s']"
    add="""
    # Export all native samples around every terminal peak and bottom minimum.
    # Metrics still use every point; merged intervals bound local plot payload.
    ranges=list(ex['native_windows_s'])
    ranges += [(q['time_s']-300e-12,q['time_s']+300e-12) for q in result['terminal_pairs']]
    ranges += [(q['min_s']-300e-12,q['min_s']+300e-12) for k,q in result['node_extrema'].items() if '.xd.net' in k]
    merged=[]
    for left,right in sorted(ranges):
        if merged and left<=merged[-1][1]:merged[-1][1]=max(right,merged[-1][1])
        else:merged.append([left,right])
    result['current_export_native_windows_s']=merged
"""
    leak=leak.replace(needle,needle+add).replace("for start,end in ex['native_windows_s']","for start,end in merged")
    leak=leak.replace("'export':'All native points in64..72ns and164..172ns; outside these windows >=100ps display sampling. Metrics use all native points.'","'export':'All native points in current_export_native_windows_s; elsewhere >=100ps display sampling. Metrics use all native points.'")
    leakpath=R/'scripts/manual_adc/cdac_l60pvt_leak_reduce.py';leakpath.write_text(leak)
    for source in [edge,leak]:ast.parse(source)
    return {'edge_source_sha':sha(p),'edge_candidate_sha':sha(edgepath),'leak_source_sha':sha(R/'scripts/manual_adc/cdac_leak_reduce.py'),'leak_candidate_sha':sha(leakpath)}

def main():
    B.mkdir(exist_ok=True)
    assert not (B/'manifest.json').exists(), 'Do not overwrite a prepared batch'
    manifest={'source_run':'manual8-cdac-nl60-ffhot-v1','scope':SCOPE,'analyzer':analyzers(),'cases':{}}
    template=json.loads((R/'management/recipes/manual8-cdac-nl60-ffhot-v1.yaml').read_text())
    for key,corner,vdd,temp in CASES:
        folder=B/key;folder.mkdir()
        recipe=copy.deepcopy(template);run='manual8-cdac-l60-'+key+'-v1'
        for item in recipe['inputs']:
            if item['source'].startswith('verification/manual_adc/'):
                (folder/item['name']).write_bytes((S/item['name']).read_bytes())
                item['source']=(folder/item['name']).relative_to(R).as_posix()
            elif item['name']=='cdac_edge_reduce.py':
                item.update(name='cdac_l60pvt_edge_reduce.py',source='scripts/manual_adc/cdac_l60pvt_edge_reduce.py')
            elif item['name']=='cdac_leak_reduce.py':
                item.update(name='cdac_l60pvt_leak_reduce.py',source='scripts/manual_adc/cdac_l60pvt_leak_reduce.py')
        (folder/'models.scs').write_text((S/'models.scs').read_text().replace('section=ffmacro_mos_moscap','section='+corner+'macro_mos_moscap'))
        old=(S/'test.scs').read_text();test=old.replace('VVDD (VDD 0) vsource dc=.9','VVDD (VDD 0) vsource dc=%.2f'%vdd).replace('val0=0 val1=.9 delay','val0=0 val1=%.2f delay'%vdd).replace('temp=125 tnom=27','temp=%d tnom=27'%temp)
        assert test.replace('VVDD (VDD 0) vsource dc=%.2f'%vdd,'VVDD (VDD 0) vsource dc=.9').replace('val0=0 val1=%.2f delay'%vdd,'val0=0 val1=.9 delay').replace('temp=%d tnom=27'%temp,'temp=125 tnom=27')==old
        (folder/'test.scs').write_text(test)
        cfg=json.loads((folder/'measure.json').read_text());cfg['logic_vdd_V']=vdd;cfg['scope']=SCOPE
        cfg['experiment'].update(case=key,corner=corner,temperature_c=temp,logic_vdd_V=vdd,reference_v=0.9)
        cfg['leakage'].update(run_id=run,source_run_id=manifest['source_run'],scope=SCOPE)
        (folder/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
        recipe.update(run_id=run,design_id='manual8_cdac_l60pvt_v1',analyzer='cdac_l60pvt_leak_reduce.py',qualification_scope=SCOPE)
        recipe['test_conditions'].update(corner=corner,vdd=vdd,temperature_c=temp,reference_v=0.9,baseline_run=manifest['source_run'],single_variable=cfg['experiment'])
        (R/'management/recipes'/(run+'.yaml')).write_text(json.dumps(recipe,indent=2)+'\n')
        identical={name:sha(folder/name)==sha(S/name) for name in ['cdac_core.scs','wrappers.scs','manual8_sample.va','manual8_cmp.va','manual8_sar.va']}
        assert all(identical.values())
        manifest['cases'][key]={'run_id':run,'corner':corner,'vdd_V':vdd,'reference_V':.9,'temperature_C':temp,'same_dut_VA':identical,'files':{p.name:sha(p) for p in folder.iterdir()}}
    (B/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Prepared',list(manifest['cases']))

if __name__=='__main__':main()
