"""Local cold-corner copies of two frozen history decks; no dispatch."""
import argparse
import copy
import difflib
import json
from pathlib import Path

import builder as b

HERE=Path(__file__).resolve().parent
OUT=HERE/'cold_controls'


def change_temperature(text):
    lines=text.splitlines(keepends=True)
    matches=[i for i,line in enumerate(lines) if line.startswith('simulatorOptions ') and ' temp=125 ' in line]
    assert len(matches)==1
    i=matches[0]
    lines[i]=lines[i].replace(' temp=125 ',' temp=-40 ',1)
    changed=''.join(lines)
    assert changed.replace(' temp=-40 ',' temp=125 ',1)==text
    return changed


def payloads():
    stream=HERE/'stream_package'
    package=json.loads((stream/'package_manifest.json').read_text())
    finite=HERE/'finite_history'
    finite_manifest=json.loads((finite/'manifest.json').read_text())
    finite40=next(x for x in finite_manifest['variants'] if x['case']=='low40')
    finite_recipe=next(x for x in json.loads((finite/'recipe_suggestions.json').read_text())['recipes']
                       if x['run_id']=='sar8audit-sample-v2-low40')
    long_recipe=json.loads((stream/'recipe_suggestions.json').read_text())['recipes'][1]
    for name,rec in package['files'].items():
        assert b.sha((stream/'common'/name).read_bytes())==rec['sha256'],name
    analyzer=b.ROOT/package['reuse']['analyzer_source']
    assert b.sha(analyzer.read_bytes())==package['reuse']['analyzer_sha256']
    controls=[('low40cold',finite/'low40/test.scs',finite40['deck_sha256'],finite_recipe),
              ('longcold',stream/'long/test.scs',package['cases']['long']['sha256'],long_recipe)]
    outputs={};recipes=[];cases=[]
    for name,source,expected,template in controls:
        original=source.read_bytes();assert b.sha(original)==expected
        text=change_temperature(original.decode());data=text.encode()
        diff=''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),
            text.splitlines(keepends=True),fromfile=source.relative_to(b.ROOT).as_posix(),
            tofile=name+'/test.scs',n=1))
        outputs[name+'/test.scs']=data
        outputs[name+'/source.diff']=diff.encode()
        recipe=copy.deepcopy(template)
        recipe['run_id']='sar8audit-sample-v2-'+name
        for item in recipe['inputs']:
            if item['name']=='test.scs':item['source']=(OUT/name/'test.scs').relative_to(b.ROOT).as_posix()
        recipe['test_conditions'].update(temperature_c=-40,history=name)
        recipe['qualification_scope']='SS cold finite40ns versus low-DC precharge/acquisition diagnosis, not full-ADC PVT'
        recipes.append(recipe)
        cases.append(dict(name=name,run_id=recipe['run_id'],source=source.relative_to(b.ROOT).as_posix(),
            source_sha256=expected,deck_sha256=b.sha(data),diff_sha256=b.sha(diff.encode()),
            only_delta='simulatorOptions temp=125 -> temp=-40',
            actual_SEQ_edges_ns=None,simulator_invoked=False))
    manifest=dict(schema_version=1,status='local_prepared_not_registered_or_run',
        generator_sha256=b.sha(Path(__file__).read_bytes()),cases=cases,
        reused_measurement_files={n:dict(path=(stream/'common'/n).relative_to(b.ROOT).as_posix(),**v)
                                 for n,v in package['files'].items()},
        analyzer=package['reuse'],core_vdd_v=.81,MOS_corner='ss',passives='tt',
        original_sources_devices_loads_and_timing_unchanged=True,
        purpose='separate finite recovery history from acquisition after low-DC precharge at cold corner',
        initial_states='low40cold starts high-DC; longcold starts low-DC; compare actual natural states explicitly',
        full_ADC_PVT_qualified=False,minimum_precharge_requirement_ns=None)
    outputs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    outputs['recipe_suggestions.json']=(json.dumps(dict(register_only_after_parent_review=True,recipes=recipes),indent=2)+'\n').encode()
    return outputs


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    outputs=payloads()
    for name,data in outputs.items():
        target=OUT/name
        if target.exists():assert target.read_bytes()==data,'existing cold control differs: '+name
        elif a.check:raise AssertionError('missing cold control: '+name)
        else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps(dict(files=len(outputs),cold_controls=2,remote=False)))


if __name__=='__main__':main()
