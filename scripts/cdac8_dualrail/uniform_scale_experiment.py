"""Native ideal-gate CDAC multiplicity sweep; immutable source hierarchy."""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import re
import shutil
import sys
from concurrent.futures import as_completed
from dataclasses import asdict
from datetime import datetime, timezone

from common import ROOT, sha
from pn_ratio_experiment import OUT as SOURCE
from run import blocks

OUT = ROOT / 'output/cdac8_uniform_scale'
SOURCE_CASE = 'neg_p2n2'
POINTS = [('nhalf', -.003515625), ('control', .453515625),
          ('nfull', -.8), ('phalf', .003515625), ('pfull', .8)]
FACTORS = [2, 3, 4]
GATES = [f'XCDAC.XS{s}{b}.{device}:2' for s in 'PN' for b in range(8)
         for device in ['MP_HIGH', 'MN_LOW']]
CASES = [(f'{point}_m{factor}', point, voltage, factor)
         for point, voltage in POINTS for factor in FACTORS]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(relative, value):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def prepare(name, point, voltage, factor, fine=False):
    source = SOURCE / f'decks/{SOURCE_CASE}.scs'
    retained = load(SOURCE / f'runs/{SOURCE_CASE}_result.json')
    original_case = load(SOURCE / f'cases/{SOURCE_CASE}.json')
    assert retained['ok'] and sha(source) == retained['deck_sha256']
    original = source.read_text()
    text = original
    old_values = {}
    for key, value in [('MP_RATIO', factor), ('MN_RATIO', factor), ('VDIFF', voltage)]:
        pattern = rf'\b{key}=([^\s]+)'
        match = re.search(pattern, text)
        assert match
        old_values[key] = match[1]
        text, count = re.subn(pattern, f'{key}={value:.14g}', text, count=1)
        assert count == 1
    observation = '\nsave ' + ' '.join(GATES) + ' sigtype=all\n'
    text += observation
    if fine:
        text, count = re.subn('maxstep=100p', 'maxstep=10p', text, count=1)
        assert count == 1
    reverse = text.removesuffix(observation)
    for key, value in old_values.items():
        reverse = re.sub(rf'\b{key}=[^\s]+', f'{key}={value}', reverse, count=1)
    if fine:
        reverse = reverse.replace('maxstep=10p', 'maxstep=100p', 1)
    assert reverse == original and blocks(text) == blocks(original)
    includes = []
    for filename, digest in retained['va_sha256'].items():
        src = SOURCE / 'sources' / filename
        assert sha(src) == sha(ROOT / 'models/veriloga' / filename) == digest
        target = OUT / 'sources' / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert sha(target) == digest
        else:
            shutil.copyfile(src, target)
        includes.append(str(target))
    deck = OUT / f'decks/{name}.scs'
    assert not deck.exists(), f'Preserve {name}'
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(text, encoding='utf-8')
    dump(f'cases/{name}.json', dict(name=name, point=point, factor=factor, vdiff_v=voltage,
         expected_code=int(min(255, max(0, math.floor((voltage + .9) / (1.8 / 256))))),
         source_case=SOURCE_CASE, source_deck_sha256=sha(source), deck_sha256=sha(deck),
         va_sha256=retained['va_sha256'], include_files=includes, gate_current_saves=GATES,
         drain_current_saves=original_case['current_saves'], native_reference_mos_count=32,
         supply_v=.9, corner='tt', temperature_c=27, stop_ns=300,
         dead_time_s=1e-10, command_edge_s=20e-12, maxstep_s=1e-11 if fine else 1e-10,
         physical_transient_noise=False,
         scope='netlist-only native reference-switch scale diagnostics; ideal gate/control/comparator; not async/OA qualification'))
    print('PREPARED', name, voltage, factor, flush=True)


def run(names):
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    cases = [load(OUT / f'cases/{name}.json') for name in names]
    for case in cases:
        assert not (OUT / f"runs/{case['name']}_result.json").exists(), case['name']
        assert sha(OUT / f"decks/{case['name']}.scs") == case['deck_sha256']
    sim = SpectreSimulator.from_env(profile='t28_io', work_dir=OUT / 'spectre', timeout=1800,
                                   spectre_args=[*spectre_mode_args('aps'), '+lqtimeout', '60'])
    progress = sys.stdout
    failures = []
    with (OUT / 'runner.log').open('a', encoding='utf-8') as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            with sim.parallel_pool(max_workers=2) as pool:
                tasks = {pool.submit(OUT / f"decks/{c['name']}.scs",
                                     {'include_files': c['include_files']}): c for c in cases}
                for task in as_completed(tasks):
                    case = tasks[task]
                    name = case['name']
                    result = task.result()
                    dump(f'runs/{name}_result.json', dict(ok=result.ok, errors=result.errors,
                         warnings=result.warnings, metadata=result.metadata,
                         deck_sha256=case['deck_sha256'], va_sha256=case['va_sha256']))
                    if result.ok:
                        dump(f'runs/{name}_waveform.json',
                             {str(k).strip('"').replace('\\', '').lower(): v for k, v in result.data.items()})
                    else:
                        failures.append((name, result.errors))
                    print('SPECTRE', name, result.ok, result.errors[:2], file=progress, flush=True)
    assert not failures, failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'prepare_fine'])
    parser.add_argument('--names', nargs='+')
    parser.add_argument('--fine-parent')
    args = parser.parse_args()
    if args.action == 'prepare':
        from virtuoso_bridge import VirtuosoClient
        client = VirtuosoClient.from_env(profile='t28_io')
        library = client.library.get('SAR_ADC_T28')
        assert library.path == '/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28'
        assert library.technology_library == 'tsmcN28'
        dump('preflight.json', dict(profile='t28_io', library=asdict(library),
                                   time_utc=datetime.now(timezone.utc).isoformat()))
        for case in CASES:
            prepare(*case)
    elif args.action == 'prepare_fine':
        assert args.fine_parent
        parent = load(OUT / f'cases/{args.fine_parent}.json')
        prepare(args.fine_parent + '_fine', parent['point'], parent['vdiff_v'], parent['factor'], fine=True)
    else:
        run(args.names or [case[0] for case in CASES])
