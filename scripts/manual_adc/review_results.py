import json,gzip,re,itertools
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def load(run):
 p=ROOT/'output/managed_execution/runs'/run/'collected/derived'
 if not (p/'wave.csv.gz').exists():return None
 with gzip.open(p/'wave.csv.gz','rt') as f:
  header=f.readline().strip().split(',');a=np.loadtxt(f,delimiter=',')
 return dict(zip(header,a.T)),json.loads((p/'result.json').read_text())
def at(d,k,t):return float(np.interp(t,d['time'],d[k]))
report={}
for run in ['manual8-sample-base-v2','manual8-sample-io-v1','manual8-sample-sine-io-v1','manual8-cmp-base-v1','manual8-cmp-hold-v1','manual8-cdac-steps-v1','manual8-logic-rc-v1','manual8-logic-patterns-v1']:
 z=load(run)
 if not z:continue
 d,r=z;t=d['time'];s={'warnings':r['native_state']['warning_codes'],'mean_VDD_power_W':r['supply_mean_W'],'native_points':r['native_points']}
 if 'sample' in run:
  if 'sine' not in run:s['track_hold_error_mV']={str(atns):[1e3*(at(d,'out'+str(i),atns*1e-9)-at(d,'in'+str(i),atns*1e-9)) for i in range(3)] for atns in [49,51,149,151]}
  else:
   ts=np.array([49.975,149.975,249.975,349.975,449.975,549.975])*1e-9
   omega=2*np.pi*4.502e6;H=np.array([np.ones(len(ts)),np.sin(omega*ts),np.cos(omega*ts)]).T
   s['sine_fit_six_samples_diagnostic_only']={}
   for i in range(3):
    y=np.interp(ts+2e-9,t,d['out'+str(i)]);q=np.linalg.lstsq(H,y,rcond=None)[0];res=y-H@q
    s['sine_fit_six_samples_diagnostic_only'][str(i)]={'offset_V':q[0],'amplitude_V':float(np.hypot(q[1],q[2])),'phase_rad':float(np.arctan2(q[2],q[1])),'residual_rms_V':float(np.sqrt(np.mean(res**2))),'not_ENOB':True}
  # exact sampled MOS terminal voltages; report all6 pair peaks independently of native warning count.
  native=(ROOT/'output/manual_adc/native/L2_bootstrap_switch/input.scs').read_text().replace('\\\n',' ')
  mos=re.findall(r'^(M\w+) \(([^)]+)\) (?:nch|pch)_mac',native,re.M)
  s['boot_terminal_pairs']={}
  for j in range(3):
   def wave(n):
    names={'GND':np.zeros(len(t)),'VDD':d['vdd'],'VIN':d.get('vin',d.get('in'+str(j))),'VOUT':d['out'+str(j)],'CLKS':d['clks']}
    return names[n] if n in names else d['x%d.%s'%(j,n.lower())]
   for name,nodes in mos:
    vals=[wave(n) for n in nodes.split()]
    for a,b in itertools.combinations(range(4),2):
     v=np.abs(vals[a]-vals[b]);k=int(np.argmax(v));s['boot_terminal_pairs']['X%d.%s:%s%s'%(j,name,'DGSB'[a],'DGSB'[b])]=dict(peak_V=float(v[k]),time_s=float(t[k]))
 if 'logic' in run:
  cs=[]
  for j in range(int((t[-1]-111e-9)/100e-9)+1):
   tt=111e-9+j*100e-9
   cs.append({'expected':([0,255,85,170,128,127,1,254][j] if 'patterns' in run else j),'actual':sum((1<<i) for i in range(8) if at(d,'do_'+str(i),tt)>.45)})
  s['captures']=cs;s['mismatches']=[c for c in cs if c['expected']!=c['actual']]
 if 'cmp' in run:
  for j in range(4):
   ee=r['edges'].get('valid'+str(j),[]);s['case'+str(j)]={'VALID_first_rise_ns':next((e[0]*1e9 for e in ee if e[1]==1),None)}
   ck=next((e[0]*1e9 for e in r['edges'].get('ck',[]) if e[1]==1),None)
   if ck is not None:s['case'+str(j)]['clock50_to_VALID50_ns']=s['case'+str(j)]['VALID_first_rise_ns']-ck
   if 'p'+str(j) in d:
    ix=(t>=9e-9)&(t<=13e-9);vd=d['p'+str(j)]-d['n'+str(j)];ref=at(d,'p'+str(j),9e-9)-at(d,'n'+str(j),9e-9)
    s['case'+str(j)]['max_differential_kickback_mV']=float(np.max(np.abs(vd[ix]-ref))*1000)
 if 'cdac' in run:
  res=.1;cm=.45;ls=[]
  for b in range(7,0,-1):
   step=.9*2**(b-1)/128;res-=step if res>=0 else -step;cm+=step/2 if b==7 else -step/2
   ts=(55+(7-b)*5+4)*1e-9;p=at(d,'topp',ts);n=at(d,'topn',ts)
   ls.append(dict(bit=b,time_ns=ts*1e9,ideal_diff_V=res,actual_diff_V=p-n,error_mV=1e3*(p-n-res),ideal_CM_V=cm,actual_CM_V=(p+n)/2))
  s['steps']=ls
 report[run]=s
out=ROOT/'verification/manual_adc/results';out.mkdir(exist_ok=True)
(out/'module_summary.json').write_text(json.dumps(report,indent=2)+'\n')
for k,v in report.items():
 w=dict(v);w.pop('boot_terminal_pairs',None);w.pop('captures',None);print(k,json.dumps(w)[:1800])
