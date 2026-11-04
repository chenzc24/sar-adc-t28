"""Bounded Python2.7/3 native analysis for the matched CDAC-input fixture."""
from __future__ import print_function
import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
import zlib

MIB = 1024*1024


def norm(n):
    return n.replace('\\', '').lower()


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for blob in iter(lambda:f.read(65536),b''):h.update(blob)
    return h.hexdigest()


def read(path):
    if os.path.getsize(path)>4*MIB:raise ValueError('Metadata exceeds4MiB')
    with open(path) as f:return json.load(f)


class Output(object):
    def __init__(self,path,limit):
        if limit<=0 or limit>30*MIB:raise ValueError('Expected <=30MiB output cap')
        self.path,self.limit,self.bytes=path,limit,0
        if not os.path.isdir(path):os.makedirs(path)
        if os.listdir(path):raise ValueError('Fresh derived directory required')

    def emit(self,handle,blob):
        if self.bytes+len(blob)>self.limit:raise ValueError('Derived output cap exceeded')
        handle.write(blob);self.bytes+=len(blob)

    def json(self,name,obj):
        blob=(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('ascii')
        with open(os.path.join(self.path,name),'wb') as f:self.emit(f,blob)


class PSF(object):
    """Every native time point, sparse updates held; missing initial data fails."""
    def __init__(self,path,selected):
        self.path,self.selected=path,set(selected)
        self.sha,self.bytes,self.points,self.last=hashlib.sha256(),0,0,None
        self.held,self.max_gap,self.binding=0,0.,{}

    def rows(self):
        section,sweep,group,prop,t,previous=None,None,None,False,None,None
        aliases,canonical,values,seen,selected_by_native={},set(),{},set(),{}
        ended=False
        with open(self.path,'rb') as f:
            while True:
                raw=f.readline(65537)
                if not raw:break
                if len(raw)>65536:raise ValueError('Native line cap exceeded')
                self.sha.update(raw);self.bytes+=len(raw)
                line=raw.decode('ascii').strip()
                if line in ('HEADER','TYPE','SWEEP','TRACE','VALUE','END'):
                    if group is not None and line!='TRACE':raise ValueError('Dangling GROUP')
                    section=line
                    if line=='VALUE':
                        if sweep!='time' or not self.selected<=canonical:raise ValueError('Required native TRACE/time missing')
                        for n in self.selected:selected_by_native.setdefault(self.binding[n],[]).append(n)
                    if line!='END':continue
                    ended=True
                else:
                    if not line or section not in ('SWEEP','TRACE','VALUE'):continue
                    if prop:
                        if line==')':prop=False
                        continue
                    if not line.startswith('"'):continue
                    _,key,tail=line.split('"',2);tail=tail.strip()
                    if section=='SWEEP':
                        if sweep is None:sweep=key
                        elif key!=sweep:raise ValueError('Multiple sweep variables')
                        prop='PROP(' in tail and ')' not in tail[tail.index('PROP('):]
                        continue
                    if section=='TRACE':
                        prop='PROP(' in tail and ')' not in tail[tail.index('PROP('):]
                        if tail.startswith('GROUP'):
                            if tail!='GROUP 1' or group is not None:raise ValueError('Unsupported GROUP')
                            group=key;continue
                        name=norm(key)
                        if name in canonical:raise ValueError('Duplicate canonical TRACE')
                        canonical.add(name);aliases[key]=name;self.binding[name]=name
                        if group is not None:
                            alias=norm(group)
                            if alias!=name and alias in canonical:raise ValueError('Duplicate GROUP alias')
                            canonical.add(alias);aliases[group]=name;self.binding[alias]=name;group=None
                        continue
                    value=float(tail)
                    if math.isnan(value) or math.isinf(value):raise ValueError('Nonfinite native value')
                    if key!=sweep:
                        if t is None:raise ValueError('Native scalar precedes time')
                        if key not in aliases:raise ValueError('Unknown native VALUE')
                        for n in selected_by_native.get(aliases[key],[]):
                            if n in seen:raise ValueError('Duplicate selected update')
                            values[n]=value;seen.add(n)
                        continue
                if t is not None:
                    if previous is not None and t<=previous:raise ValueError('Non-increasing native time')
                    if not self.points and t!=0:raise ValueError('Native history must start at zero')
                    if not self.selected<=set(values):raise ValueError('Uninitialized required native value')
                    if previous is not None:self.max_gap=max(self.max_gap,t-previous)
                    self.points+=1;self.last=t;self.held+=len(self.selected-seen)
                    yield t,values
                    previous=t
                if ended:
                    while True:
                        extra=f.read(65536)
                        if not extra:break
                        self.sha.update(extra);self.bytes+=len(extra)
                        if extra.strip():raise ValueError('Unexpected data after END')
                    break
                if t is not None and value<=t:raise ValueError('Non-increasing native marker')
                t=value;seen=set()
        if not ended or not self.points:raise ValueError('Missing native END or samples')


def inputs(v,arm):
    p,n=v[arm['topp']],v[arm['topn']]
    return dict(diff_v=p-n,cm_v=(p+n)*.5,topp_v=p,topn_v=n)


def extreme(item,name,value,t):
    s=item.setdefault(name,dict(min=value,max=value,min_time_s=t,max_time_s=t))
    if value<s['min']:s.update(min=value,min_time_s=t)
    if value>s['max']:s.update(max=value,max_time_s=t)


def reduce(path,cfg,out):
    voltages=[norm(n) for n in cfg['voltage_saves']]
    currents=[norm(n) for n in cfg['current_saves']]
    selected=voltages+currents
    if len(selected)!=len(set(selected)):raise ValueError('Duplicate configured signal')
    equations=cfg['kcl_terms']
    for node,terms in equations.items():
        incident=set(n for n,d in cfg['terminal_catalog'].items() if d['node']==node)
        if set(terms)!=incident or not set(terms)<=set(currents):raise ValueError('Incomplete top KCL incidence')
    arms=cfg['arms'];cycles=[]
    for item in cfg['cycles']:
        cycles.append(dict(configuration=item,initialized=None,after_release=None,pre_compare=None,pre_fall=None,
            raw_resolution=None,writes=[],input_excursions={},gate_charge_C={},last_phase_t=None,
            last_phase_i={},phase_first_native_s=None,phase_last_native_s=None))
    wave=['cmp_clk','cinit','prep','pren','vdd!','topp_a','topn_a','topp_b','topn_b',
          arms['evaluate']['comp_p'],arms['evaluate']['comp_n'],arms['evaluate']['data'],
          arms['evaluate']['write'],arms['evaluate']['d0'],arms['reset']['comp_p'],
          arms['reset']['comp_n'],arms['reset']['data'],arms['reset']['write'],arms['reset']['d0']]
    gate=[arms[a][n] for a in ['evaluate','reset'] for n in ['gate_p','gate_n']]
    nodes=sorted(equations)
    columns=['time']+wave+gate+['kcl:'+n for n in nodes]
    if not set(wave+gate)<=set(selected):raise ValueError('Required measurement voltage/current absent')
    out.json('wave.columns.json',dict(columns=columns,representation='f64le gzip, every native timestamp',
        units=['s']+['V']*len(wave)+['A']*(len(gate)+len(nodes))))
    pack=struct.Struct('<'+'d'*len(columns));encoder=zlib.compressobj(6,zlib.DEFLATED,31)
    psf=PSF(path,selected);stats,kcl_stats,pair_stats,all_events={},{},{},[]
    full_charge=dict((n,0.) for n in currents);previous_t,previous=None,None
    energy=0.;gzip_sha,plain_sha=hashlib.sha256(),hashlib.sha256();gzip_bytes=0
    def emit(handle,blob):
        out.emit(handle,blob);gzip_sha.update(blob)
        return len(blob)
    with open(os.path.join(out.path,'wave.native.f64le.gz'),'wb') as binary:
        for t,v in psf.rows():
            if v['vdd!']<=0:raise ValueError('Nonpositive VDD')
            row_kcl=dict((n,sum(v[b] for b in equations[n])) for n in nodes)
            for n,val in row_kcl.items():
                s=kcl_stats.setdefault(n,dict(max_abs_a=0.,time_s=t))
                if abs(val)>s['max_abs_a']:s.update(max_abs_a=abs(val),time_s=t,
                    incident_at_max_a=dict((b,v[b]) for b in equations[n]))
            for n in wave+gate:extreme(stats,n,v[n],t)
            for pair in cfg['mos_pairs']:
                a,b=pair['nodes'];delta=(0. if a=='0' else v[a])-(0. if b=='0' else v[b])
                key=pair['instance']+':'+pair['terminal'];s=pair_stats.get(key)
                if s is None or abs(delta)>s['max_abs_v']:
                    pair_stats[key]=dict(max_abs_v=abs(delta),signed_v=delta,time_s=t,
                        screen_v=pair['screen_v'],screen_exceeded=abs(delta)>pair['screen_v'])
            reset_levels=dict((name,dict((n,v[arm['prefix'].lower()+'.'+n]) for n in
                ['comp_p','comp_n','xcomp.x','xcomp.y'])) for name,arm in arms.items())
            frame=dict(time_s=t,arms=dict((a,inputs(v,arm)) for a,arm in arms.items()),
                init_control_v=v['cinit'],reset_levels_v=reset_levels,
                reset_all_above_90pct=dict((a,all(x>=.9*v['vdd!'] for x in ns.values())) for a,ns in reset_levels.items()))
            for cycle in cycles:
                c=cycle['configuration']
                if t<=c['release_start_s']:cycle['initialized']=frame
                if cycle['after_release'] is None and c['release_end_s']<=t<c['start_s']:
                    cycle['after_release']=frame
                if t<=c['start_s']:cycle['pre_compare']=frame
                if c['start_s']<=t<=c['start_s']+12e-9:
                    cycle['pre_fall']=dict(time_s=t,D0_v=v[arms['evaluate']['d0']],VDD_v=v['vdd!'])
                if c['start_s']<=t<=c['clock_fall_end_s']:
                    if abs(v['cinit'])>1e-12:raise ValueError('Initializer still active during comparator evaluation')
                    if cycle['pre_compare'] is None:raise ValueError('Missing pre-compare native sample')
                    pre=cycle['pre_compare']['arms'];now=frame['arms']
                    for name in ['diff_v','cm_v']:
                        extreme(cycle['input_excursions'],'evaluate_'+name,now['evaluate'][name]-pre['evaluate'][name],t)
                        extreme(cycle['input_excursions'],'reset_'+name,now['reset'][name]-pre['reset'][name],t)
                        ab=(now['evaluate'][name]-now['reset'][name])-(pre['evaluate'][name]-pre['reset'][name])
                        extreme(cycle['input_excursions'],'evaluate_minus_reset_'+name,ab,t)
                    if cycle['phase_first_native_s'] is None:cycle['phase_first_native_s']=t
                    cycle['phase_last_native_s']=t
                    if cycle['last_phase_t'] is not None:
                        dt=t-cycle['last_phase_t']
                        for n in gate:
                            cycle['gate_charge_C'][n]=cycle['gate_charge_C'].get(n,0.)+.5*(cycle['last_phase_i'][n]+v[n])*dt
                    cycle['last_phase_t']=t;cycle['last_phase_i']=dict((n,v[n]) for n in gate)
                    a=arms['evaluate'];difference=v[a['comp_p']]-v[a['comp_n']]
                    if cycle['raw_resolution'] is None and abs(difference)>=.5*v['vdd!']:
                        cycle['raw_resolution']=dict(first_native_time_s=t,raw_bit=int(difference>0),
                            output_difference_v=difference,inputs=frame['arms']['evaluate'])
            if previous is not None:
                dt=t-previous_t
                for n in currents:full_charge[n]+=.5*(previous[n]+v[n])*dt
                energy-=.5*(previous['vdd!']*previous['vvdd:1']+v['vdd!']*v['vvdd:1'])*dt
                for label,node in [('clock','cmp_clk'),('write',arms['evaluate']['write']),('reset_arm_write',arms['reset']['write'])]:
                    old=previous[node]-.5*previous['vdd!'];new=v[node]-.5*v['vdd!']
                    if old<0<=new:
                        if len(all_events)>=cfg['max_events']:raise ValueError('Event budget exceeded')
                        fraction=-old/(new-old);at=previous_t+fraction*dt
                        event=dict(kind=label,estimated_half_vdd_time_s=at,before_native_s=previous_t,after_native_s=t)
                        if label=='write':
                            a=arms['evaluate'];data=previous[a['data']]+fraction*(v[a['data']]-previous[a['data']])
                            rail=previous['vdd!']+fraction*(v['vdd!']-previous['vdd!'])
                            event.update(DATA_v_at_estimated_edge=data,DATA_bit=int(data>.5*rail),
                                         native_input_after_edge=frame['arms']['evaluate'])
                            for cycle in cycles:
                                c=cycle['configuration']
                                if c['start_s']<=at<c['clock_fall_end_s']:cycle['writes'].append(event)
                        all_events.append(event)
            plain=pack.pack(*([t]+[v[n] for n in wave]+[v[n] for n in gate]+[row_kcl[n] for n in nodes]))
            plain_sha.update(plain);gzip_bytes+=emit(binary,encoder.compress(plain))
            previous_t,previous=t,dict(v)
        gzip_bytes+=emit(binary,encoder.flush())
    if abs(psf.last-cfg['stop_s'])>1e-15:raise ValueError('Wrong native stop')
    for cycle in cycles:
        c=cycle['configuration']
        if any(cycle[k] is None for k in ['initialized','after_release','pre_compare','pre_fall','phase_first_native_s']):
            raise ValueError('Incomplete cycle observations')
        pre=cycle['pre_compare']['arms']['evaluate']['diff_v']
        cycle['pre_compare_target_error_v']=pre-c['target_diff_v']
        cycle['input_sign_before_clock']=1 if pre>0 else 0 if pre<0 else None
        cycle['DATA_matches_nominal_at_each_write']=[e['DATA_bit']==c['expected_DATA'] for e in cycle['writes']]
        cycle['DATA_matches_actual_precompare_sign']=[e['DATA_bit']==cycle['input_sign_before_clock'] for e in cycle['writes']]
        cycle['late_D0_bit']=int(cycle['pre_fall']['D0_v']>.5*cycle['pre_fall']['VDD_v'])
        cycle['late_D0_matches_nominal']=cycle['late_D0_bit']==c['expected_DATA']
        rise=[e for e in all_events if e['kind']=='clock' and c['start_s']<=e['estimated_half_vdd_time_s']<c['clock_fall_end_s']]
        cycle['clock_rises']=rise
        if len(rise)==1:
            clock=rise[0]['estimated_half_vdd_time_s']
            cycle['write_delay_from_clock_half_s']=[e['estimated_half_vdd_time_s']-clock for e in cycle['writes']]
            cycle['raw_resolution_delay_native_s']=None if cycle['raw_resolution'] is None else cycle['raw_resolution']['first_native_time_s']-clock
        for k in ['last_phase_t','last_phase_i']:cycle.pop(k)
    return dict(analysis_complete=True,acceptance_pass=None,circuit_repair_claim=False,scope=cfg['scope'],
        native_points=psf.points,first_native_time_s=0.,last_native_time_s=psf.last,
        native_PSF_END=True,raw_sha256=psf.sha.hexdigest(),raw_bytes=psf.bytes,
        max_native_gap_s=psf.max_gap,held_sparse_values=psf.held,
        native_trace_binding=dict((n,psf.binding[n]) for n in selected),cycles=cycles,events=all_events,
        extrema=stats,node_kcl=kcl_stats,full_native_signed_charge_C=full_charge,
        paired_module_VDD_energy_j=energy,energy_interval_s=[0.,psf.last],
        mos_pair_extrema=pair_stats,mos_screen_exceeded_records=sum(x['screen_exceeded'] for x in pair_stats.values()),
        mos_pair_scope=cfg['pair_scope'],boundaries=cfg['boundaries'],
        waveform=dict(file='wave.native.f64le.gz',rows=psf.points,columns=columns,compressed_bytes=gzip_bytes,
                      sha256=gzip_sha.hexdigest(),uncompressed_sha256=plain_sha.hexdigest()),
        interpretation='Same-grid A-minus-reset excursions are counterfactual compare disturbances. Input gate currents include total wrapper-port current; no intrinsic split or ADC code-error/noise claim.',
        measurement_methods=dict(extrema='All original native points; no decimation',
            pre_compare='Last original native point at or before the scheduled clock ramp start',
            raw_resolution='First native point with abs(COMP_P-COMP_N)>=0.5VDD; not interpolated and not a qualified decision deadline',
            write='Half-VDD event estimate from adjacent native points; DATA interpolated at that estimated event, not a setup/hold qualification',
            charge='Signed trapezoids; cycle gate charge uses only native points within the reported evaluation interval',
            clock='Original D2 ideal 0.1ns edges and12ns high window; reset reference arm stays low'))


def analyze(run,output):
    run,output=os.path.realpath(run),os.path.realpath(output)
    if os.path.normcase(output)!=os.path.normcase(os.path.join(run,'derived')):raise ValueError('Expected managed derived directory')
    cfg=read(os.path.join(run,'inputs','measurement.json'))
    state=read(os.path.join(run,'simulation.state.json'));native=state.get('native',{})
    if state.get('status')!='complete' or state.get('exit_code')!=0 or not native.get('native_analysis_pass') or not native.get('zero_error_footer'):
        raise ValueError('Native simulation incomplete')
    with open(os.path.join(run,'raw','logStatus')) as f:
        if not re.search(r'\btran_kickback\s+PASS\b',f.read(65536)):raise ValueError('Exact transient PASS missing')
    for name,h in cfg['required_input_sha256'].items():
        if '/' in name or '\\' in name or name.startswith('.'):raise ValueError('Unsafe packaged input')
        if digest(os.path.join(run,'inputs',name))!=h:raise ValueError('Frozen input hash mismatch: '+name)
    files=[n for n in os.listdir(os.path.join(run,'raw')) if n.endswith('.tran.tran')]
    if len(files)!=1:raise ValueError('Expected one native ASCII transient')
    out=Output(output,cfg['max_output_bytes'])
    log=os.path.join(run,'spectre.out')
    if os.path.getsize(log)>2*MIB:raise ValueError('Simulator log cap exceeded')
    with open(log,'rb') as src,open(os.path.join(output,'spectre.original.log'),'wb') as dest:
        for chunk in iter(lambda:src.read(65536),b''):out.emit(dest,chunk)
    result=reduce(os.path.join(run,'raw',files[0]),cfg,out)
    result.update(measurement_sha256=digest(os.path.join(run,'inputs','measurement.json')),
        native_warning_codes=native.get('warning_codes'),native_effective_settings=native.get('effective_settings'),
        simulator_version=native.get('version'),original_simulator_log_sha256=digest(log))
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>256*MIB:raise ValueError('Analysis RSS cap exceeded')
    result['derived_bytes_before_result']=out.bytes
    out.json('result.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    if sys.platform.startswith('linux'):
        import resource
        _,hard=resource.getrlimit(resource.RLIMIT_AS);soft=240*MIB if hard==resource.RLIM_INFINITY else min(240*MIB,hard)
        resource.setrlimit(resource.RLIMIT_AS,(soft,hard))
    result=analyze(a.run_dir,a.output_dir)
    print('COMPARATOR_NATIVE_KICKBACK_OK',result['native_points'],'acceptance remains null')


if __name__=='__main__':main()
