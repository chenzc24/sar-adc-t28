"""Finite metadata-only watcher: analyze this one run after completion, then exit."""
from __future__ import print_function
import fcntl,hashlib,imp,json,os,time,traceback
ROOT='/server_local_ssd/chenzc_intern25/sar-adc-t28'
HERE=ROOT+'/campaigns/sar8-noise-20261029-b101'
def read(p):
    assert os.path.getsize(p)<4*1024*1024
    with open(p) as f:return json.load(f)
def state(**d):
    d.update(epoch=time.time(),pid=os.getpid())
    with open(HERE+'/status.json.tmp','w') as f:json.dump(d,f,indent=2)
    os.rename(HERE+'/status.json.tmp',HERE+'/status.json')
def main():
    assert os.getuid()==596
    lock=open(HERE+'/coordinator.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        m=read(HERE+'/manifest.json');assert len(m['registered_hashes'])==1
        run=list(m['registered_hashes'])[0]
        assert read(ROOT+'/runs/'+run+'/registered.json')['recipe_hash']==m['registered_hashes'][run]
        path=ROOT+'/tools/agent_'+m['agent_sha256']+'.py'
        assert hashlib.sha256(open(path,'rb').read()).hexdigest()==m['agent_sha256']
        api=imp.load_source('noise_managed_agent',path).main
        while True:
            s=api(dict(action='status',run_id=run));phase='simulation' if s['simulation']['status']!='complete' else 'analysis'
            v=s[phase];st=v['status']
            if v.get('observation'):raise RuntimeError('Uncertain state: '+str(v))
            if st=='complete':
                result=read(ROOT+'/runs/'+run+'/derived/result.json')
                assert result['analysis_complete'] and result['native_decode_crosscheck']
                state(stage='complete',run_id=run,functional_pass=result['functional_pass'],comparison=result['noise_baseline_comparison']);return
            if phase=='analysis' and st=='not_started':
                # Persist intent first; never retry an uncertain call.
                assert not os.path.exists(HERE+'/analysis_requested.json')
                with open(HERE+'/analysis_requested.json','w') as f:json.dump(dict(run_id=run,epoch=time.time()),f)
                api(dict(action='analyze',run_id=run,queue=True));st='requested'
            elif st not in ['running','queued','starting','submitted','waiting']:
                raise RuntimeError('Stopped on managed state '+phase+' '+str(v))
            state(stage=phase,status=st,run_id=run,reasons=v.get('waiting_reasons',[]))
            time.sleep(60)
    except Exception:
        state(stage='failed',error=traceback.format_exc());raise
if __name__=='__main__':main()
