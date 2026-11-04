"""Native-point streaming SAR functional/timing/stress measurement, Python 2.7."""
from __future__ import print_function
import argparse,json,os,gzip,itertools,math
from reduce import frames,norm

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
 cfg=json.load(open(a.run_dir+'/inputs/measure.json'));state=json.load(open(a.run_dir+'/simulation.state.json'))
 if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native failed')
 files=[a.run_dir+'/raw/'+f for f in os.listdir(a.run_dir+'/raw') if f.endswith('.tran.tran')]
 if len(files)!=1:raise ValueError('one native transient required')
 names=[norm(s) for s in cfg['signals']];edges={};pairs={};device_pairs={};extrema={}
 for m in cfg['devices']:
  terms=[norm(n) for n in m['terminals']];dp={}
  for i,j in itertools.combinations(range(4),2):
   key='|'.join(sorted([terms[i],terms[j]]));dp['DGSB'[i]+'DGSB'[j]]=key
   if key not in pairs:pairs[key]=dict(nodes=key.split('|'),peak_V=0.,peak_t_s=0.,duration_gt_limit_s=0.,longest_interval_s=0.,active=None,previous=0.,interval_count=0)
  device_pairs[m['path']]=dp
 edge_names=set(['clks','cmpck','xdut.valid','xdut.clksn'])
 for d in cfg['dffs']:edge_names.update(norm(n) for k,n in d['ports'].items() if k not in ['VDD','VSS','VNW','VPW'])
 edge_names.discard('0');edge_names.discard('vdd')
 for path in cfg.get('delay_paths',[]):edge_names.update([norm(path['input']),norm(path['output'])])
 rawp=[norm('XDUT.'+n) for n in ['net14','net30','net29','net28','net27','net24','net33','net31']]
 rawn=[norm('XDUT.'+n) for n in ['net2','net13','net12','net10','net8','net23','net22','net20']]
 targets=sorted([(11.025e-9+i*100e-9,'reset',i) for i in range(17)]+[(89.975e-9+i*100e-9,'raw',i) for i in range(16)]+[(111.025e-9+i*100e-9,'output',i) for i in range(16)])
 samples=[];prev=None;n=0;last=-1;energy=0.;power_time=0.;lim=.99
 f=gzip.open(a.output_dir+'/wave.csv.gz','wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'))
 def word(v,ks):return sum(1<<i for i,k in enumerate(ks) if v[k]>.45)
 def rails(v,ks):return all(v[k]<=.09 or v[k]>=.81 for k in ks)
 for t,v in frames(files[0]):
  v['0']=0.;n+=1
  if n==1 and set(names)-set(v):raise ValueError('missing '+str(set(names)-set(v)))
  for k in names:
   q=v[k]
   if k not in extrema:extrema[k]=dict(min_V=q,max_V=q,min_t_s=t,max_t_s=t)
   e=extrema[k]
   if q<e['min_V']:e.update(min_V=q,min_t_s=t)
   if q>e['max_V']:e.update(max_V=q,max_t_s=t)
  for s in pairs.values():
   q=abs(v[s['nodes'][0]]-v[s['nodes'][1]])
   if q>s['peak_V']:s.update(peak_V=q,peak_t_s=t)
   if prev:
    old=s['previous'];dt=t-prev[0]
    if old>lim and q>lim:s['duration_gt_limit_s']+=dt
    elif (old>lim)!=(q>lim):
     cross=prev[0]+dt*(lim-old)/(q-old)
     if q>lim:s['active']=cross;s['interval_count']+=1;s['duration_gt_limit_s']+=t-cross
     else:
      s['duration_gt_limit_s']+=cross-prev[0]
      if s['active'] is not None:s['longest_interval_s']=max(s['longest_interval_s'],cross-s['active'])
      s['active']=None
   elif q>lim:s['active']=t;s['interval_count']+=1
   s['previous']=q
  if prev:
   for k in edge_names:
    old=prev[1][k];q=v[k]
    if old<.45<=q or old>.45>=q:edges.setdefault(k,[]).append([prev[0]+(t-prev[0])*(.45-old)/(q-old),int(q>old)])
   # Exclude startup; integrate 15 complete 100 ns cycles, all native intervals.
   lo=max(prev[0],110.025e-9);hi=min(t,1610.025e-9)
   if hi>lo:
    po=-prev[1]['vdd']*prev[1]['vvdd:1'];pn=-v['vdd']*v['vvdd:1'];dt=t-prev[0]
    pl=po+(pn-po)*(lo-prev[0])/dt;ph=po+(pn-po)*(hi-prev[0])/dt
    energy+=(pl+ph)*.5*(hi-lo);power_time+=hi-lo
   while targets and t>=targets[0][0]:
    at,kind,index=targets.pop(0);row=prev[1]
    keys=['xdut.clk_'+str(i) for i in range(8)] if kind=='reset' else rawp if kind=='raw' else ['do_'+str(i) for i in range(8)]
    samples.append(dict(time_s=at,kind=kind,frame=index,code=word(row,keys),rails=rails(row,keys),negative_raw=word(row,rawn) if kind=='raw' else None))
  # All points retained near first two resets/conversions, 100 ps elsewhere.
  u=t*1e9%100.;spacing=2e-12 if t<220e-9 and (9.95<u<11 or 49.9<u<90) else 100e-12
  if t-last>=spacing or abs(t-cfg['stop_s'])<1e-15:
   f.write((','.join(['%.12g'%t]+['%.12g'%v[k] for k in names])+'\n').encode('ascii'));last=t
  prev=(t,v)
 f.close()
 for s in pairs.values():
  if s['active'] is not None:s['longest_interval_s']=max(s['longest_interval_s'],t-s['active'])
  s.pop('active');s.pop('previous')
 def rises(k,lo,hi):return [x[0] for x in edges.get(k,[]) if x[1] and lo<x[0]<hi]
 frames_out=[]
 for i,c in enumerate(cfg['codes']):
  lo=49.975e-9+i*100e-9;hi=110.025e-9+i*100e-9
  ce=rises('cmpck',lo,hi);ve=rises('xdut.valid',lo,hi)
  shift=sorted((x,b) for b in range(8) for x in rises('xdut.clk_'+str(b),lo,hi))
  raw=next(s for s in samples if s['kind']=='raw' and s['frame']==i)
  out=next(s for s in samples if s['kind']=='output' and s['frame']==i)
  # Last raw transition or bit0 clock, no guessed propagation delay.
  changes=[x[0] for k in rawp for x in edges.get(k,[]) if lo<x[0]<hi]
  complete=max(changes+[shift[-1][0]]) if shift else None
  frames_out.append(dict(frame=i,expected=c,raw=raw['code'],negative_raw=raw['negative_raw'],output=out['code'],raw_rails=raw['rails'],output_rails=out['rails'],compare_count=len(ce),valid_count=len(ve),shift_order=[b for x,b in shift],completion_50pct_s=complete,completion_delay_s=complete-lo if complete else None))
 checks=dict(stop_complete=abs(t-cfg['stop_s'])<1e-14,
  codes_correct=all(x['output']==x['expected'] and x['raw']==x['expected'] and x['negative_raw']==255-x['expected'] for x in frames_out),
  eight_comparisons=all(x['compare_count']==8 and x['valid_count']==8 for x in frames_out),
  shift_order=all(x['shift_order']==list(range(7,-1,-1)) for x in frames_out),
  reset_within_1ns=all(x['code']==0 and x['rails'] for x in samples if x['kind']=='reset'),
  raw_within_40ns=all(x['raw']==x['expected'] and x['raw_rails'] and x['completion_delay_s'] is not None and x['completion_delay_s']<=40e-9 for x in frames_out),
  output_within_1ns=all(x['output']==x['expected'] and x['output_rails'] for x in frames_out),
  no_cmp_rise_during_stable_track=not any(11.025e-9+i*100e-9<x[0]<49.975e-9+i*100e-9 for x in edges.get('cmpck',[]) if x[1] for i in range(17)))
 stress_ok=all(s['peak_V']<=lim for s in pairs.values())
 delays=[]
 for path in cfg.get('delay_paths',[]):
  ie=[x for x in edges.get(norm(path['input']),[]) if 49e-9<x[0]<1600e-9]
  oe=edges.get(norm(path['output']),[]);errors=[]
  for at,di in ie:
   match=[x[0] for x in oe if x[1]==di and at<x[0]<at+path['td_s']+100e-12]
   if match:errors.append(min(match,key=lambda x:abs(x-at-path['td_s']))-at-path['td_s'])
  delays.append(dict(name=path['name'],target_s=path['td_s'],input_edges=len(ie),matched_edges=len(errors),max_abs_error_s=max([abs(x) for x in errors]) if errors else None))
 result=dict(functional_checks=checks,functional_ok=all(checks.values()),electrical_screen_ok=stress_ok,delay_checks=delays,
  power_W=energy/power_time,power_budget_ok=energy/power_time<=100e-6,power_window_s=[110.025e-9,1610.025e-9],
  energy_J=energy,frames=frames_out,samples=samples,edges=edges,extrema=extrema,terminal_pairs=pairs,device_pairs=device_pairs,
  coverage=dict(dff_ports=len(cfg['dffs']),internal_instances=cfg['representatives'],internal_mos=len(cfg['devices'])),
  native_points=n,native_state=state.get('native'),mode=cfg['mode'],scope=cfg['scope'],
  library_timing_constraints='unknown: setup/hold, recovery/removal and min-pulse limits not qualified',
  threshold_V=lim,metrics_use_all_native_points=True)
 json.dump(result,open(a.output_dir+'/result.json','w'),indent=2,sort_keys=True)
 if sum(os.path.getsize(a.output_dir+'/'+x) for x in os.listdir(a.output_dir))>28*1024**2:raise ValueError('bounded export exceeded')
 print('Analysis complete:',n,'points; functional',result['functional_ok'],'stress',stress_ok)
 # Circuit failures are evidence, not analyzer crashes.
if __name__=='__main__':main()
