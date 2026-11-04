"""Compare native candidate measurements with the completed original D1."""
import csv,gzip,json,itertools
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sar_cdn_report import cross
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'verification/manual_adc/sar_isolation_v1/dff_candidates_v1'
IDS=['manual8-cdn-s0-reduce-v2','manual8-dff-syn-tt-v1','manual8-dff-gdf-tt-v1']
LABELS=['DFCNQD1','SDFSYNCNQD1','GDFCNQMCOD1'];COLORS=['#2166ac','#e08214','#25844c']
def load(rid):
 p=ROOT/'output/managed_execution/runs'/rid/'collected/derived'
 with gzip.open(p/'wave.csv.gz','rt') as f:
  r=csv.reader(f);keys=next(r);a=np.array(list(r),dtype=float)
 w=dict(zip(keys,a.T));w['0']=np.zeros(len(a))
 return json.loads((p/'result.json').read_text()),w
def entry(r,inst,scope):
 rows=[]
 for dev,mp in r['device_pairs'].items():
  if not dev.startswith(inst+'.'):continue
  for pair,key in mp.items():
   s=r['terminal_stats'][scope][key];interval=s['peak_interval_s'] or [0,0]
   rows.append(dict(device=dev,pair=pair,nodes=r['pair_nodes'][key]['nodes'],peak_V=s['peak_V'],peak_t_ns=s['peak_t_s']*1e9,peak_nodes_V=s['peak_nodes_V'],peak_interval_ps=(interval[1]-interval[0])*1e12,longest_ps=s['longest_over_s']*1e12,total_ps=s['total_over_s']*1e12))
 return sorted(rows,key=lambda x:-x['peak_V'])
def main():
 cases=[load(i) for i in IDS];summary=[];validation=[]
 for i,(r,w) in enumerate(cases):
  t=w['time'];mask=(t>=4.85e-9)&(t<=6.2e-9)
  assert len(t)==r['native_points'] and abs(t[-1]-9e-9)<1e-15 and np.all(np.diff(t)>0)
  row=dict(cell=LABELS[i],source=IDS[i],native_points=len(t),function_pass=r['function_pass'],supply_energy_fJ=r['supply_energy_J']*1e15,reset_supply_energy_fJ=r['reset_supply_energy_J']*1e15,CP_abs_charge_fC=float(np.trapezoid(abs(w['vcp:1']),t)*1e15),CP_net_source_work_fJ=float(np.trapezoid(-w['cp']*w['vcp:1'],t)*1e15),instances={})
  for inst in ['XA','XB']:
   allrows=entry(r,inst,'all');resets=entry(r,inst,'reset');q='qa' if inst=='XA' else 'qb';prefix=inst.lower()+'.'
   a=cross(t,w[q],.09,-1);b=cross(t,w[q],.45,1,1.9e-9,2.3e-9)
   mm64=r['terminal_stats']['reset'][r['device_pairs'][inst+'.MM64']['DS']]
   node='net53' if i==1 else 'net176';gate='net0217' if i==1 else 'mq'
   c=cross(t,w[prefix+gate],.81,-1);d=cross(t,w[prefix+gate],.09,-1)
   row['instances'][inst]=dict(reset_worst=resets[0],all_worst=allrows[0],reset_failures=[s for s in resets if s['peak_V']>.99],all_failure_count=sum(s['peak_V']>.99 for s in allrows),qf_peak_V=float(w[prefix+'qf'][mask].max()),master_source_node=node,master_source_min_V=float(w[prefix+node][mask].min()),master_stack_gate=gate,stack_gate_fall_ps=None if c is None or d is None else (d-c)*1e12,MM64_VDS_peak_V=mm64['peak_V'],MM64_over_ps=mm64['longest_over_s']*1e12,reset_to_10pct_ps=None if a is None else (a-5e-9)*1e12,CP_to_Q50_preset_ps=None if b is None else (b-2e-9)*1e12)
  # Independent peak and continuous-time integration cross-check for all pairs.
  peakerr=0.;widtherr=0.
  for scope in ['all','reset']:
   m=np.ones_like(t,dtype=bool) if scope=='all' else mask;tt=t[m]
   for key,s in r['terminal_stats'][scope].items():
    x,y=r['pair_nodes'][key]['nodes'];v=abs(w[x][m]-w[y][m]);peakerr=max(peakerr,float(abs(v.max()-s['peak_V'])))
    old=v[:-1];new=v[1:];dt=np.diff(tt);above=(old>.99)&(new>.99);trans=(old>.99)!=(new>.99)
    area=float(dt[above].sum());frac=(.99-old[trans])/(new[trans]-old[trans]);area+=float((dt[trans]*np.where(old[trans]>.99,frac,1-frac)).sum());widtherr=max(widtherr,abs(area-s['total_over_s']))
  assert peakerr<1e-12 and widtherr<1e-21
  for lo,hi,bits in [(.2,.9,[0,0]),(3.2,4.8,[1,1]),(6,6.9,[0,0]),(7.1,7.8,[0,0]),(8.3,9,[1,0])]:
   m=(t>=lo*1e-9)&(t<=hi*1e-9)
   for q,bit in zip(['qa','qb'],bits):assert np.all(w[q][m]>.81 if bit else w[q][m]<.09)
  kcl=max(float(abs(sum(w[inst+'.'+dev+':'+str(k)] for k in range(1,5))).max()) for inst in ['xa','xb'] for dev in ['mm64','mm65','mm66','mm75','mm76','mm78']);assert kcl<1e-12
  validation.append(dict(cell=LABELS[i],peak_error_V=peakerr,width_error_s=widtherr,stable_function_pass=True,KCL_max_A=kcl))
  summary.append(row)
 plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
 for inst in ['XA','XB']:
  fig,axs=plt.subplots(4,1,figsize=(11,10),sharex=True,layout='constrained')
  fig.suptitle(('A: D fixed high' if inst=='XA' else 'B: same D falling edge')+' — native-cell comparison\nTT / 0.9 V / 27 C | CDN 1x unchanged | ideal sources | Q load 5 fF',fontsize=13)
  for i,(r,w) in enumerate(cases):
   x=(w['time']-5e-9)*1e12;p=inst.lower()+'.';col=COLORS[i]
   if inst=='XA':
    traces=[w[p+'qf_x'],w[p+'qf'],w['qa'],None]
   else:
    node='net53' if i==1 else 'net176';gate='net0217' if i==1 else 'mq'
    traces=[w[p+gate],w[p+node],w[p+'mq_x']-w[p+node],None]
   # Envelope across all terminal pairs, so changing device IDs cannot hide stress.
   envelope=np.zeros_like(x)
   for dev,mp in r['device_pairs'].items():
    if dev.startswith(inst+'.'):
     for key in mp.values():
      a,b=r['pair_nodes'][key]['nodes'];envelope=np.maximum(envelope,abs(w[a]-w[b]))
   traces[3]=envelope
   for j,y in enumerate(traces):axs[j].plot(x,y,color=col,label=LABELS[i])
  labels=['qf_x (V)','qf (V)','Q_A (V)','Max terminal |V| (V)'] if inst=='XA' else ['MM65 gate (V)','MM64 source (V)','MM64 VDS (V)','Max terminal |V| (V)']
  for ax,lab in zip(axs,labels):ax.set_ylabel(lab);ax.set_xlim(-30,420 if inst=='XB' else 120)
  axs[0].legend(loc='upper right',ncol=3,fontsize=9)
  for j in ([1,3] if inst=='XA' else [2,3]):axs[j].axhline(.99,color='#b22',ls='--',lw=1)
  if inst=='XB':axs[1].set_ylim(-.3,.08)
  axs[3].set_ylim(.88,max(1.12,max(summary[i]['instances'][inst]['reset_worst']['peak_V'] for i in range(3))+.025))
  axs[-1].set_xlabel('Time relative to CDN 50% crossing (ps)')
  fig.savefig(OUT/(inst.lower()+'_comparison.png'),dpi=160);plt.close(fig)
 fig,axs=plt.subplots(4,1,figsize=(11,8),sharex=True,layout='constrained')
 fig.suptitle('Functional reset and capture comparison\nTT / 0.9 V / 27 C | ideal CDN1x, CP and D | Q load 5 fF',fontsize=13)
 for i,(r,w) in enumerate(cases):
  if i==0:axs[0].plot(w['time']*1e9,w['cp'],color='#555');axs[1].plot(w['time']*1e9,w['cdn'],color='#555')
  for j,n in enumerate(['qa','qb'],2):axs[j].plot(w['time']*1e9,w[n],color=COLORS[i],label=LABELS[i])
 for ax,lab in zip(axs,['CP (V)','CDN (V)','Q_A (V)','Q_B (V)']):ax.set_ylabel(lab);ax.set_xlim(0,9);ax.set_ylim(-.05,1);ax.axvline(5,ls=':',color='#888');ax.axvline(7,ls=':',color='#888')
 axs[2].legend(ncol=3);axs[-1].set_xlabel('Time (ns)');fig.savefig(OUT/'function.png',dpi=160);plt.close(fig)
 (OUT/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n');(OUT/'validation.json').write_text(json.dumps(dict(cases=validation,new_simulations=2,baseline_rerun=False,adopted=False,OA_changed=False),indent=2)+'\n')
 for r in summary:
  print(r['cell'],'energy_fJ',r['supply_energy_fJ'],'CP_charge_fC',r['CP_abs_charge_fC'])
  for inst,z in r['instances'].items():print(inst,json.dumps({k:v for k,v in z.items() if k!='reset_failures'}))
if __name__=='__main__':main()
