"""Stream Issue #2 native comparisons without assuming a reference capture clock.

Works under the remote Python 2.7 runtime. Only compact frame/event data are kept.
Terminal and switch-port current diagnostics are separate from functional verdicts.
"""
from __future__ import print_function
import argparse
import csv
import json
import math
import os
import re
from native_stream import samples

EVENTS = {'sample':'sample', 'sample_int':'xdut.sample_int', 'close':'xdut.seq_sample',
          'cmp':'xdut.cmp_clk', 'write':'xdut.xctrl.phi_w', 'update':'xdut.phi_u',
          'preset':'xdut.preset'}
RX = ['xdut.xctrl.xtim.pr','xdut.xctrl.xtim.nr']


def code(v):
    return sum(1 << i for i in range(8) if v['d%d'%i] > .5*v['vdd!'])


def bottom(v, lsb):
    total=0.;worst=0.;state=[]
    for side in ['n','p']:
        word=0
        for bit in range(8):
            gn=v['xdut.g%sn%d'%(side,bit)] > .5*v['vdd!']
            gp=v['xdut.g%sp%d'%(side,bit)] > .5*v['vdd!']
            if gn != gp:return None
            word |= (1 << bit) if gn else 0
            rail=v['vrefn' if gn else 'vrefp']
            err=abs(v['xdut.xcdac.b%s%d'%(side,bit)]-rail)
            total += (1 << bit)*err/256
            worst=max(worst,err)
        state.append(word)
    if state[0] != 255-state[1]:return None
    return dict(weighted_bound_lsb=total/lsb,max_bottom_error_v=worst,gate_words=state)


def frame_new(i):
    return dict(frame=i,events=[],bits=[],code_90=None,code_98=None,observer_code=None,
                sample_close_error_lsb=None,output_stable=True,output_reference=None,
                reference_max_droop_v=0.,reference_current_peak_a=0.,
                switch_port_overlap_peak_a=0.,switch_port_overlap_integral_c=0.,
                gate_min_v=None,gate_max_v=None,issues=[])


def finish(f,ctx):
    def times(name,rise=True):return [e['time_s'] for e in f['events'] if e['signal']==name and e['rising']==rise]
    cr,wr,up=times('cmp'),times('write'),times('update')
    closes,opens=times('sample',False),times('sample',True)
    f['expected_code']=ctx['expected_codes'][f['frame']]
    f['counts']={'compare':len(cr),'write':len(wr),'update':len(up)}
    f['code_pass']=f['code_98']==f['expected_code']
    f['observer_crosscheck']=f['observer_code'] is not None and f['observer_code']==f['code_98']
    f['event_order_pass']=(len(cr)==len(wr)==len(up)==8 and
        all(cr[i]<wr[i]<up[i] for i in range(8)) and all(up[i]<cr[i+1] for i in range(7)))
    f['sample_edges_pass']=(len(closes)==len(opens)==len(times('close',False))==len(times('sample_int',False))==1)
    deadline=ctx['frame_origin_s']+(f['frame']+1)*ctx['period_s']+1.05e-9
    f['conversion_ns']=(up[-1]-closes[0])*1e9 if up and len(closes)==1 else None
    f['deadline_margin_ns']=(deadline-up[-1])*1e9 if up else None
    f['timing_pass']=bool(f['event_order_pass'] and f['sample_edges_pass'] and f['output_stable'] and up[-1]<ctx['frame_origin_s']+f['frame']*ctx['period_s']+90e-9)
    for bit in f['bits']:
        bit['bottom_screen_pass']=bit['bottom'] is not None and bit['bottom']['weighted_bound_lsb']<=ctx['settling_band_lsb']
        if not bit['bottom_screen_pass']:f['issues'].append(dict(bit=bit['bit'],reason='bottom_settling_screen'))
        if not bit.get('receiver_valid_at_write',False):f['issues'].append(dict(bit=bit['bit'],reason='receiver_not_valid_at_write'))
    if not f['code_pass']:f['issues'].append(dict(bit=None,reason='center_code'))
    if not f['timing_pass']:f['issues'].append(dict(bit=None,reason='handshake_or_deadline'))
    if not f['observer_crosscheck']:f['issues'].append(dict(bit=None,reason='native_observer_disagreement'))
    if f['sample_close_error_lsb'] is None or abs(f['sample_close_error_lsb'])>.25:
        f['issues'].append(dict(bit=7,reason='sample_close_residual_screen'))
    f['pass_function_timing']=bool(f['code_pass'] and f['timing_pass'] and f['observer_crosscheck'] and
                                  len(f['bits'])==8 and all(b.get('receiver_valid_at_write',False) for b in f['bits']))
    return f


def analyze(run_dir,output_dir,frame_finisher=None):
    ctx=json.load(open(os.path.join(run_dir,'inputs/context.json')))
    frames=[frame_new(i) for i in range(ctx['frames'])]
    obs={};warnings=set();warning_lines=[]
    with open(os.path.join(run_dir,'spectre.out')) as f:
        for line in f:
            m=re.search(r'BPROBE,0,(\d+),(\d+)',line)
            if m:
                idx=int(m.group(1))
                if idx in obs:raise ValueError('Duplicate observer frame')
                obs[idx]=int(m.group(2))
            warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
            if 'WARNING (' in line:warning_lines.append(line.strip())
    paths=[os.path.join(p,n) for p,_,names in os.walk(os.path.join(run_dir,'raw')) for n in names if n.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Expected exactly one native transient')
    prev=None;last_update=None;last_bad=None;rx_since=None;points=0;current_missing=None
    last_plot=-1.;precharge=None
    with open(os.path.join(output_dir,'timeline.csv'),'w') as out:
        writer=csv.writer(out);writer.writerow(['time_s','input_diff_v','top_diff_v','code','sample','cmp','preset','vrefp','vrefn'])
        for t,v in samples(paths[0]):
            missing=[s for s in ctx['required_signals'] if s not in v]
            if missing:raise ValueError('Missing native voltage signals: '+str(missing))
            if any(math.isnan(v[s]) or math.isinf(v[s]) for s in ctx['required_signals']):raise ValueError('Nonfinite waveform')
            if current_missing is None:current_missing=[s for s in ctx['current_signals'] if s not in v]
            points+=1
            if t<ctx['frame_origin_s']:
                precharge=dict(time_s=t,bootp_charge_v=v['xdut.xbootp.btop']-v['xdut.xbootp.bbot'],bootn_charge_v=v['xdut.xbootn.btop']-v['xdut.xbootn.bbot'])
            idx=int(math.floor((t-ctx['frame_origin_s'])/ctx['period_s']))
            f=frames[idx] if 0<=idx<len(frames) else None
            b=bottom(v,ctx['lsb_v'])
            if b is None or b['weighted_bound_lsb']>ctx['settling_band_lsb']:last_bad=t
            if f:
                base=ctx['frame_origin_s']+idx*ctx['period_s']
                if base+90e-9<=t<=base+98e-9:
                    if f['output_reference'] is None:f['output_reference']=code(v)
                    if code(v)!=f['output_reference']:f['output_stable']=False
                f['reference_max_droop_v']=max(f['reference_max_droop_v'],abs(.9-v['vrefp']),abs(v['vrefn']))
                f['reference_current_peak_a']=max(f['reference_current_peak_a'],abs(.9-v['vrefp'])/50,abs(v['vrefn'])/50)
                gates=[v['xdut.g%s%s%d'%(s,p,i)] for s in ['n','p'] for p in ['n','p'] for i in range(8)]
                f['gate_min_v']=min(gates+[f['gate_min_v']]) if f['gate_min_v'] is not None else min(gates)
                f['gate_max_v']=max(gates+[f['gate_max_v']]) if f['gate_max_v'] is not None else max(gates)
                overlap=0.
                if not current_missing:
                    for side in ['n','p']:
                        for bit in range(8):
                            prefix='xdut.xcdac.xs%s%d.'%(side,bit)
                            overlap+=min(max(0.,v[prefix+'mn_low:1']),max(0.,-v[prefix+'mp_high:1']))
                    f['switch_port_overlap_peak_a']=max(f['switch_port_overlap_peak_a'],overlap)
                    if prev:f['switch_port_overlap_integral_c']+=overlap*(t-prev[0])
            if prev:
                pt,old=prev
                transitions=[]
                for name,node in list(EVENTS.items())+[(k,k) for k in RX]:
                    a=old[node]-.5*old['vdd!'];z=v[node]-.5*v['vdd!']
                    if (a>0)!=(z>0):
                        cross=pt-a/(z-a)*(t-pt);transitions.append((cross,name,z>0))
                states=[old[k]>.5*old['vdd!'] for k in RX]
                for cross,name,rise in sorted(transitions):
                    if name in RX:
                        states[RX.index(name)]=rise
                        rx_since=cross if states[0]!=states[1] else None
                        continue
                    j=int(math.floor((cross-ctx['frame_origin_s'])/ctx['period_s']))
                    if not 0<=j<len(frames):continue
                    target=frames[j];target['events'].append(dict(signal=name,time_s=cross,rising=rise))
                    frac=(cross-pt)/(t-pt)
                    at={key:old[key]+frac*(v[key]-old[key]) for key in v}
                    if name=='close' and not rise:
                        target['sample_close_error_lsb']=(at['xdut.topp']-at['xdut.topn']-at['vinp_src']+at['vinn_src'])/ctx['lsb_v']
                        last_update=cross
                    if name=='update' and rise:last_update=cross
                    if name=='cmp' and rise:
                        target['bits'].append(dict(bit=7-len(target['bits']),compare_s=cross,top_diff_v=at['xdut.topp']-at['xdut.topn'],
                            bottom=bottom(at,ctx['lsb_v']),available_since_update_ns=(cross-last_update)*1e9 if last_update is not None else None,
                            bottom_stable_margin_ns=(cross-max(last_bad or cross,last_update or cross))*1e9))
                    if name=='write' and rise and target['bits']:
                        target['bits'][-1].update(write_s=cross,receiver_valid_at_write=states[0]!=states[1] and rx_since is not None and rx_since>target['bits'][-1]['compare_s'],
                                                receiver_margin_ps=(cross-rx_since)*1e12 if rx_since is not None else None)
                for j in range(max(0,idx-1),min(len(frames),idx+1)):
                    base=ctx['frame_origin_s']+j*ctx['period_s']
                    for offset,key in [(90e-9,'code_90'),(98e-9,'code_98')]:
                        if pt<base+offset<=t:frames[j][key]=code(v)
            if t-last_plot>=.5e-9:
                writer.writerow([t,v['vinp_src']-v['vinn_src'],v['xdut.topp']-v['xdut.topn'],code(v),v['sample'],v['xdut.cmp_clk'],v['xdut.preset'],v['vrefp'],v['vrefn']]);last_plot=t
            prev=t,v
    if prev is None or t<ctx['expected_stop_s']-1e-14:raise ValueError('Incomplete transient')
    if sorted(obs)!=list(range(ctx['frames'])):raise ValueError('Missing observer frames')
    for f in frames:f['observer_code']=obs[f['frame']]
    frames=[(frame_finisher or finish)(f,ctx) for f in frames]
    result=dict(context=ctx,analysis_complete=True,native_end_s=t,native_points=points,precharge=precharge,frames=frames,
                all_code_pass=all(f['code_pass'] for f in frames),pass_function_timing=all(f['pass_function_timing'] for f in frames),
                all_screens_pass=all(not f['issues'] for f in frames),first_issue=next((dict(frame=f['frame'],**f['issues'][0]) for f in frames if f['issues']),None),
                warning_codes=sorted(warnings),warning_lines=warning_lines,current_signals_missing=current_missing,
                electrical_verdict='record_only_not_qualified',settling_scope='Nominal positive binary weight bottom-plate bound relative to actual reference rails; does not establish floating-top kickback accuracy.',
                current_scope='Sum of simultaneous opposing switch terminal currents, includes displacement; not pure channel shoot-through or a converged power integral.',
                limitations=['No MC/noise/PEX or supply ramp','No independent extended-hold top target in this first short test','Core stress warnings retained in original spectre.out'])
    with open(os.path.join(output_dir,'result.json'),'w') as f:json.dump(result,f,indent=2);f.write('\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);parser.add_argument('--output-dir',required=True)
    parser.add_argument('--source-run-dir')
    args=parser.parse_args();analyze(args.source_run_dir or args.run_dir,args.output_dir)
