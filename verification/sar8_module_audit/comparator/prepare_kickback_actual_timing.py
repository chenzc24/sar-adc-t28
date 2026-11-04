"""Local measured-interval proposal from frozen N4/rx2 TT native events."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re

from build_kickback_fixture import exact,js,sha
from prepare_kickback_savefix import validate_saves

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'generated/kickback_hold2_v1'
DEST=HERE/'generated/kickback_actual_tt_v1'
TIMING_RUN='sar8fix-loaded-both-rx2-tt'
EVENT_SHA='9a03b81c49ffa76008aa444656038e0be0644d659a513218d2dd9b0d341cc649'
DUT_SHA='c10982b40a9cf4a8aa861852f454b2a26e45ca0988fecd9a26f83c617887cd36'
TIMING_RECIPE='ba8432cd1e6678c1c00f7888982b8511e29424b34c7981159be511fa3a8d3557'


def source_evidence():
    folder=ROOT/'output/managed_execution/runs'/TIMING_RUN
    receipt_bytes=(folder/'collected/collection_receipt.json').read_bytes();receipt=json.loads(receipt_bytes)
    if receipt['status']['run_id']!=TIMING_RUN or receipt['status']['registered']['recipe_hash']!=TIMING_RECIPE:
        raise ValueError('Wrong frozen timing source')
    inputs=[]
    def checked(name):
        entry=next(x for x in receipt['files'] if x['name']==name)
        path=folder/'collected'/name
        if not path.exists() or sha(path.read_bytes())!=entry['sha256']:
            path=path.with_name(path.stem+'.'+entry['sha256'][:12]+path.suffix)
        blob=path.read_bytes()
        if len(blob)>4*1024**2 or len(blob)!=entry['bytes'] or sha(blob)!=entry['sha256']:raise ValueError('Timing evidence mismatch: '+name)
        inputs.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(blob),bytes=len(blob)))
        return blob
    for phase in ['simulation','analysis']:
        state=json.loads(checked(phase+'.state.json'))
        if state['status']!='complete' or state['exit_code']!=0:raise ValueError('Timing source incomplete')
        if phase=='simulation' and not all(state['native'][k] for k in ['native_analysis_pass','zero_error_footer']):raise ValueError('Native source incomplete')
    events=checked('derived/wave.events.tsv')
    if sha(events)!=EVENT_SHA:raise ValueError('Source is not the frozen native event table')
    dut=(folder/'inputs/dut.scs').read_bytes()
    if sha(dut)!=DUT_SHA:raise ValueError('Timing source is not the frozen N4/rx2 DUT')
    rows=[line.split() for line in events.decode().splitlines() if line.strip()]
    rises=[float(at) for node,up,at in rows if node=='xdut.cmp_clk' and up=='1']
    falls=[float(at) for node,up,at in rows if node=='xdut.cmp_clk' and up=='0']
    pairs=[]
    for frame in [0,1]:
        rr=[t for t in rises if frame*100e-9<=t<(frame+1)*100e-9]
        ff=[t for t in falls if frame*100e-9<=t<(frame+1)*100e-9]
        if len(rr)!=8 or len(ff)!=8:raise ValueError('Expected8 native compare/reset cycles per source frame')
        for i in range(7):
            if not rr[i]<ff[i]<rr[i+1]<ff[i+1]:raise ValueError('Non-alternating source clock')
            pairs.append(dict(frame=frame,from_bit=7-i,to_bit=6-i,
                rise1_s=rr[i],fall1_s=ff[i],rise2_s=rr[i+1],fall2_s=ff[i+1],
                rise_interval_s=rr[i+1]-rr[i],high1_s=ff[i]-rr[i],low_s=rr[i+1]-ff[i],high2_s=ff[i+1]-rr[i+1]))
    shortest=min(pairs,key=lambda p:p['rise_interval_s'])
    minimum_low=min(pairs,key=lambda p:p['low_s'])
    estimate_path=ROOT/'verification/sar8_physical_repair'/ (TIMING_RUN+'_analysis.json')
    estimates=json.loads(estimate_path.read_bytes())
    if sha(estimate_path.read_bytes())!='4219071e5fc80677a519ad0d964fe3325fd0a676e870db940191463ba4407c40':raise ValueError('Frozen source context changed')
    context=[dict(bit=7-c['decision'],preclock_diff_mv_compact_estimate=c['preclock_diff_mv'],
                  source_write_delay_ns=c['write_ns']-c['clock_ns'])
             for c in estimates['comparisons'] if c['frame']==shortest['frame'] and c['decision'] in [7-shortest['from_bit'],7-shortest['to_bit']]]
    return dict(source_run=TIMING_RUN,source_recipe_sha256=TIMING_RECIPE,source_DUT_sha256=DUT_SHA,
        receipt_sha256=sha(receipt_bytes),consumed_files=inputs,source_conditions=dict(corner='TT',vdd_v=.9,temperature_c=27),
        event_evidence='0.5VDD crossings interpolated between original native simulator points, not compact waveform crossings',
        adjacent_pairs=pairs,selected_shortest_rise_interval=shortest,minimum_low_different_pair=minimum_low,
        selected_source_inputs_context=context,context_evidence='Existing20ps compact voltage estimates; not used to derive clock times',
        scope='Minimum among14 adjacent pairs in two recorded TT frames, not a global PVT/input bound')


def clock_replay(text,pair):
    match=re.search(r'(?m)^VCMP_CLK \(CMP_CLK 0\) vsource type=pwl wave=\[([^\]]+)\]$',text)
    if match is None:raise ValueError('Expected original diagnostic clock source')
    tokens=match[1].split();old=list(zip(tokens[::2],tokens[1::2]))
    later=[p for p in old if p[0].endswith('n') and float(p[0][:-1])>=100]
    rise1=20.05e-9;fall1=rise1+pair['high1_s'];rise2=rise1+pair['rise_interval_s'];fall2=rise2+pair['high2_s']
    half=.05e-9
    points=[('0n','0'),('20n','0'),('20.1n','SUP')]
    fmt=lambda t:format(t*1e9,'.17g')+'n'
    points += [(fmt(fall1-half),'SUP'),(fmt(fall1+half),'0'),
               (fmt(rise2-half),'0'),(fmt(rise2+half),'SUP'),
               (fmt(fall2-half),'SUP'),(fmt(fall2+half),'0')]+later
    replacement=' '.join(token for p in points for token in p)
    deck=text[:match.start(1)]+replacement+text[match.end(1):]
    edges=dict(rise1_half_s=rise1,fall1_half_s=fall1,rise2_half_s=rise2,fall2_half_s=fall2,
        rise2_start_s=rise2-half,fall1_start_s=fall1-half,fall1_end_s=fall1+half,
        fall2_start_s=fall2-half,fall2_end_s=fall2+half,
        fixture_zero_to_next_rise_start_s=(rise2-half)-(fall1+half),ideal_ramp_s=.1e-9)
    return deck,edges


def analyzer_copy(blob):
    text=blob.decode()
    replacements=[("if c['start_s']<=t<=c['start_s']+12e-9:","if c['start_s']<=t<=c['clock_fall_start_s']:"),
        ("if cycle['raw_resolution'] is None and abs(difference)>=.5*v['vdd!']:",
         "if cycle['raw_resolution'] is None and t<c['clock_fall_start_s'] and abs(difference)>=.5*v['vdd!']:"),
        ("if c['start_s']<=at<c['clock_fall_end_s']:cycle['writes'].append(event)",
         "if c['start_s']<=at<c['clock_fall_end_s']:\n                                    event['phase']='before_reset' if at<c['clock_fall_start_s'] else 'clock_fall'\n                                    cycle['writes'].append(event)"),
        ("        for k in ['last_phase_t','last_phase_i']:cycle.pop(k)",
         "        cycle['writes_before_reset']=[e for e in cycle['writes'] if e['phase']=='before_reset']\n"
         "        cycle['nominal_polarity_written_before_reset']=(len(cycle['writes_before_reset'])==1 and cycle['writes_before_reset'][0]['DATA_bit']==c['expected_DATA'])\n"
         "        cycle['missing_write_before_reset']=not cycle['writes_before_reset']\n"
         "        cycle['raw_resolution_scope']='Before the explicit clock fall starts only'\n"
         "        for k in ['last_phase_t','last_phase_i']:cycle.pop(k)"),
        ("        extrema=stats,node_kcl=kcl_stats,full_native_signed_charge_C=full_charge,",
         "        unassigned_write_events=[e for e in all_events if e['kind']=='write' and not any(c['configuration']['start_s']<=e['estimated_half_vdd_time_s']<c['configuration']['clock_fall_end_s'] for c in cycles)],\n"
         "        actual_interval_replay=cfg['actual_interval_replay'],\n"
         "        extrema=stats,node_kcl=kcl_stats,full_native_signed_charge_C=full_charge,"),
        ("raw_resolution='First native point with abs(COMP_P-COMP_N)>=0.5VDD; not interpolated and not a qualified decision deadline'",
         "raw_resolution='First native threshold sample before explicit clock fall; missing/late resolution retained, not qualification'"),
        ("clock='Original D2 ideal 0.1ns edges and12ns high window; reset reference arm stays low'",
         "clock='Measured native half-level intervals for first two pulses, original0.1ns ideal ramps; four later pulses remain long controls'")]
    for old,new in replacements:
        if text.count(old)!=1:raise ValueError('Unexpected frozen analyzer structure')
        text=text.replace(old,new)
    return text.encode()


def prepare():
    manifest=json.loads((SOURCE/'manifest.json').read_bytes())
    for name,h in manifest['input_hashes'].items():
        if sha((SOURCE/name).read_bytes())!=h:raise ValueError('Frozen hold2 payload changed: '+name)
    evidence=source_evidence();pair=evidence['selected_shortest_rise_interval']
    recipe=json.loads((SOURCE/'recipe_proposal.json').read_bytes())
    payload={e['name']:(SOURCE/e['name']).read_bytes() for e in recipe['inputs']}
    deck,edges=clock_replay(payload['test.scs'].decode(),pair);payload['test.scs']=deck.encode()
    payload['kickback_analyze.py']=analyzer_copy(payload['kickback_analyze.py'])
    compile(payload['kickback_analyze.py'],'actual_interval_analyzer','exec')
    cfg=json.loads(payload['measurement.json'])
    for c in cfg['cycles']:c['clock_fall_start_s']=c['start_s']+12e-9
    cfg['cycles'][0].update(clock_fall_start_s=edges['fall1_start_s'],clock_fall_end_s=edges['fall1_end_s'])
    cfg['cycles'][1].update(start_s=edges['rise2_start_s'],clock_fall_start_s=edges['fall2_start_s'],clock_fall_end_s=edges['fall2_end_s'])
    cfg['actual_interval_replay']=dict(source_run=TIMING_RUN,source_pair=pair,fixture_edges=edges,
        affected_cycle_indices=[0,1],later_cycles='Original long-interval +/-0.25LSB controls, not short-negative-input qualification',
        edge_shape='Original0.1ns ideal ramps retained; this replays native0.5VDD intervals, not the full native clock voltage waveform',
        source_input_context=evidence['selected_source_inputs_context'],
        interpretation='Source asynchronous pulses were produced with large input residues. Applying them to fixed+0.25LSB may force reset before completion; missing/late write is not automatically an async SAR defect.',
        CDAC_boundary='Bottoms fixed; no reference update/capture switching; no actual clock/DEC feedback; not a complete SAR bit sequence')
    cfg['diagnostic_history']['phase_note']='First two comparisons now use the selected measured half-level intervals; use explicit fall-start/end fields, not20/60ns or a12ns high assumption.'
    cfg['scope']='TT measured-minimum-interval comparator/CDAC diagnostic; conditional forced-clock test, not full SAR qualification'
    cfg['required_input_sha256']={name:sha(payload[name]) for name in cfg['required_input_sha256']}
    payload['measurement.json']=js(cfg).encode()
    for name,blob in payload.items():exact(DEST/name,blob)
    check=validate_saves(DEST,cfg)
    recipe.update(run_id='sar8audit-comp-actual-tt-v1',design_id='sar8_comp_actual_interval_tt_v1',qualification_scope=cfg['scope'])
    recipe['inputs']=[dict(name=name,source=(DEST/name).relative_to(ROOT).as_posix(),sha256=sha(blob)) for name,blob in payload.items()]
    recipe['test_conditions']['clock']='First pair: native shortest TT rise-to-rise intervals; original0.1ns ideal ramp shape'
    exact(DEST/'recipe_proposal.json',js(recipe));exact(DEST/'timing_source.json',js(evidence))
    exact(DEST/'manifest.json',js(dict(status='local_only_not_Spectre_compiled',parent_run='sar8audit-comp-hold2-tt-v1',
        parent_recipe_sha256='0ed949bb4dbf5cf206e928d2d27642530e91806146ef6647882d727e992d9737',
        parent_input_hashes=manifest['input_hashes'],input_hashes={n:sha(b) for n,b in payload.items()},
        clock_edges=edges,save_symbols=check,input_bytes=sum(len(b) for b in payload.values()),
        unchanged_hardware_inputs=['cells.scs','cdac_load.scs','initializer.va'],
        analyzer_changes='Explicit fall-start late-D0/raw-resolution boundary; writes classified before/reset and absence is not success',
        remote_submitted=False,baseline_adopted=False,acceptance_pass=None,builder_sha256=sha(Path(__file__).read_bytes()))))
    print('LOCAL_ACTUAL_INTERVAL',recipe['run_id'],'period_ns',pair['rise_interval_s']*1e9,
          'low_half_ns',pair['low_s']*1e9,'input_bytes',sum(len(b) for b in payload.values()))


if __name__=='__main__':prepare()
