"""Bounded end-to-end verification. No ADC, OA mutation or historical writes."""
from concurrent.futures import ThreadPoolExecutor
import copy,io,json,sys,time,unittest
from pathlib import Path
import execution as e
import project


def wait_phase(run_id,phase):
    for _ in range(20):
        result=e.phase('status',run_id)
        status=result[phase]['status']
        if status in ['complete','failed','rejected','limit_exceeded']:
            assert status=='complete',result
            return result
        time.sleep(2)
    raise RuntimeError('Still queued/running; keep worker alive and query run-status. Do not resubmit a new ID.')


def main():
    evidence=project.ROOT/'verification/managed_execution/validation.json'
    if evidence.exists():raise RuntimeError('Validation already recorded; inspect it instead of starting another smoke.')
    registration=e.register('management/recipes/rc_smoke.yaml')
    run_id=Path(registration['path']).name
    with ThreadPoolExecutor(max_workers=2) as pool:
        submissions=list(pool.map(lambda _:e.phase('submit',run_id,True),range(2)))
    assert sum(not x['existing'] for x in submissions)==(0 if registration['existing'] else 1),submissions
    simulation=wait_phase(run_id,'simulation')
    first=simulation['simulation']['child_identity']
    duplicate=e.phase('submit',run_id)
    assert duplicate['existing'] and duplicate['state']['simulation']['child_identity']==first
    analysis_submit=e.phase('analyze',run_id,True)
    final=wait_phase(run_id,'analysis')
    collection=e.collect(run_id)
    again=e.collect(run_id)
    assert collection['bytes']==again['bytes'] and collection['collected_files']==again['collected_files']
    result=project.load(project.ROOT/collection['local_path']/'derived/result.json')
    assert result['PSF_END'] and result['native_points']>20
    assert abs(result['last_time_s']-1e-8)<1e-15
    assert .999<result['signals']['out']['last']<1.001
    # A deliberately impossible *gate-only* request: never launch this budget.
    impossible=copy.deepcopy(e.recipe(run_id));impossible['resources']['simulation_rss_mib']=1024*1024
    refusal=e.rpc(dict(action='gate',recipe=impossible,phase='simulation'))
    assert not refusal['pass_gate'] and 'host_memory_headroom' in refusal['reasons']
    payload=dict(observed_at_utc=project.now(),workflow_only=True,ADC_rerun=False,OA_changes=[],historical_data_changed=False,
        run_id=run_id,registration=registration,concurrent_submissions=submissions,duplicate_submit=duplicate['existing'],
        simulation=final['simulation'],analysis=final['analysis'],collection=dict(collection,repeated_collection_verified=True),
        summary=result,oversized_gate_only_refusal=refusal,
        limitation='Watchdogs sampled, not administrator cgroups or host-wide sandboxing; SSD backup/retention unknown')
    # Native logs remain ignored; curate only small metrics and execution receipts.
    project.save(evidence,payload)
    print(json.dumps(dict(validation='PASS',run_id=run_id,native_points=result['native_points'],
        output_final=result['signals']['out']['last'],evidence=project.rel(evidence)),indent=2))

def finalize():
    """Curate bounded local receipts only; no new native jobs or source changes."""
    buffer=io.StringIO();suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern='test_*.py')
    result=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
    assert result.wasSuccessful(),buffer.getvalue()
    queued=[]
    for p in sorted((e.OUT/'transport').glob('*.output.json')):
        if p.stat().st_size>1024*1024:continue
        try:d=project.load(p).get('result',{})
        except (ValueError,OSError):continue
        if d.get('worker_pid')==318880 and d.get('gate',{}).get('reasons')==['existing_simulation_or_analysis']:
            queued.append(d)
    assert queued,'Expected retained queue receipt from first smoke'
    receipt=e.OUT/'legacy/legacy-991140739bc648fa/737443c1d054/collection_receipt.json'
    legacy=project.load(receipt);assert legacy['read_only']
    project.save(project.ROOT/'verification/managed_execution/checks.json',dict(
        observed_at_utc=project.now(),focused_tests=result.testsRun,tests_passed=True,
        fixture_output=buffer.getvalue(),queued_submission=queued[0],
        queue_label_note='Initial prototype accepted a queue worker but native admission was false; current response separates accepted/admitted',
        legacy_read_only_collection=legacy,legacy_local_receipt=project.rel(receipt),
        source_agent_sha256=project.digest(project.ROOT/'scripts/management/remote_agent.py'),
        provenance_note='Native smoke worker revision is recorded in validation.json; subsequent PID-group/error-cleanup hardening covered by fixtures and Python2 RPC loading'))
    print('FINAL_CHECKS_PASS',result.testsRun,'fixtures; queued gate and legacy read-only collection retained')

if __name__=='__main__':
    if sys.argv[1:]==['--finalize']:finalize()
    else:main()
