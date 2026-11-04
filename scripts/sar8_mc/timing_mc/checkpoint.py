"""Recover bounded native pilot metrics and scheduling decisions, without polling waveforms."""
import base64
import json
import shlex
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'verification/sar8_mc/timing_mc'
REMOTE=r'''
import os,json,hashlib
root='/server_local_ssd/chenzc_intern25/sar-adc-t28'
prefix=root+'/campaigns/sar8-timing-mc-20261104-'
def read(p):
 if not os.path.isfile(p):return None
 assert os.stat(p).st_size<4*1024*1024
 with open(p) as f:return json.load(f)
pilots={}
for corner in ['ssc','ffc']:
 for seed in [5101,5102]:
  run='sar8tm-%s-s%d-v1'%(corner,seed)
  path=root+'/runs/'+run
  r=read(path+'/derived/result.json')
  if not r:continue
  s=read(path+'/simulation.state.json')
  data={'elapsed_s':s['elapsed_seconds'],'source_hash':read(path+'/registered.json')['recipe_hash'],'frames':[],'first_issue':r['first_issue'],'warnings':r['warning_codes'],'sampling':r['sampling']}
  for f in r['frames']:
   data['frames'].append(dict(frame=f['frame'],code=f['code'],counts=f['counts'],bits=len(f['bits']),issue=f['first_issue'],min_rx_margin_ps=min([b['rx_margin_ps'] for b in f['bits'] if 'rx_margin_ps' in b] or [None])))
  review=read(prefix+'refs/'+run+'_review.json')
  if review:data['held_word_review']={'pass':review['passed'],'problems':review['problems'],'max_abs_delta_lsb':max([abs(b['same_phase_top_delta_lsb']) for b in review['bits'] if 'same_phase_top_delta_lsb' in b] or [None])}
  pilots[run]=data
st={}
for group in ['modules','cold','refs','accel']:
 s=read(prefix+group+'/status.json')
 if s:st[group]={'stage':s['stage'],'completed':len(s.get('completed',[])),'error':s.get('error')}
print(json.dumps(dict(pilots=pilots,queues=st,reference_release=read(prefix+'refs/pilot_pass.json'),reference_issue=read(prefix+'refs/first_issue.json'))))
'''
if __name__=='__main__':
    cmd='python -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(REMOTE.encode()).decode()+"'))")
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',cmd],capture_output=True,encoding='utf-8',timeout=30,check=True)
    result=json.loads(p.stdout)
    (OUT/'checkpoint.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['queues'])
    for k,v in result['pilots'].items():print(k,round(v['elapsed_s']),v['first_issue'],v.get('held_word_review'))

