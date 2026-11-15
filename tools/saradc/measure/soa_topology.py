"""Read-only terminal inventory. Python 2/3; no proprietary parameters emitted."""
from __future__ import print_function
import hashlib
import json
import re
import sys


def statements(source):
    result = []
    pending = ''
    for raw in source.splitlines():
        line = raw.split('//')[0].strip()
        if not line or line.startswith('*'):
            continue
        if line.startswith('+'):
            if pending:
                pending += ' ' + line[1:]
            elif result:
                result[-1] += ' ' + line[1:]
            else:
                raise ValueError('Orphan continuation')
            continue
        if pending:
            line = pending + ' ' + line
            pending = ''
        if line.endswith('\\'):
            pending = line[:-1]
        else:
            result.append(line)
    if pending:
        raise ValueError('Truncated continuation')
    return result


def definitions(source, spice=False):
    found = {}
    current = None
    for line in statements(source):
        words = line.split()
        op = words[0].lower().lstrip('.')
        if op == 'subckt':
            current = words[1].lower()
            ports = [w for w in words[2:] if '=' not in w]
            found[current] = {'ports': ports, 'instances': []}
        elif op == 'ends':
            current = None
        elif current:
            if spice:
                if words[0][0].lower() == 'm':
                    name, nodes, model = words[0], words[1:5], words[5]
                elif words[0][0].lower() == 'x':
                    pos = next((i for i,w in enumerate(words) if '=' in w), len(words))
                    name, nodes, model = words[0], words[1:pos-1], words[pos-1]
                elif words[0].startswith('.'):
                    raise ValueError('Unsupported library directive: '+words[0])
                else:
                    raise ValueError('Unsupported library element: '+words[0])
            else:
                match = re.match(r'^(\S+)\s*\(([^)]*)\)\s*(\S+)', line)
                if not match:
                    if op == 'parameters':
                        continue
                    raise ValueError('Unsupported circuit statement: '+line[:80])
                name, nodes, model = match.group(1), match.group(2).split(), match.group(3)
            found[current]['instances'].append((name, nodes, model.lower()))
    return found


def flatten(defs, master, ports, prefix='XDUT'):
    devices, leaves = [], {}
    globals_ = {'0', 'VDD!'}
    def visit(master, actual, path, stack):
        if master in stack:
            raise ValueError('Recursive hierarchy')
        cell = defs[master]
        if len(actual) != len(cell['ports']):
            raise ValueError('Port count: '+path)
        binding = dict(zip(cell['ports'], actual))
        def node(n):
            return binding.get(n, n if n in globals_ else path+'.'+n)
        for name, pins, model in cell['instances']:
            full = path+'.'+name
            pins = [node(p) for p in pins]
            if model in defs:
                visit(model, pins, full, stack+[master])
            elif re.match(r'^(nch|pch)_|^(nmoscap|pmoscap)', model):
                expected = 2 if 'moscap' in model else 4
                if len(pins) != expected:
                    raise ValueError('MOS terminal count: '+full)
                devices.append({'instance':full,'model':model,'nodes':pins})
            elif model in ('capacitor','resistor','iprobe','cfmom_2t','rupolym'):
                leaves[model] = leaves.get(model,0)+1
            else:
                raise ValueError('Unresolved leaf '+full+' '+model)
    visit(master, ports, prefix, [])
    return {'devices':devices,'other_leaves':leaves}


def main():
    request = json.load(sys.stdin)
    blob = open(request['library_path'],'rb').read()
    # Parse only used cells: unused library cell formats cannot affect this DUT.
    source = blob.decode('ascii')
    library = {m.group(1).lower():m.group(0) for m in re.finditer(
        r'(?ims)^\.subckt\s+(\S+).*?^\.ends[^\n]*', source)}
    defs = {}
    for text in request['sources']:
        new = definitions(text)
        if set(new)&set(defs):
            raise ValueError('Duplicate subcircuit')
        defs.update(new)
    todo = [request['master']]
    seen = set()
    while todo:
        cell = todo.pop()
        if cell in seen:continue
        seen.add(cell)
        if cell not in defs:
            defs.update(definitions(library[cell], True))
        for _,_,model in defs[cell]['instances']:
            if model in defs or model in library:todo.append(model)
    result = flatten(defs,request['master'],request['ports'])
    result.update(library_path=request['library_path'],library_sha256=hashlib.sha256(blob).hexdigest())
    print(json.dumps(result))


if __name__ == '__main__':main()
