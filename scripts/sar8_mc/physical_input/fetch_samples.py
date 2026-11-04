"""Bounded read of already-completed native mismatch scalar metadata."""
import base64,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';O=R/'output/sar8_mc/physical_input'
REMOTE=r'''
import os,json,base64,hashlib
root='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs';out={}
assert os.getuid()==596
for seed in [4121,4124]:
 run='sar8mc-comp-s%d-v2'%seed;d=root+'/'+run
 state=json.load(open(d+'/simulation.state.json'));assert state['status']=='complete',state
 files={}
 for name in ['mismatch.params','mismatch.values']:
  p=d+'/raw/'+name;assert os.path.getsize(p)<1024*1024
  b=open(p,'rb').read();files[name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'data':base64.b64encode(b)}
 out[str(seed)]={'run_id':run,'files':files}
print(json.dumps(out))
'''
def main():
    V.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
    p=subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -'],input=REMOTE,text=True,capture_output=True,timeout=30)
    assert p.returncode==0,p.stderr
    data=json.loads(p.stdout);receipts={}
    for seed,item in data.items():
        texts={}
        for n,f in item['files'].items():
            b=base64.b64decode(f['data']);assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'];texts[n]=b.decode('ascii')
            (O/(seed+'-'+n)).write_bytes(b)
        labels=texts['mismatch.params'].splitlines();values=texts['mismatch.values'].splitlines();assert values.pop(0)=='#1'
        cols=labels.pop(0).split();names=[n.strip() for n in labels if n.strip()];rows=[[float(v) for v in line.split()] for line in values if line.strip()]
        assert len(names)==len(rows) and all(len(x)==len(cols) for x in rows)
        reference=json.loads((R/'verification/sar8_mc/blocks/results'/item['run_id']/'result.json').read_text())
        assert reference['mismatch_evidence']['values_sha256']==item['files']['mismatch.values']['sha256']
        out={'source_run_id':item['run_id'],'columns':cols,'rows':dict(zip(names,rows)),
          'values_sha256':item['files']['mismatch.values']['sha256'],'labels_sha256':item['files']['mismatch.params']['sha256'],'offset_midpoint_v':reference['offset_midpoint_v']}
        (O/('sample'+seed+'.json')).write_text(json.dumps(out,indent=2)+'\n')
        receipts[seed]={k:v for k,v in out.items() if k not in ['rows','columns']};receipts[seed]['rows']=len(rows)
    (V/'retained_samples.json').write_text(json.dumps(receipts,indent=2)+'\n');print(json.dumps(receipts))
if __name__=='__main__':main()
