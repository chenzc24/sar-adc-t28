"""Gain-corrected code check of a collected short integrated ADC run (specs/arch.json targets).

The expected code removes the gain measured independently on the standalone CDAC fixture of the
same physical view: clip(128 + floor(Vin/(LSB*k)), 0, 255), tolerance +/-1 code. A code from a SAR
search over the measured effective weights is reported alongside for diagnosis. Results are merged
into Layout/results/gain_corrected_codes.json under the integrated run identity.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from Layout.project import ROOT, write_json

RUNS = ROOT / 'work/output/managed_execution/runs'
RECORD = ROOT / 'Layout/results/gain_corrected_codes.json'


def collected(run_id):
    path = RUNS / run_id / 'collected/derived/result.json'
    return path, json.loads(path.read_text(encoding='utf-8'))


def sar_code(vin, weights):
    """Binary search over measured differential weights; the mid-scale reference is the MSB weight."""
    code = 0
    for bit in range(7, -1, -1):
        trial = code | 1 << bit
        level = sum(w for i, w in enumerate(weights) if trial >> i & 1) - weights[7]
        if vin >= level:
            code = trial
    return code


def check(run_id, weights_run=None):
    spec = json.loads((ROOT / 'specs/arch.json').read_text(encoding='utf-8'))
    tolerance = spec['targets']['integrated_code_check']['tolerance_codes']
    path, result = collected(run_id)
    lsb = result['context']['lsb_v']
    if weights_run:
        wpath, standalone = collected(weights_run)
        weights = standalone['post']['metrics']['effective_weights_v']
        source = {'run_id': weights_run, 'result_sha256': hashlib.sha256(wpath.read_bytes()).hexdigest(),
                  'view': 'extracted (post) weights of the standalone CDAC fixture'}
    else:
        weights = [lsb * 2 ** i for i in range(8)]
        source = {'run_id': None, 'view': 'schematic CDAC, k = 1'}
    k = sum(weights) / (lsb * 255)
    frames = []
    for f in result['frames']:
        expected = f['expected_code']
        vin = (expected + 0.5 - 128) * lsb
        gain_code = min(255, max(0, 128 + math.floor(vin / (lsb * k))))
        actual = f['code_90']
        frames.append({'frame': f['frame'], 'input_v': vin, 'nominal_code': expected,
                       'gain_corrected_code': gain_code, 'weight_search_code': sar_code(vin, weights),
                       'actual_code': actual, 'deviation_codes': actual - gain_code,
                       'pass': abs(actual - gain_code) <= tolerance})
    raw = result['frames']
    return {'integrated_run': run_id, 'result_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'weights': source, 'k': k, 'gain_error': 1 / k - 1, 'tolerance_codes': tolerance,
            'pass': all(f['pass'] for f in frames),
            # Sampling edges, handshake order and deadlines, independent of the expected codes.
            'timing_screens_pass': all(f['timing_pass'] and f['event_order_pass'] and f['sample_edges_pass'] for f in raw),
            'min_deadline_margin_ns': min(f['deadline_margin_ns'] for f in raw),
            # Differential TOP minus input at sample close; the analyzer screens it at 0.25 LSB.
            'max_sample_close_error_lsb': max(abs(f['sample_close_error_lsb']) for f in raw),
            'sample_residual_screen_pass': all(abs(f['sample_close_error_lsb']) <= .25 for f in raw),
            # The analyzer's own verdict also requires the nominal (gain-free) codes.
            'analyzer_nominal_code_and_timing_pass': result.get('pass_function_timing'),
            'frames': frames}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('integrated_run')
    parser.add_argument('--weights-run', help='Standalone CDAC fixture run of the same physical view; omit for schematic CDAC')
    args = parser.parse_args()
    entry = check(args.integrated_run, args.weights_run)
    record = json.loads(RECORD.read_text(encoding='utf-8')) if RECORD.exists() else {
        'definition': 'specs/arch.json targets.integrated_code_check', 'runs': {}}
    record['runs'][args.integrated_run] = entry
    write_json(RECORD, record)
    print('%s k=%.5f GE=%+.2f%% pass=%s' % (args.integrated_run, entry['k'], 100 * entry['gain_error'], entry['pass']))
    for f in entry['frames']:
        print('  frame %d nominal %3d gain-corrected %3d weight-search %3d actual %3d %s' % (
            f['frame'], f['nominal_code'], f['gain_corrected_code'], f['weight_search_code'], f['actual_code'],
            'ok' if f['pass'] else 'FAIL'))


if __name__ == '__main__':
    main()
