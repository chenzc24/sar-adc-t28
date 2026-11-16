"""Read native xRC networks at the settled (resistors shorted) limit.

The analyzer is run by the managed runner against completed, hash-bound sources.
No PDK/OA/netlist is changed. Native MOM devices and parasitic capacitors are
counted separately; the two-node capacitance calculation is a diagnostic model.
"""
from __future__ import print_function
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
import re

INSTANCE = re.compile(r'^(\S+)\s*\(\s*(.*?)\s*\)\s+(\S+)(.*)$')
SCALE = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def statements(path):
    parts = []
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            if line.endswith('\\'):
                parts.append(line[:-1])
                continue
            parts.append(line)
            yield ' '.join(parts).strip()
            parts = []
    assert not parts, 'Incomplete continuation'


def parameter(text, key):
    value = re.search(r'\b'+key+r'=(\S+)', text).group(1)
    return float(value[:-1])*SCALE[value[-1]] if value[-1] in SCALE else float(value)


class Union:
    def __init__(self):
        self.parents = {}

    def find(self, x):
        p = self.parents
        if x not in p:
            p[x] = x
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def join(self, a, b):
        self.parents[self.find(a)] = self.find(b)


def analyze(base, expected):
    for name, digest in expected.items():
        assert sha(os.path.join(base, name)) == digest, 'Input hash mismatch: '+name
    pex = os.path.join(base, 'extracted.scs.pex')
    pxi = os.path.join(base, 'extracted.scs.sar8j_r1_cdac.pxi')
    main = os.path.join(base, 'extracted.scs')
    network = None
    networks = {}
    for line in statements(pex):
        if line.startswith('subckt '):
            match = re.match(r'subckt\s+(\S+)\s*\((.*?)\)$', line)
            assert match and network is None
            network = match.group(1)
            formals = match.group(2).split()
            u = Union()
            caps = []
            resistance_count = 0
        elif line.startswith('ends '):
            assert network == line.split()[1]
            # xRC can expose node 0 as an explicit formal. It is the ground
            # reference, not a disconnected fragment of this signal network.
            roots = {u.find(x) for x in formals if x != '0'}
            assert len(roots) == 1, 'Disconnected RC formal pins: '+network
            root = next(iter(roots))
            ground = 0.0
            within = 0.0
            for nodes, value in caps:
                if '0' in nodes:
                    other = nodes[0] if nodes[1] == '0' else nodes[1]
                    assert u.find(other) == root
                    ground += value
                else:
                    assert all(u.find(x) == root for x in nodes)
                    within += value
            networks[network] = dict(net=network.split('\\%')[-1],
                                     formal_count=len(formals), ground_formal_indices=[i for i,x in enumerate(formals) if x == '0'], ground_f=ground,
                                     within_net_f=within, ground_elements=sum('0' in a for a,b in caps),
                                     resistors=resistance_count, all_pins_dc_connected=True)
            network = None
        elif network:
            m = INSTANCE.match(line)
            if not m:
                assert not line or line.startswith('//'), 'Unknown RC statement'
                continue
            nodes = m.group(2).split()
            assert len(nodes) == 2
            if m.group(3) == 'resistor':
                assert parameter(m.group(4), 'r') >= 0
                u.join(*nodes)
                resistance_count += 1
            elif m.group(3) == 'capacitor':
                caps.append((nodes, parameter(m.group(4), 'c')))
            else:
                raise ValueError('Non-passive network '+m.group(3))
    assert network is None
    node_net = {'0': '0'}
    net_data = {x['net']: x for x in networks.values()}
    for line in statements(pxi):
        m = INSTANCE.match(line)
        if m and m.group(3) in networks:
            info = networks[m.group(3)]
            nodes = m.group(2).split()
            assert len(nodes) == info['formal_count']
            for index,node in enumerate(nodes):
                if index in info['ground_formal_indices']:
                    assert node == '0', 'Ground formal mapped to non-ground node'
                    continue
                assert node not in node_net or node_net[node] == info['net']
                node_net[node] = info['net']
    def net(node):
        return node_net.get(node, node)
    coupling = defaultdict(float)
    counts = Counter()
    for path in (main, pxi):
        for line in statements(path):
            m = INSTANCE.match(line)
            if m and m.group(3) == 'capacitor':
                nodes = list(map(net, m.group(2).split()))
                assert len(nodes) == 2 and nodes[0] != nodes[1]
                key = tuple(sorted(nodes))
                coupling[key] += parameter(m.group(4), 'c')
                counts[key] += 1
    mom = Counter()
    mos = Counter()
    for line in statements(main):
        m = INSTANCE.match(line)
        if m and m.group(3) == 'cfmom_2t':
            nodes = list(map(net, m.group(2).split()))
            assert len(nodes) == 2
            mom[tuple(sorted(nodes))] += 1
        elif m and m.group(3) in ('nch_mac', 'pch_mac'):
            mos[m.group(3)] += 1
    assert sum(mom.values()) == 680
    top = {}
    labels = {'0': 'ground'}
    for side in ('TOPP','TOPN'):
        units = {b if a == side else a: count for (a,b),count in mom.items() if side in (a,b)}
        assert sum(units.values()) == 256
        for n,c in units.items():
            if n not in ('VREFP','VREFN'):
                bit = c.bit_length()-1
                assert c == 2**bit
                labels[n] = side+'_B'+str(bit)
        attached = {b if a == side else a: v for (a,b),v in coupling.items() if side in (a,b)}
        info = net_data[side]
        top[side] = dict(native_units_by_net=units,ground_f=info['ground_f']+attached.get('0',0),
                         ground_elements=info['ground_elements']+counts.get(tuple(sorted((side,'0'))),0),
                         coupling_f=attached,total_attached_parasitic_f=info['ground_f']+sum(attached.values()),
                         rc_network=info)
    for side,info in top.items():
        info['coupling_by_label_f'] = {labels.get(n,n):v for n,v in info['coupling_f'].items()}
    out = dict(files_sha256=expected,network_count=len(networks),
               all_network_formals_dc_connected=True,mos_instances=dict(mos),
               native_mom_count=sum(mom.values()),top=top)
    # Every other logical net is externally driven, a switched bottom plate or
    # a supply. A floating-net topology would need a larger matrix, not this fit.
    unknown = set(net_data)-set(labels)-{'TOPP','TOPN','VREFP','VREFN','VDD','VSS'}
    unknown = {n for n in unknown if not re.match(r'^G[NP][NP][0-7]$',n)}
    assert not unknown, 'Unexpected floating/internal nets: '+str(unknown)
    return out


def predict(data, unit_f):
    tops = ['TOPP','TOPN']
    aa = [256*unit_f+data['top'][n]['total_attached_parasitic_f'] for n in tops]
    cross = data['top']['TOPP']['coupling_f'].get('TOPN',0)
    assert abs(cross-data['top']['TOPN']['coupling_f'].get('TOPP',0)) < 1e-25
    det = aa[0]*aa[1]-cross*cross
    weights = []
    for bit in range(8):
        rhs = []
        for i,n in enumerate(tops):
            term = (1 if i == 0 else -1)*2**bit*unit_f
            coupling = data['top'][n]['coupling_by_label_f']
            term += coupling.get('TOPP_B'+str(bit),0)-coupling.get('TOPN_B'+str(bit),0)
            rhs.append(.9*term)
        vp = (aa[1]*rhs[0]+cross*rhs[1])/det
        vn = (cross*rhs[0]+aa[0]*rhs[1])/det
        weights.append(vp-vn)
    ideal = [.9/128*2**b for b in range(8)]
    return dict(unit_capacitance_f=unit_f,weights_v=weights,gain_ratio=sum(weights)/sum(ideal),
                scope='Settled two-TOP charge-conservation model; other nodes held by ideal settled drives; excludes transistor leakage/nonlinear capacitance')


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True)
    p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True)
    a=p.parse_args()
    config=json.load(open(a.run_dir+'/inputs/loading_context.json'))
    result={'analysis_complete':False,'cases':{}}
    for name,case in config['cases'].items():
        source=os.path.join(os.path.dirname(a.source_run_dir),case['run_id'])
        sim=json.load(open(source+'/simulation.state.json'))
        assert sim['status']=='complete' and sim['exit_code']==0
        data=analyze(source+'/inputs',case['files_sha256'])
        data['source_run_id']=case['run_id']
        data['simulation_state_sha256']=sha(source+'/simulation.state.json')
        data['predicted']=predict(data,config['unit_f'])
        data['measured_gain_ratio']=case['measured_gain_ratio']
        data['prediction_minus_measured']=data['predicted']['gain_ratio']-case['measured_gain_ratio']
        result['cases'][name]=data
    result['analysis_complete']=True
    with open(a.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2,sort_keys=True)
    print(json.dumps({k:dict(predicted=v['predicted']['gain_ratio'],measured=v['measured_gain_ratio'],
                            top_ground_f={t:x['ground_f'] for t,x in v['top'].items()}) for k,v in result['cases'].items()}))


if __name__=='__main__':main()
