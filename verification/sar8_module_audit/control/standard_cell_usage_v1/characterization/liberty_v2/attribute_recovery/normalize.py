"""Sourced slew-coordinate appendix; never edits frozen/raw comparison artifacts."""
import copy
import json
import math
from recover import HERE,ROOT,identity,dump,record,receipt_files

URL='https://www.paripath.com/blog/characterization-blog/demystifying-slew-derate'


def main():
    scalar=json.loads((HERE/'original_scalar.json').read_bytes())
    recovered=json.loads((HERE/'recovered_attributes.json').read_bytes())
    source_run=scalar['source_run'];rec=record(source_run)
    assert rec['recipe_hash']==scalar['source_recipe_hash']
    folder=ROOT/'output/managed_execution/runs'/source_run/'collected'
    receipt,files=receipt_files(folder)
    assert identity(files['derived/result.json'])==scalar['source_result']
    assert identity(folder/'collection_receipt.json')['sha256']==scalar['source_receipt_sha256']
    assert recovered['full_string_coverage'] and recovered['original_scalar_sha256']==scalar['raw_scalar_UTF8_sha256']
    comparison=json.loads((HERE/'native_threshold_comparison.json').read_bytes())
    semantic=json.loads((HERE/'derived_semantics.json').read_bytes())
    attrs=semantic['library_attributes']
    assert attrs['slew_derate_from_library']==.5
    assert attrs['time_unit']=='1ns' and attrs['capacitive_load_unit']==[1.,'pf']
    source=dict(title='Demystifying Slew Derate',publisher='Paripath Inc.',
                url=URL,read_date='2026-10-27',
                definition='library_threshold_interval = slew_derate_from_library * library_slew_coordinate',
                applied_equation='library_slew_coordinate = measured_library_threshold_interval / explicit_derate',
                scope='Input transition coordinates only; not a reconstruction of the nonlinear waveform at10/90 thresholds.')
    edges={}
    for case,pins in comparison['actual_edges'].items():
        edges[case]={}
        for pin,directions in pins.items():
            edges[case][pin]={}
            for edge,measurement in directions.items():
                basis=comparison['threshold_basis'][pin][edge]
                factor=basis['slew_derate_from_library']['value']
                thresholds=[basis['slew_'+side+'_threshold_pct_'+edge]['value'] for side in ['lower','upper']]
                assert thresholds==[30.,70.] and isinstance(factor,(float,int)) and math.isfinite(factor) and factor>0
                events=measurement['events']
                assert events and all(e['status']=='measured_raw_threshold_interval' and e['raw_interval_s'] is not None for e in events)
                raw=[e['raw_interval_s'] for e in events]
                assert [min(raw),max(raw)]==measurement['raw_range_s']
                edges[case][pin][edge]=dict(raw_threshold_pct=thresholds,explicit_derate=factor,
                    raw_range_s=measurement['raw_range_s'],normalized_coordinate_range_s=[min(raw)/factor,max(raw)/factor],
                    event_count=len(events),derate_scope=basis['slew_derate_from_library']['source'],
                    events=[dict(native_50pct_time_s=e['halfrail']['time_s'],raw_interval_s=e['raw_interval_s'],
                                 normalized_coordinate_s=e['raw_interval_s']/factor,
                                 native_lower_bracket_s=e['lower']['native_bracket_s'],
                                 native_upper_bracket_s=e['upper']['native_bracket_s']) for e in events])
    relations=[];time_axes=0;all_within=True
    for original in comparison['axis_relations']:
        row={k:copy.deepcopy(v) for k,v in original.items() if k!='raw_interval_relations'}
        pin=row.get('mapped_reference_pin');edge=row.get('mapped_edge')
        if pin in comparison['threshold_basis'] and 'axis_range_s' in row:
            row['normalized_coordinate_relations']={}
            for case,pins in edges.items():
                selected=[pins[pin][e] for e in ([edge] if edge else ['rise','fall'])]
                low=min(x['normalized_coordinate_range_s'][0] for x in selected)
                high=max(x['normalized_coordinate_range_s'][1] for x in selected)
                bounds=row['axis_range_s']
                within=bounds[0]<=low and high<=bounds[1]
                row['normalized_coordinate_relations'][case]=dict(normalized_range_s=[low,high],
                    below_declared_axis_min=low<bounds[0],above_declared_axis_max=high>bounds[1],
                    all_sampled_edges_within_declared_axis=within,
                    interpretation='Coordinate containment only; conditional timing, load, PDK pairing and stress remain separate.')
                all_within=all_within and within
            time_axes+=1
        relations.append(row)
    inputs={name:identity(HERE/name) for name in ['original_scalar.json','recovered_attributes.json',
        'derived_semantics.json','native_threshold_comparison.json','recovery_status.json','recover.py']}
    output=dict(status='sourced_coordinate_appendix_complete',normalization_source=source,
        source_run=source_run,source_recipe_hash=rec['recipe_hash'],input_identities=inputs,
        source_result_and_receipt_unchanged=True,all_registered_source_input_hashes_verified=True,
        original_raw_axis_comparison_is_not_a_usage_violation=True,
        raw_stage_status_file_kept_unmodified=True,edge_ranges=edges,axis_relations=relations,
        mapped_input_transition_axes=time_axes,all_sampled_normalized_input_coordinates_within_axes=all_within,
        declared_input_transition_axis_range_s=[1.5e-12,262.9e-12],
        declared_Q_load_range_F=[.41e-15,102.31e-15],effective_actual_Q_load_F=None,
        declared_default_max_transition_s=attrs['default_max_transition']*1e-9,
        archive_label='180a',literal_revision=attrs['revision'],formal_PDK_compatibility_proven=False,
        full_conditional_timing_checks_completed=False,absolute_device_stress_qualification=False,
        actual_native10_90_slew_not_replaced=True,new_library_read=False,new_simulation=False)
    assert time_axes>0
    dump('normalized_coordinate.json',output)
    print(json.dumps(dict(status=output['status'],mapped_input_transition_axes=time_axes,
        all_normalized_input_coordinates_within_axes=all_within,
        ranges_ps={c:{p:{e:dict(raw=[v*1e12 for v in r['raw_range_s']],
            normalized=[v*1e12 for v in r['normalized_coordinate_range_s']])
            for e,r in es.items()} for p,es in ps.items()} for c,ps in edges.items()}),sort_keys=True))


if __name__=='__main__':main()
