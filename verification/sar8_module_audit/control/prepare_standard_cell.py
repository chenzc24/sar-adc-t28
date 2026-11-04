"""Prepare only the accepted FF X020 standard-cell comparison, locally."""
import copy
import json
import re

import prepare_first_event as base
import gate_observer_support as observer_config
from review_both_result import read_current_run

OWN, ROOT = base.OWN, base.ROOT
SRC, DEST = OWN/'sn_load_variants_v1/both', OWN/'standard_cell_v1'
META = OWN.parent/'standard_cells'
RUN = 'sar8audit-ctrl-snload-both-v1'
HASH = '66cda5e5a9c65de39abee30125b33fe39f8926729145adbe5d25999b0bcc802c'
NEW_RUN = 'sar8audit-ctrl-stdcell-ff-v1'
OBSERVER_SHA = 'fc57a31dac441f84dfcc8587a17c1247740ad6d40d2c43c04aaaf76b2daee2f6'
SPI_SHA = 'b7b366bff01b86fbe6c9728426a1643255476f5e5e63f79b9ff14ffaa2b2fc0e'
P = 'XDUT.XCTRL.XTIM.'
TARGET = P+'X020'
CELLS = {'ND2D1BWP12T30P140': ['A1','A2','ZN','VDD','VSS'],
         'INVD1BWP12T30P140': ['I','ZN','VDD','VSS']}


def metadata():
    probe = json.loads((META/'two_cell_probe_metadata.json').read_bytes())
    masters = json.loads((META/'model_master_metadata.json').read_bytes())
    ports = json.loads((META/'package_metadata.json').read_bytes())
    truth = json.loads((META/'two_cell_logic_check.json').read_bytes())
    if probe['sha256'] != SPI_SHA or probe['bytes'] != 2452584:
        raise ValueError('Parent-verified original SPICE identity differs')
    for name, pins in CELLS.items():
        if ports['subcircuits'][name]['pins'] != pins:
            raise ValueError('Verified standard-cell port order differs')
        for mos in probe['cells'][name]:
            if any(mos['dimension_form'][d]['explicit_suffix'] != 'n' for d in ['l','w']):
                raise ValueError('Explicit foundry dimension unit changed')
    if [len(probe['cells'][name]) for name in CELLS] != [4,2]:
        raise ValueError('Expected exactly NAND4 plus INV2 native MOS')
    for item in masters['definitions']:
        if (item['type'] != 'inline subckt' or item['ports'] != ['n1','n2','n3','n4']
                or item['terminal_roles'] != ['D','G','S','B']):
            raise ValueError('Verified model master/port type differs')
    if set(x['master'] for x in masters['definitions']) != {'nch_mac','pch_mac'}:
        raise ValueError('Missing model master metadata')
    return probe, masters, truth


def replace_x020(text):
    blocks = base.cells(text)
    timing = blocks['sar8audit_timing']
    old = 'X020 (Q1 LIVE VDD VSS QUIET) sar8p_and2'
    if timing.count(old) != 1:
        raise ValueError('Exact original X020 boundary missing')
    changed = timing.replace(old, 'X020 (Q1 LIVE VDD VSS QUIET) sar8audit_and2_tcb')
    wrapper = ('subckt sar8audit_and2_tcb A B VDD VSS Y\n'
               '    X000 (B A N VDD VSS) ND2D1BWP12T30P140\n'
               '    X001 (N Y VDD VSS) INVD1BWP12T30P140\n'
               'ends sar8audit_and2_tcb\n')
    return text.replace(timing, changed)+'\n'+wrapper


def expanded_leaves(text, probe):
    """Expand only connectivity metadata for measurement; never emit a PDK body."""
    leaves = base.flatten(text, 'sar8audit_ctrl_first_event', {'VDD':'VDD!','VSS':'0'})
    library = {}
    for path, part in list(leaves.items()):
        if part['model'] not in CELLS:
            continue
        bindings = dict(zip(CELLS[part['model']], part['nodes']))
        del leaves[path]
        for item in probe['cells'][part['model']]:
            key = path+'.'+item['instance']
            nodes = [bindings.get(item[t], path+'.'+item[t]) for t in ['D','G','S','B']]
            leaves[key] = dict(model=item['master'], nodes=nodes,
                               parameters='EXTERNAL_FOUNDRY_PARAMETERS_NOT_COPIED')
            library[key] = dict(cell=part['model'], master=item['master'], nodes=nodes,
                requested_numeric_terminal_currents=[key+':'+str(i) for i in range(1,5)],
                known_inline_primitive=item['master'],
                primitive_probe_path_not_assumed=key+'.'+item['master'])
    if len(library) != 6:
        raise ValueError('Exactly six foundry MOS must replace X020')
    return leaves, library


def measurement(old, leaves, library):
    m = copy.deepcopy(old)
    m.update(observer_config.observations(P+'LIVE'))
    catalog = {}
    mos = {}
    for path, part in leaves.items():
        is_mos = part['model'].startswith(('nch_', 'pch_'))
        labels = ['D','G','S','B'] if is_mos else ['PLUS','MINUS']
        for i, node in enumerate(part['nodes'], 1):
            if is_mos or node != '0':
                catalog[path+':'+str(i)] = dict(instance=path, terminal=labels[i-1],
                    port=i, node=node, kcl_coefficient=1)
        if not is_mos:
            continue
        d,g,s,b = part['nodes']
        record = dict(model=part['model'], nodes=part['nodes'],
                      group='standard_cell' if path in library else 'retained_core', six_pair_labels={})
        for suffix, (a,z) in dict(VGS=(g,s),VGD=(g,d),VDS=(d,s),VGB=(g,b),VDB=(d,b),VSB=(s,b)).items():
            label = path.removeprefix(P)+'_'+suffix
            m['stress_voltage_pairs'][label] = dict(positive_node=a, negative_node=z, limit_abs_v=.99)
            record['six_pair_labels'][suffix] = label
        mos[path] = record
    catalog['VVDD:1'] = dict(instance='VVDD',terminal='PLUS',port=1,node='VDD!',kcl_coefficient=1)
    m['terminal_current_catalog'] = catalog
    m['voltage_saves'] = sorted({n for part in leaves.values() for n in part['nodes'] if n != '0'})
    m['current_saves'] = sorted(catalog)
    m['kcl_terms'] = {n:[k.lower() for k,v in catalog.items() if v['node']==n]
                      for n in m['voltage_saves'] if n != 'VDD!'}
    m['critical_kcl_nodes'] = sorted(m['kcl_terms'])
    m['diagnostic_voltage_columns'] = [n.lower() for n in m['voltage_saves']]
    m['diagnostic_current_columns'] = [n.lower() for n in m['current_saves']]
    # Only imposed histories are initial witnesses. Changed internal states are observations.
    m['old_internal_initial_reference_diagnostic_only'] = m['expected_initial_state']
    imposed = ['xdut.sample_int','xdut.xctrl.phi_w','xdut.phi_u','xdut.active',
               'xdut.xctrl.xtim.dec','xdut.topp','xdut.topn','vdd!']
    m['expected_initial_state'] = dict(time_s=0, values_v={n:old['expected_initial_state']['values_v'][n] for n in imposed})
    for branch in ['10','14']:
        for node in ['N','MID']:
            first = (SRC/'pwl'/('bias_x0'+branch+'_'+node.lower()+'.pwl')).read_text().splitlines()[0].split()
            if float(first[0]) != 0:
                raise ValueError('Bias history does not begin at zero')
            m['expected_initial_state']['values_v'][(P+'SNLOAD'+branch+'_'+node).lower()] = float(first[1])
    for node, direction in {'Q1':-1,'X020.N':-1,'QUIET_D':1,'CLOCK_SET':1,'CLOCK_Q':1}.items():
        m['expected_edges'][(P+node).lower()] = dict(direction=direction,time_s=[],method='Measure actual native crossing; no imposed edge target')
    m['expected_edges']['xdut.cmp_clk'] = dict(direction=1,time_s=[],method='Missing before source stop stays unobserved')
    m['proposed_reproduction_contract']['status'] = 'comparison_only_not_a_source_peak_reproduction_gate'
    m['scope'] = 'FF0.99V/-40C first-event whole-X020 library NAND+INV replacement; conditioned SN diffusion replay; not full ADC/SS qualification'
    m['standard_cell_experiment'] = dict(base_run=RUN,base_recipe_sha256=HASH,
        library_mos=library,observed_mos=mos,removed_old_internal_capacitor=TARGET+'.X000.CMID',
        LIVE_to_NAND_A1=True,Q1_to_NAND_A2=True,library_geometry_changed=False,
        retained_inputs_loads_and_eleven_histories_unchanged=True,
        current_binding='Numeric 1/2/3/4 on actual MM instance, following existing mac convention; first native elaboration must verify. No nested primitive or zero substitution.',
        SS_boundary_available=False,acceptance_pass=None)
    m['terminal_voltage_policy'] = dict(limit_abs_v=.99,
        method='Six simultaneous native terminal pairs per101 MOS, zero-to-END, plus three legacy voltage aliases.',
        junctions='Signed VDB/VSB retained. Absolute screen is not forward-junction or lifetime qualification.',
        standard_cells_are_core_not_IO=True)
    if len(mos) != 101 or len(m['stress_voltage_pairs']) != 609:
        raise ValueError('Expected101 MOS and606 physical pairs plus3 legacy aliases')
    return m


def main():
    _,_,_,_,proof = read_current_run(RUN,HASH)
    source_recipe = json.loads((SRC/'recipe.suggested.yaml').read_bytes())
    for item in source_recipe['inputs']:
        if base.digest((ROOT/item['source']).read_bytes()) != item['sha256']:
            raise ValueError('Frozen source input differs')
    probe,masters,truth = metadata()
    text = (SRC/'dut.scs').read_text()
    changed = replace_x020(text)
    old = base.flatten(text,'sar8audit_ctrl_first_event',{'VDD':'VDD!','VSS':'0'})
    new,library = expanded_leaves(changed,probe)
    removed = {k for k in old if k.startswith(TARGET+'.')}
    if len(removed) != 7 or set(old)-set(new) != removed or set(new)-set(old) != set(library):
        raise ValueError('Replacement exceeds original six-MOS/one-cap X020 implementation')
    if any(new[k] != old[k] for k in set(old)-removed):
        raise ValueError('Upstream driver, passive, load or source changed')
    m = measurement(json.loads((SRC/'measurement.json').read_bytes()),new,library)
    analyzer = OWN/'full_gate_analyze.py'
    if base.digest(analyzer.read_bytes()) != OBSERVER_SHA:
        raise ValueError('Frozen native reducer changed')
    deck = (SRC/'test.scs').read_text()
    strip = lambda s: ''.join(line for line in s.splitlines(True) if not line.startswith(('save ','//')))
    prefix = 'simulator lang=spice\n.include "'+probe['file']+'"\nsimulator lang=spectre\n'
    anchor = 'include "dut.scs"\n'
    if strip(deck).count(anchor) != 1:
        raise ValueError('DUT include anchor differs')
    generated = strip(deck).replace(anchor,prefix+anchor)
    generated += ''.join('save '+name+'\n' for name in sorted(m['voltage_saves']+m['current_saves']))
    if strip(generated).replace(prefix,'',1) != strip(deck):
        raise ValueError('Solver/models/scale/source/window changed beyond external include')
    base.exact_write(DEST/'dut.scs',changed)
    base.exact_write(DEST/'test.scs',generated)
    base.write_json(DEST/'measurement.json',m)
    for p in sorted((SRC/'pwl').glob('*.pwl')):
        base.exact_write(DEST/'pwl'/p.name,p.read_bytes())
    paths = re.findall(r'\bfile="([^"]+)"',changed)
    if len(paths) != 11 or any((DEST/p).read_bytes() != (SRC/p).read_bytes() for p in paths):
        raise ValueError('Original eleven PWL histories differ')
    external = dict(file=probe['file'],sha256=probe['sha256'],bytes=probe['bytes'],
        parser_mode='spice include then restore spectre',
        identity_timing='Analyzer verifies post-simulation. Parent must verify same SHA/size read-only before managed dispatch; not a TOCTOU proof.',
        metadata_inputs={name:dict(sha256=base.digest((META/src).read_bytes()),bytes=(META/src).stat().st_size)
            for name,src in [('probe_metadata.json','two_cell_probe_metadata.json'),('master_metadata.json','model_master_metadata.json')]},
        current_probe_compatibility='Untested SPICE-M inline binding; require all declared native traces. Missing traces fail. Do not rewrite original file or M prefix.',
        external_model_child=masters['child'],model_file_body_copied=False)
    base.write_json(DEST/'external_library.json',external)
    recipe = copy.deepcopy(source_recipe)
    recipe.update(run_id=NEW_RUN,design_id='sar8_control_X020_native_standard_cell',
                  analyzer='standard_cell_analyze.py',qualification_scope=m['scope'])
    files = [(n,DEST/n) for n in ['test.scs','dut.scs','measurement.json','external_library.json']]
    files += [('full_gate_analyze.py',analyzer),('standard_cell_analyze.py',OWN/'standard_cell_analyze.py'),
              ('probe_metadata.json',META/'two_cell_probe_metadata.json'),('master_metadata.json',META/'model_master_metadata.json')]
    files += [('pwl/'+p.name,p) for p in sorted((DEST/'pwl').glob('*.pwl'))]
    recipe['inputs'] = [dict(source=p.relative_to(ROOT).as_posix(),name=n,sha256=base.digest(p.read_bytes())) for n,p in files]
    base.write_json(DEST/'recipe.suggested.yaml',recipe)
    manifest = dict(base_run=RUN,base_recipe_sha256=HASH,base_proof=proof,
        replacement=dict(removed=sorted(removed),added=sorted(library),unchanged_leaf_count=len(old)-len(removed)),
        foundry_reference=external,library_mos=library,total_MOS=101,
        total_passive=sum(v['model'] in ['cfmom_2t','rupolym'] for v in new.values()),
        voltage_saves=len(m['voltage_saves']),current_saves=len(m['current_saves']),
        critical_KCL=len(m['critical_kcl_nodes']),simultaneous_pairs=len(m['stress_voltage_pairs']),
        original_PWL_byte_identical=11,non_save_deck_only_external_include_changed=True,
        frozen_observer_sha256=OBSERVER_SHA,
        metadata_sources={name:base.digest((META/name).read_bytes()) for name in
            ['two_cell_probe_metadata.json','model_master_metadata.json','package_metadata.json','two_cell_logic_check.json']},
        declared_input_files=len(files),declared_package_bytes=sum(p.stat().st_size for _,p in files),
        recipe_file_sha256=base.digest((DEST/'recipe.suggested.yaml').read_bytes()),
        local_preparation_only=True,remote_operations=False,simulation_completed=False,qualification_pass_inferred=False)
    base.write_json(DEST/'change_manifest.json',manifest)
    base.write_json(DEST/'freeze.json',dict(recipe_sha256=manifest['recipe_file_sha256'],
        inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files]))
    print(json.dumps({k:v for k,v in manifest.items() if k not in
        ['base_proof','foundry_reference','library_mos','metadata_sources','replacement']},indent=2))


if __name__ == '__main__':
    main()
