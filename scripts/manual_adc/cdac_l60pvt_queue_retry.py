"""New run only after definitive pre-launch queue rejection and memory recovery."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2]; B=R/'verification/manual_adc/cdac_l60pvt_v1'
oldrun='manual8-cdac-l60-ff099hot-v1'; run='manual8-cdac-l60-ff099hot-v2'; key='ff099hot_retry'
state=json.loads((R/'output/managed_execution/runs'/oldrun/'collected/simulation.state.json').read_text())
assert state['status']=='rejected' and state['reason']=='queue_timeout' and 'started_epoch' not in state
dst=B/key; assert not dst.exists(); dst.mkdir()
recipe=json.loads((R/'management/recipes'/(oldrun+'.yaml')).read_text())
for item in recipe['inputs']:
    src=R/item['source']
    if src.parent==B/'ff099hot':
        (dst/item['name']).write_bytes(src.read_bytes());item['source']=(dst/item['name']).relative_to(R).as_posix()
cfg=json.loads((dst/'measure.json').read_text());cfg['leakage']['run_id']=run
cfg['experiment'].update(case=key,admission_retry_from=oldrun)
(dst/'measure.json').write_text(json.dumps(cfg,indent=2)+'\n')
recipe['run_id']=run;recipe['test_conditions']['single_variable']=cfg['experiment']
(R/'management/recipes'/(run+'.yaml')).write_text(json.dumps(recipe,indent=2)+'\n')
manifest=json.loads((B/'manifest.json').read_text());q=dict(manifest['cases']['ff099hot'])
q.update(run_id=run,admission_retry_from=oldrun)
q['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.iterdir()}
manifest['cases'][key]=q;(B/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(B/'ff099hot_admission_rejection.json').write_text(json.dumps(state,indent=2)+'\n')
print(run)
