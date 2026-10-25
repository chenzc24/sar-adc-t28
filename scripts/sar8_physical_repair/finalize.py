"""Verify completed evidence, including versioned mutable-log collection."""
import hashlib,json,re,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2];run=sys.argv[1]
out=ROOT/'output/managed_execution/runs'/run;col=out/'collected'
verify=ROOT/'verification/sar8_physical_repair'
receipt=json.loads((col/'collection_receipt.json').read_text())
resolved={}
for item in receipt['files']:
    p=col/item['name']
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
        p=p.with_name(p.stem+'.'+item['sha256'][:12]+p.suffix)
    assert p.stat().st_size==item['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
    resolved[item['name']]=p
assert not receipt['skipped']
spec=yaml.safe_load((ROOT/'management/runs'/(run+'.yaml')).read_text())
for f in spec['recipe']['files']:
    assert hashlib.sha256((out/'inputs'/f['name']).read_bytes()).hexdigest()==f['sha256']
sim=json.loads(resolved['simulation.state.json'].read_text())
ana=json.loads(resolved['analysis.state.json'].read_text())
assert sim['status']==ana['status']=='complete' and sim['exit_code']==ana['exit_code']==0
r=json.loads((verify/(run+'_analysis.json')).read_text())
log=resolved['spectre.out'].read_text()
steps=int(re.search(r'Number of accepted tran steps\s*=\s*(\d+)',log)[1])
assert r['meta']['native_points']==steps+1 and r['meta']['PSF_END']
assert len(json.loads((out/'inputs/mapping.json').read_text())['records'])==10998
assert abs(r['groups']['reference']['peak_v']-(.99-r['BP7_min_v']))<1e-12
assert r['all_codes_pass'] and r['all_event_counts_pass']
assert 'nodes 1609' in log
assert r['native_CMI_present'] and r['groups']['reference']['exceed']
for name,value in [('collection_receipt',receipt),('simulation_state',sim),('analysis_state',ana)]:
    (verify/(run+'_'+name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
v=dict(measurement_validation_passed=True,circuit_stress_passed=False,
    input_hashes_verified=True,collected_files_verified=len(receipt['files']),
    native_steps=steps,native_points=r['meta']['native_points'],
    exact_all_MOS_peak_screen=True,final_exact_timing_qualification=False,
    nodes=1609,MOS=1833,code_and_event_checks=True,reference_peak_extrema_crosscheck=True,
    native_DC_tolerance_relaxation_warning='SPECTRE-17191' in log,
    raw_retained=True,baseline_not_promoted=True,OA_changed=False,
    figure_review='Three panels visually reviewed; BP3 includes subsequent reset stages; negative-region zoom explicit in axes')
(verify/(run+'_review.json')).write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v,indent=2))
