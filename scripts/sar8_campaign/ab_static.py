"""Finite metadata coordinator. All heavy work uses the frozen managed agent API."""
from __future__ import print_function
import fcntl,hashlib,imp,json,os,sys,time,traceback
ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
HERE=ROOT+'/campaigns/sar8-functional-20261028/ab-static'
def read(p):
    assert os.path.getsize(p)<16*1024*1024,'Metadata exceeds bound'
    with open(p) as f:return json.load(f)
def write(name,d):
    p=HERE+'/'+name;q=p+'.tmp'
    with open(q,'w') as f:json.dump(d,f,indent=2);f.write('\n')
    os.rename(q,p)
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

ACTIVE=('running','queued','starting','submitted','waiting')

def eligible(runs,results,failed):
    if failed:return []
    if runs[0] not in results:return [runs[0]]
    return [r for r in runs[1:] if r not in results][:2]

class Campaign(object):
    def __init__(self,api,manifest):
        self.api=api;self.m=manifest;self.results={};self.failed={};self.finished={}
    def advance(self,run):
        s=self.api(dict(action='status',run_id=run))
        phase='simulation' if s['simulation']['status']!='complete' else 'analysis'
        v=s[phase];st=v['status']
        if v.get('observation'):return dict(failure='uncertain_worker',detail=v)
        if st=='complete':
            r=read(ROOT+'/runs/'+run+'/derived/result.json')
            assert r.get('analysis_complete') and r.get('native_decode_crosscheck')
            write(run+'_result.json',r);self.results[run]=r
            return dict(complete=True,functional_pass=r['functional_pass'])
        if st=='not_started':
            self.api(dict(action='submit' if phase=='simulation' else 'analyze',run_id=run,queue=True))
            return dict(phase=phase,status='submitted')
        if st not in ACTIVE:return dict(failure='terminal_phase',detail=v)
        return dict(phase=phase,status=st,reasons=v.get('waiting_reasons',[]))
    def tick(self):
        pending=[]
        for label in ['a','b']:
            if label in self.finished:continue
            runs=self.m['runs'][label]
            for run in eligible(runs,self.results,label in self.failed):
                r=self.advance(run)
                if r.get('failure') or (r.get('complete') and not r['functional_pass']):
                    self.failed[label]=dict(run_id=run,evidence=r);write(label+'_failure.json',self.failed[label]);break
                if not r.get('complete'):pending.append(dict(run_id=run,detail=r))
            if label in self.failed:self.finished[label]='failed_expansion_stopped_inflight_preserved'
            elif all(run in self.results for run in runs):
                result=aggregate([self.results[run] for run in runs]);write(label+'_tt_static.json',result);self.finished[label]='complete'
        state=dict(epoch=time.time(),pid=os.getpid(),stage='complete' if len(self.finished)==2 else 'managed_tt_static',pending=pending,completed=sorted(self.results),finished=self.finished,failures=self.failed,fft_mutated=False)
        write('status.json',state)
        return len(self.finished)==2
    def run(self):
        while not self.tick():time.sleep(30)

def main():
    assert os.getuid()==596
    lock=open(HERE+'/coordinator.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    m=read(HERE+'/manifest.json')
    for run,h in m['registered_hashes'].items():
        rec=read(ROOT+'/runs/'+run+'/registered.json');assert rec['recipe_hash']==h
        assert read(ROOT+'/runs/'+run+'/recipe.json')['resources']['threads']==4
    path=ROOT+'/tools/agent_'+m['agent_sha256']+'.py'
    assert hashlib.sha256(open(path,'rb').read()).hexdigest()==m['agent_sha256']
    api=imp.load_source('campaign_managed_agent',path).main
    try:Campaign(api,m).run()
    except Exception:
        write('status.json',dict(stage='failed',epoch=time.time(),pid=os.getpid(),error=traceback.format_exc(),inflight_preserved=True));raise
if __name__=='__main__':main()
