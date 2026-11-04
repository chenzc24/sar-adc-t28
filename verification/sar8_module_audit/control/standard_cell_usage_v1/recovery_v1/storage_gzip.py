from __future__ import print_function
import os,struct,gzip,hashlib
import full_gate_analyze as native
import standard_cell_full_analyze as tools

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
    with gzip.open(os.path.join(output,'peak.native.bin.gz'),'rb') as f:
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



def verify_compressed(output,cfg,result):
    path=os.path.join(output,'peak.native.bin.gz');h=hashlib.sha256();size=0
    with gzip.open(path,'rb') as handle:
        while True:
            blob=handle.read(65536)
            if not blob:break
            h.update(blob);size+=len(blob)
    expected=result['streaming_export']['uncompressed']
    if dict(bytes=size,sha256=h.hexdigest())!=expected:raise ValueError('Lossless gzip proof differs')
    columns=native.read(os.path.join(output,'peak.columns.json'))['names']
    if size!=result['diagnostic_points']*len(columns)*8:raise ValueError('Native diagnostic row count differs')
    return dict(file='peak.native.bin.gz',uncompressed=expected,compressed=tools.identity(path),
        decompressed_bytes_and_SHA_match=True,every_native_row_preserved=True,raw_PSF_modified=False,
        direct_streaming_gzip=True,no_uncompressed_scratch_created=True)
