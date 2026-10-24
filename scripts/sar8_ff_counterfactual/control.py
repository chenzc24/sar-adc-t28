"""Two immutable FF-hot controls; isolated from legacy modules named run/flow."""
from pathlib import Path
import contextlib
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/sar8_main_width'))
import width_flow as wf

OUT = ROOT / 'output/sar8_ff_counterfactual'
VERIFY = ROOT / 'verification/sar8_ff_counterfactual'
REMOTE = '/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_ff_counterfactual_20261024'
SOURCE = ROOT / 'output/sar8_main_width/w2_ff_099_125_static'
NAMES = ['ffhot_rref1', 'ffhot_quiet2']
wf.OUT = wf.base.OUT = OUT
wf.VERIFY = VERIFY
wf.REMOTE = wf.base.REMOTE = REMOTE
read, dump, sha = wf.read, wf.dump, wf.sha


def prepare():
    OUT.mkdir(exist_ok=True)
    VERIFY.mkdir(exist_ok=True)
    ctx0 = read(SOURCE / 'context.json')
    assert sha(SOURCE / 'test.scs') == ctx0['deck_sha256']
    assert sha(SOURCE / 'dut.scs') == ctx0['DUT_sha256']
    assert sha(SOURCE / 'r4_perf_monitor.va') == ctx0['monitor_sha256']
    assert ctx0['DUT_sha256'] == '839596a5b493e9868a53fea451ef98b4e051484dca5d8e3d21d5dd151bf01695'
    original = (SOURCE / 'test.scs').read_text()
    dut0 = (SOURCE / 'dut.scs').read_text()
    for name in NAMES:
        folder = OUT / name
        if folder.exists():
            prior = read(folder / 'context.json')
            assert prior['source_deck_sha256'] == ctx0['deck_sha256']
            assert sha(folder / 'test.scs') == prior['deck_sha256']
            assert sha(folder / 'dut.scs') == prior['DUT_sha256']
            continue  # Resume preparation without overwriting an existing case.
        text, dut = original, dut0
        changes = []
        if name == 'ffhot_rref1':
            for side in ['P', 'N']:
                a = f'RREF{side} (VREF{side}_SRC VREF{side}) resistor r=50'
                b = a.replace('r=50', 'r=1')
                assert text.count(a) == 1
                text = text.replace(a, b, 1)
                changes.append((a, b))
        else:
            cell = re.search(r'(?ms)^subckt sar8p_delay_quiet .*?^ends sar8p_delay_quiet', dut0)[0]
            assert cell.count('multi=30') == 2
            newcell = cell.replace('multi=30', 'multi=60')
            assert text.count(cell) == dut.count(cell) == 1
            assert len(re.findall(r'(?m)^\s*XD_QUIET_D .* sar8p_delay_quiet$', dut)) == 1
            text = text.replace(cell, newcell, 1)
            dut = dut.replace(cell, newcell, 1)
            changes.append((cell, newcell))
            assert dut.replace(newcell, cell, 1) == dut0
        restored = text
        for a, b in reversed(changes):
            assert restored.count(b) == 1
            restored = restored.replace(b, a, 1)
        assert restored == original
        folder.mkdir()
        (folder / 'test.scs').write_text(text)
        (folder / 'dut.scs').write_text(dut)
        (folder / 'r4_perf_monitor.va').write_bytes((SOURCE / 'r4_perf_monitor.va').read_bytes())
        ctx = dict(ctx0)
        ctx.update(name=name, reference_case='w2_ff_099_125_static',
                   reference_resistance_ohm=1 if name == 'ffhot_rref1' else 50,
                   quiet_cap_scale=2 if name == 'ffhot_quiet2' else 1,
                   deck_sha256=sha(folder / 'test.scs'), DUT_sha256=sha(folder / 'dut.scs'),
                   source_deck_sha256=ctx0['deck_sha256'], source_DUT_sha256=ctx0['DUT_sha256'],
                   exact_inverse_check_pass=True, OA_changed=False)
        dump(folder / 'context.json', ctx)
        dump(VERIFY / (name + '_setup.json'), {k: v for k, v in ctx.items()
             if k not in ['stress_devices', 'saved_signals', 'timing_signals']})
    dump(VERIFY / 'setup.json', dict(cases=NAMES, baseline=str(SOURCE),
         concurrency=2, threads=4, unchanged='stimulus, sampling clock, all other cells, PDK, CX settings',
         scope='Six static frames only; frame 0 startup separate; no PVT sweep/noise/mismatch/PEX'))


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare':
        prepare()
    elif action in ['preflight', 'status']:
        getattr(wf, action)()
    elif action in ['launch', 'reduce', 'collect']:
        names = sys.argv[2:] or NAMES
        with (OUT / (action + '.log')).open('a') as f, contextlib.redirect_stdout(f):
            getattr(wf, action)(names)
        print(action, names)
