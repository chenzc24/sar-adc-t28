"""Freeze complete terminal capture from an existing minimal-reference short run."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import subprocess
import yaml
from .__main__ import engine
from .measure.soa_topology import statements

ROOT=Path(__file__).resolve().parents[2]


def prepare(corner, revision='v1', maxstep_ps=10):
    if corner not in ('tt','ssc','ssh','ffc','ffh') or not math.isfinite(maxstep_ps) or maxstep_ps<=0:
        raise ValueError('Known corner and positive finite maximum step required')
    old='sar8-minref-minimal-'+corner+('-v2' if corner=='tt' else '-song-v1')
    source=ROOT/'work/decks'/old
    original=json.loads((source/'recipe.yaml').read_text())
    blobs={i['name']:(ROOT/i['source']).read_bytes() for i in original['inputs']}
    for i in original['inputs']:
        assert hashlib.sha256(blobs[i['name']]).hexdigest()==i['sha256'],i['name']
    run_id='sar8-minref-soa-'+corner+'-song-'+revision
    engine().valid_id(run_id)
    destination=ROOT/'work/decks'/run_id
    library_path=re.search(r'\.include "([^"]+)"',blobs['library_include.scs'].decode())[1]
    match=re.search(r'XDUT\s*\(([^)]+)\)\s*(\S+)','\n'.join(statements(blobs['tb.scs'].decode())))
    request=dict(library_path=library_path,sources=[b.decode() for n,b in blobs.items()
        if n.endswith('.scs') and n.startswith(('top/','xtor/'))],
        master=match[2].lower(),ports=match[1].split())
    parser=(ROOT/'tools/saradc/measure/soa_topology.py').read_bytes()
    command='python -c '+shlex.quote("import base64;exec(compile(base64.b64decode('"+
        base64.b64encode(parser).decode()+"'),'soa_topology.py','exec'))")
    response=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','thu-song',command],
                            input=json.dumps(request).encode(),capture_output=True,timeout=60)
    if response.returncode:raise RuntimeError(response.stderr.decode(errors='replace'))
    inventory=json.loads(response.stdout)
    rule_bytes=(ROOT/'specs/soa_rule.yaml').read_bytes()
    rule=yaml.safe_load(rule_bytes)
    models={d['model'] for d in inventory['devices']}
    known=set(rule['scope']['thin_oxide_mos_models']+rule['scope']['thin_oxide_moscap_models']+
              rule['scope']['thick_oxide_models_outside_this_rule'])
    assert not models-known,models-known
    nodes=sorted({n for d in inventory['devices'] for n in d['nodes']}-{'0'})
    deck=blobs['test.scs'].decode()
    deck=re.sub(r'maxstep=10p', 'maxstep=%gp'%maxstep_ps,deck)
    deck+='\n// Complete physical MOS terminal inventory; no circuit change.\n'
    deck+='\n'.join('save '+' '.join(nodes[i:i+15]) for i in range(0,len(nodes),15))+'\n'
    blobs['test.scs']=deck.encode()
    blobs['terminal_inventory.json']=(json.dumps(inventory,indent=2)+'\n').encode()
    blobs['soa_rule.yaml']=rule_bytes
    for name in ('soa.py','soa_scan.cpp','native_stream.py'):
        blobs[name]=(ROOT/'tools/saradc/measure'/name).read_bytes()
    ctx=dict(run_id=run_id,source_run_id=old,corner=corner,rule=rule,
             rule_sha256=hashlib.sha256(rule_bytes).hexdigest(),
             expected_stop_s=original['expected_stop_s'],
             expected_codes=original['test_conditions']['expected_codes'],
             source_input_hashes={i['name']:i['sha256'] for i in original['inputs']},
             change_scope='save all MOS terminal nodes; optional maxstep refinement only',maxstep_ps=maxstep_ps)
    blobs['soa_context.json']=(json.dumps(ctx,indent=2)+'\n').encode()
    for name,data in blobs.items():
        target=destination/name
        if target.exists() and target.read_bytes()!=data:raise ValueError('Immutable input differs: '+str(target))
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    resources=dict(original['resources'])
    resources.update(max_output_mib=65536,analysis_wall_seconds=14400)
    recipe=dict(schema_version=1,run_id=run_id,design_id='sar8_reference_minimal_soa',entry='test.scs',analyzer='soa.py',
                inputs=[dict(name=n,source=(destination/n).relative_to(ROOT).as_posix(),sha256=hashlib.sha256(b).hexdigest()) for n,b in blobs.items()],
                resources=resources,spectre_args=original['spectre_args'],summary_signals=['sample'],
                expected_stop_s=original['expected_stop_s'],qualification_scope='Native per-device engineering SOA; resolution review required',test_conditions=ctx)
    path=destination/'recipe.yaml';data=(json.dumps(recipe,indent=2)+'\n').encode()
    if path.exists() and path.read_bytes()!=data:raise ValueError('Immutable recipe differs')
    path.write_bytes(data)
    return path.relative_to(ROOT).as_posix(),dict(devices=len(inventory['devices']),nodes=len(nodes),models=sorted(models))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','submit']);p.add_argument('--corner',required=True,choices=['tt','ssc','ssh','ffc','ffh'])
    p.add_argument('--revision',default='v1');p.add_argument('--maxstep-ps',type=float,default=10)
    a=p.parse_args();path,info=prepare(a.corner,a.revision,a.maxstep_ps)
    if a.action=='submit':
        e=engine();e.register(path,host='thu-song')
        info['submission']=e.phase('submit',json.loads((ROOT/path).read_text())['run_id'],queue=True)
    print(json.dumps(dict(recipe=path,**info),indent=2))
