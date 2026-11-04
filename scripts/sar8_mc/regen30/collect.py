"""Collect completed managed artifacts and verify the native scalar and search evidence."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from prepare import ROOT,DEST
import execution

def recover(run):
    receipt=execution.collect(run)
    assert not receipt['skipped'],receipt
    folder=ROOT/receipt['local_path']
    original=json.loads((folder/'collection_receipt.json').read_text())
    sha=next(f['sha256'] for f in original['files'] if f['name']=='derived/result.json')
    src=folder/'derived/result.json'
    assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
    d=json.loads(src.read_text());mapping=d['sample_mapping']
    assert mapping['identical'] and mapping['native_rows']==mapping['rows_checked']==(89 if '-base-' in run else 87)
    assert d['native_event_crosscheck'] and d['analysis_complete']
    out=DEST/'results'/run;out.mkdir(parents=True,exist_ok=True)
    small={k:d[k] for k in ['context','sample_mapping','threshold_valid','native_data_valid','held_threshold_interval_v','held_offset_midpoint_v','warning_codes','records']}
    small.update(source_result_sha256=sha,collection=receipt)
    (out/'measurement.json').write_text(json.dumps(small,indent=2)+'\n')

if __name__=='__main__':
    expected=json.loads((DEST/'jobs.json').read_text())
    remote=json.loads((DEST/'launch.json').read_text())['path']
    while True:
        reply=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei','cat '+remote+'/status.json'],capture_output=True,text=True,timeout=25)
        if reply.returncode:
            print('Status temporarily unavailable:',reply.stderr.strip(),flush=True);time.sleep(30);continue
        state=json.loads(reply.stdout)
        (DEST/'queue.json').write_text(json.dumps(state,indent=2))
        for run in state['completed']:
            if not (DEST/'results'/run/'measurement.json').exists():
                recover(run);print('Recovered',run,flush=True)
        if state['stage']=='failed':raise RuntimeError(state.get('error'))
        if state['stage']=='complete':
            assert set(state['completed'])==set(expected)
            break
        time.sleep(45)
