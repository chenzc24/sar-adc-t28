"""Observe both worst latch resets, retaining all initial transient history."""
import json,re,hashlib
from setup import W,ROOT,write,recipe
run='cmpdesign-combo-latch-current-ff-hot-v1';source='cmpdesign-edge-b2i2-ff-hot-v1'
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
base=W/'testbenches'/source;dest=W/'testbenches'/run
cfg=json.loads((base/'measure.json').read_text());r=json.loads((W/'results'/source/'result.json').read_text())
c=next(c for c in cfg['contexts'] if c['name']=='A4_held');windows=[]
for node in ['ln','lp']:
    p=max([p for p in r['contexts']['A4_held']['reset_pulses'] if p['node']==node],key=lambda p:p['peak_V'])
    e=cfg['events'][p['event_index']];target='XA4_held.'+node.upper()
    branches=[dict(device=d['name'],terminal='DGSB'[i],signal='XA4_held.'+d['name']+':'+str(i+1)) for d in c['devices'] for i,n in enumerate(d['nodes']) if n==target]
    assert len(branches)==7
    windows.append(dict(tag='reset_'+node,target=target,edge_s=e['fall_start'],fall50_s=e['fall50'],window_s=[e['fall_start']-75e-12,e['fall50']+.5e-9],branches=branches,source_pulse=p))
stop=max(w['fall50_s'] for w in windows)+1.5e-9
assert stop<=400e-9
currents=['XA4_held.M%d:%d'%(i,p) for i in range(15) for p in range(1,5)]
fields=['id','ids','igs','igd','igb','ibd','ibs','igidl','igisl','qg','qd','qs','qb']
optional=['XA4_held.M%d:%s'%(i,f) for i in range(15) for f in fields]
original=(base/'test.scs').read_text();deck=original.replace('stop=400n','stop=%.16g'%stop)
assert deck!=original
deck+='save '+' '.join(currents+optional)+'\n'
write(dest/'test.scs',deck)
for n in ['dut.scs','models.scs']:write(dest/n,(base/n).read_text())
measure=dict(run_id=run,source_run_id=source,context='A4_held',stop_s=stop,vdd=.99,corner='ff',temperature_c=125,signals=list(dict.fromkeys(cfg['signals']+currents)),optional_fields=optional,windows=windows,devices=c['devices'])
write(dest/'measure.json',json.dumps(measure,indent=2)+'\n')
recipe(run,dest,measure['signals'],stop,'edge_current_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,rise_ps=200,fall_ps=500,M3_M5_multi=2,M8_M9_multi=2,observation_only=True))
write(dest/'validation.json',json.dumps(dict(only_save_and_stop_changed=True,source_run_id=source,sha256={n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}),indent=2)+'\n')
print(run,'stop',stop,'windows',[(w['tag'],w['source_pulse']['time_s']) for w in windows])
