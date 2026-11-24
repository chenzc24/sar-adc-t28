"""Package one verified Bootstrap core extraction so it serves both ADC channels."""
import json
import re

from Layout.design.bootstrap import CORE, MASTER, candidate_of, output, reference, source
from Layout.project import evidence
from Layout.tools.physical.run_physical import BOOTSTRAP_FILL_RULES
from Layout.tools.simulation.prepare_full_sim import pull, sha

INCLUDE = b'include "xtor/bootstrap/bootstrap.scs"'
INTERFACE = {'CLKS': 'CLKS', 'VIN': 'Vin', 'VOUT': 'VOUT', 'VDD': 'VDD!', 'VSS': '0'}
ALLOWED_DRC = BOOTSTRAP_FILL_RULES | {'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1', 'DIODMY_L:WARNING'}
# Schematic Bootstrap probes with no counterpart among the extracted core's nets.
INTERNAL = ['xdut.xboot%s.%s' % (s, n) for s in 'pn' for n in ('btop', 'bbot')]


def package(physical_id):
    """Files, context and probe map of a verified prefill core, with a boot_ prefix on the xRC files."""
    remote = evidence(physical_id)
    raw = pull(remote + '/manifest.json')
    boot = json.loads(raw)
    checks = boot['checks']
    assert boot['case'] == 'bootstrap' and boot['top'] == CORE and not boot.get('error')
    assert checks['lvs']['verdict'] == 'CORRECT' and 'sha256' in checks['pex']
    assert set(checks['drc']['markers_by_rule']) <= ALLOWED_DRC
    # A candidate view (layout_mmainN) is checked against its own netlist.
    built = candidate_of(boot.get('oa_view', 'layout'))
    ref = pull(remote + '/reference.cdl')
    assert sha(ref) == boot['source_sha256'][output(built).name]
    assert ref.decode('ascii').splitlines() == reference(source(built).read_bytes()).splitlines(), \
        'The extracted Bootstrap and its schematic differ'
    originals = {'extracted.scs': checks['pex']['sha256'], **checks['pex']['companion_sha256']}
    files = {}
    for name, digest in originals.items():
        assert re.fullmatch(r'extracted\.scs(?:\.[\w.-]+)?', name)
        blob = pull(remote + '/pex/' + name)
        assert sha(blob) == digest
        files['boot_' + name] = blob
    main = files['boot_extracted.scs'].decode('ascii')
    for name in originals:
        if name != 'extracted.scs':
            main, n = re.subn(r'(?m)^include "' + re.escape(name) + '"', lambda m: 'include "boot_' + name + '"', main)
            assert n == 1
    files['boot_extracted.scs'] = main.encode('ascii')
    joined = re.sub(r'\\\s*\n\s*', ' ', main)
    header = re.search(r'(?im)^subckt\s+' + CORE + r'\s*\(([^)]+)\)', joined)
    ports = header[1].split() if header else []
    assert sorted(ports) == sorted(INTERFACE), 'Unexpected extracted Bootstrap ports'
    files['bootstrap_pex.scs'] = ('simulator lang=spectre\ninclude "boot_extracted.scs"\n'
        'subckt ' + MASTER + ' CLKS VOUT Vin\nXcore (' + ' '.join(INTERFACE[n] for n in ports) + ') ' + CORE + '\n'
        'ends ' + MASTER + '\n').encode()
    files['bootstrap_physical.json'] = raw
    # The boosted gate as seen at a main-switch device: the MOS whose channel joins VIN and VOUT.
    gate = re.search(r'(?m)^XM\w*\s*\(\s*N_(?:VOUT|VIN)_\w+\s+(N_\w+_g)\s+N_(?:VIN|VOUT)_\w+', joined)
    assert gate, 'No main-switch device in the extraction'
    probes = {'xdut.xboot%s.g' % s: 'XDUT.XBOOT%s.Xcore.%s' % (s.upper(), gate[1]) for s in 'pn'}
    context = dict(bootstrap_physical_evidence=remote, bootstrap_gds_sha256=boot['gds']['sha256'],
                   bootstrap_extracted_original_sha256=originals, bootstrap_extracted_ports=ports,
                   bootstrap_gate_probe=gate[1])
    if built:
        context['sampler_candidate'] = built
    return dict(files=files, context=context, probes=probes)


def use(dut):
    """Point the DUT at the extracted wrapper instead of the schematic Bootstrap."""
    assert dut.count(INCLUDE) == 1
    return dut.replace(INCLUDE, b'include "bootstrap_pex.scs"')
