"""Validate collected CDN measurements against an independent array calculation."""
import ast,hashlib,itertools,json,shlex,subprocess
from pathlib import Path
import numpy as np
from sar_cdn_report import load,ROOT,OUT
def main():
 checks=[]
 for k in range(3):
  r,w=load(k);t=w['time'];w['0']=np.zeros_like(t);mask=(t>=4.85e-9)&(t<=6.2e-9)
  assert np.all(np.diff(t)>0) and abs(t[-1]-9e-9)<1e-15
  assert len(t)==r['native_points'];cfg=json.loads((OUT/f's{k}/measure.json').read_text())
  peakerr=0.;durationerr=0.
  for dev in cfg['devices']:
   nodes=[n.lower() for n in dev['terminals']]
   for i,j in itertools.combinations(range(4),2):
    key=r['device_pairs'][dev['path']]['DGSB'[i]+'DGSB'[j]];s=r['terminal_stats']['reset'][key]
    y=np.abs(w[nodes[i]][mask]-w[nodes[j]][mask]);tt=t[mask]
    peakerr=max(peakerr,abs(y.max()-s['peak_V']))
    duration=0.
    for a,b,ya,yb in zip(tt[:-1],tt[1:],y[:-1],y[1:]):
     if ya>.99 and yb>.99:duration+=b-a
     elif (ya>.99)!=(yb>.99):
      c=a+(b-a)*(.99-ya)/(yb-ya);duration+=c-a if ya>.99 else b-c
    durationerr=max(durationerr,abs(duration-s['total_over_s']))
  assert peakerr<1e-12 and durationerr<1e-21
  # Check whole stable intervals, not only sampled truth-table points.
  for lo,hi,expected in [(.2,.9,[0,0]),(3.2,4.8,[1,1]),(6,6.9,[0,0]),(7.1,7.8,[0,0]),(8.3,9,[1,0])]:
   m=(t>=lo*1e-9)&(t<=hi*1e-9)
   for q,bit in zip(['qa','qb'],expected):assert np.all(w[q][m]>.81 if bit else w[q][m]<.09)
  kres=0.
  for inst in ['xa','xb']:
   for m in ['mm64','mm65','mm66','mm75','mm76','mm78']:
    residual=sum(w[inst+'.'+m+':'+str(i)] for i in range(1,5));kres=max(kres,float(abs(residual).max()))
  assert kres<1e-12
  sim=json.loads((ROOT/f'output/managed_execution/runs/manual8-cdn-s{k}-tt-v1/collected/simulation.state.json').read_text())
  ana=json.loads((ROOT/f'output/managed_execution/runs/manual8-cdn-s{k}-reduce-v2/collected/analysis.state.json').read_text())
  assert sim['status']=='complete' and ana['status']=='complete'
  assert ana['source_provenance']['run_id']==f'manual8-cdn-s{k}-tt-v1'
  checks.append(dict(case=k,native_points=len(t),max_peak_error_V=peakerr,max_duration_error_s=durationerr,selected_MOS_terminal_KCL_max_A=kres,stable_function_windows_pass=True,simulation_seconds=sim['elapsed_seconds'],simulation_peak_MiB=sim['peak_rss_bytes']/1024**2,analysis_peak_MiB=ana['peak_rss_bytes']/1024**2,native=sim['native']))
 for p in (ROOT/'scripts/manual_adc').glob('sar_cdn_*.py'):ast.parse(p.read_text(encoding='utf-8'))
 import re
 path=re.search(r'\.include "([^"]+)"',(OUT/'s0/models.scs').read_text())[1]
 actual=subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei','sha256sum '+shlex.quote(path)],text=True).split()[0]
 assert actual=='b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e'
 result=dict(cases=checks,native_library_sha256=actual,library_unchanged=True,simulations=3,additional_simulations_for_analysis_fix=0,analysis_v1_failure='Python2 list-comprehension variable leaked over argparse a; v2 uses args and source_run_dir; original failed states retained',adopted=False,OA_changed=False,figures_reviewed=['xa_stress.png','xb_stress.png','function.png'])
 (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
