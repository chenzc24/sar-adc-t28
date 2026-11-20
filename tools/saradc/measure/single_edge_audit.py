"""Audit the decision-to-code mapping and pin timing of a completed single-edge transient."""
from __future__ import print_function
import argparse
import bisect
import json
import os

import native_stream
import reference_short as native
import register_constraints


def samples(path, ctx):
    """Waveform samples; post-layout decks save macro nets that context signal_aliases maps to schematic names."""
    alias = ctx.get('signal_aliases', {})
    for t, v in native_stream.samples(path):
        yield t, dict((alias.get(k, k), x) for k, x in v.items()) if alias else v


def word(v, prefix):
    return sum(1 << i for i in range(8) if v[prefix + str(i)] > .5*v['vdd!'])


def analyze(root, out, library, bottom_measure=None):
    with open(os.path.join(root, 'inputs/context.json')) as stream:
        ctx = json.load(stream)
    bottom_measure = bottom_measure or native.bottom
    raw = [os.path.join(p,n) for p,_,files in os.walk(root+'/raw')
           for n in files if n.endswith('.tran.tran')]
    if len(raw) != 1:
        raise ValueError('Expected one native transient')
    cp = 'xdut.phi_u'
    compare = 'xdut.cmp_clk'
    track = 'xdut.seq_sample'
    pins = [n for n in ctx['required_signals'] if n.endswith('.din')]
    buses = ['d%d' % i for i in range(8)]
    signals = pins + [cp, compare, track] + buses
    edges = {k: [[], [], []] for k in signals}
    frames = [dict(frame=i, bits=[], decisions=[], public_90=None, public_98=None,
                   register_pin_windows=[], preset_ready_lead_ns=None) for i in range(ctx['frames'])]
    previous = None
    ready_since = None
    for t,v in samples(raw[0], ctx):
        threshold = v['vdd!'] / 2
        ready = False
        if v['xdut.preset'] > threshold:
            b = bottom_measure(v,ctx['lsb_v'])
            if b and b['gate_words'] == [127,128]:
                err = (2*b['max_bottom_error_v']/ctx['lsb_v'] if ctx['mismatch'] else b['weighted_bound_lsb'])
                ready = err <= .25
        if not ready:
            ready_since = None
        elif ready_since is None:
            ready_since = t
        if previous is not None:
            pt,old = previous
            for net in signals:
                a,b = old[net]/old['vdd!'], v[net]/v['vdd!']
                if a == b or max(a,b)<.3 or min(a,b)>.7:
                    continue
                for j,lvl in enumerate((.3,.5,.7) if net in pins or net==cp else (.5,)):
                    if (a>lvl) == (b>lvl):
                        continue
                    pos = j if net in pins or net==cp else 1
                    frac = (lvl-a)/(b-a)
                    when = pt + frac*(t-pt)
                    rising = b>a
                    edges[net][pos].append((when,rising))
                    ix = int((when-ctx['frame_origin_s'])//ctx['period_s'])
                    if pos!=1 or not rising or ix<0 or ix>=len(frames):
                        continue
                    f=frames[ix]
                    if net == track:
                        f['preset_ready_lead_ns'] = max(0.,(when-ready_since)*1e9) if ready_since is not None else 0.
                    if net in (cp,compare):
                        at = {k:old[k]+frac*(v[k]-old[k]) for k in v}
                        if net == cp:
                            pr,nr = [at[k]>.5*at['vdd!'] for k in native.RX]
                            f['decisions'].append(int(pr) if pr!=nr else None)
                        else:
                            bot=bottom_measure(at,ctx['lsb_v'])
                            f['bits'].append(dict(code=word(at,'xdut.code'), gates=bot['gate_words'] if bot else None))
            ix = int((t-ctx['frame_origin_s'])//ctx['period_s'])
            for i in (ix-1,ix):
                if not 0<=i<len(frames):
                    continue
                base=ctx['frame_origin_s']+i*ctx['period_s']
                for ns,key in ((90,'public_90'),(98,'public_98')):
                    when=base+ns*1e-9
                    if pt<when<=t:
                        frac=(when-pt)/(t-pt)
                        at={k:old[k]+frac*(v[k]-old[k]) for k in buses+['vdd!']}
                        frames[i][key]=word(at,'d')
        previous=t,v
    def with_slew(net):
        low,mid,high=edges[net]
        result=[]
        for i,(t,up) in enumerate(mid):
            start,end=(low,high) if up else (high,low)
            l=bisect.bisect_right(start,(t,True))-1
            r=bisect.bisect_left(end,(t,False))
            slew=None
            if (l>=0 and r<len(end) and start[l][1]==up and end[r][1]==up
                and (i==0 or start[l][0]>mid[i-1][0])
                and (i+1==len(mid) or end[r][0]<mid[i+1][0])):
                slew=(end[r][0]-start[l][0])*1e12
            result.append((t,up,slew))
        return result
    pin_edges=[with_slew(p) for p in pins]
    clocks=with_slew(cp)
    for f in frames:
        base=ctx['frame_origin_s']+f['frame']*ctx['period_s']
        writes=[(t,s) for t,up,s in clocks if up and base<=t<base+ctx['period_s']]
        decided=0
        ok=len(writes)==len(f['decisions'])==len(f['bits'])==8
        if ok:
            for i,(b,decision) in enumerate(zip(f['bits'],f['decisions'])):
                mask=128>>i
                trial=decided|mask
                ok=ok and b['code']==trial and b['gates']==[255-trial,trial] and decision is not None
                if decision:decided|=mask
        f['decision_word']=decided if len(f['decisions'])==8 else None
        f['digital_pass']=bool(ok and decided==f['public_90']==f['public_98'])
        bus_times=[t for k in buses for t,_ in edges[k][1] if base<=t<=base+98e-9]
        f['public_margin_ns']=(90-(max([writes[-1][0]]+bus_times)-base)*1e9 if writes else None)
        for i,data in enumerate(pin_edges):
            times=[t for t,_,_ in data]
            for ix,(t,slew) in enumerate(writes):
                j=bisect.bisect_left(times,t)
                before=data[j-1] if j else (0.,None,None)
                after=data[j] if j<len(data) else (previous[0],None,None)
                # CDN is driven by the inverted tracking clock. Exclude any write during tracking.
                reset_edges=[edge for edge in edges[track][1] if edge[0]<=t]
                f['register_pin_windows'].append(dict(bit=i,write=ix,clock_ns=(t-base)*1e9,
                    cdn_high=bool(reset_edges and not reset_edges[-1][1]),clock_slew_ps=slew,
                    previous_data_rise=before[1],following_data_rise=after[1],
                    setup_ps=(t-before[0])*1e12,hold_ps=(after[0]-t)*1e12,
                    setup_slew_ps=before[2],hold_slew_ps=after[2]))
    result=dict(context=ctx,frames=frames)
    with open(library) as stream:
        tables=json.load(stream)
    result['ccs']=register_constraints.evaluate(result,tables)
    select_pins = [i for i,p in enumerate(pins) if p.startswith('xdut.xctrl.xsel')]
    if select_pins:
        selected=[dict(frame=f['frame'], register_pin_windows=[
            row for row in f['register_pin_windows'] if row['bit'] in select_pins]) for f in frames]
        result['selector_ccs']=register_constraints.evaluate(dict(context=ctx,frames=selected),tables)
    result['register_pins']=pins
    for f in frames:
        del f['register_pin_windows']
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--run-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--source-run-dir', required=True)
    a=ap.parse_args()
    with open(os.path.join(a.source_run_dir,'inputs/context.json')) as stream:
        groups=json.load(stream).get('cdac_plate_nodes')
    bottom_measure=None
    if groups:
        from single_edge_lpe import bottom_state
        bottom_measure=lambda v,lsb:bottom_state(v,groups,lsb)
    result = analyze(a.source_run_dir,a.output_dir,os.path.join(a.run_dir,'inputs/dff.json'),bottom_measure)
    with open(os.path.join(a.output_dir,'result.json'),'w') as stream:
        json.dump(result,stream,indent=2)
