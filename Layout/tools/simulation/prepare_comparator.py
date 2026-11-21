"""Prepare matched schematic/PEX comparator fixtures for the managed runner."""
import argparse
import json
import re

from Layout.project import ROOT, evidence
from Layout.tools.simulation.prepare_full_sim import pull, sha
from tools.saradc.blocks import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('physical_id')
    parser.add_argument('run_id')
    parser.add_argument('--schematic', action='store_true')
    parser.add_argument('--integrated', action='store_true', help='Use the current ten-frame ADC interface fixture')
    parser.add_argument('--corner', choices=['tt', 'ssc', 'ssh', 'ffc', 'ffh'], default='tt',
                        help='PVT corner of the --integrated fixture (specs/corners.json)')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,55}', args.run_id):
        raise ValueError('Invalid run identity')
    if args.corner != 'tt' and not args.integrated:
        parser.error('--corner applies only to the --integrated fixture')
    destination = ROOT / 'work/layout' / args.run_id
    if destination.exists():
        raise ValueError('Identity already prepared')
    remote = evidence(args.physical_id)
    manifest_bytes = pull(remote + '/manifest.json')
    manifest = json.loads(manifest_bytes)
    if manifest['case'] not in ('comparator','comparator-filled') or manifest.get('error'):
        raise ValueError('Need completed comparator physical evidence')
    if manifest['checks']['lvs']['verdict'] != 'CORRECT':
        raise ValueError('Comparator LVS must pass')
    allowed = {'OD.DN.3', 'PO.DN.3', 'PO.DN.3.1',
               'DIODMY_L:WARNING', 'IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1'}
    if set(manifest['checks']['drc']['markers_by_rule']) - allowed:
        raise ValueError('Unresolved local DRC')
    reference = pull(remote + '/reference.cdl')
    source_hash = sha((ROOT/'design/xtor/comparator/comparator.scs').read_bytes())
    if ('* Electrical source SHA256 ' + source_hash).encode() not in reference:
        raise ValueError('Physical reference belongs to a different comparator source')
    base_recipe = None
    if args.integrated:
        from tools.saradc.reference_short import prepare as prepare_current
        codes = json.loads((ROOT/'tb/top/short/context.json').read_text(encoding='utf-8'))['expected_codes']
        # Keep the current fixture's own output budget; it depends on what that fixture saves.
        staging = ROOT/prepare_current('current',args.corner,args.run_id,codes=codes)
        base_recipe = json.loads(staging.read_text(encoding='utf-8'))
        blobs = {row['name']:(ROOT/row['source']).read_bytes() for row in base_recipe['inputs']}
    else:
        blobs = prepare(args.run_id, modules=['comparator'], preview=True)
    context = json.loads(blobs['context.json'])
    blobs['comparator_physical.json'] = manifest_bytes
    if not args.schematic:
        original_hashes = {'extracted.scs': manifest['checks']['pex']['sha256'],
                           **manifest['checks']['pex']['companion_sha256']}
        for name, expected in original_hashes.items():
            if not re.fullmatch(r'extracted\.scs(?:\.[A-Za-z0-9_.-]+)?', name):
                raise ValueError('Unexpected extraction filename')
            blob = pull(remote + '/pex/' + name)
            if sha(blob) != expected:
                raise ValueError('Extraction bytes changed')
            blobs[name] = blob
        joined = re.sub(r'\\\s*\n\s*', ' ', blobs['extracted.scs'].decode())
        extracted_top = manifest['top']
        pins = re.search(r'(?mi)^subckt\s+'+re.escape(extracted_top)+r'\s*\(([^)]+)\)', joined)[1].split()
        ports = ['CLK', 'OUTN', 'OUTP', 'VDD', 'VINN', 'VINP', 'VSS']
        if sorted(pins) != sorted(ports):
            raise ValueError('PEX interface mismatch')
        # A filled layout has the electrical master name. Rename only its
        # extracted definition, then restore the original positional interface.
        renamed, count = re.subn(r'(?m)^(subckt|ends)\s+'+re.escape(extracted_top)+r'\b',
                                 r'\1 comparator_extracted', blobs['extracted.scs'].decode())
        if count != 2:
            raise ValueError('Unexpected extracted definition count')
        blobs['extracted.scs'] = renamed.encode()
        blobs['comparator_pex.scs'] = ('simulator lang=spectre\ninclude "extracted.scs"\n'
            'subckt sar_strongarm_t28 (' + ' '.join(ports) + ')\n'
            'XPEX (' + ' '.join(pins) + ') comparator_extracted\n'
            'ends sar_strongarm_t28\n').encode()
        original = blobs['dut.scs']
        needle = b'include "xtor/comparator/comparator.scs"'
        if original.count(needle) != 1:
            raise ValueError('Comparator include changed')
        blobs['dut.scs'] = original.replace(needle, b'include "comparator_pex.scs"')
        context['extracted_original_sha256'] = original_hashes
        context['extracted_ports'] = pins
    # Same fixture, native loading, solver settings and measurements in both runs.
    if not args.integrated:
        deck = blobs['test.scs'].decode().replace('stop=665n maxstep=100p errpreset=moderate',
                                                 'stop=105n maxstep=2p errpreset=conservative')
        blobs['test.scs'] = deck.encode()
    scope = ('TT 0.9V 27C comparator ' + ('schematic' if args.schematic else manifest['case']+' RC extraction') +
             '; signed input decisions, reset and floating-input kickback with original block fixture. '
             'Density/final fill, PVT, mismatch/noise and integrated ADC timing remain unqualified.')
    if args.integrated:
        corner = json.loads((ROOT/'specs/corners.json').read_text(encoding='utf-8'))[args.corner]
        condition = '%s %gV %dC' % (corner['mos'], corner['vdd_v'], corner['temperature_c'])
        scope = ('Current ADC ten-frame ' + condition + ' functional/timing fixture with comparator ' +
                 ('schematic' if args.schematic else manifest['case']+' RC extraction') +
                 '; remaining modules pre-layout; no noise, mismatch, PVT or terminal-reliability signoff.')
    context.update(physical_evidence=remote, gds_sha256=manifest['gds']['sha256'],
                   run_id=args.run_id, pex=not args.schematic, qualification_scope=scope)
    context['source_hashes'].update({name:sha(data) for name,data in blobs.items() if name!='context.json'})
    blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
    destination.mkdir(parents=True)
    for name, data in blobs.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    recipe = dict(schema_version=1, run_id=args.run_id, design_id='sar_strongarm_t28_layout',
                  entry='test.scs', analyzer='analyze_blocks.py',
                  inputs=[dict(name=name, source=(destination/name).relative_to(ROOT).as_posix(), sha256=sha(data))
                          for name, data in blobs.items()],
                  resources=dict(threads=4, simulation_rss_mib=1024, simulation_virtual_mib=8192,
                                 analysis_rss_mib=256, analysis_virtual_mib=1024, max_output_mib=256,
                                 simulation_wall_seconds=1800, analysis_wall_seconds=600, queue_timeout_seconds=86400),
                  spectre_args=['+preset=cx', '+mt=4', '-preset_override', '+lqtimeout', '60'],
                  summary_signals=['c_clock', 'c_outn', 'c_outp'], expected_stop_s=105e-9,
                  qualification_scope=scope, test_conditions=context)
    if base_recipe:
        for key in ['resources','spectre_args','summary_signals','expected_stop_s','analyzer']:
            recipe[key] = base_recipe[key]
    path = destination / 'recipe.json'
    path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
    print(path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
