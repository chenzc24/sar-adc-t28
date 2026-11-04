"""Create new measurements and a bounded B0/I4 corner comparison; no submission."""
import json
from setup import W,write
from build_sizing import build

source='cmpdesign-sizing-tt-v1'
r=json.loads((W/'recipes'/(source+'.yaml')).read_text())
r.update(run_id='cmpdesign-sizing-tt-measure-v2',kind='analysis_only',source_run_id=source)
for key in ['entry','spectre_args']:r.pop(key,None)
r['inputs']=[x for x in r['inputs'] if x['name'] in ['sizing_reduce.py','native_frames.py']]
r['resources']['max_output_mib']=32
write(W/'recipes'/(r['run_id']+'.yaml'),json.dumps(r,indent=2)+'\n')
for corner,vdd,temp,tag in [('ss',.81,-40,'ss-cold'),('ss',.81,125,'ss-hot'),('ff',.99,-40,'ff-cold'),('ff',.99,125,'ff-hot')]:
    build('cmpdesign-b0-i4-'+tag+'-v1',['B0','I4'],corner,vdd,temp)
