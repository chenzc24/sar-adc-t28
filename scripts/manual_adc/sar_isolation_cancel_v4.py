"""One-off stop of redundant v4 after native settings proved unchanged.
Managed worker owns final state. Verify run/PID/boot/start before SIGINT.
"""
import subprocess,base64,json
from pathlib import Path
code='''import os,json,signal
p='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/manual8-sar-a-tt-v4'
s=json.load(open(p+'/simulation.state.json'))
if s['status']!='running':
 print(json.dumps({'signal_sent':False,'state':s['status']}))
else:
 c=s['child_identity'];pid=c['pid']
 assert open('/proc/sys/kernel/random/boot_id').read().strip()==c['boot_id']
 fields=open('/proc/%d/stat'%pid).read().rsplit(')',1)[1].split()
 assert int(fields[19])==int(c['start_ticks'])
 cmd=open('/proc/%d/cmdline'%pid).read()
 assert p+'/inputs/test.scs' in cmd and 'spectre' in cmd
 os.kill(pid,signal.SIGINT)
 print(json.dumps({'signal_sent':True,'pid':pid,'reason':'native readback shows tran reltol did not change actual setting; avoid repeating v3 to same size limit'}))
'''
payload=base64.b64encode(code.encode()).decode()
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei',"python -c \"import base64;exec(base64.b64decode('"+payload+"'))\""],capture_output=True,text=True,timeout=20)
print(r.stdout,r.stderr);r.check_returncode()
out=Path(__file__).resolve().parents[2]/'verification/manual_adc/sar_isolation_v1/v4_stop_receipt.json'
out.write_text(r.stdout)
