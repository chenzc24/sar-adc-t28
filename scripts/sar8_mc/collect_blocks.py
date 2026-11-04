"""Collect bounded, hash-checked native module results; never submit work."""
import argparse,json,shlex,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];V=R/'verification/sar8_mc/blocks'
sys.path.insert(0,str(R/'scripts/management'));import execution

def snapshot(revision):
    remote='/server_local_ssd/chenzc_intern25/sar-adc-t28/campaigns/sar8-mc-20261103/modules'+('_v2' if revision==2 else '')+'/status.json'
    code='import json;print(json.dumps(json.load(open('+repr(remote)+'))))'
    r=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -c '+shlex.quote(code)],capture_output=True,text=True,timeout=25);r.check_returncode();return json.loads(r.stdout)

def main():
    p=argparse.ArgumentParser();p.add_argument('--follow',action='store_true');p.add_argument('--revision',type=int,default=1);a=p.parse_args();start=time.time();m=json.loads((V/('v2_manifest.json' if a.revision==2 else 'manifest.json')).read_text())
    receipt=V/('collections_v2.json' if a.revision==2 else 'collections.json');done=json.loads(receipt.read_text()) if receipt.exists() else {}
    while True:
        s=snapshot(a.revision);(R/('output/sar8_mc/module_status_v2.json' if a.revision==2 else 'output/sar8_mc/module_status.json')).write_text(json.dumps(s,indent=2)+'\n')
        for run in s['completed']:
            if run in done:continue
            rec=execution.collect(run);assert not rec.get('skipped'),rec.get('skipped')
            src=R/'output/managed_execution/runs'/run/'collected/derived/result.json';r=json.loads(src.read_text());assert r['analysis_complete'] and r['native_data_valid']
            dest=V/'results'/run;dest.mkdir(parents=True,exist_ok=True);(dest/'result.json').write_bytes(src.read_bytes());(dest/'collection.json').write_text(json.dumps(rec,indent=2)+'\n')
            done[run]={'collection':str((dest/'collection.json').relative_to(R)),'result':str((dest/'result.json').relative_to(R))}
            receipt.write_text(json.dumps(done,indent=2)+'\n');print('Collected',len(done),'/',len(m['runs']),run,flush=True)
        if s['stage'] in ['failed','complete']:
            print('Coordinator',s['stage'],s.get('error',''),flush=True);break
        if not a.follow or time.time()-start>4*3600:break
        time.sleep(20)
if __name__=='__main__':main()
