"""Local plots and comparison using every collected native time point."""
import csv,gzip,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/manual_adc/sar_isolation_v1/cdn_slew_v1'
COLORS=['#2166ac','#e08214','#25844c']
def load(k):
 p=ROOT/f'output/managed_execution/runs/manual8-cdn-s{k}-reduce-v2/collected/derived'
 with gzip.open(p/'wave.csv.gz','rt') as f:
  r=csv.reader(f);keys=next(r);a=np.array(list(r),dtype=float)
 return json.loads((p/'result.json').read_text()),dict(zip(keys,a.T))
def cross(t,y,level,direction,lo=4.8e-9,hi=6.2e-9):
 ids=np.where((t[1:]>=lo)&(t[1:]<=hi)&((y[:-1]>level)&(y[1:]<=level) if direction<0 else (y[:-1]<level)&(y[1:]>=level)))[0]
 if not len(ids):return None
 i=ids[0];return float(t[i]+(t[i+1]-t[i])*(level-y[i])/(y[i+1]-y[i]))
def main():
 cases=[load(k) for k in range(3)];summary=[]
 for k,(r,w) in enumerate(cases):
  t=w['time'];mask=(t>=4.85e-9)&(t<=6.2e-9)
  row=dict(case=r['case'],factor=r['factor'],function_pass=r['function_pass'],native_points=r['native_points'],CDN_fall_ps=(cross(t,w['cdn'],.09,-1)-cross(t,w['cdn'],.81,-1))*1e12,CDN_mid_ns=cross(t,w['cdn'],.45,-1)*1e9,D_mid_ns=cross(t,w['db'],.45,-1)*1e9,supply_energy_fJ=r['supply_energy_J']*1e15,reset_supply_energy_fJ=r['reset_supply_energy_J']*1e15,devices={})
  for inst,device,pair in [('XA','MM76','GB'),('XB','MM64','DS')]:
   s=r['terminal_stats']['reset'][r['device_pairs'][inst+'.'+device][pair]]
   a,b=s['peak_interval_s'] or [0,0]
   row['devices'][inst]=dict(device=device,pair=pair,peak_V=s['peak_V'],peak_time_ns=s['peak_t_s']*1e9,peak_interval_ps=(b-a)*1e12,total_over_ps=s['total_over_s']*1e12,longest_over_ps=s['longest_over_s']*1e12,qf_max_V=float(w[inst.lower()+'.qf'][mask].max()),net176_min_V=float(w[inst.lower()+'.net176'][mask].min()),Q_reset_to_10pct_ps=(cross(t,w['qa' if inst=='XA' else 'qb'],.09,-1)-5e-9)*1e12)
   for node,direction in [('qf_x',1),('mq',-1)]:
    y=w[inst.lower()+'.'+node];a=cross(t,y,.09 if direction>0 else .81,direction);b=cross(t,y,.81 if direction>0 else .09,direction)
    row['devices'][inst][node+'_slew_ps']=None if a is None or b is None else (b-a)*1e12
  worst=[]
  for dev,mp in r['device_pairs'].items():
   for pair,key in mp.items():
    s=r['terminal_stats']['reset'][key]
    if s['peak_V']>.99:worst.append(dict(device=dev,pair=pair,peak_V=s['peak_V'],longest_ps=s['longest_over_s']*1e12))
  row['reset_failures']=sorted(worst,key=lambda x:-x['peak_V']);row['all_window_max_V']=max(s['peak_V'] for s in r['terminal_stats']['all'].values())
  summary.append(row)
 plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
 for inst,title,lim in [('xa','A: fixed D high — reset-induced qf overshoot',(-100,150)),('xb','B: fixed D-fall timing — internal source undershoot',(-100,450))]:
  fig,axs=plt.subplots(4,1,figsize=(11,10),sharex=True,layout='constrained')
  fig.suptitle(title+'\nTT / 0.9 V / 27 C | native DFCNQD1 | Q load 5 fF | ideal finite-edge sources',fontsize=13)
  for k,(r,w) in enumerate(cases):
   x=(w['time']-5e-9)*1e12;c=COLORS[k];lab=f"CDN {r['factor']}x ({summary[k]['CDN_fall_ps']:.2f} ps)"
   axs[0].plot(x,w['cdn'],color=c,label=lab)
   axs[1].plot(x,w[inst+'.qf_x' if inst=='xa' else inst+'.mq'],color=c)
   axs[2].plot(x,w[inst+'.qf' if inst=='xa' else inst+'.net176'],color=c)
   stress=w[inst+'.qf'] if inst=='xa' else w[inst+'.mq_x']-w[inst+'.net176']
   axs[3].plot(x,stress,color=c)
  if inst=='xb':axs[0].plot(x,cases[-1][1]['db'],'--',color='#333',label='D: identical in all cases')
  axs[0].legend(ncol=2,loc='upper right');axs[0].set_ylabel('CDN / D (V)')
  axs[1].set_ylabel('qf_x (V)' if inst=='xa' else 'mq (V)')
  axs[2].set_ylabel('qf (V)' if inst=='xa' else 'net176 (V)');axs[2].axhline(.9 if inst=='xa' else 0,color='#555',ls=':',lw=1)
  if inst=='xb':axs[2].set_ylim(-.23,.035)
  axs[3].set_ylabel('MM76 VGB (V)' if inst=='xa' else 'MM64 VDS (V)');axs[3].axhline(.99,color='#b22',ls='--',label='0.99 V screen');axs[3].legend(loc='upper right');axs[3].set_ylim(.84,1.13)
  axs[-1].set_xlabel('Time relative to CDN 50% crossing (ps)')
  for ax in axs:ax.set_xlim(*lim)
  fig.savefig(OUT/(inst+'_stress.png'),dpi=170);plt.close(fig)
 fig,axs=plt.subplots(5,1,figsize=(11,8),sharex=True,layout='constrained')
 fig.suptitle('Reset and post-release capture: all three edge cases\nTT / 0.9 V / 27 C | original D1, ideal sources, 5 fF load',fontsize=13)
 r,w=cases[0];x=w['time']*1e9
 axs[0].plot(x,w['cp'],color='#555');axs[1].plot(x,w['cdn'],color=COLORS[0]);axs[2].plot(x,w['db'],color='#9b59b6')
 for k,(r,w) in enumerate(cases):
  for i,n in enumerate(['qa','qb'],3):axs[i].plot(w['time']*1e9,w[n],color=COLORS[k],label=str(r['factor'])+'x',lw=1.2)
 axs[3].set_ylabel('Q_A (V)');axs[4].set_ylabel('Q_B (V)');axs[0].set_ylabel('CP (V)');axs[1].set_ylabel('CDN 1x (V)');axs[2].set_ylabel('D_B (V)');axs[4].set_xlabel('Time (ns)');axs[3].legend(ncol=3)
 for ax in axs:ax.set_xlim(0,9);ax.set_ylim(-.05,1);ax.axvline(5,color='#888',ls=':',lw=1);ax.axvline(7,color='#888',ls=':',lw=1)
 fig.savefig(OUT/'function.png',dpi=170);plt.close(fig)
 (OUT/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
