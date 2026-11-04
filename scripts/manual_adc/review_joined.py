import sys,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from review_results import load,ROOT,at
run=sys.argv[1] if len(sys.argv)>1 else 'manual8-joined-dc-reduce-v2'
d,r=load(run);t=d['time'];result={'run':run,'warnings':r['native_state']['warning_codes'],'frames':[]}
expected=[142,28,227,130]
for j in range(4):
 close=(49.975+100*j)*1e-9;read=(111+100*j)*1e-9
 edges={k:[e[0]*1e9 for e in r['edges'].get(k,[]) if e[1]==1 and close<e[0]<close+60e-9] for k in ['xadc.cmpck']+['xadc.xl.clk_'+str(i) for i in range(7,-1,-1)]}
 result['frames'].append({'frame':j,'expected':expected[j],'actual':sum((1<<i) for i in range(8) if at(d,'do_'+str(i),read)>.45),'rising_edges_ns':edges,'sample_diff_V':at(d,'xadc.topp',close+1e-9)-at(d,'xadc.topn',close+1e-9),'input_diff_V':at(d,'vinp',close)-at(d,'vinn',close),'held_CM_V':(at(d,'xadc.topp',close+1e-9)+at(d,'xadc.topn',close+1e-9))/2})
result['mean_source_power_W']=r.get('all_source_mean_W',{})
result['native_code_captures']=r['code_captures']
result['native_code_mismatches']=r['code_mismatches']
result['display_integrated_power_W']={}
for v,i in [('vdd','vvdd:1'),('ref','vref:1'),('clks','vclk:1'),('vinp','vinp:1'),('vinn','vinn:1')]:
 result['display_integrated_power_W'][v]=float(np.trapezoid(-d[v]*d[i],t)/(t[-1]-t[0]))
result['functional_codes_match']=all(x['actual']==x['expected'] for x in result['frames'])
(ROOT/'verification/manual_adc/results'/f'{run}.json').write_text(json.dumps(result,indent=2)+'\n')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.constrained_layout.use':True})
fig,axs=plt.subplots(5,1,figsize=(11,10),sharex=True)
axs[0].plot(t*1e9,d['vinp']-d['vinn'],label='Input differential');axs[0].plot(t*1e9,d['xadc.topp']-d['xadc.topn'],label='CDAC differential');axs[0].set_ylabel('Differential (V)');axs[0].legend(ncol=2)
axs[1].plot(t*1e9,(d['xadc.topp']+d['xadc.topn'])/2,label='Top plate CM');axs[1].axhline(.45,ls='--',color='grey',label='Input CM');axs[1].set_ylabel('Common mode (V)');axs[1].legend(ncol=2)
axs[2].plot(t*1e9,d['clks']);axs[2].set_ylabel('Sample (V)')
axs[3].plot(t*1e9,d['xadc.cmpck']);axs[3].set_ylabel('Compare (V)')
code=sum((d['do_'+str(i)]>.45).astype(int)*(1<<i) for i in range(8));axs[4].step(t*1e9,code,where='post',label='Output code')
axs[4].plot([111+100*j for j in range(4)],expected,'o',mfc='none',label='Expected code');axs[4].legend(ncol=2);axs[4].set_ylabel('Code');axs[4].set_xlabel('Time (ns)')
for ax in axs:
 ax.set_xlim(0,420);ax.grid(alpha=.2)
 for j in range(4):ax.axvspan(10+100*j,49.975+100*j,color='grey',alpha=.08)
fig.suptitle('Manual SAR8 joined diagnostic: 10 MS/s\nTT / 0.9 V / 27 C; IO Bootstrap 4 um; native SAR + comparator + CDAC; ideal external sources; RC timing',fontsize=11)
fig.savefig(ROOT/'verification/manual_adc/figures'/f'{run}.png',dpi=150)
plt.close(fig)
mask=(t>=48e-9)&(t<=61e-9);tz=t[mask]*1e9
fig,zz=plt.subplots(4,1,figsize=(11,8),sharex=True)
zz[0].plot(tz,(d['vinp']-d['vinn'])[mask],label='Input differential');zz[0].plot(tz,(d['xadc.topp']-d['xadc.topn'])[mask],label='CDAC differential');zz[0].set_ylabel('Differential (V)');zz[0].legend(ncol=2)
zz[1].plot(tz,((d['xadc.topp']+d['xadc.topn'])/2)[mask],label='Top plate CM');zz[1].axhline(.45,ls='--',color='grey',label='Input CM');zz[1].set_ylabel('Common mode (V)');zz[1].legend(ncol=2)
zz[2].plot(tz,d['clks'][mask]);zz[2].set_ylabel('Sample (V)')
zz[3].plot(tz,d['xadc.cmpck'][mask]);zz[3].set_ylabel('Compare (V)');zz[3].set_xlabel('Time (ns)')
for ax in zz:
 ax.set_xlim(48,61);ax.grid(alpha=.2);ax.axvspan(48,49.975,color='grey',alpha=.08)
fig.suptitle('Manual SAR8: eight comparisons after sampling closes\nTT / 0.9 V / 27 C; input differential=0.1 V; transistor blocks + RC timing; ideal external sources',fontsize=11)
fig.savefig(ROOT/'verification/manual_adc/figures'/'joined_conversion_zoom.png',dpi=150)
print(json.dumps(result,indent=2))
