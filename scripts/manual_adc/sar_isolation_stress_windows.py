"""Analysis-only of first 220 ns of a completed native run. Python 2.7."""
from __future__ import print_function
import argparse,json,os,gzip,itertools
from reduce import frames,norm
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--source-run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
 src=a.source_run_dir;cfg=json.load(open(src+'/inputs/measure.json'));st=json.load(open(src+'/simulation.state.json'))
 assert st['status']=='complete' and st['native']['zero_error_footer']
 paths=[src+'/raw/'+f for f in os.listdir(src+'/raw') if f.endswith('.tran.tran')];assert len(paths)==1
 names=[norm(s) for s in cfg['signals']];pairs={};devs={}
 for d in cfg['devices']:
  ts=[norm(x) for x in d['terminals']];dp={}
  for i,j in itertools.combinations(range(4),2):
   key='|'.join(sorted([ts[i],ts[j]]));dp['DGSB'[i]+'DGSB'[j]]=key
   if key not in pairs:pairs[key]=dict(nodes=key.split('|'),peak_V=0.,peak_t_s=0.,peak_nodes_V={},active=None,previous=0.,intervals_s=[])
  devs[d['path']]=dict(terminals=ts,pairs=dp)
 windows=[(9.9e-9,11e-9),(49.9e-9,90e-9),(109.9e-9,111e-9),(149.9e-9,190e-9),(209.9e-9,211e-9)]
 f=gzip.open(a.output_dir+'/wave.csv.gz','wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'))
 previous=None;n=0;last=-1.;extrema={};events=[];end=220e-9
 for t,v in frames(paths[0]):
  if t>end:break
  v['0']=0.;n+=1
  if n==1:assert not(set(names)-set(v))
  alert=False
  for s in pairs.values():
   val=abs(v[s['nodes'][0]]-v[s['nodes'][1]])
   if val>s['peak_V']:s.update(peak_V=val,peak_t_s=t,peak_nodes_V={k:v[k] for k in s['nodes']})
   if val>.985:alert=True
   if previous:
    old=s['previous']
    if (old>.99)!=(val>.99):
     c=previous[0]+(t-previous[0])*(.99-old)/(val-old)
     if val>.99:s['active']=c
     else:
      if s['active'] is not None:s['intervals_s'].append([s['active'],c])
      s['active']=None
   elif val>.99:s['active']=t
   s['previous']=val
  for k in names:
   if ':' in k:continue
   if k not in extrema:extrema[k]=dict(min_V=v[k],max_V=v[k],min_t_s=t,max_t_s=t)
   e=extrema[k]
   if v[k]<e['min_V']:e.update(min_V=v[k],min_t_s=t)
   if v[k]>e['max_V']:e.update(max_V=v[k],max_t_s=t)
  if previous:
   for k in ['clks','xdut.clksn','cmpck','xdut.valid','dcmpp','dcmpn','xdut.clk_0','xdut.clk_7','xdut.net28','do_3']:
    old=previous[1][k];val=v[k]
    if old<.45<=val or old>.45>=val:events.append(dict(node=k,time_s=previous[0]+(t-previous[0])*(.45-old)/(val-old),direction=1 if val>old else -1))
  spacing=.5e-12 if alert else 5e-12
  if any(lo<=t<=hi for lo,hi in windows) and t-last>=spacing:
   f.write((','.join(['%.14g'%t]+['%.12g'%v[k] for k in names])+'\n').encode('ascii'));last=t
  previous=(t,v)
 f.close();last_t=previous[0]
 for s in pairs.values():
  if s['active'] is not None:s['intervals_s'].append([s['active'],last_t])
  s.pop('active');s.pop('previous');s['total_over_s']=sum(y-x for x,y in s['intervals_s']);s['longest_over_s']=max([y-x for x,y in s['intervals_s']]+[0.])
 result=dict(source_run='manual8-sar-a-tt-v6',source_native=st['native'],scope_s=[0,last_t],native_points=n,device_map=devs,terminal_pairs=pairs,extrema=extrema,events=events,
  scope='10 representative DFFs / 248 MOS, first 220 ns only; no new simulation; no branch-current attribution',display_windows_s=windows,metrics_use_all_native_points=True,limit_V=.99)
 json.dump(result,open(a.output_dir+'/result.json','w'),indent=2,sort_keys=True)
 assert sum(os.path.getsize(a.output_dir+'/'+x) for x in os.listdir(a.output_dir))<28*1024**2
 print('Processed',n,'native points through',last_t,'seconds')
if __name__=='__main__':main()
