"""Freeze the original per-seed stochastic rows and three matched threshold decks."""
import base64
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHYSICAL = ROOT / 'verification/sar8_mc/physical_input'
DEST = ROOT / 'verification/sar8_mc/regen30'
sys.path.insert(0, str(ROOT / 'scripts/management'))
sys.path.insert(0, str(ROOT / 'scripts/sar8_mc/physical_input'))
import execution
import fetch_samples

GROUPS = {'base':'noinputmm','n':'regenn','p':'regenp'}
def dump(path, data):
    content = json.dumps(data, indent=2) + '\n'
    if path.exists():
        assert path.read_text(encoding='utf-8') == content, path
    else:
        path.write_text(content, encoding='utf-8')

def prepare():
    DEST.mkdir(exist_ok=True)
    seeds = [s for s in range(4101,4131) if s not in (4121,4124)]
    remote = fetch_samples.REMOTE.replace('for seed in [4121,4124]:','for seed in '+repr(seeds)+':')
    reply = subprocess.run(['ssh','-o','BatchMode=yes','thu-wei','python -'],input=remote,text=True,capture_output=True,timeout=90,check=True)
    draws = json.loads(reply.stdout)
    runs=[]
    for seed in seeds:
        source = draws[str(seed)]
        scalars={}
        for name, item in source['files'].items():
            data=base64.b64decode(item['data'])
            assert hashlib.sha256(data).hexdigest()==item['sha256']
            scalars[name]=data.decode('ascii').splitlines()
        old=json.loads((ROOT/'verification/sar8_mc/blocks/results'/source['run_id']/'result.json').read_text())
        assert old['mismatch_evidence']['values_sha256']==source['files']['mismatch.values']['sha256']
        names=scalars['mismatch.params'];cols=names.pop(0).split()
        values=scalars['mismatch.values'];assert values.pop(0)=='#1'
        names=[n.strip() for n in names if n.strip()]
        values=[[float(x) for x in row.split()] for row in values if row.strip()]
        assert len(set(names))==len(values)==len(names)==91 and all(len(row)==len(cols) for row in values)
        for group, original in GROUPS.items():
            template='sar8phys-s4121-'+original+'-v1'
            folder=PHYSICAL/template
            run='sar8rg30-s%d-%s-v1'%(seed,group);runs.append(run)
            case=DEST/run;case.mkdir(exist_ok=True)
            ctx=json.loads((folder/'context.json').read_text())
            ctx.update(seed=seed,run_id=run,parent_run_id=source['run_id'],cycles=12,stop_s=1259e-9)
            deck=(folder/'test.scs').read_text()
            assert deck.count(' seed=4121 ')==deck.count('stop=2259n')==1
            deck=deck.replace(' seed=4121 ',' seed=%d '%seed).replace('stop=2259n','stop=1259n')
            path=case/'test.scs'
            if path.exists():assert path.read_text()==deck
            else:path.write_text(deck)
            kept={name:row for name,row in zip(names,values) if name not in ctx['nominalized_instances']}
            assert len(kept)==(89 if group=='base' else 87)
            dump(case/'context.json',ctx)
            dump(case/'expected_mismatch.json',{'rows':kept,'columns':cols,'source_run_id':source['run_id'],
                'nominalized_instances':ctx['nominalized_instances'],'values_sha256':source['files']['mismatch.values']['sha256']})
            recipe=json.loads((ROOT/'management/recipes'/(template+'.yaml')).read_text())
            recipe.update(run_id=run,expected_stop_s=ctx['stop_s'],test_conditions=ctx)
            for f in recipe['inputs']:
                if f['name'] in ['test.scs','context.json','expected_mismatch.json']:
                    f['source']=(case/f['name']).relative_to(ROOT).as_posix()
                assert (ROOT/f['source']).is_file()
                digest=hashlib.sha256((ROOT/f['source']).read_bytes()).hexdigest()
                if f['name'] not in ['test.scs','context.json','expected_mismatch.json']:assert digest==f['sha256']
                f['sha256']=digest
            dump(ROOT/'management/recipes'/(run+'.yaml'),recipe)
    dump(DEST/'jobs.json',runs)
    return runs

def register(run):
    receipt=ROOT/'output/managed_execution/runs'/run/'registration.json'
    if receipt.exists():
        return json.loads(receipt.read_text())['recipe_hash']
    info=execution.register('management/recipes/'+run+'.yaml')
    print('Registered',run,flush=True)
    return info['recipe_hash']

if __name__=='__main__':
    runs=prepare()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        hashes=dict(zip(runs,pool.map(register,runs)))
    dump(DEST/'registered.json',hashes)
