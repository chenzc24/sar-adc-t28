from __future__ import print_function
import argparse,os,json,gzip,hashlib
from reduce import frames
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--source-run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
src=a.source_run_dir;state=json.load(open(src+'/simulation.state.json'))
if state['status']!='complete' or not state['native']['zero_error_footer']:raise ValueError('source incomplete')
cfg=json.load(open(a.run_dir+'/inputs/zoom.json'));names=cfg['signals'];paths=[src+'/raw/'+s for s in os.listdir(src+'/raw') if s.endswith('.tran.tran')]
if len(paths)!=1:raise ValueError('one source')
f=gzip.open(a.output_dir+'/wave.csv.gz','wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'));n=0;out=0
for t,v in frames(paths[0]):
 n+=1
 if any(lo*1e-9<=t<=hi*1e-9 for lo,hi in cfg['windows_ns']):
  f.write((','.join(['%.15g'%t]+['%.15g'%v[k] for k in names])+'\n').encode('ascii'));out+=1
f.close()
if abs(t-120e-9)>1e-14:raise ValueError('stop')
json.dump({'native_points':n,'exported_points':out,'source_run':os.path.basename(src),'windows_ns':cfg['windows_ns'],'decimation':False,'native_end':True},open(a.output_dir+'/result.json','w'),indent=2)
print('Exported',out,'of',n)
