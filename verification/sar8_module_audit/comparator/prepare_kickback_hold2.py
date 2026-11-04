"""Local single-variable proposal: omit only the second initialization pulse."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re

from build_kickback_fixture import exact,js,sha
from prepare_kickback_savefix import validate_saves

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'generated/kickback_v2'
DEST=HERE/'generated/kickback_hold2_v1'
DROP=[('44n','0'),('44.1n','SUP'),('58n','SUP'),('58.1n','0')]


def remove_second_pulse(text):
    matches=list(re.finditer(r'(?m)^VINIT \(CINIT 0\) vsource type=pwl wave=\[([^\]]+)\]$',text))
    if len(matches)!=1:raise ValueError('Expected exactly one original CINIT source')
    match=matches[0];tokens=match[1].split()
    if len(tokens)%2:raise ValueError('Incomplete initialization PWL')
    pairs=list(zip(tokens[::2],tokens[1::2]))
    removed=[pair for pair in pairs if pair[0] in {p[0] for p in DROP}]
    if removed!=DROP:raise ValueError('Second acquisition pulse differs from frozen v2')
    kept=[pair for pair in pairs if pair not in DROP]
    replacement=' '.join(value for pair in kept for value in pair)
    return text[:match.start(1)]+replacement+text[match.end(1):]


def prepare():
    old_cfg=json.loads((SOURCE/'measurement.json').read_bytes())
    old_recipe=json.loads((SOURCE/'recipe_proposal.json').read_bytes())
    manifest=json.loads((SOURCE/'manifest.json').read_bytes())
    for name,h in manifest['input_hashes'].items():
        if sha((SOURCE/name).read_bytes())!=h:raise ValueError('Frozen v2 source differs: '+name)
    payload={row['name']:(SOURCE/row['name']).read_bytes() for row in old_recipe['inputs']}
    payload['test.scs']=remove_second_pulse(payload['test.scs'].decode()).encode()
    cfg=copy.deepcopy(old_cfg)
    cfg['required_input_sha256']['test.scs']=sha(payload['test.scs'])
    # No new release occurs before compare2. Keep measurement labels physically true.
    cfg['cycles'][1]['release_start_s']=cfg['cycles'][0]['release_start_s']
    cfg['cycles'][1]['release_end_s']=cfg['cycles'][0]['release_end_s']
    cfg['cycles'][0]['next_acquire_s']=cfg['cycles'][1]['next_acquire_s']
    cfg['diagnostic_history']=dict(variable='Second acquisition enable only',
        omitted_pulse_s=[44e-9,58.1e-9],continuous_hold_interval_s=[18.1e-9,84e-9],
        first_two_nominal_differential_v=[cfg['cycles'][i]['target_diff_v'] for i in [0,1]],
        measurement='Compare2 initialized/after_release refer to original first acquisition; inspect its actual pre_compare residual/CM and write delay',
        phase_note='Compare1 next_acquire is84ns; compare2 occurs during that hold. Do not label the whole32.1--84ns interval as reset-only.')
    payload['measurement.json']=js(cfg).encode()
    for name,blob in payload.items():exact(DEST/name,blob)
    saved=validate_saves(DEST,cfg)
    recipe=copy.deepcopy(old_recipe)
    recipe.update(run_id='sar8audit-comp-hold2-tt-v1',design_id='sar8_comp_cdac_hold2_tt_v1')
    recipe['inputs']=[dict(name=name,source=(DEST/name).relative_to(ROOT).as_posix(),sha256=sha(blob))
                      for name,blob in payload.items()]
    recipe['test_conditions']['initialization']='Omit only44--58.1ns acquisition; compare2 uses retained charge from18.1ns release'
    exact(DEST/'recipe_proposal.json',js(recipe))
    exact(DEST/'manifest.json',js(dict(status='local_single_variable_proposal_not_Spectre_compiled',
        parent_run_id='sar8audit-comp-kickback-tt-v2',
        parent_registered_recipe_sha256='033415e34b80fa7ed2bb8d4f2baf1a0582ca7e6772f5a1a118d3dabc79302db2',
        parent_input_hashes=manifest['input_hashes'],input_hashes={n:sha(blob) for n,blob in payload.items()},
        sole_electrical_change='Remove four CINIT knots defining acquisition44--58.1ns; all other statements byte-identical',
        removed_knots=DROP,metadata_only_adjustments='Release origin for compare2 and next actual acquisition for compare1',
        unchanged_inputs=['cells.scs','cdac_load.scs','initializer.va','kickback_analyze.py'],
        symbol_check=saved,total_input_bytes=sum(len(blob) for blob in payload.values()),
        resources_unchanged=recipe['resources']==old_recipe['resources'],
        frozen_as_baseline=False,remote_submitted=False,acceptance_pass=None,
        builder_sha256=sha(Path(__file__).read_bytes()))))
    print('LOCAL_HELD_SECOND_COMPARE',DEST,recipe['run_id'],'input_bytes',sum(len(blob) for blob in payload.values()))


if __name__=='__main__':prepare()
