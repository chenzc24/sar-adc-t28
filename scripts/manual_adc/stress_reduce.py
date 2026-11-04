from __future__ import print_function
import argparse,json,os,gzip,itertools
from reduce import frames,norm

def phase(t):
 ns=t*1e9;u=ns%100
 if ns<10:return 'startup'
 if 10<=u<12:return 'sampling_reset'
 if 12<=u<49.975:return 'tracking'
 if 49.975<=u<54:return 'pre_compare'
 if 54<=u<60:return 'conversion'
 return 'hold'

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
 cfg=json.load(open(a.run_dir+'/inputs/measure.json'));state=json.load(open(a.run_dir+'/simulation.state.json'))
 if state['status']!='complete' or not state['native']['zero_error_footer']:raise ValueError('source incomplete')
 files=[a.run_dir+'/raw/'+x for x in os.listdir(a.run_dir+'/raw') if x.endswith('.tran.tran')]
 if len(files)!=1:raise ValueError('transient source')
 names=[norm(n) for n in cfg['signals']];pairs={};device_pairs={}
 for m in cfg['devices']:
  terms=[norm(x) for x in m['terminals']];keys={}
  for i,j in itertools.combinations(range(4),2):
   key='|'.join(sorted([terms[i],terms[j]]));keys['DGSB'[i]+'DGSB'[j]]=key
   if key not in pairs:pairs[key]={'nodes':sorted([terms[i],terms[j]]),'peak_V':0.,'peak_t_s':0.,'duration_gt_990_s':0.,'phase_max_V':{},'intervals_s':[],'active':None,'last_value':0.}
  device_pairs[m['path']]=keys
 prev=None;n=0;last=-1.;stats={};edges={};caps=[];targets=[111e-9]
 f=gzip.open(a.output_dir+'/wave.csv.gz','wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'))
 for t,v in frames(files[0]):
  v['0']=0.;n+=1
  if n==1 and set(names)-set(v):raise ValueError(str(set(names)-set(v)))
  ph=phase(t)
  for k,s in pairs.items():
   q=abs(v[s['nodes'][0]]-v[s['nodes'][1]])
   if q>s['peak_V']:s['peak_V']=q;s['peak_t_s']=t
   if q>s['phase_max_V'].get(ph,0):s['phase_max_V'][ph]=q
   if prev is not None:
    old=s['last_value'];dt=t-prev[0]
    if old>.99 and q>.99:s['duration_gt_990_s']+=dt
    elif (old>.99)!=(q>.99):
     crossing=prev[0]+dt*(.99-old)/(q-old)
     if q>.99:s['active']=crossing;s['duration_gt_990_s']+=t-crossing
     else:
      s['duration_gt_990_s']+=crossing-prev[0]
      if s['active'] is not None:s['intervals_s'].append([s['active'],crossing])
      s['active']=None
   elif q>.99:s['active']=t
   s['last_value']=q
  for key in names:
   q=v[key]
   if key not in stats:stats[key]={'min':q,'max':q,'min_t':t,'max_t':t}
   z=stats[key]
   if q<z['min']:z.update(min=q,min_t=t)
   if q>z['max']:z.update(max=q,max_t=t)
   if prev and key in ['clks','xadc.cmpck','xadc.xl.clksn','xadc.xl.valid']:
    old=prev[1][key]
    if (old<.45<=q) or (old>.45>=q):edges.setdefault(key,[]).append([prev[0]+(t-prev[0])*(.45-old)/(q-old),int(q>old)])
  while targets and t>=targets[0]:
   tt=targets.pop(0);row=prev[1] if prev and prev[0]<=tt<t else v;caps.append({'time_s':tt,'code':sum(1<<i for i in range(8) if row['do_'+str(i)]>.45)})
  ns=t*1e9;spacing=1e-12 if (9.95<=ns<=11 or 109.95<=ns<=111) else 20e-12
  if t-last>=spacing or abs(t-cfg['stop_s'])<1e-15:f.write((','.join(['%.12g'%t]+['%.12g'%v[x] for x in names])+'\n').encode('ascii'));last=t
  prev=(t,v)
 f.close()
 if abs(t-cfg['stop_s'])>1e-14:raise ValueError('stop')
 for s in pairs.values():
  if s['active'] is not None:s['intervals_s'].append([s['active'],t])
  s.pop('active');s.pop('last_value')
 result={'native_complete':True,'native_points':n,'stop_s':t,'native_state':state['native'],'terminal_pairs':pairs,'device_pairs':device_pairs,'extrema':stats,'edges':edges,'captures':caps,'coverage':{'MOS':len(cfg['devices']),'instances':len(cfg['instances']),'scope':'all DFCNQD1/DFQD1 plus INVD4/BUFFD4 in manual_sar; excludes other combinational cell internals and analog devices'},'metrics_use_all_native_points':True,'threshold_V':.99}
 json.dump(result,open(a.output_dir+'/result.json','w'),indent=2)
 if sum(os.path.getsize(a.output_dir+'/'+x) for x in os.listdir(a.output_dir))>28*1024**2:raise ValueError('derived size')
 print('Reduced',n,'native points;',len(pairs),'unique terminal pairs')
if __name__=='__main__':main()
