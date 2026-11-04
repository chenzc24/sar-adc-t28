"""Bind the existing collector to exact native child names/raw paths. No sim controls."""
import base64,json,shlex,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
REMOTE=r'''
import os,json,signal,time,subprocess
p='/server_local_ssd/chenzc_intern25/sar-adc-t28/campaigns/sar8-mc-20261103/modules';root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/'
m=json.load(open(p+'/manifest.json'));old=json.load(open(p+'/monitor_launch.json'));pid=old['pid'];proc='/proc/'+str(pid)
assert os.getuid()==596 and os.stat(proc).st_uid==596
assert open(proc+'/stat').read().split()[21]==old['start_ticks']
cmd=open(proc+'/cmdline','rb').read();assert 'simcheck' in cmd and old['db'] in cmd and 'watch' in cmd
rows=[]
for x in m['runs'].values():
 run=x['run_id'];d=root+run;name='cap_ac' if x['family']=='cdac' else 'comp_tran'
 raw=d+'/raw/'+(name+'.ac' if x['family']=='cdac' else name+'.tran.tran')
 if x['seed'] is not None:raw=d+'/raw/mc_separate/mc-001/mc_'+name+('.ac' if x['family']=='cdac' else '.tran.tran')
 row={'id':run,'log':d+'/spectre.out','state':d+'/simulation.state.json','log_status':d+'/raw/logStatus','analysis':name,'raw':raw}
 if x['family']=='comp':row['expected_stop_s']=109e-9
 rows.append(row)
with open(p+'/monitor_manifest_v2.json','w') as f:json.dump({'runs':rows},f,indent=2)
os.kill(pid,signal.SIGTERM)
for i in range(30):
 try:
  s=open(proc+'/stat').read().split()
  if s[21]!=old['start_ticks'] or s[2]=='Z':break
 except IOError:break
 time.sleep(.1)
else:raise RuntimeError('Old collector did not exit; do not duplicate')
def setup():os.setsid();os.nice(10)
with open('/dev/null','rb') as null,open(p+'/monitor_v2.log','ab') as log:
 c=subprocess.Popen([old['python'],'-m','simcheck','--db',old['db'],'watch',p+'/monitor_manifest_v2.json','--interval','5'],cwd=old['cwd'],stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
new=dict(old,pid=c.pid,start_ticks=open('/proc/'+str(c.pid)+'/stat').read().split()[21],manifest=p+'/monitor_manifest_v2.json')
with open(p+'/monitor_launch_v2.json','w') as f:json.dump(new,f,indent=2)
print(json.dumps(new))
'''
def main():
    code='import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))'
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],capture_output=True,text=True,timeout=25);p.check_returncode();r=json.loads(p.stdout)
    (R/'verification/sar8_mc/blocks/monitor_launch_v2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
