"""Bounded streaming PSF ASCII reducer, Python2.7/3. No simulation launch."""
from __future__ import print_function
import argparse,json,os,re,gzip,math,hashlib

def norm(s):return s.replace('\\','').lower()
def frames(path):
 section=None;aliases={};group=None;prop=False;t=None;values={};ended=False
 with open(path) as f:
  for line in f:
   l=line.strip()
   if l in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
    section=l
    if l=='END':
     if t is not None:yield t,values.copy()
     ended=True;break
    continue
   if section=='TRACE':
    if prop:
     if ')' in l:prop=False
     continue
    if not l.startswith('"'):continue
    _,key,tail=l.split('"',2);tail=tail.strip()
    prop='PROP(' in tail and ')' not in tail[tail.index('PROP('):]
    if tail.startswith('GROUP'):group=key;continue
    aliases[key]=norm(key)
    if group is not None:aliases[group]=norm(key);group=None
   if section!='VALUE' or not l.startswith('"'):continue
   _,key,tail=l.split('"',2)
   v=float(tail.strip())
   if math.isnan(v) or math.isinf(v):raise ValueError('nonfinite')
   if key=='time':
    if t is not None:
     if v<=t:raise ValueError('non increasing native time')
     yield t,values.copy()
    t=v
   else:
    if key not in aliases:raise ValueError('unknown trace '+key)
    values[aliases[key]]=v
 if not ended:raise ValueError('Missing native END')

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
 cfg=json.load(open(os.path.join(a.run_dir,'inputs','measure.json')))
 state=json.load(open(os.path.join(a.run_dir,'simulation.state.json')))
 if state['status']!='complete' or state['exit_code']!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native run incomplete')
 files=[os.path.join(a.run_dir,'raw',f) for f in os.listdir(os.path.join(a.run_dir,'raw')) if f.endswith('.tran.tran')]
 if len(files)!=1:raise ValueError('need exactly one native transient')
 names=[norm(n) for n in cfg['signals']];stats={};edges={};previous=None;energy=0.;n=0;captures=[];targets=[]
 if cfg['kind'].startswith('logic_codes'):
  targets=[(111e-9+i*100e-9,i) for i in range(256)]
 fout=gzip.open(os.path.join(a.output_dir,'wave.csv.gz'),'wb');fout.write(('time,'+','.join(names)+'\n').encode('ascii'))
 last_export=-1.;snapshots=[]
 for t,v in frames(files[0]):
  missing=set(names)-set(v)
  if missing:raise ValueError('missing '+str(missing))
  n+=1
  for key in names:
   val=v[key]
   if key not in stats:stats[key]={'min':val,'max':val,'min_t':t,'max_t':t}
   s=stats[key]
   if val<s['min']:s.update(min=val,min_t=t)
   if val>s['max']:s.update(max=val,max_t=t)
   if previous and ':' not in key:
    old=previous[1][key]
    if (old<.45<=val) or (old>.45>=val):
     te=previous[0]+(t-previous[0])*(.45-old)/(val-old)
     edges.setdefault(key,[]).append([te,1 if val>old else -1])
  if previous:
   dt=t-previous[0];energy+=dt*(-v['vdd']*v['vvdd:1']-previous[1]['vdd']*previous[1]['vvdd:1'])/2
   while targets and t>=targets[0][0]:
    at,expected=targets.pop(0)
    row=previous[1] if previous[0]<=at<t else v
    code=sum((1<<i) for i in range(8) if row['do_'+str(i)]>.45)
    captures.append(dict(time=at,expected=expected,actual=code))
  # export all short module native points, digital display downsample only; metrics above use all points.
  if not cfg['kind'].startswith('logic_codes') or t-last_export>=100e-12:
   fout.write((','.join(['%.12g'%t]+['%.12g'%v[k] for k in names])+'\n').encode('ascii'));last_export=t
  if cfg['kind'].startswith('sample') and any(previous and previous[0]<u<=t for u in [49e-9,51e-9,149e-9,151e-9]):snapshots.append(dict(time=t,values=v))
  previous=(t,v)
 fout.close()
 if abs(t-cfg['stop_s'])>1e-14:raise ValueError('unexpected stop')
 if sum(os.path.getsize(os.path.join(a.output_dir,f)) for f in os.listdir(a.output_dir))>28*1024**2:raise ValueError('derived budget')
 result=dict(native_complete=True,native_points=n,stop_s=t,extrema=stats,edges=edges,supply_energy_J=energy,supply_mean_W=energy/t,code_captures=captures,code_mismatches=[x for x in captures if x['expected']!=x['actual']],snapshots=snapshots,native_state=state.get('native'),scope=cfg['kind'],power_scope='Only VVDD, excludes reference/input/clock work; not total ADC',external_stimuli='ideal',noise=False,mismatch=False,PEX=False)
 json.dump(result,open(os.path.join(a.output_dir,'result.json'),'w'),indent=2,sort_keys=True)
 print('Native reduction complete',n,'not automatic circuit acceptance')
if __name__=='__main__':main()
