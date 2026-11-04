"""Local 15-MOS rated-primitive scheme; no remote work or shared-source edits."""
import copy
import json
import math
import re

import prepare_first_event as base
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'stack_order_v1', OWN/'io_local_v1'
RUN = 'sar8audit-ctrl-stackorder-v1'
HASH = 'f7fdea18a1eb32890b5dd3688952ac6e14e91d8d05106bc8dfcd3d85305a82e3'
ANALYZER_SHA = 'fc57a31dac441f84dfcc8587a17c1247740ad6d40d2c43c04aaaf76b2daee2f6'
P = 'XDUT.XCTRL.XTIM.'
CDF = ROOT/'verification/sar8_physical_repair/io_cdf_audit.json'
REMOVED = {P+'X020.X000.RPU'+str(i) for i in range(3)}


def is_mos(part):
    return part['model'].startswith(('nch_', 'pch_'))


def choose_targets(leaves):
    targets = {k for k, v in leaves.items() if is_mos(v) and (
        k.startswith(P+'X020.') or k.startswith(P+'X001.X001.')
        or k.startswith(P+'X019.X001.') or k.startswith(P+'XD_QUIET_D.X006.')
        or k == P+'XD_QUIET_D.MP_CLEAR' or k in [P+'X022.X000.MP0', P+'X022.X000.MN0'])}
    if len(targets) != 15:
        raise ValueError('Expected exactly fifteen directly exposed MOS')
    return targets


def io_parameters(part, cdf):
    model = part['model'][0]+'ch_18_mac'
    pars = copy.deepcopy(cdf[model]['parameters'])
    if (pars['l'], pars['w'], pars['nf']) != ('150n', '320n', '1'):
        raise ValueError('Existing audited regular-IO unit geometry changed')
    width = re.search(r'\bw=(\S+)', part['parameters'])[1]
    old_multi = re.search(r'\bmulti=(\d+)', part['parameters'])[1]
    factor = {'500n': .5e-6, '1u': 1e-6, '3u': 3e-6}[width]*int(old_multi)
    pars['multi'] = math.ceil(factor/320e-9)
    for key in ['spmb', 'spmt']:
        if pars[key] == '1.11111P':
            pars[key] = '1.11111e15'
    return model, ' '.join(k+'='+str(v) for k, v in pars.items())


def specialize(text, targets, cdf):
    blocks = base.cells(text)
    definitions = dict(blocks)
    edits = targets | REMOVED
    def visit(master, prefix):
        if not any(k.startswith(prefix+'.') for k in edits):
            return master
        name = master if prefix == 'XDUT' else 'sar8io_'+prefix.removeprefix('XDUT.').replace('.', '_')
        header = blocks[master].replace('\\\n', ' ').splitlines()[0].split()[2:]
        lines = ['subckt '+name+' '+' '.join(header)]
        for instance, original in base.parts(blocks[master]).items():
            path = prefix+'.'+instance
            if path in REMOVED:
                continue
            part = copy.deepcopy(original)
            if part['model'] in blocks:
                part['model'] = visit(part['model'], path)
            if path in targets:
                part['model'], part['parameters'] = io_parameters(part, cdf)
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
    return '\n\n'.join(block for name, block in definitions.items() if name in reachable)+'\n'


def measurement(original, leaves, targets):
    m = copy.deepcopy(original)
    catalog = {}
    for name, part in leaves.items():
        labels = ['D', 'G', 'S', 'B'] if is_mos(part) else ['PLUS', 'MINUS']
        for index, node in enumerate(part['nodes'], 1):
            if is_mos(part) or node != '0':
                catalog[name+':'+str(index)] = dict(instance=name, terminal=labels[index-1],
                    port=index, node=node, kcl_coefficient=1)
    catalog['VVDD:1'] = dict(instance='VVDD', terminal='PLUS', port=1, node='VDD!', kcl_coefficient=1)
    m['terminal_current_catalog'] = catalog
    m['voltage_saves'] = sorted({node for part in leaves.values() for node in part['nodes'] if node != '0'})
    m['current_saves'] = sorted(catalog)
    m['kcl_terms'] = {node: [trace.lower() for trace, item in catalog.items() if item['node'] == node]
                      for node in m['voltage_saves'] if node != 'VDD!'}
    nodes = {n for name in targets for n in leaves[name]['nodes'] if n not in ['0', 'VDD!']}
    nodes |= {P+'XD_QUIET_D.RC0', P+'XD_QUIET_D.RC1'}
    exposed = {name for name, part in leaves.items() if is_mos(part) and set(part['nodes']) & nodes}
    # Complete the adjacent primitive cells, including their lower stack devices.
    parents = {name.rsplit('.', 1)[0] for name in exposed}
    exposed = {name for name, part in leaves.items() if is_mos(part) and name.rsplit('.', 1)[0] in parents}
    if len(exposed) != 32 or not targets <= exposed:
        raise ValueError('Expected fifteen changed and seventeen adjacent MOS')
    observed_nodes = {n for name in exposed for n in leaves[name]['nodes'] if n not in ['0', 'VDD!']}
    m['critical_kcl_nodes'] = sorted((set(m['critical_kcl_nodes']) & set(m['kcl_terms'])) | observed_nodes)
    currents = {trace.lower() for trace, item in catalog.items() if item['instance'] in exposed}
    currents |= set(sum((m['kcl_terms'][node] for node in m['critical_kcl_nodes']), []))
    m['diagnostic_current_columns'] = sorted(currents | {'vvdd:1'})
    m['diagnostic_voltage_columns'] = [node.lower() for node in m['voltage_saves']]
    # Retain original labels for direct comparisons, with the candidate model's screen.
    for pair in m['stress_voltage_pairs'].values():
        pair['limit_abs_v'] = 1.98
    observations = {}
    for name in sorted(exposed):
        part = leaves[name]
        limit = 1.98 if part['model'] in ['nch_18_mac', 'pch_18_mac'] else .99
        d, g, s, b = part['nodes']
        short = name.removeprefix(P)
        prefix = short.rsplit('.', 1)[-1] if short in ['X020.X000.MN0', 'X020.X000.MN1'] else short
        observations[name] = dict(model=part['model'], nodes=part['nodes'], changed=name in targets,
                                  limit_abs_v=limit, six_pair_labels={})
        for suffix, (a, z) in dict(VGS=(g, s), VGD=(g, d), VDS=(d, s), VGB=(g, b), VDB=(d, b), VSB=(s, b)).items():
            label = prefix+'_'+suffix
            m['stress_voltage_pairs'][label] = dict(positive_node=a, negative_node=z, limit_abs_v=limit)
            observations[name]['six_pair_labels'][suffix] = label
    m['stress_voltage_pairs']['N_versus_old_core_rail_DIAGNOSTIC'] = dict(
        positive_node=P+'X020.N', negative_node='0', limit_abs_v=.99)
    if len(m['stress_voltage_pairs']) != 196:
        raise ValueError('Unexpected stress coverage/alias count')
    m['terminal_voltage_policy'] = dict(
        method='All six pairs per changed/exposed MOS at simultaneous native time, zero-to-END. No independent extrema subtraction.',
        junctions='VDB=D-B/VSB=S-B signed. NMOS positive and PMOS negative mean reverse bias; signed extrema retained without an invented forward-bias acceptance threshold.',
        limits='Core0.99V; regular18mac1.98V provisional screen reused from existing io_screen/loaded records, not authenticated lifetime/SOA qualification. Native CMI retained. Separate N0.99V field is a historical rail diagnostic.',
        local_boundary_only=True)
    m['baseline_stack_order_experiment'] = m.pop('stack_order_experiment')
    m['scope'] = 'FF cold local rated-CMOS scheme:15 MOS class/default-unit changes plus removal of three DC pullups; conditioned first event, not ADC/PVT qualification'
    m['io_local_experiment'] = dict(base_run=RUN, base_recipe_sha256=HASH,
        classification='Scheme-level device-class/default-unit and DC-divider removal, not one sizing cause',
        changed_mos=sorted(targets), removed_pullups=sorted(REMOVED), observed_mos=observations,
        stack_order_and_all_terminal_nodes_preserved=True, original_Cu_and_RSLEW_preserved=True,
        old_internal_initial_state_match_required=False,
        FF_conditioned_PWL_valid_for_this_case_only=True, SS_actual_boundary_unavailable=True,
        no_new_bias_supply_clock_or_initial_condition=True,
        remaining_checks=['All changed and adjacent MOS six pairs, signed junctions and all native CMI',
            'N/LIVE/Q1/QUIET and receiver/RC branch native currents and KCL',
            'Low-state current, five source energies, edge counts/latencies and any missing transition before actual source-history stop',
            'Core neighbors may still fail; no boundary-wide or whole-ADC pass assumed',
            'SS0.81V actual-history/load case must be built separately, not by retagging FF PWL'])
    return m, observations


def main():
    _, _, _, _, proof = read_current_run(RUN, HASH)
    text = (SRC/'dut.scs').read_text()
    old = base.flatten(text, 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
    targets = choose_targets(old)
    cdf = json.loads(CDF.read_bytes())
    changed = specialize(text, targets, cdf)
    new = base.flatten(changed, 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
    if set(old)-set(new) != REMOVED or set(new)-set(old):
        raise ValueError('Only three pullups may be removed')
    if {k for k in new if new[k] != old[k]} != targets:
        raise ValueError('Electrical change exceeds exact fifteen MOS')
    for name in new:
        if name in targets:
            model, pars = io_parameters(old[name], cdf)
            if new[name] != dict(model=model, nodes=old[name]['nodes'], parameters=pars):
                raise ValueError('IO node/geometry mapping differs')
        elif new[name] != old[name]:
            raise ValueError('Unchanged leaf changed')
    oldm = json.loads((SRC/'measurement.json').read_bytes())
    m, boundary = measurement(oldm, new, targets)
    analyzer = OWN/'full_gate_analyze.py'
    if base.digest(analyzer.read_bytes()) != ANALYZER_SHA:
        raise ValueError('Frozen observer changed')
    base.exact_write(DEST/'dut.scs', changed)
    base.write_json(DEST/'measurement.json', m)
    source_deck = (SRC/'test.scs').read_text()
    strip = lambda s: ''.join(line for line in s.splitlines(True) if not line.startswith(('save ', '//')))
    deck = '// Local 15-MOS rated boundary; remove three DC pullups.\n'+strip(source_deck)
    deck += ''.join('save '+name+'\n' for name in sorted(m['voltage_saves']+m['current_saves']))
    if strip(deck) != strip(source_deck):
        raise ValueError('Non-save electrical deck changed')
    base.exact_write(DEST/'test.scs', deck)
    for p in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/p.name, p.read_bytes())
    paths = re.findall(r'\bfile="([^"]+)"', changed)
    if len(paths) != 11 or any((DEST/p).read_bytes() != (SRC/p).read_bytes() for p in paths):
        raise ValueError('Original eleven replay histories changed')
    recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    recipe.update(run_id='sar8audit-ctrl-iolocal-v1', design_id='sar8_control_local_rated_CMOS',
                  qualification_scope=m['scope'])
    files = [('test.scs', DEST/'test.scs'), ('dut.scs', DEST/'dut.scs'),
             ('measurement.json', DEST/'measurement.json'), ('full_gate_analyze.py', analyzer)]
    files += [('pwl/'+p.name, p) for p in sorted((DEST/'pwl').glob('*.pwl'))]
    recipe['inputs'] = [dict(source=p.relative_to(ROOT).as_posix(), name=name, sha256=base.digest(p.read_bytes())) for name, p in files]
    base.write_json(DEST/'recipe.suggested.yaml', recipe)
    fo4 = {}
    for corner in ['ffcold', 'sscold']:
        path = ROOT/'verification/sar8_physical_repair'/('sar8fix-ioscreen-'+corner+'_analysis.json')
        record = json.loads(path.read_bytes())
        fo4[corner] = dict(source=path.relative_to(ROOT).as_posix(), sha256=base.digest(path.read_bytes()),
            supply_v=record['vdd'], scope='Existing FO4 only, not this loaded interface',
            delays_ps={family: {k: v for k, v in record['blocks'][family].items() if k.startswith('fo4_')}
                       for family in ['core', '18']})
    manifest = dict(base_run=RUN, base_recipe_sha256=HASH, base_proof=proof,
        electrical_change=dict(changed_MOS={k: dict(before=old[k], after=new[k]) for k in sorted(targets)},
            removed_pullups={k: old[k] for k in sorted(REMOVED)},
            unchanged_leaf_count=sum(new[k] == old[k] for k in new)),
        CDF_record=dict(source=CDF.relative_to(ROOT).as_posix(), sha256=base.digest(CDF.read_bytes())),
        boundary=boundary, old_FO4=fo4,
        observed_MOS=len(boundary), changed_MOS=len(targets), removed_pullups=3,
        total_MOS=sum(is_mos(p) for p in new.values()),
        total_passive=sum(p['model'] in ['cfmom_2t', 'rupolym'] for p in new.values()),
        voltage_saves=len(m['voltage_saves']), current_saves=len(m['current_saves']),
        critical_KCL=len(m['critical_kcl_nodes']), diagnostic_currents=len(m['diagnostic_current_columns']),
        simultaneous_pairs=len(m['stress_voltage_pairs']), original_PWL_byte_identical=11,
        non_save_noncomment_deck_identical=True, analyzer_unchanged_sha256=ANALYZER_SHA,
        declared_input_files=len(files), declared_package_bytes=sum(p.stat().st_size for _, p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        simulation_completed=False, qualification_pass_inferred=False, remote_operations=False)
    base.write_json(DEST/'change_manifest.json', manifest)
    base.write_json(DEST/'freeze.json', dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=name, bytes=p.stat().st_size, sha256=base.digest(p.read_bytes())) for name, p in files]))
    print(json.dumps({k: v for k, v in manifest.items() if k not in
        ['base_proof', 'electrical_change', 'boundary', 'CDF_record', 'old_FO4']}, indent=2))


if __name__ == '__main__':
    main()
