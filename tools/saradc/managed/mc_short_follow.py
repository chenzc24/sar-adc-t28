"""Finite 36-run managed MC driver; two pilots per group, no implicit retries."""
from __future__ import print_function
import fcntl
import hashlib
import imp
import json
import os
import resource
import sys
import time


def pilot_gate(rows,results):
    if len(rows)!=2 or not all(r['run_id'] in results for r in rows):return False
    evidence=[results[r['run_id']] for r in rows]
    if not all(r['pilot_pass'] for r in evidence):return False
    return all(len(set(r['random_evidence'][key] for r in evidence))==2
               for key in ['process_values_sha256','mismatch_values_sha256'])


def run(folder):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,resource.getrlimit(resource.RLIMIT_AS)[1]))
    assert os.path.realpath(folder)==folder and os.stat(folder).st_uid==os.getuid()
    with open(folder+'/controller.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        b=json.load(open(folder+'/batch.json'))
        assert hashlib.sha256(open(b['agent_path'],'rb').read()).hexdigest()==b['agent_sha256']
        agent=imp.load_source('mc_managed',b['agent_path'])
        assert os.getuid()==agent.UID and agent.socket.gethostname().split('.')[0]==b['host']
        state=dict(batch_id=b['batch_id'],status='running',started_epoch=time.time(),runs={},pilot_pass={},max_inflight_runs=b['max_inflight_runs'])
        failed=set();results={};done=set();deadline=time.time()+7*86400
        def save():
            state['updated_epoch']=time.time();agent.write(folder+'/status.json',state)
        def call(action,rid):
            return agent.main(dict(action=action,run_id=rid,queue=True,expected_host=b['host']))
        def check_fft():
            path=agent.runpath(b['protected_fft_run'])
            count=0
            if os.path.isfile(path+'/spectre.out'):
                with open(path+'/spectre.out') as f:
                    for line in f:
                        if 'FFTMEAS,' in line:count+=1
            now=time.time();previous=state.get('fft_reference')
            if previous is None:state['fft_reference']=dict(epoch=now,frames=count)
            elif now-previous['epoch']>900 and count-previous['frames']>=8:
                pace=(now-previous['epoch'])/(count-previous['frames'])
                state['fft_seconds_per_frame']=pace
                if pace>1.3*b['fft_baseline_seconds_per_frame']:
                    state['max_inflight_runs']=1
                    state['fft_resource_note']='Reduced future MC admissions to one slot after FFT throughput slowdown; active jobs preserved'
                state['fft_reference']=dict(epoch=now,frames=count)
        while time.time()<deadline:
            assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<=32768
            check_fft();active=0;waiting=[]
            for row in b['runs']:
                rid=row['run_id']
                if rid in done:continue
                try:
                    o=call('status',rid)
                    assert o['registered']['recipe_hash']==row['recipe_hash']
                    assert not any(o[p].get('observation') for p in ['simulation','analysis']),'Uncertain worker identity'
                    sim,ana=o['simulation']['status'],o['analysis']['status']
                    state['runs'][rid]=dict(simulation=sim,analysis=ana,group=row['group'],seed=row['seed'])
                    if sim in agent.TERMINAL-{'complete'} or ana in agent.TERMINAL-{'complete'}:
                        failed.add(rid);done.add(rid);continue
                    if ana=='complete':
                        p=agent.runpath(rid)+'/derived/result.json';r=json.load(open(p))
                        assert r['context']['run_id']==row.get('source_run_id',rid) and r['context']['seed']==row['seed'] and r['analysis_complete']
                        results[rid]={k:r[k] for k in ['pilot_pass','random_evidence','timing_pass','settling_screen_pass']}
                        state['runs'][rid].update(result_sha256=agent.sha(p),timing_pass=r['timing_pass'],settling_screen_pass=r['settling_screen_pass'],random_valid=r['random_evidence']['valid'],first_issue=r['first_issue'],first_settling_review=r['first_settling_review'])
                        done.add(rid);continue
                    if sim=='not_started':waiting.append(row);continue
                    active+=1
                    if sim in ('complete','not_applicable') and ana=='not_started':state['runs'][rid]['analysis_submission']=call('analyze',rid)
                except Exception as exc:
                    state['runs'][rid]=dict(status='needs_reconciliation',error=str(exc));failed.add(rid);done.add(rid)
            for group in b['groups']:
                pilots=[r for r in b['runs'] if r['group']==group and r['pilot']]
                if pilot_gate(pilots,results):
                    state['pilot_pass'][group]=[r['run_id'] for r in pilots]
            eligible=[r for r in waiting if r['pilot'] or r['group'] in state['pilot_pass']]
            for row in eligible[:max(0,state['max_inflight_runs']-active)]:
                rid=row['run_id']
                try:state['runs'][rid]['submission']=call('submit',rid)
                except Exception as exc:
                    state['runs'][rid]=dict(status='needs_reconciliation',error=str(exc));failed.add(rid);done.add(rid)
            state.update(finished_count=len(done),failed_or_uncertain=sorted(failed))
            if len(done)==len(b['runs']):
                state['status']='complete_with_issues' if failed or any(not r['pilot_pass'] for r in results.values()) else 'complete'
                save();return
            if not active and not eligible and waiting:
                state['status']='pilot_review_required';save();return
            save();time.sleep(30)
        state['status']='controller_timeout';save()


if __name__=='__main__':run(sys.argv[1])
