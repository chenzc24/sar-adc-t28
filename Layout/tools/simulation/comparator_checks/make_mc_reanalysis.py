"""Analysis-only reruns of comp-v8-mc seeds: the packaged block_reduce.py reads the completed simulation
through --source-run-dir. Used when a queued analysis worker could not pass the admission gate (its
login session ended, leaving it outside the user memory cgroup).

Usage: make_mc_reanalysis.py SUFFIX SEED [SEED ...]   Run identities: comp-v8-mc-s<seed>-<SUFFIX>
"""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_mc import analyzer  # noqa: E402  same extraction-aware analyzer as the simulated packages
base = analyzer().decode()
old_args = "p.add_argument('--output-dir',required=True);a=p.parse_args()"
assert base.count(old_args) == 1, 'analyzer argument line changed'
s = base.replace(old_args, "p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir');a=p.parse_args()\n    data=a.source_run_dir or a.run_dir")
for old in ["open(a.run_dir+'/inputs/context.json')", "open(a.run_dir+'/spectre.out')",
            "comparator(a.run_dir,ctx,lines)", "random_evidence(a.run_dir)", "cdac(a.run_dir)"]:
    assert s.count(old) == 1, old
    s = s.replace(old, old.replace('a.run_dir', 'data'))
blob = s.encode()
SUFFIX = sys.argv[1]
helper = (ROOT / 'tools/saradc/measure/native_stream.py').read_bytes()
for seed in sys.argv[2:]:
    src = 'comp-v8-mc-s' + seed; rid = src + '-' + SUFFIX
    orig = json.loads((ROOT / 'work/layout' / src / 'recipe.json').read_text())
    d = ROOT / 'work/layout' / rid; d.mkdir()
    (d / 'block_reduce.py').write_bytes(blob)
    (d / 'native_stream.py').write_bytes(helper)
    spec = dict(schema_version=2, kind='analysis_only', source_run_id=src, run_id=rid, design_id=orig['design_id'],
                analyzer='block_reduce.py',
                inputs=[dict(name=n, source=(d / n).relative_to(ROOT).as_posix(), sha256=hashlib.sha256((d / n).read_bytes()).hexdigest())
                        for n in ('block_reduce.py', 'native_stream.py')],
                resources=orig['resources'], spectre_args=orig['spectre_args'], summary_signals=orig['summary_signals'],
                expected_stop_s=orig['expected_stop_s'],
                qualification_scope='Analysis-only rerun of ' + src + ' with the same analyzer, reading the completed '
                                    'simulation; the original queued analysis worker lost its user cgroup and could not pass the gate',
                test_conditions=orig['test_conditions'])
    (d / 'recipe.json').write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(rid)
