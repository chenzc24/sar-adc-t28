"""Bounded native-waveform SOA analysis, Python 2/3, standard library only."""
from __future__ import print_function
import argparse
import bisect
import hashlib
import json
import math
import os
import subprocess
from native_stream import samples


def over_intervals(t0, t1, v0, v1, limit):
    """Exact above-|limit| pieces of a signed piecewise-linear segment."""
    cuts = [t0,t1]
    if v1 != v0:
        for level in (-limit,limit):
            fraction = (level-v0)/(v1-v0)
            if 0 < fraction < 1:cuts.append(t0+fraction*(t1-t0))
    cuts.sort()
    return [(a,b) for a,b in zip(cuts,cuts[1:])
            if abs(v0+(v1-v0)*((a+b)/2-t0)/(t1-t0)) > limit]


def sliding_max(intervals, window, stop):
    """Maximum accumulated duration over any sliding window, including edges."""
    if not intervals:return 0.,None
    starts = [i[0] for i in intervals]
    ends = [i[1] for i in intervals]
    prefix = [0.]
    for a,b in intervals:prefix.append(prefix[-1]+b-a)
    def integral(t):
        i = bisect.bisect_right(ends,t)
        return prefix[i]+(max(0.,t-starts[i]) if i<len(starts) else 0.)
    best,at = 0.,None
    for end in ends+[min(stop,a+window) for a in starts]+[stop]:
        value = integral(end)-integral(max(0.,end-window))
        if value>best:best,at=value,end
    return best,at


def fast_scan(pairs, raw, limit, tool_dir, output_dir):
    scratch=os.path.join(os.path.dirname(output_dir),'soa_scratch')
    if not os.path.isdir(scratch):os.makedirs(scratch)
    binary=os.path.join(scratch,'soa_scan')
    subprocess.check_call(['g++','-std=c++11','-O2',os.path.join(tool_dir,'soa_scan.cpp'),'-o',binary])
    # Independently compare the compiled segment scanner to the Python reference,
    # including startup, both polarities, exact threshold and repeated pulses.
    test_nodes=os.path.join(scratch,'selftest.layout')
    with open(test_nodes,'w') as f:f.write('2 1 %.17g\n0\nv\n1 0 1\n'%limit)
    test_wave=os.path.join(scratch,'selftest.psf')
    points=[(0.,1.2),(30e-12,1.2),(31e-12,0.),(70e-12,0.),(71e-12,-1.25),
            (160e-12,1.25),(161e-12,limit),(300e-12,limit),(310e-12,0.)]
    expected=[]
    for (t0,v0),(t1,v1) in zip(points,points[1:]):
        for a,b in over_intervals(t0,t1,v0,v1,limit):
            if expected and expected[-1][1]==a:expected[-1][1]=b
            else:expected.append([a,b])
    with open(test_wave,'w') as f:
        f.write('SWEEP\n"time" FLOAT\nTRACE\n"v" FLOAT\nVALUE\n')
        for t,v in points:f.write('"time" %.17g\n"v" %.17g\n'%(t,v))
        f.write('END\n')
    test_out=os.path.join(scratch,'selftest.json')
    subprocess.check_call([binary,test_wave,test_nodes,test_out])
    with open(test_out) as f:observed=json.load(f)['pairs'][0]
    assert observed['peak_abs_V']==1.25 and len(observed['intervals'])==len(expected)
    assert all(abs(a-b)<1e-23 for x,y in zip(observed['intervals'],expected) for a,b in zip(x,y))
    nodes=sorted(set(n for p in pairs for n in p['nodes'])|set(['0']))
    idx={n:i for i,n in enumerate(nodes)}
    layout=os.path.join(scratch,'layout.txt')
    with open(layout,'w') as f:
        f.write('%d %d %.17g\n'%(len(nodes),len(pairs),limit))
        f.write('\n'.join(nodes)+'\n')
        for p in pairs:f.write('%d %d %d\n'%(idx[p['nodes'][0]],idx[p['nodes'][1]],p['covered']))
    result=os.path.join(scratch,'scan.json')
    subprocess.check_call([binary,raw,layout,result])
    with open(result) as f:data=json.load(f)
    for p,r in zip(pairs,data['pairs']):p.update(r)
    return data['count'],data['stop'],data['max_dt']


def analyze(run_dir, output_dir, tool_dir=None):
    inputs = os.path.join(run_dir,'inputs')
    with open(os.path.join(inputs,'soa_context.json')) as f:ctx=json.load(f)
    rule = ctx['rule']
    with open(os.path.join(inputs,'terminal_inventory.json'),'rb') as f:inventory_bytes=f.read()
    topo=json.loads(inventory_bytes)
    thin = set(rule['scope']['thin_oxide_mos_models']+rule['scope']['thin_oxide_moscap_models'])
    thick = set(rule['scope']['thick_oxide_models_outside_this_rule'])
    unknown = sorted(set(d['model'] for d in topo['devices'])-thin-thick)
    if unknown:raise ValueError('Unclassified models: '+str(unknown))
    # Deduplicate physically identical terminal differences, preserving device attribution.
    pairs, index, rows = [],{},[]
    for d in topo['devices']:
        pins = dict(zip('pn' if len(d['nodes'])==2 else 'dgsb',[n.replace('\\','').lower() for n in d['nodes']]))
        for pair in (['pn'] if len(pins)==2 else ['gs','gd','ds','gb','bs','bd']):
            key = tuple(sorted((pins[pair[0]],pins[pair[1]])))
            covered = d['model'] in thin and pair in ('gs','gd','ds','pn')
            if key not in index:
                index[key] = len(pairs)
                pairs.append(dict(nodes=key,peak_abs_V=0.,peak_time_s=0.,covered=False,intervals=[]))
            i = index[key];pairs[i]['covered'] |= covered
            rows.append(dict(instance=d['instance'],model=d['model'],terminal_pair=pair,
                             pair_index=i,in_rule=covered))
    required = set(n for p in pairs for n in p['nodes'])-{'0'}
    limit = rule['limits']['continuous_V']
    raw = os.path.join(run_dir,'raw','tran_short.tran.tran')
    previous = None
    count,total_intervals,max_dt = 0,0,0.
    stop = None
    tool_dir=tool_dir or inputs
    fast=os.path.isfile(os.path.join(tool_dir,'soa_scan.cpp'))
    if fast:count,stop,max_dt=fast_scan(pairs,raw,limit,tool_dir,output_dir)
    for t,values in ([] if fast else samples(raw)):
        if not count:
            missing = required-set(values)
            if missing:raise ValueError('Missing terminal nodes: '+str(sorted(missing)))
            if t != 0.:raise ValueError('Startup not captured')
        values['0'] = 0.
        volts = [values[a]-values[b] for a,b in (p['nodes'] for p in pairs)]
        if any(math.isnan(x) or math.isinf(x) for x in volts):raise ValueError('Nonfinite terminal voltage')
        for i,(p,v) in enumerate(zip(pairs,volts)):
            if abs(v)>p['peak_abs_V']:p['peak_abs_V'],p['peak_time_s']=abs(v),t
            if previous and p['covered'] and (abs(v)>limit or abs(previous[1][i])>limit):
                for a,b in over_intervals(previous[0],t,previous[1][i],v,limit):
                    intervals = p['intervals']
                    if intervals and intervals[-1][1]==a:intervals[-1][1]=b
                    else:
                        intervals.append([a,b]);total_intervals+=1
                        if total_intervals>500000:raise ValueError('Interval memory budget reached; preserve partial evidence')
        if previous:max_dt=max(max_dt,t-previous[0])
        previous = t,volts
        count+=1;stop=t
        if count%10000==0:
            print(json.dumps(dict(points=count,time_s=t,intervals=total_intervals)))
            import sys
            sys.stdout.flush()
    if stop is None or abs(stop-ctx['expected_stop_s'])>1e-14:raise ValueError('Incomplete transient')
    violations=[]
    for p in pairs:
        intervals=p.pop('intervals')
        if p['covered']:
            duration,end=sliding_max(intervals,rule['limits']['window_s'],stop)
            p.update(max_sliding_over_s=duration,worst_window_end_s=end,
                     total_over_s=sum(b-a for a,b in intervals),over_pulse_count=len(intervals))
            p['numeric_pass']=p['peak_abs_V']<=rule['limits']['peak_V'] and duration<=rule['limits']['max_over_s']
    for r in rows:
        r.update(pairs[r.pop('pair_index')])
        r.pop('covered')
        if not r['in_rule']:
            for k in ('numeric_pass','max_sliding_over_s','worst_window_end_s','total_over_s','over_pulse_count'):r.pop(k,None)
            r['verdict']='outside_rule'
        else:
            r['verdict']='numeric_pass_pending_review' if r['numeric_pass'] else 'violation'
            if not r['numeric_pass']:violations.append(r)
    # Code observations are a consistency check, not a fresh timing qualification.
    import re
    codes=[]
    with open(os.path.join(run_dir,'spectre.out')) as f:
        for line in f:
            match=re.search(r'BPROBE,0,(\d+),(\d+)',line)
            if match:codes.append((int(match.group(1)),int(match.group(2))))
    code_pass = codes==list(enumerate(ctx['expected_codes']))
    result=dict(analysis_complete=True,run_id=ctx['run_id'],corner=ctx['corner'],
                source_run_id=ctx['source_run_id'],rule_id=rule['rule_id'],rule_sha256=ctx['rule_sha256'],
                inventory_sha256=hashlib.sha256(inventory_bytes).hexdigest(),
                reduction_backend='compiled_stream_with_reference_selftest' if fast else 'python_reference_stream',
                native_points=count,native_start_s=0.,native_end_s=stop,max_native_step_s=max_dt,
                device_count=len(topo['devices']),checked_device_count=sum(d['model'] in thin for d in topo['devices']),
                checked_pair_count=sum(r['in_rule'] for r in rows),violation_pair_count=len(violations),
                verdict='violation' if violations else 'numeric_pass_pending_resolution_review',
                observer_codes=codes,observer_codes_pass=code_pass,
                worst_peak=max((r for r in rows if r['in_rule']),key=lambda r:r['peak_abs_V']),
                worst_duration=max((r for r in rows if r['in_rule']),key=lambda r:r['max_sliding_over_s']),
                violations=violations,raw_waveform=raw,
                limitations=['Piecewise-linear native-waveform screen; temporal-resolution review required before pass.',
                             'Body pairs and thick-oxide devices are recorded but not qualified by this rule.',
                             ctx.get('extraction_scope','%d-frame stimulus coverage only; no MC/noise/PEX/supply ramp.' % len(ctx['expected_codes']))])
    if not os.path.isdir(output_dir):os.makedirs(output_dir)
    for name,obj in [('terminal_results.json',rows),('result.json',result)]:
        with open(os.path.join(output_dir,name),'w') as f:json.dump(obj,f,indent=2);f.write('\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--source-run-dir')
    args=p.parse_args();analyze(args.source_run_dir or args.run_dir,args.output_dir,os.path.join(args.run_dir,'inputs'))
