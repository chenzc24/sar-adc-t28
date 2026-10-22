"""Native idle-tail reset candidate; immutable cases, reuse verified transport."""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/sar8_r4_staged'))
spec = importlib.util.spec_from_file_location('staged_flow', ROOT/'scripts/sar8_r4_staged/flow.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUT = ROOT/'output/sar8_r4_idle'
base.OUT = OUT
base.REMOTE = '/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_r4_idle_20261022'
read, dump, sha, cells = base.read, base.dump, base.sha, base.cells
prior = base.prior
staged_design = base.design


def design(order, rg, drive, stepcap):
    assert (order, rg, drive, stepcap) == ('msb', 1, 1, 6)
    text, _ = staged_design(order, rg, drive, stepcap)
    before = cells(text)
    ctrl = before['sar_logic_8b_physical'].replace('sar_logic_8b_physical', 'sar8i_ctrl')
    lines = ctrl.splitlines(); lines[0] += ' ACTIVE'
    ctrl = '\n'.join(lines)
    ref = before['sar8s_refword'].replace('sar8s_refword', 'sar8i_refword')
    lines = ref.splitlines(); lines[0] += ' PRESET'
    for i, line in enumerate(lines):
        if re.match(r'\s*(XRR\d|XRSTEP\d)', line):
            lines[i] = re.sub(r'\bSAMPLE\b', 'PRESET', line)
    ref = '\n'.join(lines)
    guard = before['sar8r_delay'].replace('sar8r_delay', 'sar8i_guard')
    guard, n = re.subn(r'(spm=3 multi=)20\b', r'\g<1>60', guard); assert n == 2
    idle = '''subckt sar8i_idle ACTIVE SAMPLE VDD VSS PRESET SAMPLE_MATCH
    XN (ACTIVE VDD VSS IDLE) sar8p_inv
    XD (IDLE VDD VSS IDLE_D) sar8i_guard
    XP (SAMPLE IDLE_D VDD VSS PRESET) sar8p_or2
    XA (SAMPLE SAMPLE VDD VSS SAMPLE_AND) sar8p_and2
    XB (SAMPLE_AND VDD VSS SAMPLE_MATCH) sar8p_buf
ends sar8i_idle
'''
    top = before[base.TOP].replace('sar8s_refword', 'sar8i_refword')
    top = top.replace('sar_logic_8b_physical', 'sar8i_ctrl')
    top = top.replace('XSEQ (RST_DONE ', 'XSEQ (SAMPLE_MATCH ')
    top, n = re.subn(r'(XCTRL \([^\n]*?) VDD! 0\)', r'\1 VDD! 0 ACTIVE)', top); assert n == 1
    top = top.replace('0 RST_DONE)  sar8i_refword', '0 RST_DONE PRESET)  sar8i_refword')
    assert 'RST_DONE PRESET)' in top
    top = top.replace('    XSAMPLE ', '    XIDLE (ACTIVE SAMPLE_INT VDD! 0 PRESET SAMPLE_MATCH) sar8i_idle\n    XSAMPLE ', 1)
    text = base.replace_cell(text, base.TOP, top) + '\n' + '\n'.join([ctrl, ref, guard, idle])
    after = cells(text)
    assert all(base.compact(after[k]) == base.compact(v) for k, v in before.items() if k != base.TOP)
    assert 'ahdl_include' not in text
    return text, sorted(set(after)-set(cells(base.prior.FROZEN.read_text())))


def inventory(text):
    c = cells(text); devices = []
    def walk(master, path, bindings):
        for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)', c[master]):
            name, ns, model, _ = m.groups(); ns = ns.split(); inst = path+'.'+name
            resolved = [bindings.get(n, n if n in ('0','VDD!') else path+'.'+n) for n in ns]
            if model in c:
                ports = c[model].splitlines()[0].split()[2:]
                assert len(ports) == len(ns), (inst, ports, ns)
                walk(model, inst, dict(zip(ports, resolved)))
            elif model in ('nch_mac','pch_mac','nch_18_mac','pch_18_mac'):
                group = ('reference' if inst.startswith('XDUT.XCDAC.') else
                         'comparator' if inst.startswith('XDUT.XCOMP.') else
                         'bootstrap' if inst.startswith(('XDUT.XBOOTN.','XDUT.XBOOTP.')) else
                         'reference_driver' if inst.startswith('XDUT.XREF.XDRV') else
                         'sequencer' if inst.startswith(('XDUT.XSEQ.','XDUT.XREF.XRSTEP','XDUT.XREF.XRR','XDUT.XREF.XRDONE','XDUT.XIDLE.')) else None)
                if group:
                    assert len(ns) == 4
                    devices.append(dict(instance=inst, model=model, nodes=dict(zip('dgsb',resolved)),
                                        group=group, limit_v=1.98 if '_18_' in model else .99))
    ports = c[base.TOP].splitlines()[0].split()[2:]
    walk(base.TOP, 'XDUT', dict(zip(ports,ports)))
    assert sum(d['group']=='reference' for d in devices) == 32
    return devices


base.design = design
base.inventory = inventory


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['preflight','prepare','launch','status','collect','await_collect','process_local'])
    p.add_argument('names', nargs='*'); p.add_argument('--stop',type=float,default=600)
    p.add_argument('--honor',action='store_true'); a = p.parse_args()
    if a.action == 'prepare':
        assert len(a.names)==1
        a.name=a.names[0]; a.order='msb'; a.rg=1; a.drive=1; a.stepcap=6; a.outputstart=0
        base.prepare(a)
        path=OUT/a.name/'context.json'; ctx=read(path)
        ctx['scheme']='idle_tail_msb_reset'; ctx['guard_cap_units']=60
        dump(path,ctx)
    elif a.action == 'preflight': base.preflight()
    elif a.action == 'launch':
        with (OUT/('dispatch_'+a.names[0]+'.log')).open('x') as log, contextlib.redirect_stdout(log):
            base.launch(a.names)
        print('SUBMITTED',a.names)
    elif a.action == 'status': base.status(a.names)
    elif a.action == 'collect':
        for name in a.names: base.collect(name)
    elif a.action == 'await_collect':
        for name in a.names: base.await_collect(name)
    else:
        for name in a.names: base.process_local(name,0)
