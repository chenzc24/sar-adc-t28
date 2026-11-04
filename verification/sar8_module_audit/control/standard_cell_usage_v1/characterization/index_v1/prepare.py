"""Freeze a source-bound managed audit recipe; local only, never dispatches."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
USAGE=HERE.parents[1]
OWN=USAGE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
from review_standard_cell_storage_v2 import record
import prepare_first_event as base


def dump(path,data):base.exact_write(path,json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')


def main():
    run='sar8audit-ctrl-usage-baseline-ff-v1';src=record(run)
    assert src['recipe_hash']=='a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1'
    byname={x['name']:x for x in src['recipe']['files']}
    prefix=json.loads((HERE.parent/'archive_prefix.json').read_text())['metadata']
    assert prefix['archive_bytes']==13657415950 and prefix['compressed_prefix_read_bytes']==20480
    cfg=dict(expected_hostname='thu-wei',expected_uid=596,archive=dict(path=prefix['archive'],bytes=prefix['archive_bytes'],mtime_epoch=prefix['archive_mtime_epoch']),
        compressed_max_bytes=13657415950,decoded_max_bytes=64*1024**3,
        verified_prefix_bytes=20480,verified_prefix_sha256=prefix['compressed_prefix_sha256'],
        internal_wall_seconds=1740,RSS_max_bytes=256*1024**2,
        extended_metadata_max_bytes=65536,member_path_max_chars=1024,
        index_metadata_max_bytes=640*1024,checkpoint_max_bytes=48*1024,
        small_json_max_bytes=64*1024,derived_total_max_bytes=896*1024,
        target_FF_patterns=['*/tcbn28hpcplusbwp12t30p140ffg0p99vm40c*.db','*/tcbn28hpcplusbwp12t30p140ffg0p99vm40c*.lib*'],
        stop_after_target_and_release=True,
        scope='Dependency metadata only; target FF/doc names do not prove versions compatible or expose Liberty values',
        no_automatic_repeat_or_resume=True)
    dump(HERE/'index_config.json',cfg)
    binding=dict(source_run_id=run,source_recipe_hash=src['recipe_hash'],
        source_inputs={n:dict(bytes=x['bytes'],sha256=x['sha256']) for n,x in byname.items()},
        audit_role='Dependency conditions of the actual completed native DFF baseline; no new simulation or raw-waveform read',
        real_source_library_SHA_required=True,source_raw_and_failed_derived_read_only=True)
    dump(HERE/'source_binding.json',binding)
    inputs=[('archive_index.py',HERE/'archive_index.py'),('source_audit.py',HERE/'source_audit.py'),
        ('index_config.json',HERE/'index_config.json'),('source_binding.json',HERE/'source_binding.json'),
        ('external_library.json',ROOT/byname['external_library.json']['source'])]
    recipe=dict(schema_version=1,kind='analysis_only',source_run_id=run,
        run_id='sar8audit-ctrl-dependency-ccs-index-v1',design_id='native_DFF_actual_baseline_dependency_index',
        entry='source_audit.py',analyzer='source_audit.py',
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in inputs],
        expected_stop_s=src['recipe']['expected_stop_s'],summary_signals=src['recipe']['summary_signals'],
        qualification_scope='Completed-baseline dependency audit, source signals are registry context only and not remeasured; bounded archive metadata, no library bodies/db load/compatibility or circuit qualification',
        oa_parity='read_only_dependency_audit',test_conditions=src['recipe']['test_conditions'],
        resources=dict(threads=1,analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=1,
            analysis_wall_seconds=1800,queue_timeout_seconds=600))
    dump(HERE/'recipe.suggested.yaml',recipe)
    print('DEPENDENCY_INDEX_PACKAGE_READY_NO_REGISTER_OR_EXECUTION',base.digest((HERE/'recipe.suggested.yaml').read_bytes()))


if __name__=='__main__':main()
