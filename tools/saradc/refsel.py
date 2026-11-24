"""The shared CDAC gate interface and the split-gate physical pin order."""

import re

from .candidates import definitions
from .rnl import instances, strip


CDAC_FILE = 'xtor/cdac/cdac.scs'
CDAC_MASTER = 'sar8j_r1_cdac'
SELECTS = tuple(f'REFSEL_{side}{bit}' for side in 'NP' for bit in range(8))
SPLIT_TO_SELECT = {
    f'G{side}{gate}{bit}': f'REFSEL_{side}{bit}'
    for side in 'NP' for gate in 'NP' for bit in range(8)
}
CDAC_RAILS = ('TOPN', 'TOPP', 'VDD', 'VREFN', 'VREFP', 'VSS')
CDAC_PORTS = SELECTS + CDAC_RAILS
SPLIT_CDAC_PORTS = (*SPLIT_TO_SELECT, *CDAC_RAILS)
CODES = tuple(f'CODE{bit}' for bit in range(8))
DATA = tuple(f'D{bit}' for bit in range(8))
REFERENCE_PORTS = (*CODES, *SELECTS, 'VDD', 'VSS', 'PRESET')
SPLIT_REFERENCE_PORTS = (*CODES, *DATA, *SPLIT_TO_SELECT,
                         'PHI_U', 'SAMPLE', 'VDD', 'VSS', 'RST_DONE', 'PRESET')


def connections(text, instance, ports):
    return dict(zip(ports, instances(text)[instance][0], strict=True))


def rebind(text, instance, nodes):
    pattern = rf'(?m)^([ \t]*{re.escape(instance)}[ \t]+\()[^)]+(\))'
    result, count = re.subn(pattern, lambda m: m[1] + ' '.join(nodes) + m[2], text)
    if count != 1:
        raise ValueError(f'Expected one {instance} call')
    return result


def split_cdac(source):
    """Expose both switch gates for independent drive and physical source decks."""
    cells = definitions(strip(source))
    cdac = cells[CDAC_MASTER]
    header, body = cdac.split('\n', 1)
    if tuple(header.split()[2:]) != CDAC_PORTS:
        raise ValueError('Unexpected shared-gate CDAC interface')
    for side in 'NP':
        for bit in range(8):
            name = f'XS{side}{bit}'
            nodes = instances(body)[name][0]
            expected = f'REFSEL_{side}{bit}'
            if nodes[1] != expected:
                raise ValueError(f'{name} must bind {expected} at SEL')
            body = rebind(body, name, [nodes[0], f'G{side}N{bit}', f'G{side}P{bit}', *nodes[2:]])
    cells[CDAC_MASTER] = f'subckt {CDAC_MASTER} ' + ' '.join(SPLIT_CDAC_PORTS) + '\n' + body

    for bit in range(8):
        name = f'sar8j_r1_sw_b{bit}'
        header, body = cells[name].split('\n', 1)
        if header.split()[2:] != ['BOT', 'SEL', 'VDD', 'VREFN', 'VREFP', 'VSS']:
            raise ValueError(f'Unexpected reference-switch interface: {name}')
        for device, gate in [('MN_LOW', 'GN'), ('MP_HIGH', 'GP')]:
            nodes = instances(body)[device][0]
            if nodes[1] != 'SEL':
                raise ValueError(f'{name}.{device} gate must bind SEL')
            body = rebind(body, device, [nodes[0], gate, *nodes[2:]])
        cells[name] = f'subckt {name} BOT GN GP VDD VREFN VREFP VSS\n' + body
    return '\n\n'.join(cells.values()) + '\n'


def shared_pex_wrapper(source):
    """Bind existing split PEX pins at the shared node outside the extraction."""
    source = source.replace('\r\n', '\n')
    pattern = rf'(?m)^(subckt {CDAC_MASTER})[ \t]+\(([^)]+)\)$'
    header, = re.finditer(pattern, source)
    if tuple(header[2].split()) != SPLIT_CDAC_PORTS:
        raise ValueError('Unexpected extracted CDAC wrapper interface')
    source = re.sub(pattern, lambda m: m[1] + ' (' + ' '.join(CDAC_PORTS) + ')', source)
    nodes = instances(source)['XPEX'][0]
    return rebind(source, 'XPEX', [SPLIT_TO_SELECT.get(node, node) for node in nodes])


def adapt_legacy_saves(blobs):
    """Prepare a current deck from a frozen fixture with split-gate observations."""
    remapped = {}

    def select(token):
        match = re.fullmatch(r'(?i)xdut\.(G[NP][NP][0-7])', token)
        if not match:
            return token
        node = 'XDUT.' + SPLIT_TO_SELECT[match[1].upper()]
        remapped[token.lower()] = node.lower()
        return node

    def save(match):
        return 'save ' + ' '.join(dict.fromkeys(select(token) for token in match[1].split()))

    deck = re.sub(r'(?m)^save ([^\r\n]+)', save, blobs['test.scs'].decode('utf-8'))
    if remapped:
        blobs['test.scs'] = deck.encode('utf-8')
        # The immutable analyzer still reads its original trace labels.
        blobs['native_stream.py'] += (f'\n\n_gate_aliases = {remapped!r}\n' + '''
_unaliased_samples = samples

def samples(path):
    for time, values in _unaliased_samples(path):
        values.update((name, values[source]) for name, source in _gate_aliases.items() if source in values)
        yield time, values
''').encode('ascii')
