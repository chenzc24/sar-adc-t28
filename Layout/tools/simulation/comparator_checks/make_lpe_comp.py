"""Current-design ADC check with an extracted comparator: package the single_edge_lpe verify fixture
(foundry cell LPE, extracted CDAC) unchanged, then swap the comparator include for a native PEX.

Usage: make_lpe_comp.py PHYSICAL_ID CORNER REVISION [CDAC]   (CDAC: nominal | cworst)
The run identity is single_edge_lpe's own: sar8-sebit-<corner>-<nom|cw>-verify-<revision>.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

from Layout.project import ROOT, evidence
from Layout.tools.simulation.prepare_full_sim import pull
from tools.saradc import single_edge_lpe

PORTS = ['CLK', 'OUTN', 'OUTP', 'VDD', 'VINN', 'VINP', 'VSS']
INCLUDE = b'include "xtor/comparator/comparator.scs"'


def digest(data):
    return hashlib.sha256(data).hexdigest()


physical_id, corner, revision = sys.argv[1:4]
cdac = sys.argv[4] if len(sys.argv) > 4 else 'nominal'
remote = evidence(physical_id)
manifest = json.loads(pull(remote + '/manifest.json'))
if manifest['case'] != 'comparator' or manifest.get('error') or manifest['checks']['lvs']['verdict'] != 'CORRECT':
    raise ValueError('Need a completed comparator physical run with LVS CORRECT')
source_hash = digest((ROOT / 'design/xtor/comparator/comparator.scs').read_bytes())
if ('* Electrical source SHA256 ' + source_hash).encode() not in pull(remote + '/reference.cdl'):
    raise ValueError('Physical reference belongs to a different comparator source')
recipe_path = ROOT / single_edge_lpe.prepare(corner, 'verify', cdac, revision)
dest = recipe_path.parent
recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
context = json.loads((dest / 'context.json').read_text(encoding='utf-8'))

expected = {'extracted.scs': manifest['checks']['pex']['sha256'], **manifest['checks']['pex']['companion_sha256']}
added = {}
for name, want in expected.items():
    blob = pull(remote + '/pex/' + name)
    if digest(blob) != want:
        raise ValueError('Extraction bytes changed: ' + name)
    added[name] = blob
joined = re.sub(r'\\\s*\n\s*', ' ', added['extracted.scs'].decode())
pins = re.search(r'(?mi)^subckt\s+sar_strongarm_t28_core\s*\(([^)]+)\)', joined)[1].split()
if sorted(pins) != sorted(PORTS):
    raise ValueError('PEX interface mismatch')
renamed, count = re.subn(r'(?m)^(subckt|ends)\s+sar_strongarm_t28_core\b', r'\1 comparator_extracted',
                         added['extracted.scs'].decode())
if count != 2:
    raise ValueError('Unexpected extracted definition count')
added['extracted.scs'] = renamed.encode()
added['comparator_pex.scs'] = ('simulator lang=spectre\ninclude "extracted.scs"\n'
                               'subckt sar_strongarm_t28 (' + ' '.join(PORTS) + ')\n'
                               'XPEX (' + ' '.join(pins) + ') comparator_extracted\n'
                               'ends sar_strongarm_t28\n').encode()
dut = (dest / 'dut.scs').read_bytes()
if dut.count(INCLUDE) != 1:
    raise ValueError('Expected one comparator include in the packaged dut.scs')
added['dut.scs'] = dut.replace(INCLUDE, b'include "comparator_pex.scs"')

scope = recipe['qualification_scope'] + '; comparator replaced by native RC extraction ' + physical_id
context.update(comparator_pex={'physical_evidence': physical_id, 'gds_sha256': manifest['gds']['sha256'],
                               'extracted_original_sha256': expected, 'extracted_ports': pins},
               qualification_scope=scope)
for name, blob in added.items():
    context['source_hashes'][name] = digest(blob)
added['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
for name, blob in added.items():
    target = dest / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
names = [row['name'] for row in recipe['inputs']]
names += [n for n in added if n not in names]
recipe.update(qualification_scope=scope, test_conditions=context,
              inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=digest((dest / n).read_bytes()))
                      for n in names])
recipe_path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8', newline='\n')
print(recipe_path.relative_to(ROOT).as_posix(), recipe['run_id'])
