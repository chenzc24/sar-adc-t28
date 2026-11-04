"""Native-point streaming CDAC measurements. Electrical failures are results, not parser failures."""
from __future__ import print_function
import argparse, gzip, itertools, json, math, os, re
from reduce import frames, norm


def interpolate(old, new, at):
    f=(at-old[0])/(new[0]-old[0])
    return {k:old[1][k]+f*(new[1][k]-old[1][k]) for k in old[1]}


def signature(v):
    result=[]
    for side in ['p','n']:
        for b in range(1,8):
            ctl=('dn' if side=='p' else 'dp') if b==7 else 'd'+side
            result.append(int(v['xadc.'+ctl+'_'+str(b)]>=.45))
    return tuple(result)


def target(sig, held, ref):
    t=[]
    for side in range(2):
        y=held[side]
        for b in range(1,8):
            initial=0 if b==7 else 1
            y+=ref*(2**(b-1))/128.0*((1-sig[side*7+b-1])-initial)
        t.append(y)
    return t


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--source-run-dir',required=True)
    a=p.parse_args();src=a.source_run_dir;cfg=json.load(open(src+'/inputs/measure.json'));criteria=cfg['criteria']
    state=json.load(open(src+'/simulation.state.json'))
    if state['status']!='complete' or not state.get('native',{}).get('zero_error_footer'):
        raise ValueError('Native simulation incomplete')
    paths=[src+'/raw/'+f for f in os.listdir(src+'/raw') if f.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('Expected one native transient')
    names=[norm(s) for s in cfg['signals']]
    control_keys=[]
    for side in ['p','n']:
        for b in range(1,8):
            ctl=('dn' if side=='p' else 'dp') if b==7 else 'd'+side
            control_keys.append('xadc.'+ctl+'_'+str(b))
    # First streaming pass finds 1% departure, independent of top-plate error.
    onsets={};edge_starts=[];last=None;tracking=False;command=None
    for tx,vx in frames(paths[0]):
        if last:
            tp,vp=last
            for key in ['xadc.dcmpp','xadc.dcmpn']:
                if vp[key]<.45<=vx[key]:
                    valid=tp+(tx-tp)*(.45-vp[key])/(vx[key]-vp[key])
                    command=valid+150e-12 # frozen SAR t_capture + t_update

            for i,k in enumerate(control_keys):
                level=.009 if vx[k]>vp[k] else .891
                if (vp[k]<=level<vx[k]) or (vx[k]<level<=vp[k]):
                    onsets[i]=tp+(tx-tp)*(level-vp[k])/(vx[k]-vp[k])
            if vp['clks']>=.45>vx['clks']:tracking=True
            if vp['clks']<.45<=vx['clks']:tracking=False
            if tracking:
                so=signature(vp);sn=signature(vx)
                changed=[i for i in range(14) if so[i]!=sn[i]]
                if changed:
                    if command is None or not 0<=tx-command<100e-12:raise ValueError('Missing native valid/update command')
                    edge_starts.append(command)
        last=(tx,vx)
    edge_index=0
    zoom=gzip.open(a.output_dir+'/reset_native.csv.gz','wb')
    zoom.write(('time,'+','.join(names)+'\n').encode('ascii'))
    pairs=[]
    for dev in cfg['devices']:
        terms=[norm(x) for x in dev['terminals']]
        for i,j in itertools.combinations(range(4),2):
            pairs.append({'device':dev['path'],'pair':'DGSB'[i]+'DGSB'[j],
                          'nodes':[terms[i],terms[j]],'peak_V':0.,'time_s':0.,'duration_over_s':0.,'last':0.})
    energy={k:0. for k in ['refp_net_J','refn_net_J','body_net_J','gate_net_J','gate_positive_J','input_net_J']}
    peak_current={};node_extrema={};comparisons=[];captures=[];segments=[];frames_out=[];completions=[]
    prev=None;previous_power=None;active=None;seg=None;held=None;sig=None;n=0;last_export=-1.;faultmax=0.
    capture_targets=[(111e-9+i*100e-9,c) for i,c in enumerate(cfg['codes'])]
    hold_targets=[];hold_samples=[]
    f=gzip.open(a.output_dir+'/wave.csv.gz','wb')
    columns=names+['ideal_topp','ideal_topn','dm_error','cm_error']
    f.write(('time,'+','.join(columns)+'\n').encode('ascii'))
    def finish_segment(s,end):
        if s is None:return
        s['end_s']=end
        history=[(tx,e) for tx,e in s.pop('history') if tx<end]
        if not history:raise ValueError('Empty settling interval')
        s['max_abs_error_after_budget_V']=max([e for tx,e in history if tx>=s['start_s']+criteria['settling_budget_s']] or [float('inf')])
        s['last_outside_s']=None
        olderr=0.
        for tx,e in history:
            if e>criteria['step_dm_limit_V'] or olderr>criteria['step_dm_limit_V']:s['last_outside_s']=tx
            olderr=e
        s['last_error_abs_V']=history[-1][1]
        s['settled_by_2ns']=s['max_abs_error_after_budget_V']<=criteria['step_dm_limit_V'] and end>=s['start_s']+criteria['settling_budget_s']
        # Last observed exit from the band; conservative by one native step.
        s['settling_time_upper_s']=max(0.,s['last_outside_s']-s['start_s']) if s['last_outside_s'] is not None else 0.
        if s['last_error_abs_V']>criteria['step_dm_limit_V']:s['settling_time_upper_s']=None
        segments.append(s)
    for t,v in frames(paths[0]):
        v['0']=0.;n+=1
        if 109.98e-9<=t<=110.10e-9:
            zoom.write((','.join(['%.15g'%t]+['%.15g'%v[k] for k in names])+'\n').encode('ascii'))
        if n==1 and set(names)-set(v):raise ValueError('Missing signals '+str(set(names)-set(v)))
        now=(t,v);dt=t-prev[0] if prev else 0
        faultmax=max(faultmax,v['fault'])
        for s in pairs:
            q=abs(v[s['nodes'][0]]-v[s['nodes'][1]])
            if q>s['peak_V']:s.update(peak_V=q,time_s=t)
            lim=criteria['terminal_limit_V'];old=s['last']
            if prev:
                if old>lim and q>lim:s['duration_over_s']+=dt
                elif (old>lim)!=(q>lim):
                    cut=dt*(lim-old)/(q-old)
                    s['duration_over_s']+=(dt-cut if q>lim else cut)
            s['last']=q
        for key in ['xadc.topp','xadc.topn']+[norm(q) for ns in cfg['bottom_nodes'].values() for q in ns]:
            if key not in node_extrema:node_extrema[key]={'min_V':v[key],'max_V':v[key],'min_s':t,'max_s':t}
            e=node_extrema[key]
            if v[key]<e['min_V']:e.update(min_V=v[key],min_s=t)
            if v[key]>e['max_V']:e.update(max_V=v[key],max_s=t)
        for key in ['vrefp:1','vrefn:1','vvdd:1']:
            if key not in peak_current or abs(v[key])>peak_current[key]['abs_A']:
                peak_current[key]={'abs_A':abs(v[key]),'signed_A':v[key],'time_s':t}
        gp=[v[norm(g['gate'])]*v[norm(g['current'])] for g in cfg['gate_currents']]
        power={'refp_net_J':-v['refp']*v['vrefp:1'],'refn_net_J':-v['refn']*v['vrefn:1'],
               'body_net_J':-v['vdd']*v['vvdd:1'],'gate_net_J':sum(gp),'gate_positive_J':sum(max(0,x) for x in gp),
               'input_net_J':-v['vinp']*v['vinp:1']-v['vinn']*v['vinn:1']}
        if previous_power:
            for key in energy:energy[key]+=.5*(power[key]+previous_power[key])*dt
        previous_power=power
        if prev and prev[1]['clks']>=.45>v['clks']:
            close=prev[0]+dt*(.45-prev[1]['clks'])/(v['clks']-prev[1]['clks'])
            at=interpolate(prev,now,close);held=[at['vinp'],at['vinn']];sig=signature(v)
            active={'index':len(frames_out),'close_s':close,'held_input_V':held,'code_expected':cfg['codes'][len(frames_out)]}
            frames_out.append(active)
            hold_targets += [(close+.5e-9,active['index'],0),(close+3.5e-9,active['index'],1)]
        if prev and prev[1]['clks']<.45<=v['clks'] and active is not None:
            up=prev[0]+dt*(.45-prev[1]['clks'])/(v['clks']-prev[1]['clks'])
            finish_segment(seg,up);seg=None;active=None;held=None;sig=None
        if active is not None:
            new_sig=signature(v)
            if new_sig!=sig:
                finish_segment(seg,edge_starts[edge_index]);edge_index+=1
                # A changed bottom gate is the physical control threshold event.
                changed=[i for i in range(14) if new_sig[i]!=sig[i]]
                times=[]
                for idx in changed:
                    side='p' if idx<7 else 'n';b=idx%7+1
                    ctl=('dn' if side=='p' else 'dp') if b==7 else 'd'+side
                    key='xadc.'+ctl+'_'+str(b)
                    times.append(prev[0]+dt*(.45-prev[1][key])/(v[key]-prev[1][key]))
                start=min(times);sig=new_sig
                seg={'frame':active['index'],'start_s':start,'changed_positions':changed,
                     'max_abs_error_after_budget_V':0.,'last_outside_s':None,'last_error_abs_V':0.,'history':[]}
            ideal=target(sig,held,cfg['vref_V'])
            err=(v['xadc.topp']-v['xadc.topn'])-(ideal[0]-ideal[1]);cmerr=.5*(v['xadc.topp']+v['xadc.topn']-sum(ideal))
            if seg:
                seg['history'].append((t,abs(err)))
                if abs(err)>criteria['step_dm_limit_V']:seg['last_outside_s']=t
                elif seg['last_error_abs_V']>criteria['step_dm_limit_V']:seg['last_outside_s']=t
                seg['last_error_abs_V']=abs(err)
                if t>=seg['start_s']+criteria['settling_budget_s']:
                    seg['max_abs_error_after_budget_V']=max(seg['max_abs_error_after_budget_V'],abs(err))
            if prev and prev[1]['xadc.cmpck']<.45<=v['xadc.cmpck']:
                when=prev[0]+dt*(.45-prev[1]['xadc.cmpck'])/(v['xadc.cmpck']-prev[1]['xadc.cmpck'])
                at=interpolate(prev,now,when)
                row={'frame':active['index'],'time_s':when,'ideal_topp_V':ideal[0],'ideal_topn_V':ideal[1],
                     'topp_V':at['xadc.topp'],'topn_V':at['xadc.topn']}
                row['dm_error_V']=row['topp_V']-row['topn_V']-ideal[0]+ideal[1]
                row['cm_error_V']=.5*(row['topp_V']+row['topn_V']-sum(ideal));comparisons.append(row)
            if prev and prev[1]['eoc']<.45<=v['eoc']:
                completions.append({'frame':active['index'],'time_s':t,'after_close_s':t-active['close_s']})
        else:
            ideal=[v['vinp'],v['vinn']];err=(v['xadc.topp']-v['xadc.topn'])-(ideal[0]-ideal[1]);cmerr=.5*(v['xadc.topp']+v['xadc.topn']-sum(ideal))
        while hold_targets and t>=hold_targets[0][0]:
            at,idx,pos=hold_targets.pop(0);q=interpolate(prev,now,at)
            hold_samples.append({'frame':idx,'position':pos,'time_s':at,'dm_V':q['xadc.topp']-q['xadc.topn']})
        while capture_targets and t>=capture_targets[0][0]:
            at,expected=capture_targets.pop(0);q=interpolate(prev,now,at)
            actual=sum(1<<i for i in range(8) if q['do_'+str(i)]>.45)
            captures.append({'time_s':at,'expected':expected,'actual':actual})
        if t-last_export>=20e-12 or prev is None:
            row=[v[k] for k in names]+ideal+[err,cmerr]
            f.write((','.join(['%.12g'%t]+['%.12g'%q for q in row])+'\n').encode('ascii'));last_export=t
        prev=now
    f.close();zoom.close();finish_segment(seg,t)
    if edge_index!=len(edge_starts):raise ValueError('Control event count mismatch')
    if abs(t-cfg['stop_s'])>1e-14:raise ValueError('Unexpected stop')
    for s in pairs:s.pop('last')
    drifts=[]
    for idx in range(8):
        vals=[s['dm_V'] for s in hold_samples if s['frame']==idx]
        if len(vals)!=2:raise ValueError('Missing hold samples')
        drifts.append({'frame':idx,'drift_V':vals[1]-vals[0]})
    counts=[sum(q['frame']==idx for q in comparisons) for idx in range(8)]
    checks={'codes':len(captures)==8 and all(c['expected']==c['actual'] for c in captures),
            'eight_comparisons':counts==[8]*8,'seven_updates':len(segments)==56 and all(sum(s['frame']==i for s in segments)==7 for i in range(8)),
            'no_fault':faultmax<.45,'conversion_time':len(completions)==8 and all(c['after_close_s']<=criteria['conversion_budget_s'] for c in completions),
            'comparison_dm_error':len(comparisons)==64 and all(abs(c['dm_error_V'])<=criteria['step_dm_limit_V'] for c in comparisons),
            'comparison_cm_error':len(comparisons)==64 and all(abs(c['cm_error_V'])<=criteria['compare_cm_limit_V'] for c in comparisons),
            'settling_2ns':len(segments)==56 and all(s['settled_by_2ns'] for s in segments),
            'held_drift':all(abs(d['drift_V'])<=criteria['held_drift_limit_V'] for d in drifts),
            'terminal_voltage':all(s['peak_V']<=criteria['terminal_limit_V'] for s in pairs)}
    log=open(src+'/spectre.out').read();cmi=sorted(set(re.findall(r'CMI-\d+',log)))
    checks['no_native_CMI']=not cmi
    summary={'max_compare_dm_error_V':max(abs(c['dm_error_V']) for c in comparisons),
             'max_compare_cm_error_V':max(abs(c['cm_error_V']) for c in comparisons),
             'max_held_drift_V':max(abs(d['drift_V']) for d in drifts),
             'max_terminal_V':max(s['peak_V'] for s in pairs),
             'max_conversion_s':max(c['after_close_s'] for c in completions) if completions else None,
             'refp_net_power_W':energy['refp_net_J']/t,'gate_positive_power_W':energy['gate_positive_J']/t}
    result={'native_complete':True,'short_test_pass':all(checks.values()),'checks':checks,'summary':summary,'criteria':criteria,
            'comparisons':comparisons,'captures':captures,'segments':segments,'held_drift':drifts,'frames':frames_out,
            'completions':completions,'terminal_pairs':pairs,'node_extrema':node_extrema,'reference_peak_current':peak_current,
            'source_energy':energy,'CMI_codes':cmi,'native_state':state['native'],'native_points':n,'scope':cfg['scope'],
            'power_note':'Signed source energy includes returned energy; gate positive energy is an ideal-drive load measure, not physical digital-driver power. No imposed module power pass limit.'}
    result['measurement_revision']={'source_run':os.path.basename(src),'settling_end':'next DAC update command from native valid crossing plus frozen SAR 50ps capture +100ps update; deadline remains 2ns after own gate 50%','native_zoom_ns':[109.98,110.10]}
    json.dump(result,open(a.output_dir+'/result.json','w'),indent=2,sort_keys=True)
    if sum(os.path.getsize(a.output_dir+'/'+q) for q in os.listdir(a.output_dir))>28*1024**2:raise ValueError('Derived output budget')
    print('CDAC short test measured',n,'points; electrical checks:',checks)


if __name__=='__main__':main()
