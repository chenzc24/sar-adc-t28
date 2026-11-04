"""Prepare only finite low-history input variants from the frozen short deck."""
import argparse
import copy
from decimal import Decimal
import difflib
import json
from pathlib import Path
import re

import builder as b

HERE=Path(__file__).resolve().parent
FROZEN=HERE/'stream_package'
OUT=HERE/'finite_history'
PLATEAUS=[2,10,40]


def change_history(text,plateau_ns):
    if type(plateau_ns) is not int or plateau_ns not in PLATEAUS:
        raise ValueError('only parent-approved2/10/40ns plateaus')
    end=Decimal(101)-Decimal(plateau_ns)
    start=end-Decimal('0.1')
    fmt=lambda value:format(value,'f').rstrip('0').rstrip('.') if '.' in format(value,'f') else str(value)
    old='0n SUP 100.8n SUP 100.9n 0 101n 0'
    new=f'0n SUP {fmt(start)}n SUP {fmt(end)}n 0 101n 0'
    assert text.count(old)==1
    changed=text.replace(old,new,1)
    strip=lambda s:re.sub(r'(?m)^VSAMPLE .*$', '', s)
    assert strip(text)==strip(changed)
    return changed,dict(external_low_plateau_ns=plateau_ns,
        source_fall_start_ns=float(start),source_fall_end_ns=float(end),
        source_rise_start_ns=101,source_close_start_ns=141,
        edge_duration_ns=.1,actual_SEQ_low_interval_ns=None)


def payloads():
    package=json.loads((FROZEN/'package_manifest.json').read_text())
    baseline=(FROZEN/'short/test.scs').read_bytes()
    assert b.sha(baseline)==package['cases']['short']['sha256']
    for name,rec in package['files'].items():
        assert b.sha((FROZEN/'common'/name).read_bytes())==rec['sha256'],name
    remote=b.ROOT/package['reuse']['analyzer_source']
    assert b.sha(remote.read_bytes())==package['reuse']['analyzer_sha256']
    original_recipe=json.loads((FROZEN/'recipe_suggestions.json').read_text())['recipes'][0]
    original=baseline.decode()
    outputs={};recipes=[];rows=[]
    for duration in PLATEAUS:
        name=f'low{duration}'
        changed,timing=change_history(original,duration)
        data=changed.encode()
        diff=''.join(difflib.unified_diff(original.splitlines(keepends=True),
            changed.splitlines(keepends=True),fromfile='frozen-short/test.scs',
            tofile=name+'/test.scs',n=1))
        outputs[name+'/test.scs']=data
        outputs[name+'/source.diff']=diff.encode()
        recipe=copy.deepcopy(original_recipe)
        recipe['run_id']='sar8audit-sample-v2-'+name
        for item in recipe['inputs']:
            if item['name']=='test.scs':item['source']=(OUT/name/'test.scs').relative_to(b.ROOT).as_posix()
        recipe['test_conditions'].update(history='finite_'+name,
            external_low_plateau_ns=duration,
            source_initial_fall_start_ns=timing['source_fall_start_ns'],
            source_initial_fall_end_ns=timing['source_fall_end_ns'])
        recipe['qualification_scope']='Finite external low-history sensitivity from same high-DC start; actual SEQ interval must be measured'
        recipes.append(recipe)
        rows.append(dict(case=name,run_id=recipe['run_id'],timing=timing,
            deck_sha256=b.sha(data),diff_sha256=b.sha(diff.encode()),
            only_changed_source='VSAMPLE initial falling edge',
            initial_SAMPLE='SUP',initial_DUT_operating_point='same high-DC as frozen short, subject to native DC verification',
            source_after101ns_identical=True,simulator_invoked=False))
    manifest=dict(schema_version=1,status='local_prepared_not_registered_or_run',
        generator_sha256=b.sha(Path(__file__).read_bytes()),
        source_short_sha256=package['cases']['short']['sha256'],
        reused_common={name:dict(path=(FROZEN/'common'/name).relative_to(b.ROOT).as_posix(),**rec)
                       for name,rec in package['files'].items()},
        reused_analyzer=package['reuse'],variants=rows,
        plateau_definition='source first falling transition END to source rising transition START at101ns',
        actual_SEQ_low_duration_equals_external_plateau=False,
        low_DC_case_is_finite_duration_point=False,
        unchanged=['all DUT devices/parameters/load','SS/0.81V/125C','TT passive models',
            'original input PWL including100.2-100.3ns reversal','50ohm input/reference and4pF decap',
            'formal source rise101ns and close141ns/100ps edges','mapping/pairs/selected/events/products/stream.cpp/loaded_remote.py'],
        measurement='reuse native events and20ps compact estimates; preclose versus141.8ns kept separate; actual opening/close required',
        startup_limit_v=None,droop_limit_v=None,
        analysis_rss_limit_mib=256,collection_limit_mib=32,
        strict_Bootstrap_only_causal_claim=False)
    outputs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    outputs['recipe_suggestions.json']=(json.dumps(dict(register_only_after_parent_review=True,recipes=recipes),indent=2)+'\n').encode()
    return outputs


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    outputs=payloads()
    for name,data in outputs.items():
        target=OUT/name
        if target.exists():assert target.read_bytes()==data,'existing finite-history file differs: '+name
        elif a.check:raise AssertionError('missing finite-history file: '+name)
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps(dict(files=len(outputs),variants=PLATEAUS,frozen_inputs_unchanged=True,remote=False)))


if __name__=='__main__':main()
