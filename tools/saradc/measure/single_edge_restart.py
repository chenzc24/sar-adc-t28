"""Check a valid early sample and the two conversions following it on native pins."""
from __future__ import print_function
import argparse
import json
import math
import os

import native_stream


def analyze(root, out):
    with open(root+'/inputs/context.json') as stream:
        ctx=json.load(stream)
    raw=[os.path.join(p,n) for p,_,files in os.walk(root+'/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw)!=1:
        raise ValueError('Expected one native transient')
    names=['xdut.seq_sample','xdut.cmp_clk','xdut.phi_u','xdut.preset','xdut.active']
    signals=dict((k,[]) for k in names)
    reads={}
    plan=dict(ctx.get('restart_plan',dict(openings=[60,105,205],stop_ns=304,reads=[[195,85],[295,170]])))
    if 'independent_cdac_gain' in ctx:
        # An extracted CDAC reads the gain-adjusted code, as in the integrated code check.
        gain=ctx['independent_cdac_gain']
        plan['reads']=[[start,max(0,min(255,128+int(math.floor((code+.5-128)/gain))))] for start,code in plan['reads']]
    read_ns=[ns for start,_ in plan['reads'] for ns in (start,start+8)]
    public_stable=True
    prev=None
    for t,v in native_stream.samples(raw[0]):
        if prev is not None:
            pt,pv=prev
            for k in names:
                a,b=pv[k]-.5*pv['vdd!'],v[k]-.5*v['vdd!']
                if (a>0)!=(b>0):
                    signals[k].append(((pt-a*(t-pt)/(b-a))*1e9,b>a))
            for ns in read_ns:
                if pt<ns*1e-9<=t:
                    frac=(ns*1e-9-pt)/(t-pt)
                    n=['d%d'%i for i in range(8)]+['vdd!']
                    at={k:pv[k]+frac*(v[k]-pv[k]) for k in n}
                    reads[str(ns)]=sum(1<<i for i in range(8) if at['d%d'%i]>.5*at['vdd!'])
        ns=t*1e9
        for start,expected in plan['reads']:
            if start<=ns<=start+8:
                public_stable=public_stable and all((v['d%d'%i]>.5*v['vdd!'])==bool(expected & (1<<i)) for i in range(8))
        prev=t,v
    if prev is None or prev[0]<ctx['expected_stop_s']-1e-12:
        raise ValueError('Incomplete restart waveform')
    openings=[t for t,up in signals[names[0]] if up]
    closings=[t for t,up in signals[names[0]] if not up]
    if len(openings)!=3 or len(closings)!=3 or any(abs(t-target)>2 for t,target in zip(openings,plan['openings'])):
        raise ValueError('Unexpected tracking windows')
    def rises(name,begin,end):
        return [t for t,up in signals[name] if up and begin<t<end]
    counts=[len(rises('xdut.phi_u',lo,hi)) for lo,hi in zip(closings,openings[1:]+[plan['stop_ns']])]
    compare=[len(rises('xdut.cmp_clk',lo,hi)) for lo,hi in zip(closings,openings[1:]+[plan['stop_ns']])]
    prior_active=next((up for t,up in reversed(signals['xdut.active']) if t<openings[1]), None)
    # ACTIVE may be high from DC with no crossing before this opening.
    protected=all(not rises(k,a,b) for a,b in zip(openings,closings) for k in ('xdut.cmp_clk','xdut.phi_u'))
    passed=(0<counts[0]<8 and prior_active is not False and counts[1:]==compare[1:]==[8,8] and protected
            and public_stable and reads=={str(ns):code for start,code in plan['reads'] for ns in (start,start+8)}
            and all(len(rises('xdut.preset',a,b))==1 for a,b in zip(closings[1:],[start for start,_ in plan['reads']])))
    result=dict(run_id=ctx['run_id'],pass_restart=passed,writes=counts,comparisons=compare,
                track_open_ns=openings,track_close_ns=closings,public_read_codes=reads,stable=public_stable,
                no_new_compare_or_write_during_track=protected,events=signals)
    with open(out+'/result.json','w') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir',required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir',required=True)
    a=p.parse_args()
    analyze(a.source_run_dir or a.run_dir,a.output_dir)
