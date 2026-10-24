"""Memory-mapped full-resolution comparisons; no all-signal JSON materialization."""
import gc,json,re,sys
import numpy as np
from stream_control import ROOT,OUT,VERIFY,read,dump,sha,NAMES
LSB=1.8/256;BAND=.25*LSB

def load(name):
 folder=OUT/name/'stream_v1';meta=read(folder/'wave.meta.json');receipt=read(folder/'receipt.json')
 for fn in ['wave.stress.tsv','wave.extrema.tsv','wave.meta.json','spectre.out','logStatus','wave.columns']:
  assert sha(folder/fn)==receipt['files'][fn]['sha256']
 cols=(folder/'wave.columns').read_text().splitlines()
 assert len(cols)==meta['columns'] and (folder/'wave.bin').stat().st_size==meta['points']*meta['columns']*8
 m=np.memmap(folder/'wave.bin',mode='r',dtype='<f8',shape=(meta['points'],meta['columns']))
 w={n:m[:,i] for i,n in enumerate(cols)};t=w['time']*1e9
 assert np.all(np.diff(t)>0) and abs(t[-1]-200)<1e-6 and meta['PSF_END']
 return folder,meta,receipt,m,w,t

def edges(t,v,up=True,level=.495):
 ids=np.flatnonzero((v[:-1]<level)&(v[1:]>=level) if up else (v[:-1]>level)&(v[1:]<=level))
 return t[ids]+(level-v[ids])*(t[ids+1]-t[ids])/(v[ids+1]-v[ids])

def sustained(t,error,start,end):
 """Last crossing into band, staying inside through a stated finite deadline."""
 ids=np.flatnonzero((t>start)&(t<end))
 ts=np.r_[start,t[ids],end];es=np.r_[np.interp(start,t,error),error[ids],np.interp(end,t,error)]
 bad=np.flatnonzero(es>BAND)
 if len(bad) and bad[-1]==len(ts)-1:settled=None
 elif len(bad):
  k=bad[-1];settled=float(ts[k]+(es[k]-BAND)/(es[k]-es[k+1])*(ts[k+1]-ts[k]))
 else:settled=float(start)
 return dict(start_ns=float(start),deadline_ns=float(end),band_mv=BAND*1000,
  settle_at_ns=settled,settle_after_start_ns=None if settled is None else settled-start,
  residual_at_deadline_mv=float(es[-1])*1000,settled_by_deadline=settled is not None)

def bottom_errors(t,w,start,end):
 ids=np.flatnonzero((t>=start-.01)&(t<=end+.01));ts=t[ids]
 nominal=np.zeros(len(ids));local=np.zeros(len(ids));states={};illegal=[]
 for s in ['p','n']:
  for bit in range(8):
   gn='xdut.g'+s+'n'+str(bit);gp='xdut.g'+s+'p'+str(bit);bot='xdut.xcdac.b'+s+str(bit)
   n_on=np.interp(end,t,w[gn])>.495;p_on=np.interp(end,t,w[gp])<.495
   if n_on==p_on:illegal.append(bot)
   target=.9 if p_on else 0.;rail='vrefp' if p_on else 'vrefn';states[bot]=target
   np.maximum(nominal,np.abs(w[bot][ids]-target),out=nominal)
   np.maximum(local,np.abs(w[bot][ids]-w[rail][ids]),out=local)
 assert not illegal,illegal
 return ts,nominal,local,states

def pulse_at_peak(t,y,level,negative=False):
 """Contiguous pulse at the largest excursion; explicit diagnostic level."""
 v=-y if negative else y;threshold=-level if negative else level
 peak=int(np.argmax(v));assert v[peak]>threshold
 left=peak;right=peak
 while left>0 and v[left-1]>threshold:left-=1
 while right+1<len(t) and v[right+1]>threshold:right+=1
 start=float(t[left]);end=float(t[right])
 if left>0:start=float(t[left-1]+(threshold-v[left-1])/(v[left]-v[left-1])*(t[left]-t[left-1]))
 if right+1<len(t):end=float(t[right]+(v[right]-threshold)/(v[right]-v[right+1])*(t[right+1]-t[right]))
 return dict(level_v=level,start_ns=start,end_ns=end,width_ps=(end-start)*1000,
  peak_ns=float(t[peak]),peak_v=float(y[peak]),truncated=bool(left==0 or right==len(t)-1))

def analyze(name):
 folder,meta,receipt,m,w,t=load(name);ctx=read(OUT/name/'context.json')
 log=(folder/'spectre.out').read_text();native=(folder/'logStatus').read_text()
 assert 'spectre completes with 0 errors' in log and re.search(r'tran_perf\s+PASS',native)
 mapping=read(OUT/'stream_v1_tools/mapping.json')
 pp=np.loadtxt(folder/'wave.stress.tsv');assert len(pp)==len(mapping['pairs'])==3437
 assert np.array_equal(pp[:,0],np.arange(len(pp)))
 stress=[];crosschecks=0
 for rec in mapping['records']:
  r=dict(rec);_,peak,tm=pp[r['pair_index']];r.update(peak_v=float(peak),time_ns=float(tm*1e9),exceed=bool(peak>r['limit_v']));stress.append(r)
  if r['group']=='reference':
   a,b=r['nodes'];va=0. if a=='0' else w[a];vb=0. if b=='0' else w[b]
   assert abs(float(np.max(np.abs(va-vb)))-peak)<1e-12;crosschecks+=1
 groups={g:max([r for r in stress if r['group']==g],key=lambda r:r['peak_v']/r['limit_v']) for g in sorted({r['group'] for r in stress})}
 extrema={}
 for line in (folder/'wave.extrema.tsv').read_text().splitlines():
  n,*vs=line.split('\t');extrema[n]=list(map(float,vs))
 missing=[n for n in ctx['saved_signals'] if n not in extrema]
 assert all(':' in n for n in missing),'Required voltage missing'
 clocknames=['xdut.cmp_clk','xdut.xctrl.phi_w','xdut.phi_u','xdut.xref.cap_clk']
 ev={n:dict(rise=edges(t,w[n]),fall=edges(t,w[n],False)) for n in clocknames+['xdut.seq_sample','xdut.sample_int']+[f'xdut.xref.rst{b}' for b in range(8)]}
 rows=[[float(v) for v in r.split(',')] for r in re.findall(r'R4MEAS,([^\r\n]+)',log)]
 assert [int(r[0]) for r in rows]==[0,1]
 diff=w['xdut.topp']-w['xdut.topn'];frames=[];settling=[];reset_settling=[]
 for row in rows:
  i=int(row[0]);lo=i*100;hi=lo+100;target=ctx['input_diff_v'][i]
  cmp=ev['xdut.cmp_clk']['rise'];cmp=cmp[(cmp>lo)&(cmp<hi)]
  upd=ev['xdut.phi_u']['rise'];upd=upd[(upd>lo)&(upd<hi)]
  close=ev['xdut.seq_sample']['fall'];close=close[(close>lo)&(close<hi)][0]
  start=ev['xdut.seq_sample']['rise'];start=start[(start>=lo)&(start<hi)];start=float(start[0]) if len(start) else lo
  counts=[int(np.sum((ev[n]['rise']>=lo)&(ev[n]['rise']<hi))) for n in clocknames]
  code=int(sum((np.interp(hi-2,t,w[f'd{b}'])>.495)*(1<<b) for b in range(8)))
  ideal=int(np.clip(np.floor((target+.9)/LSB),0,255));assert code==int(row[1])
  held=float(np.interp(lo+41.8,t,diff));assert abs(held-row[11])<1e-9
  acquisition=sustained(t,np.abs(diff-target),start,close-.2)
  rst=[ev[f'xdut.xref.rst{b}']['rise'] for b in range(8)];rst=[x[(x>lo+41)&(x<hi)] for x in rst]
  assert all(len(x)==1 for x in rst)
  ordered=bool(np.all(np.diff([x[0] for x in reversed(rst)])>0))
  cap=ev['xdut.xref.cap_clk']['fall'];cap=cap[(cap>lo+41)&(cap<hi)]
  rm=(t>=rst[7][0])&(t<hi-.05)
  stable=all(np.all((w[f'd{b}'][rm]>.495)==bool(code&(1<<b))) for b in range(8))
  refword=int(sum((np.interp(start,t,w[f'xdut.xref.q{b}'])>.495)*(1<<b) for b in range(8)))
  fm=(t>=lo)&(t<hi);overlap=int(sum(np.sum((w[f'xdut.xref.h{b}'][fm]>.495)&(w[f'xdut.xref.l{b}'][fm]>.495)) for b in range(8)))
  frames.append(dict(frame=i,code=code,ideal_code=ideal,code_pass=code==ideal,monitor_valid=bool(row[7]),counts=counts,
   sample_start_ns=start,sample_close_ns=float(close),sample_window_ns=float(close-start),acquisition=acquisition,
   sample_signal='xdut.seq_sample',sample_start_is_initialization=bool(i==0 and start==0),
   preclose_error_mv=float(np.interp(close-.2,t,diff)-target)*1000,
   held_error_mv=(held-target)*1000,held_time_ns=lo+41.8,held_before_first_compare=bool(lo+41.8<cmp[0]),
   conversion_ns=row[-1]*1e9,first_compare_ns=float(cmp[0]),
   reset_order_pass=ordered,reset_after_capture=bool(len(cap) and rst[7][0]>cap[-1]),held_code_stable=stable,
   acquisition_reference_word=refword,HL_overlap_samples=overlap,
   top_delta_last100ps_before_compare_mv=[float(np.interp(x-.01,t,diff)-np.interp(x-.11,t,diff))*1000 for x in cmp]))
  for j,u in enumerate(upd):
   later=cmp[cmp>u]
   if not len(later):continue
   deadline=float(later[0]-.01)
   ts,nom,local,states=bottom_errors(t,w,u,deadline)
   settling.append(dict(frame=i,update=j,start_ns=float(u),next_compare_ns=float(later[0]),
    nominal=sustained(ts,nom,u,deadline),local_rail=sustained(ts,local,u,deadline)))
  resetstart=float(rst[0][0]);ts,nom,local,states=bottom_errors(t,w,resetstart,hi-.1)
  reset_settling.append(dict(frame=i,after_last_reset=sustained(ts,nom,resetstart,hi-.1)))
 gatecols=[f'xdut.g{s}{p}{b}' for s in ['p','n'] for p in ['p','n'] for b in range(8)]
 gatehi=max((float(np.max(w[g]-w['vdd!']))*1000,g) for g in gatecols)
 gatelo=min((float(np.min(w[g]))*1000,g) for g in gatecols)
 bottoms=[f'xdut.xcdac.b{s}{b}' for s in ['p','n'] for b in range(8)]
 bottommin=min((extrema[b][0]*1000,b,extrema[b][1]*1e9) for b in bottoms)
 def preceding_event(at):
  candidates=[]
  for key in ['xdut.phi_u']+[f'xdut.xref.rst{b}' for b in range(8)]:
   earlier=ev[key]['rise'][ev[key]['rise']<=at]
   if len(earlier):candidates.append((float(earlier[-1]),key))
  return dict(zip(['time_ns','signal'],max(candidates)))
 reference_event=preceding_event(groups['reference']['time_ns'])
 bottom_event=preceding_event(bottommin[2])
 settings={k:(re.findall(r'(?m)^\s*'+re.escape(k)+r' = (.+)$',log) or [None])[-1] for k in ['maxstep','reltol','abstol(V)','abstol(I)','method','temp']}
 accepted=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',log)[1]);assert abs(accepted-meta['points'])<=1
 result=dict(name=name,corner='ff',temperature_c=ctx['temperature_c'],vdd=ctx['vdd'],gate_resistor_parallel_factor=ctx['rg_parallel_factor'],
  native_pass=True,points=meta['points'],accepted_tran_steps=accepted,source=receipt['source'],effective_settings=settings,
  groups=groups,stress_pair_count=len(stress),failing_pairs=sum(x['exceed'] for x in stress),
  failing_MOS=len({x['instance'] for x in stress if x['exceed']}),reference_crosschecks=crosschecks,
  CMI=bool(re.search(r'WARNING \(CMI-',log)),native_suppressed_warnings=int((re.findall(r'(\d+) warnings suppressed',log) or ['0'])[-1]),
  frames=frames,all_codes_pass=all(f['code_pass'] for f in frames),
  sample_edges_ns={n:{k:v.tolist() for k,v in ev[n].items()} for n in ['xdut.seq_sample','xdut.sample_int']},
  all_timing_pass=all(f['monitor_valid'] and f['counts']==[8,8,8,16] and f['conversion_ns']<60 for f in frames),
  all_idle_pass=all(f['reset_order_pass'] and f['reset_after_capture'] and f['held_code_stable'] and f['acquisition_reference_word']==128 and f['HL_overlap_samples']==0 for f in frames),
  settling=settling,reset_settling=reset_settling,bottom_min=bottommin,gate_high_excursion_mv=gatehi,gate_low_excursion_mv=gatelo,
  reference_peak_preceding_event=reference_event,bottom_min_preceding_event=bottom_event,
  bottom_pulse_below_minus1mv=pulse_at_peak(t,w[bottommin[1]],-.001,negative=True),
  bottom_min_snapshot={n:float(np.interp(bottommin[2],t,w[n])) for n in ['vrefp','vrefn','vdd!',bottommin[1],
   'xdut.g'+bottommin[1][-2]+'n'+bottommin[1][-1],'xdut.g'+bottommin[1][-2]+'p'+bottommin[1][-1]]},
  high_gate_pulse_above_vdd_plus1mv=pulse_at_peak(t,w[gatehi[1]],.991),
  missing_requested_current_signals=missing,native_trace_count=meta['traces'],
  reducer_peak_rss_kib=receipt['peak_child_rss_kib'],binary_bytes=meta['points']*meta['columns']*8,
  compressed_bytes=receipt['files']['wave.bin.gz']['bytes'],
  settling_definition='All16 bottom nodes within +/-0.25LSB of endpoint-selected nominal or instantaneous reference, sustained until next compare minus10ps. Conservative node-level diagnostic, not weighted ADC INL.',
  qualification='Two static frames,200ns. Not full PVT,FFT,mismatch or SOA signoff; missing MOS currents prevent branch-current attribution')
 dump(VERIFY/(name+'_stream_analysis.json'),result)
 dump(OUT/name/'stream_v1/stress_all.json',stress)
 print(name,'codes',[f['code'] for f in frames],'ref_peak',groups['reference']['peak_v'],'bottom',bottommin,
  'nominal_settled',sum(e['nominal']['settled_by_deadline'] for e in settling),'/',len(settling),flush=True)
 del w;del m;gc.collect()
 return result

def plot(corner):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
 colors=['#2864a0','#d35c32'];packs=[]
 for k,factor in enumerate([1,4]):
  name=f'rg{factor}_strict200_ff_{corner}';r=read(VERIFY/(name+'_stream_analysis.json'))
  _,_,_,m,w,t=load(name);event=next(x for x in r['settling'] if x['frame']==1 and x['update']==0)
  start=event['start_ns'];end=event['next_compare_ns']-.01
  mask=(t>=start-.25)&(t<=event['next_compare_ns']+.1)
  pack=dict(t=t[mask]-start,bp=w['xdut.xcdac.bp7'][mask].copy(),gn=w['xdut.gpn7'][mask].copy(),gp=w['xdut.gpp7'][mask].copy(),
   ref=w['vrefp'][mask].copy(),event=event,r=r)
  ts,nom,local,_=bottom_errors(t,w,start,end);pack.update(et=ts-start,err=nom*1000)
  packs.append(pack);del w;del m;gc.collect()
 for k,p in enumerate(packs):
  label='Baseline' if k==0 else 'Rgate / 4';style='-' if k==0 else '--';color=colors[k]
  axs[0].plot(p['t'],p['bp'],style,color=color,label=label,lw=1.7)
  axs[1].plot(p['t'],p['gn'],style,color=color,label=label+' GN',lw=1.5)
  axs[1].plot(p['t'],p['gp'],style,color=color,alpha=.6,label=label+' GP',lw=1.5)
  axs[2].semilogy(p['et'],np.maximum(p['err'],.001),style,color=color,label=label,lw=1.7)
  deadline=p['event']['next_compare_ns']-p['event']['start_ns']
  axs[2].axvline(deadline,color='#777777',ls=':',lw=1,label='Next comparison' if k==0 else None)
 axs[0].axhline(.9,color='#777777',ls=':',label='Nominal VREFP = 0.9 V')
 axs[0].axhline(0,color='#777777',ls=':',lw=.8)
 axs[0].set_ylabel('BP7 (V)');axs[0].set_ylim(-.08,1.02)
 axs[1].set_ylabel('Switch gates (V)');axs[1].set_ylim(-.05,1.1)
 axs[2].axhline(BAND*1000,color='#3a8c58',ls=':',label='0.25 LSB = 1.758 mV')
 axs[2].set_ylabel('Max bottom error (mV)');axs[2].set_xlabel('Time from first MSB update in frame 1 (ns)')
 for ax in axs:
  ax.axvline(0,color='#999999',lw=.8);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best',ncol=2)
 temp='-40' if corner=='m40' else '+125'
 fig.suptitle(f'FF / 0.99 V / {temp} C | Vin,d = -0.81 V | Native T28, Mmain 2 um, ref L 90 nm\nOnly gate-series resistance changes; ideal external supplies/sample clock, physical SAR timing',fontsize=10)
 dest=ROOT/'docs/figures/sar8_stress_closure';dest.mkdir(parents=True,exist_ok=True)
 fig.savefig(dest/(corner+'_handoff.png'),dpi=180);plt.close(fig)
 # Explicitly compare actual sampling edges, not just source-deck identity.
 a,b=[p['r'] for p in packs]
 compare=dict(corner=corner,baseline=a['name'],enhanced=b['name'],
  sample_close_delta_ps=[(y['sample_close_ns']-x['sample_close_ns'])*1000 for x,y in zip(a['frames'],b['frames'])],
  sample_window_delta_ps=[(y['sample_window_ns']-x['sample_window_ns'])*1000 for x,y in zip(a['frames'],b['frames'])])
 dump(VERIFY/(corner+'_stream_comparison.json'),compare)

def plot_stress(corner):
 """Show both gate-rail overshoot and bottom undershoot without hiding spikes."""
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 base=read(VERIFY/(f'rg1_strict200_ff_{corner}_stream_analysis.json'))
 candidate=read(VERIFY/(f'rg4_strict200_ff_{corner}_stream_analysis.json'))
 gate=base['groups']['reference'];bot=base['bottom_min']
 # These cases' worst reference pair is gate-to-body; fail instead of relabeling.
 assert gate['terminal']=='gb' and gate['nodes'][0]=='0'
 center=[gate['time_ns'],bot[2]];nodes=[gate['nodes'][1],bot[1]]
 extra=candidate['bottom_min'][1]!=bot[1]
 if extra:center.append(candidate['bottom_min'][2]);nodes.append(candidate['bottom_min'][1])
 fig,axs=plt.subplots(len(nodes),1,figsize=(10,3*len(nodes)),layout='constrained')
 colors=['#2864a0','#d35c32']
 for k,factor in enumerate([1,4]):
  name=f'rg{factor}_strict200_ff_{corner}'
  _,_,_,m,w,t=load(name)
  for j,ax in enumerate(axs):
   mask=(t>=center[j]-.18)&(t<=center[j]+.22)
   y=w[nodes[j]][mask]*1000
   extremum=float(np.max(y) if j==0 else np.min(y))
   label=('Baseline' if k==0 else 'Rgate / 4')+f': {extremum:.2f} mV'
   ax.plot(t[mask],y,'-' if k==0 else '--',color=colors[k],label=label,lw=1.7)
   if extra and j==2 and k==1:
    ax.plot(t[mask],w['vrefn'][mask]*1000,':',color='#3a8c58',label='Rgate / 4: actual VREFN',lw=1.4)
  del w;del m;gc.collect()
 axs[0].axhline(990,color='#aa3333',ls=':',label='Core screen: 990 mV')
 axs[1].axhline(0,color='#aa3333',ls=':',label='PMOS |Vbd| screen: bottom >= 0')
 axs[0].set_ylabel('Gate-to-body voltage (mV)')
 axs[1].set_ylabel('Bottom voltage (mV)')
 axs[1].set_ylim(-90,15)
 axs[1].set_xlim(center[1]-.18,center[1]+.06)
 axs[0].set_title(gate['instance']+' | after '+base['reference_peak_preceding_event']['signal'],fontsize=10)
 axs[1].set_title(bot[1]+' | after '+base['bottom_min_preceding_event']['signal'],fontsize=10)
 if extra:
  axs[2].axhline(0,color='#aa3333',ls=':',lw=1)
  axs[2].set_ylabel('Bottom / reference (mV)');axs[2].set_ylim(-100,50)
  axs[2].set_xlim(center[2]-.18,center[2]+.1)
  axs[2].set_title(nodes[2]+' | new worst case after '+candidate['bottom_min_preceding_event']['signal'],fontsize=10)
 for ax in axs:
  ax.set_xlabel('Absolute time (ns)');ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best')
 temp='-40' if corner=='m40' else '+125'
 fig.suptitle(f'FF / 0.99 V / {temp} C | 200 ns, Vin,d = +/-0.81 V | Native T28\nPhysical SAR timing; ideal external supplies/sample clock; only Rgate changes',fontsize=10)
 dest=ROOT/'docs/figures/sar8_stress_closure';dest.mkdir(parents=True,exist_ok=True)
 fig.savefig(dest/(corner+'_stress.png'),dpi=180);plt.close(fig)

if __name__=='__main__':
 if sys.argv[1]=='plot':plot(sys.argv[2]);plot_stress(sys.argv[2])
 else:
  for name in sys.argv[1:]:analyze(name)
