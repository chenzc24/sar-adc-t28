"""Python2-compatible streaming native-point reducer for two DFFs."""
from __future__ import print_function
import argparse,gzip,itertools,json,os
from reduce import frames,norm

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--source-run-dir');p.add_argument('--output-dir',required=True);args=p.parse_args()
 src=args.source_run_dir or args.run_dir
 cfg=json.load(open(src+'/inputs/measure.json'));st=json.load(open(src+'/simulation.state.json'))
 assert st['status']=='complete' and st['exit_code']==0 and st['native']['zero_error_footer']
 paths=[src+'/raw/'+f for f in os.listdir(src+'/raw') if f.endswith('.tran.tran')];assert len(paths)==1
 names=[norm(x) for x in cfg['signals']];pairs={};mapping={}
 for d in cfg['devices']:
  ts=[norm(x) for x in d['terminals']];mp={}
  for i,j in itertools.combinations(range(4),2):
   key='|'.join([ts[i],ts[j]]);mp['DGSB'[i]+'DGSB'[j]]=key
   pairs[key]=dict(nodes=[ts[i],ts[j]])
  mapping[d['path']]=mp
 def initial():return dict(peak_V=-1,peak_t_s=None,peak_nodes_V=None,intervals_s=[],active=None,previous=None)
 stats={scope:{k:initial() for k in pairs} for scope in ['all','reset']}
 f=gzip.open(args.output_dir+'/wave.csv.gz','wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'))
 prev=None;n=0;energy=0.;reset_energy=0.;snaps={};targets=[.8e-9,4e-9,6e-9,7.5e-9,8.8e-9];last_reset=None
 for t,v in frames(paths[0]):
  v['0']=0.;n+=1
  assert not(set(names)-set(v))
  f.write((','.join(['%.16g'%t]+['%.16g'%v[k] for k in names])+'\n').encode('ascii'))
  for scope in ['all','reset']:
   if scope=='reset' and not cfg['window_s'][0]<=t<=cfg['window_s'][1]:continue
   if scope=='reset':last_reset=t
   for key,base in pairs.items():
    s=stats[scope][key];x,y=base['nodes'];val=abs(v[x]-v[y])
    if val>s['peak_V']:s.update(peak_V=val,peak_t_s=t,peak_nodes_V={x:v[x],y:v[y]})
    old=s['previous']
    if old is not None and (old[1]>.99)!=(val>.99):
     cross=old[0]+(t-old[0])*(.99-old[1])/(val-old[1])
     if val>.99:s['active']=cross
     elif s['active'] is not None:s['intervals_s'].append([s['active'],cross]);s['active']=None
    elif old is None and val>.99:s['active']=t
    s['previous']=[t,val]
  if prev:
   de=-(t-prev[0])*(v['vdd']*v['vvdd:1']+prev[1]['vdd']*prev[1]['vvdd:1'])/2
   energy+=de
   if cfg['window_s'][0]<=prev[0] and t<=cfg['window_s'][1]:reset_energy+=de
   while targets and t>=targets[0]:
    at=targets.pop(0);ratio=(at-prev[0])/(t-prev[0])
    snaps[str(at)]={k:prev[1][k]+ratio*(v[k]-prev[1][k]) for k in ['qa','qb','cdn','cp','da','db']}
  prev=(t,v)
 f.close();assert abs(t-cfg['stop_s'])<1e-15
 for scope in stats:
  for s in stats[scope].values():
   if s['active'] is not None:s['intervals_s'].append([s['active'],last_reset if scope=='reset' else t])
   s.pop('active');s.pop('previous')
   s['total_over_s']=sum(b-a for a,b in s['intervals_s']);s['longest_over_s']=max([b-a for a,b in s['intervals_s']]+[0.])
   s['peak_interval_s']=next(([a,b] for a,b in s['intervals_s'] if a<=s['peak_t_s']<=b),None)
 checks={}
 for at,expected in [(.8e-9,[0,0]),(4e-9,[1,1]),(6e-9,[0,0]),(7.5e-9,[0,0]),(8.8e-9,[1,0])]:
  v=snaps[str(at)];checks[str(at)]=all(v[k]>.81 if bit else v[k]<.09 for k,bit in zip(['qa','qb'],expected))
 result=dict(case=cfg['case'],factor=cfg['factor'],native_points=n,stop_s=t,native_state=st['native'],device_pairs=mapping,pair_nodes=pairs,terminal_stats=stats,function_samples=snaps,function_checks=checks,function_pass=all(checks.values()),supply_energy_J=energy,reset_supply_energy_J=reset_energy,threshold_V=.99,metrics_native_points=True,scope='TT two D1 cells, 5fF diagnostic load, ideal finite sources; no PVT or ADC qualification')
 json.dump(result,open(args.output_dir+'/result.json','w'),indent=2,sort_keys=True)
 assert sum(os.path.getsize(args.output_dir+'/'+x) for x in os.listdir(args.output_dir))<28*1024**2
 print('complete',n,'points; functional pass',result['function_pass'])
if __name__=='__main__':main()
