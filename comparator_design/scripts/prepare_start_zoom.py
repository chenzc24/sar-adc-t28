"""Export the smaller start-edge overshoot from its existing completed source."""
import json
from setup import W,write

source='cmpdesign-b0-i4-ff-cold-v1';run='cmpdesign-start-overshoot-zoom-v1'
data=json.loads((W/'results'/source/'result.json').read_text())
cfg=json.loads((W/'testbenches'/source/'measure.json').read_text())
peak=data['contexts']['I4_held']['terminal_pairs']['M9:DB']
zoom={'source_run_id':source,'start_s':peak['time_s']-.15e-9,'end_s':peak['time_s']+.35e-9,
      'pair_nodes':['XI4_held.net2','0'],'expected_peak_V':peak['peak_V'],'signals':cfg['signals']}
write(W/'testbenches'/run/'zoom.json',json.dumps(zoom,indent=2)+'\n')
r=json.loads((W/'recipes/cmpdesign-worst-terminal-zoom-v1.yaml').read_text())
r.update(run_id=run,source_run_id=source,summary_signals=cfg['signals'],test_conditions={k:cfg[k] for k in ['corner','vdd','temperature_c']})
r['inputs'][-1]={'source':'comparator_design/testbenches/'+run+'/zoom.json','name':'zoom.json'}
write(W/'recipes'/(run+'.yaml'),json.dumps(r,indent=2)+'\n')
print(run,peak)
