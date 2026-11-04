"""Only promote the fifteen observed failing retained-core devices; local package."""
import copy
import json
import math
import re

import prepare_first_event as base
from prepare_io_local import is_mos
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'io_local_v1', OWN/'io_boundary_v2'
RUN = 'sar8audit-ctrl-iolocal-v1'
HASH = 'aa418b9919dce4576fe5013f09e6d1721c63df76b856e20e205a682d570682a7'
ANALYZER_SHA = 'fc57a31dac441f84dfcc8587a17c1247740ad6d40d2c43c04aaaf76b2daee2f6'
P = 'XDUT.XCTRL.XTIM.'
CDF = ROOT/'verification/sar8_physical_repair/io_cdf_audit.json'


def replacement(part, cdf):
    model = part['model'][0]+'ch_18_mac'
    pars = copy.deepcopy(cdf[model]['parameters'])
    if (pars['l'], pars['w'], pars['nf']) != ('150n', '320n', '1'):
        raise ValueError('Audited regular IO unit differs')
    width = re.search(r'\bw=(\S+)', part['parameters'])[1]
    multi = int(re.search(r'\bmulti=(\d+)', part['parameters'])[1])
    widths = {'500n': .5e-6, '1u': 1e-6, '2u': 2e-6}
    pars['multi'] = math.ceil(widths[width]*multi/320e-9)
    for key in ['spmb', 'spmt']:
        if pars[key] == '1.11111P':
            pars[key] = '1.11111e15'
    return model, ' '.join(k+'='+str(v) for k, v in pars.items())


def specialize(text, targets, cdf):
    blocks = base.cells(text)
    definitions = dict(blocks)
    def visit(master, prefix):
        if not any(k.startswith(prefix+'.') for k in targets):
            return master
        name = master if prefix == 'XDUT' else 'sar8io2_'+prefix.removeprefix('XDUT.').replace('.', '_')
        ports = blocks[master].replace('\\\n', ' ').splitlines()[0].split()[2:]
        lines = ['subckt '+name+' '+' '.join(ports)]
        for instance, original in base.parts(blocks[master]).items():
            path = prefix+'.'+instance
            part = copy.deepcopy(original)
            if part['model'] in blocks:
                part['model'] = visit(part['model'], path)
            if path in targets:
                part['model'], part['parameters'] = replacement(part, cdf)
            lines.append('    '+instance+' ('+' '.join(part['nodes'])+') '+part['model']+
                         (' '+part['parameters'] if part['parameters'] else ''))
        lines.append('ends '+name)
        definitions[name] = '\n'.join(lines)
        return name
    visit('sar8audit_ctrl_first_event', 'XDUT')
    reachable = set()
    def mark(master):
        if master in reachable:
            return
        reachable.add(master)
        for part in base.parts(definitions[master]).values():
            if part['model'] in definitions:
                mark(part['model'])
    mark('sar8audit_ctrl_first_event')
    return '\n\n'.join(v for k, v in definitions.items() if k in reachable)+'\n'


def main():
    _, _, result, source_m, proof = read_current_run(RUN, HASH)
    targets, reasons = set(), {}
    for name, item in source_m['io_local_experiment']['observed_mos'].items():
        failures = {suffix: result['full_history_voltage_stress'][label]
                    for suffix, label in item['six_pair_labels'].items()
                    if result['full_history_voltage_stress'][label]['over_limit_native_points']}
        if failures:
            if item['model'] not in ['nch_mac', 'pch_mac'] or item['changed']:
                raise ValueError('Selection must consist only of retained failing core MOS')
            targets.add(name)
            reasons[name] = failures
    if len(targets) != 15:
        raise ValueError('Expected exactly the fifteen measured core failures')
    source = (SRC/'dut.scs').read_text()
    ports = {'VDD': 'VDD!', 'VSS': '0'}
    old = base.flatten(source, 'sar8audit_ctrl_first_event', ports)
    cdf = json.loads(CDF.read_bytes())
    text = specialize(source, targets, cdf)
    new = base.flatten(text, 'sar8audit_ctrl_first_event', ports)
    if set(new) != set(old) or {k for k in new if new[k] != old[k]} != targets:
        raise ValueError('Unexpected leaf set or edits beyond measured fifteen')
    for name in targets:
        model, pars = replacement(old[name], cdf)
        if new[name] != dict(model=model, parameters=pars, nodes=old[name]['nodes']):
            raise ValueError('Device geometry/terminal change outside specification')
    m = copy.deepcopy(source_m)
    m['baseline_io_local_experiment'] = m.pop('io_local_experiment')
    m['stress_voltage_pairs'] = {label: source_m['stress_voltage_pairs'][label] for label in
        ['MP1_VSG', 'MP1_VGD', 'INV_MN_VGS', 'N_versus_old_core_rail_DIAGNOSTIC']}
    watched = {}
    for name, part in sorted(new.items()):
        if not is_mos(part):
            continue
        model = part['model']
        if model in ['nch_mac', 'pch_mac']:
            limit = .99
        elif model in ['nch_18_mac', 'pch_18_mac', 'nch_na18_mac']:
            limit = 1.98
        else:
            raise ValueError('No inherited voltage screen for '+model)
        d, g, s, b = part['nodes']
        short = name.removeprefix(P)
        prefix = short.rsplit('.', 1)[-1] if short in ['X020.X000.MN0', 'X020.X000.MN1'] else short
        watched[name] = dict(model=model, nodes=part['nodes'], changed_this_candidate=name in targets,
                              limit_abs_v=limit, six_pair_labels={})
        for suffix, (a, z) in dict(VGS=(g, s), VGD=(g, d), VDS=(d, s), VGB=(g, b), VDB=(d, b), VSB=(s, b)).items():
            label = prefix+'_'+suffix
            m['stress_voltage_pairs'][label] = dict(positive_node=a, negative_node=z, limit_abs_v=limit)
            watched[name]['six_pair_labels'][suffix] = label
    if len(watched) != 101 or len(m['stress_voltage_pairs']) != 610:
        raise ValueError('Expected all101 fixture MOS and610 observed pairs/aliases')
    # Existing native saves contain all voltages/currents: expand compact observation only.
    m['diagnostic_voltage_columns'] = [x.lower() for x in m['voltage_saves']]
    m['diagnostic_current_columns'] = [x.lower() for x in m['current_saves']]
    m['critical_kcl_nodes'] = sorted(m['kcl_terms'])
    m['scope'] = 'FF cold boundary correction:only15 measured failing core devices promoted; all101 existing fixture MOS observed, not all converted or ADC-qualified'
    m['terminal_voltage_policy']['coverage'] = 'All six pairs for all101 existing fixture MOS, including unchanged logic/comparator/conditional loads; observation expansion does not imply circuit replacement or qualification.'
    m['boundary_correction_v2'] = dict(base_run=RUN, base_recipe_sha256=HASH,
        selected_failure_evidence=reasons, changed_this_candidate=sorted(targets), watched_mos=watched,
        unchanged_leaf_count=sum(new[k] == old[k] for k in new),
        previous15_IO_devices_unchanged=True, unfailed_previous_core_devices_not_promoted=True,
        no_added_removed_rewired_leaf=True, original_passives_and_all_FF_PWL_preserved=True,
        all_fixture_MOS_measured_not_all_replaced=True, full_cycle_PVT_noise_mismatch_PEX_unqualified=True,
        SS_requires_valid_SS_boundary_not_retagged_FF=True)
    analyzer = OWN/'full_gate_analyze.py'
    if base.digest(analyzer.read_bytes()) != ANALYZER_SHA:
        raise ValueError('Frozen analyzer changed')
    base.exact_write(DEST/'dut.scs', text)
    base.write_json(DEST/'measurement.json', m)
    deck = (SRC/'test.scs').read_text()
    deck = re.sub(r'\A//[^\n]*\n', '// Boundary correction:15 additional measured failures use regularIO; no wiring/stimulus change.\n', deck, count=1)
    if '\n'.join(x for x in deck.splitlines() if not x.startswith('//')) != '\n'.join(
            x for x in (SRC/'test.scs').read_text().splitlines() if not x.startswith('//')):
        raise ValueError('Electrical deck changed')
    base.exact_write(DEST/'test.scs', deck)
    for p in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/p.name, p.read_bytes())
    replay = re.findall(r'\bfile="([^"]+)"', text)
    if len(replay) != 11 or any((DEST/x).read_bytes() != (SRC/x).read_bytes() for x in replay):
        raise ValueError('Replay histories changed')
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    recipe.update(run_id='sar8audit-ctrl-ioboundary-v2', design_id='sar8_control_local_IO_boundary_v2', qualification_scope=m['scope'])
    files = [('test.scs', DEST/'test.scs'), ('dut.scs', DEST/'dut.scs'),
             ('measurement.json', DEST/'measurement.json'), ('full_gate_analyze.py', analyzer)]
    files += [('pwl/'+p.name, p) for p in sorted((DEST/'pwl').glob('*.pwl'))]
    recipe['inputs'] = [dict(name=name, source=p.relative_to(ROOT).as_posix(), sha256=base.digest(p.read_bytes())) for name, p in files]
    base.write_json(DEST/'recipe.suggested.yaml', recipe)
    manifest = dict(base_run=RUN, base_recipe_sha256=HASH, base_proof=proof,
        reason_by_changed_instance=reasons,
        changed_devices={k: dict(before=old[k], after=new[k]) for k in sorted(targets)},
        changed_MOS=15, cumulative_changed_from_stackorder=30, unchanged_leaves=116,
        total_MOS=101, total_passives=19, observed_MOS=101, simultaneous_pairs=610,
        raw_voltage_saves=len(m['voltage_saves']), raw_current_saves=len(m['current_saves']),
        diagnostic_voltages=len(m['diagnostic_voltage_columns']), diagnostic_currents=len(m['diagnostic_current_columns']),
        critical_KCL=len(m['critical_kcl_nodes']), original_FF_PWL_byte_identical=11,
        all_terminal_nodes_and_prior15_IO_unchanged=True,
        shared_analyzer_sha256=ANALYZER_SHA, CDF_record_sha256=base.digest(CDF.read_bytes()),
        declared_input_files=len(files), declared_package_bytes=sum(p.stat().st_size for _, p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        simulation_completed=False, qualification_pass_inferred=False, remote_operations=False)
    base.write_json(DEST/'change_manifest.json', manifest)
    base.write_json(DEST/'freeze.json', dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=name, bytes=p.stat().st_size, sha256=base.digest(p.read_bytes())) for name, p in files]))
    print(json.dumps({k: v for k, v in manifest.items() if k not in ['base_proof', 'reason_by_changed_instance', 'changed_devices']}, indent=2))


if __name__ == '__main__':
    main()
