"""Independent integer P/N multiplicity scan; never edits OA or PDK sources."""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import shutil
from pathlib import Path

from common import ROOT, sha
from no_driver_experiment import OUT as SOURCE, statements
from run import blocks

OUT = ROOT / 'output/cdac8_pn_ratio'
FACTORS = [(1, 1), (2, 1), (1, 2), (2, 2)]
CASES = [(f'{tag}_p{p}n{n}', p, n, source)
         for tag, source in [('neg', 'direct_bad'), ('pos', 'direct_control')]
         for p, n in FACTORS]
CURRENT_SAVES = [f'XCDAC.XS{s}{b}.{device}:1'
                 for s in 'PN' for b in [5, 6, 7]
                 for device in ['MP_HIGH', 'MN_LOW']]


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(relative: str, value):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def prepare(name, p, n, source, fine=False):
    source_deck = SOURCE / f'decks/{source}.scs'
    retained = load(SOURCE / f'runs/{source}_result.json')
    source_case = load(SOURCE / f'cases/{source}.json')
    assert retained['ok'] and sha(source_deck) == retained['deck_sha256']
    text = source_deck.read_text()
    original = text
    before = blocks(text)
    for bit in range(8):
        key = f'cdac8_dr_sw_b{bit}'
        old = before[key]
        new = old
        old_statements = statements(old)
        assert set(old_statements) == {'MP_HIGH', 'MN_LOW', 'E_PGATE', 'E_NGATE'}
        for device, factor in [('MP_HIGH', 'MP_RATIO'), ('MN_LOW', 'MN_RATIO')]:
            statement = old_statements[device]
            target, count = re.subn(r'\bmulti=(\d+)\*MULT_R\b',
                                     rf'multi=\1*MULT_R*{factor}', statement)
            assert count == 1 and target.replace('*' + factor, '') == statement
            new = new.replace(statement, target, 1)
        assert new.replace('*MP_RATIO', '').replace('*MN_RATIO', '') == old
        text = text.replace(old, new, 1)
    text, count = re.subn(r'(?m)^parameters ',
                          f'parameters MP_RATIO={p} MN_RATIO={n} ', text, count=1)
    assert count == 1
    text += '\nsave ' + ' '.join(CURRENT_SAVES) + ' sigtype=all\n'
    if fine:
        text, count = re.subn('maxstep=100p', 'maxstep=10p', text, count=1)
        assert count == 1
    # The reverse transformation must exactly reproduce the completed source.
    reverse = text.replace('*MP_RATIO', '').replace('*MN_RATIO', '')
    reverse = reverse.replace(f'parameters MP_RATIO={p} MN_RATIO={n} ', 'parameters ', 1)
    reverse = reverse.removesuffix('\nsave ' + ' '.join(CURRENT_SAVES) + ' sigtype=all\n')
    if fine:
        reverse = reverse.replace('maxstep=10p', 'maxstep=100p', 1)
    assert reverse == original
    after = blocks(text)
    assert all(after[k] == before[k] for k in before if not k.startswith('cdac8_dr_sw_b'))
    include_files = []
    for filename, digest in retained['va_sha256'].items():
        local = ROOT / 'models/veriloga' / filename
        assert sha(local) == sha(SOURCE / 'sources' / filename) == digest
        target = OUT / 'sources' / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert sha(target) == digest
        else:
            shutil.copyfile(local, target)
        include_files.append(str(target))
    deck = OUT / f'decks/{name}.scs'
    assert not deck.exists(), f'Preserve {name}'
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(text, encoding='utf-8')
    case = dict(name=name, p_multiplier=p, n_multiplier=n, source_case=source,
                source_deck_sha256=sha(source_deck), deck_sha256=sha(deck),
                va_sha256=retained['va_sha256'], include_files=include_files,
                vdiff_v=source_case['vdiff_v'], supply_v=.9, corner='tt',
                temperature_c=27, stop_ns=300, maxstep_s=1e-11 if fine else 1e-10,
                dead_time_s=1e-10, command_edge_s=20e-12,
                physical_transient_noise=False, current_saves=CURRENT_SAVES,
                native_reference_mos_count=32,
                scope='netlist-only native diagnostic; ideal gates/sign comparator; not an OA or async implementation')
    dump(f'cases/{name}.json', case)
    print('PREPARED', name, p, n, flush=True)


def run(names):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    cases = [load(OUT / f'cases/{name}.json') for name in names]
    for case in cases:
        name = case['name']
        assert not (OUT / f'runs/{name}_result.json').exists(), f'Preserve {name}'
        assert sha(OUT / f'decks/{name}.scs') == case['deck_sha256']
    sim = SpectreSimulator.from_env(profile='t28_io', work_dir=OUT / 'spectre',
                                   timeout=1800,
                                   spectre_args=[*spectre_mode_args('aps'), '+lqtimeout', '60'])
    tasks = [(OUT / f"decks/{case['name']}.scs", {'include_files': case['include_files']})
             for case in cases]
    with (OUT / 'runner.log').open('a', encoding='utf-8') as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            results = sim.run_parallel(tasks, max_workers=2)
    for case, result in zip(cases, results, strict=True):
        name = case['name']
        dump(f'runs/{name}_result.json', dict(ok=result.ok, errors=result.errors,
             warnings=result.warnings, metadata=result.metadata,
             deck_sha256=case['deck_sha256'], va_sha256=case['va_sha256']))
        if result.ok:
            dump(f'runs/{name}_waveform.json',
                 {str(k).strip('"').replace('\\', '').lower(): v for k, v in result.data.items()})
        print('SPECTRE', name, result.ok, result.errors[:3], flush=True)
    assert all(result.ok for result in results), 'Failure evidence retained'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'prepare_fine'])
    parser.add_argument('--names', nargs='+')
    parser.add_argument('--fine-parent')
    args = parser.parse_args()
    if args.action == 'prepare':
        for case in CASES:
            prepare(*case)
    elif args.action == 'prepare_fine':
        assert args.fine_parent
        parent = load(OUT / f'cases/{args.fine_parent}.json')
        prepare(args.fine_parent + '_fine', parent['p_multiplier'], parent['n_multiplier'],
                parent['source_case'], fine=True)
    else:
        run(args.names or [case[0] for case in CASES])
