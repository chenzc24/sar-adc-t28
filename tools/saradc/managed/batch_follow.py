"""Finite remote batch driver; all simulations/analyses use the managed agent.

Python 2.7/3 compatible. Launch once against an immutable registered manifest.
It never resubmits a failed/uncertain operation and never deletes waveforms.
"""
from __future__ import print_function
import fcntl
import hashlib
import json
import os
import resource
import sys
import time

def load_agent(path):
    try:
        import imp
        return imp.load_source('frozen_batch_agent',path)
    except ImportError:
        import importlib.util
        spec=importlib.util.spec_from_file_location('frozen_batch_agent',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def run(folder):
    # Keep the inherited hard ceiling: managed children set their own declared
    # simulation/analysis limits. A 256 MiB hard limit here would break them.
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,resource.getrlimit(resource.RLIMIT_AS)[1]))
    assert os.path.realpath(folder)==folder and os.stat(folder).st_uid==os.getuid()
    with open(folder+'/controller.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return follow(folder)

def follow(folder):
    with open(folder+'/batch.json') as f:batch=json.load(f)
    agent_path=batch['agent_path']
    with open(agent_path,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==batch['agent_sha256']
    agent=load_agent(agent_path)
    assert os.getuid()==agent.UID and agent.socket.gethostname().split('.')[0]==batch['host']
    state=dict(batch_id=batch['batch_id'],started_epoch=time.time(),runs={},status='running')
    stop=time.time()+48*3600
    failed=set()
    def save():
        state['updated_epoch']=time.time()
        agent.write(folder+'/status.json',state)
    def call(action,rid):
        return agent.main(dict(action=action,run_id=rid,queue=True,expected_host=batch['host']))
    while time.time()<stop:
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<=32*1024
        active=0;done=0;waiting=[]
        for row in batch['runs']:
            rid=row['run_id']
            if rid in failed:done+=1;continue
            try:
                observed=call('status',rid)
                assert observed['registered']['recipe_hash']==row['recipe_hash']
                assert not any(observed[p].get('observation') for p in ('simulation','analysis')),'Worker identity needs reconciliation'
                sim=observed['simulation'].get('status');analysis=observed['analysis'].get('status')
                state['runs'][rid]=dict(simulation=sim,analysis=analysis)
                if sim in agent.TERMINAL-{'complete'} or analysis in agent.TERMINAL-{'complete'}:
                    failed.add(rid);done+=1;continue
                if sim=='complete' and analysis=='complete':done+=1;continue
                if sim=='not_started':waiting.append(rid);continue
                active+=1
                if sim=='complete' and analysis=='not_started':
                    state['runs'][rid]['analysis_submission']=call('analyze',rid)
            except Exception as exc:
                state['runs'][rid]=dict(status='needs_reconciliation',error=str(exc))
                failed.add(rid);done+=1
            save()
        for rid in waiting[:max(0,batch['max_inflight_runs']-active)]:
            try:state['runs'][rid]['simulation_submission']=call('submit',rid)
            except Exception as exc:
                state['runs'][rid]=dict(status='needs_reconciliation',error=str(exc));failed.add(rid)
            save()
        state.update(failed_or_uncertain=sorted(failed),finished_count=done)
        save()
        if done==len(batch['runs']):
            state['status']='finished_with_failures' if failed else 'complete';save();return
        time.sleep(30)
    state['status']='controller_timeout';save()

if __name__=='__main__':run(sys.argv[1])
