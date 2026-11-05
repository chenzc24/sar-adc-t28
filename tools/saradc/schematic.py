"""Netlist-authored RNL, official viewer manifests and reproducible SVG exports."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
from . import views,candidates
from .rnl import EXTERNAL,INSTANCE,record,strip,symbol,instances
from .rnl_layouts import annotate
ROOT=Path(__file__).resolve().parents[2]
def sha(body):return hashlib.sha256(body).hexdigest()
def electrical_statements(body):
    return [re.sub(r'\s+',' ',line.strip()) for line in body.replace('\\\n',' ').splitlines()
            if line.strip() and not line.lstrip().startswith('//')]

def sources(root,view='current',candidate=None,package=None):
    blobs=views.build(view,root,candidate);levels={};origin={};hashes={}
    manifest=json.loads((root/'design/manifest.json').read_text())
    for path in sorted({v['file'] for v in manifest['subcircuits'].values()}):
        for name,body in candidates.definitions(blobs[path].decode('utf-8')).items():levels[name]=body;origin[name]='design/'+path
        hashes['design/'+path]=sha((root/'design'/path).read_bytes())
    hashes.update({p:sha((root/p).read_bytes()) for p in ['tools/saradc/schematic.py','tools/saradc/rnl.py','tools/saradc/rnl_layouts.py','tools/saradc/rnl_viewer.py','tools/saradc/rnl_viewer.lock.json','tools/saradc/drawing.html','design/dut.scs','design/manifest.json','specs/candidates.json','specs/views.json']})
    hashes.update({row['file']:row['sha256'] for row in candidates.catalog(root)})
    if package:
        folder=(root/package).resolve()
        fixture_blobs={p.name:p.read_bytes() for p in folder.glob('*_fixture.scs')}
        fixture_blobs['context.json']=(folder/'context.json').read_bytes()
        if (folder/'sar_environment.scs').is_file():fixture_blobs['sar_environment.scs']=(folder/'sar_environment.scs').read_bytes()
    else:
        from .blocks import prepare
        fixture_blobs=prepare('sar8-schematic-preview',root=root,preview=True)
    if fixture_blobs:
        ctx=json.loads(fixture_blobs['context.json'])
        for filename,data in sorted(fixture_blobs.items()):
            if not filename.endswith('_fixture.scs'):continue
            text=data.decode('utf-8');module=filename.removesuffix('_fixture.scs');name='tb_'+module
            levels[name]='subckt '+name+'\n'+text+'\nends '+name
            origin[name]=ctx['contracts'][module]['template']
        if 'sar_environment.scs' in fixture_blobs:
            for name,body in candidates.definitions(fixture_blobs['sar_environment.scs'].decode('utf-8')).items():levels[name]=body;origin[name]='tb/blocks/sar/acceptance.scs (generated electrical environment)'
        hashes.update(ctx['source_hashes'])
    ports={name:body.splitlines()[0].split()[2:] for name,body in levels.items()};ports.update(EXTERNAL)
    va_files=list((root/'design/behav/veriloga').glob('*.va'))+[root/'tb/behav/observer.va',root/'tb/common/veriloga/block_switch.va']
    for path in va_files:
        for match in re.finditer(r'\bmodule\s+(\w+)\s*\(([^)]*)\)\s*;',path.read_text(encoding='utf-8'),re.S):ports[match.group(1)]=[p.strip() for p in match.group(2).split(',')]
    ports.update(b_sampler_bridge=['CLKS','VOUT','Vin'],b_tb_switch=['A','B','EN','VDD','VSS'])
    for name in ['sar8p_delay_valid','sar8p_delay_write','sar8p_delay_quiet','sar8p_delay_capture','sar8p_delay_bbm','sar8r_delay','sar8s_step','sar8i_guard','sar8r_edge','sar8p_clkbuf']:ports['b_'+name]=['A','VDD','VSS','Y']
    for name,terms in list(ports.items()):
        if name not in levels:
            levels[name]='subckt '+name+' '+' '.join(terms)+'\nends '+name
            origin[name]='external interface only' if name in EXTERNAL else 'design/behav/veriloga (behavioral interface only)'
    return levels,ports,origin,hashes


def header(package_path):
    return ['@RNL(type="header") { @VERSION("0.3");',
            '@USE-PACKAGE(name="sar8",version="0.1",path='+json.dumps(package_path)+');',
            '@USE-PACKAGE(name="rnl-std-fill") {}; }']


def symbols_text(ports):
    text=['@RNL(type="header") { @VERSION("0.3"); @PACKAGE(name="sar8",version="0.1");',
          '@USE-PACKAGE(name="rnl-std-core",version="0.3");',
          '@DEVICE(name="*",model="nch*",terminals=["d","g","s","b"]);',
          '@DEVICE(name="*",model="pch*",terminals=["d","g","s","b"]); }','@RNL {']
    for name,terms in ports.items():
        sym=symbol(name,terms)
        text+=['$'+sym.name+' = @DEFINE-SYMBOL {']+sym.lines+['};',
                '# @SELECT-INSTANCE(model='+json.dumps(name)+') => @SET-SYMBOL $'+sym.name+';']
    text+=['}']
    return '\n'.join(text)+'\n'

def write_symbols(root,ports):
    path=root/'design/rnl/sar8.rnl';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(symbols_text(ports),encoding='utf-8')

def portable_text(levels,ports):
    symbols=symbols_text(ports).split('@RNL {',1)[1].rsplit('}',1)[0]
    inline_header=['@RNL(type="header") { @VERSION("0.3"); @USE-PACKAGE(name="rnl-std-fill") {};',
                   '@DEVICE(name="*",model="nch*",terminals=["d","g","s","b"]);',
                   '@DEVICE(name="*",model="pch*",terminals=["d","g","s","b"]);',
                   '@USE-PACKAGE(name="sar8",version="0.1") {']+symbols.splitlines()+['} }']
    return '\n\n'.join(['// Display-only self-contained RNL export. Use design/dut.scs for simulation.',record(inline_header),
                        'simulator lang=spectre']+list(levels.values()))+'\n'

def candidate_exports(root,rnl,catalog):
    """One registered replacement at a time, without changing simulation defaults."""
    from .rnl_layouts import graph
    from .rnl import Sheet
    base=root/'work/drawings/candidates';base.mkdir(parents=True,exist_ok=True);served={}
    for row in catalog:
        if row['selected']:continue
        module,cid=row['module'],row['candidate'];levels,ports,origin,_=sources(root,candidate={module:cid})
        folder=base/(module+'-'+cid);folder.mkdir(parents=True,exist_ok=True)
        defs=candidates.definitions((root/row['file']).read_text(encoding='utf-8'));changed={}
        for name,body in list(levels.items()):
            if name in defs or '// BEGIN SARADC RNL' not in body:
                if name in defs:
                    # A new topology has no claimed hand-reviewed layout. Show every
                    # instance/terminal; the current implementation keeps its authored drawing.
                    clean=strip(body);s=Sheet(name,clean,ports);graph(s)
                    at=re.search(r'(?m)^ends\b',clean).start();drawn=clean[:at]+s.finish()+clean[at:]
                else:drawn,_=annotate(name,body,ports)
                if electrical_statements(drawn)!=electrical_statements(body):raise ValueError('Candidate drawing changed source')
                levels[name]=drawn
        data=portable_text(levels,ports);entry=folder/'candidate.scs';entry.write_text(data,encoding='utf-8')
        validate(rnl,entry)
        render=subprocess.run([rnl,'render',str(entry),'-o',str(folder/'svg')],capture_output=True,text=True)
        if render.returncode:raise ValueError(render.stdout+render.stderr)
        for name in defs:
            body=levels[name]
            meta=dict(source=row['file'],instances=len(instances(body)),ports=ports[name],kind='candidate / automatic layout',
                      electrical_body_sha256=sha('\n'.join(electrical_statements(body)).encode()),
                      children=[{'instance':n,'level':m,'nets':ns} for n,(ns,m,_) in instances(body).items() if m in levels])
            changed[name]=dict(svg=(folder/'svg'/('candidate.'+name+'.svg')).read_text(encoding='utf-8'),source=body,meta=meta)
        prefix='/candidate/'+folder.name+'/'
        manifest={'format':1,'id':folder.name,'entry':'candidate.scs','base':'http://127.0.0.1:8875'+prefix,
                  'level':next(iter(candidates.read(root)['modules'][module]['interfaces'])),
                  'files':[{'path':'candidate.scs','sha256':sha(entry.read_bytes()),'size':entry.stat().st_size}],
                  'display':{'background':'light','grid':'none','view':{'fit':True}}}
        (folder/'workspace.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        for p in [entry,folder/'workspace.json']:served[prefix+p.name]=p.relative_to(root).as_posix()
        row.update(workspace=prefix+'workspace.json',changed_levels=changed,export_source=data)
    (base/'index.json').write_text(json.dumps(served,indent=2)+'\n',encoding='utf-8')


def annotate_native(root,ports):
    """Regenerate only our comment blocks, preserving every other source byte."""
    from .rnl_layouts import layout
    manifest=json.loads((root/'design/manifest.json').read_text(encoding='utf-8'))
    evidence={}
    for rel in sorted({row['file'] for row in manifest['subcircuits'].values()}):
        path=root/'design'/rel;before=path.read_bytes();clean=strip(before.decode('utf-8'))
        nl='\r\n' if '\r\n' in clean else '\n'
        def add(match):
            body=match.group();name=match[1];offset=re.search(r'(?m)^ends\b',body).start()
            comment=layout(name,body.replace('\r\n','\n'),ports).replace('\n',nl)
            return body[:offset]+comment+body[offset:]
        updated=candidates.SUBCKT.sub(add,clean)
        at=updated.index('\n')+1
        package=os.path.relpath(root/'design/rnl/sar8.rnl',path.parent).replace('\\','/')
        updated=updated[:at]+record(header(package)).replace('\n',nl)+updated[at:]
        if strip(updated)!=clean:raise ValueError('RNL changed host bytes: '+str(path))
        path.write_bytes(updated.encode('utf-8'))
        evidence[path.relative_to(root).as_posix()]={'host_sha256':sha(clean.encode('utf-8')),'annotated_sha256':sha(path.read_bytes())}
    return evidence


def validate(rnl,path):
    result=subprocess.run([rnl,'check',str(path)],capture_output=True,text=True,encoding='utf-8')
    output=result.stdout+result.stderr
    if result.returncode or re.search(r'(?m)^(error|warning)\b',output):raise ValueError('RNL validation failed:\n'+output[:6000])
    return output.strip()


def build(root=None,rnl=None,package=None,annotate_sources=False):
    root=(root or ROOT).resolve();rnl=rnl or shutil.which('rnl') or str(root/'work/tools/rnl-0.5.5/cli/rnl.exe')
    version=subprocess.check_output([rnl,'--version'],text=True).strip()
    if not version.startswith('rnl 0.5.5 '):raise ValueError('Use pinned RNL 0.5.5')
    levels,ports,origin,hashes=sources(root,package=package)
    write_symbols(root,ports)
    if annotate_sources:
        annotate_native(root,ports)
        levels,ports,origin,hashes=sources(root,package=package)
    native={n:b for n,b in levels.items() if origin[n].startswith(('design/xtor','design/top'))}
    if any('// BEGIN SARADC RNL' not in b for b in native.values()):
        raise ValueError('Native sources need drawing records: run draw --annotate once')
    native_paths=sorted(set(origin[n] for n in native))
    folder=root/'design/rnl';folder.mkdir(parents=True,exist_ok=True)
    fixtures=['// Generated display-only testbench / behavioral / external interfaces.',record(header('sar8.rnl')),'simulator lang=spectre']
    for n,b in levels.items():
        if n not in native:
            drawn,_=annotate(n,b,ports)
            if electrical_statements(b)!=electrical_statements(drawn):raise ValueError('Fixture altered: '+n)
            fixtures.append(drawn)
    (folder/'testbenches.scs').write_text('\n\n'.join(fixtures)+'\n',encoding='utf-8')
    text=['// RNL workspace entry. DISPLAY ONLY: use design/dut.scs for simulation.',record(header('sar8.rnl')),'simulator lang=spectre']
    text+=['include "'+os.path.relpath(root/p,folder).replace('\\','/')+'"' for p in native_paths]
    text+=['include "testbenches.scs"']
    entry=folder/'current.scs';entry.write_text('\n'.join(text)+'\n',encoding='utf-8')
    diagnostics=validate(rnl,entry)
    out=root/'docs/schematics';out.mkdir(parents=True,exist_ok=True)
    svg_folder=root/'work/drawings/svg';svg_folder.mkdir(parents=True,exist_ok=True)
    rendered=subprocess.run([rnl,'render',str(entry),'-o',str(svg_folder)],capture_output=True,text=True)
    if rendered.returncode:raise ValueError(rendered.stdout+rendered.stderr)
    reachable=set();pending=['sar_adc8_join_r4']
    while pending:
        name=pending.pop()
        if name in reachable or name not in levels:continue
        reachable.add(name);pending.extend(m[1] for m in instances(levels[name]).values())
    drawings={};metadata={}
    for name,body in levels.items():
        file=svg_folder/('current.'+name+'.svg')
        if not file.is_file():raise ValueError('Missing SVG: '+name)
        meta=dict(source=origin[name],instances=len(instances(body)),ports=ports[name],reachable_from_top=name in reachable,
                  electrical_body_sha256=sha('\n'.join(electrical_statements(body)).encode()),
                  kind='native' if name in native else 'testbench' if name.startswith('tb_') else 'interface',
                  children=[{'instance':n,'level':m,'nets':ns} for n,(ns,m,_) in instances(body).items() if m in levels])
        metadata[name]=meta;drawings[name]=dict(svg=file.read_text(encoding='utf-8'),source=body,meta=meta)
    # A portable flattened export for downloading or opening without a server.
    flat={n:b if n in native else annotate(n,b,ports)[0] for n,b in levels.items()}
    (folder/'export.scs').write_text(portable_text(flat,ports),encoding='utf-8')
    validate(rnl,folder/'export.scs')
    served=native_paths+['design/rnl/current.scs','design/rnl/sar8.rnl','design/rnl/testbenches.scs','design/rnl/export.scs']
    # The official viewer uses this allow-listed, hash-bound workspace. No PDK/model/OA files.
    workspace={'format':1,'id':'sar8-current','title':'SAR8 current netlist','base':'http://127.0.0.1:8875/repo/',
               'entry':'design/rnl/current.scs','level':'sar_adc8_join_r4','pool':[],
               'files':[{'path':p,'sha256':sha((root/p).read_bytes()),'size':(root/p).stat().st_size} for p in served],
               'display':{'background':'light','grid':'none','view':{'fit':True}}}
    (folder/'workspace.json').write_text(json.dumps(workspace,indent=2)+'\n',encoding='utf-8')
    catalog=candidates.catalog(root)
    candidate_exports(root,rnl,catalog)
    payload={'levels':drawings,'candidates':catalog,'workspace':'/repo/design/rnl/workspace.json',
             'viewer_version':'0.5.3 / core 0.5.5','default_level':'sar_adc8_join_r4',
             'export_source':(folder/'export.scs').read_text(encoding='utf-8')}
    page=(root/'tools/saradc/drawing.html').read_text(encoding='utf-8').replace('/*DRAWINGS*/',json.dumps(payload,ensure_ascii=False).replace('</',r'<\/'))
    (out/'index.html').write_text(page,encoding='utf-8')
    hashes.update({'design/rnl/sar8.rnl':sha((folder/'sar8.rnl').read_bytes())})
    generated=['design/rnl/current.scs','design/rnl/testbenches.scs','design/rnl/export.scs','design/rnl/workspace.json','docs/schematics/index.html']
    manifest=dict(generator='tools/saradc/schematic.py',rnl_version=version,source_hashes=hashes,levels=metadata,
                  generated_hashes={p:sha((root/p).read_bytes()) for p in generated},diagnostics=diagnostics,
                  electrical_statements_preserved=True,
                  scope='Native topology is authored in source @RNL comments. VA / foundry cells show interfaces only. Not OA or layout.')
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return dict(levels=len(levels),native_levels=len(native),testbench_levels=sum(m['kind']=='testbench' for m in metadata.values()),
                rnl_diagnostics=diagnostics,index='docs/schematics/index.html')


def check(root=None):
    root=root or ROOT;data=json.loads((root/'design/rnl/manifest.json').read_text(encoding='utf-8'))
    changed=[p for p,h in {**data['source_hashes'],**data['generated_hashes']}.items() if not (root/p).is_file() or sha((root/p).read_bytes())!=h]
    if changed:raise ValueError('Schematic sources changed; regenerate: '+', '.join(changed))
    return dict(source_match=True,levels=len(data['levels']),rnl_diagnostics=data['diagnostics'])
