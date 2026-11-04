"""Recover only the exact indexed extension gap; Python2.7/3, metadata only."""
from __future__ import print_function
import hashlib
import json
import archive_index as archive


def small(value,cfg):
    if len(json.dumps(value,ensure_ascii=True))>cfg['extension_path_JSON_max_bytes']:
        raise archive.BoundReached('extension_path_output_bytes')
    return value


def extensions(blob,start,cfg):
    at=0;local={};global_gap={};long_name=None;long_link=None;records=[]
    while at<len(blob):
        if len(records)>=cfg['extension_records_max']:raise archive.BoundReached('extension_record_count')
        if at+512>len(blob):raise archive.InvalidArchive('Incomplete indexed extension header')
        block=blob[at:at+512];head=archive.header(block);body=at+512
        if head['type'] not in ['x','g','L','K']:raise archive.InvalidArchive('Indexed gap contains a non-extension header')
        if head['size']>cfg['extension_payload_max_bytes']:raise archive.BoundReached('extension_payload_bytes')
        end=body+head['size'];padded=body+((head['size']+511)//512)*512
        if padded>len(blob):raise archive.InvalidArchive('Extension crosses exact indexed metadata gap')
        payload=blob[body:end];parsed={}
        if head['type'] in ['x','g']:
            parsed=archive.pax_fields(payload)
            for key,value in parsed.items():
                if key in ['path','linkpath']:small(value,cfg)
                elif key=='size' and len(value)>32:raise archive.BoundReached('PAX_size_metadata_length')
            if head['type']=='g':global_gap.update(parsed)
            else:local=parsed
        elif head['type']=='L':long_name=small(archive.text(payload),cfg);parsed={'GNU_longname':long_name}
        else:long_link=small(archive.text(payload),cfg);parsed={'GNU_longlink':long_link}
        records.append(dict(decoded_header_offset=start+at,type=head['type'],metadata_name=head['name'],
            payload_bytes=head['size'],header_sha256=hashlib.sha256(block).hexdigest(),
            payload_sha256=hashlib.sha256(payload).hexdigest(),recognized_fields=parsed))
        at=padded
    fields=dict(global_gap);fields.update(local)
    return dict(records=records,PAX_fields=fields,local_PAX=local,gap_global_PAX=global_gap,
        GNU_longname=long_name,GNU_longlink=long_link,
        earlier_global_PAX_state_read=False,
        scope='Only extension records between the immediate indexed predecessor padded end and exact target header; no earlier directory rescan')


def locate(stream,target,predecessor,cfg,checkpoint):
    start=predecessor['decoded_body_offset']+((predecessor['bytes']+511)//512)*512
    stop=target['decoded_header_offset'];length=stop-start
    if predecessor['decoded_header_offset']>=stop or length<0:raise archive.InvalidArchive('Invalid exact indexed predecessor span')
    if length>cfg['metadata_gap_max_bytes']:raise archive.BoundReached('indexed_metadata_gap_bytes')
    if stream.position!=0:raise archive.InvalidArchive('Reader must start one fresh sequential pass')
    while stream.position<start:
        stream.skip(min(64*1024**2,start-stream.position));checkpoint()
    parts=[];remaining=length
    while remaining:
        block=stream.read_exact(min(65536,remaining));parts.append(block);remaining-=len(block)
    gap=b''.join(parts);actual_header_offset=stream.position
    raw=stream.read_exact(512);actual_body_offset=stream.position
    evidence=dict(indexed_predecessor=predecessor,metadata_gap_start=start,metadata_gap_bytes=length,
        metadata_gap_sha256=hashlib.sha256(gap).hexdigest(),target_header_sha256=hashlib.sha256(raw).hexdigest(),
        raw_name_field=archive.text(raw[:100]),raw_prefix_field=archive.text(raw[345:500]),
        raw_size_field=archive.text(raw[124:136]),raw_type_field=raw[156:157].decode('ascii','replace'),
        actual_decoded_header_offset=actual_header_offset,actual_decoded_body_offset=actual_body_offset,
        raw_header=None,recovered_fields=None,extension_evidence=None,header_decode_error=None,
        extension_recovery_error=None,extension_bound_hit=False,body_bytes_read=0,no_raw_gap_or_library_body_saved=True)
    try:
        head=archive.header(raw);evidence['raw_header']=head;evidence['raw_header_checksum_valid']=True
    except archive.InvalidArchive as error:
        head=None;evidence['raw_header_checksum_valid']=False;evidence['header_decode_error']=str(error)
    try:evidence['extension_evidence']=extensions(gap,start,cfg)
    except archive.BoundReached as error:
        evidence['extension_recovery_error']=str(error);evidence['extension_bound_hit']=True
    except archive.InvalidArchive as error:evidence['extension_recovery_error']=str(error)
    observed=dict(name=None,bytes=None,type=None,link_name=None,
        decoded_header_offset=actual_header_offset,decoded_body_offset=actual_body_offset)
    sources=dict(name='unresolved',bytes='unresolved',type='raw_header',link_name='unresolved',
        decoded_header_offset='stream_consumed_offset',decoded_body_offset='stream_consumed_offset')
    extension=evidence['extension_evidence']
    if head is not None and extension is not None:
        fields=extension['PAX_fields']
        name=fields.get('path',extension['GNU_longname'] or head['name'])
        size=head['size']
        if 'size' in fields:
            try:size=int(fields['size'])
            except ValueError:evidence['extension_recovery_error']='Invalid recovered PAX size';size=None
            if size is not None and size<0:evidence['extension_recovery_error']='Negative recovered PAX size';size=None
        link=fields.get('linkpath',extension['GNU_longlink'] or head['link_name'])
        observed.update(name=name,bytes=size,type=head['type'],link_name=link or None)
        sources.update(name='PAX.path' if 'path' in fields else 'GNU.longname' if extension['GNU_longname'] is not None else 'raw_USTAR_header',
            bytes='PAX.size' if 'size' in fields else 'raw_header_size',
            link_name='PAX.linkpath' if 'linkpath' in fields else 'GNU.longlink' if extension['GNU_longlink'] is not None else 'raw_header_link')
    evidence['recovered_fields']=observed
    comparisons={}
    for field in ['name','bytes','type','decoded_header_offset','decoded_body_offset','link_name']:
        value=observed[field];expected=target.get(field)
        comparisons[field]=dict(expected=expected,observed=value,match=value==expected,source=sources[field])
    evidence['comparisons']=comparisons
    evidence['all_required_fields_match']=bool(evidence['raw_header_checksum_valid'] and extension is not None
        and not evidence['extension_recovery_error'] and all(v['match'] for v in comparisons.values()))
    evidence['actual_extension_kind_established']=bool(extension and extension['records'])
    evidence['name_check_preserved']=True
    checkpoint()
    return evidence
