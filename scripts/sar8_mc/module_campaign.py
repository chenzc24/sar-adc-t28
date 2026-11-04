"""Finite managed coordinator: validate two pilots, then finish30 seeds/block.

Python2/3. Reads only small state/results and uses immutable managed APIs.
No PDK/raw processing, unbounded retries, circuit edits or simulator signalling.
"""
from __future__ import print_function
import hashlib,json,os,sys,time,traceback
ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
DEST=ROOT+'/campaigns/sar8-mc-20261103/modules'

def read(p):
    with open(p) as f:return json.load(f)
def write(p,d):
    tmp=p+'.tmp'
    with open(tmp,'w') as f:json.dump(d,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.rename(tmp,p)

class Campaign(object):
    def __init__(self,m,api):self.m=m;self.api=api;self.done={};self.started=time.time()
    def state(self,stage,**kw):
        kw.update(stage=stage,epoch=time.time(),pid=os.getpid(),completed=sorted(self.done));write(DEST+'/status.json',kw)
    def finish_many(self,runs,stage):
        waiting=list(runs);active=[]
        while waiting or active:
            if time.time()-self.started>20*3600:raise RuntimeError('Finite20h coordinator deadline; keep existing workers/checkpoint')
            while waiting and len(active)<4:active.append(waiting.pop(0))
            pending=[]
            for run in list(active):
                s=self.api({'action':'status','run_id':run})
                phase='simulation' if s['simulation']['status']!='complete' else 'analysis'
                v=s[phase];status=v['status']
                if v.get('observation'):raise RuntimeError('Uncertain managed worker '+run+' '+str(v))
                if status=='complete':
                    result=read(ROOT+'/runs/'+run+'/derived/result.json')
                    assert result['analysis_complete'] and result['native_data_valid'],run
                    self.done[run]=result;write(DEST+'/'+run+'_result.json',result);active.remove(run);continue
                if status=='not_started':self.api({'action':'submit' if phase=='simulation' else 'analyze','run_id':run,'queue':True});status='submitted'
                elif status not in ['running','queued','starting','submitted','waiting']:raise RuntimeError('Terminal managed state '+run+' '+phase+' '+str(v))
                pending.append({'run_id':run,'phase':phase,'status':status,'reasons':v.get('waiting_reasons',[])})
            self.state(stage,pending=pending,remaining=len(waiting))
            if waiting or active:time.sleep(15)
    def result(self,key):return self.done[self.m['runs'][key]['run_id']]
    def pilot_check(self,family):
        nominal=self.result(family+'-nominal')
        pilots=[self.result(family+'-s%d'%i) for i in range(4101,4104)]
        fingerprints=[r['mismatch_evidence']['values_sha256'] for r in pilots]
        assert len(set(fingerprints))==3,'No independent random values'
        selected=[r['mismatch_evidence']['selected'] for r in pilots]
        assert len(set(json.dumps(x,sort_keys=True) for x in selected))==3,'Target parameters do not vary'
        if family=='cdac':
            assert nominal['weights']['dac_dnl_abs_max_lsb']<.005,'Nominal capacitor weights inconsistent'
            assert len(set(json.dumps(x['capacitance_f'],sort_keys=True) for x in pilots))==3,'Native capacitors do not vary'
        else:
            assert nominal['threshold_valid'] and abs(nominal['offset_midpoint_v'])<.002,'Nominal comparator fixture failed'
            # Random search failures remain performance results, not a claim of yield.
        rec={'pilot_configuration_valid':True,'family':family,'independent_draws':3,
            'random_hashes':fingerprints,'pilot_performance_flags':[r.get('threshold_valid',True) for r in pilots]}
        write(DEST+'/'+family+'_pilot_review.json',rec)
    def run(self):
        nominal=[self.m['runs'][f+'-nominal']['run_id'] for f in ['cdac','comp']]
        self.finish_many(nominal,'nominal_controls')
        pilots=[self.m['runs'][f+'-s%d'%i]['run_id'] for i in range(4101,4104) for f in ['cdac','comp']]
        self.finish_many(pilots,'first_three_seeds')
        for f in ['cdac','comp']:self.pilot_check(f)
        repeats=[self.m['runs'][f+'-s4101-repeat']['run_id'] for f in ['cdac','comp']]
        self.finish_many(repeats,'repeatability_controls')
        for f in ['cdac','comp']:
            a=self.result(f+'-s4101');b=self.result(f+'-s4101-repeat')
            assert a['mismatch_evidence']['values_sha256']==b['mismatch_evidence']['values_sha256'],'Repeat sample changed'
            if f=='cdac':assert all(abs(a['capacitance_f'][k]/b['capacitance_f'][k]-1)<1e-6 for k in a['capacitance_f'])
            else:
                assert abs(a['offset_midpoint_v']-b['offset_midpoint_v'])<1e-7
                for x,y in zip(a['records'],b['records']):
                    assert x[:6]==y[:6] and x[9:11]==y[9:11]
                    assert abs(x[6]-y[6])<1e-12 and abs(x[7]-y[7])<1e-12
        rest=[self.m['runs'][f+'-s%d'%i]['run_id'] for i in range(4104,4131) for f in ['cdac','comp']]
        self.state('pilots_verified_automatic_remaining_authorized')
        self.finish_many(rest,'remaining_seeds')
        summary={}
        for f in ['cdac','comp']:
            rows=[self.result(f+'-s%d'%i) for i in range(4101,4131)]
            summary[f]={'samples':30,'runs':[r['context']['run_id'] for r in rows],
                'all_native_data_valid':all(r['native_data_valid'] for r in rows),
                'performance_flags':[r.get('threshold_valid',r.get('weights',{}).get('dac_levels_monotonic')) for r in rows]}
        write(DEST+'/summary.json',summary);self.state('complete',summary=summary)

def main():
    m=read(DEST+'/manifest.json');agent=ROOT+'/tools/agent_'+m['agent_sha256']+'.py'
    blob=open(agent,'rb').read();assert hashlib.sha256(blob).hexdigest()==m['agent_sha256']
    scope={'__name__':'managed_agent','__file__':agent};exec(compile(blob,agent,'exec'),scope)
    for run,h in m['registered_hashes'].items():assert read(ROOT+'/runs/'+run+'/registered.json')['recipe_hash']==h
    c=Campaign(m,scope['main'])
    try:c.run()
    except Exception as exc:c.state('failed',error=repr(exc),traceback=traceback.format_exc());raise
if __name__=='__main__':main()
