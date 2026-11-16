"""Finite same-draw boundary campaign, survives client shutdown, four-hour stop."""
from __future__ import print_function
import fcntl,hashlib,imp,json,os,resource,sys,time,tarfile,ctypes,stat


def summarize(row,result):
    frames=result['frames'];bits=[b for f in frames for b in f['bits']]
    def extreme(key,items,maximum=True):
        good=[(x[key],x) for x in items if x.get(key) is not None]
        if not good:return None
        value,item=(max if maximum else min)(good,key=lambda x:x[0])
        return dict(value=value,frame=item.get('frame'),bit=item.get('bit'))
    indexed=[dict(b,frame=f['frame']) for f in frames for b in f['bits']]
    for b in indexed:
        if b.get('write_s') is not None and b.get('receiver_margin_ps') is not None:
            b['decision_ns']=(b['write_s']-b['compare_s'])*1e9-b['receiver_margin_ps']/1000
    return dict(run_id=row['run_id'],seed=row['seed'],group=row['group'],mode=row['mode'],pilot=row['pilot'],
        timing_pass=result['timing_pass'],settling_screen_pass=result['settling_screen_pass'],
        random_valid=result['random_evidence']['valid'],boundary_valid=result['boundary']['valid'],
        pass_diagnostic=result['pass_diagnostic'],first_issue=result['first_issue'],
        boundary_errors=result['boundary']['errors'],brackets=result['boundary']['brackets'],
        conversion_max_ns=extreme('conversion_ns',frames),receiver_margin_min_ps=extreme('receiver_margin_ps',indexed,False),
        decision_max_ns=extreme('decision_ns',indexed),bottom_bound_max_lsb=extreme('conservative_settling_bound_lsb',indexed),
        top_excursion_max_v=extreme('post_100ps_excursion_v',result['top_interface']),
        warning_codes=result['warning_codes'],frames=len(frames),bits=len(bits))


def cache_release(agent,rid):
    """Drop only clean cache of closed, completed, owned native files; never unlink."""
    root=agent.runpath(rid)
    if not all(os.path.isfile(root+'/'+p+'.state.json') and agent.read(root+'/'+p+'.state.json')['status']=='complete' for p in ['simulation','analysis']):return []
    opened=set()
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid)==os.getpid():continue
        try:
            pp='/proc/'+pid
            if os.stat(pp).st_uid!=agent.UID or open(pp+'/comm').read().strip()=='sshd':continue
            for fd in os.listdir(pp+'/fd'):
                try:opened.add(os.readlink(pp+'/fd/'+fd))
                except OSError:pass
        except (IOError,OSError):
            if os.path.exists('/proc/'+pid):return []
    advice=ctypes.CDLL(None).posix_fadvise
    advice.argtypes=[ctypes.c_int,ctypes.c_longlong,ctypes.c_longlong,ctypes.c_int];advice.restype=ctypes.c_int
    receipts=[]
    for parent,dirs,names in os.walk(root+'/raw'):
        for name in names:
            p=parent+'/'+name
            if not name.endswith('.tran.tran') or p in opened or os.path.realpath(p)!=p:continue
            before=os.stat(p)
            assert before.st_uid==agent.UID and stat.S_ISREG(before.st_mode)
            fd=os.open(p,os.O_RDONLY)
            try:
                current=os.fstat(fd);assert (before.st_dev,before.st_ino,before.st_size)==(current.st_dev,current.st_ino,current.st_size)
                assert advice(fd,0,before.st_size,4)==0
            finally:os.close(fd)
            after=os.stat(p);assert (before.st_ino,before.st_size,before.st_mtime)==(after.st_ino,after.st_size,after.st_mtime)
            receipts.append(dict(path=p,bytes=before.st_size,method='POSIX_FADV_DONTNEED',deleted=False))
    return receipts


def archive(agent,folder,row):
    root=agent.runpath(row['run_id']);paths=[]
    for item in agent.read(root+'/recipe.json')['files']:
        paths.append(root+'/inputs/'+item['name'])
    for sub in ['derived']:
        for parent,dirs,names in os.walk(root+'/'+sub):
            for name in names:
                p=parent+'/'+name
                if name.endswith(('.pyc','.pyo')):continue
                assert os.path.realpath(p)==p
                paths.append(p)
    for name in ['recipe.json','registered.json','simulation.state.json','analysis.state.json','spectre.out']:
        paths.append(root+'/'+name)
    assert sum(os.stat(p).st_size for p in paths)<32*1024**2
    dest=folder+'/archives';agent.mkdir(dest);target=dest+'/'+row['run_id']+'.tar.gz'
    if not os.path.isfile(target):
        with tarfile.open(target+'.partial','w:gz') as tar:
            for p in paths:tar.add(p,arcname=os.path.relpath(p,root),recursive=False)
        os.rename(target+'.partial',target)
    return dict(path=target,sha256=agent.sha(target),bytes=os.stat(target).st_size,
        files=[dict(name=os.path.relpath(p,root),sha256=agent.sha(p),bytes=os.stat(p).st_size) for p in paths])


def run(folder):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,resource.getrlimit(resource.RLIMIT_AS)[1]))
    with open(folder+'/controller.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        b=json.load(open(folder+'/batch.json'))
        assert hashlib.sha256(open(b['agent_path'],'rb').read()).hexdigest()==b['agent_sha256']
        agent=imp.load_source('paired_managed',b['agent_path'])
        assert os.getuid()==agent.UID and agent.socket.gethostname().split('.')[0]==b['host']
        assert folder==agent.ROOT+'/batches/'+b['batch_id'] and os.path.realpath(folder)==folder
        state=dict(batch_id=b['batch_id'],started_epoch=time.time(),deadline_epoch=b['deadline_epoch'],status='running',runs={},results={},archives={},cache_releases=[],max_inflight_runs=2)
        done=set();failed=set();skipped=set();cache_done=set();durations=[]
        def call(action,rid,**kw):
            req=dict(action=action,run_id=rid,queue=True,expected_host=b['host']);req.update(kw);return agent.main(req)
        def save():
            state.update(updated_epoch=time.time(),finished=len(done),failed_or_uncertain=sorted(failed),budget_skipped=sorted(skipped))
            agent.write(folder+'/status.json',state)
            agent.write(folder+'/summary.json',dict(batch_id=b['batch_id'],status=state['status'],updated_epoch=state['updated_epoch'],deadline_epoch=b['deadline_epoch'],
                complete_cases=len([r for r in state['results'].values() if not r['pilot']]),planned_cases=16,results=state['results'],
                failed_or_uncertain=sorted(failed),budget_skipped=sorted(skipped),fft=state.get('fft',{}),
                scope=b['scope'],limitations=['Selected stress cases, not yield','Top excursions are not independently measured equilibrium error','No noise/PEX/full SOA']))
        def fft_check():
            count=0;path=agent.runpath(b['protected_fft_run'])
            for line in open(path+'/spectre.out'):
                if 'FFTMEAS,' in line:count+=1
            now=time.time();old=state.get('fft_reference')
            state['fft']=dict(run_id=b['protected_fft_run'],frames=count,epoch=now,status=agent.read(path+'/simulation.state.json')['status'])
            if old is None:state['fft_reference']=dict(epoch=now,frames=count)
            elif now-old['epoch']>900 and count-old['frames']>=8:
                pace=(now-old['epoch'])/(count-old['frames']);state['fft']['seconds_per_frame']=pace
                if pace>b['fft_baseline_seconds_per_frame']*1.3:state['max_inflight_runs']=1
                state['fft_reference']=dict(epoch=now,frames=count)
        while True:
            assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<32768
            fft_check();active=0;waiting=[]
            for row in b['runs']:
                rid=row['run_id']
                if rid in done:continue
                try:
                    o=call('status',rid);assert o['registered']['recipe_hash']==row['recipe_hash']
                    assert not any(o[p].get('observation') for p in ['simulation','analysis']),'Uncertain managed identity'
                    sim,ana=o['simulation']['status'],o['analysis']['status']
                    state['runs'][rid]=dict(simulation=sim,analysis=ana)
                    if sim in agent.TERMINAL-{'complete'} or ana in agent.TERMINAL-{'complete'}:
                        done.add(rid);failed.add(rid);continue
                    if ana=='complete':
                        path=agent.runpath(rid)+'/derived/result.json';result=agent.read(path)
                        assert result['context']['run_id']==rid and result['context']['source_run_id']==row['source_run_id']
                        state['results'][rid]=summarize(row,result);state['results'][rid]['result_sha256']=agent.sha(path)
                        state['archives'][rid]=archive(agent,folder,row)
                        elapsed=o['simulation'].get('elapsed_seconds')
                        if elapsed:durations.append(elapsed*(34./6 if row['pilot'] else 1.))
                        done.add(rid);del result;continue
                    if sim=='not_started':waiting.append(row);continue
                    active+=1
                    if time.time()>=b['deadline_epoch']:
                        phase='analysis' if sim=='complete' else 'simulation'
                        if o[phase]['status']!='not_started':
                            call('cancel',rid,phase=phase,reason='User authorized four-hour batch budget exhausted; protected FFT untouched')
                        state['runs'][rid]['budget_cancelled']=True;failed.add(rid);done.add(rid)
                    elif sim=='complete' and ana=='not_started':state['runs'][rid]['analysis_submission']=call('analyze',rid)
                except Exception as exc:
                    state['runs'][rid]=dict(status='needs_reconciliation',error=str(exc));done.add(rid);failed.add(rid)
            # Completed waveform cache can otherwise fill this account's cgroup.
            for rid in sorted(set(r['source_run_id'] for r in b['runs'])|set(state['results'])):
                if rid in cache_done:continue
                try:
                    receipts=cache_release(agent,rid)
                    if receipts:state['cache_releases']+=receipts;cache_done.add(rid)
                except Exception as exc:state['cache_note']=str(exc)
            pilots=[r for r in b['runs'] if r['pilot']]
            gate=all(r['run_id'] in state['results'] and state['results'][r['run_id']]['pass_diagnostic'] for r in pilots)
            state['pilot_gate']=gate
            pilot_failed=any(r['run_id'] in failed or (r['run_id'] in state['results'] and not state['results'][r['run_id']]['pass_diagnostic']) for r in pilots)
            eligible=[r for r in waiting if r['pilot'] or gate]
            estimate=max([1200.]+durations)*1.25+300
            state['estimated_next_case_seconds']=estimate
            if time.time()>=b['deadline_epoch']:
                for row in waiting:skipped.add(row['run_id']);done.add(row['run_id'])
            elif not pilot_failed:
                for row in eligible[:max(0,state['max_inflight_runs']-active)]:
                    rid=row['run_id']
                    if b['deadline_epoch']-time.time()<estimate:
                        skipped.add(rid);done.add(rid);continue
                    try:state['runs'][rid]['submission']=call('submit',rid)
                    except Exception as exc:
                        state['runs'][rid]=dict(status='needs_reconciliation',error=str(exc));done.add(rid);failed.add(rid)
            if pilot_failed and active==0:
                state['status']='pilot_review_required';save();return
            if len(done)==len(b['runs']):
                state['status']='complete' if not failed and not skipped and all(r['pass_diagnostic'] for r in state['results'].values()) else 'finished_with_issues_or_budget_limit'
                save();return
            save();time.sleep(20)


if __name__=='__main__':run(sys.argv[1])
