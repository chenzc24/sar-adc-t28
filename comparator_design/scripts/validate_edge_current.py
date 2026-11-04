"""Independent source identity, KCL, original voltage reproduction and charge checks."""
import ast,csv,gzip,json,re
from pathlib import Path
import numpy as np
from setup import W,ROOT,write

run='cmpdesign-edge-current-a4-ff-hot-v1';source='cmpdesign-r200-f500-a4-ff-hot-v1'
new=W/'testbenches'/run;old=W/'testbenches'/source
for n in ['dut.scs','models.scs']:assert (new/n).read_bytes()==(old/n).read_bytes()
original=(old/'test.scs').read_text();actual=(new/'test.scs').read_text()
assert actual.splitlines()[:-1]==original.replace('stop=400n','stop=85n').splitlines()
assert actual.splitlines()[-1].startswith('save ')
cfg=json.loads((new/'measure.json').read_text());native=json.loads((W/'results'/run/'result.json').read_text())
assert not native['missing_optional_fields']
baseline={w['tag']:[] for w in cfg['windows']}
with gzip.open(ROOT/'output/managed_execution/runs'/source/'collected/derived/wave.csv.gz','rt') as f:
    for r in csv.DictReader(f):
        t=float(r['time'])
        for w in cfg['windows']:
            if w['window_s'][0]<=t<=w['window_s'][1]:baseline[w['tag']].append((t,float(r[w['target'].lower()])))
tests=[]
for w,result in zip(cfg['windows'],native['windows']):
    with gzip.open(ROOT/'output/managed_execution/runs'/run/'collected/derived'/(w['tag']+'.csv.gz'),'rt') as f:rows=list(csv.DictReader(f))
    ts=np.array([float(r['time']) for r in rows]);vs=np.array([float(r[w['target'].lower()]) for r in rows]);i=int(np.argmax(vs))
    b=max(baseline[w['tag']],key=lambda x:x[1])
    dv=vs[i]-b[1];dt=ts[i]-b[0]
    assert abs(dv)<1e-7 and abs(dt)<1e-12,(w['tag'],dv,dt)
    ports=[s['signal'].lower() for s in w['branches']]
    kcl=max(abs(sum(float(r[p]) for p in ports)) for r in rows)
    assert kcl<1e-15
    # Check reported connections directly against DUT text.
    body=(new/'dut.scs').read_text()
    for branch in w['branches']:
        line=re.search(r'^'+branch['device']+r' \(([^)]+)\)',body,re.M).group(1).split()
        assert line['DGSB'.index(branch['terminal'])]==w['target'].split('.')[-1]
    ix=i
    while ix>0 and vs[ix-1]>.99:ix-=1
    j=i
    while j+1<len(vs) and vs[j+1]>.99:j+=1
    start=ts[ix-1]+(ts[ix]-ts[ix-1])*(.99-vs[ix-1])/(vs[ix]-vs[ix-1])
    end=ts[j]+(ts[j+1]-ts[j])*(.99-vs[j])/(vs[j+1]-vs[j])
    tests.append(dict(tag=w['tag'],peak_difference_V=float(dv),peak_time_difference_s=float(dt),kcl_max_A=kcl,above_start_s=float(start),above_end_s=float(end),above_duration_s=float(end-start),window_points=len(rows)))
for n in ['prepare_edge_current','edge_current_reduce','review_edge_current','validate_edge_current']:
    ast.parse((W/'scripts'/(n+'.py')).read_text())
logs=(W/'results'/run/'spectre.out').read_text(errors='replace')
warnings=sorted(set(re.findall(r'(?:CMI|SFE|SPECTRE)-\d+',logs)))
states={n:json.loads((W/'results'/run/(n+'.state.json')).read_text()) for n in ['simulation','analysis']}
for n,s in states.items():assert s['exit_code']==0
write(W/'results/edge_current_validation.json',json.dumps(dict(run_id=run,only_save_and_stop_changed=True,identity_pass=True,original_voltage_reproduction=tests,warnings=warnings,states=states),indent=2)+'\n')
print(json.dumps(dict(warnings=warnings,checks=tests),indent=2))
