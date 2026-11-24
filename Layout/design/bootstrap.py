"""Generate Bootstrap's independent LVS source from the electrical master."""
import argparse
import hashlib
import json
import re

from Layout.project import ROOT


MASTER = 'sar_bootstrap_flat_8b_p'
CORE = MASTER + '_core'
SOURCE = ROOT / 'design/xtor/bootstrap/bootstrap.scs'
OUTPUT = ROOT / 'work/layout/bootstrap/bootstrap-reference.cdl'


def candidate_of(view):
    """OA view layout holds the selected sampler; layout_<name> holds candidate <name>."""
    if view == 'layout':
        return None
    match = re.fullmatch(r'layout_(mmain\d{1,2})', view)
    if not match:
        raise ValueError('Unknown Bootstrap view: ' + view)
    return match[1]


def source(candidate=None):
    """Electrical netlist of the selected sampler, or of an unselected candidate."""
    if not candidate:
        return SOURCE
    rows = json.loads((ROOT / 'specs/candidates.json').read_text(encoding='utf-8'))
    return ROOT / rows['modules']['sampler']['candidates'][candidate]['file']


def output(candidate=None):
    return OUTPUT.with_name('bootstrap-%s-reference.cdl' % candidate) if candidate else OUTPUT


def reference(source):
    text = re.sub(r'\\\s*\r?\n\s*', ' ', source.decode('utf-8'))
    lines = [line.split('//', 1)[0].strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if lines[0] != f'subckt {MASTER} CLKS VOUT Vin' or lines[-1] != 'ends ' + MASTER:
        raise ValueError('Bootstrap electrical interface changed')
    result = ['* Electrical source SHA256 ' + hashlib.sha256(source).hexdigest(),
              '.SUBCKT ' + CORE + ' CLKS VOUT VIN VDD VSS']
    supplies = {'VDD!': 'VDD', '0': 'VSS', 'Vin': 'VIN'}
    for line in lines[1:-1]:
        match = re.fullmatch(r'(\w+)\s+\(([^)]+)\)\s+(\w+)\s+(.+)', line)
        if not match:
            raise ValueError('Unexpected Bootstrap device: ' + line)
        name, pins, model, arguments = match.groups()
        nodes = ' '.join(supplies.get(net, net) for net in pins.split())
        params = dict(field.split('=', 1) for field in arguments.split())
        if name.startswith('M') and model in {'nch_18_mac', 'pch_18_mac'}:
            if params['nf'] != '1' or len(pins.split()) != 4:
                raise ValueError('Review the electrical device width and terminal convention')
            result.append(f"{name} {nodes} {model} L={params['l']} W={params['w']} M={params['multi']}")
        elif name == 'Cboot' and model == 'cfmom_2t' and len(pins.split()) == 2:
            geometry = ' '.join(key + '=' + params[key] for key in ('nr', 'lr', 'w', 's', 'stm', 'spm'))
            for unit in range(int(params['multi'])):
                result.append(f'X{name}_{unit} {nodes} {model} {geometry} multi=1')
        else:
            raise ValueError('Unmapped Bootstrap device: ' + name)
    return '\n'.join(result + ['.ENDS ' + CORE, ''])


def generate(candidate=None):
    path = output(candidate)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(reference(source(candidate).read_bytes()), encoding='ascii')
    print(path.relative_to(ROOT))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', help='Unselected sampler candidate, built into OA view layout_<name>')
    generate(parser.parse_args().candidate)
