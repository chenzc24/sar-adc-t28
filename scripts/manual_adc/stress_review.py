import json,gzip,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];OUT=R/'verification/manual_adc/stress_diagnosis'
run=sys.argv[1] if len(sys.argv)>1 else 'manual8-stress-baseline-v1';p=R/'output/managed_execution/runs'/run/'collected/derived';r=json.loads((p/'result.json').read_text());pairs=r['terminal_pairs'];rows=[]
for dev,links in r['device_pairs'].items():
 for term,key in links.items():
  z=pairs[key]
  if z['peak_V']>.99:rows.append(dict(device=dev,terminals=term,peak_V=z['peak_V'],peak_ns=z['peak_t_s']*1e9,duration_ps=z['duration_gt_990_s']*1e12,phase_max_V=z['phase_max_V'],intervals_ns=[[a*1e9,b*1e9] for a,b in z['intervals_s']]))
rows.sort(key=lambda x:-x['peak_V']);group={}
for row in rows:
 inst=row['device'].rsplit('.',1)[0]
 if inst not in group:group[inst]={'peak_V':0,'devices':set(),'phases':set()}
 g=group[inst];g['peak_V']=max(g['peak_V'],row['peak_V']);g['devices'].add(row['device'].split('.')[-1]);g['phases'].update(k for k,v in row['phase_max_V'].items() if v>.99)
for g in group.values():g['devices']=sorted(g['devices']);g['phases']=sorted(g['phases'])
summary=dict(run=run,coverage=r['coverage'],captures=r['captures'],exceeding_device_count=len(set(x['device'] for x in rows)),groups=group,rows=rows)
(OUT/'stress_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('groups',json.dumps(group,indent=2));print('top20')
for x in rows[:20]:print(x['device'],x['terminals'],round(x['peak_V'],6),round(x['peak_ns'],6),round(x['duration_ps'],3))
print('rows',len(rows),'MOS',summary['exceeding_device_count'],'captures',r['captures'])
