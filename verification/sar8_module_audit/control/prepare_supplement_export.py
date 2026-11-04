"""Prepare two local analysis-only suggestions. No registration, remote or simulation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import yaml

import supplement_native_export as export

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[2]
DEST = OWN / 'supplement_export_v1'
HELPER_SHA = '293b8aa64012577e527691007c623f017b7a3dd3ed53eb2f18e36314ed646064'
PARSER_SHA = 'c379d993c02438621d6609c67616b6b10dd7dbf5947713a0ea5156ebf7510e52'


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def write_exact(path, value):
    blob = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != blob:
            raise ValueError('Preserve existing unreviewed/generated package: ' + str(path))
    else:
        path.write_bytes(blob)


def prepare(label, source_id, run_id):
    record = yaml.safe_load((ROOT / 'management/runs' / (source_id + '.yaml')).read_text())
    recipe = record['recipe']
    canonical = json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()
    if digest(canonical) != record['recipe_hash'] or recipe['run_id'] != source_id:
        raise ValueError('Source recipe identity/hash mismatch')
    folder = ROOT / 'output/managed_execution/runs' / source_id
    state = json.loads((folder / 'collected/simulation.state.json').read_bytes())
    if (state['status'] != 'complete' or state['exit_code'] != 0
            or not state['native']['native_analysis_pass'] or not state['native']['zero_error_footer']):
        raise ValueError('Source local completion evidence missing')
    source_inputs = {}
    for item in recipe['files']:
        path = folder / 'inputs' / item['name']
        blob = path.read_bytes()
        if digest(blob) != item['sha256'] or len(blob) != item['bytes']:
            raise ValueError('Frozen source input changed: ' + item['name'])
        source_inputs[item['name']] = dict(sha256=item['sha256'], bytes=len(blob))
    text = (folder / 'inputs/test.scs').read_text()
    saved = set(re.findall(r'(?m)^save\s+(\S+)', text))
    signals = [dict(frozen_save_name=name.upper(), native_match_name=name,
                    role='voltage_witness_only', required=True) for name in export.SELECTIONS[source_id]]
    if any(item['frozen_save_name'] not in saved for item in signals):
        raise ValueError('Proposed signal was not explicitly saved')
    analysis = re.findall(r'(?m)^(\w+)\s+tran\b', text)
    if len(analysis) != 1:
        raise ValueError('Expected one source transient analysis')
    config = dict(schema_version=1, source_run_id=source_id, source_recipe_hash=record['recipe_hash'],
        source_input_sha256={name: source_inputs[name]['sha256'] for name in ['dut.scs', 'test.scs']},
        source_analysis_name=analysis[0], history_start_s=0., history_stop_s=export.STOP,
        diagnostic_start_s=40.8e-9, diagnostic_stop_s=export.STOP, signals=signals,
        reviewed_helper_sha256=HELPER_SHA, reviewed_parser_sha256=PARSER_SHA,
        max_parser_output_bytes=30*1024**2, max_collected_directory_bytes=32*1024**2-1,
        max_runtime_rss_kib=256*1024,
        endpoint_policy='Keep the real last native row, which may be below requested stop. Prove interval coverage using a later native time marker or scanned END; never fabricate endpoint.',
        END_policy='Source native PASS/completed state and parser END-observed are separate evidence. A prefix-only scan reports END false explicitly.')
    export.validate_config(config)
    target = DEST / label
    write_exact(target / 'manifest.json', config)
    sources = [('supplement_native_export.py', OWN / 'supplement_native_export.py'),
               ('native_boundary_export.py', OWN / 'native_boundary_export.py'),
               ('stream_native_boundary.cpp', OWN / 'stream_native_boundary.cpp'),
               ('supplement_manifest.json', target / 'manifest.json')]
    inputs = [dict(source=path.relative_to(ROOT).as_posix(), name=name, sha256=digest(path.read_bytes()))
              for name, path in sources]
    if inputs[1]['sha256'] != HELPER_SHA or inputs[2]['sha256'] != PARSER_SHA:
        raise ValueError('Reviewed frozen helper/parser changed')
    suggestion = dict(kind='analysis_only', source_run_id=source_id, run_id=run_id,
        design_id='sar8_control_SN_native_witnesses', analyzer='supplement_native_export.py', inputs=inputs,
        summary_signals=[signals[0]['native_match_name']], expected_stop_s=export.STOP,
        qualification_scope='Existing native voltage witnesses only; no simulation, circuit repair, reproduction or ADC acceptance',
        oa_parity='source_netlist_only_no_OA_change',
        test_conditions=dict(source_corner='ff', source_vdd=.99, source_temp_c=-40,
                             history_end_ns=export.STOP*1e9, source_voltage_count=len(signals)),
        resources=dict(threads=1, simulation_rss_mib=1024, simulation_virtual_mib=8192,
            simulation_wall_seconds=1, analysis_rss_mib=256, analysis_virtual_mib=1024,
            analysis_wall_seconds=900, max_output_mib=64, queue_timeout_seconds=600))
    write_exact(target / 'recipe.suggested.yaml', suggestion)
    write_exact(target / 'package_manifest.json', dict(status='local_preparation_only',
        source_id=source_id, source_recipe_sha256=record['recipe_hash'],
        source_registered_input_hashes_verified=source_inputs,
        package_inputs=[dict(name=name, bytes=path.stat().st_size, sha256=digest(path.read_bytes())) for name, path in sources],
        package_total_bytes=sum(path.stat().st_size for _, path in sources),
        registration_or_remote_execution=False))
    return dict(label=label, source_id=source_id, suggested_run_id=run_id,
                signals=len(signals), package_bytes=sum(path.stat().st_size for _, path in sources))


def main():
    result = [prepare('source', 'sar8fix-loaded-both-ffcold', 'sar8audit-ctrl-source-sn-v1'),
              prepare('fixture', 'sar8audit-ctrl-first-event-v1', 'sar8audit-ctrl-fixture-sn-v1')]
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
