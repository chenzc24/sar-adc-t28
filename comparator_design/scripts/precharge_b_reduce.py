"""Same sizing metrics; native startup/reset windows and phase-specific internal peaks."""
from __future__ import print_function
import argparse,json,os,gzip,itertools
from native_frames import frames,norm

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--source-run-dir');a=p.parse_args()
    source=a.source_run_dir or a.run_dir
    cfg=json.load(open(os.path.join(source,'inputs','measure.json')))
    state=json.load(open(os.path.join(source,'simulation.state.json')))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native incomplete')
    paths=[os.path.join(source,'raw',s) for s in os.listdir(os.path.join(source,'raw')) if s.endswith('.tran.tran')]
    if len(paths)!=1:raise ValueError('ambiguous transient')
    contexts=cfg['contexts'];events=cfg['events'];vv=cfg['vdd'];limit=cfg['terminal_limit_V'];prev=None;last_export=-1;count=0
    pairs=list(itertools.combinations(range(4),2));letters='DGSB';results={};clock_energy=0.
    for c in contexts:
        for field in ['vinp','vinn','op','on','supply_current']:c[field]=norm(c[field])
        c['internal']=[norm(s) for s in c['internal']]
        for dev in c['devices']:dev['nodes']=[norm(n) for n in dev['nodes']]
        results[c['name']]={'energy_J':0.,'rows':[],'terminal_pairs':{},'phase_node_peaks':{}}
        for e in events:
            results[c['name']]['rows'].append({'diff_V':e['diff'],'cm_V':e['cm'],'clock50_s':e['clock50'],
                'decision_last_bad_s':e['clock50'],'decision_good':False,'decision_since_s':None,'reset_last_bad_s':e['fall50'],'reset_good':False,'reset_since_s':None,
                'max_diff_kick_V':0.,'max_cm_kick_V':0.,'pre_eval_diff_V':None,'residual_before_reset_V':None,
                'internal_reset_max_error_V':None})
    names=[norm(s) for s in cfg['signals']];f=gzip.open(os.path.join(a.output_dir,'wave.csv.gz'),'wb');f.write(('time,'+','.join(names)+'\n').encode('ascii'))
    for t,v in frames(paths[0]):
        v['0']=0.;count+=1
        if set(names)-set(v):raise ValueError('missing saved node')
        if prev:
            clock_energy+=-(v[norm('CK')]*v[norm('VCK:1')]+prev[1][norm('CK')]*prev[1][norm('VCK:1')])*(t-prev[0])/2
        for c in contexts:
            r=results[c['name']];op=v[c['op']];on=v[c['on']];dm=v[c['vinp']]-v[c['vinn']];cm=(v[c['vinp']]+v[c['vinn']])/2
            if prev:r['energy_J']+=-(v[c['supply_current']]+prev[1][c['supply_current']])*vv*(t-prev[0])/2
            for i,e in enumerate(events):
                if not (e['t']-.1e-9<=t<=e['end']):continue
                row=r['rows'][i]
                phase='evaluate' if e['t']<=t<e['t']+1.5e-9 else ('reset' if e['t']+1.5e-9<=t<=e['end'] else 'preclock')
                for n in c['internal']:
                    key=phase+':'+n.rsplit('.',1)[-1];value=v[n]
                    entry=r['phase_node_peaks'].get(key)
                    if entry is None or value>entry['peak_V']:r['phase_node_peaks'][key]={'peak_V':value,'time_s':t,'event_index':i}
                if t<=e['t']:row['pre_eval_diff_V']=dm
                if e['clock50']<=t<e['t']+1.5e-9:
                    correct=(op>=.8*vv and on<=.2*vv) if e['diff']>0 else (on>=.8*vv and op<=.2*vv)
                    row['decision_good']=correct
                    if not correct:row['decision_last_bad_s']=t;row['decision_since_s']=None
                    elif row['decision_since_s'] is None:row['decision_since_s']=t
                    delta=dm-(row['pre_eval_diff_V'] if row['pre_eval_diff_V'] is not None else e['diff'])
                    row['max_diff_kick_V']=max(row['max_diff_kick_V'],abs(delta))
                    row['max_cm_kick_V']=max(row['max_cm_kick_V'],abs(cm-e['cm']))
                    row['residual_before_reset_V']=delta
                if e['fall50']<=t<e['fall50']+.8e-9:
                    good=max(op,on)<=.2*vv;row['reset_good']=good
                    if not good:row['reset_last_bad_s']=t;row['reset_since_s']=None
                    elif row['reset_since_s'] is None:row['reset_since_s']=t
                    if t>=e['fall50']+.5e-9 and row['internal_reset_max_error_V'] is None:
                        row['internal_reset_max_error_V']=max(abs(v[n]-vv) for n in c['internal'])
            for dev in c['devices']:
                ns=dev['nodes'];vals=[v[n] for n in ns]
                for i,j in pairs:
                    key=dev['name']+':'+letters[i]+letters[j];value=abs(vals[i]-vals[j])
                    entry=r['terminal_pairs'].get(key)
                    if entry is None:entry={'peak_V':value,'time_s':t,'time_above_s':0.};r['terminal_pairs'][key]=entry
                    elif value>entry['peak_V']:entry.update(peak_V=value,time_s=t)
                    if prev:
                        old=abs(prev[1][ns[i]]-prev[1][ns[j]]);dt=t-prev[0]
                        if old>limit and value>limit:entry['time_above_s']+=dt
                        elif (old>limit)!=(value>limit):entry['time_above_s']+=dt*(max(old,value)-limit)/abs(value-old)
        if prev is None or t-last_export>=20e-12 or any(e['fall50']-125e-12<=t<=e['fall50']+325e-12 or e['t']-100e-12<=t<=e['t']+350e-12 for e in events):
            f.write((','.join(['%.12g'%t]+['%.12g'%v[n] for n in names])+'\n').encode('ascii'));last_export=t
        prev=(t,v)
    f.close()
    if abs(t-cfg['stop_s'])>1e-14:raise ValueError('wrong stop')
    for c in contexts:
        r=results[c['name']]
        for row in r['rows']:
            row['decision_s']=row['decision_since_s']-row['clock50_s'] if row['decision_good'] else None
            i=r['rows'].index(row)
            row['reset_s']=row['reset_since_s']-events[i]['fall50'] if row['reset_good'] else None
        r['max_decision_s']=max([x['decision_s'] for x in r['rows'] if x['decision_s'] is not None] or [0])
        r['max_reset_s']=max([x['reset_s'] for x in r['rows'] if x['reset_s'] is not None] or [0])
        r['all_correct']=all(x['decision_good'] for x in r['rows'])
        r['all_reset']=all(x['reset_good'] for x in r['rows'])
        r['max_residual_V']=max(abs(x['residual_before_reset_V'] or 0) for x in r['rows'])
        r['peak_terminal_V']=max(x['peak_V'] for x in r['terminal_pairs'].values())
        r['stress_fail_pairs']={k:x for k,x in r['terminal_pairs'].items() if x['peak_V']>limit}
        r['mean_comparator_supply_W']=r['energy_J']/t
        r['screens']={'polarity':r['all_correct'],'decision':r['all_correct'] and r['max_decision_s']<=cfg['goals']['decision_s'],
                      'reset':r['all_reset'] and r['max_reset_s']<=cfg['goals']['reset_s'],
                      'terminal':not r['stress_fail_pairs'],'residual':r['max_residual_V']<=cfg['goals']['residual_V'],
                      'power':r['mean_comparator_supply_W']<=cfg['goals']['power_W']}
    out={'source_run_id':cfg['run_id'],'contexts':results,'native_points':count,'native_state':state.get('native'),'load_F':cfg['load_F'],
         'shared_testbench_clock_energy_J':clock_energy,'shared_testbench_clock_mean_W':clock_energy/t,
         'clock_energy_scope':'Total ideal clock source net energy for ALL comparator contexts in this testbench; not per-comparator power. Input-source energy not measured.',
         'timing_note':'First good native sample after last bad sample, persistent until evaluation ends BEFORE falling edge starts. Conservative discrete upper bound; inspect native maxstep. Reset similarly measured after clock50 falling.',
         'scope':'No noise/mismatch/offset sweep qualification; comparator-only stress; receiver represented by equivalent C'}
    json.dump(out,open(os.path.join(a.output_dir,'result.json'),'w'),indent=2,sort_keys=True)
    print('Comparator sizing reduced',count,'native points; electrical failures retained')

if __name__=='__main__':main()
