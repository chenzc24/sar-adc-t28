"""Freeze four fixed-0.9 V MOS process/temperature cases from reviewed s100."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'verification/manual_adc/cdac_edge_v1/s100'
BASE = ROOT / 'verification/manual_adc/cdac_100ps_corners_v1'
CASES = [('ffcold', 'ff', -40), ('ffhot', 'ff', 125),
         ('sscold', 'ss', -40), ('sshot', 'ss', 125)]
SCOPE = ('CDAC reference MOS process/temperature screen at fixed 0.9 V; '
         'ideal capacitors, sampling conductance and other blocks. Not full-voltage PVT or ADC qualification.')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    template = json.loads((ROOT/'management/recipes/manual8-cdac-edge-s100-tt-v1.yaml').read_text())
    BASE.mkdir(exist_ok=True)
    manifest = {'source_run': 'manual8-cdac-edge-s100-tt-v1', 'scope': SCOPE, 'cases': {}}
    for key, corner, temp in CASES:
        dest = BASE/key
        dest.mkdir(exist_ok=False)
        for name in ['manual8_sample.va', 'manual8_cmp.va', 'manual8_sar.va',
                     'cdac_core.scs', 'wrappers.scs']:
            (dest/name).write_bytes((SRC/name).read_bytes())
            assert sha(dest/name) == sha(SRC/name)
        models = (SRC/'models.scs').read_text()
        assert models.count('section=ttmacro_mos_moscap') == 1
        changed = models.replace('section=ttmacro_mos_moscap', 'section='+corner+'macro_mos_moscap')
        (dest/'models.scs').write_text(changed)
        assert changed.replace('section='+corner+'macro_mos_moscap', 'section=ttmacro_mos_moscap') == models
        test = (SRC/'test.scs').read_text()
        assert test.count('temp=27 tnom=27') == 1
        changed = test.replace('temp=27 tnom=27', 'temp=%s tnom=27'%temp)
        (dest/'test.scs').write_text(changed)
        assert changed.replace('temp=%s tnom=27'%temp, 'temp=27 tnom=27') == test
        measure = json.loads((SRC/'measure.json').read_text())
        measure['scope'] = SCOPE
        measure['experiment'].update(case=key, corner=corner, temperature_c=temp)
        (dest/'measure.json').write_text(json.dumps(measure, indent=2)+'\n')
        recipe = copy.deepcopy(template)
        run = 'manual8-cdac-s100-'+key+'-v1'
        recipe.update(run_id=run, design_id='manual8_cdac_s100_corners_v1', qualification_scope=SCOPE)
        recipe['test_conditions'].update(corner=corner, temperature_c=temp,
                                         single_variable=measure['experiment'])
        for item in recipe['inputs']:
            if item['source'].startswith('verification/manual_adc/cdac_edge_v1/s100/'):
                item['source'] = (dest/item['name']).relative_to(ROOT).as_posix()
        (ROOT/'management/recipes'/ (run+'.yaml')).write_text(json.dumps(recipe, indent=2)+'\n')
        manifest['cases'][key] = {'run_id': run, 'corner': corner, 'temperature_c': temp, 'vdd_V': .9,
                                 'hashes': {p.name: sha(p) for p in sorted(dest.iterdir())},
                                 'input_diff_pass': True, 'allowed_changes': ['MOS section', 'temperature', 'metadata']}
    (BASE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
