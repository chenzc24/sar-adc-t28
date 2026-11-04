"""One actual-format check with explicit neighbor guards; no native run."""
from pathlib import Path
import json
import read_info_v2 as parser

HERE=Path(__file__).resolve().parent


def main():
    evidence=json.loads((HERE/'target_scope_v2.json').read_bytes())['metadata']['exact_files']
    op,nodes=evidence
    assert op['target_scope_start_line']==5002 and op['target_scope_last_line']==5107
    assert len(op['all_target_field_names'])==98==len(set(op['all_target_field_names']))
    # Original selected native lines plus deliberately synthetic adjacent scopes.
    rows=[(4896,'Instance: XDUT.XU19.XFF.NEIGHBOR_LEFT of nch_mac'),
          (4897,'Model: XDUT.XU19.XFF.MM65.nch.35'),(4965,'ids = 4.68775 nA')]
    rows += [(x['line'],x['text']) for x in op['explicit_headers']+op['selected_actual_format_lines']]
    rows += [(5004,'    d : XDUT.XU19.XFF.net176'),
             (5108,'Instance: XDUT.XU19.XFF.NEIGHBOR_RIGHT of nch_mac'),
             (5109,'Model: XDUT.XU19.XFF.MM65.nch.35'),(5177,'ids = 99 A')]
    parsed=parser.parse_op_lines(sorted(rows))
    assert list(parsed['target_instance_scopes'])==[parser.TARGET]
    target=parsed['target_instance_scopes'][parser.TARGET]
    assert target['model_identifier']=='XDUT.XU19.XFF.MM65.nch.35'
    assert target['scope_first_line']==5002 and target['scope_last_line']==5107
    assert target['field_count']==len(op['selected_actual_format_lines'])==14
    assert target['fields']['ids']['value_as_rendered']=='850.088 aA'
    assert target['fields']['id']['value_as_rendered']=='323.622 fA'
    assert target['fields']['ids']['explicit_unit']=='aA' and target['fields']['id']['explicit_unit']=='fA'
    assert target['fields']['region']['unit_status']=='enumerated_value'
    ports=parser.parse_nodes_lines((x['line'],x['text']) for x in nodes['selected_actual_format_lines'])
    actual=ports['instances'][parser.TARGET]
    assert actual['primitive']=='tmibsimbulk' and actual['master']=='nch_mac'
    assert {k:v['node'] for k,v in actual['ports'].items()}==dict(d='XDUT.XU19.XFF.net176',g='XDUT.XU19.XFF.mq',s='XDUT.XU19.XFF.net184',b='0')
    result=dict(status='one_focused_actual_format_check_pass',actual_native_selected_fields=14,
        all_native_target_field_names_observed=98,all_native_field_units_recovery_pending_parent_analysis=True,
        neighbor_guards_are_synthetic=True,neighbor_model_cannot_activate_target=True,node_paths_cannot_close_target=True,
        explicit_instance_scope=[5002,5107],model_identifier_retained_in_full=True,ports_confirmed=actual,
        parsed_selected_native_OP=parsed,pure_channel_inference=False,new_simulation=False)
    (HERE/'actual_format_check.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print('ACTUAL_FORMAT_SCOPE_AND_UNITS_CHECK_PASS',target['field_count'],'selected fields;98native names observed')


if __name__=='__main__':main()
