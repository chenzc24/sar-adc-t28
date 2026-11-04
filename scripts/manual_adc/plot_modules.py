import sys,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent))
from review_results import load,ROOT
out=ROOT/'verification/manual_adc/figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.constrained_layout.use':True})
a,_=load('manual8-cdac-steps-v1');t=a['time']*1e9
fig,axs=plt.subplots(3,1,figsize=(10,7),sharex=True)
axs[0].plot(t,a['topp'],label='Top P');axs[0].plot(t,a['topn'],label='Top N');axs[0].set_ylabel('Top plate (V)');axs[0].legend(ncol=2)
axs[1].plot(t,a['topp']-a['topn'],label='Measured differential');axs[1].plot(t,(a['topp']+a['topn'])/2,label='Measured common mode')
s=json.loads((ROOT/'verification/manual_adc/results/module_summary.json').read_text())['manual8-cdac-steps-v1']['steps'];axs[1].plot([x['time_ns'] for x in s],[x['ideal_diff_V'] for x in s],'o',mfc='none',label='Ideal differential');axs[1].plot([x['time_ns'] for x in s],[x['ideal_CM_V'] for x in s],'s',mfc='none',label='Ideal common mode');axs[1].set_ylabel('Voltage (V)');axs[1].legend(ncol=2,fontsize=8)
axs[2].plot(t,a['clks'],label='Sample');axs[2].set_ylabel('Sample (V)');axs[2].set_xlabel('Time (ns)')
for ax in axs:ax.axvspan(10,49.975,color='grey',alpha=.08);ax.grid(alpha=.2);ax.set_xlim(5,95)
fig.suptitle('Manual CDAC: first up, then down\nTT / 0.9 V / 27 C; Cunit=10 fF; transistor reference switches; ideal sampling clamp and references',fontsize=11)
fig.savefig(out/'cdac_steps.png',dpi=170);plt.close(fig)
a,_=load('manual8-sample-sine-io-v1');t=a['time']*1e9
fig,axs=plt.subplots(3,1,figsize=(10,7),sharex=True)
axs[0].plot(t,a['vin'],color='k',lw=1,label='Ideal input')
for j in range(3):axs[0].plot(t,a['out'+str(j)],lw=.9,label='Mmain=%d um'%[1,2,4][j])
axs[0].legend(ncol=4,fontsize=8);axs[0].set_ylabel('Voltage (V)')
for j in range(3):
 mask=a['clks']>.89;error=(a['out'+str(j)]-a['vin'])*1000;error[~mask]=np.nan;axs[1].plot(t,error,label='%d um'%[1,2,4][j])
axs[1].set_ylim(-35,35);axs[1].set_ylabel('Track error (mV)');axs[1].axhline(0,color='k',lw=.6)
axs[2].plot(t,a['clks']);axs[2].set_ylabel('Sample (V)');axs[2].set_xlabel('Time (ns)')
for ax in axs:ax.grid(alpha=.2);ax.set_xlim(100,610)
fig.suptitle('Bootstrap IO candidate: tracking and hold\nTT / 0.9 V / 27 C; 4.502 MHz, 0.401 V amplitude; 1.28 pF load; original connections; ideal external sources',fontsize=11)
fig.savefig(out/'sampling_sine.png',dpi=170);plt.close(fig)
a,_=load('manual8-cmp-hold-v1');t=a['time']*1e9
fig,axs=plt.subplots(3,1,figsize=(10,7),sharex=True)
axs[0].plot(t,a['ck'],label='Evaluate clock');axs[0].set_ylabel('CLK (V)')
for j in range(4):
 label='CM %.3f, %s0.25 LSB'%([.45,.45,.675,.675][j],'+' if j%2==0 else '-')
 ref=(.0017578125 if j%2==0 else -.0017578125)
 axs[1].plot(t,(a['p'+str(j)]-a['n'+str(j)]-ref)*1e6,label=label)
 axs[2].plot(t,a['op'+str(j)],label='P out case%d'%j)
axs[1].set_ylim(-6,6);axs[1].set_ylabel('Differential kickback (uV)');axs[1].legend(ncol=2,fontsize=8);axs[2].set_ylabel('Output P (V)');axs[2].legend(ncol=2,fontsize=8);axs[2].set_xlabel('Time (ns)')
for ax in axs:ax.grid(alpha=.2);ax.set_xlim(9.5,14)
fig.suptitle('StrongArm: capacitive input and native receiving-gate load\nTT / 0.9 V / 27 C; 1.28 pF/side; original sizes; receiver DFF CMI warning remains',fontsize=11)
fig.savefig(out/'comparator_hold.png',dpi=170);plt.close(fig)
print('Wrote3 module figures')
