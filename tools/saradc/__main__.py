"""Current netlist, test preparation and managed Spectre command entry."""
import argparse
import hashlib
import json
import re
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBCKT = re.compile(r'(?ms)^subckt (\w+)\b.*?^ends \1\b[^\n]*')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def engine():
    sys.path.insert(0, str(ROOT / 'tools/saradc/managed'))
    import execution
    return execution


def checked_source(row):
    path = (ROOT / row['source']).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError('Missing project input: ' + row['source'])
    if digest(path) != row['sha256']:
        raise ValueError('Changed frozen case input: ' + row['source'])
    return path


def check():
    manifest = read('design/manifest.json')
    frozen = ROOT / manifest['source']
    if digest(frozen) != manifest['source_sha256']:
        raise ValueError('Historical B input bytes changed')
    originals = {m.group(1): m.group() for m in SUBCKT.finditer(frozen.read_text(encoding='utf-8'))}
    parsed = {}
    files = sorted({row['file'] for row in manifest['subcircuits'].values()})
    for name in files:
        from .rnl import strip
        body = strip((ROOT / 'design' / name).read_text(encoding='utf-8'))
        for match in SUBCKT.finditer(body):
            if match.group(1) in parsed:
                raise ValueError('Duplicate subcircuit ' + match.group(1))
            parsed[match.group(1)] = match.group()
    if set(parsed) != set(manifest['subcircuits']):
        raise ValueError('Current subcircuit set differs from the declared manifest')
    matches=0
    for name, row in manifest['subcircuits'].items():
        actual = hashlib.sha256(parsed[name].encode()).hexdigest()
        matches+=actual==row['text_sha256']
        header=parsed[name].replace('\\\n',' ').splitlines()[0].split()[2:]
        if header!=row['ports']:raise ValueError('Current interface differs from manifest: '+name)
    cases = read('specs/tests.json')
    for case in cases.values():
        for row in case['inputs']:
            checked_source(row)
    from .behavioral import check_generated
    behavior=check_generated()
    return dict(pass_check=True, exact_subcircuits=matches,comparison='original statements after removing SARADC RNL comment blocks',current_subcircuits=len(parsed),matches_frozen_b=parsed==originals,locked_cases=len(cases),
                frozen_b_sha256=manifest['source_sha256'],behavioral_spec=behavior)


def prepare(case_name, run_id=None, seed=None, split_design=None, view=None, candidate=None):
    cases = read('specs/tests.json')
    if case_name not in cases:
        raise ValueError('Unknown case: ' + case_name)
    case = cases[case_name]
    from . import views, candidates
    view=view or views.registry(ROOT)['default']
    if split_design is True and view not in ('current',['current']):
        raise ValueError('The legacy --split-design alias cannot be combined with another --view')
    profile=views.resolve(view,ROOT)
    frozen=profile.get('regression_only',False)
    mixed=not views.physical(view,ROOT)
    label='+'.join(view) if isinstance(view,list) else view
    overrides=candidates.assignments(candidate) if not isinstance(candidate,dict) else candidate
    selected={} if frozen else candidates.selected(overrides,ROOT)
    if frozen and overrides:raise ValueError('Frozen B cannot select a candidate')
    if mixed and case_name!='tt_short':
        raise ValueError('Mixed views support TT short verification, not frozen MC/PVT measurements')
    run_id = run_id or ('sar8-next-' + ('mixed-' if mixed else '') + case_name.replace('_', '-') + ('-s%d' % seed if seed is not None else '-v1'))
    # Validate identity before writing any input.
    engine().valid_id(run_id)
    if seed is not None and (not case_name.startswith('mc_') or not 1 <= seed <= 2147483647):
        raise ValueError('A positive integer seed is supported only for MC templates')
    dest = ROOT / 'work/decks' / run_id
    blobs = {}
    for row in case['inputs']:
        member = Path(row['name'])
        if member.is_absolute() or any(p in {'.', '..'} for p in member.parts) or '\\' in row['name']:
            raise ValueError('Unsafe case member')
        blobs[row['name']] = checked_source(row).read_bytes()
    context = json.loads(blobs['context.json'].decode('utf-8'))
    if 'dut.scs' in blobs:
        blobs.update(views.build(view,ROOT,overrides))
        if not frozen and 'library_include.scs' in blobs:
            blobs['library_include.scs'] = views.standard_cell_library(ROOT, blobs['dut.scs'], context.get('corner'))
    elif not frozen and case_name=='mc_comparator_tt':
        # This frozen module fixture embeds its comparator; replace that one
        # definition with the current leaf, retaining receiver/load conditions.
        leaf=(ROOT/selected['comparator']['file']).read_text(encoding='utf-8')
        replacement=next(m.group() for m in SUBCKT.finditer(leaf) if m.group(1)=='sar_strongarm_t28')
        original=blobs['test.scs'].decode('utf-8')
        blobs['test.scs']=SUBCKT.sub(lambda m:replacement if m.group(1)=='sar_strongarm_t28' else m.group(),original).encode('utf-8')
    elif not frozen and case_name=='mc_cdac_tt':
        # Preserve the characterization connections and draw identities while
        # taking geometry/multiplicity from the actual current MOM instances.
        caps=re.compile(r'(?m)^[ \t]*(CMOM[NP][0-8])\s+\(([^)]*)\)\s+(cfmom_2t[^\n]*)')
        current=(ROOT/selected['cdac']['file']).read_text(encoding='utf-8').replace('\\\n',' ')
        parameters={m.group(1):m.group(3) for m in caps.finditer(current)}
        original=blobs['test.scs'].decode('utf-8')
        if len(parameters)!=18 or set(parameters)!={m.group(1) for m in caps.finditer(original)}:
            raise ValueError('The CDAC characterization template must match the current 18-instance MOM interface')
        blobs['test.scs']=caps.sub(lambda m:m.group(1)+' ('+m.group(2)+') '+parameters[m.group(1)],original).encode('utf-8')
    context['run_id'] = run_id
    if not frozen and 'dut.scs' in blobs:
        # The aggregate hash and input manifest bind the actual split source.
        # Preserve the measured ancestor separately instead of relabelling it.
        manifest = read('design/manifest.json')
        context['parent_dut_sha256'] = manifest['source_sha256']
        context['dut_sha256'] = hashlib.sha256(blobs['dut.scs']).hexdigest()
    context['design_view']=label
    context['module_views']=profile
    context['module_candidates']={k:{key:v for key,v in row.items() if key!='definitions'} for k,row in selected.items()} if not frozen else {}
    if not frozen and case_name in {'mc_comparator_tt','mc_cdac_tt'}:
        name='comparator' if case_name=='mc_comparator_tt' else 'cdac'
        context['characterized_source']=selected[name]['file']
        context['characterized_source_sha256']=digest(ROOT/context['characterized_source'])
    if mixed:
        from .modular import adapt_short
        adapt_short(blobs,context,ROOT)
    if seed is not None:
        original_seed = context['seed']
        needle = re.compile(rb'\bseed=' + str(original_seed).encode() + rb'\b')
        blobs['test.scs'], count = needle.subn(b'seed=' + str(seed).encode(), blobs['test.scs'])
        if count != 1:
            raise ValueError('MC seed must occur exactly once in the template')
        context['seed'] = seed
    blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode('utf-8')
    for member, blob in blobs.items():
        target = (dest / member).resolve()
        if not target.is_relative_to(dest.resolve()):
            raise ValueError('Unsafe prepared member')
        if target.exists() and target.read_bytes() != blob:
            raise ValueError('Existing run input differs: ' + member)
    for member, blob in blobs.items():
        target = dest / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    recipe = dict(schema_version=1, run_id=run_id,
                  design_id=read('specs/arch.json')['design_id'],
                  entry=case['entry'], analyzer='analyze_modules.py' if mixed else case['analyzer'],
                  inputs=[dict(name=member,source=(dest/member).relative_to(ROOT).as_posix(),
                               sha256=hashlib.sha256(blob).hexdigest()) for member,blob in blobs.items()],
                  resources=case['resources'], spectre_args=case['spectre_args'],
                  summary_signals=case['summary_signals'], expected_stop_s=case['expected_stop_s'],
                  qualification_scope=case['qualification_scope'] if not mixed else 'TT mixed public-pin function and event timing only; no native MC, analog precision or terminal qualification',
                  test_conditions=dict(context, current_design=not frozen,
                                       template_run_id=case['run_id']))
    text = json.dumps(recipe, indent=2) + '\n'
    path = dest / 'recipe.yaml'
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise ValueError('Existing run recipe differs')
    path.write_text(text, encoding='utf-8', newline='\n')
    return path.relative_to(ROOT).as_posix()


def main():
    from .views import registry
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    p = sub.add_parser('behav')
    p.add_argument('operation',choices=['generate','check','prepare','sim','collect','follow'])
    p.add_argument('--run-id',default='sar8-modules-v3')
    for action in ['prepare', 'sim']:
        p = sub.add_parser(action)
        p.add_argument('case', choices=sorted(read('specs/tests.json')))
        p.add_argument('--run-id')
        p.add_argument('--seed', type=int)
        p.add_argument('--view',action='append',help='Base profile, then repeat module=xtor|va overrides')
        p.add_argument('--candidate',action='append',help='Repeat module=candidate for physical modules')
        p.add_argument('--split-design', action='store_true',default=None,help=argparse.SUPPRESS)
    for action in ['status','analyze','collect','gate','register']:
        p = sub.add_parser(action)
        p.add_argument('target')
        p.add_argument('--queue', action='store_true')
        p.add_argument('--phase', choices=['simulation','analysis'],default='simulation')
    p = sub.add_parser('observe')
    p.add_argument('group', choices=['modules','cold','refs'])
    p.add_argument('--wait', action='store_true')
    sub.add_parser('checkpoint')
    sub.add_parser('module-results')
    p=sub.add_parser('candidates')
    p.add_argument('operation',choices=['list','add'],default='list',nargs='?')
    p.add_argument('--module');p.add_argument('--id');p.add_argument('--file')
    p=sub.add_parser('block')
    p.add_argument('operation',choices=['list','prepare','sim','follow','collect','reanalyze'])
    p.add_argument('--module',action='append',help='Repeat for a subset; default is all six modules')
    p.add_argument('--view',action='append',help='Base profile then module=xtor|va overrides')
    p.add_argument('--candidate',action='append')
    p.add_argument('--run-id',default='sar8-blocks-tt-v1')
    p.add_argument('--source-run')
    p=sub.add_parser('draw')
    p.add_argument('--rnl',help='Pinned RNL 0.5.5 executable')
    p.add_argument('--annotate',action='store_true',help='Regenerate topology comments in current source files')
    p.add_argument('--serve',action='store_true',help='Serve the official RNL viewer locally on loopback')
    p.add_argument('--port',type=int,default=8875)
    p.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.action == 'behav':
        from . import behavioral
        if args.operation=='generate':
            behavioral.generate()
            result=behavioral.check_generated()
        elif args.operation=='check':
            result=behavioral.local_report()
        elif args.operation=='prepare':
            result=dict(recipe=behavioral.prepare(args.run_id))
        elif args.operation=='collect':
            result=behavioral.collect(args.run_id)
        elif args.operation=='follow':
            from .modular import follow
            result=follow(args.run_id)
        else:
            path='work/behav/'+args.run_id+'/recipe.yaml'
            if not (ROOT/path).exists():path=behavioral.prepare(args.run_id)
            context=read('work/behav/'+args.run_id+'/context.json')
            sources=context.get('source_hashes',context.get('source_files',{}))
            for name,expected in sources.items():
                if digest(ROOT/name.replace('\\','/'))!=expected:
                    raise ValueError('This ID freezes an earlier model source; choose a new run ID after the input change: '+name)
            for row in read(path)['inputs']:
                checked_source(row)
            result=dict(registration=engine().register(path))
            result['submission']=engine().phase('submit',args.run_id,queue=True)
    elif args.action == 'check':
        result = check()
    elif args.action in {'prepare','sim'}:
        check()
        path = prepare(args.case,args.run_id,args.seed,args.split_design,args.view,args.candidate)
        if args.action == 'prepare':
            result = dict(recipe=path)
        else:
            result = dict(registration=engine().register(path))
            result['submission'] = engine().phase('submit',json.loads((ROOT/path).read_text())['run_id'],queue=True)
    elif args.action=='draw':
        from . import schematic
        result=schematic.check(ROOT) if args.check or args.serve else schematic.build(ROOT,args.rnl,annotate_sources=args.annotate)
        if args.serve:
            from .rnl_viewer import serve
            serve(ROOT,args.port)
    elif args.action=='block':
        from . import blocks,candidates
        if args.operation=='list':result=blocks.catalog(ROOT)
        elif args.operation=='follow':result=blocks.follow(args.run_id)
        elif args.operation=='collect':result=blocks.collect(args.run_id,ROOT)
        elif args.operation=='reanalyze':
            if not args.source_run:raise ValueError('reanalyze requires --source-run')
            result=blocks.reanalyze(args.run_id,args.source_run,ROOT)
        else:
            path=blocks.prepare(args.run_id,args.module,args.view or 'current',candidates.assignments(args.candidate),ROOT)
            result=dict(recipe=path)
            if args.operation=='sim':
                result['registration']=engine().register(path)
                result['submission']=engine().phase('submit',args.run_id,queue=True)
    elif args.action=='candidates':
        from . import candidates
        if args.operation=='list':result=candidates.catalog(ROOT)
        else:
            if not all([args.module,args.id,args.file]):raise ValueError('add requires --module --id --file')
            result=candidates.add(args.module,args.id,args.file,ROOT)
    elif args.action in {'checkpoint','module-results'}:
        path = ROOT / 'tools/saradc/monitor' / (args.action.replace('-','_') + '.py')
        runpy.run_path(str(path), run_name='__main__')
        return
    elif args.action == 'observe':
        from .monitor.observe import observe
        observe(args.group,args.wait)
        return
    elif args.action == 'register':
        result = engine().register(args.target)
    elif args.action == 'collect':
        result = engine().collect(args.target)
    elif args.action == 'gate':
        result = engine().admission(args.target,args.phase)
    else:
        result = engine().phase('status' if args.action == 'status' else args.action,args.target,args.queue)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
