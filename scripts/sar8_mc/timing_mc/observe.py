"""Read the pinned inspector and save wait cursors. Never submits or changes runs."""
import argparse
import collections
import json
import shlex
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'verification/sar8_mc/timing_mc'
def observe(group,wait):
    r=json.loads((OUT/(group+'_launch.json')).read_text())
    cursor=OUT/(group+'_cursor.json')
    args=[r['python'],'-m','simcheck','--db',r['db']]
    if wait and cursor.exists():
        args+=['wait','--json','--cursor',json.loads(cursor.read_text())['cursor'],'--timeout','30']
    else:args+=['status','--json']
    remote='cd '+shlex.quote(r['cwd'])+' && '+shlex.join(args)
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei',remote],capture_output=True,encoding="utf-8",timeout=65)
    if p.returncode not in (0,3,4):raise RuntimeError(p.stderr)
    data=json.loads(p.stdout)
    if data.get('cursor'):cursor.write_text(json.dumps({'cursor':data['cursor']},indent=2)+'\n')
    print(group, 'collector',data.get('collector'), 'states',dict(collections.Counter(x['state'] for x in data.get('runs',[]) if 'state' in x)), 'cursor',data.get('cursor'))
    dest=ROOT/'output/sar8_mc/timing_mc'
    dest.mkdir(parents=True,exist_ok=True)
    (dest/(group+('_wait.json' if wait else '_status.json'))).write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('group',choices=['modules','cold','refs']);p.add_argument('--wait',action='store_true')
    a=p.parse_args();observe(a.group,a.wait)
