"""Managed source-bound dependency index; Python2.7/3; no simulator/tool launch."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import resource
import socket
import stat
import sys
import time
import archive_index as parser
sys.dont_write_bytecode=True


def read(path,cap=1024*1024):
    if os.path.getsize(path)>cap:raise ValueError('Small metadata read bound exceeded')
    with open(path) as f:return json.load(f)


def identity(path,cap=32*1024**2):
    before=os.stat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_size>cap:raise ValueError('Unexpected dependency file type/size')
    h=hashlib.sha256();count=0
    with open(path,'rb') as f:
        while True:
            blob=f.read(parser.CHUNK)
            if not blob:break
            h.update(blob);count+=len(blob)
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):raise ValueError('Read-only identity changed')
    return dict(bytes=count,sha256=h.hexdigest())


def inside(path,root):return path==root or path.startswith(root+os.sep)
def safe_file(root,rel):
    path=os.path.realpath(os.path.join(root,rel))
    if not inside(path,root) or os.path.islink(os.path.join(root,rel)) or not os.path.isfile(path):raise ValueError('Unsafe/missing managed source file:'+rel)
    return path


def verify_source(run,source,binding):
    if os.path.basename(source)!=binding['source_run_id']:raise ValueError('Source run mismatch')
    rec=read(safe_file(source,'recipe.json'))
    digest=hashlib.sha256(json.dumps(rec,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    if digest!=binding['source_recipe_hash'] or rec.get('kind','simulation')!='simulation':raise ValueError('Source canonical recipe mismatch')
    reg=read(safe_file(source,'registered.json'));state=read(safe_file(source,'simulation.state.json'))
    if reg.get('recipe_hash')!=digest or not reg.get('files_complete'):raise ValueError('Source registration mismatch')
    native=state.get('native',{})
    if state.get('status')!='complete' or state.get('exit_code')!=0 or not native.get('native_analysis_pass') or not native.get('zero_error_footer'):raise ValueError('Real completed source native PASS/footer required')
    with open(safe_file(source,'raw/logStatus')) as f:
        if not re.search(r'\btran_first\s+PASS\b',f.read(65536)):raise ValueError('Source native transient PASS missing')
    prov=read(safe_file(run,'source_provenance.json'))
    if prov.get('run_id')!=binding['source_run_id'] or prov.get('recipe_hash')!=digest or os.path.realpath(prov.get('path',''))!=source:raise ValueError('Managed source provenance mismatch')
    hashes={}
    for rel,key in [('recipe.json','recipe_file_sha256'),('registered.json','registration_sha256'),('simulation.state.json','simulation_state_sha256')]:
        hashes[rel]=identity(safe_file(source,rel))
        if prov.get(key)!=hashes[rel]['sha256']:raise ValueError('Managed source metadata SHA mismatch')
    for name,want in binding['source_inputs'].items():
        if identity(safe_file(source,'inputs/'+name))!=want:raise ValueError('Frozen source input changed:'+name)
    for rel in ['spectre.out','raw/logStatus']:hashes[rel]=identity(safe_file(source,rel))
    return dict(run_id=binding['source_run_id'],recipe_hash=digest,source_metadata=hashes,
        source_native_PASS=True,source_read_only=True,source_raw_read=False,
        original_analysis_success_not_required='Dependency audit, not waveform recovery; actual source simulation completion is required')


def write_atomic(path,obj,cap):
    blob=(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(blob)>cap:raise ValueError('Small JSON output bound exceeded')
    temp=path+'.writing'
    if os.path.lexists(temp):raise ValueError('Preserve previous checkpoint temp')
    with open(temp,'wb') as f:f.write(blob)
    os.rename(temp,path)


class IndexSink(object):
    def __init__(self,path,cap):self.f=open(path,'wb');self.cap=cap;self.bytes=0
    def emit(self,row):
        blob=(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
        if self.bytes+len(blob)>self.cap:raise parser.BoundReached('index_metadata_output_bytes')
        self.f.write(blob);self.f.flush();self.bytes+=len(blob)
    def close(self):self.f.close()


def fingerprint(path):
    s=os.stat(path)
    if not stat.S_ISREG(s.st_mode):raise ValueError('Archive must be a regular file')
    return dict(path=path,realpath=os.path.realpath(path),bytes=s.st_size,mtime_epoch=s.st_mtime,inode=s.st_ino,device=s.st_dev)


def audit(run,output,source):
    run,output,source=[os.path.realpath(p) for p in [run,output,source]]
    if inside(run,source) or inside(source,run) or output!=os.path.join(run,'derived'):raise ValueError('Fresh disjoint managed output required')
    if os.path.isdir(output) and os.listdir(output):raise ValueError('Preserve previous index/checkpoint; no repeat scan')
    binding=read(safe_file(run,'inputs/source_binding.json'));cfg=read(safe_file(run,'inputs/index_config.json'))
    if os.getuid()!=cfg['expected_uid'] or socket.gethostname()!=cfg['expected_hostname']:raise ValueError('Unexpected dependency audit host/UID')
    proof=verify_source(run,source,binding)
    external=read(safe_file(source,'inputs/external_library.json'))
    if identity(safe_file(run,'inputs/external_library.json'))!=binding['source_inputs']['external_library.json']:raise ValueError('Audited library metadata differs from real source')
    libwant=dict(bytes=external['bytes'],sha256=external['sha256'])
    if identity(external['file'])!=libwant:raise ValueError('Real source SPICE library changed')
    dependency_proof={external['file']:libwant}
    for path,want in external['model_files'].items():
        if identity(path)!=want:raise ValueError('Real source PDK dependency changed')
        dependency_proof[path]=want
    archive=cfg['archive']['path'];before=fingerprint(archive)
    if before['bytes']!=cfg['archive']['bytes'] or before['mtime_epoch']!=cfg['archive']['mtime_epoch']:raise ValueError('Known archive identity changed')
    if not os.path.isdir(output):os.makedirs(output)
    write_atomic(os.path.join(output,'identity_before.json'),dict(hostname=socket.gethostname(),uid=os.getuid(),source=proof,library_and_PDK=dependency_proof,archive=before),cfg['small_json_max_bytes'])
    sink=IndexSink(os.path.join(output,'members.ndjson'),cfg['index_metadata_max_bytes'])
    handle=open(archive,'rb');stream=parser.GzipStream(handle,before['bytes'],cfg)
    checkpoint_path=os.path.join(output,'checkpoint.json')
    def checkpoint(value):write_atomic(checkpoint_path,value,cfg['checkpoint_max_bytes'])
    try:result=parser.scan(stream,cfg,sink.emit,checkpoint)
    finally:sink.close();handle.close()
    if fingerprint(archive)!=before:raise ValueError('Read-only archive metadata changed during index')
    if verify_source(run,source,binding)!=proof:raise ValueError('Real source evidence changed during dependency audit')
    for path,want in dependency_proof.items():
        if identity(path)!=want:raise ValueError('Real source library/PDK identity changed during audit')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    if rss>cfg['RSS_max_bytes']:raise ValueError('Audit peak RSS exceeded256MiB')
    result.update(audit_finished=True,analysis_complete=result['archive_index_complete'],
        hostname=socket.gethostname(),uid=os.getuid(),
        analysis_kind='source_bound_library_dependency_archive_index',source=proof,
        library_and_PDK=dependency_proof,archive_identity_before_after=before,
        index_metadata_bytes=sink.bytes,peak_RSS_bytes=rss,
        no_library_body_retention=True,no_db_loaded=True,no_files_extracted=True,
        no_new_simulation=True,library_PDK_compatibility_proven=False,
        Liberty_values_obtained=False,summary_lists_limited_to_first_matches=dict(FF=8,release=16,text_Liberty=8),
        partial_index_is_not_resume_instruction=True,no_automatic_retry=True)
    write_atomic(os.path.join(output,'result.json'),result,cfg['small_json_max_bytes'])
    if sum(os.path.getsize(os.path.join(output,n)) for n in os.listdir(output))>cfg['derived_total_max_bytes']:raise ValueError('Derived metadata budget exceeded')
    return result


def main():
    ap=argparse.ArgumentParser()
    for key in ['run-dir','output-dir','source-run-dir']:ap.add_argument('--'+key,required=True)
    a=ap.parse_args();r=audit(a.run_dir,a.output_dir,a.source_run_dir)
    print('DEPENDENCY_INDEX_AUDIT_FINISHED',r['index_status'],'archive_complete',r['archive_index_complete'],'headers',r['indexed_headers'])
    if r['index_status']=='incomplete_read_error':raise SystemExit(1)


if __name__=='__main__':main()
