"""One finite serial batch: inspect low codes, then conditionally finish TT static.

This is not a scheduled automation. Unknown/failed state stops without retrying.
"""
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/sar8_frozen_static'
VERIFY=ROOT/'verification/sar8_frozen_static'


def save(path,obj):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)


def call(*args):
    p=subprocess.run([sys.executable,str(ROOT/'scripts/management/project.py')]+list(args),
        cwd=str(ROOT),capture_output=True,text=True,timeout=240)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return json.loads(p.stdout)


def state(**data):
    data.update(epoch=time.time(),pid=os.getpid())
    save(OUT/'flow_status.json',data)
    print(json.dumps(data),flush=True)


def finish(run):
    for phase,command in [('simulation','submit'),('analysis','analyze')]:
        s=call('run-status',run)
        if s[phase]['status']=='not_started':call(command,run,'--queue')
        while True:
            s=call('run-status',run); st=s[phase]['status']
            state(run_id=run,stage=phase,status=st,detail=s[phase])
            if st=='complete':break
            if st not in ['running','queued','starting','submitted','waiting']:
                raise RuntimeError('Terminal or uncertain state: '+json.dumps(s))
            time.sleep(30)
    receipt=call('collect',run)
    assert not receipt.get('skipped'), 'Collection incomplete'
    p=ROOT/receipt['local_path']/'derived/result.json'
    result=json.loads(p.read_text())
    save(VERIFY/run/'result.json',result)
    state(run_id=run,stage='reviewed',functional_pass=result['functional_pass'],centers=result['centers'],
        startup_codes=[r['code'] for r in result['startup_frames']])
    assert result['analysis_complete'] and result['native_decode_crosscheck']
    assert result['functional_pass'], 'Measured functional failure; stop further cases'
    return result


def aggregate(results):
    thresholds=[t for r in results for t in r['thresholds']]
    assert [t['k'] for t in thresholds]==list(range(1,256))
    codes={c['expected']:c['code'] for r in results for c in r['centers']}
    assert codes==dict((k,k) for k in range(256))
    # Repeated seam centers must agree too, not merely the final dictionary entry.
    assert all(c['expected']==c['code'] for r in results for c in r['centers'])
    lo=[t['lower_v'] for t in thresholds];hi=[t['upper_v'] for t in thresholds]
    assert all(a<b for a,b in zip(hi,lo[1:])), 'Cross-segment monotonicity'
    mid=[(a+b)/2 for a,b in zip(lo,hi)];lsb=1.8/256;ep=(mid[-1]-mid[0])/254
    dnl=[(b-a)/lsb-1 for a,b in zip(mid,mid[1:])]
    raw=[(v-(-.9+(i+1)*lsb))/lsb for i,v in enumerate(mid)]
    endpoint=[(v-(mid[0]+i*ep))/ep for i,v in enumerate(mid)]
    obj=dict(complete=True,design_id='sar8_l90_mmain2_frozen',runs=[r['context']['run_id'] for r in results],
        thresholds=thresholds,code_coverage=256,boundary_count=255,missing_center_codes=[],
        max_bracket_width_lsb=max(b-a for a,b in zip(lo,hi))/lsb,dnl_nominal_lsb=dnl,
        dnl_min_lsb=min(dnl),dnl_max_lsb=max(dnl),inl_raw_lsb=raw,inl_endpoint_lsb=endpoint,
        inl_raw_abs_max_lsb=max(map(abs,raw)),inl_endpoint_abs_max_lsb=max(map(abs,endpoint)),
        offset_v=mid[0]-(-.9+lsb),endpoint_gain_error_percent=(ep/lsb-1)*100,
        dnl_lower_bound_lsb=[(b-a)/lsb-1 for a,b in zip(hi,lo[1:])],
        dnl_upper_bound_lsb=[(b-a)/lsb-1 for a,b in zip(lo,hi[1:])],
        max_conversion_ns=max(r['max_conversion_ns'] for r in results),
        electrical_verdict='deferred_not_qualified',conditions=results[0]['context'],
        scope='TT segmented static; startup separate; no noise/mismatch/PEX/FFT')
    save(VERIFY/'results.json',obj)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # Do not permit another local flow to race this finite submission sequence.
    with (OUT/'flow.lock').open('x') as f:f.write(str(os.getpid()))
    jobs=json.loads((VERIFY/'batch.json').read_text())['runs']
    results=[]
    for i,run in enumerate(jobs):
        if not (ROOT/'management/runs'/(run+'.yaml')).exists():
            call('register','management/recipes/'+run+'.yaml')
        results.append(finish(run))
        if i==0:
            save(VERIFY/'low_code_review.json',dict(functional_pass=True,source_run=run,
                centers=results[0]['centers'],thresholds=results[0]['thresholds'],
                startup_frames=results[0]['startup_frames'],full_code_authorized_by_low_code_pass=True,
                electrical_verdict='deferred_not_qualified'))
    aggregate(results)
    state(stage='complete',runs=jobs,result='verification/sar8_frozen_static/results.json')


if __name__=='__main__':
    try:main()
    except Exception:
        state(stage='failed',error=traceback.format_exc())
        raise
