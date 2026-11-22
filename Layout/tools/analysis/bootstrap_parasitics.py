"""Wiring load of the Bootstrap hold-phase discharge path in verified core extractions.

For each extraction this reads the packaged xRC netlist (Layout/tools/simulation/bootstrap_pex.package) and
finds, from device connectivity, the main-switch gate net G (the gate of the devices whose channel joins VIN
and VOUT), GRESET (source of Maux, the device from G with its gate at VDD) and CLKSB (gate of MRSTG, the device
from GRESET to VSS). It reports per net the extracted capacitance to ground and to every other net, the devices
whose terminals sit on G, and the effective wiring resistance from the Maux drain to each main-switch gate
contact. Device intrinsic capacitance is in the device models and is not included.
  python -m Layout.tools.analysis.bootstrap_parasitics boot-core-20261121 boot-core-20261121-cworst-t ...
"""
import argparse
import json
import re

import numpy as np

from Layout.project import ROOT
from Layout.tools.simulation import bootstrap_pex
from Layout.tools.simulation.prepare_full_sim import sha

VALUE = re.compile(r'\b(c|r)=([0-9.eE+-]+)(f?)')


def lines(blob):
    return re.sub(r'\\\s*\n\s*', ' ', blob.decode('ascii')).splitlines()


def net_of(node):
    m = re.match(r'N_([A-Za-z0-9]+)_', node)
    return m[1] if m else node


def value(line):
    kind, number, femto = VALUE.search(line).groups()
    return float(number) * (1e-15 if femto else 1.)


def parse(files):
    top = lines(files['boot_extracted.scs'])
    pxi = lines(next(b for n, b in files.items() if n.endswith('.pxi')))
    pex = lines(files['boot_extracted.scs.pex'])
    devices = {}
    for line in top:
        m = re.match(r'^(X\S+)\s*\(\s*([^)]*)\)\s*(\S+)(.*)$', line)
        if m and m[3] in ('nch_18_mac', 'pch_18_mac'):
            w = re.search(r'\bw=([0-9.eE+-]+)', m[4])
            devices[m[1].replace('\\', '')] = dict(pins=m[2].split(), model=m[3], w=float(w[1]) if w else None)
    subckts, current = {}, None
    for line in pex:
        m = re.match(r'^subckt\s+PM_\S+%(\S+)\s*\(([^)]*)\)', line)
        if m:
            current = subckts[m[1]] = dict(ports=m[2].split(), r=[], c=[])
        elif line.startswith('ends'):
            current = None
        elif current is not None:
            m = re.match(r'^([rc])\S*\s*\(\s*(\S+)\s+(\S+)\s*\)', line)
            if m:
                current[m[1]].append((m[2], m[3], value(line)))
    calls, coupling = {}, []
    for line in pxi:
        m = re.match(r'^x_PM_\S+%(\S+)\s*\(([^)]*)\)', line)
        if m:
            calls[m[1]] = m[2].split()
            continue
        m = re.match(r'^c\S*\s*\(\s*(\S+)\s+(\S+)\s*\)', line)
        if m:
            coupling.append((m[1], m[2], value(line)))
    return devices, subckts, calls, coupling


def resistance(sub, call, a, b):
    """Effective resistance between instance nodes a and b of one parasitic net subcircuit."""
    local = dict(zip(call, sub['ports']))
    nodes = sorted({n for x, y, _ in sub['r'] for n in (x, y)})
    index = dict((n, i) for i, n in enumerate(nodes))
    lap = np.zeros((len(nodes), len(nodes)))
    for x, y, r in sub['r']:
        i, j = index[x], index[y]
        g = 1. / max(r, 1e-6)
        lap[i, i] += g
        lap[j, j] += g
        lap[i, j] -= g
        lap[j, i] -= g
    if local[a] not in index or local[b] not in index:
        return 0.
    i, j = index[local[a]], index[local[b]]
    keep = [k for k in range(len(nodes)) if k != j]
    current = np.zeros(len(nodes))
    current[i] = 1.
    v = np.linalg.solve(lap[np.ix_(keep, keep)], current[keep])
    return float(v[keep.index(i)])


def summarize(identity):
    package = bootstrap_pex.package(identity)
    manifest = json.loads(package['files']['bootstrap_physical.json'])
    devices, subckts, calls, coupling = parse(package['files'])
    mains = [d for d in devices.values() if {net_of(d['pins'][0]), net_of(d['pins'][2])} == {'VIN', 'VOUT'}]
    gate = {net_of(d['pins'][1]) for d in mains}
    assert len(gate) == 1 and len(mains) == 4
    gate = gate.pop()
    aux = [(k, d) for k, d in devices.items() if net_of(d['pins'][0]) == gate and d['pins'][1] == 'VDD']
    assert len(aux) == 1
    reset = net_of(aux[0][1]['pins'][2])
    rst = [(k, d) for k, d in devices.items() if net_of(d['pins'][0]) == reset and net_of(d['pins'][2]) == 'VSS']
    assert len(rst) == 1
    clksb = net_of(rst[0][1]['pins'][1])
    names = {gate: 'G', reset: 'GRESET', clksb: 'CLKSB'}

    def load(net):
        to = {}
        for x, y, c in subckts[net]['c']:
            key = 'ground' if '0' in (x, y) else 'internal'
            to[key] = to.get(key, 0.) + c
        for x, y, c in coupling:
            a, b = net_of(x), net_of(y)
            if net in (a, b):
                other = b if a == net else a
                key = 'ground' if other in ('0', 'VSS') else names.get(other, other)
                to[key] = to.get(key, 0.) + c
        return dict(total_fF=sum(to.values()) * 1e15, by_neighbour_fF=dict(sorted(((k, v * 1e15) for k, v in to.items()),
                                                                                  key=lambda kv: -kv[1])))

    on_gate = []
    for k, d in sorted(devices.items()):
        terms = [t for t, n in zip('dgsb', d['pins']) if net_of(n) == gate]
        if terms:
            on_gate.append(dict(device=k, model=d['model'], w_um=d['w'] * 1e6 if d['w'] else None, terminals=terms))
    drain = aux[0][1]['pins'][0]
    r = {k: resistance(subckts[gate], calls[gate], drain, d['pins'][1])
         for k, d in devices.items() if d in mains}
    return dict(identity=identity, interconnect_rc=manifest.get('interconnect_rc', 'typical'),
                extracted_sha256=package['context']['bootstrap_extracted_original_sha256']['extracted.scs'],
                nets=dict(G=gate, GRESET=reset, CLKSB=clksb), maux=aux[0][0], mrstg=rst[0][0],
                load=dict((names[n], load(n)) for n in (gate, reset, clksb)), gate_devices=on_gate,
                net_total_fF=dict(sorted((names.get(n, n), load(n)['total_fF']) for n in subckts)),
                gate_main_width_um=sum(d['w'] for d in mains) * 1e6,
                maux_drain_to_main_gate_ohm=dict(sorted(r.items())), method=__doc__.strip())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('identities', nargs='+')
    ap.add_argument('--output')
    a = ap.parse_args()
    text = json.dumps([summarize(i) for i in a.identities], indent=1) + '\n'
    if a.output:
        (ROOT / a.output).write_text(text, encoding='utf-8', newline='\n')
    else:
        print(text)
