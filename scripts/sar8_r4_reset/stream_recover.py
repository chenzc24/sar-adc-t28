"""Bounded scalar-PSF streaming recovery; preserve every native sample.

Only downloaded task results are read. No simulator launch or bridge changes.
"""
import argparse
from array import array
import hashlib
import re
import numpy as np
from experiment import OUT,read,dump,sha


def stream(path):
    state={};series={};groups={};pending_group=None;section=None;sweep=None
    times=array('d');ended=False
    def snapshot():
        assert set(state)==set(series),'Missing or unexpected trace at snapshot'
        for key,buf in series.items():buf.append(state[key])
    with path.open(encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line in ('HEADER','TYPE','SWEEP','TRACE','VALUE','END'):
                section=line
                if line=='END':
                    if times:snapshot()
                    ended=True
                    assert not f.read(1024).strip(),'Unexpected data after END'
                    break
                continue
            if not line:continue
            if section not in ('SWEEP','TRACE','VALUE'):continue
            if section=='SWEEP' and sweep is not None:continue # Sweep properties, not further vectors.
            assert line.startswith('"'),line[:100]
            _,key,tail=line.split('"',2)
            if section=='SWEEP':
                assert sweep is None
                sweep=key
            elif section=='TRACE':
                if tail.strip().startswith('GROUP'):
                    assert tail.strip()=='GROUP 1','Unsupported multi-signal GROUP'
                    pending_group=key
                else:
                    assert key not in series
                    series[key]=array('d')
                    if pending_group is not None:groups[pending_group]=key
                    pending_group=None
            elif section=='VALUE':
                value=float(tail.strip()) # Real-valued transient only; reject unsupported format.
                if key==sweep:
                    if times:snapshot()
                    times.append(value)
                else:
                    name=groups.get(key,key)
                    assert name in series,name
                    state[name]=value
    assert ended and sweep=='time' and len(times)>1
    wave={sweep:np.frombuffer(times,dtype=np.float64)}
    wave.update({k.replace('\\','').lower():np.frombuffer(v,dtype=np.float64) for k,v in series.items()})
    assert np.all(np.diff(wave['time'])>0)
    assert all(len(v)==len(times) and np.isfinite(v).all() for v in wave.values())
    return wave


def verify():
    folder=OUT/'base_cx_500'
    w=stream(folder/'spectre/test.raw/tran_perf.tran.tran')
    old=np.load(folder/'wave.npz')
    assert set(w)==set(old.files)
    for k in w:assert np.array_equal(w[k],old[k]),k
    print('STREAM_PARSER_EXACT_BASELINE_MATCH',len(w['time']),len(w),flush=True)


def recover(name):
    assert name=='reset_first_c20_precise500','Recovery is bounded to the audited stopped helper'
    folder=OUT/name;ctx=read(folder/'context.json')
    assert not (folder/'result.json').exists() and not (folder/'wave.npz').exists()
    log_path=folder/'spectre/spectre.out';log=log_path.read_text(errors='replace')
    raw=folder/'spectre/test.raw';status=(raw/'logStatus').read_text()
    assert 'spectre completes with 0 errors' in log and re.search(r'tran_perf\s+PASS',status)
    assert [int(x) for x in re.findall(r'R4MEAS,(\d+),',log)]==list(range(int(ctx['stop_ns']//100)))
    assert sha(folder/'test.scs')==ctx['deck_sha256']
    psf=raw/'tran_perf.tran.tran'
    print('STREAM_PARSE_START',name,psf.stat().st_size,flush=True)
    wave=stream(psf)
    assert set(wave)=={'time'}|{s.replace('\\','').lower() for s in ctx['saved_signals']}
    assert wave['time'][-1]>=ctx['stop_ns']*1e-9-1e-14
    with psf.open('rb') as f:psf_hash=hashlib.file_digest(f,'sha256').hexdigest()
    print('STREAM_PARSE_VERIFIED',len(wave['time']),flush=True)
    np.savez_compressed(folder/'wave.npz',**wave)
    dump(folder/'wave_receipt.json',dict(sha256=sha(folder/'wave.npz'),points=len(wave['time']),signals=list(wave)))
    dump(folder/'result.json',dict(ok=True,errors=[],
        warnings=sorted(set(re.findall(r'WARNING \(([^)]+)\)',log))),
        deck_sha256=ctx['deck_sha256'],recovery=dict(
            reason='Stopped owned local postprocessing PID38252 after native completion to limit memory use.',
            original_runner_exit_code=None,native_process_exit_code=None,
            native_zero_error_summary=True,native_analysis_PASS=True,
            parser='task-local streaming scalar PSF; exact baseline vector comparison passed',
            psf_sha256=psf_hash,native_log_sha256=sha(log_path),
            basis='Native zero-error summary, logStatus PASS, all frames, PSF END, exact signal set and complete finite waveform')))
    print('STREAM_RECOVERY_COMPLETE',name,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name',nargs='?');a=p.parse_args()
    verify()
    if a.name:recover(a.name)
