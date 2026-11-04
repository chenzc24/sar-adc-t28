"""Narrow pre-admission reader revision. Local only; frozen v1 reused unchanged."""
from pathlib import Path
import difflib
import json
import sys

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'liberty_v1'
OWN=HERE.parents[2]
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
import prepare_first_event as base
from review_standard_cell_storage_v2 import record,identity
from review_standard_cell_full_result import receipt_files


def dump(path,data):base.exact_write(path,json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Exact reader transform count differs:'+old[:70])
    return text.replace(old,new)


def main():
    v1_id='sar8audit-ctrl-ff-liberty-semantics-v1';prior=record(v1_id)
    assert prior['recipe_hash']=='a4a97646beb0fbd2033ff805ac83ac9c7ee787337b8d2443c3e38fa817dc17f9'
    folder=ROOT/'output/managed_execution/runs'/v1_id/'collected';receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==prior['recipe_hash']
    failed=json.loads(files['derived/result.json'].read_bytes());state=json.loads(files['analysis.state.json'].read_bytes())
    assert state['status']=='failed' and state['exit_code']==1 and failed['member_bytes_read']==0
    assert failed['stop_reason']=='Indexed tar header/body identity mismatch'
    index='sar8audit-ctrl-dependency-ccs-index-v1';rec=record(index)
    ip=ROOT/'output/managed_execution/runs'/index/'collected';_,indexfiles=receipt_files(ip)
    rows=[json.loads(line) for line in indexfiles['derived/members.ndjson'].read_text().splitlines()]
    binding=json.loads((OLD/'source_binding.json').read_text());k=rows.index(binding['member'])
    assert k>0;binding['predecessor']=rows[k-1]
    dump(HERE/'source_binding.json',binding)
    start=binding['predecessor']['decoded_body_offset']+((binding['predecessor']['bytes']+511)//512)*512
    gap=binding['member']['decoded_header_offset']-start
    assert gap==1024
    dump(HERE/'v1_failure_reference.json',dict(prior_run_id=v1_id,prior_recipe_hash=prior['recipe_hash'],
        collected_evidence={n:identity(files[n]) for n in ['analysis.state.json','derived/result.json','derived/checkpoint.json']},
        actual_error=failed['stop_reason'],actual_member_bytes_read=0,
        actual_decoded_consumed=json.loads(files['derived/checkpoint.json'].read_bytes())['decoded_bytes_consumed'],
        metadata_gap_bytes=gap,actual_mismatched_field='not recorded in v1; GNU/PAX remains hypothesis until new read',
        frozen_v1_preserved=True,no_remote_read_started=True))
    config=json.loads((OLD/'semantic_config.json').read_text())
    config.update(metadata_gap_max_bytes=128*1024,extension_payload_max_bytes=65536,extension_records_max=16,extension_path_JSON_max_bytes=1024)
    dump(HERE/'semantic_config.json',config)
    original=(OLD/'source_semantics.py').read_text();text=original
    text=replace(text,'import measured_comparison as measured','import measured_comparison as measured\nimport header_reader')
    text=replace(text,'    matches=[]\n','    matches=[];previous=None;predecessor=None\n')
    text=replace(text,"            if row['name']==binding['member']['name']:matches.append(row)",
        "            if row['name']==binding['member']['name']:matches.append(row);predecessor=previous\n            previous=row")
    text=replace(text,"    if matches!=[binding['member']]:raise ValueError('Exact indexed member identity differs')",
        "    if matches!=[binding['member']]:raise ValueError('Exact indexed member identity differs')\n    if predecessor!=binding['predecessor']:raise ValueError('Exact indexed predecessor differs')")
    text=replace(text,"archive_sha256=result['full_compressed_sha256'],member=matches[0])",
        "archive_sha256=result['full_compressed_sha256'],member=matches[0],predecessor=predecessor)")
    text=replace(text,"member=None;semantic_parser=None;semantic=None;stage='known_prefix_skip';reason=None;status='incomplete'",
        "member=None;semantic_parser=None;semantic=None;header_evidence=None;stage='known_prefix_skip';reason=None;status='incomplete'")
    oldblock="""        target=binding['member'];offset=target['decoded_header_offset']
        while stream.position<offset:
            stream.skip(min(64*1024**2,offset-stream.position));checkpoint()
        head=archive.header(stream.read_exact(512))
        if head['name']!=target['name'] or head['size']!=target['bytes'] or head['type']!=target['type'] or stream.position!=target['decoded_body_offset']:raise archive.InvalidArchive('Indexed tar header/body identity mismatch')"""
    newblock="""        target=binding['member'];stage='indexed_gap_and_header_identity'
        header_evidence=header_reader.locate(stream,target,binding['predecessor'],cfg,checkpoint)
        bound.write_atomic(os.path.join(output,'header_evidence.json'),header_evidence,65536)
        if header_evidence['extension_bound_hit']:raise archive.BoundReached(header_evidence['extension_recovery_error'])
        if not header_evidence['all_required_fields_match']:raise archive.InvalidArchive('Indexed effective header fields mismatch; see header_evidence.json')"""
    text=replace(text,oldblock,newblock)
    text=replace(text,"analysis_kind='source_bound_indexed_FF_Liberty_semantics'","analysis_kind='source_bound_indexed_FF_Liberty_semantics_header_v2'")
    text=replace(text,"member=binding['member'],member_bytes_read=member.count if member else 0,",
        "member=binding['member'],header_identity_evidence=header_evidence,member_bytes_read=member.count if member else 0,")
    base.exact_write(HERE/'source_semantics.py',text)
    base.exact_write(HERE/'reader_delta.diff',''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='frozen_liberty_v1/source_semantics.py',tofile='liberty_v2/source_semantics.py')))
    spec=json.loads((OLD/'recipe.suggested.yaml').read_text())
    spec['run_id']='sar8audit-ctrl-ff-liberty-semantics-v2'
    spec['design_id']='native_DFF_indexed_FF_Liberty_header_recovery'
    spec['qualification_scope']='Narrow exact indexed predecessor-gap GNU/PAX header reader recovery; all effective name/size/type/offset/link checks retained and recorded, frozen semantic/reference modules reused, no library body copy/new simulation/compatibility qualification'
    revised=[]
    for item in spec['inputs']:
        path=HERE/item['name'] if item['name'] in ['source_semantics.py','source_binding.json','semantic_config.json'] else ROOT/item['source']
        revised.append(dict(name=item['name'],source=path.relative_to(ROOT).as_posix(),sha256=base.digest(path.read_bytes())))
    revised.append(dict(name='header_reader.py',source=(HERE/'header_reader.py').relative_to(ROOT).as_posix(),sha256=base.digest((HERE/'header_reader.py').read_bytes())))
    spec['inputs']=revised
    dump(HERE/'recipe.suggested.yaml',spec)
    print('LOCAL_HEADER_READER_V2_PREPARED',base.digest((HERE/'recipe.suggested.yaml').read_bytes()),'metadata_gap',gap,'no_remote')


if __name__=='__main__':main()
