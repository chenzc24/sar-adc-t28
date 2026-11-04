"""Strict derivation from retained scalar tokens; local only, no source reread."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import re
import sys

HERE=Path(__file__).resolve().parent
V2=HERE.parent
V1=V2.parent/'liberty_v1'
OWN=V2.parents[2]
ROOT=OWN.parents[2]
sys.path.insert(0,str(OWN))
from review_standard_cell_storage_v2 import record,identity
from review_standard_cell_full_result import receipt_files

NUMERIC=frozenset(['default_max_transition','default_inout_pin_cap','default_input_pin_cap','default_output_pin_cap',
    'slew_lower_threshold_pct_rise','slew_upper_threshold_pct_rise','slew_lower_threshold_pct_fall','slew_upper_threshold_pct_fall',
    'slew_derate_from_library','input_threshold_pct_rise','input_threshold_pct_fall','output_threshold_pct_rise','output_threshold_pct_fall'])
NUM=re.compile(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?\Z')
NAME=re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
UNIT=re.compile(r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?:W|mW|uW|nW|pW|fW)\Z')


class RecoveryError(ValueError):
    def __init__(self,message,offset,field=None):
        self.offset=offset;self.field=field
        super().__init__(message+' at offset '+str(offset)+((' field '+field) if field else ''))


def recover_scalar(raw,outer,existing):
    if outer not in NUMERIC or existing.get(outer)!=raw:raise RecoveryError('Outer retained scalar identity mismatch',0,outer)
    if len(raw.encode('utf-8'))>65536:raise RecoveryError('Retained scalar size bound',0,outer)
    at=0;values={};segments=[]
    def whitespace(pos):
        while pos<len(raw) and raw[pos].isspace():pos+=1
        return pos
    def literal(pos):
        end=pos
        while end<len(raw) and not raw[end].isspace():end+=1
        if end==pos:raise RecoveryError('Missing literal',pos)
        return raw[pos:end],end
    def add(name,token,start,end,value_start):
        if name in values:raise RecoveryError('Duplicate retained field',start,name)
        if name in existing and name!=outer:raise RecoveryError('Duplicate/conflicting independently retained field',start,name)
        if name in NUMERIC:
            if not NUM.fullmatch(token):raise RecoveryError('Expected complete numeric literal',value_start,name)
            value=float(token)
            if not math.isfinite(value):raise RecoveryError('Nonfinite numeric literal',value_start,name)
            if 'threshold_pct_' in name and not 0<=value<=100:raise RecoveryError('Percent outside0..100',value_start,name)
            if name=='slew_derate_from_library' and value<=0:raise RecoveryError('Nonpositive explicit derate',value_start,name)
            if name.startswith('default_') and value<0:raise RecoveryError('Negative explicit default',value_start,name)
            kind='explicit_named_numeric'
        elif name=='leakage_power_unit':
            if not UNIT.fullmatch(token):raise RecoveryError('Unsupported explicit unit literal',value_start,name)
            value=token;kind='explicit_typed_unit_not_a_numeric_condition'
        else:raise RecoveryError('Unknown field; refusing partial recovery',start,name)
        values[name]=value
        segments.append(dict(name=name,literal=token,value=value,kind=kind,span=[start,end],value_span=[value_start,end]))
    at=whitespace(at);token,end=literal(at);add(outer,token,at,end,at);at=end
    while whitespace(at)<len(raw):
        at=whitespace(at);start=at;match=NAME.match(raw,at)
        if not match:raise RecoveryError('Expected explicit field name',at)
        name=match.group(0);at=whitespace(match.end())
        if at>=len(raw) or raw[at]!=':':raise RecoveryError('Missing explicit colon',at,name)
        at=whitespace(at+1);value_start=at;token,end=literal(at)
        add(name,token,start,end,value_start);at=end
    at=whitespace(at)
    if at!=len(raw):raise RecoveryError('Unconsumed retained tokens',at)
    merged=dict(existing);merged.update(values)
    for edge in ['rise','fall']:
        lower=merged.get('slew_lower_threshold_pct_'+edge);upper=merged.get('slew_upper_threshold_pct_'+edge)
        if not isinstance(lower,(int,float)) or not isinstance(upper,(int,float)) or not 0<lower<upper<100:
            raise RecoveryError('Missing/invalid unambiguous slew threshold pair',len(raw),edge)
    return dict(recovered=values,segments=segments,full_string_coverage=True,consumed_characters=at,
        original_scalar_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        original_scalar_UTF8_bytes=len(raw.encode('utf-8')),unit_tail_only_typed_not_guessed=True)


def dump(name,obj):
    path=HERE/name;blob=(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    if path.exists() and path.read_bytes()!=blob:raise ValueError('Preserve existing derived artifact:'+name)
    path.write_bytes(blob)


def main():
    run='sar8audit-ctrl-ff-liberty-semantics-v2';rec=record(run)
    assert rec['recipe_hash']=='cc657c424bacb365f6c71c3dbc920297ff29e59c2d9c6053b260beeaae3f5be9'
    folder=ROOT/'output/managed_execution/runs'/run/'collected';receipt,files=receipt_files(folder)
    assert receipt['status']['registered']['recipe_hash']==rec['recipe_hash']
    result=json.loads(files['derived/result.json'].read_bytes())
    assert result['status']=='complete' and result['full_archive_sha256_verified']
    assert result['header_identity_evidence']['all_required_fields_match']
    semantic=result['semantic'];attributes=semantic['library_attributes'];outer='default_max_transition';raw=attributes[outer]
    assert isinstance(raw,str) and len(semantic['timing_arcs'])==15 and not semantic['unresolved_template_references']
    dump('original_scalar.json',dict(source_run=run,source_recipe_hash=rec['recipe_hash'],
        source_result=identity(files['derived/result.json']),source_receipt_sha256=identity(folder/'collection_receipt.json')['sha256'],
        member_sha256=result['member_sha256'],outer_attribute=outer,raw_scalar=raw,
        raw_scalar_UTF8_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        source_read_complete=True,source_attribute_extraction_complete=False,
        missing_threshold_dict_made_original_actual_edges_unusable=True))
    try:recovery=recover_scalar(raw,outer,attributes)
    except RecoveryError as error:
        dump('recovery_status.json',dict(status='refused_ambiguous_or_incomplete',error=str(error),
            offset=error.offset,field=error.field,no_condition_inference=True,remote_read=False));return
    dump('recovered_attributes.json',recovery)
    derived=copy.deepcopy(semantic);derived['library_attributes'].update(recovery['recovered'])
    files_byname={x['name']:ROOT/x['source'] for x in rec['recipe']['files']}
    reference_path=files_byname['native_references.json']
    references=json.loads(reference_path.read_bytes())
    for case,meta in references['cases'].items():
        path=files_byname[meta['file']]
        assert path.parent==reference_path.parent and identity(path)==meta['compressed']
    spec=importlib.util.spec_from_file_location('frozen_measured_comparison',files_byname['measured_comparison.py'])
    measured=importlib.util.module_from_spec(spec);spec.loader.exec_module(measured)
    comparison=measured.compare(derived,references,str(reference_path.parent))
    assert all(comparison['threshold_basis'][p][e]['raw_threshold_interval_available'] for p in ['CP','D','CDN'] for e in ['rise','fall'])
    assert all(comparison['actual_edges'][c][p][e].get('raw_range_s') is not None for c in references['cases'] for p in ['CP','D','CDN'] for e in ['rise','fall'])
    dump('derived_semantics.json',derived)
    dump('native_threshold_comparison.json',comparison)
    summary=dict(status='strict_small_evidence_recovery_complete',origin='Derived from retained v2 scalar, not reread of original Liberty',
        source_read_complete=True,source_attribute_extraction_complete=False,
        recovered_numeric_attributes=sum(x['kind']=='explicit_named_numeric' for x in recovery['segments']),
        recovered_explicit_unit=recovery['recovered'].get('leakage_power_unit'),
        library=derived['library'],literal_revision=derived['library_attributes']['revision'],
        archive_label='180a',formal_PDK_compatibility_proven=False,
        raw_threshold_pct=dict(rise=[recovery['recovered']['slew_lower_threshold_pct_rise'],recovery['recovered']['slew_upper_threshold_pct_rise']],
                              fall=[recovery['recovered']['slew_lower_threshold_pct_fall'],recovery['recovered']['slew_upper_threshold_pct_fall']]),
        explicit_slew_derate_from_library=recovery['recovered']['slew_derate_from_library'],derate_formula_applied=False,
        raw_slew_ranges_ps={case:{pin:{edge:[v*1e12 for v in comparison['actual_edges'][case][pin][edge]['raw_range_s']] for edge in ['rise','fall']} for pin in ['CP','D','CDN']} for case in references['cases']},
        all15_arcs_and_template_references_preserved=True,effective_actual_Q_load_F=None,
        table_axes_are_not_absolute_reliability_limits=True,new_archive_read=False,new_simulation=False)
    dump('recovery_status.json',summary)
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
