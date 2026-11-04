"""Backfill three managed lanes with already registered work, prioritizing pilot 5102."""
from __future__ import print_function
import hashlib
import json
import os
import time
import traceback

def main():
    dest=os.path.dirname(os.path.abspath(__file__))
    root='/server_local_ssd/chenzc_intern25/sar-adc-t28'
    def read(p):
        with open(p) as f:return json.load(f)
    def checkpoint(**kw):
        tmp=dest+'/status.tmp'
        with open(tmp,'w') as f:json.dump(kw,f)
        os.rename(tmp,dest+'/status.json')
    modules=read(root+'/campaigns/sar8-timing-mc-20261104-modules/manifest.json')
    cold=read(root+'/campaigns/sar8-timing-mc-20261104-cold/manifest.json')
    path=root+'/tools/agent_'+modules['agent_sha256']+'.py'
    src=open(path,'rb').read()
    assert hashlib.sha256(src).hexdigest()==modules['agent_sha256']==cold['agent_sha256']
    ns={'__file__':path,'__name__':'managed_agent'}
    eval(compile(src,path,'exec'),ns)
    api=ns['main']
    waiting=cold['jobs'][2:4]+list(reversed(modules['jobs']))
    active=[];done=[];start=time.time()
    try:
        while waiting or active:
            assert time.time()-start<36*3600,'Finite backfill window exhausted'
            if not active:
                ms=read(root+'/campaigns/sar8-timing-mc-20261104-modules/status.json')
                assert ms['stage']!='held','Module campaign held, inspect before advancing'
            while waiting and len(active)<3:
                run=waiting.pop(0)
                if run in modules['registered_hashes']:
                    # Leave the forward coordinator sole owner of the near-frontier work.
                    first=[x for x in modules['jobs'] if not os.path.exists(root+'/runs/'+x+'/derived/result.json')][:8]
                    if run in first:
                        waiting=[];break
                current=api({'action':'status','run_id':run})['simulation']
                if current.get('observation'):raise RuntimeError(str(current))
                if current['status']!='not_started':continue
                expected=(cold if run in cold['registered_hashes'] else modules)['registered_hashes'][run]
                assert read(root+'/runs/'+run+'/registered.json')['recipe_hash']==expected
                api({'action':'submit','run_id':run,'queue':True})
                active.append(run)
            for run in active[:]:
                state=api({'action':'status','run_id':run})
                phase='analysis' if state['simulation']['status']=='complete' else 'simulation'
                item=state[phase]
                if item.get('observation'):raise RuntimeError(str(item))
                if item['status']=='not_started' and phase=='analysis':
                    api({'action':'analyze','run_id':run,'queue':True})
                elif phase=='analysis' and item['status']=='complete':
                    active.remove(run);done.append(run)
                elif item['status'] not in ('running','submitted','starting','queued','waiting'):
                    raise RuntimeError(str(item))
            checkpoint(stage='backfill',active=active,completed=done)
            if waiting or active:time.sleep(6)
        checkpoint(stage='complete',active=[],completed=done)
    except Exception as exc:
        checkpoint(stage='held',active=active,completed=done,error=repr(exc),traceback=traceback.format_exc());raise
if __name__=='__main__':main()
