"""Execute explicit user stop for exactly two registered current MC runs."""
import base64,json,subprocess,shlex
from pathlib import Path
R=Path(__file__).resolve().parents[2]
REMOTE=r'''
import os,json,signal,time
assert os.getuid()==596
root='/server_local_ssd/chenzc_intern25/sar-adc-t28';assert os.path.realpath(root)==root
rows=[]
def live(ident):
 try:
  p='/proc/'+str(ident['pid']);s=open(p+'/stat').read().split()
  return os.stat(p).st_uid==596 and s[21]==ident['start_ticks'] and s[2]!='Z'
 except IOError:return False
 except OSError:return False
for run in ['sar8mc-b-tt-s3102-v1','sar8mc-b-tt-s3103-v1']:
 d=root+'/runs/'+run;v=json.load(open(d+'/simulation.state.json'));reg=json.load(open(d+'/registered.json'))
 assert reg['recipe_hash']==EXPECTED[run]
 receipt={'run_id':run,'authorization':'User explicitly requested stopping two MC runs, keeping nominal and seed3101','epoch':time.time(),'before_status':v['status']}
 if v['status']=='running':
  child=v['child_identity'];assert live(child),'Process identity changed; do not signal'
  pid=child['pid'];cmd=open('/proc/'+str(pid)+'/cmdline','rb').read().split('\x00')
  assert any('spectre' in x for x in cmd) and d+'/inputs/test.scs' in cmd,cmd
  assert os.getpgid(pid)==child['pgid']==pid
  os.killpg(pid,signal.SIGTERM);receipt.update(signal='SIGTERM',child_identity=child)
  until=time.time()+10
  while live(child) and time.time()<until:time.sleep(.25)
  receipt['child_still_alive']=live(child)
 else:receipt['signal']='none_already_terminal'
 with open(d+'/user_stop_20261103.json','w') as f:json.dump(receipt,f,indent=2)
 rows.append(receipt)
print(json.dumps(rows))
'''
def main():
    m=json.loads((R/'verification/sar8_mc/server_manifest.json').read_text())
    source='EXPECTED='+repr(m['registered_hashes'])+'\n'+REMOTE
    code='import base64;exec(base64.b64decode('+repr(base64.b64encode(source.encode()).decode())+'))'
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],capture_output=True,text=True,timeout=35)
    (R/'output/sar8_mc/user_stop_stdout.txt').write_text(p.stdout);(R/'output/sar8_mc/user_stop_stderr.txt').write_text(p.stderr)
    p.check_returncode();rows=json.loads(p.stdout)
    (R/'verification/sar8_mc/user_stop.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
if __name__=='__main__':main()
