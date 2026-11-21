"""Bind the block sampler fixture to the verified prefill core or its schematic."""
import argparse
import json
import re

from Layout.design.bootstrap import CORE, MASTER, candidate_of, output, reference, source
from Layout.project import ROOT, evidence
from Layout.tools.simulation.prepare_full_sim import pull, sha
from tools.saradc.blocks import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('physical_id')
    parser.add_argument('run_id')
    parser.add_argument('--schematic', action='store_true')
    parser.add_argument('--corner', choices=['tt', 'ssc', 'ssh', 'ffc', 'ffh'], default='tt',
                        help='PVT corner from specs/corners.json; MOM and passive sections stay TT')
    parser.add_argument('--candidate', help='Unselected sampler candidate from specs/candidates.json; '
                        'schematic only, with physical_id "none"')
    args = parser.parse_args()
    if args.candidate and (not args.schematic or args.physical_id != 'none'):
        parser.error('--candidate needs --schematic and physical_id "none"')
    corner = json.loads((ROOT / 'specs/corners.json').read_text(encoding='utf-8'))[args.corner]
    overrides = {'sampler': args.candidate} if args.candidate else None
    blobs = prepare(args.run_id, modules=['sampler'], candidate=overrides, preview=True)
    destination = ROOT / 'work/layout' / args.run_id
    if destination.exists():
        raise ValueError('Use a new run identity or resume the existing recipe')
    manifest = None
    if not args.candidate:
        remote = evidence(args.physical_id)
        physical = pull(remote + '/manifest.json')
        manifest = json.loads(physical)
        checks = manifest['checks']
        if (manifest['case'] != 'bootstrap' or manifest['top'] != CORE or manifest.get('error')
                or checks['lvs']['verdict'] != 'CORRECT' or 'sha256' not in checks['pex']):
            raise ValueError('Completed Bootstrap LVS and extraction required')
        # A candidate view is checked against its own netlist, not the selected one.
        built = candidate_of(manifest.get('oa_view', 'layout'))
        ref = pull(remote + '/reference.cdl')
        if (sha(ref) != manifest['source_sha256'][output(built).name]
                or ref.decode('ascii').splitlines() != reference(source(built).read_bytes()).splitlines()):
            raise ValueError('The extracted design and its schematic do not match')
        blobs['bootstrap_physical.json'] = physical
    context = json.loads(blobs['context.json'])
    if args.candidate or (manifest and built):
        context['sampler_candidate'] = args.candidate or built
    if not args.schematic:
        hashes = {'extracted.scs': checks['pex']['sha256'], **checks['pex']['companion_sha256']}
        for name, digest in hashes.items():
            if not re.fullmatch(r'extracted\.scs(?:\.[\w.-]+)?', name):
                raise ValueError('Unexpected xRC file name')
            data = pull(remote + '/pex/' + name)
            if sha(data) != digest:
                raise ValueError('Extraction hash mismatch: ' + name)
            blobs[name] = data
        joined = re.sub(r'\\\s*\n\s*', ' ', blobs['extracted.scs'].decode())
        header = re.search(r'(?im)^subckt\s+' + CORE + r'\s*\(([^)]+)\)', joined)
        native_ports = header[1].split() if header else []
        interface = {'CLKS': 'CLKS', 'VIN': 'Vin', 'VOUT': 'VOUT', 'VDD': 'VDD!', 'VSS': '0'}
        if sorted(native_ports) != sorted(interface):
            raise ValueError('Unexpected extracted core ports')
        connections = ' '.join(interface[n] for n in native_ports)
        blobs['bootstrap_pex.scs'] = (f'simulator lang=spectre\ninclude "extracted.scs"\n'
            f'subckt {MASTER} CLKS VOUT Vin\nXcore ({connections}) {CORE}\nends {MASTER}\n').encode()
        include = b'include "xtor/bootstrap/bootstrap.scs"'
        if blobs['dut.scs'].count(include) != 1:
            raise ValueError('Could not identify the electrical Bootstrap include')
        blobs['dut.scs'] = blobs['dut.scs'].replace(include, b'include "bootstrap_pex.scs"')
        context.update(extracted_ports=native_ports, extracted_sha256=hashes)

    # All sampler measurement windows end before 260 ns. Keep the two benches identical.
    original = b'stop=665n maxstep=100p errpreset=moderate'
    if blobs['test.scs'].count(original) != 1:
        raise ValueError('Review changed transient settings')
    blobs['test.scs'] = blobs['test.scs'].replace(original, b'stop=260n maxstep=5p errpreset=conservative')
    if args.corner != 'tt':
        # Supply and clock high level follow VDD; only the MOS section and temperature change.
        vdd = '%g' % corner['vdd_v']
        for name, old, new in (
                ('test.scs', 'VVDD (VDD! 0) vsource dc=0.9\n', f'VVDD (VDD! 0) vsource dc={vdd}\n'),
                ('test.scs', 'section=ttmacro_mos_moscap', 'section=' + corner['mos'].lower() + 'macro_mos_moscap'),
                ('test.scs', 'temp=27', 'temp=%d' % corner['temperature_c']),
                ('sampler_fixture.scs', 'val0=0 val1=0.9 ', f'val0=0 val1={vdd} ')):
            if blobs[name].count(old.encode()) != 1:
                raise ValueError('Review the corner substitution in ' + name + ': ' + old.strip())
            blobs[name] = blobs[name].replace(old.encode(), new.encode())
        context['conditions'].update(vdd_v=corner['vdd_v'], temperature_c=corner['temperature_c'],
                                     process=corner['mos'], passive_sections='TT, unchanged')
    view = 'schematic' if args.schematic else 'prefill RC extraction'
    if args.candidate:
        view = 'candidate ' + args.candidate + ' schematic'
    condition = '%s %g V, %d C' % (corner['mos'], corner['vdd_v'], corner['temperature_c'])
    scope = (f'Bootstrap {view}, {condition}, 50 ohm source and 256-unit native MOM load. '
             'Acquisition after the first two sample edges and hold drift.')
    context.update(run_id=args.run_id, qualification_scope=scope,
                   physical_evidence=None if args.candidate else args.physical_id,
                   gds_sha256=manifest['gds']['sha256'] if manifest else None, physical_view=view)
    context['source_hashes'].update({name: sha(data) for name, data in blobs.items() if name != 'context.json'})
    blobs['context.json'] = (json.dumps(context, indent=2) + '\n').encode()
    destination.mkdir()
    for name, data in blobs.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    recipe = dict(schema_version=1, run_id=args.run_id, design_id=MASTER, entry='test.scs',
        analyzer='analyze_blocks.py', expected_stop_s=260e-9,
        summary_signals=context['required_signals'], test_conditions=context, qualification_scope=scope,
        inputs=[dict(name=name, source=(destination / name).relative_to(ROOT).as_posix(), sha256=sha(data))
                for name, data in blobs.items()],
        resources=dict(threads=4, simulation_rss_mib=1024, simulation_virtual_mib=8192,
            analysis_rss_mib=256, analysis_virtual_mib=1024, max_output_mib=256,
            simulation_wall_seconds=1800, analysis_wall_seconds=600, queue_timeout_seconds=86400),
        spectre_args=['+preset=cx', '+mt=4', '-preset_override', '+lqtimeout', '60'])
    path = destination / 'recipe.json'
    path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
    print(path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
