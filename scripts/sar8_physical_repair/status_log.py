"""Bounded read-only native log inspection; never starts simulation or analysis."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_stress_closure'))
import stream_control
stream_control.OUT=ROOT/'output/sar8_physical_repair'
run=sys.argv[1]
assert run.startswith('sar8fix-') and all(c.isalnum() or c=='-' for c in run)
code='''import os,json,re
p=PATH+'/spectre.out'
with open(p) as f:
 x=f.read(200000)
 f.seek(max(0,os.path.getsize(p)-4000));tail=f.read()
at=x.find('Output and IC/nodeset')
raw=PATH+'/raw/tran_perf.tran.tran';last=None
if os.path.isfile(raw):
 with open(raw,'rb') as f:
  f.seek(max(0,os.path.getsize(raw)-131072));times=re.findall(r'^"time" ([^\\n]+)',f.read(),re.M)
 if times:last=float(times[-1])*1e9
print(json.dumps(dict(size=os.path.getsize(p),save_summary=x[at:at+350],
 last_saved_ns=last,
 errors=[l for l in x.splitlines() if any(w in l for w in ['No outputs','Failed to find','ERROR (','SPECTRE-8003'])],
 measurements=[l for l in x.splitlines() if 'R4MEAS' in l],
 tail=[l for l in tail.splitlines() if any(w in l for w in ['tran:','R4MEAS','Total time','completes','Maximum resident','ERROR ('])])))
'''.replace('PATH',repr('/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/'+run))
print(stream_control.remote(code))
