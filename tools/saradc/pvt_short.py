"""Prepare the remaining 40 points of the explicit 45-point short-test matrix."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from . import reference_short

ROOT=Path(__file__).resolve().parents[2]

def matrix(config):
    return {('%s_%s_%s'%(p.lower(),s,'m40' if t==-40 else t)):
            dict(mos=p,temperature_c=t,vdd_v=v)
            for p,(s,v),t in itertools.product(config['process'],config['supply_v'].items(),config['temperature_c'])}

def prepare(revision='resetor40-v1'):
    cfg=json.loads((ROOT/'specs/pvt_short.json').read_text(encoding='utf-8'))
    conditions=matrix(cfg)
    assert len(conditions)==45 and len(cfg['existing_five'])==5
    assert set(cfg['existing_five'])<=set(conditions)
    adoption, original_sources = reference_short.resetor_20261115_sources()
    batch=dict(schema_version=1,revision=revision,host='thu-song',design_id=adoption['design_id'],
               design_source_sha256=adoption['source_sha256'],scope=cfg['scope'],code_centers=cfg['code_centers_in_order'],
               existing_five={n:'sar8-minref-soa-'+old+'-song-'+cfg['existing_five_revision'] for n,old in cfg['existing_five'].items()},runs=[])
    for name,condition in conditions.items():
        if name in cfg['existing_five']:continue
        path=reference_short.prepare('current',name,revision,condition=condition,codes=cfg['code_centers_in_order'],
                                     max_output_mib=cfg['max_output_mib_per_run'],source_blobs=original_sources)
        recipe=json.loads((ROOT/path).read_text(encoding='utf-8'))
        assert recipe['test_conditions']['passive_sections']==cfg['passive_sections']
        assert recipe['test_conditions']['reference_v']==cfg['reference_v']
        assert recipe['test_conditions']['frames']==cfg['frames_per_new_corner']
        actual={r['name']:r['sha256'] for r in recipe['inputs']}
        assert all(actual[n]==h for n,h in adoption['source_sha256'].items())
        batch['runs'].append(dict(corner=name,condition=condition,run_id=recipe['run_id'],recipe=path,
                                  prepared_recipe_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()))
    assert len(batch['runs'])==40
    dest=ROOT/'work/pvt45'/revision/'batch.json';dest.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(batch,indent=2)+'\n').encode()
    if dest.exists() and dest.read_bytes()!=data:raise ValueError('Existing batch identity differs')
    dest.write_bytes(data)
    return dest.relative_to(ROOT).as_posix()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',default='resetor40-v1')
    print(prepare(p.parse_args().revision))
