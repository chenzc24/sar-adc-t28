"""Score the two physical delay polarities and all 510 CDAC terminals at compare."""
from __future__ import print_function
import argparse
import json
import math
import os
import re

import native_stream


def bottom_state(v, groups, lsb):
    words, total, maximum = [], 0., 0.
    for side in ('n', 'p'):
        gates = 0
        for bit, ports in enumerate(groups[side]):
            gn, gp = [v['xdut.g%s%s%d' % (side, gate, bit)] > .5*v['vdd!'] for gate in ('n', 'p')]
            if gn != gp:
                return None
            gates |= int(gn) << bit
            target = v['vrefn' if gn else 'vrefp']
            errors = [abs(v[port] - target) for port in ports]
            if any(math.isinf(x) or math.isnan(x) for x in errors):
                raise ValueError('Nonfinite physical capacitor voltage')
            total += sum(errors)
            maximum = max(maximum, max(errors))
        words.append(gates)
    if sum(words) != 255:
        return None
    return dict(gate_words=words, weighted_bound_lsb=total/(256*lsb), max_port_error_v=maximum)


def word(v, prefix):
    return sum(1 << b for b in range(8) if v[prefix+str(b)] > .5*v['vdd!'])


def selector_handoff(frame):
    """Check the actual T-high/T-low overlap across the entire Q transition."""
    edges = frame['selector_edges']
    bits, writes = frame['bits'], frame['writes']
    result = dict(passed=False)
    if len(bits) != 8 or len(writes) != 8 or len(frame['track']) != 2:
        return result
    close = frame['track'][1]['ns']
    def window(key, start, end):
        return [(t, up) for t, up in edges[key] if start < t <= end]
    select = []
    for key in ('q10', 'q50', 'q90'):
        changes = window(key, close, 98.)
        if len(changes) != 1 or not changes[0][1]:
            return result
        select.append(changes[0][0])
    q10, q50, q90 = select
    result.update(commit5_ns=writes[2]['ns'], q10_ns=q10, q50_ns=q50, q90_ns=q90)
    rail_windows = []
    for key in ('high90', 'low90'):
        before = [e for e in edges[key] if e[0] <= q10]
        after = [e for e in edges[key] if e[0] > q10]
        if not before or not after or not before[-1][1] or after[0][1]:
            return result
        rail_windows.append((before[-1][0], after[0][0]))
    result['both_high_before_q10_ps'] = (q10-max(a for a,b in rail_windows))*1000.
    result['both_high_after_q90_ps'] = (min(b for a,b in rail_windows)-q90)*1000.
    bit3 = dict((key, window(key,writes[3]['ns'],writes[4]['ns']))
                for key in ('launch','delivery'))
    result['bit3'] = bit3
    result['passed'] = bool(
        writes[2]['ns'] < q10 <= q50 <= q90 < bits[3]['cmp_ns']
        and result['both_high_before_q10_ps'] > 0 and result['both_high_after_q90_ps'] > 0
        and all(b['low_q'] == (b['bit'] <= 4) for b in bits)
        and all(w['trial5'] == (j == 2) for j,w in enumerate(writes))
        and all(len(window(k,close,writes[-1]['ns'])) == 8 for k in ('launch','delivery'))
        and all(len(v) == 1 and v[0][1] for v in bit3.values()))
    return result


def analyze(root, out):
    with open(root+'/inputs/context.json') as stream:
        ctx=json.load(stream)
    raw=[os.path.join(p,n) for p,_,files in os.walk(root+'/raw') for n in files if n.endswith('.tran.tran')]
    if len(raw)!=1:
        raise ValueError('Expected one native transient')
    origin,period=ctx['frame_origin_s'],ctx['period_s']
    groups=ctx['cdac_plate_nodes']
    for side in ('n','p'):
        if [len(g) for g in groups[side]] != [1<<i for i in range(8)]:
            raise ValueError('Unexpected number of physical terminals per bit')
    frames=[dict(frame=i,input_code=c,bits=[],writes=[],track=[],preset=[],public=[],track_overlaps=[],code90=None,code98=None)
            for i,c in enumerate(ctx['expected_codes'])]
    cmpnet,wr,track='xdut.cmp_clk','xdut.phi_u','xdut.seq_sample'
    launch,delivery=['xdut.xctrl.xtim.'+s for s in ('phase_request','delivered')]
    bus=['d%d'%i for i in range(8)]
    watch=[cmpnet,wr,track,launch,delivery,'xdut.preset']+bus
    selector = ctx.get('selector_probes')
    thresholds = []
    if selector:
        thresholds = [('q10',selector['q'],.1),('q50',selector['q'],.5),('q90',selector['q'],.9),
                      ('high90',selector['high'],.9),('low90',selector['low'],.9)]
        for f in frames:
            f['selector_edges'] = {k:[] for k in ('q10','q50','q90','high90','low90','launch','delivery')}
    fine = ctx.get('fine_window_frame_ns')
    max_fine_step_ps = 0.
    fine_intervals = 0
    fine_trace = []
    phases={launch:[],delivery:[]}
    last_write,last_reset=None,None
    write_widths,compare_low=[],[]
    prev=None
    points=0
    for t,v in native_stream.samples(raw[0]):
        points+=1
        if prev is None:
            missing=set(ctx['required_signals'])-set(v)
            if missing:
                raise ValueError('Missing physical probe(s): '+repr(sorted(missing)[:10]))
            prev=t,v
            continue
        pt,pv=prev
        if fine:
            base = origin+(len(frames)-1)*period
            frame_ns = (t-base)*1e9
            if fine[0] <= frame_ns <= fine[1]:
                fine_trace.append([frame_ns] + [v[k]/v['vdd!'] for k in
                    (wr,selector['q'],selector['low'],selector['high'],launch,delivery,cmpnet)])
            if pt >= base+fine[0]*1e-9 and t <= base+fine[1]*1e-9:
                max_fine_step_ps = max(max_fine_step_ps,(t-pt)*1e12)
                fine_intervals += 1
        for key,net,level in thresholds:
            a,b = pv[net]-level*pv['vdd!'],v[net]-level*v['vdd!']
            if (a>0) != (b>0):
                when = pt-a/(b-a)*(t-pt)
                i = int(math.floor((when-origin)/period))
                if 0 <= i < len(frames):
                    frames[i]['selector_edges'][key].append(((when-origin-i*period)*1e9,b>a))
        def at(frac):
            return {k:pv[k]+frac*(v[k]-pv[k]) for k in v}
        edges=[]
        for net in watch:
            a,b=pv[net]-.5*pv['vdd!'],v[net]-.5*v['vdd!']
            if (a>0)!=(b>0):
                frac=-a/(b-a)
                edges.append((pt+frac*(t-pt),net,b>a,frac))
        for when,net,up,frac in sorted(edges):
            if net==wr:
                if up:last_write=when
                elif last_write is not None:write_widths.append((when-last_write)*1e12)
            if net==cmpnet:
                if not up:last_reset=when
                elif last_reset is not None:compare_low.append((when-last_reset)*1e12)
            if net in phases:
                phases[net].append((when,up))
                i=int(math.floor((when-origin)/period))
                if selector and 0<=i<len(frames):
                    key = 'launch' if net==launch else 'delivery'
                    frames[i]['selector_edges'][key].append(((when-origin-i*period)*1e9,up))
                continue
            i=int(math.floor((when-origin)/period))
            if not 0<=i<len(frames):continue
            f=frames[i]
            tm=(when-origin-i*period)*1e9
            if net in bus:
                f['public'].append(tm)
            elif net==track:
                sample=at(frac)
                if up and any(sample[n]>.5*sample['vdd!'] for n in (cmpnet,wr)):
                    f['track_overlaps'].append(dict(ns=tm,event='high at opening'))
                residual=(sample['xdut.topp']-sample['xdut.topn']-sample['vinp_src']+sample['vinn_src'])/ctx['lsb_v']
                f['track'].append(dict(ns=tm,up=up,close_error_lsb=None if up else residual,
                    preset_bottom=bottom_state(sample,groups,ctx['lsb_v']) if up else None,
                    preset_asserted=sample['xdut.preset']>.5*sample['vdd!']))
            elif net=='xdut.preset' and up:
                f['preset'].append(tm)
            elif net==wr and up:
                sample=at(frac)
                if sample[track]>.5*sample['vdd!']:
                    f['track_overlaps'].append(dict(ns=tm,event='write during track'))
                pr,nr=[sample['xdut.xctrl.xtim.'+x]>.5*sample['vdd!'] for x in ('pr','nr')]
                f['writes'].append(dict(ns=tm,decision=int(pr) if pr!=nr else None))
                if selector:
                    f['writes'][-1]['trial5'] = sample['xdut.xctrl.trial5'] > .5*sample['vdd!']
            elif net==cmpnet and up:
                sample=at(frac)
                if sample[track]>.5*sample['vdd!']:
                    f['track_overlaps'].append(dict(ns=tm,event='compare during track'))
                j=len(f['bits'])
                base=origin+i*period
                prior=f['writes'][-1]['ns'] if f['writes'] else next((x['ns'] for x in reversed(f['track']) if not x['up']),None)
                timing={}
                for key,ph in [('launch',launch),('delivery',delivery)]:
                    timestamps=[(s,r) for s,r in phases[ph] if prior is not None and base+prior*1e-9<s<=when]
                    timing[key]=[dict(ns=(s-base)*1e9,rise=r) for s,r in timestamps]
                f['bits'].append(dict(bit=7-j,group='high' if j<3 else 'low',cmp_ns=tm,
                    trial=word(sample,'xdut.code'),top_diff_v=sample['xdut.topp']-sample['xdut.topn'],
                    bottom=bottom_state(sample,groups,ctx['lsb_v']),phase=timing))
                if selector:
                    f['bits'][-1]['low_q'] = sample[selector['q']] > .5*sample['vdd!']
        i=int(math.floor((t-origin)/period))
        for j in (i-1,i):
            if 0<=j<len(frames):
                base=origin+j*period
                for ns,key in ((90,'code90'),(98,'code98')):
                    at_time=base+ns*1e-9
                    if pt<at_time<=t:frames[j][key]=word(at((at_time-pt)/(t-pt)),'d')
        prev=t,v
    if prev is None or prev[0]<ctx['expected_stop_s']-1e-12:
        raise ValueError('Incomplete transient')
    obs={}
    warnings=set()
    with open(root+'/spectre.out') as stream:
        for line in stream:
            m=re.search(r'BPROBE,0,(\d+),(\d+)',line)
            if m:
                if int(m.group(1)) in obs: raise ValueError('Duplicate observer frame')
                obs[int(m.group(1))]=int(m.group(2))
            warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
    for f in frames:
        bits,writes=f['bits'],f['writes']
        ordered=len(bits)==len(writes)==8
        decided=0
        for j,(b,w) in enumerate(zip(bits,writes)):
            if j>=8:
                ordered=False
                break
            trial=decided|(128>>j)
            ph=b['phase']
            valid=(len(ph['launch'])==len(ph['delivery'])==1 and
                   ph['launch'][0]['rise']==ph['delivery'][0]['rise']==(j%2==0) and
                   ph['launch'][0]['ns']<ph['delivery'][0]['ns']<b['cmp_ns'])
            b['phase_pass']=valid
            b['decision']=w['decision']
            b['trial_pass']=bool(b['bottom'] and b['bottom']['gate_words']==[255-trial,trial] and b['trial']==trial)
            if j: ordered=ordered and writes[j-1]['ns']<b['cmp_ns']
            ordered=ordered and b['cmp_ns']<w['ns'] and b['trial_pass'] and valid and w['decision'] is not None
            if w['decision']:decided|=128>>j
        coord=ctx.get('input_code_coordinates',ctx['expected_codes'])[f['frame']]
        f['input_code_coordinate']=coord
        ideal=max(0,min(255,128+int(math.floor((coord+.5-128)/ctx['independent_cdac_gain']))))
        f['gain_expected']=ideal
        f['digital_pass']=bool(ordered and f['code90']==f['code98']==obs.get(f['frame'])==decided)
        directed_center = ctx.get('kind') in ('boundary','reversal') and f['frame']>=2
        tolerance=0 if directed_center else 1
        f['analog_code_pass']=f['code90'] is not None and abs(f['code90']-ideal)<=tolerance
        f['decision_word']=decided if len(writes)==8 else None
        f['settling_pass']=len(bits)==8 and all(b['bottom'] and b['bottom']['weighted_bound_lsb']<=.25 for b in bits)
        f['margin_ns']=90-max([writes[-1]['ns']]+[s for s in f['public'] if s<=98]) if len(writes)==8 else None
        f['routing_fraction']=None
        if f['margin_ns'] is not None and len(f['track'])==2:
            f['routing_fraction']=f['margin_ns']/(90-f['track'][1]['ns'])
        f['track_pass']=bool(len(f['track'])==2 and [x['up'] for x in f['track']]==[True,False] and
            f['track'][0]['preset_asserted'] and f['track'][0]['preset_bottom'] and f['track'][0]['preset_bottom']['gate_words']==[127,128] and
            f['track'][0]['preset_bottom']['weighted_bound_lsb']<=.25 and abs(f['track'][1]['close_error_lsb'])<=.25)
        f['control_pass']=bool(not f['track_overlaps'] and len(f['track'])==2 and len(bits)==len(writes)==8 and f['track'][1]['ns']<bits[0]['cmp_ns']
                              and len(f['preset'])==1 and writes[-1]['ns']<f['preset'][0])
        f['pass']=bool(f['digital_pass'] and f['analog_code_pass'] and f['settling_pass'] and f['control_pass'] and
                       f['track_pass'] and f['margin_ns']>0)
        if selector:
            f['handoff'] = selector_handoff(f)
            f['pass'] = f['pass'] and f['handoff']['passed']
    margins=[f['margin_ns'] for f in frames if f['margin_ns'] is not None]
    floor_ok=len(margins)==len(frames) and min(margins)>=3
    target_ok=len(margins)==len(frames) and min(margins)>=5
    result=dict(run_id=ctx['run_id'],cell_lpe=ctx['cell_lpe'],taps=[ctx['tap_high'],ctx['tap_low']],
        cdac_gds=ctx['cdac_physical_gds_sha256'],native_points=points,ports=510,frames=frames,
        routing_floor_3ns_pass=floor_ok,routing_target_5ns_pass=target_ok,
        all_pass=all(f['pass'] for f in frames) and (ctx['corner']!='ssc' or floor_ok),warnings=sorted(warnings))
    if fine:
        f=frames[-1]
        covered=(len(f['bits'])==len(f['writes'])==8 and fine[0]<f['writes'][2]['ns']
                 and f['writes'][4]['ns']<fine[1] and fine_trace
                 and fine_trace[0][0]<=fine[0]+.001 and fine_trace[-1][0]>=fine[1]-.001)
        result['fine_grid'] = dict(frame_ns=fine, intervals=fine_intervals, max_step_ps=max_fine_step_ps,
                                   passed=bool(covered and fine_intervals and max_fine_step_ps<.51))
        result['all_pass'] = result['all_pass'] and result['fine_grid']['passed']
        with open(os.path.join(out,'selector_trace.csv'),'w') as trace:
            trace.write('frame_ns,commit,low_q,t_low,t_high,phase_request,delivered,cmp_clk\n')
            for row in fine_trace:
                trace.write(','.join('%.9g'%s for s in row)+'\n')
    if 'min_cp_high_ps' in ctx:
        import single_edge_audit as audit
        checked=audit.analyze(root,out,os.path.join(root,'inputs/dff.json'),
                              bottom_measure=lambda v,lsb:bottom_state(v,groups,lsb))
        ccs=checked['ccs']
        counts=ccs['observation_counts']
        pin_count = 11 if selector else 10
        pin_pass=(counts['writes']==len(frames)*8*pin_count and not counts.get('inactive_or_unknown_cdn') and
                  bool(write_widths) and min(write_widths)>=ctx['min_cp_high_ps'] and
                  all(ccs['minimum_slack'].get(k,{}).get('slack_ps',-1)>=0 for k in ('setup','hold')))
        result.update(ccs=ccs,pin_pass=pin_pass,min_write_high_ps=min(write_widths) if write_widths else None,
                      min_compare_low_ps=min(compare_low) if compare_low else None,
                      min_cp_high_reference_ps=ctx['min_cp_high_ps'],all_pass=result['all_pass'] and pin_pass)
        if 'selector_ccs' in checked:
            result['selector_ccs'] = checked['selector_ccs']
    with open(out+'/result.json','w') as stream:
        json.dump(result,stream,indent=2)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir',required=True)
    p.add_argument('--source-run-dir')
    p.add_argument('--output-dir',required=True)
    args=p.parse_args()
    analyze(args.source_run_dir or args.run_dir,args.output_dir)
