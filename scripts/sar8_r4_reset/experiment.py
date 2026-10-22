"""Immutable native-MOS sequencing experiments; never edit R4 or OA."""
from pathlib import Path
import argparse
import contextlib
import hashlib
import json
import os
import re
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/sar8_r4_reset'
FROZEN = ROOT / 'netlist/sar8_physical/dut.scs'
SOURCE = ROOT / 'output/sar8_r4_performance/cases/sine_cx_1024_k461'
TOP = 'sar_adc8_join_r4'
os.environ.setdefault('VB_DISABLE_CONTROL_MASTER', '1')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, x):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, indent=2, default=str, allow_nan=False)+'\n', encoding='utf-8')


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def cells(text):
    text = re.sub(r'\\\r?\n\s*', ' ', text)
    return {m[1]: m[0] for m in re.finditer(r'(?ms)^subckt (\w+) .*?^ends \1\s*$', text)}


def compact(x):
    return ' '.join(x.split())


def modified_dut(kind, cap):
    original = FROZEN.read_text(); c = cells(original)
    if kind == 'baseline':
        return original, []
    # Copy an existing PDK delay: two RC/inverter stages with fast clear.
    delay = c['sar8p_delay_capture'].replace('sar8p_delay_capture', 'sar8r_delay')
    delay, n = re.subn(r'(spm=3 multi=)10\b', rf'\g<1>{cap}', delay)
    assert n == 2
    edge = '''subckt sar8r_edge A VDD VSS Y
    XD (A VDD VSS AD) sar8r_delay
    XA (A AD VDD VSS QUAL) sar8p_and2
    XB (QUAL VDD VSS Y) sar8p_clkbuf
ends sar8r_edge
'''
    top = c[TOP]
    top = top.replace('    XSAMPLE ', '    XSEQ (SAMPLE_INT VDD! 0 SEQ_SAMPLE) sar8r_edge\n    XSAMPLE ', 1)
    if kind == 'reset_first':
        for side in 'NP':
            old = f'XBOOT{side} (SAMPLE_INT TOP{side} VIN{side})'
            assert top.count(old) == 1
            top = top.replace(old, old.replace('SAMPLE_INT', 'SEQ_SAMPLE'))
    elif kind == 'sample_first':
        old = 'GPP7 PHI_U SAMPLE_INT VDD! 0)'
        assert top.count(old) == 1
        top = top.replace(old, old.replace('SAMPLE_INT', 'SEQ_SAMPLE'))
    else:
        raise ValueError(kind)
    # Replace exact original top block (line continuations removed only in it).
    match = re.search(r'(?ms)^subckt '+TOP+r' .*?^ends '+TOP+r'\s*$', original)
    text = original[:match.start()] + delay + '\n' + edge + '\n' + top + '\n' + original[match.end():]
    new = cells(text)
    assert all(compact(new[k]) == compact(v) for k, v in c.items() if k != TOP)
    assert set(new) - set(c) == {'sar8r_delay', 'sar8r_edge'}
    assert 'ahdl_include' not in text
    return text, ['sar8r_delay', 'sar8r_edge']


def stress_devices(text):
    """Resolve terminal nets for selected native MOS hierarchies, not PDK internals."""
    c = cells(text)
    devices = []
    prefixes = ('XDUT.XCDAC.', 'XDUT.XCOMP.', 'XDUT.XBOOTN.', 'XDUT.XBOOTP.', 'XDUT.XSEQ.')
    def descend(master, path, bindings):
        block = c[master]
        for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)', block):
            name, ns, model, params = m.groups()
            ns = ns.split()
            resolved = [bindings.get(n, n if n in ('0', 'VDD!') else path+'.'+n) for n in ns]
            inst = path+'.'+name
            if model in c:
                ports = c[model].splitlines()[0].split()[2:]
                assert len(ports) == len(ns), (inst, ports, ns)
                descend(model, inst, dict(zip(ports, resolved)))
            elif model in ('nch_mac', 'pch_mac', 'nch_18_mac', 'pch_18_mac') and inst.startswith(prefixes):
                assert len(ns) == 4
                devices.append(dict(instance=inst, model=model, nodes=dict(zip('dgsb', resolved)),
                                    limit_v=1.98 if '_18_' in model else .99))
    ports = c[TOP].splitlines()[0].split()[2:]
    descend(TOP, 'XDUT', dict(zip(ports, ports)))
    assert sum(d['instance'].startswith('XDUT.XCDAC.') for d in devices) == 32
    return devices


def prepare(a):
    folder = OUT / a.name
    assert not folder.exists(), 'Immutable case already exists'
    ctx = read(SOURCE/'context.json')
    src = SOURCE/'sine_cx_1024_k461.scs'
    assert sha(src) == ctx['deck_sha256']
    provenance = read(ROOT/'netlist/sar8_physical/provenance.json')
    assert sha(FROZEN) == provenance['files']['dut.scs']
    dut, added = modified_dut(a.kind, a.cap)
    text = src.read_text()
    original = FROZEN.read_text()
    assert text.count(original) == 1
    text = text.replace(original, dut)
    mos = stress_devices(dut)
    saves = {n for d in mos for n in d['nodes'].values() if n != '0'}
    saves.update(['SAMPLE','XDUT.SAMPLE_INT','XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U',
                  'XDUT.XREF.CAP_CLK','VINP_SRC','VINN_SRC','VINP','VINN','VREFP','VREFN','VDD!'])
    saves.update(f'D{i}' for i in range(8))
    for bit in range(8):
        saves.add(f'XDUT.XREF.Q{bit}')
        saves.update(f'XDUT.XREF.XDRV{bit}.{g}DRV' for g in ('GNN','GNP','GPN','GPP'))
    text, n = re.subn(r'(?m)^tran_perf tran.*$',
        f'tran_perf tran stop={a.stop}n maxstep={a.maxstep}p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=all outputstart={a.outputstart}n', text)
    assert n == 1
    text, n = re.subn(r'(?m)^save .*$', 'save '+' '.join(sorted(saves)), text); assert n == 1
    # Full native adaptive output includes startup; do not drop bad initial frames.
    folder.mkdir(parents=True)
    inc = SOURCE/'r4_perf_monitor.va'
    (folder/inc.name).write_bytes(inc.read_bytes())
    deck = folder/'test.scs'; deck.write_text(text, encoding='utf-8')
    (folder/'dut.scs').write_text(dut, encoding='utf-8')
    args = (['+aps'] if a.mode == 'aps' else ['+preset=cx']) + [f'+mt={a.threads}','+lqtimeout','60']
    if a.honor and a.mode != 'aps':
        args.append('-preset_override')
    dump(folder/'context.json', dict(name=a.name,kind=a.kind,cap_units=a.cap,stop_ns=a.stop,
         solver=a.mode,honor_options=a.honor,requested_maxstep_ps=a.maxstep,spectre_args=args,
         outputstart_ns=a.outputstart,threads=a.threads,
         frozen_DUT_sha256=sha(FROZEN),DUT_sha256=sha(folder/'dut.scs'),deck_sha256=sha(deck),
         monitor_sha256=sha(folder/inc.name),source_deck_sha256=sha(src),added_native_cells=added,
         OA_changed=False,baseline_replaced=False,stress_devices=mos,saved_signals=sorted(saves)))
    print('PREPARED',a.name,len(mos),'MOS',len(saves),'signals',flush=True)


def run(a):
    from virtuoso_bridge.spectre.runner import SpectreSimulator
    folder = OUT/a.name; ctx=read(folder/'context.json')
    lock = folder/'launch.json'
    with lock.open('x') as f:
        json.dump(dict(local_pid=os.getpid(),started_epoch=time.time()), f)
    assert not (folder/'result.json').exists()
    assert sha(folder/'test.scs') == ctx['deck_sha256']
    assert sha(folder/'r4_perf_monitor.va') == ctx['monitor_sha256']
    sim=SpectreSimulator.from_env(profile='t28_io',work_dir=folder/'spectre',timeout=21600,
                                 spectre_args=ctx['spectre_args'])
    start=time.monotonic()
    with (folder/'runner.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        r=sim.run_simulation(folder/'test.scs',dict(include_files=[folder/'r4_perf_monitor.va']))
    dump(folder/'result.json',dict(ok=r.ok,errors=r.errors,warnings=r.warnings,metadata=r.metadata,
                                 elapsed_s=time.monotonic()-start,deck_sha256=ctx['deck_sha256']))
    if not r.ok:
        raise RuntimeError(r.errors)
    w={str(k).strip('"').replace('\\','').lower():np.asarray(v) for k,v in r.data.items()
       if isinstance(v,(list,np.ndarray)) and str(k).lower()!='units'}
    assert np.all(np.diff(w['time'])>0) and w['time'][-1]>=ctx['stop_ns']*1e-9-1e-14
    assert all(len(v)==len(w['time']) and np.isfinite(v).all() for v in w.values())
    np.savez_compressed(folder/'wave.npz',**w)
    dump(folder/'wave_receipt.json',dict(sha256=sha(folder/'wave.npz'),points=len(w['time']),signals=list(w)))
    print('COMPLETE',a.name,len(w['time']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['prepare','run']);p.add_argument('name')
    p.add_argument('--kind',choices=['baseline','reset_first','sample_first'],default='baseline')
    p.add_argument('--cap',type=int,default=20);p.add_argument('--stop',type=float,default=500)
    p.add_argument('--mode',choices=['cx','aps'],default='cx');p.add_argument('--maxstep',type=float,default=10)
    p.add_argument('--honor',action='store_true')
    p.add_argument('--outputstart',type=float,default=0);p.add_argument('--threads',type=int,default=2)
    a=p.parse_args(); prepare(a) if a.action=='prepare' else run(a)
