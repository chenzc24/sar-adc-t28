"""Freeze two small native DFF decks. Local only; no registration or simulator."""
from pathlib import Path
import copy
import difflib
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
OWN = HERE.parent
ROOT = OWN.parents[2]
sys.path.insert(0, str(OWN))
import prepare_first_event as base
import prepare_standard_cell_full as source


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, data):
    base.exact_write(path, data)


def dump(path, data):
    write(path, json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')


def make_dut():
    text = (OWN / 'standard_cell_full_v1/full_adc/dut.scs').read_text()
    blocks = base.cells(text)
    original = base.cells((OWN / 'standard_cell_full_v1/storage_dut.scs').read_text())['sar8audit_std_storage']
    statements = base.parts(original)
    keep = ['XCU19', 'XDU19', 'XRU19', 'XU19', 'XLU19_0', 'XLU19_1', 'XLU19_2']
    top = '\n'.join(['subckt sar8audit_std_usage VDD VSS FF_CK FF_D FF_RST CONTEXT'] +
                    ['    ' + statements[name]['statement'] for name in keep] + ['ends sar8audit_std_usage'])
    needed = set()

    def visit(name):
        if name in needed:
            return
        needed.add(name)
        for part in base.parts(blocks[name]).values():
            if part['model'] in blocks:
                visit(part['model'])
    for name in keep:
        visit(statements[name]['model'])
    return '\n\n'.join([blocks[name] for name in sorted(needed)] + [top]) + '\n'


def measurement(dut):
    probe = read(OWN / 'standard_cell_full_v1/library_probe.json')
    root = dict(VDD='VDD!', VSS='0', **{n: n for n in ['FF_CK', 'FF_D', 'FF_RST', 'CONTEXT']})
    flat, libraries = source.expand_library(dut, 'sar8audit_std_usage', probe, root)
    catalog, mos, pairs = {}, {}, {}
    for path, item in flat.items():
        ismos = item['model'].startswith(('nch_', 'pch_'))
        roles = ['D', 'G', 'S', 'B'] if ismos else ['PLUS', 'MINUS']
        for port, node in enumerate(item['nodes'], 1):
            catalog[path + ':' + str(port)] = dict(instance=path, terminal=roles[port-1], port=port, node=node)
        if ismos:
            d, g, s, b = item['nodes']
            mos[path] = dict(model=item['model'], nodes=item['nodes'], library=path in libraries)
            for label, (p, n) in dict(VGS=(g,s), VGD=(g,d), VDS=(d,s), VGB=(g,b), VDB=(d,b), VSB=(s,b)).items():
                pairs[path + '_' + label] = dict(positive_node=p, negative_node=n, limit_abs_v=.99)
    ports = {'VVDD': 'VDD!', **{'V'+n: n for n in ['FF_CK','FF_D','FF_RST','CONTEXT']}}
    for name, node in ports.items():
        catalog[name + ':1'] = dict(instance=name, terminal='PLUS', port=1, node=node)
    critical = ['XDUT.XU19.XFF.'+n for n in ['net176','net184','mq_x','clkbb','clkb','mq']]
    affected = {v['instance'] for v in catalog.values() if v['node'] in critical}
    # All four actual native ports of incident MOS; source currents separately.
    chosen = {p: v for p, v in catalog.items() if v['instance'] in affected or v['instance'] in ports or v['instance']=='XDUT.RCK'}
    kcl = {node: [p.lower() for p, v in catalog.items() if v['node']==node] for node in critical}
    assert all(terms and set(terms) <= {n.lower() for n in chosen} for terms in kcl.values())
    original = read(OWN / 'standard_cell_storage_v2/ff/measurement.json')
    cfg = copy.deepcopy(original)
    obs = [o for o in cfg['storage']['observers'] if o['name']=='U19']
    volts = sorted({n for x in flat.values() for n in x['nodes'] if n!='0'})
    cfg.update(scope='One native DFCNQD1 U19 with unchanged conditioners and exact original three first-hop loads; CK series resistance diagnostic only',
        voltage_saves=volts, current_saves=sorted(chosen), terminal_current_catalog=chosen,
        observed_mos=mos, library_mos=libraries, stress_voltage_pairs=pairs,
        kcl_terms=kcl, critical_kcl_nodes=critical,
        diagnostic_voltage_columns=volts, diagnostic_current_columns=sorted(chosen),
        max_derived_binary_bytes=20*1024**2,
        source_power_ports={n: dict(voltage_node=v,current=n+':1') for n,v in ports.items()},
        expected_native_peak=dict(node='XDUT.XU19.XFF.net176', value_v=0.,time_s=0.),
        proposed_reproduction_contract=dict(status='diagnostic_only_not_an_ADC_acceptance_gate',
            baseline_MM64_peak_v=1.105788039958454, baseline_MM64_peak_time_s=5.031257327444921e-9,
            proposed_peak_tolerance_v=.001, proposed_peak_time_tolerance_s=10e-12,
            reason='Isolated U19 retains exact electrical network; native global time grid differs after removing independent contexts. Review reproduction before attributing contrast.'))
    cfg['storage'].update(observers=obs, raw_all_actual_MOS_ports=False, full_history_all_KCL=False,
        phase_expected_end_source='Original external commands unchanged; actual CK/D/CDN slew and resulting delay must be measured',
        full_KCL_measured_only_at_nodes=critical, collection_cap_bytes=30*1024**2)
    cfg['usage'] = dict(input_pins=dict(CK='XDUT.U19_CK', D='XDUT.U19_D', CDN='XDUT.XU19.RN'),
        vdd_v=.99, total_native_terminal_currents=True, region_saved=False,
        current_decomposition='No intrinsic channel/overlap/junction decomposition inferred from total terminal currents',
        MM64='XDUT.XU19.XFF.MM64', MM65='XDUT.XU19.XFF.MM65')
    return cfg, flat


def main():
    original = make_dut()
    contrast = original.replace('    XU19 (U19_CK U19_D U19_Q U19_RST VDD VSS)',
                                '    RCK (U19_CK_DRV U19_CK) resistor r=2000\n    XU19 (U19_CK U19_D U19_Q U19_RST VDD VSS)')
    contrast = contrast.replace('    XCU19 (FF_CK VDD VSS U19_CK)', '    XCU19 (FF_CK VDD VSS U19_CK_DRV)')
    assert contrast != original and contrast.count('RCK (')==1
    write(HERE/'single_variable.diff', ''.join(difflib.unified_diff(original.splitlines(True),contrast.splitlines(True),fromfile='baseline/dut.scs',tofile='rck2k/dut.scs')))
    deck = (OWN/'standard_cell_storage_v2/ff/test.scs').read_text().splitlines()
    prefix = '\n'.join(deck[:14]) + '\n'
    source_lines = [x for x in deck[14:22] if x.startswith(('VVDD ', 'VFF_', 'VCONTEXT '))]
    suffix = '\n'.join(deck[21:24]) + '\n'
    library = OWN/'standard_cell_full_v1/ff/external_library.json'
    allcases = {}
    for label, text in [('baseline',original),('rck2k',contrast)]:
        folder = HERE/label
        write(folder/'dut.scs',text)
        cfg,flat = measurement(text)
        cfg['usage']['case'] = label
        dump(folder/'measurement.json',cfg)
        top = 'XDUT (VDD! 0 FF_CK FF_D FF_RST CONTEXT) sar8audit_std_usage\n'
        saves = ''.join('save '+n+'\n' for n in cfg['voltage_saves']+cfg['current_saves'])
        write(folder/'test.scs',prefix+'\n'.join(source_lines)+'\n'+top+suffix+saves)
        inputs=[('test.scs',folder/'test.scs'),('dut.scs',folder/'dut.scs'),('measurement.json',folder/'measurement.json'),
            ('external_library.json',library),('usage_analyze.py',HERE/'usage_analyze.py'),
            ('full_gate_analyze.py',OWN/'full_gate_analyze.py'),('standard_cell_full_analyze.py',OWN/'standard_cell_full_analyze.py'),
            ('fast_gate_analyze.py',OWN/'standard_cell_storage_fastanalysis_v1/fast_gate_analyze.py')]
        for n in ['ff_ck','ff_d','ff_rst','context']:
            inputs.append(('pwl/'+n+'.pwl',OWN/'standard_cell_full_v1/ff/pwl'/(n+'.pwl')))
        recipe=dict(schema_version=1,run_id='sar8audit-ctrl-usage-'+label+'-ff-v1',
            design_id='native_DFCNQD1_U19_slew_diagnostic_'+label,entry='test.scs',analyzer='usage_analyze.py',
            inputs=[dict(name=n,source=p.relative_to(ROOT).as_posix(),sha256=base.digest(p.read_bytes())) for n,p in inputs],
            expected_stop_s=20e-9,summary_signals=['XDUT.U19_Q','XDUT.U19_CK','XDUT.XU19.XFF.net176'],
            qualification_scope=cfg['scope'],oa_parity='netlist_only',
            test_conditions=dict(corner='ff',vdd=.99,temperature_c=-40,noise=False,mismatch=False,PEX=False),
            spectre_args=['+preset=cx','+mt=1','+lqtimeout','60','-preset_override'],
            resources=dict(threads=1,simulation_rss_mib=1024,simulation_virtual_mib=8192,
                analysis_rss_mib=256,analysis_virtual_mib=1024,max_output_mib=256,
                simulation_wall_seconds=300,analysis_wall_seconds=300,queue_timeout_seconds=600))
        dump(folder/'recipe.suggested.yaml',recipe)
        allcases[label]=dict(MOS=len(cfg['observed_mos']),voltage_traces=len(cfg['voltage_saves']),
            current_traces=len(cfg['current_saves']),terminal_pairs=len(cfg['stress_voltage_pairs']),
            complete_KCL_nodes=cfg['critical_kcl_nodes'],physical_leaves=flat,
            proposed_recipe_sha256=base.digest((folder/'recipe.suggested.yaml').read_bytes()))
    dump(HERE/'manifest.json',dict(cases=allcases,variable='CK series resistance absent -> ideal2000Ohm',
        external_command_PWL_unchanged=True,sampling_contract_unchanged=True,
        native_library_internals_unchanged=True,physical_implementation_of_RCK=False,
        library_characterization_coverage_unknown=True,no_simulation_or_registration=True))
    print('LOCAL_USAGE_FIXTURE_READY', {k:(v['MOS'],v['voltage_traces'],v['current_traces']) for k,v in allcases.items()})


if __name__=='__main__':
    main()
