"""One targeted static consistency check; no remote or native execution."""
from pathlib import Path
import ast
import json
import re
import sys

HERE=Path(__file__).resolve().parent
OWN=HERE.parents[2]
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
from review_standard_cell_storage_v2 import record,identity


def read(p):return json.loads(p.read_bytes())


def main():
    rec=record('sar8audit-ctrl-usage-baseline-ff-v1');files={x['name']:ROOT/x['source'] for x in rec['recipe']['files']}
    recipe=read(HERE/'recipe.suggested.yaml');manifest=read(HERE/'manifest.json');freeze=read(HERE/'freeze.json')
    assert freeze['proposed_recipe_file']==identity(HERE/'recipe.suggested.yaml')
    assert freeze['manifest']==identity(HERE/'manifest.json')
    assert freeze['single_measurement_diff']==identity(HERE/'single_measurement.diff')
    for x in manifest['inputs']:assert identity(ROOT/x['source'])=={k:x[k] for k in ['bytes','sha256']}
    for x in recipe['inputs']:assert identity(ROOT/x['source'])['sha256']==x['sha256']
    old=files['test.scs'].read_text();new=(HERE/'test.scs').read_text();assert new.startswith(old)
    suffix=new[len(old):];statements=[x for x in suffix.splitlines() if x and not x.startswith('//')]
    assert len(statements)==4 and all(' info what=' in x for x in statements)
    assert {re.search(r'what=(\w+)',x).group(1) for x in statements}=={'inst','nodes','primitives','oppoint'}
    assert all('where=file' in x and 'descriptions=yes' in x and 'extremes=no' in x for x in statements)
    assert new.count('tran_first tran ')==old.count('tran_first tran ')==1
    assert [x for x in new.splitlines() if x.startswith('save ')]==[x for x in old.splitlines() if x.startswith('save ')]
    assert not any('inst=[' in x for x in statements)
    assert '.M1' not in suffix and ':ids' not in suffix and ':oppoint' not in suffix
    assert {re.search(r'file="([^"]+)"',x).group(1) for x in statements}=={'../raw/'+n for n in read(HERE/'mapping.json')['info_files'].values()}
    names={x['name']:x for x in recipe['inputs']}
    for n in ['dut.scs','measurement.json','pwl/ff_ck.pwl','pwl/ff_d.pwl','pwl/ff_rst.pwl','pwl/context.pwl']:
        assert names[n]['sha256']==identity(files[n])['sha256']
    cfg=read(files['measurement.json']);assert (len(cfg['observed_mos']),len(cfg['stress_voltage_pairs']),len(cfg['voltage_saves']),len(cfg['current_saves']),len(cfg['kcl_terms']))==(58,348,36,73,6)
    for topic in ['info','save']:
        m=read(HERE/('installed_'+topic+'_help.json'))['metadata']
        assert m['command'][-1]==topic and m['returncode']==0 and m['stop_reason'] is None and m['elapsed_s']<8
    for f in HERE.glob('*.py'):ast.parse(f.read_text(encoding='utf-8'),filename=str(f))
    result=dict(status='one_targeted_static_check_pass',native_run=False,remote_simulation_or_analysis_execution=False,readonly_help_queries=2,
        source_run=rec['recipe']['run_id'],source_recipe_hash=rec['recipe_hash'],source13inputs_unchanged=True,
        candidate_recipe_file=freeze['proposed_recipe_file'],manifest=freeze['manifest'],
        candidate_inputs=len(recipe['inputs']),input_bytes=freeze['input_bytes'],
        sole_deck_delta='four supported static info statements',electrical_or_transient_change=False,
        original_saves_dut_PWL_measurement_unchanged=True,no_transient_OP_groups=True,no_guessed_child_alias=True,
        dimensions=dict(MOS=58,pairs=348,voltage_saves=36,current_saves=73,KCL_nodes=6),
        ids_id_interpretation='Named values only if exposed; no pure-channel or pass gate',
        AST='pass',fields_not_exposed_result='record once without retry',commit=False,push=False)
    (HERE/'validation.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],recipe_sha256=freeze['proposed_recipe_file']['sha256'],input_count=len(recipe['inputs']),input_bytes=freeze['input_bytes'])))


if __name__=='__main__':main()
