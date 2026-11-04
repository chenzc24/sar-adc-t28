"""Prepare one local CMID multiplicity experiment; never register or run it."""
import copy
import difflib
import json
import re

import prepare_first_event as base
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC = OWN / 'mp1_floor_v1'
DEST = OWN / 'cmid_half_v1'
RUN = 'sar8audit-ctrl-mp1floor-v1'
HASH = '3813f5e217e5d2b360b75fa11d46603b3ca0bbeb8e6e56380f56caa2b0fb529f'
CELL = 'sar8audit_nand2_mp1shape'
TARGET = 'XDUT.XCTRL.XTIM.X020.X000.CMID'
ANALYZER_SHA = 'fc57a31dac441f84dfcc8587a17c1247740ad6d40d2c43c04aaaf76b2daee2f6'


def main():
    _, _, _, _, proof = read_current_run(RUN, HASH)
    old_bytes = (SRC / 'dut.scs').read_bytes()
    old = old_bytes.decode('utf-8')
    block = base.cells(old)[CELL]
    part = base.parts(block)['CMID']
    witness = base.parts(base.cells(old)['sar8p_sr'])['CQB']
    old_parameters = part['parameters']
    new_parameters, count = re.subn(r'\bmulti=2\b', 'multi=1', old_parameters)
    if (count != 1 or part['model'] != 'cfmom_2t'
            or witness['model'] != part['model'] or witness['parameters'] != new_parameters):
        raise ValueError('Expected exact already-used MOM unit geometry and multi=1 witness')
    # Locate only the private cell CMID statement; no shared NAND/global replacement.
    match = re.search(r'(?m)^\s*CMID\s+\([^)]*\)[^\n]*', block)
    if not match:
        raise ValueError('Private CMID statement missing')
    changed_line, count = re.subn(r'\bmulti=2\b', 'multi=1', match[0])
    if count != 1:
        raise ValueError('CMID multiplicity not on expected statement')
    new_block = block[:match.start()] + changed_line + block[match.end():]
    if old.count(block) != 1:
        raise ValueError('Private cell is not unique')
    new = old.replace(block, new_block, 1)
    old_leaf = base.flatten(old, 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
    new_leaf = base.flatten(new, 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
    if set(old_leaf) != set(new_leaf):
        raise ValueError('Instances added or removed')
    changed = [k for k in old_leaf if old_leaf[k] != new_leaf[k]]
    expected = copy.deepcopy(old_leaf[TARGET])
    expected['parameters'] = new_parameters
    if changed != [TARGET] or new_leaf[TARGET] != expected:
        raise ValueError('Electrical change exceeds only the X020 CMID multiplicity')
    # Verify precisely one ASCII byte changes; all whitespace and other source remain.
    new_bytes = new.encode('utf-8')
    differing = [i for i, (a, b) in enumerate(zip(old_bytes, new_bytes)) if a != b]
    if len(new_bytes) != len(old_bytes) or len(differing) != 1:
        raise ValueError('DUT must differ by exactly one byte')
    if (old_bytes[differing[0]], new_bytes[differing[0]]) != (ord('2'), ord('1')):
        raise ValueError('Unexpected changed byte')

    measurement = json.loads((SRC / 'measurement.json').read_bytes())
    baseline_measurement = copy.deepcopy(measurement)
    measurement['scope'] = ('Single private X020 CMID multi2->1 on the positive-floor '
                            'conditional-load fixture; FF-cold first event, not ADC qualification')
    measurement['cmid_multiplicity_experiment'] = dict(
        base_run=RUN, base_recipe_sha256=HASH, target_instance=TARGET,
        old_multiplicity=2, new_multiplicity=1,
        legal_geometry_witness='sar8p_sr.CQB; identical cfmom_2t model and parameters at multi=1',
        single_variable='Only target CMID multiplicity; no MOS, resistor, supply or PWL change',
        hypothesis='Less stored MID charge may establish upper-MN0 absorption from N earlier',
        pass_not_inferred=True,
        retained_observation_scope='All native CMI logs, terminal-current KCL, voltage extrema, '
            'three configured simultaneous full-history stress pairs and five source energies',
        required_checks=['N overshoot and all native CMI warnings',
            'Existing MP1 VSG/VGD and restoring INV NMOS VGS full-history stress',
            'MID decay, MP1 drain injection versus upper MN0 drain absorption',
            'QUIET rising/falling counts, edge delay and source power/energy',
            'External sampling window/closing edge unchanged; first-event scope only'])
    electrical_keys = set(baseline_measurement) - {'scope'}
    if any(measurement[k] != baseline_measurement[k] for k in electrical_keys):
        raise ValueError('Observer/incidence or old measurement contract changed')
    analyzer = OWN / 'full_gate_analyze.py'
    if base.digest(analyzer.read_bytes()) != ANALYZER_SHA:
        raise ValueError('Frozen all-time stress/energy observer changed')
    base.exact_write(DEST / 'dut.scs', new_bytes)
    base.exact_write(DEST / 'test.scs', (SRC / 'test.scs').read_bytes())
    pwl = sorted((SRC / 'pwl').glob('*.pwl'))
    if len(pwl) != 11:
        raise ValueError('Expected all eleven frozen source histories')
    for path in pwl:
        base.exact_write(DEST / 'pwl' / path.name, path.read_bytes())
    base.write_json(DEST / 'measurement.json', measurement)
    if len(list((DEST / 'pwl').iterdir())) != 11:
        raise ValueError('Unexpected replay files')
    for path in pwl:
        if (DEST / 'pwl' / path.name).read_bytes() != path.read_bytes():
            raise ValueError('PWL bytes changed')
    # Resolve all eleven actual Spectre paths from the managed inputs cwd.
    deck = (DEST / 'test.scs').read_text()
    refs = re.findall(r'\bfile="([^"]+)"', new + '\n' + deck)
    if set(refs) != {'pwl/' + p.name for p in pwl} or len(refs) != 11:
        raise ValueError('Wrong replay paths')
    if any(not (DEST / ref).is_file() for ref in refs):
        raise ValueError('Replay path does not resolve')
    recipe = json.loads((SRC / 'recipe.suggested.yaml').read_bytes())
    recipe.update(run_id='sar8audit-ctrl-cmidhalf-v1',
                  design_id='sar8_control_private_X020_CMID_half',
                  qualification_scope=measurement['scope'])
    files = [('test.scs', DEST / 'test.scs'), ('dut.scs', DEST / 'dut.scs'),
             ('measurement.json', DEST / 'measurement.json'), ('full_gate_analyze.py', analyzer)]
    files += [('pwl/' + p.name, DEST / 'pwl' / p.name) for p in pwl]
    recipe['inputs'] = [dict(source=p.relative_to(ROOT).as_posix(), name=name,
                             sha256=base.digest(p.read_bytes())) for name, p in files]
    base.write_json(DEST / 'recipe.suggested.yaml', recipe)
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
        fromfile='frozen_mp1_floor_v1/dut.scs', tofile='cmid_half_v1/dut.scs', n=2))
    base.exact_write(DEST / 'electrical_change.diff', diff)
    manifest = dict(base_run=RUN, base_recipe_sha256=HASH, base_proof=proof,
        target_instance=TARGET, before=old_leaf[TARGET], after=new_leaf[TARGET],
        legal_geometry_witness=dict(cell='sar8p_sr', instance='CQB', model=witness['model'],
                                    parameters=witness['parameters']),
        changed_leaf_count=1, unchanged_leaf_count=len(old_leaf)-1,
        added_leaf_count=0, removed_leaf_count=0, differing_dut_bytes=1,
        all_original_MOS_resistors_and_other_capacitors_unchanged=True,
        test_deck_byte_identical=True, native_PWL_files_byte_identical=11,
        observer_byte_identical_sha256=ANALYZER_SHA,
        total_MOS=sum(p['model'].startswith(('nch_', 'pch_')) for p in new_leaf.values()),
        total_passive=sum(p['model'] in ('cfmom_2t', 'rupolym') for p in new_leaf.values()),
        voltage_saves=len(measurement['voltage_saves']), current_saves=len(measurement['current_saves']),
        critical_kcl_nodes=len(measurement['critical_kcl_nodes']),
        declared_input_files=len(files), declared_package_bytes=sum(p.stat().st_size for _, p in files),
        recipe_file_sha256=base.digest((DEST / 'recipe.suggested.yaml').read_bytes()),
        netlist_only=True, remote_operations=False, simulation_completed=False,
        qualification_pass_inferred=False)
    base.write_json(DEST / 'change_manifest.json', manifest)
    base.write_json(DEST / 'freeze.json', dict(
        recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=name, sha256=base.digest(p.read_bytes()), bytes=p.stat().st_size)
                for name, p in files]))
    print(json.dumps({k: v for k, v in manifest.items()
                      if k not in ['base_proof', 'before', 'after', 'legal_geometry_witness']}, indent=2))


if __name__ == '__main__':
    main()
