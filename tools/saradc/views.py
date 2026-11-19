"""Compose physical/VA implementations at declared module interfaces."""
import json
from pathlib import Path
import re
from . import candidates
ROOT=Path(__file__).resolve().parents[2]
MODULES=('sampler','cdac','comparator','sar','reference','timing')


def standard_cell_library(root=None, dut=None, mos_corner=None):
    """Resolve the active ADC library, preserving source-bound historical transients."""
    root = root or ROOT
    manifest = json.loads((root/'design/manifest.json').read_text(encoding='utf-8'))
    legacy = 'tb/common/platform/library_include.scs'
    default = manifest['standard_cell_include']
    if dut is not None and default != legacy:
        timing_file = candidates.read(root)['modules']['timing']['target']
        if ('include "' + timing_file + '"').encode() not in dut:
            return (root/legacy).read_bytes()
    source = manifest.get('standard_cell_includes_by_mos', {}).get((mos_corner or '').upper(), default)
    return (root/source).read_bytes()


def registry(root=None):
    return json.loads(((root or ROOT)/'specs/views.json').read_text(encoding='utf-8'))


def resolve(name='current',root=None):
    items=[name] if isinstance(name,str) else list(name or ['current'])
    rows=registry(root)['profiles'];result=None;changed=set()
    for item in items:
        if '=' not in item:
            if result is not None: raise ValueError('Give one base profile before module overrides')
            if item not in rows: raise ValueError('Unknown design view: '+item)
            row=dict(rows[item]);base=row.pop('base',None)
            result=resolve(base,root) if base else {};result.update(row)
        else:
            if result is None: result=resolve(registry(root)['default'],root)
            module,view=item.split('=',1)
            if module not in MODULES or view not in {'xtor','va'}: raise ValueError('Expected module=xtor|va: '+item)
            if module in changed: raise ValueError('Duplicate view override: '+module)
            if result.get('regression_only'): raise ValueError('Frozen B cannot combine module overrides')
            changed.add(module);result[module]=view
    return result


def physical(name='current',root=None):
    return not any(v=='va' for v in resolve(name,root).values())


def build(name='current',root=None,candidate_overrides=None):
    root=root or ROOT;config=registry(root);profile=resolve(name,root)
    manifest=json.loads((root/'design/manifest.json').read_text(encoding='utf-8'))
    if profile.get('regression_only'):
        if candidate_overrides: raise ValueError('Frozen B cannot select another candidate')
        return {'dut.scs':(root/manifest['source']).read_bytes()}
    blobs={'dut.scs':(root/'design/dut.scs').read_bytes()}
    for path in sorted({r['file'] for r in manifest['subcircuits'].values()}):
        blobs[path]=(root/'design'/path).read_bytes()
    calls=re.compile(r'(?m)^\s*\w+\s+\(([^)]*)\)\s+(\S+)')
    baseline_defs={name for data in blobs.values() for name in candidates.definitions(data.decode('utf-8'))}
    external_arity={m.group(2):len(m.group(1).split()) for data in blobs.values()
                    for m in calls.finditer(data.decode('utf-8').replace('\\\n',' ')) if m.group(2) not in baseline_defs}
    selections=candidates.selected(candidate_overrides,root)
    for module,item in selections.items():
        if profile.get(module)=='va' and candidate_overrides and module in candidate_overrides:
            raise ValueError('Physical candidate selected for a VA module: '+module)
        blobs[item['target']]=(root/item['file']).read_bytes()
    owners={}
    arity=dict(external_arity)
    # Native zero-voltage current probes join separately exposed interface pins.
    # They are ideal wires, not behavioral replacement gates or extra drivers.
    arity['iprobe']=2
    arity['rupolym']=2  # Retained RC timing candidate.
    # Native library header verified on thu-song: A1 A2 Z VDD VSS.
    arity['OR2D1BWP12T30P140']=5
    # The installed DEL cells have ordered terminals I, Z, VDD, VSS.
    for size in (25, 50, 75, 100, 150, 200, 250):
        arity[f'DEL{size:03d}D1BWP12T30P140'] = 4
    for filename,body in blobs.items():
        for master,definition in candidates.definitions(body.decode('utf-8')).items():
            if master in owners: raise ValueError('Duplicate candidate master: '+master)
            owners[master]=filename
            arity[master]=len(definition.splitlines()[0].split()[2:])
    for filename,body in blobs.items():
        for match in calls.finditer(body.decode('utf-8').replace('\\\n',' ')):
            nodes,master=match.groups()
            if master not in arity:raise ValueError('Unresolved candidate dependency: '+filename+'/'+master)
            if len(nodes.split())!=arity[master]:raise ValueError('Candidate call port count differs: '+filename+'/'+master)
    if not any(v=='va' for v in profile.values()):return blobs
    mapping={row['master']:row['va'] for module,row in config['modules'].items() if profile[module]=='va'}
    timing=json.loads((root/'specs/arch.json').read_text())['behavior_models']['default_timing']
    delays=config['timing_approximations']['models']
    if profile['timing']=='va':mapping.update({old:'b_'+old for old in delays})
    if profile['reference']=='va':mapping['sar8i_idle']='b_idle'
    for path in list(blobs):
        if path=='dut.scs':continue
        text=blobs[path].decode('utf-8')
        for old,new in mapping.items():
            text=re.sub(r'(\)\s+)'+re.escape(old)+r'(?=\s*(?:\n|$))',r'\g<1>'+new,text)
        blobs[path]=text.encode('utf-8')
    files=sorted(p for p in (root/'design/behav/veriloga').iterdir() if p.suffix in {'.va','.vh'})
    for p in files:blobs[p.name]=p.read_bytes()
    prelude=''.join('ahdl_include "'+p.name+'"\n' for p in files if p.suffix=='.va')
    prelude+='subckt b_sampler_bridge CLKS VOUT Vin\nXVA (CLKS VOUT Vin VDD! 0) b_sampler\nends b_sampler_bridge\n'
    prelude+='subckt b_sample_buffer A VDD VSS Y\nXVA (A VDD VSS Y) b_edge delay_s='+str(timing['sample_buffer_s'])+'\nends b_sample_buffer\n'
    for old,delay in delays.items():
        prelude+='subckt b_%s A VDD VSS Y\nXVA (A VDD VSS Y) b_delay rise_s=%.17g fall_s=%.17g\nends b_%s\n'%(old,delay['rise_s'],delay['fall_s'],old)
    blobs['dut.scs']=(prelude+blobs['dut.scs'].decode('utf-8')).encode('utf-8')
    return blobs
