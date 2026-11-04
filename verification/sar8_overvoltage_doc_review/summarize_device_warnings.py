"""Bounded, read-only native-log inventory; never computes waveform extrema."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'output/sar8_overvoltage_doc_review'
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hierarchy(path):
    result = {}
    current = None
    for line in path.read_text().splitlines():
        m = re.match(r'\s*subckt\s+(\S+)', line)
        if m:
            current = m[1]
            result[current] = {}
        elif re.match(r'\s*ends\b', line):
            current = None
        elif current:
            m = re.match(r'\s*(\S+)\s*\([^)]*\)\s*(\S+)', line)
            if m:
                result[current][m[1]] = m[2]
    return result


def main():
    library = json.loads((WORK / 'library_device_types.json').read_text())
    limits = json.loads((WORK / 'device_limits_raw.json').read_text())
    models = {}
    for model, data in limits['devices'].items():
        models[model] = {
            'nominal_voltage_v': 1.8 if '_18_' in model else 0.9,
            'default_warning_threshold_v': 1.98 if '_18_' in model else 0.99,
            'default_ratio': 1,
            'terminal_parameter_first_lines': {
                pair: min(expressions.values()) for pair, expressions in data['checks'].items()
            },
            'observed_check_declarations': data['count'],
            'transient_permission_envelope': None,
        }
    runs = [('A', 'tt_short', 'sar8camp-a-mm-bench-v2')]
    for variant in ('A', 'B'):
        for corner in ('ffc', 'ffh', 'ssc', 'ssh'):
            runs.append((variant, corner, f'sar8camp-{variant.lower()}-{corner}-screen-mm-v2'))
        runs.append((variant, 'tt_fft1024', f'sar8camp-{variant.lower()}-tt-fft1024-mm-v1'))
    result = {
        'scope': '11 existing collected native logs from frozen A/B campaign; not every historical experiment',
        'limitations': [
            'Printed warnings are rounded and suppressed after repeated occurrences.',
            'Values are reported events, not waveform extrema; durations and event counts are unknown.',
            'Zero printed warnings is not a complete electrical or lifetime qualification.',
            'B TT short native log is not locally collected; excluded, not treated as zero warnings.',
            'Thresholds are model warning checks, not transient voltage-duration permission.',
        ],
        'model_path': limits['path'],
        'model_sha256': next(s['sha256'] for s in json.loads((OUT / 'sources.json').read_text())['sources']
                             if s['remote_path'] == limits['path']),
        'standard_library': json.loads((WORK / 'library_identity.json').read_text()),
        'models': models,
        'runs': [],
    }
    pattern = re.compile(
        r'WARNING \((CMI-\d+)\): (\S+): (V\w+)\(=([\d.eE+\-]+) (mV|V)\) '
        r'has exceeded (\w+)\s*\(=([\d.eE+\-]+) (mV|V)\)')
    for variant, condition, run_id in runs:
        run = ROOT / 'output/managed_execution/runs' / run_id
        log = run / 'collected/spectre.out'
        netlist = run / 'inputs/dut.scs'
        assert log.stat().st_size < 1024 * 1024
        cells = hierarchy(netlist)
        cells.update(library)
        rows = []
        time = None
        for lineno, line in enumerate(log.read_text().splitlines(), 1):
            t = re.search(r'Warning from spectre at time = (.*?) during', line)
            if t:
                time = t[1]
            m = pattern.search(line)
            if not m:
                continue
            warning, instance, pair, value, unit, check, bound, boundunit = m.groups()
            parts = instance.split('.')
            assert parts[0] == 'XDUT', instance
            cell = 'sar_adc8_join_r4'
            parents = []
            for part in parts[1:]:
                parents.append(cell)
                cell = cells.get(cell, {}).get(part)
                if cell is None:
                    break
            assert cell in models, (run_id, instance, parents, cell)
            rows.append({
                'line': lineno, 'time_as_printed': time, 'warning': warning,
                'instance': instance, 'model': cell, 'parent_cell': parents[-1],
                'terminal_pair': pair, 'reported_voltage_v': float(value) * (0.001 if unit == 'mV' else 1),
                'check': check, 'reported_limit_v': float(bound) * (0.001 if boundunit == 'mV' else 1),
            })
        native_count = sum('WARNING (CMI-' in x for x in log.read_text().splitlines())
        assert native_count == len(rows), (run_id, native_count, len(rows))
        result['runs'].append({
            'run_id': run_id, 'variant': variant, 'condition': condition,
            'native_log': log.relative_to(ROOT).as_posix(), 'native_log_sha256': sha(log),
            'frozen_run_netlist': netlist.relative_to(ROOT).as_posix(), 'netlist_sha256': sha(netlist),
            'printed_terminal_warnings': len(rows), 'events': rows,
        })
    (OUT / 'device_warning_inventory.json').write_text(json.dumps(result, indent=2) + '\n')
    for run in result['runs']:
        groups = {}
        for row in run['events']:
            key = row['model']
            if key not in groups or abs(row['reported_voltage_v']) > abs(groups[key]['reported_voltage_v']):
                groups[key] = row
        print(run['run_id'], run['printed_terminal_warnings'],
              [(k, v['instance'], v['terminal_pair'], v['reported_voltage_v']) for k, v in groups.items()])


if __name__ == '__main__':
    main()
