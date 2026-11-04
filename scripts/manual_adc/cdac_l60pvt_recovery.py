"""A separately identified numerical recovery; no circuit or stimulus changes."""
import hashlib
import json
from pathlib import Path

R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc/cdac_l60pvt_v1'
key='ss081cold_i1p'; run='manual8-cdac-l60-ss081cold-i1p-v1'
dst=B/key
assert not dst.exists()
dst.mkdir()
recipe=json.loads((R/'management/recipes/manual8-cdac-l60-ss081cold-v1.yaml').read_text())
for item in recipe['inputs']:
    src=R/item['source']
    if src.parent==B/'ss081cold':
        (dst/item['name']).write_bytes(src.read_bytes())
        item['source']=(dst/item['name']).relative_to(R).as_posix()
p=dst/'test.scs'; text=p.read_text(); assert text.count('iabstol=1e-14')==1
p.write_text(text.replace('iabstol=1e-14','iabstol=1e-12'))
cfg=json.loads((dst/'measure.json').read_text())
cfg['leakage']['run_id']=run
cfg['experiment'].update(case=key,numerical_recovery_from='manual8-cdac-l60-ss081cold-v1',iabstol_A=1e-12)
(dst/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
recipe['run_id']=run
recipe['test_conditions']['single_variable']=cfg['experiment']
(R/'management/recipes'/(run+'.yaml')).write_text(json.dumps(recipe,indent=2)+'\n')
manifest=json.loads((B/'manifest.json').read_text())
q=dict(manifest['cases']['ss081cold'])
q.update(run_id=run,numerical_recovery_from='manual8-cdac-l60-ss081cold-v1',iabstol_A=1e-12)
q['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.iterdir()}
manifest['cases'][key]=q
(B/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(run)
