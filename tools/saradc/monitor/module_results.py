"""Recover only compact per-seed native measurement summaries, including unresolved seeds."""
import base64
import json
import shlex
import statistics
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'work/state/timing_mc'
REMOTE=r'''
import json,os,sys
root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs'
data=[]
for family in ['cdac','comp']:
 for seed in range(4101,4301):
  run=('sar8mc-%s-s%d-v2' if seed<4131 else 'sar8tm-%s-s%d-v1')%(family,seed)
  d=root+'/'+run
  path=d+'/derived/result.json'
  if not os.path.exists(path):continue
  if json.load(open(d+'/analysis.state.json'))['status']!='complete':continue
  assert os.path.getsize(path)<1024*1024
  r=json.load(open(path));assert r['context']['run_id']==run and r['context']['seed']==seed
  row=dict(run=run,seed=seed,family=family,native_valid=r['native_data_valid'],warnings=r['warning_codes'],draw_hash=r['mismatch_evidence']['values_sha256'])
  if family=='cdac':
   w=r['weights'];row.update(monotonic=w['dac_levels_monotonic'],abs_dnl=w['dac_dnl_abs_max_lsb'],abs_inl=w['dac_inl_endpoint_abs_max_lsb'])
  else:row.update(threshold_valid=r['threshold_valid'],offset_mv=r['offset_midpoint_v']*1000 if r['threshold_valid'] else None,speed=r['speed_probes'])
  data.append(row)
print(json.dumps(data))
'''
if __name__=='__main__':
    cmd='python -c '+shlex.quote("import base64;exec(base64.b64decode('"+base64.b64encode(REMOTE.encode()).decode()+"'))")
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',cmd],capture_output=True,encoding='utf-8',timeout=45,check=True)
    assert len(p.stdout)<4*1024*1024
    rows=json.loads(p.stdout)
    cs=[r for r in rows if r['family']=='cdac']
    vs=[r for r in rows if r['family']=='comp']
    for family in (cs,vs):
        assert len(set(r['draw_hash'] for r in family))==len(family)
    offsets=[r['offset_mv'] for r in vs if r['threshold_valid'] and r['native_valid']]
    summary=dict(complete=len(cs)==200 and len(vs)==200,cdac=len(cs),comparator=len(vs),valid_offsets=len(offsets),offset_sample_sd_mv=statistics.stdev(offsets) if len(offsets)>1 else None,offset_range_mv=[min(offsets),max(offsets)] if offsets else [],abs_dnl=max((r['abs_dnl'] for r in cs),default=None),abs_inl=max((r['abs_inl'] for r in cs),default=None))
    (OUT/'module_results.json').write_text(json.dumps(dict(summary=summary,rows=rows),indent=2)+'\n')
    print(summary)
