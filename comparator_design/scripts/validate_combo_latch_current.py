"""Independent frozen-input, connectivity, raw peak and current verification."""
import ast,csv,gzip,json,re
import numpy as np
from setup import W,ROOT,write

run='cmpdesign-combo-latch-current-ff-hot-v2';source='cmpdesign-edge-b2i2-ff-hot-v1'
new=W/'testbenches'/run;old=W/'testbenches'/source
for n in ['dut.scs','models.scs']:assert (new/n).read_bytes()==(old/n).read_bytes()
def strip_obs(text):
    return re.sub(r'stop=\S+','stop=OBSERVATION',re.sub(r'^save .*\n','',text,flags=re.M))
assert strip_obs((new/'test.scs').read_text())==strip_obs((old/'test.scs').read_text())
cfg=json.loads((new/'measure.json').read_text());native=json.loads((W/'results'/run/'result.json').read_text())
attr=json.loads((W/'results/combo_latch_attribution.json').read_text())
assert not native['missing_optional_fields']
baseline={w['tag']:[] for w in cfg['windows']}
with gzip.open(ROOT/'output/managed_execution/runs'/source/'collected/derived/wave.csv.gz','rt') as f:
    for row in csv.DictReader(f):
        t=float(row['time'])
        for w in cfg['windows']:
            if w['window_s'][0]<=t<=w['window_s'][1]:baseline[w['tag']].append((t,float(row[w['target'].lower()])))
tests=[];body=(new/'dut.scs').read_text()
for w,result,a in zip(cfg['windows'],native['windows'],attr):
    with gzip.open(ROOT/'output/managed_execution/runs'/run/'collected/derived'/(w['tag']+'.csv.gz'),'rt') as f:rows=list(csv.DictReader(f))
    ts=np.array([float(r['time']) for r in rows]);vs=np.array([float(r[w['target'].lower()]) for r in rows]);i=int(np.argmax(vs))
    b=max(baseline[w['tag']],key=lambda x:x[1]);dv=vs[i]-b[1];dt=ts[i]-b[0]
    assert abs(dv)<1e-7 and abs(dt)<1e-12,(w['tag'],dv,dt)
    ports=[p['signal'].lower() for p in w['branches']]
    kcl=max(abs(sum(float(r[p]) for p in ports)) for r in rows);assert kcl<1e-15
    # Count every connected terminal directly from the frozen netlist.
    connected={(dev,'DGSB'[i]) for dev,nodes in re.findall(r'^(M\d+) \(([^)]+)\)',body,re.M) for i,n in enumerate(nodes.split()) if n==w['target'].split('.')[-1]}
    assert connected=={(b['device'],b['terminal']) for b in w['branches']}
    left=right=i
    while left>0 and vs[left-1]>.99:left-=1
    while right+1<len(vs) and vs[right+1]>.99:right+=1
    start=ts[left-1]+(ts[left]-ts[left-1])*(.99-vs[left-1])/(vs[left]-vs[left-1])
    end=ts[right]+(ts[right+1]-ts[right])*(.99-vs[right])/(vs[right+1]-vs[right])
    assert abs(a['duration_s']-(end-start))<1e-18
    assert abs((end-start)-w['source_pulse']['duration_s'])<1e-12
    gate_checks=[dict(device=b['device'],error_fC=b['phase']['above_to_peak']['gate_Q_error_fC'],into_fC=b['phase']['above_to_peak']['into_fC']) for b in a['branches'] if b['terminal']=='G']
    for b in a['branches'][:2]:
        p=b['phase']['above_to_peak']
        assert b['terminal']=='G' and abs(p['gate_Q_error_fC']/p['into_fC'])<.001
        assert p['gate_leak_peak_A']<2e-12
    p=a['branches'][2]['phase']['above_to_peak']
    assert a['branches'][2]['terminal']=='D' and abs(p['id_q_reconstruction_error_fC'])<1e-6
    tests.append(dict(tag=w['tag'],peak_difference_V=float(dv),peak_time_difference_s=float(dt),kcl_max_A=kcl,above_start_s=float(start),above_end_s=float(end),above_duration_s=float(end-start),window_points=len(rows),gate_checks=gate_checks))
for n in ['prepare_combo_latch_current','prepare_combo_latch_current_v2','review_combo_latch_current','validate_combo_latch_current','run']:
    ast.parse((W/'scripts'/(n+'.py')).read_text(encoding='utf-8'))
logs=(W/'results'/run/'spectre.out').read_text(errors='replace')
warnings=sorted(set(re.findall(r'(?:CMI|SFE|SPECTRE)-\d+',logs)))
states={n:json.loads((W/'results'/run/(n+'.state.json')).read_text()) for n in ['simulation','analysis']}
for s in states.values():assert s['exit_code']==0 and s['status']=='complete'
for left,right in zip(attr[0]['branches'],attr[1]['branches']):
    assert abs(left['phase']['above_to_peak']['into_fC']-right['phase']['above_to_peak']['into_fC'])<1e-9
assert native['native_state']['zero_error_footer']
write(W/'results/combo_latch_validation.json',json.dumps(dict(run_id=run,only_save_and_stop_changed=True,identity_pass=True,original_voltage_reproduction=tests,warnings=warnings,states=states),indent=2)+'\n')
print(json.dumps(dict(warnings=warnings,checks=tests),indent=2))
