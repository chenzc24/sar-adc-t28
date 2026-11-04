"""Streaming native-point protocol/stress reduction; Python2.7/3, no NumPy."""
from __future__ import print_function
import argparse
import hashlib
import math
import os
import re
import struct
import sys
import zlib

import native_support as s

MIB=1024*1024


def frame(t,v,cfg):
    r=cfg['roles'];rail=v[r['rail']]
    levels=dict((n,v[r[n]]) for n in ['comp_p','comp_n','x','y','pr','nr','raw','dec','clock'])
    ready=all(levels[n]>=.9*rail for n in ['comp_p','comp_n','x','y','pr','nr']) and all(levels[n]<=.1*rail for n in ['raw','dec','clock'])
    return dict(time_s=t,input_diff_v=v[r['topp']]-v[r['topn']],input_cm_v=.5*(v[r['topp']]+v[r['topn']]),
        reset_levels_v=levels,reset_ready_90pct=ready,
        control_levels_v=dict((n,v[r[n]]) for n in ['active','write','update','clock_reset','clock_q','quiet']),
        token_bits=[i for i,n in enumerate(cfg['tokens']) if v[n]>.5*rail],
        D_v=[v[n] for n in cfg['data_nodes']],D_bits=[int(v[n]>.5*rail) for n in cfg['data_nodes']],
        ref_Q_bits=[int(v[n]>.5*rail) for n in cfg['ref_q_nodes']],rail_v=rail)


def finalize(c,observation,where):
    c['after_write_observation']=observation;c['after_write_observation_boundary']=where
    token=c['token_bit']
    c['stored_bit_after_recovery']=None if token is None else observation['D_bits'][token]
    c['stored_bit_matches_positive_input']=token is not None and c['stored_bit_after_recovery']==1
    c['expected_D_bits_after_write']=None if token is None else [int(i>=token) for i in range(8)]
    c['all_D_bits_match_token_history']=token is not None and observation['D_bits']==c['expected_D_bits_after_write']
    c['held_target_error_before_compare_v']=c['pre_compare']['input_diff_v']-.0017578125
    if c.get('clock_fall_half_s') is not None:
        end=c.get('next_clock_rise_half_s')
        c['reset_to_next_compare_half_interval_s']=None if end is None else end-c['clock_fall_half_s']
        ready=c.get('first_reset_ready_native')
        c['first_ready_delay_from_clock_fall_half_s']=None if ready is None else ready['time_s']-c['clock_fall_half_s']
        c['native_clock_half_high_width_s']=c['clock_fall_half_s']-c['clock_rise_half_s']
        c['reset_assert_to_clock_fall_half_s']=None if len(c['resets'])!=1 else c['clock_fall_half_s']-c['resets'][0]['time_s']
    c['write_count']=len(c['writes']);c['update_count']=len(c['updates']);c['reset_count']=len(c['resets'])
    c['write_delay_from_clock_half_s']=[e['time_s']-c['clock_rise_half_s'] for e in c['writes']]
    c['protocol_pass']=(token is not None and len(c['writes'])==len(c['updates'])==len(c['resets'])==1
        and c.get('clock_fall_half_s') is not None and c['stored_bit_matches_positive_input'] and c['all_D_bits_match_token_history']
        and c['writes'][0]['DATA_bit']==1 and c['writes'][0]['token_bits']==[token]
        and c['writes'][0]['time_s']<c['updates'][0]['time_s']<=c['resets'][0]['time_s']
        and c['resets'][0]['time_s']<=c['clock_fall_half_s'])


def reduce(path,cfg,out):
    selected=[s.norm(n) for n in cfg['voltage_saves']+cfg['current_saves']]
    if len(selected)!=len(set(selected)):raise ValueError('Duplicate configured save')
    r=cfg['roles'];cols=['time']+cfg['wave_voltage_columns']+cfg['wave_current_columns']+['kcl:'+n for n in sorted(cfg['kcl_terms'])]
    if len(cols)!=len(set(cols)) or not set(cfg['wave_voltage_columns']+cfg['wave_current_columns'])<=set(selected):raise ValueError('Invalid native wave columns')
    for node,terms in cfg['kcl_terms'].items():
        incident=set(n for n,d in cfg['terminal_catalog'].items() if d['node']==node)
        if set(terms)!=incident or not set(terms)<=set(selected):raise ValueError('Incomplete KCL incidence')
    # One streaming maximum per unordered node pair, then expand to every MOS.
    groups={}
    for p in cfg['mos_pairs']:groups.setdefault(tuple(sorted(p['nodes'])),None)
    pairs=list(groups);maxima=[None]*len(pairs)
    pack=struct.Struct('<'+'d'*len(cols));encoder=zlib.compressobj(6,zlib.DEFLATED,31)
    gzip_sha=hashlib.sha256();plain_sha=hashlib.sha256();gzip_bytes=0
    psf=s.PSF(path,selected);cycles=[];events=[];unassigned=[];stats={};kcl_stats={}
    previous,pt,last_low,first_frame,last_frame=None,None,None,None,None
    last_ready_state=None;energy=0.;charge=dict((n,0.) for n in cfg['current_saves'])
    charge=dict((s.norm(n),v) for n,v in charge.items())
    event_signals=[('clock','clock','rise'),('clock_fall','clock','fall'),('write','write','rise'),('write_fall','write','fall'),
        ('update','update','rise'),('update_fall','update','fall'),('reset','clock_reset','rise')]
    def output(blob,handle):
        out.emit(handle,blob);gzip_sha.update(blob)
        return len(blob)
    with open(os.path.join(out.path,'wave.native.f64le.gz'),'wb') as binary:
        for t,v in psf.rows():
            if psf.points>cfg['max_native_points']:raise ValueError('Native point budget exceeded')
            rail=v[r['rail']]
            if rail<=0:raise ValueError('Nonpositive rail')
            now=frame(t,v,cfg);last_frame=now
            if first_frame is None:first_frame=now
            if v[r['clock']]<=.1*rail:last_low=now
            if t>=cfg['release_end_s'] and abs(v[r['init']])>1e-10:raise ValueError('Initializer reattached after release')
            rowkcl=dict((n,sum(v[b] for b in terms)) for n,terms in cfg['kcl_terms'].items())
            for n,val in rowkcl.items():
                old=kcl_stats.get(n)
                if old is None or abs(val)>old['max_abs_a']:
                    kcl_stats[n]=dict(max_abs_a=abs(val),time_s=t,incident_at_max_a=dict((b,v[b]) for b in cfg['kcl_terms'][n]))
            for n in cfg['wave_voltage_columns']+cfg['wave_current_columns']:s.extreme(stats,n,v[n],t)
            for i,(a,b) in enumerate(pairs):
                delta=(0. if a=='0' else v[a])-(0. if b=='0' else v[b]);old=maxima[i]
                if old is None or abs(delta)>old[0]:maxima[i]=(abs(delta),delta,t)
            if previous is not None:
                dt=t-pt
                for n in charge:charge[n]+=.5*(previous[n]+v[n])*dt
                energy-=.5*(previous[r['rail']]*previous['vvdd:1']+rail*v['vvdd:1'])*dt
                found=[]
                for label,role,direction in event_signals:
                    node=r[role];a=previous[node]-.5*previous[r['rail']];b=v[node]-.5*rail
                    if (direction=='rise' and a<0<=b) or (direction=='fall' and a>0>=b):
                        f=-a/(b-a);at=pt+f*dt
                        if at<cfg['sample_fall_end_s']:continue
                        found.append((at,label,f))
                for at,label,f in sorted(found):
                    if len(events)>=cfg['max_events']:raise ValueError('Event cap exceeded')
                    tokens=[i for i,n in enumerate(cfg['tokens']) if previous[n]+f*(v[n]-previous[n])>.5*(previous[r['rail']]+f*(rail-previous[r['rail']]))]
                    e=dict(kind=label,time_s=at,before_native_s=pt,after_native_s=t,token_bits=tokens)
                    if label=='clock':
                        if cycles:
                            cycles[-1]['next_clock_rise_half_s']=at
                            finalize(cycles[-1],last_low or frame(pt,previous,cfg),'last native CLK<=0.1VDD before next rise')
                        pre=last_low or frame(pt,previous,cfg)
                        c=dict(index=len(cycles),token_bit=tokens[0] if len(tokens)==1 else None,clock_rise_half_s=at,
                            pre_compare=pre,writes=[],updates=[],resets=[],clock_fall_half_s=None,
                            first_reset_ready_native=None,reset_ready_transitions=[],next_clock_rise_half_s=None)
                        cycles.append(c);last_ready_state=None
                    elif not cycles:unassigned.append(e)
                    else:
                        c=cycles[-1]
                        if label=='write':
                            dv=previous[r['data']]+f*(v[r['data']]-previous[r['data']]);rv=previous[r['rail']]+f*(rail-previous[r['rail']])
                            e.update(DATA_v=dv,DATA_bit=int(dv>.5*rv));c['writes'].append(e)
                        elif label=='update':c['updates'].append(e)
                        elif label=='reset':c['resets'].append(e)
                        elif label=='clock_fall':
                            if c['clock_fall_half_s'] is not None:e['duplicate_clock_fall']=True
                            c['clock_fall_half_s']=at
                    events.append(e)
            if cycles and cycles[-1]['clock_fall_half_s'] is not None:
                c=cycles[-1]
                if now['reset_ready_90pct'] and c['first_reset_ready_native'] is None:c['first_reset_ready_native']=now
                if now['reset_ready_90pct']!=last_ready_state:
                    if len(c['reset_ready_transitions'])>=100:raise ValueError('Reset readiness transition cap')
                    c['reset_ready_transitions'].append(dict(time_s=t,ready=now['reset_ready_90pct']))
                    last_ready_state=now['reset_ready_90pct']
            plain=pack.pack(*([t]+[v[n] for n in cfg['wave_voltage_columns']+cfg['wave_current_columns']]+[rowkcl[n] for n in sorted(rowkcl)]))
            plain_sha.update(plain);gzip_bytes+=output(encoder.compress(plain),binary)
            previous,pt=dict(v),t
        gzip_bytes+=output(encoder.flush(),binary)
    if abs(psf.last-cfg['stop_s'])>1e-15:raise ValueError('Native endpoint mismatch')
    if cycles:finalize(cycles[-1],last_frame,'final native endpoint; no subsequent compare assumed')
    extrema={};group_results=dict(zip(pairs,maxima))
    for p in cfg['mos_pairs']:
        key=tuple(sorted(p['nodes']));value,signed,at=group_results[key]
        if p['nodes'][0]!=key[0]:signed=-signed
        extrema[p['instance']+':'+p['terminal']]=dict(max_abs_v=value,signed_v=signed,time_s=at,
            screen_v=p['screen_v'],screen_exceeded=value>p['screen_v'])
    counts=dict((label,sum(e['kind']==label for e in events)) for label in ['clock','clock_fall','write','update','reset'])
    sequence=[c['token_bit'] for c in cycles]
    terminated=(not last_frame['token_bits'] and all(last_frame['control_levels_v'][n]<=.1*last_frame['rail_v'] for n in ['active','write','update','clock_reset','clock_q']) and last_frame['reset_levels_v']['clock']<=.1*last_frame['rail_v'])
    result=dict(analysis_complete=True,acceptance_pass=None,circuit_repair_claim=False,scope=cfg['scope'],
        protocol_eight_pass=len(cycles)==8 and sequence==list(range(7,-1,-1)) and all(c['protocol_pass'] for c in cycles) and not unassigned and all(n==8 for n in counts.values()) and terminated,
        token_sequence_terminated=terminated,final_native_frame=last_frame,
        event_counts=counts,token_sequence=sequence,cycles=cycles,events=events,unassigned_events=unassigned,
        native_points=psf.points,first_native_time_s=0.,last_native_time_s=psf.last,native_PSF_END=True,
        raw_sha256=psf.sha.hexdigest(),raw_bytes=psf.bytes,max_native_gap_s=psf.max_gap,held_sparse_values=psf.held,
        native_trace_binding=dict((n,psf.binding[n]) for n in selected),extrema=stats,node_kcl=kcl_stats,
        full_native_signed_charge_C=charge,fixture_VDD_energy_j=energy,energy_interval_s=[0.,psf.last],
        mos_pair_extrema=extrema,mos_screen_exceeded_records=sum(v['screen_exceeded'] for v in extrema.values()),
        mos_pair_scope=cfg['pair_scope'],unique_node_pairs_streamed=len(pairs),boundaries=cfg['boundaries'],
        waveform=dict(file='wave.native.f64le.gz',rows=psf.points,columns=cols,compressed_bytes=gzip_bytes,sha256=gzip_sha.hexdigest(),uncompressed_sha256=plain_sha.hexdigest()),
        measurement_methods=dict(event='Adjacent-native half-VDD crossing estimate; token/DATA evaluated on that bracket, not a setup/hold margin',
            pre_compare='Last native point with CLK<=0.1VDD; regeneration may already have begun below this diagnostic threshold',
            recovery='Actual CLK half-fall to next half-rise, first native full-level recovery and pre-rise levels; no fixed reset timer',
            readiness='COMP_P/N,X/Y,PR/NR>=0.9VDD and RAW,DEC,CLK<=0.1VDD, diagnostic only; threshold not a qualified margin',
            final_write='Token-indexed D observation before next comparison, or native endpoint for final token',
            stress='Every original native time point, all retained MOS six terminal pairs; deduplicated node pairs then expanded',
            accuracy='No inferred ADC code/ENOB, input noise/offset, reference settling or post-cut Miller claim'))
    out.json('wave.columns.json',dict(columns=cols,representation='f64le gzip, all native timestamps'))
    return result


def analyze(run,output):
    run,output=os.path.realpath(run),os.path.realpath(output)
    if os.path.normcase(output)!=os.path.normcase(os.path.join(run,'derived')):raise ValueError('Expected managed derived directory')
    cfg=s.read(os.path.join(run,'inputs','measurement.json'));state=s.read(os.path.join(run,'simulation.state.json'));native=state.get('native',{})
    if state.get('status')!='complete' or state.get('exit_code')!=0 or not native.get('native_analysis_pass') or not native.get('zero_error_footer'):raise ValueError('Native simulation incomplete')
    with open(os.path.join(run,'raw','logStatus')) as f:
        if not re.search(r'\btran_feedback\s+PASS\b',f.read(65536)):raise ValueError('Exact native transient PASS missing')
    for n,h in cfg['required_input_sha256'].items():
        if '/' in n or '\\' in n or n.startswith('.'):raise ValueError('Unsafe input path')
        if s.digest(os.path.join(run,'inputs',n))!=h:raise ValueError('Frozen input hash differs: '+n)
    files=[n for n in os.listdir(os.path.join(run,'raw')) if n.endswith('.tran.tran')]
    if len(files)!=1:raise ValueError('Expected one ASCII native transient')
    log=os.path.join(run,'spectre.out')
    if os.path.getsize(log)>2*MIB:raise ValueError('Native log cap exceeded')
    extra=['analysis.admission.json','analysis.state.json','simulation.admission.json','simulation.state.json','raw/logStatus']
    overhead=sum(os.path.getsize(os.path.join(run,n)) for n in extra if os.path.isfile(os.path.join(run,n)))
    if overhead>512*1024:raise ValueError('Collection state/logStatus metadata reserve exceeded')
    with open(log,'rb') as f:log_bytes=f.read()
    text=log_bytes.decode('ascii')
    for n,kind in [(len(cfg['voltage_saves']),'voltage'),(len(cfg['current_saves']),'current')]:
        if not re.search(r'save\s+%d\s+\(%s\)'%(n,kind),text):raise ValueError('Accepted native save count differs')
    if 'allpub' in text:raise ValueError('Unexpected allpub fallback')
    accepted=re.search(r'Number of accepted tran steps\s*=\s*(\d+)',text)
    if not accepted:raise ValueError('Missing accepted native step count')
    out=s.Output(output,cfg['max_output_bytes'])
    with open(os.path.join(output,'spectre.original.log'),'wb') as f:out.emit(f,log_bytes)
    result=reduce(os.path.join(run,'raw',files[0]),cfg,out)
    if result['native_points']!=int(accepted.group(1))+1:raise ValueError('Native row/accepted-step mismatch')
    result.update(measurement_sha256=s.digest(os.path.join(run,'inputs','measurement.json')),original_simulator_log_sha256=s.digest(log),
        native_warning_codes=native.get('warning_codes'),native_effective_settings=native.get('effective_settings'),simulator_version=native.get('version'),
        collection_budget=dict(derived_cap_bytes=cfg['max_output_bytes'],native_log_cap_bytes=2*MIB,
            state_metadata_cap_bytes=512*1024,receipt_reserve_bytes=512*1024,total_cap_bytes=32*MIB))
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
    print('COMPARATOR_NATIVE_FEEDBACK_ANALYSIS_COMPLETE',result['native_points'],'protocol_eight_pass',result['protocol_eight_pass'])


if __name__=='__main__':main()
