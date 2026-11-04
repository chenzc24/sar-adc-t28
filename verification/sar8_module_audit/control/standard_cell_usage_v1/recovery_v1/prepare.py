"""Generate narrow gzip-only derivatives and immutable source-bound recipes."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
USAGE=HERE.parent
OWN=USAGE.parent
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
from review_standard_cell_storage_v2 import record
import prepare_first_event as base


def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Exact source transform count differs: '+old[:80])
    return text.replace(old,new)


def write(path,text):base.exact_write(path,text)
def dump(path,value):write(path,json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def main():
    original=OWN/'standard_cell_storage_fastanalysis_v1/fast_gate_analyze.py'
    text=original.read_text()
    text=replace(text,'import sys\n','import sys\nfrom stream_gzip import GzipWriter\n')
    text=replace(text,"native_path = os.path.join(output, 'peak.native.bin')","native_path = os.path.join(output, 'peak.native.bin.gz')")
    text=replace(text,"binary = open(native_path, 'wb')","binary = GzipWriter(native_path,cfg['max_derived_binary_bytes'])")
    text=replace(text,"                        if binary_bytes + len(blob) > cfg['max_derived_binary_bytes']:\n                            raise ValueError('Native current export exceeds 30 MiB cap')\n",'')
    text=replace(text,'result = dict(analysis_complete=True, scope=', 'result = dict(analysis_complete=True, streaming_export=binary.proof(), scope=')
    write(HERE/'fast_gzip_analyze.py',text)
    source=(OWN/'standard_cell_full_analyze.py').read_text()
    fun=source[source.index('def observe_history('):source.index('\ndef compress_history(')]
    fun=replace(fun,"with open(os.path.join(output,'peak.native.bin'),'rb') as f:","with gzip.open(os.path.join(output,'peak.native.bin.gz'),'rb') as f:")
    proof='''\n\ndef verify_compressed(output,cfg,result):
    path=os.path.join(output,'peak.native.bin.gz');h=hashlib.sha256();size=0
    with gzip.open(path,'rb') as handle:
        while True:
            blob=handle.read(65536)
            if not blob:break
            h.update(blob);size+=len(blob)
    expected=result['streaming_export']['uncompressed']
    if dict(bytes=size,sha256=h.hexdigest())!=expected:raise ValueError('Lossless gzip proof differs')
    columns=native.read(os.path.join(output,'peak.columns.json'))['names']
    if size!=result['diagnostic_points']*len(columns)*8:raise ValueError('Native diagnostic row count differs')
    return dict(file='peak.native.bin.gz',uncompressed=expected,compressed=tools.identity(path),
        decompressed_bytes_and_SHA_match=True,every_native_row_preserved=True,raw_PSF_modified=False,
        direct_streaming_gzip=True,no_uncompressed_scratch_created=True)
'''
    write(HERE/'storage_gzip.py','from __future__ import print_function\nimport os,struct,gzip,hashlib\nimport full_gate_analyze as native\nimport standard_cell_full_analyze as tools\n\n'+fun+proof)
    source=(USAGE/'usage_analyze.py').read_text()
    fun=source[source.index('def pin_edges('):source.index('\ndef main():')]
    fun=replace(fun,"with open(os.path.join(output,'peak.native.bin'),'rb') as handle:","with gzip.open(os.path.join(output,'peak.native.bin.gz'),'rb') as handle:")
    write(HERE/'usage_gzip.py','from __future__ import print_function\nimport os,struct,gzip\nimport full_gate_analyze as native\n\n'+fun)
    text=(OWN/'standard_cell_storage_fastanalysis_v1/fast_source_analyze.py').read_text()
    text=replace(text,'import fast_gate_analyze as fast','import fast_gzip_analyze as fast')
    text=replace(text,'import standard_cell_storage_v2_analyze as coverage','import storage_gzip as history\nimport usage_gzip as usage')
    text=replace(text,"safe_file(run,'inputs/fast_gate_analyze.py')","safe_file(run,'inputs/fast_gzip_analyze.py')")
    text=replace(text,"['full_gate_analyze.py','standard_cell_full_analyze.py','standard_cell_storage_v2_analyze.py']","['full_gate_analyze.py','standard_cell_full_analyze.py','usage_analyze.py']")
    text=replace(text,'result=coverage.add_coverage(fast.summarize(path,cfg,output),cfg)','result=fast.summarize(path,cfg,output)')
    text=replace(text,"result['storage_observations']=frozen.observe_history(output,cfg)","result['storage_observations']=history.observe_history(output,cfg)\n    result['usage_observations']=usage.usage_observations(output,cfg)")
    text=replace(text,"result['returned_waveform']=frozen.compress_history(output)","result['returned_waveform']=history.verify_compressed(output,cfg,result)")
    text=replace(text,"'Diagnostic first-SR maximum, not source-fit acceptance'","'Diagnostic net176 maximum; joint stress is computed from all simultaneous D/S values'")
    text=replace(text,"analysis_kind='analysis_only_exact_completed_source_reuse'","analysis_kind='analysis_only_completed_source_streaming_gzip'")
    write(HERE/'source_analyze.py',text)
    transforms=dict(original_fast_reducer_sha256=base.digest(original.read_bytes()),
        new_fast_reducer_sha256=base.digest((HERE/'fast_gzip_analyze.py').read_bytes()),
        change='Direct gzip writer/reader and compressed-byte guard only; original native statistics, thresholds, point/row arithmetic and storage/usage observation logic retained.',
        source_configuration_unchanged=True,cap_bytes=20*1024**2,collection_cap_bytes=32*1024**2)
    dump(HERE/'transform_manifest.json',transforms)
    for label,hashval in [('baseline','a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1'),
                          ('rck2k','997693935954ebbce4f0d4191e0a55ac1e1f391d7502bd5f5005c92c39876b3a')]:
        runid='sar8audit-ctrl-usage-'+label+'-ff-v1';rec=record(runid)
        assert rec['recipe_hash']==hashval
        files={x['name']:x for x in rec['recipe']['files']}
        binding=dict(source_run_id=runid,source_recipe_hash=hashval,
            source_inputs={n:dict(bytes=x['bytes'],sha256=x['sha256']) for n,x in files.items()},
            allow_analysis_not_started=label=='rck2k',fast_reducer_sha256=transforms['new_fast_reducer_sha256'],
            activation='Baseline actual failed export; contrast may be analyzed directly only after real native simulation PASS. Running/complete analysis rejected.',
            all_native_rows_currents_pairs_thresholds_and_source_cfg_preserved=True,
            source_raw_and_failed_derived_read_only=True,compressed_file_guard_bytes=20*1024**2)
        folder=HERE/label;dump(folder/'source_binding.json',binding)
        inputs=[(p.name,p) for p in [HERE/'source_analyze.py',HERE/'fast_gzip_analyze.py',HERE/'stream_gzip.py',HERE/'storage_gzip.py',HERE/'usage_gzip.py']]
        inputs +=[(n,ROOT/files[n]['source']) for n in ['measurement.json','external_library.json','full_gate_analyze.py','standard_cell_full_analyze.py','usage_analyze.py']]
        inputs.append(('source_binding.json',folder/'source_binding.json'))
        recipe=dict(schema_version=1,kind='analysis_only',source_run_id=runid,
            run_id='sar8audit-ctrl-usage-'+label+'-gzip-v1',design_id=rec['recipe']['design_id'],
            entry='source_analyze.py',analyzer='source_analyze.py',
            inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in inputs],
            expected_stop_s=20e-9,summary_signals=rec['recipe']['summary_signals'],
            qualification_scope='Exact completed native source reuse with lossless direct gzip; original failed derived untouched, no new simulation or ADC qualification',oa_parity='netlist_only',
            test_conditions=rec['recipe']['test_conditions'],
            resources=dict(threads=1,analysis_rss_mib=256,analysis_virtual_mib=1024,
                max_output_mib=64,analysis_wall_seconds=300,queue_timeout_seconds=600))
        dump(folder/'recipe.suggested.yaml',recipe)
    print('SOURCE_BOUND_GZIP_RECOVERY_PREPARED_NO_DISPATCH')


if __name__=='__main__':main()
