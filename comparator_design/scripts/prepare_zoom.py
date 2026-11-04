"""Pick the worst held-input peak only after all five conditions are collected."""
import json
from setup import W,write
from report import RUNS,load

available=[(label,run,load(run)) for label,run in RUNS]
peak,label,run,key,data=max([(r['peak_terminal_V'],label,run,k,d) for label,run,d in available for k,r in d['contexts'].items() if k.endswith('_held')],key=lambda a:a[0])
pair,entry=max(data['contexts'][key]['terminal_pairs'].items(),key=lambda a:a[1]['peak_V'])
source=data['source_run_id'];cfg=json.loads((W/'testbenches'/source/'measure.json').read_text())
context=next(c for c in cfg['contexts'] if c['name']==key)
device,pins=pair.split(':');dev=next(d for d in context['devices'] if d['name']==device)
nodes=[dev['nodes']['DGSB'.index(p)] for p in pins];run_id='cmpdesign-worst-terminal-zoom-v1'
zoom={'source_run_id':source,'start_s':entry['time_s']-.35e-9,'end_s':entry['time_s']+.55e-9,'pair_nodes':nodes,'expected_peak_V':peak,'signals':cfg['signals']}
write(W/'testbenches'/run_id/'zoom.json',json.dumps(zoom,indent=2)+'\n')
r=json.loads((W/'recipes'/('cmpdesign-sizing-tt-measure-v2.yaml')).read_text())
r.update(run_id=run_id,source_run_id=source,analyzer='zoom_reduce.py')
r['summary_signals']=cfg['signals'];r['test_conditions']={k:cfg[k] for k in ['corner','vdd','temperature_c']}
r['inputs']=[{'source':'comparator_design/scripts/'+n,'name':n} for n in ['zoom_reduce.py','native_frames.py']]+[{'source':'comparator_design/testbenches/'+run_id+'/zoom.json','name':'zoom.json'}]
write(W/'recipes'/(run_id+'.yaml'),json.dumps(r,indent=2)+'\n')
write(W/'results/zoom_selection.json',json.dumps({'run_id':run_id,'source_run_id':source,'context':key,'pair':pair,'expected_peak_V':peak},indent=2)+'\n')
print(run_id,source,key,pair,peak)
