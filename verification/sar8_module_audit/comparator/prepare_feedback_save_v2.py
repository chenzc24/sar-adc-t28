"""Measurement-only feedback TT v2. Never modify/retry the failed v1."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re

import build_kickback_fixture as k

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE/'generated/feedback_tt_v1'
OUT=HERE/'generated/feedback_tt_v2'
RUN='sar8audit-comp-feedback-tt-v1'
PREFIXES=('xdut.xcomp.','xdut.xctrl.xtim.')


def sha(blob):return hashlib.sha256(blob).hexdigest()
def js(v):return json.dumps(v,indent=2,allow_nan=False)+'\n'


def prepare():
    parent=json.loads((BASE/'recipe_proposal.json').read_bytes())
    manifest=json.loads((BASE/'manifest.json').read_bytes())
    for f in parent['inputs']:
        if sha((ROOT/f['source']).read_bytes())!=f['sha256']:raise ValueError('Frozen v1 input differs: '+f['name'])
    evidence=ROOT/'output/managed_execution/runs'/RUN/'collected'
    receipt=json.loads((evidence/'collection_receipt.json').read_bytes())
    for f in receipt['files']:
        blob=(evidence/f['name']).read_bytes()
        if len(blob)!=f['bytes'] or sha(blob)!=f['sha256']:raise ValueError('Failure evidence hash differs')
    log=(evidence/'spectre.out').read_bytes();text=log.decode('ascii')
    if ('allpub' in text or 'save   711     (voltage)' not in text or 'save   23      (current)' not in text
        or 'SPECTRE-27' not in text or '38.0381 ns' not in text):raise ValueError('Native failure differs')
    old=json.loads((BASE/'measurement.json').read_bytes());cfg=copy.deepcopy(old)
    selected=[p for p in old['mos_pairs'] if p['instance'].startswith(PREFIXES)]
    mos_count=len({p['instance'] for p in selected})
    need=set(old['wave_voltage_columns'])|{n for p in selected for n in p['nodes'] if n!='0'}
    need|={'prep','pren','vcm','vrefp','vrefn'}
    exact={n.lower():n for n in old['voltage_saves']}
    if not need<=exact.keys():raise ValueError('Required native voltage not found')
    cfg['voltage_saves']=sorted(exact[n] for n in need);cfg['mos_pairs']=selected
    if (len(cfg['voltage_saves']),mos_count,len(selected))!=(124,165,990):raise ValueError('Unreviewed selection expansion')
    cfg['scope']='Native-feedback functional diagnosis with165-MOS direct-chain stress screen; full1457-MOS stress waveform coverage deferred'
    cfg['pair_scope']='Selected165MOS: full N4 comparator plus all154MOS sar8p_timing incl rx2/RAW/DEC/write/update/SR/QUIET/clock driver.990 pairs only;1292MOS/7752 pairs deferred.'
    cfg['stress_save_scope']=dict(selected_MOS_count=165,selected_pair_count=990,full_MOS_count=1457,full_pair_count=8742,
        deferred_MOS_count=1292,deferred_pair_count=7752,full_waveform_stress_complete=False,
        native_CMI='Original PDK/model checks remain enabled on all unchanged1457MOS; log preserved, not lifetime signoff',
        selected_instance_prefixes=list(PREFIXES))
    lines=(BASE/'test.scs').read_text(encoding='utf-8').splitlines()
    deck='\n'.join([n for n in lines if not n.startswith('save ')]+['save '+n for n in cfg['voltage_saves']+cfg['current_saves']])+'\n'
    original=(BASE/'feedback_analyze.py').read_text(encoding='utf-8')
    before="mos_screen_exceeded_records=sum(v['screen_exceeded'] for v in extrema.values()),"
    after="""selected_mos_screen_exceeded_records=sum(v['screen_exceeded'] for v in extrema.values()),
        selected_mos_count=cfg['stress_save_scope']['selected_MOS_count'],selected_mos_pair_count=len(cfg['mos_pairs']),
        full_mos_count=1457,full_mos_pair_count=8742,full_mos_screen_complete=False,
        full_mos_screen_exceeded_records=None,stress_save_scope=cfg['stress_save_scope'],"""
    if original.count(before)!=1:raise ValueError('Stress-result replacement is not exact')
    analyzer=original.replace(before,after)
    before="Every original native time point, all retained MOS six terminal pairs; deduplicated node pairs then expanded"
    after="Every native point for selected165MOS/990 pairs only;1292MOS/7752 pairs deferred. Full-device native CMI logs retained separately"
    if analyzer.count(before)!=1:raise ValueError('Stress-method replacement is not exact')
    analyzer=analyzer.replace(before,after)
    payload={n:(BASE/n).read_bytes() for n in ['cells.scs','cdac_load.scs','initializer.va','native_support.py']}
    payload.update({'test.scs':deck.encode(),'feedback_analyze.py':analyzer.encode()})
    cfg['required_input_sha256']={n:sha(v) for n,v in payload.items()}
    payload['measurement.json']=js(cfg).encode()
    # This is a measurement cut: no settings, internal nodes or sources change.
    stripped=lambda t:'\n'.join(n for n in t.splitlines() if not n.startswith('save '))
    if stripped(deck)!=stripped('\n'.join(lines)):raise ValueError('Non-save deck content changed')
    for key in ['roles','tokens','data_nodes','ref_q_nodes','wave_voltage_columns','wave_current_columns','kcl_terms','terminal_catalog','stop_s','release_end_s','sample_fall_end_s','max_output_bytes','collection_allowance_bytes']:
        if cfg[key]!=old[key]:raise ValueError('Required measurement/protocol boundary changed: '+key)
    # Empirical ASCII estimate, not a promise about future native point density.
    cost=lambda names:sum(len(n)+32 for n in names)+48
    old_cost=cost([n.lower() for n in old['voltage_saves']+old['current_saves']])
    new_cost=cost([n.lower() for n in cfg['voltage_saves']+cfg['current_saves']])
    estimate=2048*100/38.0381*new_cost/old_cost
    if estimate*1.5>=2048:raise ValueError('Estimated save volume lacks review headroom')
    report=dict(status='local_only_not_Spectre_compiled',parent_run=RUN,parent_managed_recipe_sha256='f8fc3ef1e8edbfb22c81215cc4ee066884ca6af8d934bad9f918bab5ee3062ea',
        parent_proposal_sha256=sha((BASE/'recipe_proposal.json').read_bytes()),parent_failure_log_sha256=sha(log),
        failure_receipt_bytes=receipt['total_bytes'],failure_native_PASS=False,failure_time_s=38.0381e-9,
        failure_type='SPECTRE-27/output_size_limit, not demonstrated memory exhaustion',
        circuit_MOS=1457,selected_MOS=165,selected_pairs=990,deferred_MOS=1292,deferred_pairs=7752,
        voltage_saves=124,current_saves=23,unchanged_returned_columns=57,unchanged_payloads=['cells.scs','cdac_load.scs','initializer.va','native_support.py'],
        measurement_only_changes=['test.scs save statements','measurement.json required signals/screen scope','feedback_analyze.py selected/deferred stress labels only'],
        ascii_output_estimate=dict(v1_limit_MiB=2048,v1_failure_time_ns=38.0381,stop_ns=100,old_row_cost=old_cost,new_row_cost=new_cost,
            same_density_MiB=estimate,density_factor_allowance=1.5,allowance_MiB=estimate*1.5,hard_gate_MiB=2048,
            assumption='Bytes proportional to requested TRACE name/field cost times native point count;1.5x density is an assumption, no accepted-step footer after abort'),
        input_hashes={n:sha(v) for n,v in payload.items()},input_bytes=sum(map(len,payload.values())),
        physical_cut_manifest_relative='../feedback_tt_v1/manifest.json',physical_cut_manifest_sha256=sha((BASE/'manifest.json').read_bytes()),
        builder_sha256=sha(Path(__file__).read_bytes()),baseline_adopted=False,remote_submitted=False)
    recipe=copy.deepcopy(parent)
    recipe.update(run_id='sar8audit-comp-feedback-tt-v2',design_id='sar8_comp_native_feedback_tt_v2',qualification_scope=cfg['scope'],
        inputs=[dict(name=n,source=(OUT/n).relative_to(ROOT).as_posix(),sha256=sha(v)) for n,v in payload.items()])
    if recipe['resources']!=parent['resources'] or recipe['spectre_args']!=parent['spectre_args']:raise ValueError('Resource/solver settings changed')
    for n,v in payload.items():k.exact(OUT/n,v)
    k.exact(OUT/'manifest.json',js(report));k.exact(OUT/'recipe_proposal.json',js(recipe));k.exact(OUT/'README.md',README)
    print('LOCAL_FEEDBACK_V2',OUT,'saves124V/23I','input_bytes',report['input_bytes'],'estimate_MiB',round(estimate,2))
    return report


README='''# Feedback TT v2: measurement-only save reduction

Local only, not Spectre compiled/submitted. recipe_proposal.json is ready for
parent managed serial registration. The failed v1 is immutable and not retried.
Same1457MOS, full feedback, physical cut,100ns, sources/initialization, model
includes, solver tolerances,1GiB RSS/one thread and2048MiB output budget.
cells.scs/cdac_load.scs/initializer.va/native_support.py are byte-identical.

Save124V/23I. Keep exactly the same57 returned native timing/current/KCL columns.
Additional required voltages cover all N4 comparator and the complete native
154MOS sar8p_timing cone, including rx2, RAW/DEC, write/update, SR/QUIET and
clock output driver:165MOS/990 terminal-pair screens. Every requested save uses
its actual case from the native v1 accepted list. No wildcard/allpub saves.

1292 retainedMOS/7752 pairs are explicitly unmeasured by local waveform stress
analysis. Output full_mos_screen_complete=false and full_mos_screen_exceeded_records
=null; selected_mos_screen_exceeded_records is only the165MOS screen. Native CMI
remains enabled across the unchanged circuit and its complete log is preserved.
No all1457/8742 waveform-stress pass or lifetime qualification can be claimed.

V1 accepted711V/23I; its2GiB psfascii failure at38.0381ns starts with SPECTRE-27,
followed by7082/USIMUWI-20006. Native PASS=false; peakRSS319,078,400B does not
demonstrate memory exhaustion. Log/receipt hashes are in manifest.json.
ASCII name/field-cost extrapolation estimates1007.6MiB to100ns or1511.4MiB at
1.5x native point density. No accepted-step footer exists after abort, so this
is a capacity estimate, not a guaranteed bound;2048MiB hard gate stays active.

Only save statements/configuration and stress-report scope labels change.
Native protocol, token/write/update/reset and recovery algorithms are unchanged.
All original warnings/native errors must remain visible. Streaming derived cap
29MiB and total32MiB collection allowance remain; do not collect raw PSF.
'''

if __name__=='__main__':prepare()
