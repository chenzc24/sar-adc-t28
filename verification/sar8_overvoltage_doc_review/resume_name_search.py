"""Resume bounded read-only filename discovery without abandoning the queue."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'output/sar8_overvoltage_doc_review/persistent_namewalk.json'

REMOTE = r'''
import os,json,re,time
state=INITIAL_STATE
queue=state['queue'];out=[];errors=[];skipped=[];count=0;files=0;t=time.time()
rx=re.compile(r'reliab|qualif|qr[-_ ]*0(?:95|02|03|74|87)|aging|ageing|mosra|relxpert|tddb|nbti|pbti|soac|safe.?operat',re.I)
skip=set(['memory','sram','layout','schematic','symbol','.git','.cache','psf','simulation','ahdlsimdb','__pycache__'])
while queue and time.time()-t<22:
 d=queue.pop()
 try: names=os.listdir(d)
 except OSError as e:errors.append({'path':d,'error':str(e)});continue
 count+=1
 for n in names:
  p=os.path.join(d,n)
  if rx.search(n):out.append({'path':p,'is_link':os.path.islink(p)})
  if os.path.islink(p):continue
  if os.path.isdir(p):
   if n.lower() in skip or n.startswith('.'):
    skipped.append(p)
   else:queue.append(p)
  else:files+=1
print(json.dumps({'queue':queue,'matches':out,'errors':errors,'skipped':skipped,'directories':count,'files':files,'elapsed_s':time.time()-t}))
'''


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {
        'queue': ['/home/process/tsmc28n'], 'matches': [], 'errors': [],
        'skipped': [], 'directories': 0, 'files': 0, 'chunks': 0,
    }
    if not state['queue']:
        print('Already complete:', state['directories'], 'directories')
        return
    script = REMOTE.replace('INITIAL_STATE', repr({'queue': state['queue']}))
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                        'thu-wei', '/usr/bin/nice -n 10 python -'], input=script,
                       capture_output=True, text=True, timeout=38)
    if r.returncode:
        raise RuntimeError(r.stderr)
    chunk = json.loads(r.stdout)
    state['queue'] = chunk['queue']
    for key in ('matches', 'errors', 'skipped'):
        state[key].extend(chunk[key])
    for key in ('directories', 'files'):
        state[key] += chunk[key]
    state['chunks'] += 1
    STATE.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps({k: state[k] for k in ('directories', 'files', 'chunks')}))
    print('remaining dirs:', len(state['queue']), 'new matches:', chunk['matches'][:30],
          'new errors:', chunk['errors'][:5])


if __name__ == '__main__':
    main()
