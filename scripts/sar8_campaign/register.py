"""Register future immutable recipes only; never launch simulations."""
import hashlib,json,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'scripts/management'))
import execution
def main():
    folder=R/'verification/sar8_campaign';manifest=json.loads((folder/'manifest.json').read_text())
    receipts=[];run_ids=[]
    for label in ['a','b']:
        for point in ['tt','ssc','ssh','ffc','ffh']:
            d=manifest['labels'][label]['points'][point]
            run_ids+=([d['screen']] if 'screen' in d else [])+d['static']+([d['dynamic']] if 'dynamic' in d else [])
    for i,run in enumerate(run_ids):
        receipt=execution.register('management/recipes/'+run+'.yaml');receipts.append(dict(run_id=run,receipt=receipt))
        (folder/'registration_receipts.json').write_text(json.dumps(receipts,indent=2))
        if (i+1)%10==0:print('Registered %d/%d'%(i+1,len(run_ids)),flush=True)
    manifest['registered_hashes']=dict((r['run_id'],r['receipt']['recipe_hash']) for r in receipts)
    import yaml
    for run in ['sar8ab-'+l+'-tt-short-v1' for l in ['a','b']]+['sar8ab-phase60-'+l+'-tt-v1' for l in ['a','b']]:
        record=yaml.safe_load((R/'management/runs'/(run+'.yaml')).read_text())
        manifest['registered_hashes'][run]=record['recipe_hash']
    manifest['agent_sha256']=hashlib.sha256((R/'scripts/management/remote_agent.py').read_bytes()).hexdigest()
    (folder/'server_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('All recipes registered; server manifest ready.',flush=True)
if __name__=='__main__':main()
