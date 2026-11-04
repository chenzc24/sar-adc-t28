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
        body = (ROOT / 'design' / name).read_text(encoding='utf-8')
        for match in SUBCKT.finditer(body):
            if match.group(1) in parsed:
                raise ValueError('Duplicate subcircuit ' + match.group(1))
            parsed[match.group(1)] = match.group()
    if parsed != originals or set(parsed) != set(manifest['subcircuits']):
        raise ValueError('Subcircuit partition differs from measured B')
    for name, row in manifest['subcircuits'].items():
        actual = hashlib.sha256(parsed[name].encode()).hexdigest()
        if actual != row['text_sha256']:
            raise ValueError('Subcircuit changed: ' + name)
    cases = read('specs/tests.json')
    for case in cases.values():
        for row in case['inputs']:
            checked_source(row)
    from .behavioral import check_generated
    behavior=check_generated()
    return dict(pass_check=True, exact_subcircuits=len(parsed), locked_cases=len(cases),
                frozen_b_sha256=manifest['source_sha256'],behavioral_spec=behavior)


def prepare(case_name, run_id=None, seed=None, split_design=False):
    cases = read('specs/tests.json')
    if case_name not in cases:
        raise ValueError('Unknown case: ' + case_name)
    case = cases[case_name]
    run_id = run_id or ('sar8-next-' + case_name.replace('_', '-') + ('-s%d' % seed if seed is not None else '-v1'))
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
    if split_design:
        if 'dut.scs' not in blobs:
            raise ValueError('This module template does not instantiate the whole ADC')
        blobs['dut.scs'] = (ROOT / 'design/dut.scs').read_bytes()
        manifest = read('design/manifest.json')
        for path in sorted({row['file'] for row in manifest['subcircuits'].values()}):
            blobs[path] = (ROOT / 'design' / path).read_bytes()
    context = json.loads(blobs['context.json'].decode('utf-8'))
    context['run_id'] = run_id
    if split_design:
        # The aggregate hash and input manifest bind the actual split source.
        # Preserve the measured ancestor separately instead of relabelling it.
        manifest = read('design/manifest.json')
        context['parent_dut_sha256'] = manifest['source_sha256']
        context['dut_sha256'] = hashlib.sha256(blobs['dut.scs']).hexdigest()
        context['design_view'] = 'split'
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
                  entry=case['entry'], analyzer=case['analyzer'],
                  inputs=[dict(name=member,source=(dest/member).relative_to(ROOT).as_posix(),
                               sha256=hashlib.sha256(blob).hexdigest()) for member,blob in blobs.items()],
                  resources=case['resources'], spectre_args=case['spectre_args'],
                  summary_signals=case['summary_signals'], expected_stop_s=case['expected_stop_s'],
                  qualification_scope=case['qualification_scope'],
                  test_conditions=dict(context, directory_migration=split_design,
                                       template_run_id=case['run_id']))
    text = json.dumps(recipe, indent=2) + '\n'
    path = dest / 'recipe.yaml'
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise ValueError('Existing run recipe differs')
    path.write_text(text, encoding='utf-8', newline='\n')
    return path.relative_to(ROOT).as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('check')
    p = sub.add_parser('behav')
    p.add_argument('operation',choices=['generate','check','prepare','sim','collect'])
    p.add_argument('--run-id',default='sar8-behav-cross-v1')
    for action in ['prepare', 'sim']:
        p = sub.add_parser(action)
        p.add_argument('case', choices=sorted(read('specs/tests.json')))
        p.add_argument('--run-id')
        p.add_argument('--seed', type=int)
        p.add_argument('--split-design', action='store_true')
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
        else:
            path='work/behav/'+args.run_id+'/recipe.yaml'
            if not (ROOT/path).exists():path=behavioral.prepare(args.run_id)
            for row in read(path)['inputs']:
                checked_source(row)
            result=dict(registration=engine().register(path))
            result['submission']=engine().phase('submit',args.run_id,queue=True)
    elif args.action == 'check':
        result = check()
    elif args.action in {'prepare','sim'}:
        check()
        path = prepare(args.case,args.run_id,args.seed,args.split_design)
        if args.action == 'prepare':
            result = dict(recipe=path)
        else:
            result = dict(registration=engine().register(path))
            result['submission'] = engine().phase('submit',json.loads((ROOT/path).read_text())['run_id'],queue=True)
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
