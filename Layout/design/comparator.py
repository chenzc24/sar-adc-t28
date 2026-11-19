"""Derive the comparator LVS reference directly from the current electrical source."""
import hashlib
import re
from Layout.project import ROOT


def generate():
    source = ROOT / 'design/xtor/comparator/comparator.scs'
    text = source.read_text(encoding='utf-8')
    header = re.search(r'^subckt sar_strongarm_t28 (.+)$', text, re.M)
    devices = re.findall(r'^\s*(M\w+) \(([^)]+)\) (\w+) l=(\S+) w=(\S+) multi=(\d+) nf=(\d+)', text, re.M)
    if not header or len(devices) != 11:
        raise ValueError('Unexpected comparator interface or device count')
    lines = ['* Electrical source SHA256 ' + hashlib.sha256(source.read_bytes()).hexdigest(),
             '.SUBCKT sar_strongarm_t28_core ' + header[1]]
    for name, nodes, model, length, width, multi, fingers in devices:
        if multi != '1' or fingers != '1':
            raise ValueError('Layout requires one finger per comparator device')
        lines.append(f'{name} {nodes} {model} L={length} W={width}')
    lines.append('.ENDS sar_strongarm_t28_core')
    destination = ROOT / 'work/layout/comparator/comparator-reference.cdl'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    filled = destination.with_name('comparator-filled-reference.cdl')
    filled.write_text(('\n'.join(lines) + '\n').replace('sar_strongarm_t28_core', 'sar_strongarm_t28'), encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    generate()
