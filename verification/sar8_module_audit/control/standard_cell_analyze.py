"""Identity/probe/edge wrapper around the frozen native reducer. Python2.7/3."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import re
import struct
import sys

import full_gate_analyze as native


def file_identity(path):
    sha = hashlib.sha256()
    size = 0
    with open(path,'rb') as handle:
        while True:
            blob = handle.read(65536)
            if not blob:
                break
            sha.update(blob); size += len(blob)
    return dict(sha256=sha.hexdigest(),bytes=size)


def verify_library(manifest_path):
    manifest = native.read(manifest_path)
    for name,expected in manifest['metadata_inputs'].items():
        if file_identity(os.path.join(os.path.dirname(manifest_path),name)) != expected:
            raise ValueError('Required supplied metadata SHA/size differs: '+name)
    actual = file_identity(manifest['file'])
    if actual != dict(sha256=manifest['sha256'],bytes=manifest['bytes']):
        raise ValueError('Read-only foundry SPICE SHA/size mismatch')
    return dict(file=manifest['file'],sha256=actual['sha256'],bytes=actual['bytes'],
                checked_at='analysis or explicit identity-only preflight; no time-of-use proof',
                source_content_modified=False)


def diagnostic_timing(output,cfg):
    """Native rows only; linear interpolation locates threshold events, not new waves."""
    columns = native.read(os.path.join(output,'peak.columns.json'))['names']
    prefix = 'xdut.xctrl.xtim.'
    signals = ['xdut.sample_int',prefix+'sn',prefix+'q1',prefix+'live',prefix+'x020.n',
               prefix+'quiet',prefix+'quiet_d',prefix+'clock_reset',prefix+'clock_set',
               prefix+'clock_q','xdut.cmp_clk',prefix+'xd_quiet_d.rc0',prefix+'xd_quiet_d.rc1',
               prefix+'xd_quiet_d.ab']
    indices = dict((n,columns.index(n)) for n in signals)
    rail = columns.index('vdd!')
    events = dict((n,[]) for n in signals)
    previous = None
    last = {}
    row_struct = struct.Struct('<'+'d'*len(columns))
    with open(os.path.join(output,'peak.native.bin'),'rb') as handle:
        while True:
            blob = handle.read(row_struct.size)
            if not blob:
                break
            if len(blob) != row_struct.size:
                raise ValueError('Incomplete diagnostic native row')
            row = row_struct.unpack(blob)
            for name,index in indices.items():
                last[name] = row[index]
                if previous is None:
                    continue
                for fraction in [.1,.5,.9]:
                    before = previous[index]-fraction*previous[rail]
                    after = row[index]-fraction*row[rail]
                    direction = 1 if before < 0 <= after else -1 if before > 0 >= after else 0
                    if direction:
                        at = previous[0]-before*(row[0]-previous[0])/(after-before)
                        events[name].append(dict(fraction=fraction,direction=direction,time_s=at))
            previous = row
    if previous is None:
        raise ValueError('Missing diagnostic native rows')
    metrics = {}
    for name in signals:
        sequence = sorted(events[name],key=lambda v:v['time_s'])
        halves = [e for e in sequence if e['fraction']==.5]
        pulses = []
        opened = None
        for event in halves:
            if event['direction']==1:
                opened = event['time_s']
            elif opened is not None:
                pulses.append(dict(start_s=opened,stop_s=event['time_s'],width_s=event['time_s']-opened)); opened=None
        slew = {1:[], -1:[]}
        pending = {1:None,-1:None}
        for e in sequence:
            f,d,at = e['fraction'],e['direction'],e['time_s']
            if (f,d)==(.1,1): pending[1]=at
            if (f,d)==(.1,-1): pending[1]=None
            if (f,d)==(.9,-1): pending[-1]=at
            if (f,d)==(.9,1): pending[-1]=None
            if (f,d) in [(.9,1),(.1,-1)] and pending[d] is not None:
                slew[d].append(at-pending[d]); pending[d]=None
        metrics[name] = dict(threshold_events=sequence,
            rise_halfrail_count=sum(e['direction']==1 for e in halves),
            fall_halfrail_count=sum(e['direction']==-1 for e in halves),
            observed_high_pulses=pulses,open_high_pulse_at_stop=opened is not None,
            rise_10_90_s=slew[1],fall_90_10_s=slew[-1],end_voltage_v=last[name],
            no_halfrail_edge_observed=(not halves),full_settling_pass=None)
    closes = [e['time_s'] for e in events['xdut.sample_int'] if e['fraction']==.5 and e['direction']==-1]
    if len(closes)!=1:
        raise ValueError('Expected exactly one preserved sample closing edge in diagnostic window')
    return dict(start_s=cfg['diagnostic_start_s'],stop_s=previous[0],sample_close_s=closes[0],signals=metrics,
                scope='Diagnostic native window only; all crossings retained without glitch rejection. Missing event is unobserved, not zero delay. No full-cycle/reset claim.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir')
    parser.add_argument('--output-dir')
    parser.add_argument('--check-library',metavar='MANIFEST')
    args = parser.parse_args()
    if args.check_library:
        print(json.dumps(verify_library(args.check_library),sort_keys=True)); return
    if not args.run_dir or not args.output_dir:
        parser.error('--run-dir and --output-dir required for analysis')
    run,output = os.path.realpath(args.run_dir),os.path.realpath(args.output_dir)
    if output != os.path.join(run,'derived') or os.path.exists(os.path.join(output,'result.json')):
        raise ValueError('Expected fresh managed derived directory')
    library = verify_library(os.path.join(run,'inputs','external_library.json'))
    state = native.read(os.path.join(run,'simulation.state.json'))
    if (state['status']!='complete' or state['exit_code']!=0
            or not state.get('native',{}).get('native_analysis_pass')
            or not state.get('native',{}).get('zero_error_footer')):
        raise ValueError('Native fixture simulation not complete')
    with open(os.path.join(run,'raw','logStatus')) as handle:
        if not re.search(r'tran_first\s+PASS',handle.read()):
            raise ValueError('Native transient PASS missing')
    paths = [os.path.join(run,'raw',name) for name in os.listdir(os.path.join(run,'raw')) if name.endswith('.tran.tran')]
    if len(paths)!=1:
        raise ValueError('Expected one native ASCII transient')
    cfg_path = os.path.join(run,'inputs','measurement.json')
    cfg = native.read(cfg_path)
    result = native.summarize(paths[0],cfg,output)
    result['measurement_sha256'] = file_identity(cfg_path)['sha256']
    result['external_library_identity'] = library
    binding = cfg['standard_cell_experiment']['library_mos']
    result['standard_cell_native_current_bindings'] = dict((name,dict(
        requested=item['requested_numeric_terminal_currents'],
        actual=dict((p,result['trace_bindings'][native.norm(p)]) for p in item['requested_numeric_terminal_currents']),
        nested_inline_primitive_probe_not_used=True)) for name,item in binding.items())
    result['diagnostic_timing'] = diagnostic_timing(output,cfg)
    groups = {}
    stress = result['full_history_voltage_stress']
    for name,item in cfg['standard_cell_experiment']['observed_mos'].items():
        group = groups.setdefault(item['group'],dict(MOS=0,pairs=0,failed_pairs=0,failed_instances=[]))
        group['MOS']+=1; group['pairs']+=len(item['six_pair_labels'])
        failed = sum(stress[label]['over_limit_native_points']>0 for label in item['six_pair_labels'].values())
        group['failed_pairs']+=failed
        if failed: group['failed_instances'].append(name)
    result['physical_terminal_screen_groups'] = groups
    result['native_warning_codes'] = state['native'].get('warning_codes')
    codes = result['native_warning_codes']
    result['CMI_warning_present'] = any(c.startswith('CMI') for c in codes) if codes is not None else None
    result['native_effective_settings'] = state['native'].get('effective_settings')
    result['analysis_peak_rss_bytes'] = None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*1024**2:
            raise ValueError('Analysis RSS exceeds256 MiB')
    if sum(os.path.getsize(os.path.join(output,n)) for n in os.listdir(output))+1024*1024>=32*1024**2:
        raise ValueError('Derived output cap exceeded')
    native.write_new(os.path.join(output,'result.json'),result)
    print('CONTROL_STANDARD_CELL_NATIVE_ANALYSIS_OK',result['native_points'],'acceptance remains unapproved')


if __name__ == '__main__':
    main()
