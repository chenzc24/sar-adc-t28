"""Finite metadata coordinator. All heavy work uses the frozen managed agent API."""
from __future__ import print_function
import fcntl,hashlib,imp,json,os,sys,time,traceback
ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
HERE=ROOT+'/campaigns/sar8-functional-20261028/a-companion'
def read(p):
    assert os.path.getsize(p)<16*1024*1024,'Metadata exceeds bound'
    with open(p) as f:return json.load(f)
def write(name,d):
    p=HERE+'/'+name;q=p+'.tmp'
    with open(q,'w') as f:json.dump(d,f,indent=2);f.write('\n')
    os.rename(q,p)
def passed(r):
    return bool(r.get('analysis_complete') and r.get('native_event_code_crosscheck') and
        r.get('startup_code_pass') and r.get('startup_timing_pass') and
        r.get('all_code_pass') and r.get('steady_timing_pass'))
def select(a,b):
    if passed(b):return 'b'
    if passed(a):return 'a'
    raise RuntimeError('Neither phase60 candidate passes first/all codes and timing')
def aggregate(results):
    thresholds=[t for r in results for t in r['thresholds']]
    assert [t['k'] for t in thresholds]==list(range(1,256))
    assert all(r['functional_pass'] for r in results)
    assert all(r['effective_settings']==results[0]['effective_settings'] for r in results)
    centers=[c for r in results for c in r['centers']]
    assert all(c['code']==c['expected'] for c in centers)
    assert set(c['code'] for c in centers)==set(range(256))
    lo=[t['lower_v'] for t in thresholds];hi=[t['upper_v'] for t in thresholds]
    assert all(x<y for x,y in zip(hi,lo[1:])), 'Cross-part boundary overlap'
    mid=[(x+y)/2 for x,y in zip(lo,hi)];lsb=1.8/256;ep=(mid[-1]-mid[0])/254
    dnl=[(y-x)/lsb-1 for x,y in zip(mid,mid[1:])]
    ine=[(v-(mid[0]+i*ep))/ep for i,v in enumerate(mid)]
    return dict(functional_pass=True,context=results[0]['context'],runs=[r['context']['run_id'] for r in results],
        thresholds=thresholds,boundary_count=255,code_coverage=256,missing_center_codes=[],
        dnl_nominal_lsb=dnl,dnl_min_lsb=min(dnl),dnl_max_lsb=max(dnl),saturated_endpoint_widths_excluded=[0,255],
        inl_endpoint_lsb=ine,inl_endpoint_abs_max_lsb=max(map(abs,ine)),offset_v=mid[0]-(-.9+lsb),
        endpoint_gain_error_percent=(ep/lsb-1)*100,max_bracket_width_lsb=max(y-x for x,y in zip(lo,hi))/lsb,
        electrical_verdict='deferred_not_qualified')
def solver_compare(reference,candidate):
    issues=[]
    if not passed(candidate):issues.append('functional_or_timing_failure')
    diffs=[]
    for x,y in zip(reference['frames'],candidate['frames']):
        row=dict(frame=x['frame'])
        if x['code_98']!=y['code_98']:issues.append('code_difference')
        for key in ['sample_int_close_s','seq_sample_close_s','external_close_s']:
            if len(x[key])!=1 or len(y[key])!=1:issues.append('missing_edge');continue
            delta=abs(y[key][0]-x[key][0])*1e12;row[key+'_delta_ps']=delta
            if delta>5:issues.append('aperture_delta_gt5ps')
        for key,limit in [('conversion_ns',.05),('preclose_error_source_v',.02*1.8/256),('preclose_error_pin_v',.02*1.8/256)]:
            if key not in x or key not in y:issues.append('missing_measure');continue
            delta=abs(y[key]-x[key]);row[key+'_delta']=delta
            if delta>limit:issues.append(key+'_delta_exceeds_diagnostic')
        xt=x['dac_tail_diagnostics'];yt=y['dac_tail_diagnostics']
        if len(xt)!=len(yt):issues.append('tail_count')
        elif any(abs(a['quiet_margin_ps']-b['quiet_margin_ps'])>50 for a,b in zip(xt,yt)):issues.append('tail_delta_gt50ps')
        diffs.append(row)
    return dict(pass_diagnostic=not issues,issues=sorted(set(issues)),differences=diffs,
        scope='Short diagnostic numerical comparison only; not equal-accuracy proof',
        reference_settings=reference['effective_settings'],candidate_settings=candidate['effective_settings'])
class Campaign(object):
    def __init__(self,api,manifest):self.api=api;self.m=manifest
    def state(self,**d):
        d.update(epoch=time.time(),pid=os.getpid());write('status.json',d)
    def finish_many(self,runs):
        assert 1<=len(runs)<=6
        for run in runs:
            rec=read(ROOT+'/runs/'+run+'/registered.json')
            assert rec['recipe_hash']==self.m['registered_hashes'][run],'Run identity changed'
        results={}
        while len(results)<len(runs):
            pending=[]
            for run in runs:
                if run in results:continue
                actual=self.m.get('analysis_overrides',{}).get(run,run)
                if actual!=run:
                    assert read(ROOT+'/runs/'+actual+'/registered.json')['recipe_hash']==self.m['registered_hashes'][actual]
                s=self.api(dict(action='status',run_id=actual))
                phase='analysis' if actual!=run else ('simulation' if s['simulation']['status']!='complete' else 'analysis')
                action='submit' if phase=='simulation' else 'analyze'
                v=s[phase];st=v['status']
                if v.get('observation'):raise RuntimeError('Uncertain worker: '+str(v))
                if st=='complete':
                    result=read(ROOT+'/runs/'+actual+'/derived/result.json')
                    assert result.get('analysis_complete')
                    results[run]=result;write(run+'_result.json',result);continue
                if st=='not_started':
                    self.api(dict(action=action,run_id=actual,queue=True));st='submitted'
                elif st not in ['running','queued','starting','submitted','waiting']:
                    raise RuntimeError('Terminal managed state '+run+' '+str(v))
                pending.append(dict(run_id=run,phase=phase,status=st,reasons=v.get('waiting_reasons',[])))
            self.state(stage='managed_batch',pending=pending,completed=sorted(results))
            if len(results)<len(runs):time.sleep(30)
        return [results[r] for r in runs]
    def finish(self,run):return self.finish_many([run])[0]
    def static(self,runs,point):
        results=[]
        groups=[runs[:1]]+[runs[i:i+2] for i in range(1,len(runs),2)]
        for group in groups:
            batch=self.finish_many(group);results.extend(batch)
            for run,r in zip(group,batch):
                if not r['functional_pass']:
                    write(point+'_static_failure.json',dict(run_id=run,result=r));return False
        write(point+'_static.json',aggregate(results));return True
    def run(self):
        reference=self.finish('sar8ab-phase60-a-tt-v1')
        assert passed(reference),'A strict reference fails'
        candidate=self.finish('sar8camp-a-mm-bench-v2')
        check=solver_compare(reference,candidate)
        profile='mm' if check['pass_diagnostic'] else 'strict'
        run='sar8camp-a-tt-fft1024-mm-v1' if profile=='mm' else 'sar8camp-a-tt-fft1024-v1'
        write('solver_selection.json',dict(label='a',profile=profile,check=check,fft_run=run,
            baseline_adopted=False,electrical_verdict='deferred_not_qualified'))
        result=self.finish(run)
        write('tt_dynamic.json',result)
        self.state(stage='a_fft_complete',profile=profile,run_id=run,functional_pass=result['functional_pass'])

def main():
    assert os.getuid()==596
    lock=open(HERE+'/coordinator.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    m=read(HERE+'/manifest.json');path=ROOT+'/tools/agent_'+m['agent_sha256']+'.py'
    assert hashlib.sha256(open(path,'rb').read()).hexdigest()==m['agent_sha256']
    api=imp.load_source('campaign_managed_agent',path).main
    c=Campaign(api,m)
    try:c.run()
    except Exception:
        c.state(stage='failed',error=traceback.format_exc());raise
if __name__=='__main__':main()
