"""Expose frozen SAR8 B sources and exact managed test inputs for human review."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs'
EXPECTED = 'f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'
DESIGN = ROOT / 'design/sar8_b'
CASES = {
    'tt_short': 'sar8camp-b-mm-bench-v1',
    'tt_fft1024': 'sar8camp-b-tt-fft1024-mm-v1',
    'tt_static_low': 'sar8camp-b-tt-s001-003-v1',
    'mc_comparator_tt': 'sar8mc-comp-s4101-v2',
    'mc_cdac_tt': 'sar8mc-cdac-s4101-v2',
    'mc_cold_ss': 'sar8tm-ssc-s5101-v1',
    'mc_cold_ff': 'sar8tm-ffc-s5101-v1',
}
GROUPS = {
    'blocks/standard_cells.scs': [
        'sar8p_inv', 'sar8p_clkbuf', 'sar8p_nand2', 'sar8p_and2',
        'sar8p_buf', 'sar8p_xor2', 'sar8p_or2', 'sar8p_sr',
        'sar8p_dffr', 'sar8p_mux2',
    ],
    'blocks/delays.scs': [
        'sar8p_delay_valid', 'sar8p_delay_write', 'sar8p_delay_quiet',
        'sar8p_delay_capture', 'sar8p_delay_bbm', 'sar8r_delay',
        'sar8r_edge', 'sar8s_step', 'sar8i_guard',
    ],
    'blocks/bootstrap.scs': ['sar_bootstrap_flat_8b_p'],
    'blocks/cdac.scs': ['sar8j_r1_sw_b%d' % i for i in range(8)] + ['sar8j_r1_cdac'],
    'blocks/comparator.scs': ['sar_strongarm_t28'],
    'blocks/sar_logic.scs': [
        'sar8p_timing', 'sar8p_bitseq8', 'sar8p_bit',
        'sar_logic_8b_physical', 'sar8i_ctrl',
    ],
    'blocks/reference.scs': ['sar8p_nonoverlap'] + [
        'sar8p_refdrv_b%d' % i for i in range(8)
    ] + ['sar8p_refword', 'sar8s_refword', 'sar8i_refword', 'sar8i_idle'],
    'top/adc_top.scs': ['sar_adc8_join_r4'],
}
BLOCK = re.compile(r'(?ms)^subckt (\w+)\b.*?^ends \1\b[^\n]*')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blocks(text):
    found = {m.group(1): m.group() for m in BLOCK.finditer(text)}
    if len(found) != len(list(BLOCK.finditer(text))):
        raise ValueError('Repeated subcircuit name')
    rest = BLOCK.sub('', text)
    rest = re.sub(r'(?m)//.*$', '', rest).strip()
    if rest:
        raise ValueError('Unexpected statements outside subcircuits: ' + rest[:120])
    return found


def logical(text):
    return re.sub(r'\\\n\s*', ' ', text)


def derived():
    if sha(SOURCE) != EXPECTED:
        raise ValueError('Frozen B source changed')
    text = SOURCE.read_text(encoding='utf-8')
    source = blocks(text)
    names = [n for members in GROUPS.values() for n in members]
    if len(names) != len(set(names)) or set(names) != set(source):
        raise ValueError('Subcircuit partition is incomplete')
    outputs = {}
    index = {}
    for filename, members in GROUPS.items():
        outputs[DESIGN / filename] = (
            '// Generated from frozen B by scripts/sar8_entry.py build.\n'
            '// Electrical subcircuit statements are preserved verbatim.\n\n'
            + '\n\n'.join(source[n] for n in members) + '\n'
        )
        for name in members:
            body = logical(source[name])
            header = body.splitlines()[0].split()
            calls = re.findall(r'(?m)^\s*(X\w+)\s+\([^)]*\)\s+(\w+)', body)
            index[name] = dict(
                file=filename, source_line=text[:text.index(source[name])].count('\n') + 1,
                ports=header[2:], instances=[dict(instance=i, master=m) for i, m in calls],
                text_sha256=hashlib.sha256(source[name].encode()).hexdigest(),
            )
    outputs[DESIGN / 'dut.scs'] = (
        '// Frozen B electrical view. PDK and standard-cell includes belong to the test deck.\n'
        'simulator lang=spectre\n' + ''.join('include "%s"\n' % f for f in GROUPS)
    )
    reachable = set()
    pending = ['sar_adc8_join_r4']
    external = set()
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable.add(name)
        for call in index[name]['instances']:
            master = call['master']
            if master in index:
                pending.append(master)
            else:
                external.add(master)
    if external != {'DFCNQD1BWP12T30P140', 'INVD1BWP12T30P140', 'ND2D1BWP12T30P140'}:
        raise ValueError('Unexpected external subcircuit dependencies: ' + str(external))
    manifest = dict(
        design_id='sar8_l90_mmain2_stdcell_v1', source=SOURCE.relative_to(ROOT).as_posix(),
        source_sha256=EXPECTED, top='sar_adc8_join_r4',
        status='generated_partition_of_frozen_source',
        validation='exact_subcircuit_text_identity; native simulation evidence uses original frozen source',
        standard_cell_include='netlist/sar8_l90_mmain2_stdcell_v1/library_include.scs',
        reachable_from_top=sorted(reachable),
        retained_auxiliary_definitions=sorted(set(index) - reachable),
        external_standard_cell_masters=sorted(external), subcircuits=index,
    )
    outputs[DESIGN / 'manifest.json'] = json.dumps(manifest, indent=2) + '\n'
    cases = {}
    for alias, run in CASES.items():
        path = ROOT / 'management/recipes' / (run + '.yaml')
        recipe = json.loads(path.read_text(encoding='utf-8'))
        for item in recipe['inputs']:
            if sha(ROOT / item['source']) != item['sha256']:
                raise ValueError('Recipe dependency changed: ' + item['source'])
        cases[alias] = dict(
            run_id=run, recipe=path.relative_to(ROOT).as_posix(),
            recipe_sha256=sha(path), entry=recipe['entry'], analyzer=recipe['analyzer'],
            inputs=recipe['inputs'], resources=recipe['resources'],
            spectre_args=recipe['spectre_args'], conditions=recipe.get('test_conditions'),
            remote_path='/server_local_ssd/chenzc_intern25/sar-adc-t28/runs/' + run,
        )
    outputs[ROOT / 'tb/sar8_b/cases.json'] = json.dumps(cases, indent=2) + '\n'
    return outputs, source


def build():
    outputs, _ = derived()
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8', newline='\n')
    check()


def check():
    outputs, source = derived()
    for path, expected in outputs.items():
        if path.read_text(encoding='utf-8') != expected:
            raise ValueError('Generated file differs: ' + str(path.relative_to(ROOT)))
    parsed = {}
    for filename in GROUPS:
        parsed.update(blocks((DESIGN / filename).read_text(encoding='utf-8')))
    if parsed != source:
        raise ValueError('Split and original subcircuits differ')
    print('B source verified; %d identical subcircuits; %d locked test cases.' % (len(parsed), len(CASES)))


def export_case(alias):
    check()
    item = json.loads((ROOT / 'tb/sar8_b/cases.json').read_text(encoding='utf-8'))[alias]
    dest = ROOT / 'output/sar8_b' / alias
    for row in item['inputs']:
        target = dest / row['name']
        if not target.resolve().is_relative_to(dest.resolve()):
            raise ValueError('Unsafe bundle path')
        if target.exists() and sha(target) != row['sha256']:
            raise ValueError('Existing exported file differs: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / row['source']).read_bytes())
    print('Exact original test inputs exported to ' + str(dest))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'check', 'export'])
    parser.add_argument('case', nargs='?', choices=list(CASES))
    args = parser.parse_args()
    if args.action == 'export':
        if not args.case:
            parser.error('export requires a case')
        export_case(args.case)
    elif args.action == 'build':
        build()
    else:
        check()
