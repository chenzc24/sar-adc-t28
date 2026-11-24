"""Streaming independent measurements. Python 2.7/3; no complete waveform arrays."""
from __future__ import print_function
import argparse,bisect,glob,json,os,re
try:
    from .native_stream import samples
except (ImportError,ValueError):
    from native_stream import samples


def overlap_fraction(a0,a1,b0,b1):
    """Fraction where GN > half supply and GP < half supply, linear between saved points."""
    lo,hi=0.,1.
    for x0,x1,greater in [(a0,a1,True),(b0,b1,False)]:
        if x0==x1:
            if not ((x0>.45) if greater else (x0<.45)):return 0.
        else:
            cross=(.45-x0)/(x1-x0)
            after=(x1>x0)==greater
            if after:lo=max(lo,cross)
            else:hi=min(hi,cross)
    return max(0.,min(1.,hi)-max(0.,lo))


def analyze(context,trace,probes):
    modules=context['modules'];issues=[];diagnostics=[];metrics={};edges={};seen={};previous=None;max_step=0.
    requests=[]
    if 'sampler' in modules:requests += [99.9e-9,101.1e-9,155e-9,199.9e-9,201.1e-9,255e-9]
    if 'cdac' in modules:requests += [45e-9,59e-9]+[(79+20*i)*1e-9 for i in range(10)]+[(77+20*i)*1e-9 for i in range(10)]
    if 'comparator' in modules:requests += [14.5e-9,19e-9]+[(9+10*i)*1e-9 for i in range(10)]
    if 'reference' in modules:requests += [(70+80*i)*1e-9 for i in range(6)]
    if context.get('sar_stalled'):requests += [(80+100*i)*1e-9 for i in range(6)]
    requests=sorted(set(requests));index=0;overlap={};first_overlap=None
    kick_extrema=[];reference_rails={};gate_last_outside=[None]*6
    edge_names=['c_clock','c_outn','c_outp','t_clock']+['t_out'+str(i) for i in range(10)]+['xsar.cmp_clk','xsar.phi_u','xsar.comp_n','xsar.comp_p']
    if context.get('sar_stalled'):edge_names+=['xstalled.cmp_clk','xstalled.phi_u']
    gate_aliases=context.get('reference_gate_aliases',{})
    required=set(context['required_signals']) | set(gate_aliases)
    for t,values in trace():
        if gate_aliases:
            values=dict(values)
            values.update((alias,values[signal]) for alias,signal in gate_aliases.items())
        if 'comparator' in modules and 15.05e-9<=t<=20.05e-9:
            dv=values['k_p']-values['k_n'];cm=(values['k_p']+values['k_n'])/2
            if not kick_extrema:kick_extrema=[dv,dv,cm,cm]
            else:kick_extrema=[min(kick_extrema[0],dv),max(kick_extrema[1],dv),min(kick_extrema[2],cm),max(kick_extrema[3],cm)]
        if 'cdac' in modules:
            for pin in ['d_rn','d_rp']:
                v=values[pin];old=reference_rails.get(pin,[v,v]);reference_rails[pin]=[min(old[0],v),max(old[1],v)]
        if 'reference' in modules:
            frame=int((t-50.05e-9)/80e-9)
            if 0<=frame<6 and (50.05+80*frame)*1e-9<=t<(70+80*frame)*1e-9:
                word=context['reference_words'][frame]
                if any(abs(values['r_'+g+str(k)]-.9*((1-((word>>k)&1)) if g in ['gnn','gnp'] else ((word>>k)&1)))>.09
                       for g in ['gnn','gnp','gpn','gpp'] for k in range(8)):
                    gate_last_outside[frame]=t-(50.05+80*frame)*1e-9
        if previous is None:
            missing=required-set(values)
            if missing:raise ValueError('Missing required saved traces: '+','.join(sorted(missing)))
        else:
            pt,pv=previous;dt=t-pt;max_step=max(max_step,dt)
            while index<len(requests) and requests[index]<=t:
                when=requests[index]
                if when>=pt:
                    f=(when-pt)/dt
                    seen[when]={key:pv[key]+f*(values[key]-pv[key]) for key in required}
                index+=1
            for name in edge_names:
                if name not in required:continue
                a=pv[name]-.45;b=values[name]-.45
                if (a<0<=b) or (a>0>=b):
                    when=pt+dt*(-a)/(b-a)
                    edges.setdefault(name,[]).append((when,1 if b>a else -1))
                    if len(edges[name])>2000:raise ValueError('Unexpected unbounded event count')
            if 'reference' in modules:
                for side,n,p in [('n','gnn','gnp'),('p','gpn','gpp')]:
                    for bit in range(8):
                        gn='r_'+n+str(bit);gp='r_'+p+str(bit)
                        width=dt*overlap_fraction(pv[gn],values[gn],pv[gp],values[gp])
                        if width>0:
                            key=side+str(bit);overlap[key]=overlap.get(key,0.)+width
                            if first_overlap is None:first_overlap=dict(time_s=pt,side=side,bit=bit)
        previous=(t,values)
    if index<len(requests):raise ValueError('Waveform ended before required probe times')
    def at(t,node):return seen[t][node]
    def crossing(name,direction,start,end):return [t for t,d in edges.get(name,[]) if d==direction and start<=t<end]
    if 'sampler' in modules:
        first=at(101.1e-9,'b_hold')-.2;normal=at(201.1e-9,'b_hold')-.8
        row=dict(startup_error_v=first,normal_error_v=normal,
                 first_hold_droop_v=at(155e-9,'b_hold')-at(101.1e-9,'b_hold'),
                 normal_hold_droop_v=at(255e-9,'b_hold')-at(201.1e-9,'b_hold'))
        row['hold_droop_v']=max(abs(row['first_hold_droop_v']),abs(row['normal_hold_droop_v']))
        limit=context['contracts']['sampler']['limits']['sample_error_v']
        if max(abs(first),abs(normal))>limit:issues.append(dict(module='sampler',issue='sample_error',metrics=row))
        metrics['sampler']=row
    if 'comparator' in modules:
        rows=[]
        for i,vd in enumerate(context['comparator_inputs_v']):
            start=(5.05+10*i)*1e-9;end=(10.05+10*i)*1e-9
            n=crossing('c_outn',-1,start,end);p=crossing('c_outp',-1,start,end)
            decided=bool(n or p);positive=(bool(n) and (not p or n[0]<p[0]))
            at_time=(9+10*i)*1e-9
            losing=at(at_time,'c_outp' if vd>0 else 'c_outn')
            delay=min((n+p) or [end])-start if decided else None
            reset=[]
            for pin in ['c_outn','c_outp']:
                reset.extend(crossing(pin,1,end,(15+10*i)*1e-9))
            row=dict(input_v=vd,decided=decided,positive=positive if decided else None,delay_s=delay,
                     reset_s=max(reset)-end if reset else 0.,losing_output_v=losing)
            rows.append(row)
            if abs(vd)>=.003515625 and (not decided or positive!=(vd>0)):
                issues.append(dict(module='comparator',issue='wrong_large_signal_decision',cycle=i,measurement=row))
            elif not decided or positive!=(vd>0):diagnostics.append(dict(module='comparator',issue='small_input_offset_or_no_response',cycle=i,measurement=row))
            if delay is not None and delay>context['contracts']['comparator']['limits']['diagnostic_speed_s']:
                diagnostics.append(dict(module='comparator',issue='speed_screen',cycle=i,delay_s=delay))
        before=at(14.5e-9,'k_p')-at(14.5e-9,'k_n');after=at(19e-9,'k_p')-at(19e-9,'k_n')
        cm_before=(at(14.5e-9,'k_p')+at(14.5e-9,'k_n'))/2
        metrics['comparator']=dict(decisions=rows,decision_delay_s=[r['delay_s'] for r in rows],reset_s=[r['reset_s'] for r in rows],
                                  wrong_decisions_above_half_lsb=sum((not r['decided'] or r['positive']!=(r['input_v']>0)) for r in rows if abs(r['input_v'])>=.003515625),
                                  differential_kickback_v=after-before,kickback_initial_v=before,
                                  differential_kickback_peak_abs_v=max(abs(kick_extrema[0]-before),abs(kick_extrema[1]-before)) if kick_extrema else None,
                                  common_mode_kickback_peak_abs_v=max(abs(kick_extrema[2]-cm_before),abs(kick_extrema[3]-cm_before)) if kick_extrema else None)
    if 'cdac' in modules:
        def diff(t):return at(t,'d_n')-at(t,'d_p')
        base=diff(59e-9);plateaus=[diff((79+20*i)*1e-9) for i in range(10)]
        settle=[None]*10;stable=[abs(plateaus[i]-diff((77+20*i)*1e-9))<.0017578125 for i in range(10)]
        band=context['contracts']['cdac']['limits']['settle_band_v']
        for t,v in trace():
            i=int((t-60e-9)/20e-9)
            if 0<=i<10 and (60+20*i)*1e-9<=t<(79+20*i)*1e-9:
                if abs((v['d_n']-v['d_p'])-plateaus[i])>band:settle[i]=t-(60+20*i)*1e-9
        weights=[x-base for x in plateaus[:8]]
        if not all(x>0 for x in weights):issues.append(dict(module='cdac',issue='wrong_step_polarity',weights_v=weights))
        if not all(stable):diagnostics.append(dict(module='cdac',issue='finite_dwell_target_not_stable',stable=stable))
        metrics['cdac']=dict(effective_weights_v=weights,settle_to_quarter_lsb_s=settle,finite_dwell_stable=stable,
                             baseline_hold_droop_v=base-diff(45e-9),plateau_differential_v=plateaus,
                             hold_droop_v=base-diff(45e-9),reference_min_max_v=reference_rails,
                             settling_scope='Time since ideal gate command, relative to a stable 19 ns finite-dwell target; not an infinite-hold oracle')
    if 'reference' in modules:
        errors=[]
        for i,word in enumerate(context['reference_words']):
            values=seen[(70+80*i)*1e-9]
            for bit in range(8):
                b=(word>>bit)&1
                for group,want in [('gnn',1-b),('gnp',1-b),('gpn',b),('gpp',b)]:
                    got=values['r_'+group+str(bit)]>.45
                    if got!=bool(want):errors.append(dict(frame=i,bit=bit,pin=group,voltage_v=values['r_'+group+str(bit)],expected=want))
        if errors:issues.append(dict(module='reference',issue='stored_word',first=errors[0],count=len(errors)))
        if overlap:diagnostics.append(dict(module='reference',issue='logic_threshold_overlap',first=first_overlap,total_by_side_bit_s=overlap))
        metrics['reference']=dict(stored_word_errors=len(errors),first_word_error=errors[0] if errors else None,
                                  logic_overlap_duration_s=sum(overlap.values()),overlap_by_side_bit_s=overlap,first_overlap=first_overlap,
                                  gate_settle_s=gate_last_outside,gate_settle_band_v=.09,
                                  scope='Actual CDAC gate load; gate settling to 10 percent of the rail after update; half-supply overlap proxy, not MOS-current conduction')
    if 'sar' in modules:
        rows=[]
        for j,want in enumerate(context['expected_codes']):
            start=(100.05+j*100)*1e-9;end=start+60e-9
            cmp=crossing('xsar.cmp_clk',1,start,end);update=crossing('xsar.phi_u',1,start,end)
            got=probes.get((901,j));elapsed=update[-1]-start if update else None
            row=dict(frame=j,startup=j==0,expected=want,code=got,comparisons=len(cmp),updates=len(update),conversion_s=elapsed)
            rows.append(row)
            if got!=want or len(cmp)!=8 or len(update)!=8:
                issues.append(dict(module='sar',issue='code_or_handshake',first_uncompleted_bit=max(0,7-len(update)),measurement=row))
        metrics['sar']=rows
        if context.get('sar_stalled'):
            stalled=[]
            for j in range(6):
                start=(100.05+j*100)*1e-9;end=start+60e-9
                cm=crossing('xstalled.cmp_clk',1,start,end);up=crossing('xstalled.phi_u',1,start,end)
                reset=seen[(80+100*j)*1e-9]
                cleared=reset['xstalled.cmp_clk']<.45 and all(reset['f_d'+str(k)]<.45 for k in range(8))
                row=dict(frame=j,comparisons=len(cm),updates=len(up),blocked_bit=7,cleared_during_acquisition=cleared)
                stalled.append(row)
                if len(cm)!=1 or up or not cleared:issues.append(dict(module='sar',issue='stalled_reset_or_false_update',measurement=row))
            metrics['sar_stalled']=stalled
    return dict(analysis_complete=True,pass_validation=not issues and not diagnostics,pass_functional=not issues,diagnostic_screens_pass=not diagnostics,failures=issues,diagnostics=diagnostics,
                metrics=metrics,max_saved_step_s=max_step,context=context,
                scope='Independent TT module measurements. Diagnostic screens are separate from electrical signoff. Unallocated limits, native noise, MC/PVT, power and terminal reliability remain open.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--source-run-dir')
    args=p.parse_args();base=args.source_run_dir or args.run_dir;context=json.load(open(base+'/inputs/context.json'))
    raw=glob.glob(base+'/raw/*.tran')
    if len(raw)!=1:raise ValueError('Expected one complete native transient file')
    probes={};warnings=set()
    for line in open(base+'/spectre.out'):
        warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
        m=re.search(r'BPROBE,(\d+),(\d+),(\d+)',line)
        if m:probes[(int(m.group(1)),int(m.group(2)))]=int(m.group(3))
    result=analyze(context,lambda:samples(raw[0]),probes);result['warning_codes']=sorted(warnings)
    if not os.path.isdir(args.output_dir):os.makedirs(args.output_dir)
    with open(args.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2);f.write('\n')
    print('BLOCK_CHARACTERIZATION_COMPLETE',result['pass_validation'],len(result['failures']),len(result['diagnostics']))


if __name__=='__main__':main()
