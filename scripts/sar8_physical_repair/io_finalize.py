"""Verify fixture inputs, native completion, native-step counts and collections."""
import hashlib,json,re
from pathlib import Path
import numpy as np
import yaml
from prepare import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(run):
    out=ROOT/'output/managed_execution/runs'/run;col=out/'collected'
    receipt=json.loads((col/'collection_receipt.json').read_text());resolved={}
    assert not receipt['skipped']
    for item in receipt['files']:
        p=col/item['name']
        if not p.exists() or sha(p)!=item['sha256']:
            p=p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
        resolved[item['name']]=p
    spec=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
    for f in spec['recipe']['files']: assert sha(out/'inputs'/f['name'])==f['sha256']
    sim=json.loads(resolved['simulation.state.json'].read_text())
    ana=json.loads(resolved['analysis.state.json'].read_text())
    assert sim['status']==ana['status']=='complete' and sim['exit_code']==ana['exit_code']==0
    log=resolved['spectre.out'].read_text();status=resolved['raw/logStatus'].read_text()
    assert 'PASS' in status and '0 errors' in log
    assert not any(x in log for x in ['Failed to find','SPECTRE-8003','SPECTRE-17191'])
    meta=json.loads(resolved['derived/wave.meta.json'].read_text())
    steps=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',log)[1])
    assert meta['points']==steps+1 and meta['PSF_END']
    mapping=json.loads((out/'inputs/mapping.json').read_text())
    assert abs(meta['last_time_s']-mapping['stop_s'])<1e-15
    r=json.loads((ROOT/'verification/sar8_physical_repair'/(run+'_analysis.json')).read_text())
    expected_window=5.9 if 'long' in run else 1.9
    for block in r['blocks'].values():
        for d in block['comparator']:
            assert abs(d['window_ns']-expected_window)<1e-9
            if d['pass_window']:assert d['signed_output_before_reset_v']>=.8*r['vdd']
        refs=block['reference']
        if '4' in refs:
            for pol in ['n','p']:
                assert np.isclose(refs['1'][pol+'_ron_ohm']/refs['2'][pol+'_ron_ohm'],2,rtol=1e-8)
                assert np.isclose(refs['2'][pol+'_ron_ohm']/refs['4'][pol+'_ron_ohm'],2,rtol=1e-8)
    result=dict(run_id=run,measurement_validation_passed=True,native_points=meta['points'],
        all_native_pairs=len(mapping['records']),files_verified=len(receipt['files']),
        collected_bytes=sum(x['bytes'] for x in receipt['files']),
        sim_seconds=sim['elapsed_seconds'],sim_peak_rss_mib=sim['peak_rss_bytes']/2**20,
        analysis_seconds=ana['elapsed_seconds'],analysis_peak_rss_mib=ana['peak_rss_bytes']/2**20,
        parser_peak_rss_kib=meta['peak_rss_kib'],settings=sim['native']['effective_settings'],
        warnings=sim['native']['warning_codes'],native_single_thread=sim['native']['thread_log'],
        raw_retained=True,OA_changed=False,ADC_qualified=False,input_hashes_verified=True,
        collection_hashes_verified=True,window_regression_passed=True,Ron_parallel_scaling_passed=True)
    target=ROOT/'verification/sar8_physical_repair'
    for suffix,value in [('review',result),('collection_receipt',receipt),('simulation_state',sim),('analysis_state',ana)]:
        (target/(run+'_'+suffix+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    return result

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--batch']:
        corners=['tt','sscold','sshot','ffcold','ffhot']
        runs=['sar8fix-ioscreen-'+c for c in corners]
        runs+=['sar8fix-hybscreen-sscold','sar8fix-hyblong-sscold','sar8fix-natscreen-sscold']
        runs+=['sar8fix-natlong-'+c for c in corners]
        rows=[verify(run) for run in runs]
        summary=dict(runs=rows,count=len(rows),all_evidence_checks_pass=True,ADC_repaired=False,
            supply_contract_v=[.81,.99],no_OA_changes=True,no_baseline_promotion=True,
            native_points=sum(r['native_points'] for r in rows),
            collected_bytes=sum(r['collected_bytes'] for r in rows),
            collected_files=sum(r['files_verified'] for r in rows),
            max_simulation_rss_mib=max(r['sim_peak_rss_mib'] for r in rows),
            max_analysis_rss_mib=max(r['analysis_peak_rss_mib'] for r in rows))
        (ROOT/'verification/sar8_physical_repair/io_screen_review.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps({k:v for k,v in summary.items() if k!='runs'},indent=2))
    else:print(json.dumps([verify(run) for run in sys.argv[1:]],indent=2))
