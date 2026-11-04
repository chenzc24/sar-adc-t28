"""Streaming full-native measurements; Python2.7/3; circuit failures are retained."""
from __future__ import print_function
import argparse,json,os,gzip,itertools,math
from reduce import frames,norm

def phase(t):
    if t<10e-9:return 'precharge'
    u=(t*1e9)%100
    if 10<=u<49.95:return 'track'
    if 49.95<=u<50.5:return 'turnoff'
    if 50.5<=u<54:return 'hold_before_compare'
    if 54<=u<75:return 'conversion'
    return 'idle_hold'

def decoded(v,p):return sum(1<<i for i in range(8) if v[p+str(i)]>.45)
def delta(v,p,n):return v[p]-v[n]
def maxabs(xs):return max(abs(x) for x in xs) if xs else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True);ap.add_argument('--output-dir',required=True);a=ap.parse_args()
    cfg=json.load(open(a.run_dir+'/inputs/measure.json'));state=json.load(open(a.run_dir+'/simulation.state.json'))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native incomplete')
    sources=[a.run_dir+'/raw/'+s for s in os.listdir(a.run_dir+'/raw') if s.endswith('.tran.tran')]
    if len(sources)!=1:raise ValueError('native transient count')
    names=[norm(x) for x in cfg['signals']];pairs={};mapping={};limit=cfg['terminal_screen_V']
    for dev in cfg['devices']:
        terms=[norm(x) for x in dev['terminals']];m={}
        for i,j in itertools.combinations(range(4),2):
            key='|'.join(sorted([terms[i],terms[j]]));m['DGSB'[i]+'DGSB'[j]]=key
            if key not in pairs:pairs[key]={'nodes':[terms[i],terms[j]],'peak_V':0,'peak_t_s':0,'duration_over_s':0,'phase_peaks_V':{},'last':0}
        mapping[dev['path']]=m
    targets=[];snapshots=[{} for _ in range(cfg['frames'])]
    for i in range(cfg['frames']):
        close=cfg['sample_close0_s']+i*1e-7;op=cfg['sample_open0_s']+i*1e-7
        for label,when in [('precharge',op-.1e-9),('preclose',close-.075e-9),('close',close),('held',close+1e-9),('quiet_end',close+49e-9),('post_step',close+59e-9),('code',111e-9+i*1e-7)]:
            targets.append((when,i,label))
    targets.sort();prev=None;count=0;last=-1.;stats={};edges={};energy={k:0. for k in ['vdd','clock','input','hold_vdd']}
    lastbad=[None]*cfg['frames'];faultmax=0;ideal_faultmax=0
    fout=gzip.open(a.output_dir+'/wave.csv.gz','wb');fout.write(('time,'+','.join(names)+'\n').encode('ascii'))
    def powers(v):return {'vdd':-v['vdd']*v['vvdd:1'],'clock':-v['clks']*v['vclk:1'],
                         'input':v['vinp']*v['vsenp:1']+v['vinn']*v['vsenn:1'],'hold_vdd':-v['vddh']*v['vvddh:1']}
    for t,v in frames(sources[0]):
        count+=1;v['0']=0
        if count==1 and set(names)-set(v):raise ValueError('missing nodes '+str(set(names)-set(v)))
        ph=phase(t)
        for key,z in pairs.items():
            q=abs(v[z['nodes'][0]]-v[z['nodes'][1]])
            if q>z['peak_V']:z.update(peak_V=q,peak_t_s=t)
            if q>z['phase_peaks_V'].get(ph,0):z['phase_peaks_V'][ph]=q
            if prev:
                old=z['last'];dt=t-prev[0]
                if old>limit and q>limit:z['duration_over_s']+=dt
                elif (old>limit)!=(q>limit):
                    cross=prev[0]+dt*(limit-old)/(q-old)
                    z['duration_over_s']+=t-cross if q>limit else cross-prev[0]
            z['last']=q
        for key in names:
            q=v[key]
            if key not in stats:stats[key]={'min':q,'max':q,'min_t':t,'max_t':t}
            z=stats[key]
            if q<z['min']:z.update(min=q,min_t=t)
            if q>z['max']:z.update(max=q,max_t=t)
        faultmax=max(faultmax,v['fault']);ideal_faultmax=max(ideal_faultmax,v['ifault'])
        frame=int(max(0,math.floor((t-10.025e-9)/1e-7)))
        if frame<cfg['frames'] and 10.025e-9+frame*1e-7<=t<=49.9e-9+frame*1e-7:
            err=delta(v,'xadc.topp','xadc.topn')-delta(v,'vinp','vinn')
            if abs(err)>.1*cfg['lsb_V']:lastbad[frame]=t
        if prev:
            pt,pv=prev
            for key in ['clks','xadc.cmpck','xideal.cmpck','eoc','ieoc']:
                if pv[key]<.45<=v[key] or pv[key]>.45>=v[key]:
                    te=pt+(t-pt)*(.45-pv[key])/(v[key]-pv[key]);edges.setdefault(key,[]).append([te,int(v[key]>pv[key])])
            # Complete N sample periods, excluding the extra next-frame capture tail.
            lo=max(pt,10e-9);hi=min(t,cfg['frames']*1e-7+10e-9)
            if hi>lo:
                p0=powers(pv);p1=powers(v);u0=(lo-pt)/(t-pt);u1=(hi-pt)/(t-pt)
                for k in energy:energy[k]+=(hi-lo)*(p0[k]+(p1[k]-p0[k])*u0+p0[k]+(p1[k]-p0[k])*u1)/2
            while targets and targets[0][0]<=t:
                when,idx,label=targets.pop(0);u=(when-pt)/(t-pt)
                if not 0<=u<=1+1e-9:raise ValueError('snapshot interpolation outside segment')
                row={k:pv[k]+u*(v[k]-pv[k]) for k in names}
                snapshots[idx][label]={'time_s':when,'values':row}
        # Exact near turnoff for display; all measurements above use native points.
        u=(t*1e9)%100;spacing=2e-12 if 49.8<=u<=50.5 else 100e-12
        if t-last>=spacing or count==1:fout.write((','.join(['%.12g'%t]+['%.12g'%v[k] for k in names])+'\n').encode('ascii'));last=t
        prev=(t,v)
    fout.close()
    if targets or abs(t-cfg['stop_s'])>1e-14:raise ValueError('missing samples/stop')
    rows=[]
    for i,s in enumerate(snapshots):
        pc=s['preclose']['values'];cl=s['close']['values'];h=s['held']['values'];q=s['quiet_end']['values'];st=s['post_step']['values'];pre=s['precharge']['values'];co=s['code']['values']
        src=delta(cl,'vinp','vinn');hd=delta(h,'xadc.topp','xadc.topn');hd0=delta(h,'hp','hn')
        rr={'frame':i,'sample_close_s':s['close']['time_s'],'input_at_close_V':src,'held_diff_V':hd,'held_diff_error_V':hd-src,
            'ideal_held_diff_V':delta(h,'xideal.topp','xideal.topn'),'increment_vs_ideal_V':hd-delta(h,'xideal.topp','xideal.topn'),
            'preclose_diff_error_V':delta(pc,'xadc.topp','xadc.topn')-delta(pc,'vinp','vinn'),
            'held_common_mode_V':(h['xadc.topp']+h['xadc.topn'])/2,
            'quiet_hold_drift_V':delta(q,'hp','hn')-hd0,'post_input_step_drift_V':delta(st,'hp','hn')-delta(q,'hp','hn'),
            'turnoff_diff_change_V':hd-delta(pc,'xadc.topp','xadc.topn'),
            'turnoff_P_change_V':h['xadc.topp']-pc['xadc.topp'],'turnoff_N_change_V':h['xadc.topn']-pc['xadc.topn'],
            'precharge_P_V':pre['xadc.xp.xs.net2']-pre['xadc.xp.xs.net3'],'precharge_N_V':pre['xadc.xn.xs.net2']-pre['xadc.xn.xs.net3'],
            'track_end_VGS_P_V':pc['xadc.xp.xs.net1']-pc['inp'],'track_end_VGS_N_V':pc['xadc.xn.xs.net1']-pc['inn'],
            'last_outside_settle_band_s':lastbad[i],'actual_code':decoded(co,'do_'),'ideal_code':decoded(co,'ido_')}
        rr['code_delta']=rr['actual_code']-rr['ideal_code'];rr['expected_center_code']=cfg['codes'][i] if cfg['codes'] else None
        rr['comparisons']=sum(49.975e-9+i*1e-7<e[0]<110e-9+i*1e-7 and e[1]==1 for e in edges.get('xadc.cmpck',[]))
        rows.append(rr)
    for z in pairs.values():z.pop('last')
    baddev=[path for path,m in mapping.items() if any(pairs[k]['peak_V']>limit for k in m.values())]
    warnings=state.get('native',{}).get('warning_codes',[])
    budget=cfg['budgets'];lsb=cfg['lsb_V'];duration=cfg['frames']*1e-7
    checks={'zero_native_CMI':not any('CMI-' in w for w in warnings),'terminal_screen':len(baddev)==0,
            'controller_function':faultmax<.45 and ideal_faultmax<.45 and all(x['comparisons']==8 for x in rows),
            'codes_within_one_of_ideal':all(abs(x['code_delta'])<=1 for x in rows),
            'quiet_hold_drift':maxabs(x['quiet_hold_drift_V'] for x in rows)<=budget['quiet_hold_LSB']*lsb,
            'post_input_step_feedthrough':maxabs(x['post_input_step_drift_V'] for x in rows)<=budget['input_feedthrough_LSB']*lsb,
            'precharge':all(min(x['precharge_P_V'],x['precharge_N_V'])>=.9*budget['precharge_fraction'] for x in rows),
            'VDD_clock_budget':(energy['vdd']+energy['clock'])/duration<=budget['VDD_plus_clock_W']}
    if cfg['case']!='sine':
        checks['static_preclose']=maxabs(x['preclose_diff_error_V'] for x in rows)<=budget['static_preclose_LSB']*lsb
        checks['held_differential']=maxabs(x['held_diff_error_V'] for x in rows)<=budget['held_diff_LSB']*lsb
    result={'case':cfg['case'],'frames':rows,'checks':checks,'snapshots':snapshots,'extrema':stats,'edges':edges,
            'terminal_pairs':pairs,'device_pairs':mapping,'exceeding_devices':baddev,'terminal_screen_V':limit,
            'power_W':{k:energy[k]/duration for k in energy},'power_interval_s':[10e-9,10e-9+duration],
            'native_points':count,'native_state':state.get('native'),'all_metrics_use_native_samples':True,
            'scope':'Unchanged bootstrap only; behavioral other modules; no PVT/FFT or lifetime qualification',
            'budgets':budget,'lsb_V':lsb,'stop_s':t,'function_fault_peak_V':faultmax}
    json.dump(result,open(a.output_dir+'/result.json','w'),indent=2,sort_keys=True)
    if sum(os.path.getsize(a.output_dir+'/'+x) for x in os.listdir(a.output_dir))>28*1024**2:raise ValueError('derived size guard')
    print('Reduced',count,'points;',len(baddev),'devices over screen; circuit checks',checks)

if __name__=='__main__':main()
