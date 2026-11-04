"""Instance-scoped native info parser; model identifiers never activate a scope."""
from __future__ import print_function
import re

TARGET='XDUT.XU19.XFF.MM65'
INSTANCE=re.compile(r'^Instance:\s+(\S+)\s+of\s+(\S+)\s*$')
MODEL=re.compile(r'^Model:\s+(\S+)\s*$')
FIELD=re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$')
NUMBER=re.compile(r'^([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)(.*)$')


def target_instance(name):return name.lower()==TARGET.lower() or name.lower().startswith(TARGET.lower()+'.')


def parse_op_lines(lines):
    scopes={};active=None;last_line=0
    for number,line in lines:
        last_line=number
        if len(line)>4096:raise ValueError('Native info line bound exceeded')
        header=INSTANCE.match(line.strip())
        if header:
            if active is not None:scopes[active]['scope_last_line']=number-1
            active=None;name=header.group(1)
            if target_instance(name):
                if name in scopes:raise ValueError('Repeated explicit target Instance header')
                scopes[name]=dict(instance=name,master=header.group(2),scope_first_line=number,scope_last_line=None,model_identifier=None,fields={})
                active=name
            continue
        if active is None:continue
        model=MODEL.match(line.strip())
        if model:
            scopes[active]['model_identifier']=model.group(1)  # full binned name, including numeric suffix
            continue
        match=FIELD.match(line)
        if not match:continue
        name=match.group(1);render=match.group(2)
        if name in scopes[active]['fields']:raise ValueError('Repeated OP field in one explicit Instance scope')
        numeric=NUMBER.match(render);unit=None
        if numeric:
            tail=numeric.group(2).strip()
            if tail and re.match(r'^[A-Za-z][A-Za-z0-9*/.^-]{0,31}$',tail):unit=tail
        item=dict(explicit_unit=unit,line=number,
            unit_status='reported_unit_token' if unit else 'enumerated_value' if not numeric else 'not_explicitly_reported')
        if name.lower() in ['ids','id']:item['value_as_rendered']=render
        scopes[active]['fields'][name]=item
        if len(scopes[active]['fields'])>256:raise ValueError('Target OP field bound exceeded')
    if active is not None:scopes[active]['scope_last_line']=last_line
    for s in scopes.values():
        s['exposed_field_names']=sorted(s['fields']);s['field_count']=len(s['fields'])
    return dict(status='explicit_instance_scopes_parsed' if scopes else 'target_instance_header_not_found',
        target_instance_scopes=scopes,model_identifiers_are_not_instance_aliases=True,
        ids_id_values_are_named_only=True,pure_channel_current_identified=False,
        static_OP_time_not_assigned=True)


def parse_nodes_lines(lines):
    active=None;reports={}
    for number,line in lines:
        header=re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s+(\S+)\s+of\s+(\S+)\s*$',line.strip())
        if header:
            active=None;name=header.group(2)
            if target_instance(name):
                if name in reports:raise ValueError('Repeated target terminal block')
                active=name;reports[name]=dict(instance=name,primitive=header.group(1),master=header.group(3),header_line=number,ports={})
            continue
        if active is None:continue
        port=re.match(r'^\s*([dgbs])\s*:\s*(\S+)\s*$',line)
        if port:
            name=port.group(1)
            if name in reports[active]['ports']:raise ValueError('Repeated target port')
            reports[active]['ports'][name]=dict(node=port.group(2),line=number)
    return dict(status='explicit_primitive_port_blocks_parsed' if reports else 'target_terminal_header_not_found',instances=reports)


def read_op(path):
    with open(path,'r') as f:return parse_op_lines(enumerate(f,1))


def read_nodes(path):
    with open(path,'r') as f:return parse_nodes_lines(enumerate(f,1))
