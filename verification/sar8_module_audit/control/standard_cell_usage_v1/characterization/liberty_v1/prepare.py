"""Prepare exact indexed-member binding and compact native references; local."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import struct
import sys

HERE=Path(__file__).resolve().parent
OWN=HERE.parents[2]
USAGE=HERE.parents[1]
ROOT=OWN.parents[2]
INDEX=HERE.parent/'index_v1'
sys.path.insert(0,str(OWN))
from review_standard_cell_storage_v2 import record,identity
from review_standard_cell_full_result import receipt_files
import prepare_first_event as base


def dump(path,value):base.exact_write(path,json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def compact(case):
    run='sar8audit-ctrl-usage-'+case+'-gzip-v1';rec=record(run)
    folder=ROOT/'output/managed_execution/runs'/run/'collected'
    receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==rec['recipe_hash']
    result=json.loads(files['derived/result.json'].read_bytes())
    assert result['analysis_complete'] and result['source_raw_unchanged'] and result['simulation_started'] is False
    names=json.loads(files['derived/peak.columns.json'].read_bytes())['names']
    selected=['time','vdd!','xdut.u19_ck','xdut.u19_d','xdut.xu19.rn'];indices=[names.index(n) for n in selected]
    old=struct.Struct('<'+'d'*len(names));new=struct.Struct('<5d')
    target=HERE/('native_'+case+'.bin.gz');temp=target.with_suffix(target.suffix+'.writing')
    if temp.exists():raise ValueError('Preserve previous local reference scratch')
    original=hashlib.sha256();derived=hashlib.sha256();count=0;previous=None
    with gzip.open(files['derived/peak.native.bin.gz'],'rb') as source,temp.open('wb') as output:
        sink=gzip.GzipFile(filename='',mode='wb',compresslevel=6,fileobj=output,mtime=0)
        try:
            while True:
                blob=source.read(old.size)
                if not blob:break
                assert len(blob)==old.size
                original.update(blob);row=old.unpack(blob)
                assert previous is None or row[0]>previous
                previous=row[0];out=new.pack(*[row[i] for i in indices]);derived.update(out);sink.write(out);count+=1
        finally:sink.close()
    assert count==result['native_points']==result['diagnostic_points']
    assert dict(bytes=count*old.size,sha256=original.hexdigest())==result['returned_waveform']['uncompressed']
    if target.exists():
        if identity(target)!=identity(temp):raise ValueError('Preserve prior compact native reference')
        temp.unlink()
    else:temp.replace(target)
    return dict(file=target.name,columns=['time_s','VDD_V','CP_V','D_V','CDN_V'],native_points=count,
        decoded_bytes=count*new.size,decoded_sha256=derived.hexdigest(),compressed=identity(target),
        source_analysis_run=run,source_analysis_recipe_hash=rec['recipe_hash'],
        source_run_id=result['source_run_id'],source_recipe_hash=result['source_recipe_hash'],
        source_raw_sha256=result['raw_sha256'],source_full_decoded_sha256=original.hexdigest(),
        source_receipt_sha256=base.digest((folder/'collection_receipt.json').read_bytes()),
        every_native_time_and_selected_pin_value_preserved=True)


def main():
    source_id='sar8audit-ctrl-usage-baseline-ff-v1';source=record(source_id)
    index_id='sar8audit-ctrl-dependency-ccs-index-v1';index=record(index_id)
    assert source['recipe_hash']=='a4880aca396bc8ee6112e2069a7eb18579d54be2d04a1f795f6708667f47b1a1'
    assert index['recipe_hash']=='61b56ce7a68b2915029f9071b2157734ff1ba7d30575c8987cf5b15963d6f9b2'
    folder=ROOT/'output/managed_execution/runs'/index_id/'collected';receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==index['recipe_hash']
    result=json.loads(files['derived/result.json'].read_bytes())
    assert result['archive_index_complete'] and result['gzip_integrity_verified']
    rows=[json.loads(line) for line in files['derived/members.ndjson'].read_text().splitlines()]
    members=[x for x in rows if x['name'].endswith('/tcbn28hpcplusbwp12t30p140ffg0p99vm40c_ccs.lib')]
    assert len(members)==1;member=members[0]
    assert member['bytes']==1556315212 and member['decoded_body_offset']==13230658048
    binding=dict(source_run_id=source_id,source_recipe_hash=source['recipe_hash'],
        source_inputs={x['name']:dict(bytes=x['bytes'],sha256=x['sha256']) for x in source['recipe']['files']},
        index_run_id=index_id,index_recipe_hash=index['recipe_hash'],
        index_inputs={x['name']:dict(bytes=x['bytes'],sha256=x['sha256']) for x in index['recipe']['files']},
        index_outputs={name:identity(files[name]) for name in ['analysis.state.json','source_provenance.json','derived/result.json','derived/members.ndjson','derived/identity_before.json']},
        member=member,archive_sha256=result['full_compressed_sha256'],
        archive_decoded_bytes=result['decoded_bytes_produced'])
    dump(HERE/'source_binding.json',binding)
    prefix=json.loads((INDEX/'index_config.json').read_text())
    config=dict(expected_hostname='thu-wei',expected_uid=596,archive=result['archive_identity_before_after'],
        compressed_max_bytes=result['compressed_bytes_read'],decoded_max_bytes=result['decoded_bytes_produced']+65536,
        verified_prefix_bytes=prefix['verified_prefix_bytes'],verified_prefix_sha256=prefix['verified_prefix_sha256'],
        internal_wall_seconds=840,target_cell='DFCNQD1BWP12T30P140',target_pins=['D','CP','CDN','Q'],
        selected_string_max_bytes=65536,table_value_max_count=4096,selected_group_max_count=2048,
        semantic_result_max_bytes=1024*1024,model_pairing_claim=False)
    dump(HERE/'semantic_config.json',config)
    references=dict(cases={case:compact(case) for case in ['baseline','rck2k']},
        actual_effective_Q_load_F=None,actual_load='Unchanged three native first-hop transistor/RC networks, not a fitted lumped capacitance',
        interpretation='Recompute arbitrary declared Liberty percent crossings at exact original native points/brackets. Raw intervals only; no assumed slew-derate formula.')
    dump(HERE/'native_references.json',references)
    byname={x['name']:x for x in source['recipe']['files']}
    inputs=[(n,HERE/n) for n in ['source_semantics.py','liberty_semantics.py','measured_comparison.py',
        'source_binding.json','semantic_config.json','native_references.json','native_baseline.bin.gz','native_rck2k.bin.gz']]
    inputs += [('archive_index.py',INDEX/'archive_index.py'),('source_audit.py',INDEX/'source_audit.py'),
        ('external_library.json',ROOT/byname['external_library.json']['source'])]
    spec=dict(schema_version=1,kind='analysis_only',source_run_id=source_id,
        run_id='sar8audit-ctrl-ff-liberty-semantics-v1',design_id='native_DFF_indexed_FF_Liberty_conditions',
        entry='source_semantics.py',analyzer='source_semantics.py',
        inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in inputs],
        expected_stop_s=20e-9,summary_signals=['XDUT.U19_CK','XDUT.U19_D','XDUT.XU19.RN'],
        qualification_scope='Read exact indexed FF text member and selected DFF semantics; full archive SHA/CRC same pass, compact native-pin threshold reference only, no library copy/db decode/new simulation/compatibility or reliability qualification',
        oa_parity='read_only_dependency_audit',test_conditions=source['recipe']['test_conditions'],
        resources=dict(threads=1,analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=4,
            analysis_wall_seconds=900,queue_timeout_seconds=600))
    dump(HERE/'recipe.suggested.yaml',spec)
    print('LOCAL_INDEXED_LIBERTY_PACKAGE_PREPARED',base.digest((HERE/'recipe.suggested.yaml').read_bytes()),
        'inputs_bytes',sum(p.stat().st_size for n,p in inputs))


if __name__=='__main__':main()
