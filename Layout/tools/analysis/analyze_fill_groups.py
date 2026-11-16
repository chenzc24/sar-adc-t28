"""Attribute TOP loading using completed native fill-ablation extractions.

Managed analysis-only: anchored to the completed filled hold simulation.
Group gains are charge-model predictions, not new transient measurements.
"""
from __future__ import print_function
import argparse
import json
import os

from analyze_top_loading import analyze, predict, sha

FIXED = ('0', 'VSS', 'VDD', 'VREFP', 'VREFN')


def fixed_load(data):
    return sum(t['ground_f'] + sum(t['coupling_f'].get(n, 0) for n in FIXED if n != '0')
               for t in data['top'].values()) / 2


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--source-run-dir', required=True)
    a = p.parse_args()
    inputs = os.path.join(a.run_dir, 'inputs')
    config = json.load(open(os.path.join(inputs, 'fill_groups_context.json')))
    source = json.load(open(os.path.join(a.source_run_dir, 'simulation.state.json')))
    assert source['status'] == 'complete' and source['exit_code'] == 0
    assert os.path.basename(a.source_run_dir) == config['source_run_id']
    baseline = json.load(open(os.path.join(inputs, 'loading_baseline.json')))
    assert baseline['analysis_complete']
    result = dict(scope='Native fill-group extraction and settled charge model; no new transient validation or physical signoff',
                  analysis_complete=False, cases=baseline['cases'], physical_signoff=False)
    for name, case in config['cases'].items():
        directory = os.path.realpath(case['physical_directory'])
        roots=config.get('owned_evidence_roots') or [config['owned_evidence_root']]
        assert os.path.dirname(directory) in roots
        path = os.path.join(directory, 'manifest.json')
        assert sha(path) == case['manifest_sha256']
        m = json.load(open(path))
        assert m['case'] == 'full' and not m.get('error')
        assert m['stream_evidence'] == 'cdac-full-filled7'
        assert m['diagnostic']['omitted_fill'] == case['omitted_fill']
        assert m['diagnostic']['source_gds_sha256'] == config['source_gds_sha256']
        assert m['diagnostic']['functional_top_sha256'] == config['functional_top_sha256']
        assert sha(os.path.join(directory, 'fixture.gds')) == m['gds']['sha256']
        assert m['checks']['lvs']['verdict'] == 'CORRECT'
        assert all(m['checks'][k]['returncode'] == 0 for k in ('drc', 'lvs', 'phdb', 'rcc', 'format'))
        expected = dict(m['checks']['pex']['companion_sha256'])
        expected['extracted.scs'] = m['checks']['pex']['sha256']
        data = analyze(os.path.join(directory, 'pex'), expected)
        data['predicted'] = predict(data, config['unit_f'])
        data['physical_evidence'] = directory
        data['manifest_sha256'] = case['manifest_sha256']
        data['gds_sha256'] = m['gds']['sha256']
        data['drc'] = m['checks']['drc']
        data['measured_gain_ratio'] = None
        data['native_warnings'] = {}
        for phase in ('rcc', 'format'):
            # Preserve original messages rather than silently normalizing them.
            lines = open(os.path.join(directory, phase + '.console')).read().splitlines()
            data['native_warnings'][phase] = [line for line in lines if 'WARNING' in line or 'ERROR' in line]
        result['cases'][name] = data
    cases = result['cases']
    loads = {k: fixed_load(v) for k, v in cases.items()}
    gains = {k: v['predicted']['gain_ratio'] for k, v in cases.items()}
    result['mean_fixed_load_f'] = loads
    result['predicted_gain_ratio'] = gains
    result['fixed_load_factorial_f'] = dict(
        metal_without_odpo=loads['metal_only']-loads['prefill'],
        metal_with_odpo=loads['filled']-loads['odpo_only'],
        odpo_without_metal=loads['odpo_only']-loads['prefill'],
        odpo_with_metal=loads['filled']-loads['metal_only'],
        interaction=loads['filled']-loads['metal_only']-loads['odpo_only']+loads['prefill'])
    result['analysis_complete'] = True
    with open(os.path.join(a.output_dir, 'result.json'), 'w') as f:
        json.dump(result, f, indent=2, sort_keys=True)
    print(json.dumps(dict(mean_fixed_load_f=loads, predicted_gain_ratio=gains,
                          factorial=result['fixed_load_factorial_f']), indent=2))


if __name__ == '__main__':
    main()
