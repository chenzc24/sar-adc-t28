"""Use already completed combo run: both node voltages, all seven LN currents."""
import csv,gzip,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from setup import W,ROOT,write
from review_edge_current import integral

source='cmpdesign-edge-b2i2-ff-hot-v1'
cfg=json.loads((W/'testbenches/cmpdesign-combo-latch-current-ff-hot-v2/measure.json').read_text())
rows=[[] for w in cfg['windows']]
with gzip.open(ROOT/'output/managed_execution/runs'/source/'collected/derived/wave.csv.gz','rt') as f:
    for row in csv.DictReader(f):
        for w,rs in zip(cfg['windows'],rows):
            if w['window_s'][0]<=float(row['time'])<=w['window_s'][1]:rs.append(row)
data=[{k:np.array([float(row[k]) for row in rs]) for k in rs[0]} for rs in rows]
ln=data[0];w=cfg['windows'][0];t=ln['time'];v=ln['xa4_held.ln'];i=v.argmax();l=i
while l>0 and v[l-1]>.99:l-=1
cross=t[l-1]+(t[l]-t[l-1])*(.99-v[l-1])/(v[l]-v[l-1]);peak=t[i]
bs=[]
for b in w['branches']:
    y=-ln[b['signal'].lower()]
    bs.append(dict(device=b['device'],terminal=b['terminal'],into_fC=integral(t,y,cross,peak)*1e15,peak_into_uA=float(y.max()*1e6)))
bs.sort(key=lambda b:b['into_fC'],reverse=True)
kcl=float(max(abs(sum(ln[b['signal'].lower()] for b in w['branches']))));assert kcl<1e-15
snap={k:dict(cross=float(np.interp(cross,t,ln[k])),peak=float(ln[k][i])) for k in ['ck','xa4_held.lp','xa4_held.ln','xa4_held.net1','xa4_held.net2','xa4_held.net3','pa4_held','na4_held']}
out=dict(source_run_id=source,branch_measurement_scope='LN all seven ports; LP voltages only, no LP current inference as measured',cross_s=float(cross),peak_s=float(peak),peak_V=float(v[i]),branches=bs,kcl_max_A=kcl,snapshots=snap,windows=[w['source_pulse'] for w in cfg['windows']])
write(W/'results/combo_latch_source_attribution.json',json.dumps(out,indent=2)+'\n')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(4,1,figsize=(11,11),layout='constrained');x=(t-w['fall50_s'])*1e12
for name,label in [('ck','CLK'),('xa4_held.lp','LP'),('xa4_held.net1','net1'),('xa4_held.net2','net2')]:ax[0].plot(x,ln[name],label=label)
ax[0].set_ylabel('LN event: recovery (V)');ax[0].legend(ncol=4)
for d,win in zip(data,cfg['windows']):
    target=win['target'].lower();xx=(d['time']-win['fall50_s'])*1e12
    ax[1].plot(xx,(d[target]-.99)*1e3,label='%s, fall50 %.3f ns'%(target.split('.')[-1].upper(),win['fall50_s']*1e9),ls='-' if target.endswith('ln') else '--')
ax[1].set_ylabel('LP/LN excess (mV)');ax[1].set_ylim(-1,5.2);ax[1].legend()
for b in bs:ax[2].plot(x,-ln['xa4_held.'+b['device'].lower()+':'+str('DGSB'.index(b['terminal'])+1)]*1e6,label=b['device']+'.'+b['terminal'])
ax[2].set_ylabel('Into LN (+) / out (-), uA');ax[2].legend(ncol=4);ax[2].set_xlabel('Time from respective falling 50% crossing (ps)')
for a in ax[:3]:
    a.set_xlim(-300,120);a.axvline(0,color='gray',ls=':');a.axvline((peak-w['fall50_s'])*1e12,color='#b34237',ls=':');a.axvspan((cross-w['fall50_s'])*1e12,(peak-w['fall50_s'])*1e12,color='#d3e0e9',alpha=.45);a.grid(alpha=.2)
ax[2].axhline(0,color='gray',lw=.7)
ax[3].bar([b['device']+'.'+b['terminal'] for b in bs],[b['into_fC'] for b in bs],color=['#bc7146' if b['into_fC']>0 else '#557f9e' for b in bs]);ax[3].axhline(0,color='gray',lw=.7);ax[3].set_ylabel('Charge into LN (fC)');ax[3].set_title('Only LN above-VDD phase: 355.337611 ns to 355.472714 ns');ax[3].grid(axis='y',alpha=.2)
fig.suptitle('Combined comparator | LP/LN reset overshoot and measured LN branch currents\nFF,0.99V,125C | M2/M4 x4; M3/M5 and M8/M9 x2 | rise/fall200/500ps\nIdeal sources; held1.28pF/side; output6.1fF/side; no real SAR/noise/mismatch/PEX\nTotal terminal currents include displacement. Shading: LN crossing VDD to peak.',fontsize=11)
fig.savefig(W/'figures/combo_latch_source.png',dpi=150);plt.close(fig)
print(json.dumps(out,indent=2))
