"""Stream native storage truth/stress evidence. Python2.7/3, never launches."""
from __future__ import print_function
import argparse
import gzip
import hashlib
import json
import os
import re
import struct
import sys

import full_gate_analyze as native


def identity(path):
    h=hashlib.sha256();size=0
    with open(path,'rb') as f:
        while True:
            b=f.read(65536)
            if not b:break
            h.update(b);size+=len(b)
    return dict(bytes=size,sha256=h.hexdigest())


def verify_external(path):
    m=native.read(path)
    for f,want in [(m['file'],dict(bytes=m['bytes'],sha256=m['sha256']))]+list(m['model_files'].items()):
        if identity(f)!=want:raise ValueError('Frozen external library/model identity changed: '+f)
    return dict(file=m['file'],sha256=m['sha256'],model_files=m['model_files'],
                readonly_checked_at='post simulation; parent must also preflight before dispatch')


def observe_history(output,cfg):
    """All native hold samples, threshold brackets and complete pulse counts."""
    names=native.read(os.path.join(output,'peak.columns.json'))['names']
    indices=dict((n,i) for i,n in enumerate(names));rail=indices['vdd!']
    spec=cfg['storage'];observers=spec['observers'];sets={}
    needed=set(['vdd!'])
    for o in observers:
        signals=[o[k] for k in ['Q','QB','R','S','CK','D','RST','CDN'] if k in o]
        needed.update(native.norm(n) for n in signals)
        phases=spec['SR_phases'] if o['kind']=='SR' else spec['DFF_phases']
        sets[o['name']]=dict(source_instance=o['source_instance'],kind=o['kind'],
                            phases=[dict(index=p['index'],native_hold_points=0,
                                input_mismatch_points=0,Q_mismatch_points=0,QB_mismatch_points=0,
                                first_hold_native_s=None,last_hold_native_s=None) for p in phases])
    if not needed<=set(indices):raise ValueError('Required storage functional voltage column missing')
    events=dict((n,[]) for n in needed if n!='vdd!')
    previous=None;last=None;rows=0;gap=0.;rowstruct=struct.Struct('<'+'d'*len(names))
    def at(row,node):return row[indices[native.norm(node)]]
    def match(row,node,value):
        return at(row,node)>=spec['hold_rail_high']*row[rail] if value else at(row,node)<=spec['hold_rail_low']*row[rail]
    with open(os.path.join(output,'peak.native.bin'),'rb') as f:
        while True:
            blob=f.read(rowstruct.size)
            if not blob:break
            if len(blob)!=rowstruct.size:raise ValueError('Incomplete storage observation row')
            row=rowstruct.unpack(blob);t=row[0];rows+=1
            if previous is not None:
                if t<=previous[0]:raise ValueError('Nonincreasing storage observation time')
                gap=max(gap,t-previous[0])
                for n in events:
                    before=at(previous,n)-.5*previous[rail];after=at(row,n)-.5*row[rail]
                    d=1 if before<0<=after else -1 if before>0>=after else 0
                    if d:
                        tm=previous[0]-before*(t-previous[0])/(after-before)
                        events[n].append(dict(time_s=tm,direction=d,native_bracket_s=[previous[0],t]))
            for o in observers:
                phases=spec['SR_phases'] if o['kind']=='SR' else spec['DFF_phases']
                #20 short phases,26 contexts: bounded work, no waveform arrays.
                for j,p in enumerate(phases):
                    if not p['hold_start_s']<=t<=p['hold_stop_s']:continue
                    out=sets[o['name']]['phases'][j];out['native_hold_points']+=1
                    out['last_hold_native_s']=t
                    if out['first_hold_native_s'] is None:out['first_hold_native_s']=t
                    keys=['R','S'] if o['kind']=='SR' else ['CK','D','RST']
                    out['input_mismatch_points']+=int(any(not match(row,o[k],p[k]) for k in keys))
                    out['Q_mismatch_points']+=int(not match(row,o['Q'],p['Q']))
                    if 'QB' in o:out['QB_mismatch_points']+=int(not match(row,o['QB'],p['QB']))
            previous=row;last=t
    if rows<2 or abs(last-cfg['source_history_stop_s'])>1e-15:
        raise ValueError('Storage observation history END missing')
    verdicts=[];patterns=[]
    for o in observers:
        phases=spec['SR_phases'] if o['kind']=='SR' else spec['DFF_phases'];lastq=None
        for j,p in enumerate(phases):
            out=sets[o['name']]['phases'][j]
            qevents=[e for e in events[native.norm(o['Q'])] if p['start_s']<=e['time_s']<p['stop_s']]
            expected_change=lastq is not None and p['Q']!=lastq
            wanted_dir=1 if expected_change and p['Q'] else -1
            clean=(len(qevents)==1 and qevents[0]['direction']==wanted_dir) if expected_change else not qevents
            out.update(expected_Q=p['Q'],Q_events=qevents,expected_Q_change=expected_change,
                       exact_expected_edge_pattern=clean,overlap_clock_reset=p.get('overlap_clock_reset',False),
                       signed_actual_input_to_Q_delay_s=None,delay_status='not_applicable')
            if expected_change:
                if o['kind']=='SR':
                    old=phases[j-1];key='R' if p['R']!=old['R'] else 'S'
                else:key='RST' if p['RST'] else 'CK'
                direction=1 if p[key] else -1
                cause=[e for e in events[native.norm(o[key])] if e['direction']==direction
                       and p['start_s']-.1e-9<=e['time_s']<p['start_s']+.3e-9]
                out['delay_status']='missing_or_ambiguous_native_threshold_events'
                if len(cause)==1 and len(qevents)==1:
                    out['signed_actual_input_to_Q_delay_s']=qevents[0]['time_s']-cause[0]['time_s']
                    out['delay_status']='linear_halfrail_estimate_between_declared_native_brackets'
            flags=[out[k] for k in ['input_mismatch_points','Q_mismatch_points','QB_mismatch_points']]
            verdict=None if out['native_hold_points']<2 else not any(flags)
            out['stable_hold_observation_pass']=verdict;verdicts.append(verdict)
            # Initial DC transition has no previous accepted state. All later
            # extra/missing edges are retained, including reset/clock overlap.
            if lastq is not None:patterns.append(clean)
            lastq=p['Q']
    return dict(contexts=sets,events=events,native_rows=rows,max_native_grid_gap_s=gap,
        stable_hold_observation_pass=False if False in verdicts else None if None in verdicts else True,
        clean_expected_Q_edge_patterns=all(patterns),
        hold_policy='Every original native point in400..900ps phase hold windows,10/90percent VDD bands; not library noise-margin or setup/hold signoff.',
        event_policy='Linear halfrail estimates include original native brackets; no waveform interpolation, extrema replacement or phase recentering.',
        overlap_policy='Simultaneous source clock/reset assertion is deliberate; stable reset priority and any extra Q pulses are separate results, not automatically waived.',
        setup_hold_recovery_removal_qualified=None)


def compress_history(output):
    path=os.path.join(output,'peak.native.bin');dest=path+'.gz';temp=dest+'.writing'
    if os.path.exists(dest) or os.path.exists(temp):raise ValueError('Preserve prior compressed history')
    before=identity(path)
    with open(path,'rb') as source,open(temp,'wb') as out:
        gz=gzip.GzipFile(filename='',mode='wb',compresslevel=6,fileobj=out,mtime=0)
        try:
            while True:
                blob=source.read(65536)
                if not blob:break
                gz.write(blob)
        finally:gz.close()
    decoded=hashlib.sha256();size=0
    with gzip.open(temp,'rb') as f:
        while True:
            blob=f.read(65536)
            if not blob:break
            size+=len(blob);decoded.update(blob)
    if dict(bytes=size,sha256=decoded.hexdigest())!=before:
        raise ValueError('Lossless history validation failed')
    os.rename(temp,dest)
    os.remove(path) # Only new derived scratch, never original native PSF.
    return dict(file='peak.native.bin.gz',uncompressed=before,compressed=identity(dest),
                decompressed_bytes_and_SHA_match=True,every_native_row_preserved=True,
                raw_PSF_modified=False)


def collection_budget(run,output,cfg,pending_result_bytes=0):
    known=['simulation.state.json','analysis.state.json','simulation.admission.json','analysis.admission.json',
           'spectre.out','raw/logStatus','source_provenance.json']
    paths=[os.path.join(run,n) for n in known]
    for parent,dirs,files in os.walk(output,followlinks=False):
        dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(parent,d))]
        paths += [os.path.join(parent,f) for f in files]
    sizes=dict((os.path.relpath(p,run),os.path.getsize(p)) for p in paths if os.path.isfile(p) and not os.path.islink(p))
    reserve=cfg['storage']['final_state_reserve_bytes'];total=sum(sizes.values())+pending_result_bytes+reserve
    if total>cfg['storage']['collection_cap_bytes']:
        raise ValueError('Storage collection exceeds30MiB including all logs/states and final-state reserve')
    return dict(existing_members=sizes,pending_result_bytes=pending_result_bytes,
                final_state_reserve_bytes=reserve,projected_bytes=total,
                user_cap_bytes=cfg['storage']['user_collection_cap_bytes'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True);ap.add_argument('--output-dir',required=True)
    a=ap.parse_args();run=os.path.realpath(a.run_dir);out=os.path.realpath(a.output_dir)
    if out!=os.path.join(run,'derived') or os.path.exists(os.path.join(out,'result.json')):
        raise ValueError('Fresh managed derived directory required')
    state=native.read(os.path.join(run,'simulation.state.json'));n=state.get('native',{})
    if state['status']!='complete' or state['exit_code']!=0 or not n.get('native_analysis_pass') or not n.get('zero_error_footer'):
        raise ValueError('Native simulation not complete/PASS')
    with open(os.path.join(run,'raw/logStatus')) as f:
        if not re.search(r'tran_first\s+PASS',f.read()):raise ValueError('Native transient PASS missing')
    external=verify_external(os.path.join(run,'inputs/external_library.json'))
    raw=[os.path.join(run,'raw',s) for s in os.listdir(os.path.join(run,'raw')) if s.endswith('.tran.tran')]
    if len(raw)!=1:raise ValueError('Exactly one native ASCII transient required')
    cfgpath=os.path.join(run,'inputs/measurement.json');cfg=native.read(cfgpath)
    result=native.summarize(raw[0],cfg,out)
    result['storage_observations']=observe_history(out,cfg)
    for key in ['peak_error_v','peak_time_error_s']:result.pop(key,None)
    result['peak_snapshot_role']='Diagnostic maximum on first SR output, not a source-fit target or acceptance gate'
    result['measurement_sha256']=identity(cfgpath)['sha256'];result['external_identity']=external
    result['physical_terminal_screen_pass']=not any(v['over_limit_native_points'] for v in result['full_history_voltage_stress'].values())
    result['native_warning_codes']=n.get('warning_codes');codes=result['native_warning_codes']
    result['native_CMI_present']=any(c.startswith('CMI') for c in codes) if codes is not None else None
    result['native_effective_settings']=n.get('effective_settings');result['whole_ADC_qualified']=None
    result['returned_waveform']=compress_history(out)
    result['analysis_peak_rss_bytes']=None
    if sys.platform.startswith('linux'):
        import resource
        result['analysis_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if result['analysis_peak_rss_bytes']>cfg['storage']['max_analysis_rss_bytes']:
            raise ValueError('Storage analysis exceeds256MiB RSS')
    result['collection_budget_policy']=dict(derived_guard_bytes=cfg['storage']['collection_cap_bytes'],
        user_cap_bytes=cfg['storage']['user_collection_cap_bytes'],final_state_reserve_bytes=cfg['storage']['final_state_reserve_bytes'],
        full_PSF_retained_remote=True,no_time_or_extrema_decimation=True)
    encoded=(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    budget=collection_budget(run,out,cfg,len(encoded))
    native.write_new(os.path.join(out,'result.json'),result)
    print('STANDARD_STORAGE_NATIVE_COMPLETE',result['native_points'],
          'hold',result['storage_observations']['stable_hold_observation_pass'],
          'edge_patterns',result['storage_observations']['clean_expected_Q_edge_patterns'],
          'physical',result['physical_terminal_screen_pass'],
          'collection_bytes',budget['projected_bytes'],'whole_ADC_unqualified')


if __name__=='__main__':main()
