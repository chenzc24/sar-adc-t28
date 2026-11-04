"""Review recovered native voltages and prepare one immutable FF-cold fixture.

Local only: no bridge, simulator, remote command, sizing change or registration.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

import numpy as np

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[2]
EXPORT_RUN = 'sar8audit-ctrl-native-v1'
SOURCE_RUN = 'sar8fix-loaded-both-ffcold'
FIXTURE = OWN / 'first_event_v1'
P = 'XDUT.XCTRL.XTIM.'


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def exact_write(path, blob):
    if isinstance(blob, str):
        blob = blob.encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != blob:
            raise ValueError('Preserve existing generated file: ' + str(path))
    else:
        path.write_bytes(blob)


def write_json(path, value):
    exact_write(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def collected():
    folder = ROOT / 'output/managed_execution/runs' / EXPORT_RUN / 'collected'
    receipt_path = folder / 'collection_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if receipt['skipped']:
        raise ValueError('Incomplete collection')
    files, hashes = {}, []
    for item in receipt['files']:
        name = item['name']
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Unsafe collected member')
        path = folder / name
        if not path.exists() or digest(path.read_bytes()) != item['sha256']:
            path = path.with_name(path.stem + '.' + item['sha256'][:12] + path.suffix)
        blob = path.read_bytes()
        if len(blob) != item['bytes'] or digest(blob) != item['sha256']:
            raise ValueError('Collection SHA/size mismatch: ' + name)
        files[name] = (path, blob)
        hashes.append(dict(name=name, sha256=item['sha256'], bytes=len(blob)))
    if sum(x['bytes'] for x in hashes) != receipt['total_bytes']:
        raise ValueError('Collection total mismatch')
    state = json.loads(files['analysis.state.json'][1])
    if state['status'] != 'complete' or state['exit_code'] != 0:
        raise ValueError('Native export analysis incomplete')
    result = json.loads(files['derived/result.json'][1])
    if not result['analysis_complete'] or result['source_run_id'] != SOURCE_RUN:
        raise ValueError('Recovered result identity mismatch')
    for name, entry in result['files'].items():
        blob = files['derived/' + name][1]
        if digest(blob) != entry['sha256'] or len(blob) != entry['bytes']:
            raise ValueError('Nested result hash mismatch: ' + name)
    provenance = json.loads(files['derived/source_readonly_provenance.json'][1])
    if (not provenance['source_readonly_checks_pass']
            or provenance['raw_stat_before'] != provenance['raw_stat_after']):
        raise ValueError('Source read-only evidence incomplete')
    meta = json.loads(files['derived/native_export.meta.json'][1])
    columns = json.loads(files['derived/boundary.columns.json'][1])['columns']
    names = [c['name'] for c in columns]
    values = np.frombuffer(files['derived/boundary.native.bin'][1], dtype='<f8').reshape((meta['points'], meta['columns']))
    peak_values = np.frombuffer(files['derived/peak.native.bin'][1], dtype='<f8').reshape((meta['diagnostic_points'], meta['columns']))
    if (len(names) != meta['columns'] or not np.isfinite(values).all()
            or not np.all(np.diff(values[:, 0]) > 0) or values[0, 0] != 0):
        raise ValueError('Invalid native table')
    if not np.array_equal(values[(values[:, 0] >= 40.8e-9) & (values[:, 0] <= 41.6e-9)], peak_values):
        raise ValueError('Peak table differs from native history subset')
    initial = json.loads(files['derived/initial_state.json'][1])
    if initial['time_s'] != 0 or any(initial['values_v'][n] != values[0, i] for i, n in enumerate(names) if i):
        raise ValueError('Initial-state witness differs from native row')
    idx = names.index('xdut.xctrl.xtim.x020.n')
    k = int(np.argmax(peak_values[:, idx]))
    measured = dict(node=names[idx], time_s=float(peak_values[k, 0]), value_v=float(peak_values[k, idx]))
    if measured['time_s'] != 41.089515433655805e-9 or measured['value_v'] != 1.078642014935018:
        raise ValueError('Export does not reproduce recorded native peak')
    peak_summary = json.loads(files['derived/peak_summary.json'][1])['signals']
    if any(float(peak_values[:, i].max()) != peak_summary[n]['max_v'] for i, n in enumerate(names) if i):
        raise ValueError('Native summary peak mismatch')
    review = dict(export_run=EXPORT_RUN, source_run=SOURCE_RUN, all_receipt_hashes=hashes,
        receipt_sha256=digest(receipt_path.read_bytes()), files=len(files), total_bytes=receipt['total_bytes'],
        native_points=len(values), diagnostic_points=len(peak_values), source_prefix_sha256=provenance['consumed_native_prefix_sha256'],
        native_peak=measured, export_peak_error_v=0., export_peak_time_error_s=0.,
        initial_state_witnesses=initial, parser_peak_rss_kib=meta['parser_peak_rss_kib'],
        managed_analysis_peak_rss_bytes=state['peak_rss_bytes'], analysis_elapsed_s=state['elapsed_seconds'],
        native_history_stop_s=float(values[-1, 0]), source_END_scanned=False,
        note='This verifies lossless data recovery; no isolated electrical reproduction or current attribution has run.',
        current_attribution_available=False)
    return values, names, review


def cells(text):
    return {m[1]: m[0] for m in re.finditer(r'(?ms)^subckt (\w+)\b.*?^ends \1\b[^\n]*', text)}


def parts(block):
    flat = block.replace('\\\n', ' ')
    return {m[1]: dict(nodes=m[2].split(), model=m[3], parameters=' '.join(m[4].split()), statement=m[0].strip())
            for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)', flat)}


def flatten(text, top, ports):
    blocks = cells(text)
    leaves = {}
    def walk(master, prefix, bind):
        for name, item in parts(blocks[master]).items():
            label = prefix + '.' + name
            nodes = [bind.get(n, n if n in ('0', 'VDD!') else prefix + '.' + n) for n in item['nodes']]
            if item['model'] in blocks:
                header = blocks[item['model']].replace('\\\n', ' ').splitlines()[0].split()[2:]
                if len(header) != len(nodes):
                    raise ValueError('Port count mismatch: ' + label)
                walk(item['model'], label, dict(zip(header, nodes)))
            else:
                leaves[label] = dict(model=item['model'], nodes=nodes, parameters=item['parameters'])
    walk(top, 'XDUT', ports)
    return leaves


REPLAYS = {
    'sample_int': 'xdut.sample_int', 'phi_w': 'xdut.xctrl.phi_w', 'phi_u': 'xdut.phi_u',
    'active': 'xdut.active', 'dec': 'xdut.xctrl.xtim.dec', 'topp': 'xdut.topp', 'topn': 'xdut.topn',
}


def source_line(label, node, file):
    # Managed invocation explicitly cd's into inputs before executing Spectre.
    return '    VREPLAY_%s (%s VSS) vsource type=pwl file="pwl/%s.pwl"' % (label.upper(), node, file)


def check_pwl_paths(text, package_root):
    """Resolve exactly as managed Spectre does, from the packaged inputs cwd."""
    root = Path(package_root).resolve()
    paths = re.findall(r'\bfile="([^"]+)"', text)
    expected = {'pwl/' + name + '.pwl' for name in REPLAYS}
    if len(paths) != len(expected) or set(paths) != expected:
        raise ValueError('Expected seven package-relative pwl/name.pwl paths')
    checked = []
    for relative in paths:
        target = root / relative
        if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root):
            raise ValueError('PWL path missing or outside package: ' + relative)
        checked.append(dict(name=relative, bytes=target.stat().st_size, sha256=digest(target.read_bytes())))
    return sorted(checked, key=lambda x: x['name'])


def recipe_suggestion(stop):
    """Produce a review artifact, never call the managed registrar or remote."""
    files = [('test.scs', FIXTURE / 'test.scs'), ('dut.scs', FIXTURE / 'dut.scs'),
             ('measurement.json', FIXTURE / 'measurement.json'),
             ('first_event_analyze.py', OWN / 'first_event_analyze.py')]
    files += [('pwl/' + name + '.pwl', FIXTURE / 'pwl' / (name + '.pwl')) for name in sorted(REPLAYS)]
    inputs = [dict(source=path.relative_to(ROOT).as_posix(), name=name, sha256=digest(path.read_bytes()))
              for name, path in files]
    return dict(schema_version=1, run_id='sar8audit-ctrl-first-event-v1',
        kind='simulation', design_id='sar8_control_first_event_97mos_diagnostic',
        entry='test.scs', analyzer='first_event_analyze.py', inputs=inputs,
        expected_stop_s=float(stop),
        summary_signals=['XDUT.XCTRL.XTIM.X020.N', 'XDUT.XCTRL.XTIM.X020.X000.MID',
                         'XDUT.SAMPLE_INT', 'XDUT.XCTRL.XTIM.LIVE', 'XDUT.CMP_CLK'],
        qualification_scope='First sampling-close reproduction/current KCL only; proposed acceptance unapproved; no ADC, repair, PVT or lifetime qualification',
        oa_parity='netlist_only',
        test_conditions=dict(corner='ffmacro_mos_moscap', vdd=.99, temperature_c=-40,
                             noise=False, mismatch=False, PEX=False),
        spectre_args=['+preset=cx', '+mt=1', '+lqtimeout', '60', '-preset_override'],
        resources=dict(threads=1, simulation_rss_mib=1024, simulation_virtual_mib=8192,
            analysis_rss_mib=256, analysis_virtual_mib=1024, max_output_mib=1024,
            simulation_wall_seconds=900, analysis_wall_seconds=600, queue_timeout_seconds=3600))


def construct_dut(source):
    blocks = cells(source)
    dependencies = ['sar8p_inv', 'sar8p_nand2', 'sar8p_and2', 'sar8p_or2', 'sar8p_buf',
                    'sar8p_sr', 'sar8p_delay_quiet', 'sar_strongarm_t28']
    timing_names = ['X020', 'XD_QUIET_D', 'X022', 'XCLOCK', 'X025', 'X015', 'X009',
                    'X000', 'X016', 'X017', 'X018', 'X019', 'X001', 'X023', 'X002', 'X003']
    original = parts(blocks['sar8p_timing'])
    timing = ['subckt sar8audit_timing ACTIVE CMP_CLK COMP_N COMP_P PHI_U PHI_W SAMPLE VDD VSS',
              source_line('dec', 'DEC', 'dec')]
    timing += ['    ' + original[n]['statement'] for n in timing_names]
    timing.append('ends sar8audit_timing')
    control = '\n'.join([
        'subckt sar8audit_control ACTIVE CMP_CLK COMP_N COMP_P PHI_U SAMPLE VDD VSS',
        source_line('phi_w', 'PHI_W', 'phi_w'),
        '    XTIM (ACTIVE CMP_CLK COMP_N COMP_P PHI_U PHI_W SAMPLE VDD VSS) sar8audit_timing',
        'ends sar8audit_control'])
    top = ['subckt sar8audit_ctrl_first_event VDD VSS']
    for label, node in [('sample_int', 'SAMPLE_INT'), ('phi_u', 'PHI_U'), ('active', 'ACTIVE'), ('topp', 'TOPP'), ('topn', 'TOPN')]:
        top.append(source_line(label, node, label))
    top.append('    XCTRL (ACTIVE CMP_CLK COMP_N COMP_P PHI_U SAMPLE_INT VDD VSS) sar8audit_control')
    old_top = parts(blocks['sar_adc8_join_r4'])
    top += ['    ' + old_top[n]['statement'] for n in ['XCOMP', 'CL_COMP_P', 'CL_COMP_N', 'CL_CMP_CLK']]
    top.append('ends sar8audit_ctrl_first_event')
    text = '\n\n'.join([blocks[n] for n in dependencies] + ['\n'.join(timing), control, '\n'.join(top)]) + '\n'
    original_ports = blocks['sar_adc8_join_r4'].replace('\\\n', ' ').splitlines()[0].split()[2:]
    old = flatten(source, 'sar_adc8_join_r4', dict(zip(original_ports, original_ports)))
    new = flatten(text, 'sar8audit_ctrl_first_event', {'VDD': 'VDD!', 'VSS': '0'})
    actual = {n: v for n, v in new.items() if v['model'] != 'vsource'}
    if len(actual) != 115 or sum(v['model'].startswith(('nch_', 'pch_')) for v in actual.values()) != 97:
        raise ValueError('Unexpected 97-MOS/18-passive boundary')
    if any(n not in old or v != old[n] for n, v in actual.items()):
        raise ValueError('Retained native instance connectivity/parameter drift')
    if sum(v['model'] == 'vsource' for v in new.values()) != 7:
        raise ValueError('Unexpected replay-source count')
    forbidden = {'XDUT.COMP_P', 'XDUT.COMP_N', P + 'WD', P + 'PR', P + 'NR', P + 'QUIET', P + 'CLOCK_Q', 'XDUT.CMP_CLK'}
    driven = {v['nodes'][0] for v in new.values() if v['model'] == 'vsource'}
    if forbidden & driven:
        raise ValueError('Ideal source drives retained native output')
    return text, new, {n: digest(blocks[n].encode()) for n in dependencies}


def edge_time(t, v, rail, rising):
    x = v - .5 * rail
    indices = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0) if rising else (x[:-1] > 0) & (x[1:] <= 0))
    return [float(t[i] - x[i] * (t[i + 1] - t[i]) / (x[i + 1] - x[i])) for i in indices]


def measurement(leaves, review, t, names, values):
    catalog, currents = {}, set()
    for name, item in leaves.items():
        labels = ['D', 'G', 'S', 'B'] if item['model'].startswith(('nch_', 'pch_')) else ['PLUS', 'MINUS']
        for i, node in enumerate(item['nodes']):
            if item['model'].startswith(('nch_', 'pch_')) or node != '0':
                trace = name + ':' + str(i + 1)
                currents.add(trace)
                catalog[trace] = dict(instance=name, terminal=labels[i], port=i + 1, node=node, kcl_coefficient=1)
    catalog['VVDD:1'] = dict(instance='VVDD', terminal='PLUS', port=1, node='VDD!', kcl_coefficient=1)
    currents.add('VVDD:1')
    voltages = sorted({node for item in leaves.values() for node in item['nodes'] if node != '0'})
    kcl = {node: [trace.lower() for trace, item in catalog.items() if item['node'] == node]
           for node in voltages if node != 'VDD!'}
    primary = P + 'X020.N'
    if len(kcl[primary]) != 5:
        raise ValueError('Primary NAND-node KCL must have five native terminal contributions')
    critical_nodes = [P + n for n in ['X020.N', 'X020.X000.MID', 'QUIET', 'XD_QUIET_D.RC0', 'XD_QUIET_D.RC1', 'CLOCK_SET', 'CLOCK_Q']]
    critical_i = sorted(set(sum((kcl[n] for n in critical_nodes), [])))
    rail = values[:, names.index('vdd!')]
    expected_edges = {}
    for node, rising in [('xdut.sample_int', False), (P.lower() + 'live', True),
                         (P.lower() + 'clock_reset', False), (P.lower() + 'quiet', True)]:
        expected_edges[node] = dict(direction=1 if rising else -1,
            time_s=edge_time(t, values[:, names.index(node)], rail, rising),
            method='0.5VDD crossing interpolated between original native samples; not a new waveform sample')
    return dict(schema_version=1, scope='First sampling-close FF-cold isolation; no comparison/ADC/PVT qualification',
        source_run=SOURCE_RUN, export_run=EXPORT_RUN, source_history_stop_s=float(t[-1]),
        diagnostic_start_s=40.8e-9, diagnostic_stop_s=float(t[-1]),
        voltage_saves=voltages, current_saves=sorted(currents), terminal_current_catalog=catalog,
        kcl_terms=kcl, critical_kcl_nodes=critical_nodes, diagnostic_current_columns=critical_i,
        sign_convention='Native terminal current positive leaving its connected node into the device; KCL is the signed sum. Injection into node is negative of this current.',
        native_port_policy='MOS D/G/S/B ports1/2/3/4. Passive/source ports use explicit netlist order; only grounded return ports may be omitted. Require every requested TRACE; never fill missing current with zero.',
        current_multiplicity='Native terminal currents already include instance multiplicity; do not multiply again',
        expected_native_peak=review['native_peak'], expected_initial_state=review['initial_state_witnesses'], expected_edges=expected_edges,
        diagnostic_voltage_columns=names[1:],
        proposed_reproduction_contract=dict(status='proposal_pending_parent_review',
            peak_voltage_error_abs_v=.001, peak_time_error_abs_s=5e-12,
            expected_edge_time_error_abs_s=5e-12, initial_witness_error_abs_v=.001,
            critical_kcl_peak_abs_a=1e-9,
            rationale='Numerical first-reproduction diagnostics at unchanged devices and native replay; not ADC accuracy, lifetime or a zero-stress pass requirement.'),
        acceptance_pass=None, max_derived_binary_bytes=30 * 1024**2,
        boundary_differences=[
            'SAMPLE_INT/PHI_W/PHI_U/ACTIVE replace omitted sampler buffer/write/update/token networks with measured voltage histories.',
            'TOPP/TOPN replace CDAC/Bootstrap input impedance and reciprocal comparator kickback; preserve recorded baseline voltages only.',
            'DEC replaces omitted RAW/XOR/qualification feedback. Native COMP outputs and X002/X003 receivers remain physically driven.',
            'PR/NR downstream qualification fanout and WD-to-X010 write-clock fanout are omitted; no artificial voltage clamps or guessed lumped capacitors replace them.',
            'Full native SR internal feedback, clock buffer/direct load, Q1/LIVE/reset forward logic and original MOM/RC components are retained.',
            'Stop before the original first compare at 43.468866 ns. This fixture addresses the 41.089515 ns event only.'])


def plot_native(values, names):
    os.environ.setdefault('MPLCONFIGDIR', str(OWN / '.mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    t = values[:, 0] * 1e9
    sel = (t >= 41.04) & (t <= 41.20)
    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True, layout='constrained')
    groups = [(['xdut.sample_int', 'xdut.xctrl.xtim.live', 'xdut.xctrl.xtim.q1'], ['SAMPLE_INT', 'LIVE', 'Q1']),
              (['xdut.xctrl.xtim.x020.n', 'xdut.xctrl.xtim.x020.x000.mid'], ['NAND output N', 'NAND MID']),
              (['xdut.xctrl.xtim.quiet', 'xdut.xctrl.xtim.quiet_d', 'xdut.cmp_clk'], ['QUIET', 'QUIET_D', 'CMP_CLK'])]
    for ax, (signals, labels) in zip(axes, groups):
        for name, label in zip(signals, labels):
            ax.plot(t[sel], values[sel, names.index(name)], lw=1.25, label=label)
        ax.axvline(41.089515433655805, color='#777', ls=':', lw=.8)
        ax.set_ylabel('Voltage (V)'); ax.grid(alpha=.2); ax.legend(fontsize=8, ncol=3, loc='best')
    axes[1].axhline(.99, color='#b34b40', ls='--', lw=.9, label='0.99 V core screening line')
    axes[1].plot(41.089515433655805, 1.078642014935018, 'o', color='#b34b40', ms=4)
    axes[1].annotate('1.07864 V\n41.089515 ns', xy=(41.089515433655805, 1.078642014935018),
                     xytext=(41.125, .78), fontsize=9, arrowprops=dict(arrowstyle='->', lw=.8))
    axes[1].legend(fontsize=8, ncol=3, loc='lower left')
    axes[-1].set(xlabel='Time (ns)', xlim=(41.04, 41.20))
    fig.suptitle('Original FF-cold control: first sampling-close event', fontsize=13)
    fig.supxlabel('0.99 V / -40 C; IO reference + N4, original core control; native points, no resampling\n'
                  'External supplies/clock ideal; no mismatch, transient noise or PEX; currents not yet measured', fontsize=8)
    path = OWN / 'native_first_event.png'
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    values, names, review = collected()
    config = json.loads((OWN / 'native_export_manifest.json').read_text())
    folder = ROOT / 'output/managed_execution/runs' / SOURCE_RUN / 'inputs'
    source = {}
    for name, expected in config['source_input_sha256'].items():
        blob = (folder / name).read_bytes()
        if digest(blob) != expected:
            raise ValueError('Frozen source changed: ' + name)
        source[name] = blob.decode().replace('\r\n', '\n')
    dut, leaves, cell_hashes = construct_dut(source['dut.scs'])
    exact_write(FIXTURE / 'dut.scs', dut)
    for label, name in REPLAYS.items():
        lines = ''.join('%.17g %.17g\n' % (row[0], row[names.index(name)]) for row in values)
        exact_write(FIXTURE / 'pwl' / (label + '.pwl'), lines)
    checked_paths = check_pwl_paths(dut, FIXTURE)
    measure = measurement(leaves, review, values[:, 0], names, values)
    write_json(FIXTURE / 'measurement.json', measure)
    includes = '\n'.join(line for line in source['test.scs'].splitlines() if line.startswith('include "/home/process/'))
    saves = sorted(set(measure['voltage_saves'] + measure['current_saves']))
    deck = ('// First-event isolation only: native device/geometry preserved.\n'
        'simulator lang=spectre\nglobal 0 VDD!\n' + includes + '\ninclude "dut.scs"\n'
        'VVDD (VDD! 0) vsource dc=0.99 type=dc\n'
        'XDUT (VDD! 0) sar8audit_ctrl_first_event\n'
        'simulatorOptions options psfversion="1.4.0" method=gear2only reltol=1e-6 vabstol=1e-8 iabstol=1e-13 '
        'temp=-40 tnom=27 scalem=1 scale=1 gmin=1e-12 rforce=1 maxnotes=5 maxwarns=5 digits=5 cols=80 pivrel=1e-3 checklimitdest=psf\n'
        'saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no\n'
        'tran_first tran stop=%.17g maxstep=10p errpreset=conservative lteratio=10\n' % values[-1, 0]
        + '\n'.join('save ' + n for n in saves) + '\n')
    exact_write(FIXTURE / 'test.scs', deck)
    catalog = dict(schema_version=1, source_hashes=config['source_input_sha256'],
        inherited_cell_text_sha256=cell_hashes, retained_native_devices={k: v for k, v in leaves.items() if v['model'] != 'vsource'},
        replay_sources={k: v for k, v in leaves.items() if v['model'] == 'vsource'},
        native_MOS=97, native_passives=18, original_history_points=len(values),
        all_retained_parameters_and_nodes_match=True, generated_hardware_output_voltage_sources=[])
    write_json(FIXTURE / 'device_identity.json', catalog)
    write_json(FIXTURE / 'package_paths.json', dict(spectre_working_directory='managed RUN/inputs',
        package_relative_paths=checked_paths, all_paths_resolve=True, registration_or_submission_performed=False))
    # JSON is valid YAML, consistent with existing managed recipe source files.
    write_json(FIXTURE / 'recipe.suggested.yaml', recipe_suggestion(values[-1, 0]))
    write_json(OWN / 'recovered_review.json', review)
    plot_native(values, names)
    print(json.dumps(dict(receipt_files=review['files'], receipt_bytes=review['total_bytes'], native_peak=review['native_peak'],
        fixture=str(FIXTURE), MOS=97, passives=18, pwl_files=7, native_points=len(values),
        pwl_total_bytes=sum(p.stat().st_size for p in (FIXTURE / 'pwl').iterdir()), simulation_started=False)))


if __name__ == '__main__':
    main()
