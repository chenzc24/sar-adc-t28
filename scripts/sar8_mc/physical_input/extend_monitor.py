"""Reload only our identified read-only collector for the expanded run manifest."""
import base64,json,shlex,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input'
REMOTE=r'''
import os,json,signal,time,subprocess,resource
p=json.load(__import__('sys').stdin);c=p['monitor'];dest=p['path'];pid=c['pid'];proc='/proc/'+str(pid)
if os.path.exists(proc):
 assert open(proc+'/stat').read().split()[21]==str(c['start_ticks'])
 assert int(next(l for l in open(proc+'/status') if l.startswith('Uid:')).split()[1])==596
 cmd=open(proc+'/cmdline','rb').read().replace('\0',' ');assert c['db'] in cmd and 'simcheck' in cmd and 'watch' in cmd
 os.kill(pid,signal.SIGINT)
 for i in range(25):
  if not os.path.exists(proc) or open(proc+'/stat').read().split()[2]=='Z':break
  time.sleep(.2)
 else:raise RuntimeError('Own collector has not retired; do not start duplicate')
target=dest+'/monitor_manifest_extended2.json';assert not os.path.exists(target)
with open(target,'w') as f:json.dump({'runs':p['runs']},f,indent=2)
def setup():os.setsid();os.nice(10);resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
with open('/dev/null','rb') as null,open(dest+'/monitor_extended.log','ab') as log:
 q=subprocess.Popen([c['python'],'-m','simcheck','--db',c['db'],'watch',target,'--interval','5'],cwd=c['cwd'],stdin=null,stdout=log,stderr=log,preexec_fn=setup,close_fds=True)
c.update(pid=q.pid,start_ticks=open('/proc/'+str(q.pid)+'/stat').read().split()[21],previous_pid=pid,manifest=target)
with open(dest+'/monitor_extended2_launch.json','w') as f:json.dump(c,f,indent=2)
print(json.dumps(c))
'''
def main():
    launch=json.loads((V/'launch.json').read_text());launch['monitor']=json.loads((V/'monitor_extended_launch.json').read_text());server=json.loads((V/'server_manifest.json').read_text());runs=server['initial_runs']+server['paired_runs']
    for kind in ['controls','width4','width2','accuracy']:runs+=json.loads((V/('followup_'+kind+'_manifest.json')).read_text())['runs']
    rows=[];root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs'
    for run in runs:
        ctx=json.loads((R/'management/recipes'/(run+'.yaml')).read_text())['test_conditions'];rand=ctx['seed'] is not None;name='mc_phys_tran' if rand else 'phys_tran'
        rows.append({'id':run,'log':root+'/'+run+'/spectre.out','state':root+'/'+run+'/simulation.state.json','log_status':root+'/'+run+'/raw/logStatus','analysis':'phys_tran',
          'raw':root+'/'+run+'/raw/'+('mc_separate/mc-001/' if rand else '')+name+'.tran.tran','expected_stop_s':ctx['stop_s']})
    code='import base64;exec(base64.b64decode('+repr(base64.b64encode(REMOTE.encode()).decode())+'))'
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],input=json.dumps({'monitor':launch['monitor'],'path':launch['path'],'runs':rows}),text=True,capture_output=True,timeout=25);assert p.returncode==0,p.stderr
    (V/'monitor_extended2_launch.json').write_text(p.stdout);print(p.stdout)
if __name__=='__main__':main()
