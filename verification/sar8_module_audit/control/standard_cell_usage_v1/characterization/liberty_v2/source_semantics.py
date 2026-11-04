"""Managed indexed-member semantic audit. Python2.7/3; never launches tools."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import resource
import socket
import sys
import zlib
import archive_index as archive
import source_audit as bound
import liberty_semantics as liberty
import measured_comparison as measured
import header_reader
sys.dont_write_bytecode=True


class Member(object):
    def __init__(self,stream,size,notify=None):
        self.stream=stream;self.size=size;self.remaining=size;self.count=0
        self.digest=hashlib.sha256();self.notify=notify;self.next_notice=64*1024**2
    def read_some(self,size):
        if not 0<size<=65536:raise ValueError('Member read must be bounded')
        if not self.remaining:return b''
        blob=self.stream.read_some(min(size,self.remaining))
        if not blob:raise archive.InvalidArchive('Indexed Liberty member truncated')
        self.remaining-=len(blob);self.count+=len(blob);self.digest.update(blob)
        if self.notify and self.count>=self.next_notice:
            self.notify();self.next_notice=self.count+64*1024**2
        return blob


def verify_index(source,binding):
    root=os.path.realpath(os.path.join(os.path.dirname(source),binding['index_run_id']))
    if os.path.basename(root)!=binding['index_run_id']:raise ValueError('Unexpected completed index path')
    recipe=bound.read(bound.safe_file(root,'recipe.json'))
    digest=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if digest!=binding['index_recipe_hash'] or recipe.get('kind')!='analysis_only':raise ValueError('Index canonical recipe mismatch')
    if recipe.get('source',{}).get('run_id')!=binding['source_run_id'] or recipe['source']['recipe_hash']!=binding['source_recipe_hash']:raise ValueError('Index does not audit the same real baseline')
    reg=bound.read(bound.safe_file(root,'registered.json'));state=bound.read(bound.safe_file(root,'analysis.state.json'))
    if reg.get('recipe_hash')!=digest or not reg.get('files_complete') or state.get('status')!='complete' or state.get('exit_code')!=0:raise ValueError('Completed registered index required')
    for name,want in binding['index_inputs'].items():
        if bound.identity(bound.safe_file(root,'inputs/'+name))!=want:raise ValueError('Frozen index input changed')
    for rel,want in binding['index_outputs'].items():
        if bound.identity(bound.safe_file(root,rel))!=want:raise ValueError('Completed index evidence changed:'+rel)
    result=bound.read(bound.safe_file(root,'derived/result.json'))
    if not result['archive_index_complete'] or not result['gzip_integrity_verified'] or result['full_compressed_sha256']!=binding['archive_sha256']:raise ValueError('Index was not a complete integrity-verified archive audit')
    matches=[];previous=None;predecessor=None
    with open(bound.safe_file(root,'derived/members.ndjson')) as f:
        for line in f:
            row=json.loads(line)
            if row['name']==binding['member']['name']:matches.append(row);predecessor=previous
            previous=row
    if matches!=[binding['member']]:raise ValueError('Exact indexed member identity differs')
    if predecessor!=binding['predecessor']:raise ValueError('Exact indexed predecessor differs')
    return dict(index_run_id=binding['index_run_id'],index_recipe_hash=digest,
        archive_index_complete=True,gzip_integrity_verified=True,
        archive_sha256=result['full_compressed_sha256'],member=matches[0],predecessor=predecessor)


def audit(run,output,source):
    run,output,source=[os.path.realpath(p) for p in [run,output,source]]
    if bound.inside(run,source) or bound.inside(source,run) or output!=os.path.join(run,'derived'):raise ValueError('Fresh disjoint managed output required')
    if os.path.isdir(output) and os.listdir(output):raise ValueError('Preserve previous semantics/checkpoint; no automatic repeat')
    binding=bound.read(bound.safe_file(run,'inputs/source_binding.json'))
    cfg=bound.read(bound.safe_file(run,'inputs/semantic_config.json'))
    if os.getuid()!=cfg['expected_uid'] or socket.gethostname()!=cfg['expected_hostname']:raise ValueError('Unexpected audit host/UID')
    source_proof=bound.verify_source(run,source,binding);index_proof=verify_index(source,binding)
    external=bound.read(bound.safe_file(source,'inputs/external_library.json'))
    if bound.identity(bound.safe_file(run,'inputs/external_library.json'))!=binding['source_inputs']['external_library.json']:raise ValueError('Source library metadata differs')
    deps={external['file']:dict(bytes=external['bytes'],sha256=external['sha256'])}
    deps.update(external['model_files'])
    for path,want in deps.items():
        if bound.identity(path)!=want:raise ValueError('Actual source library/PDK changed')
    path=cfg['archive']['path'];before=bound.fingerprint(path)
    if before!=cfg['archive']:raise ValueError('Indexed archive fingerprint changed')
    if not os.path.isdir(output):os.makedirs(output)
    bound.write_atomic(os.path.join(output,'identity_before.json'),dict(source=source_proof,index=index_proof,library_and_PDK=deps,archive=before),65536)
    raw=open(path,'rb');stream=archive.GzipStream(raw,before['bytes'],cfg)
    member=None;semantic_parser=None;semantic=None;header_evidence=None;stage='known_prefix_skip';reason=None;status='incomplete'
    def checkpoint():
        bound.write_atomic(os.path.join(output,'checkpoint.json'),dict(stage=stage,compressed_bytes_read=stream.compressed,
            decoded_bytes_consumed=stream.position,decoded_bytes_produced=stream.decoded,
            member_bytes_read=member.count if member else 0,
            member_semantic_bytes_consumed=semantic_parser.lex.total if semantic_parser else 0,
            library_target_cell_complete=bool(semantic_parser and semantic_parser.result.get('target_cell')),
            repeat_or_resume_authorized=False),65536)
    checkpoint()
    try:
        target=binding['member'];stage='indexed_gap_and_header_identity'
        header_evidence=header_reader.locate(stream,target,binding['predecessor'],cfg,checkpoint)
        bound.write_atomic(os.path.join(output,'header_evidence.json'),header_evidence,65536)
        if header_evidence['extension_bound_hit']:raise archive.BoundReached(header_evidence['extension_recovery_error'])
        if not header_evidence['all_required_fields_match']:raise archive.InvalidArchive('Indexed effective header fields mismatch; see header_evidence.json')
        stage='selected_Liberty_semantics';member=Member(stream,target['bytes'],checkpoint)
        semantic_parser=liberty.Semantics(member,cfg);semantic=semantic_parser.parse()
        if member.remaining:raise liberty.ParseError('Semantic parser did not consume the complete bounded member')
        stage='remaining_archive_integrity_drain';checkpoint()
        # Discard remaining decoded data in the SAME pass, without parsing the
        # directory again. This is not the tar-zero-only archive.drain method.
        next_notice=stream.position+256*1024**2
        while stream.read_some(65536):
            if stream.position>=next_notice:checkpoint();next_notice=stream.position+256*1024**2
        if not stream.done or not stream.gzip_end or stream.digest.hexdigest()!=binding['archive_sha256'] or stream.decoded!=binding['archive_decoded_bytes']:raise archive.InvalidArchive('Full indexed archive SHA/CRC/decoded count mismatch')
        stage='native_pin_threshold_comparison';checkpoint()
        refs=bound.read(bound.safe_file(run,'inputs/native_references.json'))
        for case,meta in refs['cases'].items():
            if bound.identity(bound.safe_file(run,'inputs/'+meta['file']))!=meta['compressed']:raise ValueError('Frozen compact native reference changed')
        comparison=measured.compare(semantic,refs,os.path.join(run,'inputs'))
        status='complete';stage='finished';checkpoint()
    except (archive.BoundReached,liberty.SemanticBound) as error:
        reason=str(error);status='incomplete_bound';comparison=None
    except (archive.InvalidArchive,liberty.ParseError,zlib.error) as error:
        reason=str(error);status='incomplete_parse_or_integrity_error';comparison=None
    finally:raw.close()
    if bound.fingerprint(path)!=before or bound.verify_source(run,source,binding)!=source_proof or verify_index(source,binding)!=index_proof:raise ValueError('Read-only source/index/archive identity changed')
    for path,want in deps.items():
        if bound.identity(path)!=want:raise ValueError('Source library/PDK changed during semantic audit')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    if rss>256*1024**2:raise ValueError('Semantic audit RSS exceeds256MiB')
    result=dict(analysis_kind='source_bound_indexed_FF_Liberty_semantics_header_v2',analysis_complete=status=='complete',
        status=status,stop_reason=reason,source=source_proof,index=index_proof,library_and_PDK=deps,
        archive_identity_before_after=before,full_archive_sha256_verified=status=='complete',
        compressed_bytes_read=stream.compressed,decoded_bytes_produced=stream.decoded,
        member=binding['member'],header_identity_evidence=header_evidence,member_bytes_read=member.count if member else 0,
        member_sha256=member.digest.hexdigest() if member and member.remaining==0 else None,
        semantic=semantic if status=='complete' else None,measured_comparison=comparison,
        target_cell_found=bool(semantic and semantic.get('target_cell')),peak_RSS_bytes=rss,
        no_library_body_copy=True,no_db_decode=True,no_directory_rescan=True,
        one_sequential_archive_pass=True,no_new_simulation=True,
        SPI170a_Liberty180a_pairing_proven=False,table_ranges_are_not_absolute_reliability_limits=True,
        whole_ADC_qualified=None)
    checkpoint()
    bound.write_atomic(os.path.join(output,'result.json'),result,cfg['semantic_result_max_bytes'])
    return result


def main():
    ap=argparse.ArgumentParser()
    for key in ['run-dir','output-dir','source-run-dir']:ap.add_argument('--'+key,required=True)
    args=ap.parse_args();result=audit(args.run_dir,args.output_dir,args.source_run_dir)
    print('INDEXED_FF_LIBERTY_SEMANTICS',result['status'],'target_found',result['target_cell_found'],'no_simulation')
    if result['status']=='incomplete_parse_or_integrity_error':raise SystemExit(1)


if __name__=='__main__':main()
