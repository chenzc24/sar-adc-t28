"""Prepare conditional original-MOS SN load experiments from checked native bias.

No remote operations. Missing collected bias is reported, never replaced by a
rail, guessed capacitance or generated endpoint. Registered inputs stay intact.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np
import yaml

import prepare_first_event as base
import supplement_native_export as supplement

OWN, ROOT = base.OWN, base.ROOT
DEST = OWN / 'sn_load_variants_v1'
P = 'XDUT.XCTRL.XTIM.'
SOURCE = 'sar8fix-loaded-both-ffcold'
FIXTURE = 'sar8audit-ctrl-first-event-v1'
SOURCE_SHA = '5fa0009c9440314865e346dd7713f57012a24f5b06c41644ac8260ed13b8b325'
FIXTURE_SHA = '587e794d928d6f25fa64ce7749d1d613fd0dd6fe3e1e46b7554b1dd1efb74ae7'
EXPORT_SHA = {
    'sar8audit-ctrl-source-sn-v1':'3d1cc7bc36e51363159025e12f5b282335e1d6886190126a517f62bb3ce202d0',
    'sar8audit-ctrl-fixture-sn-v1':'512786dc52e02927814401dc2e46771a0d267b833c1923897971141f69932680',
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def read_supplement(run_id, source_id, expected_sha):
    folder = ROOT / 'output/managed_execution/runs' / run_id / 'collected'
    receipt_path = folder / 'collection_receipt.json'
    receipt = json.loads(receipt_path.read_bytes())
    record = yaml.safe_load((ROOT/'management/runs'/(run_id+'.yaml')).read_text())
    recipe = record['recipe']
    if (record['recipe_hash'] != EXPORT_SHA[run_id]
            or sha(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode()) != EXPORT_SHA[run_id]
            or recipe['run_id'] != run_id or recipe['source']['run_id'] != source_id
            or recipe['source']['recipe_hash'] != expected_sha):
        raise ValueError('Supplement analysis recipe/source binding differs')
    if receipt['skipped']:
        raise ValueError('Supplement collection incomplete')
    data = {}
    for item in receipt['files']:
        relative = Path(item['name'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe supplement member')
        path = folder / relative
        if not path.exists() or sha(path.read_bytes()) != item['sha256']:
            path = path.with_name(path.stem + '.' + item['sha256'][:12] + path.suffix)
        blob = path.read_bytes()
        if sha(blob) != item['sha256'] or len(blob) != item['bytes']:
            raise ValueError('Supplement receipt SHA/size mismatch')
        data[item['name']] = blob
    if sum(len(x) for x in data.values()) != receipt['total_bytes']:
        raise ValueError('Supplement receipt total mismatch')
    result = json.loads(data['derived/result.json'])
    if (not result['analysis_complete'] or result['source_run_id'] != source_id
            or result['source_recipe_hash'] != expected_sha
            or not result['source_completed_simulation_verified'] or result['simulation_started']):
        raise ValueError('Supplement source/result identity differs')
    for name, item in result['files'].items():
        blob = data['derived/' + name]
        if sha(blob) != item['sha256'] or len(blob) != item['bytes']:
            raise ValueError('Supplement nested file mismatch')
    state = json.loads(data['analysis.state.json'])
    if state['status'] != 'complete' or state['exit_code'] != 0:
        raise ValueError('Supplement analysis incomplete')
    provenance = json.loads(data['derived/source_readonly_provenance.json'])
    if (not provenance['source_readonly_checks_pass'] or provenance['recipe_hash'] != expected_sha
            or provenance['raw_stat_before'] != provenance['raw_stat_after']):
        raise ValueError('Supplement source-readonly evidence differs')
    names = [item['name'] for item in json.loads(data['derived/boundary.columns.json'])['columns']]
    expected_names = ['time'] + supplement.SELECTIONS[source_id]
    if names != expected_names:
        raise ValueError('Supplement voltage selection differs')
    values = np.frombuffer(data['derived/boundary.native.bin'], '<f8').reshape((-1, len(names)))
    meta = json.loads(data['derived/native_export.meta.json'])
    if (len(values) != meta['points'] or not np.isfinite(values).all()
            or values[0, 0] != 0 or not np.all(np.diff(values[:, 0]) > 0)):
        raise ValueError('Invalid supplementary native table')
    config = json.loads((folder.parent/'inputs/supplement_manifest.json').read_bytes())
    if supplement.check_coverage(meta,config) != result['coverage']:
        raise ValueError('Supplement coverage proof differs')
    initial = json.loads(data['derived/initial_state.json'])
    if any(initial['values_v'][name] != values[0, i] for i, name in enumerate(names) if i):
        raise ValueError('Supplement initial witness differs')
    if (values[-1, 0] != result['coverage']['actual_last_exported_native_time_s']
            or result['coverage']['fabricated_endpoint']):
        raise ValueError('Supplement actual endpoint differs')
    proof = dict(export_run=run_id, source_run=source_id, source_recipe_sha256=expected_sha,
        receipt_sha256=sha(receipt_path.read_bytes()), receipt_bytes=receipt['total_bytes'],
        native_points=len(values), initial_state=initial, coverage=result['coverage'])
    return values, names, proof


def frozen_base():
    record = yaml.safe_load((ROOT / 'management/runs' / (FIXTURE + '.yaml')).read_text())
    recipe = record['recipe']
    if sha(json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()) != FIXTURE_SHA:
        raise ValueError('Frozen baseline recipe changed')
    for item in recipe['files']:
        if sha((ROOT / item['source']).read_bytes()) != item['sha256']:
            raise ValueError('Frozen v1 input changed: ' + item['name'])
    source_path = ROOT / 'output/managed_execution/runs' / SOURCE / 'inputs/dut.scs'
    identity = json.loads((OWN / 'first_event_v1/device_identity.json').read_bytes())
    if sha(source_path.read_bytes()) != identity['source_hashes']['dut.scs']:
        raise ValueError('Original source DUT changed')
    return (OWN/'first_event_v1/dut.scs').read_text(), (OWN/'first_event_v1/test.scs').read_text(), \
        json.loads((OWN/'first_event_v1/measurement.json').read_bytes()), source_path.read_text()


def make_case(branches, values, names, proof, target):
    if tuple(branches) not in [('10',), ('14',), ('10', '14')]:
        raise ValueError('Only independent X010/X014 SN-load experiments are supported')
    if (names != ['time'] + supplement.SELECTIONS[SOURCE] or values[0, 0] != 0
            or not np.isfinite(values).all() or not np.all(np.diff(values[:, 0]) > 0)
            or values[-1, 0] < 41.2e-9):
        raise ValueError('Complete checked original native bias histories required')
    dut, deck, measure, original = frozen_base()
    original_parts = base.parts(base.cells(original)['sar8p_nand2'])
    additions, new_catalog, device_map, pwl_files = [], {}, {}, {}
    old_nodes = set(measure['voltage_saves'])
    for branch in branches:
        for suffix, voltage in [('N', 'n'), ('MID', 'x000.mid')]:
            node = 'SNLOAD' + branch + '_' + suffix
            path = 'pwl/bias_x0' + branch + '_' + suffix.lower() + '.pwl'
            signal = 'xdut.xctrl.xtim.x0' + branch + '.' + voltage
            pwl_files[path] = ''.join('%.17g %.17g\n' % (row[0], row[names.index(signal)]) for row in values).encode()
            label = 'VBIAS' + branch + '_' + suffix
            additions.append('    %s (%s VSS) vsource type=pwl file="%s"' % (label, node, path))
            new_catalog[P + label + ':1'] = dict(instance=P+label, terminal='PLUS', port=1,
                                                node=P+node, kcl_coefficient=1)
        for leaf, pin_names in [('MP1', ['SNLOAD'+branch+'_N', 'SN', 'VDD', 'VDD']),
                                ('MN1', ['SNLOAD'+branch+'_MID', 'SN', 'VSS', 'VSS'])]:
            part = original_parts[leaf]
            label = 'MSNLOAD' + branch + '_' + leaf
            additions.append('    %s (%s) %s %s' % (label, ' '.join(pin_names), part['model'], part['parameters']))
            nodes = [('VDD!' if n == 'VDD' else '0' if n == 'VSS' else P+n) for n in pin_names]
            device_map[P+label] = dict(original_instance=P+'X0'+branch+'.X000.'+leaf,
                original_gate_node=P+'SN', conditional_bias_nodes=nodes,
                model=part['model'], parameters=part['parameters'], all_original_instance_parameters_unchanged=True)
            for port, (terminal, node) in enumerate(zip(['D','G','S','B'], nodes), 1):
                new_catalog[P+label+':'+str(port)] = dict(instance=P+label, terminal=terminal,
                    port=port, node=node, kcl_coefficient=1)
    anchor = 'ends sar8audit_timing'
    if dut.count(anchor) != 1:
        raise ValueError('Unexpected frozen timing boundary')
    dut = dut.replace(anchor, '\n'.join(additions)+'\n'+anchor)
    old_leaf = base.flatten((OWN/'first_event_v1/dut.scs').read_text(),
                            'sar8audit_ctrl_first_event', {'VDD':'VDD!', 'VSS':'0'})
    new_leaf = base.flatten(dut, 'sar8audit_ctrl_first_event', {'VDD':'VDD!', 'VSS':'0'})
    if any(new_leaf.get(k) != v for k, v in old_leaf.items()):
        raise ValueError('A frozen native instance or upstream source changed')
    extra_sources = [v for k,v in new_leaf.items() if k not in old_leaf and v['model']=='vsource']
    if any(v['nodes'][0] in old_nodes for v in extra_sources):
        raise ValueError('New bias source clamps an original active node')
    measure = copy.deepcopy(measure)
    measure['scope'] = 'Conditional original-MOS SN gate-load sensitivity; not complete X010/X014 logic restoration or ADC qualification'
    measure['terminal_current_catalog'].update(new_catalog)
    catalog = measure['terminal_current_catalog']
    measure['current_saves'] = sorted(catalog)
    measure['voltage_saves'] = sorted({item['node'] for item in catalog.values() if item['node'] != '0'})
    measure['kcl_terms'] = {node:[trace.lower() for trace,item in catalog.items() if item['node']==node]
                            for node in measure['voltage_saves'] if node != 'VDD!'}
    new_nodes = sorted(set(measure['voltage_saves']) - old_nodes)
    measure['critical_kcl_nodes'] += [P+'SN'] + new_nodes
    measure['diagnostic_voltage_columns'] += [(P+'SN').lower()] + [n.lower() for n in new_nodes]
    measure['diagnostic_current_columns'] = sorted(set(measure['diagnostic_current_columns']) |
        set(sum((measure['kcl_terms'][node] for node in [P+'SN']+new_nodes), [])))
    measure['expected_initial_state']['values_v'][(P+'SN').lower()] = float(values[0, names.index((P+'SN').lower())])
    measure['expected_edges'][(P+'SN').lower()] = dict(direction=1,
        time_s=base.edge_time(values[:,0], values[:,names.index((P+'SN').lower())], .99, True),
        method='Source-native halfrail event; interpolation only for event time')
    stop = min(measure['source_history_stop_s'], float(values[-1,0]))
    measure['source_history_stop_s'] = stop
    measure['diagnostic_stop_s'] = stop
    measure['SN_load_experiment'] = dict(branches=list(branches), source_evidence=proof,
        original_devices=device_map, conditioning='Drain diffusion biases follow unchanged original source-native voltage histories; SN gate is naturally driven by the retained inverter.',
        limitations=['Not full X010/X014 gate logic or reciprocal drain feedback.',
            'No fitted capacitor, device resizing, forced SN, waveform smoothing or external sampling change.',
            'Ideal diffusion-bias sources exchange energy; this fixture does not qualify whole-ADC power.',
            'Record the original 1mV fidelity screen and all warnings; it does not mechanically block this sensitivity experiment.'],
        stop_policy='End at available real source-native history if earlier; no fabricated bias endpoint')
    measure['boundary_differences'].append('Conditional PDK MOS replicas restore selected missing SN gate terminals with measured diffusion bias; original v1 feedback cuts remain.')
    deck = re.sub(r'(tran_first tran stop=)\S+', lambda m:m[1]+'%.17g'%stop, deck)
    saved = set(re.findall(r'(?m)^save\s+(\S+)', deck))
    deck += ''.join('save '+name+'\n' for name in sorted(set(measure['voltage_saves']+measure['current_saves'])-saved))
    base.exact_write(target/'dut.scs', dut)
    base.exact_write(target/'test.scs', deck)
    for path in (OWN/'first_event_v1/pwl').iterdir():
        base.exact_write(target/'pwl'/path.name, path.read_bytes())
    for relative, blob in pwl_files.items():
        base.exact_write(target/relative, blob)
    base.write_json(target/'measurement.json', measure)
    identity = dict(base_run=FIXTURE, base_recipe_sha256=FIXTURE_SHA, original_source_run=SOURCE,
        source_export_evidence=proof, added_MOS=2*len(branches), native_MOS=97+2*len(branches), native_passives=18,
        new_conditional_bias_sources=2*len(branches), original_v1_leaf_identity_unchanged=True,
        retained_active_outputs_forced=[], new_load_device_map=device_map, stop_s=stop,
        base_pwl_bytes_unchanged=True, added_bias_native_points=len(values))
    base.write_json(target/'device_identity.json', identity)
    files = [('test.scs', target/'test.scs'), ('dut.scs',target/'dut.scs'),
        ('measurement.json',target/'measurement.json'), ('first_event_analyze.py',OWN/'first_event_analyze.py')]
    files += [('pwl/'+p.name,p) for p in sorted((target/'pwl').iterdir())]
    suffix = 'both' if len(branches)==2 else 'x0'+branches[0]
    recipe = dict(schema_version=1, run_id='sar8audit-ctrl-snload-'+suffix+'-v1',
        design_id='sar8_control_conditional_SN_MOS_load', entry='test.scs',analyzer='first_event_analyze.py',
        inputs=[dict(source=p.relative_to(ROOT).as_posix(),name=name,sha256=sha(p.read_bytes())) for name,p in files],
        expected_stop_s=stop,summary_signals=[(P+'SN').lower(),(P+'LIVE').lower(),(P+'X020.N').lower()],
        qualification_scope=measure['scope'],oa_parity='netlist_only',
        test_conditions=dict(corner='ff',vdd=.99,temperature_c=-40,noise=False,mismatch=False,PEX=False),
        spectre_args=['+preset=cx','+mt=1','+lqtimeout','60','-preset_override'],
        resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,
            analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=1024,
            simulation_wall_seconds=900,analysis_wall_seconds=600,queue_timeout_seconds=600))
    base.write_json(target/'recipe.suggested.yaml', recipe)
    return identity


def main():
    expected = [('sar8audit-ctrl-source-sn-v1',SOURCE,SOURCE_SHA),
                ('sar8audit-ctrl-fixture-sn-v1',FIXTURE,FIXTURE_SHA)]
    missing = [run for run,_,_ in expected if not (ROOT/'output/managed_execution/runs'/run/'collected/collection_receipt.json').exists()]
    if missing:
        print(json.dumps(dict(status='awaiting_real_collected_bias',missing=missing,
                              variants_generated=False,remote_operations=False)))
        return
    source, names, proof = read_supplement(*expected[0])
    fixture, fixture_names, fixture_proof = read_supplement(*expected[1])
    DEST.mkdir(exist_ok=True)
    base.write_json(DEST/'source_bias_evidence.json',dict(source=proof,fixture=fixture_proof))
    identities = [make_case(branches,source,names,proof,DEST/name) for name,branches in
                  [('x010_only',('10',)),('x014_only',('14',)),('both',('10','14'))]]
    print(json.dumps(dict(status='local_variants_ready',native_MOS=[x['native_MOS'] for x in identities],
                         variants_generated=True,remote_operations=False)))


if __name__ == '__main__':
    main()
