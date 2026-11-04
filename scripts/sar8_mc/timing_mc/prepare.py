"""Clone exact managed recipe inputs; only new immutable run IDs are registered."""
import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'verification/sar8_mc/timing_mc'
REC = ROOT/'management/recipes'
sys.path.insert(0, str(ROOT/'scripts/management'))
import execution


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode() if isinstance(content, str) else (json.dumps(content, indent=2)+'\n').encode()
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Immutable input changed: '+str(path))
    else:
        path.write_bytes(data)


def build(kind, seed):
    module = kind in ('cdac', 'comp')
    parent = 'sar8mc-%s-s4101-v2'%kind if module else 'sar8camp-b-%s-screen-mm-v2'%kind
    run = 'sar8tm-%s-s%d-v1'%(kind,seed)
    recipe = json.loads((REC/(parent+'.yaml')).read_text())
    dest = OUT/run
    files = []
    for item in recipe['inputs']:
        name = item['name']
        path = ROOT/item['source']
        assert sha(path)==item['sha256'],path
        if name=='context.json':
            ctx = json.loads(path.read_text())
            ctx.update(run_id=run,seed=seed,mismatch=True)
            path = dest/name
            save(path,ctx)
            recipe['test_conditions']=ctx
        elif name=='test.scs':
            deck = path.read_text()
            if module:
                assert deck.count(' seed=4101 ')==1
                deck = deck.replace(' seed=4101 ',' seed=%d '%seed)
            else:
                child = re.search(r'(?m)^tran_ab tran .+$',deck).group()
                deck = deck.replace(child,('mc montecarlo numruns=1 seed=%d variations=mismatch dut=[XDUT.XCOMP XDUT.XCDAC] sampling=standard donominal=no savemismatchparams=yes mismatchparamfile="mismatch.params" mismatchscalarfile="mismatch.values" savefamilyplots=yes savedatainseparatedir=yes {\n'%seed)+child+'\n}')
                corner = kind[:2]
                for old,new in [(corner+'macro_mos_moscap',corner.upper()+'GlobalCorner_LocalMC_MOS_MOSCAP'),('tt_mom','TTGlobalCorner_LocalMC_MOM')]:
                    assert deck.count('section='+old+'\n')==1
                    deck=deck.replace('section='+old+'\n','section='+new+'\n')
                pins = ['XDUT.XCDAC.B%s%d'%(side,b) for side in 'PN' for b in range(8)] + ['XDUT.G%s%s%d'%(side,g,b) for side in 'PN' for g in 'NP' for b in range(8)]
                deck += 'save '+' '.join(pins)+'\n'
                deck += 'save XDUT.XCTRL.XTIM.PR XDUT.XCTRL.XTIM.NR XDUT.XCTRL.DATA\n'
            path=dest/name
            save(path,deck)
        if not module and name==recipe['analyzer']:
            name='timing.py'
            path=Path(__file__).with_name(name)
        files.append({'name':name,'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
    if not module:
        for name,rel in [('native_stream.py','scripts/sar8_campaign/native_stream.py'),('block_reduce.py','scripts/sar8_mc/block_reduce.py')]:
            path=ROOT/rel
            files.append({'name':name,'source':rel,'sha256':sha(path)})
        recipe['analyzer']='timing.py'
        recipe['resources'].update(max_output_mib=1536,simulation_wall_seconds=21600)
    recipe.update(inputs=files,run_id=run)
    save(REC/(run+'.yaml'),recipe)
    return run


def register(run):
    saved=ROOT/'output/managed_execution/runs'/run/'registration.json'
    if saved.exists():
        return json.loads(saved.read_text())['recipe_hash']
    return execution.register('management/recipes/'+run+'.yaml')['recipe_hash']


if __name__=='__main__':
    group=sys.argv[1]
    if group=='modules':
        jobs=[build(k,s) for s in range(4131,4301) for k in ('cdac','comp')]
    elif group=='cold':
        jobs=[build(k,s) for s in range(5101,5151) for k in ('ssc','ffc')]
    else:
        raise ValueError(group)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        hashes=dict(zip(jobs,pool.map(register,jobs)))
    save(OUT/(group+'.json'),{'jobs':jobs,'registered_hashes':hashes,'group':group,'agent_sha256':sha(ROOT/'scripts/management/remote_agent.py')})
    print(group,len(hashes),flush=True)
