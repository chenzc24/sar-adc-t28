"""Only swap the two private NAND NMOS gates; prepare local immutable inputs."""
import copy
import json
import re

import prepare_first_event as base
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'cmid_half_v1', OWN/'stack_order_v1'
SOURCE_RUN = 'sar8audit-ctrl-cmidhalf-v1'
SOURCE_HASH = '4a7e6299c079bec1b798b68ea076c72482005a04c273b39a7824fd039c972069'
ANALYZER_SHA = 'fc57a31dac441f84dfcc8587a17c1247740ad6d40d2c43c04aaaf76b2daee2f6'
P = 'XDUT.XCTRL.XTIM.'
TARGETS = [P+'X020.X000.MN0', P+'X020.X000.MN1']


def build_measurement(original, leaves):
    m = copy.deepcopy(original)
    cat = m['terminal_current_catalog']
    moved = {}
    for trace, item in cat.items():
        instance = item['instance']
        if instance not in leaves:
            if instance != 'VVDD':
                raise ValueError('Unknown catalog instance: '+instance)
            continue
        node = leaves[instance]['nodes'][item['port']-1]
        if node != item['node']:
            moved[trace] = dict(before=item['node'], after=node, terminal=item['terminal'])
            item['node'] = node
    expected_moved = {
        TARGETS[0]+':2': dict(before=P+'Q1', after=P+'LIVE', terminal='G'),
        TARGETS[1]+':2': dict(before=P+'LIVE', after=P+'Q1', terminal='G'),
    }
    if moved != expected_moved:
        raise ValueError('Unexpected gate-current incidence change')
    m['kcl_terms'] = {node: [trace.lower() for trace, part in cat.items() if part['node'] == node]
                      for node in m['voltage_saves'] if node != 'VDD!'}
    if P+'Q1' not in m['critical_kcl_nodes']:
        m['critical_kcl_nodes'].append(P+'Q1')
    extra = set(m['kcl_terms'][P+'Q1']+m['kcl_terms'][P+'LIVE'])
    for instance in TARGETS+[P+'X020.X000.MP1']:
        extra.update((instance+':'+str(port)).lower() for port in [1, 2, 3, 4])
    m['diagnostic_current_columns'] = sorted(set(m['diagnostic_current_columns']) | extra)
    for node in [P+'LIVE', P+'Q1', P+'X020.N', P+'X020.X000.MID']:
        if node.lower() not in m['diagnostic_voltage_columns']:
            m['diagnostic_voltage_columns'].append(node.lower())
    selected = {x.lower() for x in m['current_saves']}
    if not set(m['diagnostic_current_columns']) <= selected:
        raise ValueError('Diagnostic current not saved')
    for instance in TARGETS:
        d, g, s, b = leaves[instance]['nodes']
        pairs = dict(VGS=(g, s), VGD=(g, d), VDS=(d, s), VGB=(g, b), VDB=(d, b), VSB=(s, b))
        label = instance.rsplit('.', 1)[-1]
        for suffix, (positive, negative) in pairs.items():
            m['stress_voltage_pairs'][label+'_'+suffix] = dict(
                positive_node=positive, negative_node=negative, limit_abs_v=.99)
    if len(m['stress_voltage_pairs']) != 15:
        raise ValueError('Expected original three plus twelve NMOS terminal pairs')
    m['terminal_voltage_policy'] = dict(
        method='Every difference uses simultaneous native values over zero-to-END; never independent extrema subtraction.',
        junctions='VDB=drain-body and VSB=source-body; positive is reverse bias for these NMOS junctions. Signed minima/maxima and times retained.',
        screen='0.99V absolute diagnostic screen for the configured terminal differences; not a newly qualified forward-junction limit. Native CMI and signed negative excursions remain authoritative evidence.',
        coverage='All six pairwise terminal differences for each of X020 MN0/MN1, plus the old three observations; not all-MOS circuit qualification.')
    # Move former single-variable descriptions into explicitly historical context.
    m['baseline_experiment_history'] = {key: m.pop(key) for key in
        ['local_suppression_experiment', 'gate_floor_experiment', 'cmid_multiplicity_experiment']}
    old_initial = copy.deepcopy(m['expected_initial_state'])
    old_contract = copy.deepcopy(m['proposed_reproduction_contract'])
    imposed = set(base.REPLAYS.values()) | {'vdd!'}
    boundary_initial = {key: value for key, value in old_initial['values_v'].items() if key in imposed}
    if set(boundary_initial) != imposed:
        raise ValueError('Expected seven imposed PWL boundary witnesses plus VDD')
    m['historical_source_reference'] = dict(
        initial_state=old_initial, peak=copy.deepcopy(m['expected_native_peak']),
        reproduction_contract=old_contract,
        interpretation='Historical observations only. Changed MID/internal initial state and changed peak/timing are intended responses, not reproduction gates.')
    m['expected_initial_state'] = dict(time_s=0, values_v=boundary_initial,
        scope='Imposed replay boundary voltages and VDD only; internal initial state is naturally solved, not constrained to historical values.')
    m['proposed_reproduction_contract'] = dict(status='intentional_topology_change_not_reproduction',
        internal_initial_state_equality_required=False, historical_peak_match_required=False,
        edge_time_match_required=False, critical_kcl_peak_abs_a=old_contract['critical_kcl_peak_abs_a'],
        rationale='Compare stress, currents/charge, native KCL, measured edge counts/order/delay and power. Acceptance remains unset; all original CMI retained.')
    m['scope'] = 'Only private X020 NMOS gate-order swap on CMID-half/floor fixture; FF-cold first event, no full-cycle or ADC qualification'
    m['stack_order_experiment'] = dict(base_run=SOURCE_RUN, base_recipe_sha256=SOURCE_HASH,
        changed_gate_incidence=moved, only_two_NMOS_gate_nodes_changed=True,
        same_MOS_geometry_and_models=True, CMID_and_floor_branch_unchanged=True,
        initial_MID_change_expected=True, forced_initial_condition_added=False,
        DC_floor_power_still_unresolved=True,
        remaining_checks=['Full-history original and twelve added simultaneous voltage differences; retain native CMI',
            'New LIVE-to-N total MN0 gate/drain current exchange versus MP1 drain injection',
            'Native N/MID/LIVE/Q1 KCL, source energies/current and QUIET counts/delay',
            'Q1 transitions/reset/full-cycle later; unchanged external sampling window/closing edge'])
    return m, moved


def main():
    _, _, _, _, proof = read_current_run(SOURCE_RUN, SOURCE_HASH)
    original_bytes = (SRC/'dut.scs').read_bytes()
    original = original_bytes.decode('utf-8')
    cell = 'sar8audit_nand2_mp1shape'
    block = base.cells(original)[cell]
    changed_block = block
    for before, after in [('MN0 (Y A MID VSS)', 'MN0 (Y B MID VSS)'),
                          ('MN1 (MID B VSS VSS)', 'MN1 (MID A VSS VSS)')]:
        if changed_block.count(before) != 1:
            raise ValueError('Private NAND connection anchor differs')
        changed_block = changed_block.replace(before, after, 1)
    if original.count(block) != 1:
        raise ValueError('Private cell is not unique')
    changed = original.replace(block, changed_block, 1)
    changed_bytes = changed.encode('utf-8')
    differing = [(a, b) for a, b in zip(original_bytes, changed_bytes) if a != b]
    if len(original_bytes) != len(changed_bytes) or sorted(differing) != [(65, 66), (66, 65)]:
        raise ValueError('Expected exactly two gate-label bytes to swap')
    ports = {'VDD': 'VDD!', 'VSS': '0'}
    old_leaf = base.flatten(original, 'sar8audit_ctrl_first_event', ports)
    new_leaf = base.flatten(changed, 'sar8audit_ctrl_first_event', ports)
    if set(old_leaf) != set(new_leaf):
        raise ValueError('Leaf set changed')
    changed_instances = {k for k in old_leaf if old_leaf[k] != new_leaf[k]}
    if changed_instances != set(TARGETS):
        raise ValueError('Change escaped target two NMOS')
    for instance, gate in zip(TARGETS, [P+'LIVE', P+'Q1']):
        expected = copy.deepcopy(old_leaf[instance])
        expected['nodes'][1] = gate
        if new_leaf[instance] != expected:
            raise ValueError('Non-gate terminal or parameter changed')
    original_measurement = json.loads((SRC/'measurement.json').read_bytes())
    m, moved = build_measurement(original_measurement, new_leaf)
    analyzer = OWN/'full_gate_analyze.py'
    if base.digest(analyzer.read_bytes()) != ANALYZER_SHA:
        raise ValueError('Frozen generic analyzer changed')
    base.exact_write(DEST/'dut.scs', changed_bytes)
    base.exact_write(DEST/'test.scs', (SRC/'test.scs').read_bytes())
    for source in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/source.name, source.read_bytes())
    base.write_json(DEST/'measurement.json', m)
    pwl = sorted((DEST/'pwl').iterdir())
    if len(pwl) != 11 or any(p.read_bytes() != (SRC/'pwl'/p.name).read_bytes() for p in pwl):
        raise ValueError('Replay inputs differ')
    deck = (DEST/'test.scs').read_text()
    saves = set(re.findall(r'(?m)^save\s+(\S+)', deck))
    if not set(m['voltage_saves']+m['current_saves']) <= saves:
        raise ValueError('Actual Spectre save list missing probes')
    refs = re.findall(r'\bfile="([^"]+)"', changed+'\n'+deck)
    if set(refs) != {'pwl/'+p.name for p in pwl} or len(refs) != 11:
        raise ValueError('Unexpected PWL path')
    if any(not (DEST/ref).is_file() for ref in refs):
        raise ValueError('PWL path missing from managed inputs cwd')
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    recipe.update(run_id='sar8audit-ctrl-stackorder-v1', design_id='sar8_control_X020_NMOS_stack_order',
                  qualification_scope=m['scope'])
    files = [('test.scs', DEST/'test.scs'), ('dut.scs', DEST/'dut.scs'),
             ('measurement.json', DEST/'measurement.json'), ('full_gate_analyze.py', analyzer)]
    files += [('pwl/'+p.name, p) for p in pwl]
    recipe['inputs'] = [dict(source=p.relative_to(ROOT).as_posix(), name=name,
                             sha256=base.digest(p.read_bytes())) for name, p in files]
    base.write_json(DEST/'recipe.suggested.yaml', recipe)
    old_lines, new_lines = original.splitlines(True), changed.splitlines(True)
    changed_lines = [(i, a, b) for i, (a, b) in enumerate(zip(old_lines, new_lines), 1) if a != b]
    if len(old_lines) != len(new_lines) or len(changed_lines) != 2:
        raise ValueError('Expected exactly two changed gate statement lines')
    # Avoid repeated identical MOS-parameter lines confusing sequence alignment.
    exact_diff = '--- frozen_cmid_half_v1/dut.scs\n+++ stack_order_v1/dut.scs\n'
    exact_diff += ''.join('@@ -%d +%d @@\n-%s+%s'%(i, i, a, b) for i, a, b in changed_lines)
    base.exact_write(DEST/'electrical_change.diff', exact_diff)
    manifest = dict(base_run=SOURCE_RUN, base_recipe_sha256=SOURCE_HASH, base_proof=proof,
        changed_instances={k: dict(before=old_leaf[k], after=new_leaf[k]) for k in TARGETS},
        moved_current_catalog_terms=moved, changed_leaf_count=2, unchanged_leaf_count=len(old_leaf)-2,
        added_or_removed_leaf_count=0, differing_dut_bytes=2,
        all_models_sizes_and_non_gate_nodes_unchanged=True, private_cell_only=True,
        test_deck_byte_identical=True, original_PWL_byte_identical_count=11,
        shared_analyzer_byte_identical_sha256=ANALYZER_SHA, new_wrapper_required=False,
        voltage_saves=len(m['voltage_saves']), current_saves=len(m['current_saves']),
        critical_kcl_nodes=len(m['critical_kcl_nodes']), diagnostic_currents=len(m['diagnostic_current_columns']),
        simultaneous_full_history_stress_pairs=len(m['stress_voltage_pairs']),
        total_MOS=sum(p['model'].startswith(('nch_', 'pch_')) for p in new_leaf.values()),
        total_passive=sum(p['model'] in ('cfmom_2t', 'rupolym') for p in new_leaf.values()),
        initial_internal_state_equality_required=False, declared_input_files=len(files),
        declared_package_bytes=sum(p.stat().st_size for _, p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        remote_operations=False, simulation_completed=False, qualification_pass_inferred=False)
    base.write_json(DEST/'change_manifest.json', manifest)
    base.write_json(DEST/'freeze.json', dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=name, sha256=base.digest(p.read_bytes()), bytes=p.stat().st_size) for name, p in files]))
    print(json.dumps({k: v for k, v in manifest.items() if k not in ['base_proof', 'changed_instances']}, indent=2))


if __name__ == '__main__':
    main()
