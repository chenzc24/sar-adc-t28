"""Append observations to unchanged comparator experiments, retain full pre-event history."""
import json,re
from setup import W,write,recipe

for tag,source,key,stop,edge,center,node,devices in [
 ('reset','cmpdesign-b0-i4-ff-hot-v1','B0_held',160e-9,155.5e-9,155.5316829102707e-9,'LN',['M0','M1','M4','M6','M7','M13','M14']),
 ('start','cmpdesign-b0-i4-ff-cold-v1','I4_held',355e-9,354e-9,354.0331704307273e-9,'net2',['M5','M7','M9'])]:
    run='cmpdesign-current-'+tag+'-v1';dest=W/'testbenches'/run;old=W/'testbenches'/source
    cfg=json.loads((old/'measure.json').read_text());context=next(c for c in cfg['contexts'] if c['name']==key)
    for name in ['dut.scs','models.scs']:write(dest/name,(old/name).read_text())
    currents=['X'+key+'.M'+str(i)+':'+str(p) for i in range(15) for p in range(1,5)]
    fields=['id','ids','igs','igd','igb','ibd','ibs','igidl','igisl','qg','qd','qs','qb']
    optional=['X'+key+'.'+d+':'+f for d in devices for f in fields]
    deck=(old/'test.scs').read_text();deck=re.sub(r'stop=400n','stop=%.12g'%stop,deck)
    deck+='save '+' '.join(currents+optional)+'\n'
    write(dest/'test.scs',deck)
    branches=[];target='X'+key+'.'+node
    for dev in context['devices']:
        for i,n in enumerate(dev['nodes']):
            if n==target:branches.append({'device':dev['name'],'terminal':'DGSB'[i],'signal':'X'+key+'.'+dev['name']+':'+str(i+1)})
    measure={'source_run_id':source,'run_id':run,'context':key,'stop_s':stop,'edge_s':edge,'center_s':center,'target':target,
             'vdd':cfg['vdd'],'corner':cfg['corner'],'temperature_c':cfg['temperature_c'],'signals':cfg['signals']+currents,
             'optional_fields':optional,'branches':branches,'window_s':[edge-.1e-9,edge+.25e-9],
             'devices':context['devices'],'source_peak_V':json.loads((W/'results'/source/'result.json').read_text())['contexts'][key]['terminal_pairs']['M14:GB' if tag=='reset' else 'M9:DB']['peak_V']}
    write(dest/'measure.json',json.dumps(measure,indent=2)+'\n')
    recipe(run,dest,measure['signals'],stop,'current_reduce.py',{k:cfg[k] for k in ['corner','vdd','temperature_c']})
    print(run,branches)
