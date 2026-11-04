"""Bind a fresh analysis-only proposal to completed feedback v2; local only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import build_kickback_fixture as k

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE/'generated/feedback_tt_v2'
OUT=HERE/'generated/feedback_v2_reduce_v1'
SOURCE=ROOT/'output/managed_execution/runs/sar8audit-comp-feedback-tt-v2'
MANAGED='d56adca4380107296e7bd8aebe5fadd39f419aa579e8a0235bc53284b2b5cb90'


def sha(b):return hashlib.sha256(b).hexdigest()
def js(v):return json.dumps(v,indent=2,allow_nan=False)+'\n'


def prepare():
    recipe=json.loads((SOURCE/'recipe.json').read_bytes())
    actual=sha(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii'))
    if actual!=MANAGED:raise ValueError('Registered source recipe differs')
    for f in recipe['files']:
        if sha((SOURCE/'inputs'/f['name']).read_bytes())!=f['sha256']:raise ValueError('Registered source input differs')
    evidence=SOURCE/'collected';receipt=json.loads((evidence/'collection_receipt.json').read_bytes())
    if receipt.get('skipped') or receipt['total_bytes']!=30426213:raise ValueError('Expected complete failed-analysis evidence')
    for f in receipt['files']:
        h=hashlib.sha256();p=evidence/f['name']
        with p.open('rb') as stream:
            for blob in iter(lambda:stream.read(65536),b''):h.update(blob)
        if p.stat().st_size!=f['bytes'] or h.hexdigest()!=f['sha256']:raise ValueError('Collection hash differs')
    state=json.loads((evidence/'simulation.state.json').read_bytes())
    if state['status']!='complete' or not state['native']['native_analysis_pass'] or not state['native']['zero_error_footer']:raise ValueError('Native completion required')
    log=(evidence/'spectre.out').read_bytes();steps=int(re.search(rb'Number of accepted tran steps\s*=\s*(\d+)',log)[1])
    if steps!=156160:raise ValueError('Native source point count differs')
    policy=dict(baseline_row_budget=20000,max_witness_times=10000,max_export_rows=30000,max_wave_bytes=14*1024**2,
        selection='every ceil(native_points/20000)-th original row plus metric/event/recovery witnesses; no metric decimation',
        export_range_s=[0.,100e-9],figure_label_required=True)
    payload={n:(BASE/n).read_bytes() for n in ['feedback_analyze.py','native_support.py','measurement.json']}
    payload['feedback_source_reduce.py']=(HERE/'feedback_source_reduce.py').read_bytes()
    binding=dict(schema_version=1,source_run_id=recipe['run_id'],source_recipe_hash=MANAGED,source_analysis_name='tran_feedback',
        source_raw_relative_path='raw/tran_feedback.tran.tran',source_input_sha256={f['name']:f['sha256'] for f in recipe['files']},
        native_log_sha256=sha(log),simulation_state_sha256=sha((evidence/'simulation.state.json').read_bytes()),native_points=steps+1,
        measurement_sha256=sha(payload['measurement.json']),frozen_module_sha256={n:sha(payload[n]) for n in ['feedback_analyze.py','native_support.py']},
        max_derived_bytes=29*1024**2,collection_cap_bytes=32*1024**2,export_policy=policy,
        preceding_partial_waveform='Failed-analysis artifact only; never input to this recovery')
    payload['source_binding.json']=js(binding).encode()
    proposal=dict(kind='analysis_only',source_run_id=recipe['run_id'],run_id='sar8audit-comp-feedback-v2-reduce1',design_id=recipe['design_id'],
        analyzer='feedback_source_reduce.py',inputs=[dict(name=n,source=(OUT/n).relative_to(ROOT).as_posix(),sha256=sha(v)) for n,v in payload.items()],
        summary_signals=recipe['summary_signals'],expected_stop_s=100e-9,
        qualification_scope='Analysis-only completed-v2 full-native protocol/990 stress metrics; bounded native-row export only, full8742 stress coverage incomplete',
        oa_parity='completed_source_netlist_only_no_OA_change',
        test_conditions=dict(source_run=recipe['run_id'],source_recipe_hash=MANAGED,simulation_reused=True,
            measurement_native_points=steps+1,waveform_decimated_only=True,metric_decimation=False),
        resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,simulation_wall_seconds=1,
            analysis_rss_mib=256,analysis_virtual_mib=512,analysis_wall_seconds=1800,max_output_mib=32,queue_timeout_seconds=600))
    manifest=dict(status='local_analysis_only_proposal_not_executed',source_recipe_hash=MANAGED,
        source_native_points=steps+1,partial_old_gzip_not_used=True,all_native_metrics_preserved=True,
        frozen_inputs_unchanged=['feedback_analyze.py','native_support.py','measurement.json'],
        maximum_wave_uncompressed_bytes=30000*57*8,wave_cap_bytes=14*1024**2,derived_cap_bytes=29*1024**2,collection_cap_bytes=32*1024**2,
        input_bytes=sum(map(len,payload.values())),input_sha256={n:sha(v) for n,v in payload.items()},builder_sha256=sha(Path(__file__).read_bytes()),
        baseline_stride_for_this_source=(steps+1+19999)//20000,metric_sampling='All156161 native points, both complete raw passes SHA checked',
        source_raw_sha256='Measured in both remote read-only passes, not available from local partial export')
    for n,v in payload.items():k.exact(OUT/n,v)
    k.exact(OUT/'recipe_proposal.json',js(proposal));k.exact(OUT/'manifest.json',js(manifest));k.exact(OUT/'README.md',README)
    print('LOCAL_FEEDBACK_ANALYSIS_ONLY',OUT,'inputs',manifest['input_bytes'],'native_points',steps+1,'baseline_stride',manifest['baseline_stride_for_this_source'])


README='''# Completed feedback v2: analysis-only waveform-export repair

No Spectre job, circuit/clock/solver change or write to the completed source.
Source sar8audit-comp-feedback-tt-v2, managed hash in source_binding.json.
Its100ns native run passed with156160 accepted steps. Earlier analysis failed
its29MiB gzip output cap; the collected partial gzip is never used as input.

Frozen feedback_analyze.py/native_support.py/measurement.json are byte-identical
to v2. Pass1 invokes the unchanged native reducer with only its waveform encoder
suppressed: every native metric, event, current integral, KCL and990 selected
stress extrema is computed. Pass2 reads the identical complete raw again; hashes,
END, point count and source file stat must match. No interpolation/resimulation.

Keep all57 waveform columns but export every8th original point for this source,
plus original event brackets, signal/KCL extrema, all990 selected stress peak
times, precompare/after-write and reset-recovery witnesses. The exact source
range, stride and native/export row counts are recorded in wave.columns.json
and result.json. Figures must label the sampled export; metrics remain all
156161 points. Witnesses are never silently dropped to satisfy a file cap.

At most20000 baseline rows +10000 witness times =>30000 rows,13,680,000 bytes
uncompressed (57x8-byte columns). Gzip cap14MiB, total derived29MiB and managed
output/collection32MiB. Source raw remains remote/read-only for later zooms.
Full1457MOS/8742-pair waveform stress still incomplete;165MOS/990 pairs only.
Original native CMI/warnings/logs are retained. Native PASS is not module signoff.

Parent alone registers and calls managed analyze on recipe_proposal.json.
It is kind=analysis_only with source_run_id, never a simulation submit.
'''

if __name__=='__main__':prepare()
