"""Join the source-verified Stage 6 conversion and register feed measurements by case."""
import argparse
import hashlib
import json
from pathlib import Path


def measured(f):
    path = f / 'collected/derived/result.json'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    receipt = json.loads((f / 'collected/collection_receipt.json').read_bytes())
    status = receipt['status']
    if status['analysis']['status'] != 'complete' or status['simulation']['status'] != 'complete':
        raise ValueError('Incomplete result: ' + f.name)
    if not any(row['name'] == 'derived/result.json' and row['sha256'] == digest for row in receipt['files']):
        raise ValueError('Digest differs from the native result collection receipt')
    return dict(run=f.name, host=status.get('host'), recipe_hash=status['registered']['recipe_hash'],
                result_sha256=digest), json.loads(raw)


def combine(core_results, register_runs):
    core = {r['parent']: r for r in json.loads(core_results.read_bytes())}
    out = []
    for folder in register_runs:
        identity, result = measured(folder)
        if not result['passed']:
            raise ValueError('Register-word comparison failed: ' + folder.name)
        plan = result['plan']
        for case in plan['cases']:
            row = core.pop(case['parent'])
            reg = result['cases'][case['case']]
            if (row['corner'] != plan['corner'] or len(row['frames']) != len(case['codes'])
                    or abs(row['period_s']-plan['period_ns']*1e-9) > 1e-15):
                raise ValueError('Source power windows differ')
            if [f['q_read'] for f in reg['frames']] != case['codes']:
                raise ValueError('Replay differs from the source code words')
            total = row['combined_uW'] + reg['register_uW']
            out.append(dict(corner=plan['corner'], case=case['case'], design_v=plan['vdd_v'],
                            io_v=plan['vddio_v'], temperature_c=plan['temperature_c'],
                            core_parent=case['parent'], core_power_run=row['run'],
                            core_power_result_sha256=row['result_sha256'],
                            parent_readout_sha256=case['parent_result_sha256'],
                            register_measurement=identity, duration_ns=len(case['codes'])*plan['period_ns'],
                            core_uW=row['core_uW'], reference_uW=row['reference_uW'],
                            register_uW=reg['register_uW'], total_uW=total,
                            total_pJ_per_conversion=total*row['period_s']*1e6, within_1mW=total<=1000.,
                            register_measurement_start_ns=case['measure_begin_ns'],
                            alternate_sample_register_uW=reg['alternate_sample_uW'],
                            output_replay_source=plan['output_fixture'],
                            board_load_pf=plan['board_load_pf'],
                            frames=reg['frames']))
    if core:
        raise ValueError('Missing register measurement for ' + ', '.join(sorted(core)))
    return dict(measured_count=len(out), limit_uW=1000.,
                scope='Original Stage 6 Core and VREF power paired with the register-pin power measured in an extracted-output replay of the same seven scored codes. Pad supplies and the external clock source are separate.',
                cases=out)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('core_results', type=Path)
    cli.add_argument('register_runs', type=Path, nargs='+')
    args = cli.parse_args()
    print(json.dumps(combine(args.core_results,args.register_runs),indent=2))
