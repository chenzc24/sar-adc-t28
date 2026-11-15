"""Read-only native DFF windows, bound to a completed full-terminal source."""
import argparse
import csv
import json
import os
import subprocess


def crossings(rows, node, level, rising):
    result = []
    for left, right in zip(rows, rows[1:]):
        a, b = left[node], right[node]
        crossed = a < level <= b if rising else a > level >= b
        if crossed:
            result.append(left['time'] + (right['time']-left['time'])*(level-a)/(b-a))
    return result


def pulses(rows, values, level):
    intervals = []
    start = rows[0]['time'] if values[0] > level else None
    for i in range(1, len(rows)):
        a, b = values[i-1], values[i]
        if (a > level) != (b > level):
            t = rows[i-1]['time'] + (rows[i]['time']-rows[i-1]['time'])*(level-a)/(b-a)
            if b > level:
                start = t
            else:
                intervals.append([start, t]); start = None
    if start is not None:
        intervals.append([start, rows[-1]['time']])
    return dict(intervals_s=intervals, total_s=sum(b-a for a, b in intervals),
                clipped=values[0] > level or values[-1] > level)


def analyze(run_dir, output_dir, source):
    inputs = os.path.join(run_dir, 'inputs')
    with open(os.path.join(inputs, 'event_config.json')) as f:
        config = json.load(f)
    with open(os.path.join(source, 'inputs', 'soa_context.json')) as f:
        context = json.load(f)
    assert context['run_id'] == config['source_run_id']
    if not os.path.isdir(output_dir): os.makedirs(output_dir)
    scratch = os.path.join(run_dir, 'event_scratch')
    if not os.path.isdir(scratch): os.makedirs(scratch)
    binary = os.path.join(scratch, 'native_window')
    subprocess.check_call(['g++', '-std=c++11', '-O2', os.path.join(inputs, 'native_window.cpp'), '-o', binary])
    # Independent linear crossings and clipped-pulse checks before actual data.
    test = [{'time':float(t), 'v':v} for t,v in [(0,0), (1,2), (2,0)]]
    assert crossings(test, 'v', 1, True) == [.5]
    assert pulses(test, [0,2,0], 1)['intervals_s'] == [[.5,1.5]]
    assert pulses(test, [2,2,2], 1)['clipped']
    nodes = config['nodes']; windows = config['windows_s']
    layout = os.path.join(scratch, 'window.layout')
    with open(layout, 'w') as f:
        f.write('%d %d\n' % (len(nodes), len(windows)) + '\n'.join(nodes) + '\n')
        for a,b in windows: f.write('%.17g %.17g\n' % (a,b))
    output = os.path.join(output_dir, 'events.csv')
    receipt = json.loads(subprocess.check_output([binary, os.path.join(source,'raw','tran_short.tran.tran'), layout, output]).decode())
    assert abs(receipt['stop'] - context['expected_stop_s']) < 1e-14
    with open(output) as f:
        rows = [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    summaries = []
    role = config['roles']; supply = config['supply_v']
    for a,b in windows:
        data = [r for r in rows if a <= r['time'] <= b]; assert len(data) >= 2
        vds = [abs(r[role['drain']]-r[role['source']]) for r in data]
        peak_index = max(range(len(data)), key=lambda i:vds[i])
        edges = {}
        for name in ('cp','cdn','data','q','reset','gate','mq'):
            n = role[name]; edges[name] = {}
            for rising in (True,False):
                lower,upper = (.3,.7) if rising else (.7,.3)
                t0=crossings(data,n,lower*supply,rising);t1=crossings(data,n,upper*supply,rising)
                widths=[]
                # Preserve only paired, complete edges in the diagnostic window.
                for t in t0:
                    ends=[u for u in t1 if u>=t]
                    if ends and not any(t<u<ends[0] for u in t0):widths.append(ends[0]-t)
                edges[name]['rise' if rising else 'fall']=dict(half_times_s=crossings(data,n,.5*supply,rising),
                    intervals_30_70_s=widths,liberty_coordinate_s=[w/.5 for w in widths])
        summaries.append(dict(window_s=[a,b],samples=len(data),peak_abs_vds=vds[peak_index],
            peak_row=data[peak_index],over_1p1=pulses(data,vds,1.1),edges=edges,
            start_row=data[0],end_row=data[-1],extrema={n:dict(min=min(r[n] for r in data),max=max(r[n] for r in data)) for n in nodes}))
    result=dict(source_run_id=context['run_id'],corner=context['corner'],analysis_complete=True,
        extraction=receipt,roles=role,windows=summaries,
        scope='Selected native event windows only; full-run SOA remains source-bound to original terminal_results',
        slew_definition='30/70 interval; Liberty coordinate divides by recorded 0.5 derate; not complete library use qualification')
    with open(os.path.join(output_dir,'result.json'),'w') as f: json.dump(result,f,indent=2)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir',required=True)
    a=p.parse_args();analyze(a.run_dir,a.output_dir,a.source_run_dir)
