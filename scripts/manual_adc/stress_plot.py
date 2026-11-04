import gzip,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];OUT=R/'verification/manual_adc/stress_diagnosis';figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
p=R/'output/managed_execution/runs/manual8-stress-zoom-v1/collected/derived/wave.csv.gz'
keys=['time','clks','xadc.xl.clksn','xadc.xl.valid','xadc.cmpck','xadc.xl.net28']
keys+=['xadc.xl.i12.'+n for n in ['qf','qf_x','mq','mq_x','net176','net184','net093','clkb','clkbb']]
keys+=['xadc.xl.i12.'+m+':'+str(i) for m,i in [('mm4',1),('mm3',1),('msltn1',1),('msltp1',1),('mm76',2),('mm77',2),('mm64',3),('mm65',1),('mm65',2)]]
keys+=['xadc.xl.i46_3.'+n for n in ['mq','mq_x','net0118','clkb','clkbb']]
with gzip.open(p,'rt') as f:
 h=f.readline().strip().split(',');a=np.loadtxt(f,delimiter=',',usecols=[h.index(k) for k in keys])
d=dict(zip(keys,a.T));t=d['time']*1e9
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.constrained_layout.use':True})
def base(title,lo,hi,n=4):
 fig,axs=plt.subplots(n,1,figsize=(10.8,8.7),sharex=True);ix=(t>=lo)&(t<=hi);tt=(t[ix]-lo)*1000
 fig.suptitle(title+'\nTT / 0.9 V / 27 C; unchanged manual ADC + RC timing; ideal external sources; native samples and terminal metrics',fontsize=11)
 for ax in axs:ax.grid(alpha=.2);ax.set_xlim(0,(hi-lo)*1000)
 axs[-1].set_xlabel('Time relative to %.3f ns (ps)'%lo)
 return fig,axs,ix,tt
def line(ax,tt,ix,key,label,scale=1):ax.plot(tt,d[key][ix]*scale,label=label)
def done(fig,axs,name):
 for ax in axs:ax.legend(loc='best',ncol=2,fontsize=8)
 fig.savefig(figdir/name,dpi=170);plt.close(fig)
pfx='xadc.xl.i12.'
fig,ax,ix,x=base('A. Shift-register I12: reset drives qf above VDD',110.02,110.085)
for k,label in [('clks','Sample CLKS'),('xadc.xl.clksn','Clear CDN, active low'),('xadc.xl.valid','Shift clock VALID')]:line(ax[0],x,ix,k,label)
ax[0].set_ylabel('Control (V)')
for k,label in [('qf','qf'),('qf_x','qf_x'),('net093','MM3 source net093')]:line(ax[1],x,ix,pfx+k,label)
ax[1].axhline(.9,color='grey',ls='--',label='VDD = 0.9 V');ax[1].axhline(.99,color='red',ls=':',label='0.99 V screen');ax[1].set_ylabel('Internal node (V)')
ax[2].plot(x,np.abs(d[pfx+'qf'][ix]),label='MM76 |VGB| = |qf|');ax[2].plot(x,np.abs(d[pfx+'clkbb'][ix]-d[pfx+'net093'][ix]),label='MM3 |VGS|');ax[2].axhline(.99,color='red',ls=':',label='0.99 V limit');ax[2].set_ylabel('Terminal stress (V)')
ax[3].plot(x,-(d[pfx+'mm76:2']+d[pfx+'mm77:2'])[ix]*1e6,label='Into qf from MM76/MM77 gates');ax[3].plot(x,(d[pfx+'mm4:1']+d[pfx+'mm3:1']+d[pfx+'msltn1:1']+d[pfx+'msltp1:1'])[ix]*1e6,label='From qf into drain branches');ax[3].set_ylabel('Terminal current (uA)')
done(fig,ax,'reset_qf.png')
fig,ax,ix,x=base('B. Shift-register I12: floating NMOS stack during reset',110.10,110.65)
for k,label in [('mq','MM65 gate mq'),('mq_x','MM64 drain mq_x')]:line(ax[0],x,ix,pfx+k,label)
line(ax[0],x,ix,'xadc.xl.clksn','MM66 gate CDN');ax[0].set_ylabel('Control / drain (V)')
for k,label in [('net176','MM64 source net176'),('net184','MM66 drain net184')]:line(ax[1],x,ix,pfx+k,label)
ax[1].axhline(0,color='grey',ls='--');ax[1].set_ylabel('Stack node (V)')
ax[2].plot(x,np.abs(d[pfx+'mq_x'][ix]-d[pfx+'net176'][ix]),label='MM64 |VDS| (simultaneous terminals)');ax[2].axhline(.99,color='red',ls=':',label='0.99 V limit');ax[2].set_ylabel('Terminal stress (V)')
line(ax[3],x,ix,pfx+'mm65:2','MM65 total gate current',1e6);line(ax[3],x,ix,pfx+'mm65:1','MM65 drain current',1e6);line(ax[3],x,ix,pfx+'mm64:3','MM64 source current',1e6);ax[3].set_ylabel('Terminal current (uA)')
done(fig,ax,'reset_net176.png')
fig,ax,ix,x=base('C. Output-register I46_3: data changes while the master is transparent',56.62,57.05)
for k,label in [('clks','Output DFF clock CLKS'),('xadc.xl.net28','Output DFF data D = bit3 Q')]:line(ax[0],x,ix,k,label)
ax[0].set_ylabel('Port (V)');pfx='xadc.xl.i46_3.'
for k,label in [('mq','PMOS MM60 gate mq'),('clkb','PMOS MM79 gate clkb')]:line(ax[1],x,ix,pfx+k,label)
ax[1].set_ylabel('Gate (V)')
for k,label in [('net0118','MM79 source net0118'),('mq_x','MM79 drain mq_x')]:line(ax[2],x,ix,pfx+k,label)
ax[2].axhline(.9,color='grey',ls='--',label='VDD');ax[2].set_ylabel('Internal node (V)')
ax[3].plot(x,np.abs(d[pfx+'net0118'][ix]-d[pfx+'mq_x'][ix]),label='MM79 |VDS|');ax[3].axhline(.99,color='red',ls=':',label='0.99 V limit');ax[3].set_ylabel('Terminal stress (V)')
done(fig,ax,'conversion_output_ff.png')
print('Wrote three native-evidence figures')
