"""Recover only completed small results from the finite physical-input flow."""
import hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';O=R/'output/sar8_mc/physical_input';sys.path.insert(0,str(R/'scripts/management'))
import execution
def main():
    receipt=V/'collections.json';done=json.loads(receipt.read_text()) if receipt.exists() else {};deadline=time.monotonic()+4*3600
    while True:
        remote="print(open('/server_local_ssd/chenzc_intern25/sar-adc-t28/campaigns/sar8-physical-input-20261104/recovery_v2/status.json').read())"
        p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','thu-wei','python -'],input=remote,text=True,capture_output=True,timeout=25)
        assert p.returncode==0,p.stderr
        status=json.loads(p.stdout);(O/'recovery_status.json').write_text(p.stdout)
        for run in status['completed']:
            if run in done:continue
            c=execution.collect(run);assert not c['skipped'];src=R/c['local_path']/'derived/result.json';d=V/'results'/run;d.mkdir(parents=True,exist_ok=True)
            original=json.loads((R/c['local_path']/'collection_receipt.json').read_text());h=next(f['sha256'] for f in original['files'] if f['name']=='derived/result.json')
            assert hashlib.sha256(src.read_bytes()).hexdigest()==h
            target=d/'result.json'
            if target.exists():assert target.read_bytes()==src.read_bytes()
            else:shutil.copyfile(src,target)
            (d/'collection.json').write_text(json.dumps(c,indent=2)+'\n');done[run]={'result':target.relative_to(R).as_posix(),'result_sha256':h,'bytes':c['bytes']};receipt.write_text(json.dumps(done,indent=2)+'\n')
            x=json.loads(src.read_text());print('Collected',len(done),run,'held_mV',x['held_offset_midpoint_v']*1000,'mapping',x['sample_mapping']['identical'],flush=True)
        if status['stage'] in ['complete','failed']:
            print('Finite flow',status['stage'],status.get('error',''),flush=True);return
        if time.monotonic()>deadline:raise RuntimeError('Finite collection4h deadline; preserve remote workers')
        time.sleep(20)
if __name__=='__main__':main()
