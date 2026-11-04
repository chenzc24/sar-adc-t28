"""Stream native cold waveforms. Distinguish protocol deadlines from analog diagnostics."""
from __future__ import print_function
import argparse
import hashlib
import json
import math
import os
import re
from native_stream import samples

CLOCK='xdut.cmp_clk'
WRITE='xdut.xctrl.phi_w'
UPDATE='xdut.phi_u'
RESET='xdut.seq_sample'
RX=['xdut.xctrl.xtim.pr','xdut.xctrl.xtim.nr']
BITS=['d%d'%i for i in range(8)]
BAD='first_issue'
def findone(root,suffix):
    paths=[os.path.join(p,n) for p,_,names in os.walk(root) for n in names if n.endswith(suffix)]
    assert len(paths)==1,(suffix,paths)
    return paths[0]

def scope_check(raw):
    p=findone(raw,'mismatch.params')
    v=findone(raw,'mismatch.values')
    with open(p) as labels,open(v) as values:
        cols=next(labels).split()
        assert next(values).strip()=='#1'
        rows={}
        for name in labels:
            name=name.strip().upper()
            if not name:continue
            vals=[float(x) for x in next(values).split()]
            assert len(vals)==len(cols) and all(not (math.isinf(x) or math.isnan(x)) for x in vals)
            rows[name]=vals
        assert not any(line.strip() for line in values)
    outsiders=[n for n in rows if not n.startswith(('XDUT.XCDAC.','XDUT.XCOMP.')) and any(rows[n])]
    moms=[n for n in rows if n.startswith('XDUT.XCDAC.CMOM')]
    ins=[n for n in rows if n in ('XDUT.XCOMP.MNINN','XDUT.XCOMP.MNINP')]
    return dict(valid=not outsiders and len(moms)==18 and len(ins)==2 and rows[ins[0]]!=rows[ins[1]],non_target_nonzero=outsiders[:10],mom_count=len(moms),input_count=len(ins),values_sha256=hashlib.sha256(open(v,'rb').read()).hexdigest())

def bottom(v,vdd):
    # Independent final rail selected by the actual complementary switch gates.
    result={}
    for side in 'pn':
        errors=[]
        for b in range(8):
            gn=v['xdut.g%sn%d'%(side,b)]>vdd/2
            gp=v['xdut.g%sp%d'%(side,b)]>vdd/2
            if gn!=gp:return None
            target=v['vrefn' if gn else 'vrefp']
            errors.append(v['xdut.xcdac.b%s%d'%(side,b)]-target)
        result[side]=errors
    return result

def analyze_frame(frame, events, cmp_rows, rx_write, status, codes, ctx):
    rows=[]
    issue=None
    def add(i,msg):
        return dict(frame=frame,bit=7-i,reason=msg)
    for i in range(8):
        if i>=len(cmp_rows):
            issue=issue or add(i,'missing_compare');break
        r=dict(cmp_rows[i],bit=7-i)
        start=r['cmp_s']
        stop=cmp_rows[i+1]['cmp_s'] if i+1<len(cmp_rows) else ctx['frame_origin_s']+(frame+1)*1e-7
        w=[x for x in rx_write if start<x['t']<stop]
        u=[t for t in events[UPDATE] if start<t<stop]
        if len(w)!=1 or len(u)!=1 or w[0]['t']>=u[0]:
            issue=issue or add(i,'write_or_update_missing_or_out_of_order')
        else:
            r.update(write_s=w[0]['t'],update_s=u[0],receiver_valid=w[0]['valid'])
            valid_since=w[0]['valid_since']
            if not w[0]['valid'] or valid_since is None or not start<valid_since<w[0]['t']:
                issue=issue or add(i,'receiver_not_resolved_before_capture')
            else:r['rx_margin_ps']=(w[0]['t']-valid_since)*1e12
            falls=[t for t in events['fall'] if start<t<stop]
            if len(falls)!=1:issue=issue or add(i,'reset_edge_missing_before_next_compare')
            elif i<7:r['reset_to_next_ps']=(stop-falls[0])*1e12
            if u[0]>ctx['frame_origin_s']+frame*1e-7+90e-9:
                issue=issue or add(i,'conversion_deadline')
        if r['bottom_plate_bound_lsb'] is None:issue=issue or add(i,'unresolved_reference_switch_state')
        elif r['bottom_plate_bound_lsb']>0.25:issue=issue or add(i,'CDAC_rail_settling_screen')
        rows.append(r)
    if len(cmp_rows)>8:issue=issue or dict(frame=frame,bit=None,reason='extra_compare')
    counts=[len(cmp_rows),len(rx_write),len(events[UPDATE]),len(events['cap'])]
    if counts!=status[2:6] or codes!=status[1] or not status[7]:
        issue=issue or dict(frame=frame,bit=None,reason='native_observer_or_frame_protocol')
    return dict(frame=frame,code=codes,expected_nominal_code=ctx['expected_codes'][frame],counts=counts,bits=rows,first_issue=issue)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    ctx=json.load(open(a.run_dir+'/inputs/context.json'))
    raw=a.run_dir+'/raw'
    rng=scope_check(raw)
    obs=[];warnings=set()
    for line in open(a.run_dir+'/spectre.out'):
        m=re.search(r'R4MEAS,([^\r\n]+)',line)
        if m:obs.append([int(float(x)) for x in m.group(1).split(',')[:8]])
        warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
    assert len(obs)==10 and [x[0] for x in obs]==list(range(10))
    half=ctx['vdd']/2
    origin=ctx['frame_origin_s']
    frames=[dict(events={UPDATE:[],'cap':[],'fall':[]},comp=[],writes=[],code=None) for _ in range(10)]
    prev=None;rx_since=None
    cap='xdut.xref.cap_clk'
    for t,v in samples(findone(raw,'.tran.tran')):
        if prev is not None:
            pt,old=prev
            transitions=[]
            for key in [CLOCK,WRITE,UPDATE,cap]+RX:
                if (old[key]>half)!=(v[key]>half):
                    x=pt+(half-old[key])*(t-pt)/(v[key]-old[key])
                    transitions.append((x,key,v[key]>half))
            states=[old[key]>half for key in RX]
            for x,k,rise in sorted(transitions):
                idx=int(math.floor((x-origin)/1e-7))
                f=frames[idx] if 0<=idx<10 else None
                if k in RX:
                    states[RX.index(k)]=rise
                    rx_since=x if states[0]!=states[1] else None
                elif f is not None:
                    if k==CLOCK and rise:
                        frac=(x-pt)/(t-pt)
                        at={key:old[key]+frac*(v[key]-old[key]) for key in v}
                        err=bottom(at,ctx['vdd'])
                        bound=sum(max(map(abs,z)) for z in err.values())/ctx['LSB'] if err else None
                        f['comp'].append(dict(cmp_s=x,top_diff_v=at['xdut.topp']-at['xdut.topn'],bottom_plate_bound_lsb=bound))
                    if k==CLOCK and not rise:f['events']['fall'].append(x)
                    if k==WRITE and rise:f['writes'].append(dict(t=x,valid=states[0]!=states[1],valid_since=rx_since))
                    if k in (cap,UPDATE) and rise:f['events'][('cap' if k==cap else k)].append(x)
            idx=int(math.floor((t-origin)/1e-7))
            if 0<=idx<10 and pt<origin+idx*1e-7+98e-9<=t:
                frames[idx]['code']=sum((1<<i) for i,k in enumerate(BITS) if v[k]>half)
        prev=t,v
    assert t>=ctx['expected_stop_s']-1e-14
    results=[analyze_frame(i,f['events'],f['comp'],f['writes'],obs[i],f['code'],ctx) for i,f in enumerate(frames)]
    r=dict(context=ctx,frames=results,sampling=rng,warning_codes=sorted(warnings),analysis_complete=True,native_data_valid=True,measurement_valid=rng['valid'],first_issue=next((f[BAD] for f in results if f[BAD]),None),cdac_scope='Independent actual rail versus every physical bottom plate at compare, conservative bound for normalized positive capacitor weights. Does not bound floating-top kickback or substitute for independent held-word top target.')
    with open(a.output_dir+'/result.json','w') as out:json.dump(r,out,indent=2)
if __name__=='__main__':
    main()
