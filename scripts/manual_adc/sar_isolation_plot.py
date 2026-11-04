"""Plot collected bounded waveforms. Metrics remain native-point measurements."""
import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];run=sys.argv[1]
p=R/'output/managed_execution/runs'/run/'collected/derived'
if not p.exists():p=R/'output/managed_execution/runs'/run/'collected'
r=json.loads((p/'result.json').read_text());d=pd.read_csv(p/'wave.csv.gz');t=d['time'].to_numpy()*1e9
out=R/'verification/manual_adc/sar_isolation_v1/figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22,'axes.spines.top':False,'axes.spines.right':False})
def a(k):return np.zeros(len(t)) if k=='0' else d[k].to_numpy()
def word(keys):return sum((a(k)>.45).astype(int)*(1<<i) for i,k in enumerate(keys))
raw=word(['xdut.'+s for s in ['net14','net30','net29','net28','net27','net24','net33','net31']]);codes=word(['do_'+str(i) for i in range(8)])
mask=(t>=140)&(t<=212)
fig,axs=plt.subplots(6,1,figsize=(12,10),sharex=True,gridspec_kw={'height_ratios':[1,1,1.5,1,3,1.5]})
for ax,k,label in zip(axs[:2],['clks','cmpck'],['Sampling CLKS','Compare CMPCK']):
 ax.plot(t[mask],a(k)[mask],lw=1);ax.set_ylabel(label+'\n(V)');ax.set_ylim(-.08,1.02)
axs[2].plot(t[mask],a('dcmpn')[mask],label='N',lw=1);axs[2].plot(t[mask],a('dcmpp')[mask]+1.15,label='P (+1.15 V)',lw=1);axs[2].set_ylabel('Ideal response\n(V, offset)');axs[2].legend(loc='upper right',ncol=2)
axs[3].plot(t[mask],a('xdut.valid')[mask]);axs[3].set_ylabel('Native VALID\n(V)')
for i in range(8):axs[4].plot(t[mask],a('xdut.clk_'+str(7-i))[mask]/.9+1.4*(7-i),lw=1)
axs[4].set_yticks([1.4*i+.4 for i in range(8)],['CLK'+str(i) for i in range(8)]);axs[4].set_ylabel('Thermometer chain\n(normalized, offset)')
axs[5].step(t[mask],raw[mask],where='post',label='Raw P');axs[5].step(t[mask],codes[mask],where='post',label='Registered DO');axs[5].set_ylabel('Code');axs[5].set_xlabel('Time (ns)');axs[5].legend(ncol=2)
for ax in axs:ax.axvline(149.975,color='k',ls=':',lw=.7);ax.axvline(210.025,color='k',ls=':',lw=.7)
boundary='TB-A: prescribed comparator bits; no analog signal path' if r['mode']=='a' else 'TB-B: VA sampler / CDAC / comparator'
fig.suptitle(run+' | TT / 0.9 V / 27 C / 10 MS/s\n'+boundary+'; native SAR + ideal logic delay; static MOS gates; DO=5 fF',fontsize=11)
fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(out/(run+'_timing.png'),dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(12,3.6));idx=np.arange(16);ax.step(idx,[x['expected'] for x in r['frames']],where='mid',label='Expected',lw=2);ax.plot(idx,[x['output'] for x in r['frames']],'o',mfc='none',label='Registered DO');ax.set(xlabel='Frame',ylabel='Code',xticks=idx,title=run+' | 16 frames, expected vs registered output');ax.legend();fig.tight_layout();fig.savefig(out/(run+'_codes.png'),dpi=160);plt.close(fig)
# Display three known mechanisms at high-resolution first-two-frame windows.
cases=[('Reset: I5 qf','xdut.i5.qf',10.0,10.25),('Shift: I12 internal source','xdut.i12.net176',109.9,111.0),('Output: I46_3 master','xdut.i46_3.net0118',150,190)]
fig,axs=plt.subplots(2,3,figsize=(14,6))
for col,(title,node,lo,hi) in enumerate(cases):
 inst=['XDUT.I5.','XDUT.I12.','XDUT.I46_3.'][col]
 # Select the largest pair in this displayed window, not an unrelated global event.
 mask=(t>=lo)&(t<=hi);pk=-1;best=None
 for dev,ps in r['device_pairs'].items():
  if not dev.startswith(inst):continue
  for pair,key in ps.items():
   n1,n2=r['terminal_pairs'][key]['nodes'];v=np.abs(a(n1)-a(n2));value=v[mask].max()
   if value>pk:pk=value;best=(dev,pair,n1,n2,v)
 dev,pair,n1,n2,v=best;peak_idx=np.flatnonzero(mask)[np.argmax(v[mask])];tp=t[peak_idx]
 # Zoom around the actual maximum in the nominated event window.
 width=.12 if col==0 else .55;z=(t>=tp-width)&(t<=tp+width)
 for k in dict.fromkeys([n1,n2,'clks' if col<2 else 'xdut.net28']):axs[0,col].plot(t[z],a(k)[z],label=k,lw=1.2)
 axs[0,col].legend(fontsize=7);axs[0,col].set_title(title);axs[0,col].set_ylabel('Node voltage (V)')
 axs[1,col].plot(t[z],v[z],label=dev.split('.')[-1]+' |V'+pair+'|');axs[1,col].axhline(.99,color='r',ls='--',label='0.99 V screen');axs[1,col].legend(fontsize=8);axs[1,col].set_xlabel('Time (ns)');axs[1,col].set_ylabel('Terminal difference (V)')
fig.suptitle(run+' | Representative internal stress at TT / 0.9 V / 27 C\nDisplay decimated to 2 ps in these windows; numerical metrics use every native point',fontsize=12)
fig.tight_layout(rect=[0,0,1,.91]);fig.savefig(out/(run+'_stress.png'),dpi=180);plt.close(fig)
print(out)
