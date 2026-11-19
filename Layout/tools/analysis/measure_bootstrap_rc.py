"""Summarize the single-channel xRC network and check device-to-net correspondence."""
import argparse
from collections import Counter
from itertools import permutations
import json
from pathlib import Path

import numpy as np

from Layout.design.bootstrap import CORE, SOURCE, reference
from Layout.tools.analysis.analyze_top_loading import INSTANCE, parameter, sha, statements


def mos_key(model, nodes):
    drain, gate, source, bulk = nodes
    return model, gate, bulk, tuple(sorted((source, drain)))


def measure(base):
    manifest = json.loads((base / 'bootstrap_physical.json').read_bytes())
    main = base / 'extracted.scs'
    rc = base / 'extracted.scs.pex'
    pxi = base / ('extracted.scs.' + CORE + '.pxi')
    hashes = {'extracted.scs': manifest['checks']['pex']['sha256'],
              **manifest['checks']['pex']['companion_sha256']}
    if any(sha(base / name) != value for name, value in hashes.items()):
        raise ValueError('The xRC files do not match the native manifest')

    networks = {}
    network = None
    for line in statements(rc):
        if line.startswith('subckt '):
            name = line.split()[1]
            pins = line[line.index('(')+1:line.index(')')].split()
            net = name.split(r'\%')[-1]
            network = networks[name] = dict(net=net, pins=pins, grounded_f=0.0, resistors=[])
        elif line.startswith('ends '):
            network = None
        elif line and network and (m := INSTANCE.match(line)):
            a, b = m[2].split()
            if m[3] == 'resistor':
                network['resistors'].append((a, b, parameter(m[4], 'r')))
            elif m[3] == 'capacitor' and '0' in (a, b):
                network['grounded_f'] += parameter(m[4], 'c')
    port_nodes = {}
    fragments = {}
    coupling = Counter()
    parsed = [m for path in (pxi, main) for line in statements(path) if (m := INSTANCE.match(line))]
    for m in parsed:
        if m[3] in networks:
            info = networks[m[3]]
            pairs = dict(zip(m[2].split(), info['pins'], strict=True))
            for actual, formal in pairs.items():
                if formal == '0':
                    if actual != '0':
                        raise ValueError('Unexpected xRC ground reference')
                else:
                    if actual in port_nodes and port_nodes[actual] != info['net']:
                        raise ValueError('xRC external node assigned to different nets')
                    port_nodes[actual] = info['net']
            fragments[info['net']] = pairs

    devices, plate_order, terminal_landings = [], Counter(), []
    for m in parsed:
        nodes = m[2].split()
        logical = [port_nodes.get(n, n) for n in nodes]
        if m[3] in ('nch_18_mac', 'pch_18_mac'):
            devices.append((m[3], logical))
            if 'VOUT' in logical and 'VIN' in logical:
                terminal_landings.append(nodes[logical.index('VOUT')])
        elif m[3] == 'cfmom_2t':
            for key, val in dict(nr=8, lr=2.5e-6, w=50e-9, s=50e-9, stm=1, spm=3).items():
                if not np.isclose(parameter(m[4], key), val, atol=0, rtol=1e-10):
                    raise ValueError('MOM geometry changed')
            plate_order[tuple(logical)] += 1
        elif m[3] == 'capacitor' and logical[0] != logical[1]:
            coupling[tuple(sorted(logical))] += parameter(m[4], 'c')

    expected = Counter()
    caps = Counter()
    for line in reference(SOURCE.read_bytes()).splitlines():
        fields = line.split()
        if line.startswith('M'):
            expected[mos_key(fields[5], fields[1:5])] += 1
        elif line.startswith('X'):
            caps[tuple(sorted(fields[1:3]))] += 1
    ports = {'VIN', 'VOUT', 'CLKS', 'VDD', 'VSS'}
    local_nets = sorted({n for _, nodes in devices for n in nodes} - ports)
    names = sorted({n for _, gate, bulk, sides in expected for n in (gate, bulk, *sides)} - ports)
    solutions = []
    for assignment in permutations(names):
        table = dict(zip(local_nets, assignment, strict=True))
        mapped = Counter(mos_key(model, [table.get(n, n) for n in nodes]) for model, nodes in devices)
        mapped_caps = Counter()
        for (a, b), count in plate_order.items():
            mapped_caps[tuple(sorted((table.get(a, a), table.get(b, b))))] += count
        if mapped == expected and mapped_caps == caps:
            solutions.append(table)
    if len(solutions) != 1:
        raise ValueError('No unique mapping to the Bootstrap schematic')
    label = solutions[0]
    def named(n):
        return label.get(n, n)
    ground = {named(x['net']): x['grounded_f']*1e15 for x in networks.values()}
    cpair = {' / '.join(sorted(map(named, nodes))): v*1e15 for nodes, v in coupling.items()}
    attached = dict(ground)
    for pair, value in coupling.items():
        for n in pair:
            if n != '0':
                attached[named(n)] = attached.get(named(n), 0.0) + value*1e15

    # Two-terminal DC effective resistance with other contacts open.
    vout = next(n for n in networks.values() if n['net'] == 'VOUT')
    wire = vout['resistors']
    source = fragments['VOUT']['VOUT']
    nodes = sorted({n for a, b, _ in wire for n in (a, b)} - {source})
    index = {n: i for i, n in enumerate(nodes)}
    conductance = np.zeros((len(nodes), len(nodes)))
    for a, b, resistance in wire:
        g = 1 / resistance
        for n in (a, b):
            if n != source:
                conductance[index[n], index[n]] += g
        if source not in (a, b):
            conductance[index[a], index[b]] -= g
            conductance[index[b], index[a]] -= g
    resistance = {}
    for landing in terminal_landings:
        k = index[fragments['VOUT'][landing]]
        current = np.zeros(len(nodes))
        current[k] = 1.0
        resistance[landing] = float(np.linalg.solve(conductance, current)[k])
    return dict(xrc_net_to_schematic=label, extraction_sha256=hashes, native_mos=len(devices),
                mom_units=sum(plate_order.values()),
                extracted_mom_terminal_order={' / '.join(map(named, pair)): n for pair, n in plate_order.items()},
                capacitance_scope='Explicit xRC interconnect only. Attached capacitance sums distinct-net and extraction-ground capacitors with other nodes fixed. MOS, well-diode and native MOM compact-model capacitances are excluded.',
                ground_fF=ground, coupling_fF=cpair, attached_fF=attached, vout_port_to_switch_diffusion_ohm=resistance)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bench', type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.bench), indent=2, sort_keys=True))
