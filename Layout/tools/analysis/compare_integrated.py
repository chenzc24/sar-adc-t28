"""Compare the collected full-ADC/CDAC-PEX short test with measured B evidence."""
import argparse,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(data):
    frames=data['frames']
    tails=[(r['frame'],t) for r in frames for t in r['dac_tail_diagnostics']]
    slow=max(tails,key=lambda pair:pair[1]['settling_after_update_ps']) if tails else None
    quiet=min(tails,key=lambda pair:pair[1]['quiet_margin_ps']) if tails else None
    conversions=[r['conversion_ns'] for r in frames if r.get('conversion_ns') is not None]
    pin_errors=[abs(r['preclose_error_pin_v'])/data['context']['LSB'] for r in frames
                if r.get('preclose_error_pin_v') is not None]
    return dict(codes=[r['code_98'] for r in frames],
                all_code_pass=data['all_code_pass'],startup_code_pass=data['startup_code_pass'],
                all_timing_pass=all(r['timing_pass'] and r['count_crosscheck'] for r in frames),
                conversion_ns_range=[min(conversions),max(conversions)] if conversions else None,
                measured_conversion_frames=len(conversions),
                worst_tail=dict(frame=slow[0],**slow[1]) if slow else None,
                minimum_quiet_margin=dict(frame=quiet[0],**quiet[1]) if quiet else None,
                max_preclose_pin_error_lsb=max(pin_errors) if pin_errors else None,
                warning_codes=data['warning_codes'])


def main():
    p=argparse.ArgumentParser();p.add_argument('run_id');p.add_argument('--analysis-run-id');a=p.parse_args()
    run=ROOT/'work/output/managed_execution/runs'/(a.analysis_run_id or a.run_id)
    path=run/'collected/derived/result.json'
    baseline=ROOT/'results/migration/original_short.json'
    before=json.loads(baseline.read_text());after=json.loads(path.read_text())
    if after.get('context',{}).get('prelayout_design_id'):
        raise ValueError('This historical B comparison cannot score a current-design PEX run; use its current handshake result and a matching prelayout identity')
    if a.analysis_run_id:
        provenance=json.loads((run/'collected/source_provenance.json').read_text())
        assert provenance['run_id']==a.run_id
    assert after['context']['run_id']==a.run_id and after['context']['pex_modules']==['cdac']
    assert before['context']['expected_codes']==after['context']['expected_codes']
    assert len(before['frames'])==len(after['frames'])==10
    frames=[]
    for old,new in zip(before['frames'],after['frames']):
        row={k:new.get(k) for k in ['frame','expected_code','code_90','code_98','code_pass','counts','observer_counts',
                               'count_crosscheck','ordered_8_cycles','timing_pass','output_stable_90_98','conversion_ns']}
        row.update(prelayout_code=old['code_98'],conversion_delta_ps=
                   1000*(new['conversion_ns']-old['conversion_ns']) if new.get('conversion_ns') is not None else None)
        for name in ['external_close_s','sample_int_close_s','seq_sample_close_s']:
            row[name]={'before':old[name],'after':new[name],
                       'delta_ps':(new[name][0]-old[name][0])*1e12 if len(new[name])==len(old[name])==1 else None}
        row['acquisition_error_pin_lsb']=(new['preclose_error_pin_v']/after['context']['LSB']
                                          if new.get('preclose_error_pin_v') is not None else None)
        row['dac_tail_diagnostics']=new['dac_tail_diagnostics']
        frames.append(row)
    report=dict(run_id=a.run_id,analysis_run_id=a.analysis_run_id or a.run_id,
                baseline_source=before.get('source_run_dir',before['context']['run_id']),
                baseline_result_sha256=digest(baseline),result_sha256=digest(path),
                physical_evidence=after['context']['physical_evidence'],gds_sha256=after['context']['gds_sha256'],
                missing_optional_precharge_signals=after.get('missing_optional_precharge_signals',[]),
                before=summarize(before),after=summarize(after),frames=frames,
                limits=after['limitations']+['Only CDAC is extracted; all other ADC modules remain pre-layout.',
                       'Ten TT frames do not establish full-code linearity, PVT, mismatch or reliability signoff.',
                       'The tail target is the measured value 20ps before comparison, not an independent DC reference.'])
    out=ROOT/'work/layout/full-cdac/integrated_comparison.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['run_id','before','after']},indent=2))


if __name__=='__main__':main()
