"""Bounded MM65 metadata extraction; no model bodies or pure-current inference."""
from __future__ import print_function
import hashlib
import os
import re

TARGET='XDUT.XU19.XFF.MM65'
PATH=re.compile(r'\bXDUT(?:\.[A-Za-z_][A-Za-z0-9_<>]*)+',re.I)
FIELD=re.compile(r'^\s*(?:\d+\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]{1,40})\))?\s*[=:]\s*(.*?)\s*$')
UNIT=re.compile(r'^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?\s*([fpnumkMG]?(?:A|V|S|F|C|Ohm|Hz))\b')


def is_target(path):return path.lower()==TARGET.lower() or path.lower().startswith(TARGET.lower()+'.')


def identity(path):
    h=hashlib.sha256();size=0
    with open(path,'rb') as f:
        while True:
            blob=f.read(65536)
            if not blob:break
            h.update(blob);size+=len(blob)
    return dict(bytes=size,sha256=h.hexdigest())


def scan(path,kind,cap):
    if not os.path.isfile(path):return dict(status='not_exposed_or_file_not_created',relative_file='raw/'+os.path.basename(path))
    if os.path.getsize(path)>cap:return dict(status='info_file_over_cap_not_read',bytes=os.path.getsize(path),cap=cap)
    before=os.stat(path);found=[];aliases=set();terminals=[];fields={};active=False
    with open(path,'r') as f:
        for line_no,line in enumerate(f,1):
            if len(line)>4096:return dict(status='info_line_over_cap_not_interpreted',identity=identity(path))
            paths=PATH.findall(line);target=[n for n in paths if is_target(n)]
            if paths:
                active=bool(target)
                if target:
                    aliases.update(target);found.append(line_no)
                    if len(found)>2000:raise ValueError('MM65 metadata occurrence bound exceeded')
            if kind=='nodes' and target:
                terminals.append(dict(line=line_no,text=line.strip()[:300]))
                if len(terminals)>32:raise ValueError('MM65 terminal evidence bound exceeded')
            if kind=='oppoint' and active:
                clean=line
                # A fully qualified field has an explicit name before its value.
                if target:
                    match=re.search(re.escape(target[0])+r'\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*[=:]\s*(.*)',line,re.I)
                    if match:clean=match.group(1)+' = '+match.group(2)
                match=FIELD.match(clean)
                if match:
                    name=match.group(1);render=match.group(3);unit=match.group(2)
                    if name.lower() in ['model','instance','type','device','component','primitive','parent','master']:continue
                    if unit is None:
                        explicit=UNIT.match(render);unit=explicit.group(1) if explicit else None
                    field=dict(explicit_unit=unit,unit_status='explicit_in_native_info' if unit else 'not_explicitly_identified',line=line_no)
                    if name.lower() in ['ids','id']:field['value_as_rendered']=render[:120]
                    if name in fields:
                        return dict(status='ambiguous_repeated_target_OP_field',field=name,identity=identity(path),target_aliases=sorted(aliases))
                    fields[name]=field
                    if len(fields)>256:raise ValueError('Target OP field bound exceeded')
    after=os.stat(path)
    if (before.st_size,before.st_mtime,before.st_ino)!=(after.st_size,after.st_mtime,after.st_ino):raise ValueError('Static info changed while reading')
    result=dict(status='target_metadata_found' if found else 'target_not_identified_in_info_format',identity=identity(path),
        target_aliases=sorted(aliases),target_evidence_lines=found)
    if kind=='nodes':result['native_terminal_to_node_lines']=terminals
    if kind=='oppoint':result.update(exposed_field_names=sorted(fields),fields=fields,
        field_parse_status='explicit_target_fields_parsed' if fields else 'no_fields_identified_do_not_infer_absence')
    if kind=='primitives':
        with open(path,'r') as f:
            result['native_primitive_type_lines']=[dict(line=i,text=line.strip()[:240]) for i,line in enumerate(f,1) if re.search(r'\b(?:tmibsimbulk|bsimbulk)\b',line,re.I)][:16]
    return result


def observe(run,cfg):
    raw=os.path.realpath(os.path.join(run,'raw'));reports={}
    for kind,name in cfg['info_files'].items():
        path=os.path.realpath(os.path.join(raw,name))
        if os.path.dirname(path)!=raw:raise ValueError('Info file leaves exact raw directory')
        reports[kind]=scan(path,kind,cfg['per_info_file_cap_bytes'])
    return dict(status='single_pass_native_field_exposure_diagnostic',target=TARGET,reports=reports,
        expected_public_ports_from_SPI=cfg['expected_public_ports_from_SPI'],
        values_are_named_observables_only=True,pure_channel_current_identified=False,
        actual_TMI_current_definition_verified=False,ids_id_are_not_an_acceptance_gate=True,
        OP_solution_time='Not assigned to5ns/5.5ns/5.95ns; metadata info outside timed tran snapshots',
        transient_OP_waveforms_added=False,model_parameter_bodies_returned=False,
        missing_fields_cause_no_automatic_retry=True,whole_ADC_qualified=None)
