"""Small B view selector. Only generated packages change; physical sources do not."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]


def registry(root=None):
    return json.loads(((root or ROOT)/'specs/views.json').read_text(encoding='utf-8'))


def resolve(name,root=None):
    rows=registry(root)['profiles']
    if name not in rows:raise ValueError('Unknown design view: '+name)
    row=dict(rows[name]);base=row.pop('base',None)
    result=resolve(base,root) if base else {}
    result.update(row)
    return result


def build(name='current',root=None):
    root=root or ROOT;config=registry(root);profile=resolve(name,root)
    manifest=json.loads((root/'design/manifest.json').read_text(encoding='utf-8'))
    if name=='frozen-b':return {'dut.scs':(root/manifest['source']).read_bytes()}
    blobs={'dut.scs':(root/'design/dut.scs').read_bytes()}
    for path in sorted({r['file'] for r in manifest['subcircuits'].values()}):
        blobs[path]=(root/'design'/path).read_bytes()
    if name=='current':return blobs
    top=blobs['top/adc_top.scs'].decode('utf-8')
    for key,row in config['modules'].items():
        if profile[key]=='va':
            top=re.sub(r'\b'+row['master']+r'(?=\s*(?:\n|$))',row['va'],top)
    if profile['timing']=='va':
        for old,new in [('sar8r_edge','b_edge'),('sar8i_idle','b_idle'),('sar8p_clkbuf','b_sample_buffer')]:
            top=re.sub(r'\b'+old+r'(?=\s*(?:\n|$))',new,top)
    blobs['top/adc_top.scs']=top.encode('utf-8')
    files=[p for p in (root/'design/behav/veriloga').iterdir() if p.suffix in {'.va','.vh'}]
    for p in files:blobs[p.name]=p.read_bytes()
    prelude=''.join('ahdl_include "'+p.name+'"\n' for p in files if p.suffix=='.va')
    prelude+='''subckt b_sampler_bridge CLKS VOUT Vin
XVA (CLKS VOUT Vin VDD! 0) b_sampler
ends b_sampler_bridge
subckt b_sample_buffer A VDD VSS Y
XVA (A VDD VSS Y) b_edge delay_s='''+str(json.loads((root/'specs/arch.json').read_text())['behavior_models']['default_timing']['sample_buffer_s'])+'''
ends b_sample_buffer
'''
    blobs['dut.scs']=(prelude+blobs['dut.scs'].decode('utf-8')).encode('utf-8')
    return blobs
