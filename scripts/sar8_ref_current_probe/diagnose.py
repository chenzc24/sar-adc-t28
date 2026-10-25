"""Baseline-only event metrics; currents are positive into component terminals."""
import json,re,sys
import numpy as np
from analyze import load,checks
from probe import ROOT,OUT,VERIFY,read,dump,sha
from stream_analyze import bottom_errors,sustained

def crossing(t,y,lo=0.,level=.495):
 ids=np.flatnonzero((y[:-1]<level)&(y[1:]>=level)&(t[:-1]>=lo))
 return [float(t[i]+(level-y[i])/(y[i+1]-y[i])*(t[i+1]-t[i])) for i in ids]

def summarize_event(t,w,lo,hi,peak_signal,minimum=False):
 ids=np.flatnonzero((t>=lo)&(t<=hi));y=w[peak_signal][ids]
 k=ids[np.argmin(y) if minimum else np.argmax(y)]
 at={n:float(w[n][k]) for n in w if n!='time'}
 charge={n:float(np.trapezoid(w[n][ids],t[ids]*1e-9))*1e15 for n in w if ':' in n}
 peak={n:dict(min_a=float(np.min(w[n][ids])),max_a=float(np.max(w[n][ids]))) for n in w if ':' in n}
 before=ids[ids<=k];slope=np.gradient(w[peak_signal][before],t[before])
 sk=before[np.argmin(slope) if minimum else np.argmax(slope)]
 phase={}
 for label,ix in [('before_voltage_peak',before),('after_voltage_peak',ids[ids>=k])]:
  phase[label]=dict(window_ns=[float(t[ix[0]]),float(t[ix[-1]])],charge_fc={
   n:float(np.trapezoid(w[n][ix],t[ix]*1e-9))*1e15 for n in w if ':' in n})
 return dict(window_ns=[lo,hi],peak_time_ns=float(t[k]),peak_signal=peak_signal,
  peak_voltage_v=float(w[peak_signal][k]),at_peak=at,signed_charge_fc=charge,current_extrema=peak,
  steepest_before_peak=dict(time_ns=float(t[sk]),slope_v_per_ns=float(slope[np.where(before==sk)[0][0]]),
   values={n:float(w[n][sk]) for n in w if n!='time'}),phase_charges=phase)

def baseline_check(name,w,t):
 source=read(OUT/name/'manifest.json')['source']
 d=ROOT/'output/sar8_stress_closure'/source/'stream_v1';meta=read(d/'wave.meta.json')
 cols=(d/'wave.columns').read_text().splitlines()
 old=np.memmap(d/'wave.bin',mode='r',dtype='<f8',shape=(meta['points'],meta['columns']))
 ot=old[:,0]*1e9;diffs={};same_time=len(ot)==len(t) and np.array_equal(ot,t)
 for i,col in enumerate(cols):
  if col=='time' or col not in w:continue
  yi=old[:,i] if same_time else np.interp(t,ot,old[:,i])
  diffs[col]=float(np.max(np.abs(w[col]-yi)))
 return dict(source=source,old_points=len(ot),new_points=len(t),identical_time_grid=same_time,
  maximum_interpolated_difference_v=max(diffs.values()),voltage_differences_v=diffs)

def analyze(name):
 d,m,w,t=load(name);assert abs(t[-1]-200)<1e-6
 kcl=checks(w);baseline=baseline_check(name,w,t)
 rst=crossing(t,w['xdut.xref.rst7'],lo=140)[0];update=crossing(t,w['xdut.phi_u'],lo=140)[0]
 events=dict(gate=summarize_event(t,w,rst-.05,rst+1.1,'xdut.gnn4'),
  bottom=summarize_event(t,w,update-.05,update+1.1,'xdut.xcdac.bp7',True),
  idle_bottom=summarize_event(t,w,rst-.05,rst+1.1,'xdut.xcdac.bp3',True))
 gn=crossing(t,-w['xdut.gpn7'],lo=update,level=-.99*.98)[0]
 gp=crossing(t,-w['xdut.gpp7'],lo=update,level=-.99*.98)[0]
 b=events['bottom'];b['gate_fall_98percent_ns']={'GN':gn,'GP':gp}
 b['bp7_at_gp_fall_v']=float(np.interp(gp,t,w['xdut.xcdac.bp7']))
 b['stage_charge_into_bp7_fc']={}
 for stage,start,end in [('GN_fall_to_GP_fall',gn,gp),('GP_fall_to_bottom_min',gp,b['peak_time_ns'])]:
  ix=np.flatnonzero((t>start)&(t<end));ts=np.r_[start,t[ix],end]
  b['stage_charge_into_bp7_fc'][stage]={n:float(np.trapezoid(-np.r_[np.interp(start,t,w[n]),w[n][ix],np.interp(end,t,w[n])],ts*1e-9))*1e15
   for n in ['xdut.xcdac.xsp7.mn_low:1','xdut.xcdac.xsp7.mp_high:1','xdut.xcdac.cmomp7:2']}
 codes=[sum((np.interp(tm,t,w['d'+str(b)])>.495)*2**b for b in range(8)) for tm in [98,198]]
 monitor=re.findall(r'R4MEAS,[^\r\n]+',(d/'spectre.out').read_text());assert len(monitor)==2
 settings={};log=(d/'spectre.out').read_text()
 for key in ['reltol','maxstep','abstol(V)','abstol(I)','method','temp']:
  match=re.findall(r'^\s*'+re.escape(key)+r' = (.+)$',log,re.M);settings[key]=match[-1] if match else None
 rails={}
 for rail,dev,side in [('n','mn_low','n'),('p','mp_high','p')]:
  branch=sum(w['xdut.xcdac.xs%s%d.%s:3'%(s,b,dev)] for s in ['p','n'] for b in range(8))
  residual=branch+w['xdut.xcdac.cmom%s8:2'%side]+w['cref'+rail+':1']+w['rref'+rail+':2']
  rails[rail]=dict(max_kcl_residual_a=float(np.max(np.abs(residual))),max_switch_sum_a=float(np.max(np.abs(branch))))
 counts=[];settling=[]
 for frame in range(2):
  lo,hi=frame*100,(frame+1)*100
  enames=['xdut.cmp_clk','xdut.xctrl.phi_w','xdut.phi_u','xdut.xref.cap_clk']
  ev={n:np.array([e for e in crossing(t,w[n]) if lo<e<hi]) for n in enames}
  counts.append([len(ev[n]) for n in enames])
  for u in ev['xdut.phi_u']:
   later=ev['xdut.cmp_clk'][ev['xdut.cmp_clk']>u]
   if not len(later):continue
   deadline=later[0]-.01;ts,nom,local,_=bottom_errors(t,w,u,deadline)
   settling.append(sustained(ts,nom,u,deadline))
 source=read(OUT/name/'manifest.json')['source']
 previous=read(ROOT/'verification/sar8_stress_closure'/(source+'_stream_analysis.json'))
 logold=(ROOT/'output/sar8_stress_closure'/source/'stream_v1/spectre.out').read_text()
 inventory=lambda text:re.search(r'Circuit inventory:(.*?)Analysis and control statement inventory:',text,re.S)[1].strip()
 same_inventory=inventory(log)==inventory(logold)
 result=dict(name=name,native_pass=True,settings=settings,simulator_version=re.search(r'^Version (.+)$',log,re.M)[1],codes=[int(c) for c in codes],monitor=monitor,
  sample_close_ns=crossing(t,-w['xdut.seq_sample'],level=-.495),kcl=kcl,rail_kcl=rails,
  baseline_comparison=baseline,events=events,raw_bytes=read(d/'receipt.json')['raw_bytes'],
  native_resource=read(d/'finished.json'),counts=counts,settling=settling,same_circuit_inventory=same_inventory,
  original_peak_reference_v=previous['groups']['reference']['peak_v'],original_bottom_min_mv=previous['bottom_min'][0])
 result['sample_close_delta_ps']=[(a-b['sample_close_ns'])*1000 for a,b in zip(result['sample_close_ns'],previous['frames'])]
 assert same_inventory and result['codes']==[243,12] and counts==[[8,8,8,16],[8,8,8,16]]
 assert all(x['residual_a']<max(1e-9,.001*x['peak_branch_a']) for x in kcl.values()),'KCL validation failed'
 dump(VERIFY/(name+'_analysis.json'),result)
 print(json.dumps(dict(name=name,codes=result['codes'],baseline=baseline['maximum_interpolated_difference_v'],
  kcl_worst=max(x['residual_a'] for x in kcl.values()),rail_kcl=rails,
  events={k:dict(time_ns=e['peak_time_ns'],voltage_v=e['peak_voltage_v']) for k,e in events.items()}),indent=2))
 return result

def plot(name):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2})
 d,m,w,t=load(name);r=read(VERIFY/(name+'_analysis.json'))
 folder=ROOT/'docs/figures/sar8_ref_current_probe';folder.mkdir(parents=True,exist_ok=True)
 temp='-40' if name.endswith('cold') else '+125';colors=['#176b9b','#d94b40','#269c84','#9c65aa']
 def curve(ax,node,label,ids,scale=1,color=None,ls='-'):
  ax.plot(t[ids],w[node][ids]*scale,label=label,color=color,ls=ls,lw=1.55)
 for kind in ['gate','bottom','idle_bottom']:
  e=r['events'][kind];lo,hi=e['window_ns'];mark=e['peak_time_ns']
  if kind=='bottom':lo=e['gate_fall_98percent_ns']['GN']-.025;hi=mark+.015
  ids=np.flatnonzero((t>=lo)&(t<=hi))
  fig,axs=plt.subplots(5,1,figsize=(11,11),sharex=True,layout='constrained')
  titles=dict(gate='GNN4 gate overshoot during bit7 reset',bottom='BP7 undershoot during MSB reference update',idle_bottom='BP3 disturbance during bit7 reset')
  fig.suptitle(titles[kind]+'\n'+
   'T28 | FF '+temp+' C | VDD 0.99 V | original Rgate | Mmain 2 um | ref L 90 nm',fontsize=13)
  if kind=='gate':
   curve(axs[0],'xdut.xref.rst7','RST7',ids,color=colors[0]);curve(axs[0],'xdut.xref.rst4','RST4',ids,color=colors[1])
   for n,l,c in [('xdut.xcdac.bn7','BN7',colors[0]),('xdut.topn','TOPN',colors[1]),('xdut.xcdac.bn4','BN4',colors[2])]:curve(axs[1],n,l,ids,color=c)
   for n,l,c in [('xdut.gnn4','GNN4 at switch',colors[1]),('xdut.xref.xdrv4.gnndrv','GNNDRV before Rgate',colors[0])]:curve(axs[2],n,l,ids,color=c)
   axs[2].axhline(.99,color='#777',ls='--',lw=1,label='VDD = 0.99 V')
   axs[3].plot(t[ids],-w['xdut.xcdac.xsn4.mn_low:2'][ids]*1e6,label='out of MN_LOW gate',color=colors[1])
   curve(axs[3],'xdut.xref.xdrv4.rgnn1_5__dmy0:2','gate -> Rgate',ids,1e6,colors[0],'--')
   curve(axs[3],'xdut.xref.xdrv4.rgnn0:1','driver -> Rgate',ids,1e6,colors[2])
   curve(axs[4],'vrefn','VREFN',ids,1000,colors[0]);curve(axs[4],'xdut.xref.xdrv4.gnnb','driver input GNNB',ids,1000,colors[1])
   ys=['Reset (V)','CDAC (V)','Gate (V)','Current (uA)','Voltage (mV)']
  elif kind=='bottom':
   curve(axs[0],'xdut.gpn7','GPN7 low-side gate',ids,color=colors[0]);curve(axs[0],'xdut.gpp7','GPP7 high-side gate',ids,color=colors[1])
   curve(axs[1],'xdut.xcdac.bp7','BP7',ids,1000,colors[1]);curve(axs[1],'vrefn','VREFN',ids,1000,colors[0]);axs[1].axhline(0,color='#777',ls='--',lw=1,label='Nominal low reference: 0 V')
   axs[1].set_ylim(-90,80)
   for n,l,c in [('xdut.xcdac.xsp7.mn_low:1','low NMOS -> BP7',colors[0]),('xdut.xcdac.xsp7.mp_high:1','high PMOS -> BP7',colors[1]),('xdut.xcdac.cmomp7:2','CDAC -> BP7',colors[2])]:curve(axs[2],n,l,ids,-1e6,c)
   for p,l,c in [('1','into high PMOS drain',colors[0]),('2','into high PMOS gate',colors[1]),('3','into high PMOS source',colors[2]),('4','into high PMOS bulk',colors[3])]:curve(axs[3],'xdut.xcdac.xsp7.mp_high:'+p,l,ids,1e6,c)
   for n,l,c in [('xdut.xcdac.xsp7.mn_low:1','low NMOS -> BP7',colors[0]),('xdut.xcdac.xsp7.mp_high:1','high PMOS -> BP7',colors[1]),('xdut.xcdac.cmomp7:2','CDAC -> BP7',colors[2])]:
    v=-w[n][ids];q=np.r_[0,np.cumsum(.5*(v[:-1]+v[1:])*np.diff(t[ids])*1e-9)]*1e15
    axs[4].plot(t[ids],q,label=l,color=c,lw=1.55)
   ys=['Gate (V)','Undershoot (mV)','Into BP7 (uA)','PMOS terminal (uA)','Integrated inflow (fC)']
  else:
   curve(axs[0],'xdut.xref.rst7','RST7',ids,color=colors[0]);curve(axs[0],'xdut.xref.rst3','RST3',ids,color=colors[1])
   curve(axs[1],'xdut.xcdac.bp3','BP3',ids,1000,colors[1]);curve(axs[1],'vrefn','VREFN',ids,1000,colors[0]);axs[1].axhline(0,color='#777',ls='--',lw=1,label='Nominal low reference: 0 V')
   for n,l,c in [('xdut.xcdac.xsp3.mn_low:1','low NMOS -> BP3',colors[0]),('xdut.xcdac.xsp3.mp_high:1','high PMOS -> BP3',colors[1]),('xdut.xcdac.cmomp3:2','CDAC -> BP3',colors[2])]:curve(axs[2],n,l,ids,-1e6,c)
   curve(axs[3],'xdut.gpn3','GPN3 low-side gate',ids,color=colors[0]);curve(axs[3],'xdut.gpp3','GPP3 high-side gate',ids,color=colors[1])
   curve(axs[4],'xdut.topp','TOPP',ids,color=colors[1]);curve(axs[4],'xdut.xcdac.bp7','BP7 resetting',ids,color=colors[0]);curve(axs[4],'vrefp','VREFP',ids,color=colors[2])
   ys=['Reset (V)','Voltage (mV)','Into BP3 (uA)','Gate (V)','Voltage (V)']
  for ax,y in zip(axs,ys):
   ax.axvline(mark,color='#777',ls=':',lw=1)
   if kind=='bottom':
    ax.axvline(e['gate_fall_98percent_ns']['GP'],color='#bbb',ls='--',lw=.8)
    ax.axvspan(lo,e['gate_fall_98percent_ns']['GP'],color=colors[0],alpha=.035)
    ax.axvspan(e['gate_fall_98percent_ns']['GP'],hi,color=colors[1],alpha=.035)
   else:ax.axvline(lo+.05,color='#bbb',ls='--',lw=.8)
   ax.set_ylabel(y);ax.legend(loc='best',fontsize=8,ncol=2);ax.set_xlim(lo,hi);ax.ticklabel_format(axis='x',useOffset=False)
  axs[2 if kind=='gate' else 1].annotate('%.2f mV @ %.4f ns'%(e['peak_voltage_v']*1000,mark),
   xy=(mark,e['peak_voltage_v']*(1 if kind=='gate' else 1000)),xytext=((.2,.15) if kind=='bottom' else (.55,.88)),textcoords='axes fraction',arrowprops={'arrowstyle':'->','color':'#555'},fontsize=9)
  axs[-1].set_xlabel('Time (ns)');fig.savefig(folder/(name+'_'+kind+'.png'),dpi=170);plt.close(fig)

if __name__=='__main__':
 if sys.argv[1]=='analyze':analyze(sys.argv[2])
 elif sys.argv[1]=='plot':plot(sys.argv[2])
