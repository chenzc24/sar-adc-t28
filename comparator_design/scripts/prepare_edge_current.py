"""Observe unchanged 200/500ps A4 through 85ns; keep full initial history."""
import hashlib,json,re
from setup import W,ROOT,write,recipe

run='cmpdesign-edge-current-a4-ff-hot-v1'
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
source='cmpdesign-r200-f500-a4-ff-hot-v1'
old=W/'testbenches'/source;dest=W/'testbenches'/run
cfg=json.loads((old/'measure.json').read_text())
context=next(c for c in cfg['contexts'] if c['name']=='A4_held')
for n in ['dut.scs','models.scs']:write(dest/n,(old/n).read_text())
currents=['XA4_held.M%d:%d'%(i,p) for i in range(15) for p in range(1,5)]
fields=['id','ids','igs','igd','igb','ibd','ibs','igidl','igisl','qg','qd','qs','qb']
optional=['XA4_held.M%d:%s'%(i,f) for i in range(15) for f in fields]
original=(old/'test.scs').read_text()
deck=original.replace('stop=400n','stop=85n')
assert deck!=original
deck+='save '+' '.join(currents+optional)+'\n'
assert deck.splitlines()[:-1]==original.replace('stop=400n','stop=85n').splitlines()
write(dest/'test.scs',deck)
windows=[]
for tag,node,edge,lo,hi in [('reset_net2','net2',79.275e-9,79.2e-9,79.95e-9),('input_net2','net2',80.1e-9,80.0e-9,80.65e-9),('reset_net1','net1',83.275e-9,83.2e-9,83.95e-9)]:
    target='XA4_held.'+node
    branches=[{'device':d['name'],'terminal':'DGSB'[i],'signal':'XA4_held.'+d['name']+':'+str(i+1)} for d in context['devices'] for i,n in enumerate(d['nodes']) if n==target]
    windows.append(dict(tag=tag,target=target,edge_s=edge,window_s=[lo,hi],branches=branches))
measure=dict(source_run_id=source,run_id=run,context='A4_held',stop_s=85e-9,vdd=.99,corner='ff',temperature_c=125,signals=list(dict.fromkeys(cfg['signals']+currents)),optional_fields=optional,windows=windows,devices=context['devices'])
write(dest/'measure.json',json.dumps(measure,indent=2)+'\n')
recipe(run,dest,measure['signals'],85e-9,'edge_current_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,rise_ps=200,fall_ps=500,observation_only=True))
write(dest/'validation.json',json.dumps(dict(only_save_and_stop_changed=True,DUT_models_identical=True,sha256={n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in ['dut.scs','models.scs','test.scs','measure.json']}),indent=2)+'\n')
print(run,'frozen; only observations and stop changed')
