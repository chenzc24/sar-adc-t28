"""Reduced observations after confirmed v1 output limit; circuit unchanged."""
import json,re,hashlib
from setup import W,ROOT,write,recipe
run='cmpdesign-combo-latch-current-ff-hot-v2';old='cmpdesign-combo-latch-current-ff-hot-v1'
assert not (ROOT/'management/runs'/(run+'.yaml')).exists(),'Already registered'
base=W/'testbenches'/old;dest=W/'testbenches'/run
cfg=json.loads((base/'measure.json').read_text());cfg['run_id']=run
branches=[b for w in cfg['windows'] for b in w['branches']]
currents=sorted(set(b['signal'] for b in branches))
optional=[]
for b in branches:
    fields=['id','qd'] if b['terminal']=='D' else ['qg','igs','igd','igb']
    optional += ['XA4_held.'+b['device']+':'+f for f in fields]
voltages=['CK','PA4_held','NA4_held','OPA4_held','ONA4_held']+['XA4_held.'+n for n in ['LP','LN','net1','net2','net3']]
cfg['signals']=voltages+currents;cfg['optional_fields']=sorted(set(optional))
deck=re.sub(r'^save .*\n','',(base/'test.scs').read_text(),flags=re.M)
deck+='save '+' '.join(cfg['signals']+cfg['optional_fields'])+'\n'
write(dest/'test.scs',deck)
for n in ['dut.scs','models.scs']:write(dest/n,(base/n).read_text())
write(dest/'measure.json',json.dumps(cfg,indent=2)+'\n')
recipe(run,dest,cfg['signals'],cfg['stop_s'],'edge_current_reduce.py',dict(corner='ff',vdd=.99,temperature_c=125,rise_ps=200,fall_ps=500,M3_M5_multi=2,M8_M9_multi=2,observation_only=True,preceding_failed_run=old))
print(run,'saved signals',len(cfg['signals'])+len(cfg['optional_fields']))
