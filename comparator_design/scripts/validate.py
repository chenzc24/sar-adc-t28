"""Check provenance and completeness; explicitly separate data checks from circuit pass."""
import hashlib,json
from setup import W,ROOT,write
from report import RUNS,load

provenance=json.loads((W/'baseline/provenance.json').read_text())
source_checks={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in provenance.items()}
assert all(source_checks.values()),'Read-only source changed; review before accepting provenance'
records=[];points=0;all_function=True;all_electrical=True
for label,run in RUNS:
    data=load(run)
    assert data['native_state']['zero_error_footer'] and data['native_state']['native_exit']==0
    for key,r in data['contexts'].items():
        assert len(r['rows'])==32 and len(r['terminal_pairs'])==15*6
        assert all(row['pre_eval_diff_V'] is not None and row['residual_before_reset_V'] is not None and row['internal_reset_max_error_V'] is not None for row in r['rows'])
        points+=32;all_function=all_function and r['all_correct'] and r['all_reset']
        all_electrical=all_electrical and all(r['screens'].values())
    records.append({'condition':label,'run_id':run,'source_run_id':data['source_run_id'],'native_points':data['native_points'],'warnings':data['native_state']['warning_codes']})
resources=[]
for folder in (W/'results').iterdir():
    if not folder.is_dir():continue
    for stage,budget in [('simulation',1024*2**20),('analysis',256*2**20)]:
        p=folder/(stage+'.state.json')
        if p.exists():
            s=json.loads(p.read_text());assert s['status']=='complete' and s['exit_code']==0
            assert s.get('peak_rss_bytes',0)<=budget
            resources.append({'run_id':folder.name,'stage':stage,'peak_rss_bytes':s.get('peak_rss_bytes'),'elapsed_s':s.get('elapsed_seconds')})
zoom=load('cmpdesign-worst-terminal-zoom-v1');assert zoom['peak_verified'] and not zoom['decimation']
out={'source_unchanged':source_checks,'data_integrity_pass':True,'evaluations_unique':points,'deterministic_polarity_and_reset_pass':all_function,
     'all_screens_pass':all_electrical,'comparator_qualified':False,'remaining':['FF terminal stress','short reset / threshold history','noise','mismatch / offset','real receiver and CDAC interface'],
     'runs':records,'resources':resources,'native_zoom':zoom,
     'figures_reviewed':['tt_size_tradeoff.png','tt_decision_waveform.png','five_point_screen.png','worst_terminal_waveform.png']}
write(W/'validation.json',json.dumps(out,indent=2)+'\n')
print(json.dumps({'data_integrity_pass':True,'evaluations_unique':points,'all_screens_pass':all_electrical,
                  'max_simulation_rss_MiB':max(r['peak_rss_bytes']/2**20 for r in resources if r['stage']=='simulation'),
                  'max_analysis_rss_MiB':max(r['peak_rss_bytes']/2**20 for r in resources if r['stage']=='analysis')},indent=2))
