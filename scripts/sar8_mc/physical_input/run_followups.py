"""Run one bounded three-case diagnostic set using managed state, no resubmits."""
import argparse,hashlib,json,shutil,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';O=R/'output/sar8_mc/physical_input';sys.path.insert(0,str(R/'scripts/management'))
import execution
def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['controls','width4','width2','accuracy','regen']);a=p.parse_args()
    runs=json.loads((V/('followup_'+a.kind+'_manifest.json')).read_text())['runs'];done={};last={};deadline=time.monotonic()+4*3600
    while len(done)<len(runs):
        pending=[]
        for run in runs:
            if run in done:continue
            s=execution.phase('status',run);phase='simulation' if s['simulation']['status']!='complete' else 'analysis';state=s[phase]
            if state['status']=='not_started':
                x=execution.phase('submit' if phase=='simulation' else 'analyze',run,True);print('Start',phase,run,json.dumps(x),flush=True)
            elif state['status']=='complete':
                c=execution.collect(run);assert not c['skipped'];src=R/c['local_path']/'derived/result.json';d=V/'results'/run;d.mkdir(parents=True,exist_ok=True);dest=d/'result.json'
                receipt=json.loads((R/c['local_path']/'collection_receipt.json').read_text());h=next(x['sha256'] for x in receipt['files'] if x['name']=='derived/result.json');assert hashlib.sha256(src.read_bytes()).hexdigest()==h
                if dest.exists():assert dest.read_bytes()==src.read_bytes()
                else:shutil.copyfile(src,dest)
                (d/'collection.json').write_text(json.dumps(c,indent=2)+'\n');r=json.loads(src.read_text());done[run]={'result':dest.relative_to(R).as_posix(),'result_sha256':h,'native_data_valid':r['native_data_valid'],'threshold_valid':r['threshold_valid']}
                print('Collected',run,'held_mV',r['held_offset_midpoint_v']*1000,'mapping',r['sample_mapping']['identical'],'changed',r['sample_mapping'].get('changed',[]),flush=True)
                continue
            elif state['status'] not in ['running','queued','starting','submitted','waiting']:raise RuntimeError('Preserve failed run '+run+' '+phase+' '+str(state))
            current=(phase,state['status'])
            if last.get(run)!=current:print('State',run,*current,flush=True);last[run]=current
            pending.append({'run_id':run,'phase':phase,'status':state['status']})
        status={'stage':'complete' if len(done)==len(runs) else 'running','completed':done,'pending':pending,'epoch':time.time()}
        (O/(a.kind+'_status.json')).write_text(json.dumps(status,indent=2)+'\n');(V/(a.kind+'_collections.json')).write_text(json.dumps(done,indent=2)+'\n')
        if time.monotonic()>deadline:raise RuntimeError('Finite4h timeout; remote tasks preserved')
        if len(done)<len(runs):time.sleep(20)
    print('Set complete',a.kind,flush=True)
if __name__=='__main__':main()
