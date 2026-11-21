"""Kickback into the extracted CDAC TOP: clone a prepared standalone comparator corner package and
replace the floating-input fixture's two 256-unit MOM loads by the extracted 510-terminal CDAC.

The CDAC is held in a static valid state (each bit's GN = GP: 0 drives the plate to VREFP, VDD to
VREFN), the MSB trial: P side bit 7 high and bits 6..0 low, N side complementary. References are the
ADC testbench model (ideal source, 50 ohm, 4 pF). The sampling switches, release time, clock and the
analyzer's kickback measurement are unchanged.
Usage: make_kick.py SOURCE_PACKAGE RUN_ID [--cdac nominal|cworst]
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.saradc import single_edge_lpe  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source')
    ap.add_argument('run_id')
    ap.add_argument('--cdac', choices=['nominal', 'cworst'], default='nominal')
    a = ap.parse_args()
    src, dest = ROOT / 'work/layout' / a.source, ROOT / 'work/layout' / a.run_id
    if dest.exists():
        raise ValueError('Identity already prepared')
    recipe = json.loads((src / 'recipe.json').read_text(encoding='utf-8'))
    blobs = {row['name']: (src / row['name']).read_bytes() for row in recipe['inputs']}
    for row in recipe['inputs']:
        if sha(blobs[row['name']]) != row['sha256']:
            raise ValueError('Source package changed: ' + row['name'])
    context = json.loads(blobs['context.json'])
    vdd = (context.get('corner') or {}).get('vdd_v', 0.9)
    bundle = single_edge_lpe.cdac_bundle(a.cdac, 'ssc' if a.cdac == 'cworst' else 'tt')
    cdac = bundle['files']
    original = re.search(r'(?m)^subckt\s+(\S+)\s*\(', cdac['cdac_pex_wrapper.scs'].decode())[1]
    # The block fixture's dut.scs already defines the schematic CDAC under this name; rename the wrapper only.
    master = 'cdac_kick_extracted'
    wrapper, count = re.subn(r'(?m)^(subckt|ends)\s+' + re.escape(original) + r'\b', r'\1 ' + master,
                             cdac['cdac_pex_wrapper.scs'].decode())
    if count != 2:
        raise ValueError('Unexpected CDAC wrapper definition count')
    cdac = dict(cdac, **{'cdac_pex_wrapper.scs': wrapper.encode()})
    fixture = blobs['comparator_fixture.scs'].decode()
    old = ('CKP (k_p 0) cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 multi=256 mismatchflag=1\n'
           'CKN (k_n 0) cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 multi=256 mismatchflag=1\n')
    if fixture.count(old) != 1:
        raise ValueError('Kickback MOM loads changed')
    gates, sources = [], []
    for kind in ('GN', 'GP'):
        for side in ('N', 'P'):
            for bit in range(8):
                name = 'k_%s%s%d' % (kind.lower(), side.lower(), bit)
                gates.append(name)
                high = (bit == 7) == (side == 'P')
                sources.append('VK%s%s%d (%s 0) vsource dc=%g' % (kind, side, bit, name, 0 if high else vdd))
    new = ('// Extracted CDAC TOP (%s xRC, %s) replaces the 256-unit MOM loads; static MSB-trial state.\n'
           'include "cdac_pex_wrapper.scs"\n'
           'XKCDAC (%s k_n k_p VDD! k_vrefn k_vrefp 0) %s\n%s\n'
           'VKREFN (k_vrefn_src 0) vsource dc=0\nRKREFN (k_vrefn_src k_vrefn) resistor r=50\nCKREFN (k_vrefn 0) capacitor c=4p\n'
           'VKREFP (k_vrefp_src 0) vsource dc=%g\nRKREFP (k_vrefp_src k_vrefp) resistor r=50\nCKREFP (k_vrefp 0) capacitor c=4p\n'
           % (a.cdac, bundle['source'], ' '.join(gates), master, '\n'.join(sources), vdd))
    blobs['comparator_fixture.scs'] = fixture.replace(old, new).encode()
    blobs.update(cdac)
    scope = recipe['qualification_scope'] + ('; kickback source is the extracted CDAC (%s, %s) in a static MSB-trial '
                                             'state with 50 ohm / 4 pF references instead of 256 MOM units' % (a.cdac, bundle['source']))
    context.update(run_id=a.run_id, kickback_cdac=dict(view=a.cdac, source=bundle['source'], gds_sha256=bundle['gds'],
                                                       master=master, original_master=original, state='P bit7 high, N complementary'),
                   source_package=a.source, qualification_scope=scope)
    context['source_hashes'].update({n: sha(b) for n, b in blobs.items() if n != 'context.json'})
    blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
    dest.mkdir(parents=True)
    for name, data in blobs.items():
        (dest / name).parent.mkdir(parents=True, exist_ok=True)
        (dest / name).write_bytes(data)
    recipe.update(run_id=a.run_id, qualification_scope=scope, test_conditions=context,
                  inputs=[dict(name=n, source=(dest / n).relative_to(ROOT).as_posix(), sha256=sha(d)) for n, d in blobs.items()])
    recipe['resources'].update(simulation_rss_mib=4096, simulation_virtual_mib=16384, simulation_wall_seconds=10800)
    (dest / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(a.run_id)


if __name__ == '__main__':
    main()
