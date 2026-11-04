"""Local v2: correct Spectre save-name case, preserving every v1 circuit byte."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re

import build_d_fixture as d
from build_kickback_fixture import exact, js, sha

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE/'generated/kickback_v1'
NEW=HERE/'generated/kickback_v2'


def symbols(folder):
    """Resolve declared hierarchy and top-level primitives; preserve spelling."""
    definitions=d.blocks((folder/'cells.scs').read_text())
    definitions.update(d.blocks((folder/'cdac_load.scs').read_text()))
    devices,nodes={},set()
    for line in (folder/'test.scs').read_text().splitlines():
        match=re.fullmatch(r'(\w+)\s+\(([^)]*)\)\s+(\w+)(.*)',line)
        if match is None:continue
        name,args,master,params=match.groups();args=args.split();nodes.update(args)
        if master in definitions:
            pins=d.ports(definitions[master])
            if len(pins)!=len(args):raise ValueError('Top-level port mismatch: '+name)
            devices.update(d.flatten(definitions,master,dict(zip(pins,args)),prefix=name))
        else:
            devices[name]=dict(model=master,nodes=args,parameters=params.strip())
    for item in devices.values():nodes.update(item['nodes'])
    names={}
    for node in nodes:
        normalized=node.lower()
        if normalized in names and names[normalized]!=node:
            raise ValueError('Ambiguous normalized node spelling: '+node)
        names[normalized]=node
    instance_names={}
    for name in devices:
        normalized=name.lower()
        if normalized in instance_names:raise ValueError('Ambiguous normalized instance')
        instance_names[normalized]=name
    return names,instance_names,devices


def expected_saves(folder,cfg):
    nodes,instances,devices=symbols(folder)
    resolved={}
    for requested in cfg['voltage_saves']:
        if requested.lower() not in nodes:raise ValueError('Requested node absent: '+requested)
        resolved[requested]=nodes[requested.lower()]
    for requested in cfg['current_saves']:
        name,port=requested.rsplit(':',1)
        if name.lower() not in instances:raise ValueError('Requested device absent: '+name)
        actual=instances[name.lower()]
        if not 1<=int(port)<=len(devices[actual]['nodes']):raise ValueError('Invalid requested port: '+requested)
        resolved[requested]=actual+':'+port
    return resolved


def validate_saves(folder,cfg):
    expected=list(expected_saves(folder,cfg).values())
    actual=[line[5:] for line in (folder/'test.scs').read_text().splitlines() if line.startswith('save ')]
    if len(actual)!=len(expected) or set(actual)!=set(expected):
        raise ValueError('Spectre case-sensitive save symbols do not match actual netlist declarations')
    return dict(voltage_requests=len(cfg['voltage_saves']),current_requests=len(cfg['current_saves']),
                resolved_requests=len(actual),exact_case_symbols_verified=True)


def prepare():
    old_cfg=json.loads((OLD/'measurement.json').read_bytes())
    old_recipe=json.loads((OLD/'recipe_proposal.json').read_bytes())
    for name,h in old_cfg['required_input_sha256'].items():
        if sha((OLD/name).read_bytes())!=h:raise ValueError('Preserve frozen v1 inputs: '+name)
    resolved=expected_saves(OLD,old_cfg)
    old_text=(OLD/'test.scs').read_text()
    new_text='\n'.join('save '+resolved[line[5:]] if line.startswith('save ') else line
                       for line in old_text.splitlines())+'\n'
    if new_text==old_text:raise ValueError('Expected v1 invalid lowercase saves')
    payload={item['name']:(OLD/item['name']).read_bytes() for item in old_recipe['inputs']}
    payload['test.scs']=new_text.encode()
    cfg=copy.deepcopy(old_cfg)
    cfg['required_input_sha256']['test.scs']=sha(payload['test.scs'])
    payload['measurement.json']=js(cfg).encode()
    for name,blob in payload.items():exact(NEW/name,blob)
    check=validate_saves(NEW,cfg)
    if [line for line in old_text.splitlines() if not line.startswith('save ')]!=[
            line for line in new_text.splitlines() if not line.startswith('save ')]:
        raise ValueError('A non-save statement changed')
    recipe=copy.deepcopy(old_recipe)
    recipe['run_id']='sar8audit-comp-kickback-tt-v2'
    recipe['resources']['queue_timeout_seconds']=600
    recipe['inputs']=[dict(name=name,source=(NEW/name).relative_to(ROOT).as_posix(),sha256=sha(blob))
                      for name,blob in payload.items()]
    exact(NEW/'recipe_proposal.json',js(recipe))
    manifest=dict(status='local_save_case_fix_not_Spectre_compiled',parent_run='sar8audit-comp-kickback-tt-v1',
        parent_registered_recipe_sha256='5c3eee55600347ee6100a5dd2115f747cc4aa43a5ec490f51032f03bce65b769',
        change='Only exact-case Spectre save spellings and corresponding input hashes; no device/clock/tolerance/budget changes',
        parent_input_hashes={n:sha((OLD/n).read_bytes()) for n in payload},
        input_hashes={n:sha(blob) for n,blob in payload.items()},save_binding=resolved,symbol_check=check,
        max_output_mib=recipe['resources']['max_output_mib'],total_input_bytes=sum(len(v) for v in payload.values()),
        warnings='Retain all native warnings. Recheck SPECTRE-16881 IC convergence, SFE-3031 reset-clock cap removal, and every requested TRACE.',
        acceptance_pass=None,remote_submitted=False,builder_sha256=sha(Path(__file__).read_bytes()))
    exact(NEW/'manifest.json',js(manifest))
    print('LOCAL_V2_SAVE_CASE_FIX',check,'input_bytes',manifest['total_input_bytes'])


if __name__=='__main__':prepare()
