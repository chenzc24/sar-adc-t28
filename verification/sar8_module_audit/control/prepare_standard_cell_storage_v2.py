"""Measurement-only storage v2. Preserve all v1 electrical/solver inputs."""
from __future__ import annotations
import copy
import json
from pathlib import Path

import prepare_first_event as base

OWN,ROOT=base.OWN,base.ROOT
V1=OWN/'standard_cell_full_v1'
OUT=OWN/'standard_cell_storage_v2'


def read(path):return json.loads(Path(path).read_bytes())


def selected_currents(cfg,boundaries):
    selected={p['current'] for p in cfg['source_power_ports'].values()}
    groups=dict(external_sources=sorted(selected),SR=[],RC=[])
    for observer in cfg['storage']['observers']:
        if observer['kind']!='SR':continue
        path='XDUT.X'+observer['name']
        sr=[]
        for gate in ['X001','X002','X003']:
            sr += [path+'.'+gate+'.XLIB.'+mos+':1' for mos in ['MM1','MM2','MM4','MM9']]
        sr += [path+'.X000.XLIB.'+mos+':1' for mos in ['MM0','MM1']]
        sr += [path+'.'+gate+'.XLIB.MM4:3' for gate in ['X002','X003']]
        sr += [path+'.CQB:1']
        selected.update(sr);groups['SR']+=sr
    for load in boundaries['boundaries']:
        if not load['complete_RC_block_retained']:continue
        path=load['replica']
        rc=[path+'.'+part+':1' for part in ['R0','R1','C0','C1','MN_CLEAR','MP_CLEAR']]
        selected.update(rc);groups['RC']+=rc
    if not selected<=set(cfg['current_saves']) or len(selected)>100:
        raise ValueError('Unverified/oversized current selection')
    return sorted(selected),groups


def measurement(source,boundaries):
    cfg=copy.deepcopy(source);selected,groups=selected_currents(source,boundaries)
    cfg['scope']='All26 isolated storage contexts; all980 voltage histories/11220 terminal pairs,89 selected source/SR/RC currents, no complete KCL; not complete Miller/ADC qualification'
    cfg['current_saves']=selected
    cfg['terminal_current_catalog']={k:v for k,v in source['terminal_current_catalog'].items() if k in selected}
    cfg['kcl_terms']={};cfg['critical_kcl_nodes']=[]
    cfg['storage'].update(raw_all_actual_MOS_ports=False,full_history_all_KCL=False)
    cfg['selected_current_coverage']=dict(selected_current_names=list(selected),selected_current_count=len(selected),
        original_v1_current_count=len(source['current_saves']),unsaved_current_count=len(source['current_saves'])-len(selected),
        groups=groups,all_actual_MOS_terminal_currents_measured=False,
        missing_unsaved_status='unknown/unmeasured, not zero',
        scope='Seven independent ideal-source positive terminals; two SR internal drain/selected NM source/CQB branches; eight actual RC input blocks R0/R1/C0/C1/clear drains.',
        no_complete_node_KCL_saved=True,whole_fixture_KCL_pass=None)
    if len(selected)!=89:raise ValueError('Expected89 selected native current histories')
    return cfg


def save_only_deck(deck,cfg):
    unchanged=''.join(l for l in deck.splitlines(True) if not l.startswith('save '))
    return unchanged+''.join('save '+s+'\n' for s in sorted(cfg['voltage_saves']+cfg['current_saves']))


def main():
    boundaries=read(V1/'load_boundaries.json');oldmanifest=read(V1/'manifest.json');cases={}
    failure=dict(source='Parent-reported managed state/native log excerpt; no remote read in this preparation',
        run_id='sar8audit-ctrl-stdfull-storage-ff-v1',status='limit_exceeded',
        last_native_time_s=3.11464e-9,output_bytes=2151981342,elapsed_s=79.35,peak_RSS_bytes=379396096,
        primary_native_codes=['SPECTRE-27','SPECTRE-7082'],subsequent_code='USIMUWI-20006',
        native_complete=False,zero_error_footer=False,electrical_verdict=None,
        inference='Output2GiB guard tripped. Subsequent allocation message is not evidence of RSS exhaustion. Old raw preserved; SSv1 registered but not started.')
    base.write_json(OUT/'v1_failure_reference.json',failure)
    for tag in ['ff','ss']:
        src=V1/tag;oldrecipe=read(src/'recipe.suggested.yaml');oldcfg=read(src/'measurement.json')
        if base.digest((src/'recipe.suggested.yaml').read_bytes())!=oldmanifest['cases'][tag]['recipe_file_sha256']:
            raise ValueError('Preserve frozen v1 recipe')
        for item in oldrecipe['inputs']:
            if base.digest((ROOT/item['source']).read_bytes())!=item['sha256']:raise ValueError('Frozen v1 input changed')
        dest=OUT/tag;cfg=measurement(oldcfg,boundaries)
        base.write_json(dest/'measurement.json',cfg)
        deck=save_only_deck((src/'test.scs').read_text(),cfg);base.exact_write(dest/'test.scs',deck)
        recipe=copy.deepcopy(oldrecipe);run='sar8audit-ctrl-stdfull-storage-'+tag+'-v2'
        recipe.update(run_id=run,design_id='standard_cell_full_storage_'+tag+'_measure_v2',
                      analyzer='standard_cell_storage_v2_analyze.py',qualification_scope=cfg['scope'])
        replacements={'test.scs':dest/'test.scs','measurement.json':dest/'measurement.json'}
        files=[(x['name'],replacements.get(x['name'],ROOT/x['source'])) for x in oldrecipe['inputs']]
        files += [('standard_cell_storage_v2_analyze.py',OWN/'standard_cell_storage_v2_analyze.py')]
        recipe['inputs']=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in files]
        # No circuit, stimulus, simulator option or resource modification.
        if recipe['resources']!=oldrecipe['resources'] or recipe['spectre_args']!=oldrecipe['spectre_args']:
            raise ValueError('Resource/solver contract changed')
        base.write_json(dest/'recipe.suggested.yaml',recipe)
        freeze=dict(recipe_file_sha256=base.digest((dest/'recipe.suggested.yaml').read_bytes()),
            inputs=[dict(name=n,bytes=p.stat().st_size,sha256=base.digest(p.read_bytes())) for n,p in files])
        base.write_json(dest/'freeze.json',freeze)
        ratio=(len(cfg['voltage_saves'])+len(cfg['current_saves']))/(len(oldcfg['voltage_saves'])+len(oldcfg['current_saves']))
        estimate=failure['output_bytes']*(20e-9/failure['last_native_time_s'])*ratio
        cases[tag]=dict(run_id=run,**freeze,parent_v1_recipe_file_sha256=oldmanifest['cases'][tag]['recipe_file_sha256'],
            voltage_saves=len(cfg['voltage_saves']),current_saves=len(cfg['current_saves']),
            physical_pairs=len(cfg['stress_voltage_pairs']),storage_contexts=len(cfg['storage']['observers']),
            full_MOS_currents=False,complete_KCL=False,whole_fixture_KCL_pass=None,
            raw_trace_count_ratio=ratio,rough20ns_output_bytes=estimate,rough20ns_output_GiB=estimate/1024**3,
            raw_size_estimate_policy='Scale incomplete FFv1 bytes/time by saved trace count only. Activity, sparse updates, number formatting and timestep differ by phase; estimate is not a completion guarantee or SS measurement.',
            source_DUT_stimuli_solver_and_resources_unchanged=True,old_inputs_or_raw_overwritten=False,
            raw_limit_GiB=2,collection_limit_MiB=32,submitted=False)
    base.write_json(OUT/'manifest.json',dict(cases=cases,measurement_only_delta=True,
        all980_voltage_and11220_physical_pairs_preserved=True,all26_functional_observers_preserved=True,
        full_KCL_conclusions_removed=True,unsaved_currents='unknown',
        current_selection='89 =7 sources +34 SR +48 RC',
        v1_failure_reference='v1_failure_reference.json',SSv1_must_not_start=True,
        remote_query_or_submission=False,resource_limits_increased=False))
    print(json.dumps({tag:{k:v[k] for k in ['run_id','recipe_file_sha256','current_saves','rough20ns_output_GiB']} for tag,v in cases.items()},indent=2))


if __name__=='__main__':main()
