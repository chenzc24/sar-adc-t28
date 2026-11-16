"""Finite pilot -> continuous FFT -> analysis; no retries or raw deletion."""
from __future__ import print_function
import fcntl
import hashlib
import imp
import json
import os
import resource
import sys
import time


def run(folder):
    resource.setrlimit(resource.RLIMIT_AS, (256*1024**2, resource.getrlimit(resource.RLIMIT_AS)[1]))
    assert os.path.realpath(folder) == folder and os.stat(folder).st_uid == os.getuid()
    with open(folder+'/controller.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        b = json.load(open(folder+'/batch.json'))
        assert hashlib.sha256(open(b['agent_path'],'rb').read()).hexdigest() == b['agent_sha256']
        agent = imp.load_source('noise_fft_managed', b['agent_path'])
        state = dict(status='running', started_epoch=time.time(), runs={})
        deadline = time.time()+7*86400
        def save():
            state['updated_epoch'] = time.time()
            agent.write(folder+'/status.json', state)
        def call(action, rid):
            return agent.main(dict(action=action, run_id=rid, queue=True, expected_host=b['host']))
        try:
            while time.time() < deadline:
                assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss <= 32768
                pilot_pass = False
                finished = False
                for role in ['pilot', 'full']:
                    row = b[role]
                    rid = row['run_id']
                    observed = call('status',rid)
                    assert observed['registered']['recipe_hash'] == row['recipe_hash']
                    assert not any(observed[p].get('observation') for p in ['simulation','analysis']), 'Worker identity uncertain'
                    sim, ana = observed['simulation'].get('status'), observed['analysis'].get('status')
                    state['runs'][role] = dict(run_id=rid, simulation=sim, analysis=ana)
                    if sim in agent.TERMINAL-{'complete'} or ana in agent.TERMINAL-{'complete'}:
                        raise RuntimeError(role+' ended without completion; preserve original identity')
                    if role == 'full' and not pilot_pass:
                        state['runs'][role]['waiting_for'] = 'pilot native protocol and independent decode'
                        break
                    if sim == 'not_started':
                        state['runs'][role]['submission'] = call('submit',rid)
                    elif sim == 'complete' and ana == 'not_started':
                        state['runs'][role]['analysis_submission'] = call('analyze',rid)
                    elif ana == 'complete':
                        result_path = agent.runpath(rid)+'/derived/result.json'
                        result = json.load(open(result_path))
                        assert result['context']['run_id'] == rid and result['context']['noise']
                        assert result['analysis_complete'] and result['native_decode_crosscheck']
                        if not result['functional_pass']:
                            state['invalid_frames'] = result['invalid_all_frames']
                            raise RuntimeError(role+' has invalid protocol frames')
                        if role == 'pilot':
                            assert result['context']['pilot'] and len(result['frames']) == 8
                            pilot_pass = True
                            state['pilot_pass'] = dict(run_id=rid, result_sha256=agent.sha(result_path), epoch=time.time(),
                                                      scope='Observer/protocol and native decode only; not a noise bandwidth qualification')
                        else:
                            assert len(result['codes']) == 1024 and not result['context']['pilot']
                            state['spectrum'] = result['spectrum']
                            state['result_sha256'] = agent.sha(result_path)
                            finished = True
                if finished:
                    state['status'] = 'complete'
                    save()
                    return
                save()
                time.sleep(30)
            state['status'] = 'controller_timeout'
        except Exception as exc:
            state['status'] = 'needs_reconciliation'
            state['error'] = str(exc)
        save()


if __name__ == '__main__':
    run(sys.argv[1])
