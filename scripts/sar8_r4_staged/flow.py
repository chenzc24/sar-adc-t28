"""Bounded native staged-reset experiments; immutable cases and streamed reads."""
from pathlib import Path
import argparse
import contextlib
import gzip
import hashlib
import json
import os
import re
import shlex
import shutil
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_r4_reset'))
import experiment as prior
from stream_recover import stream
OUT=ROOT/'output/sar8_r4_staged'
REMOTE='/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_r4_staged_20261022'
TOP=prior.TOP
read,dump,cells,compact=prior.read,prior.dump,prior.cells,prior.compact
os.environ['VB_DISABLE_CONTROL_MASTER']='1'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def client():
    from virtuoso_bridge import VirtuosoClient
    return VirtuosoClient.from_env(profile='t28_io',timeout=30,log_to_ciw=False).ssh_runner


def command(ssh,cmd,timeout=30):
    r=ssh.run_command(cmd,timeout=timeout)
    assert r.returncode==0,(cmd,r.stderr)
    return r.stdout


def preflight():
    from virtuoso_bridge.spectre.runner import SpectreSimulator
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'preflight.log').open('w') as f,contextlib.redirect_stdout(f):
        sim=SpectreSimulator.from_env(profile='t28_io',work_dir=OUT/'preflight',timeout=60)
        lic=sim.check_license();ssh=client()
        resources=command(ssh,'uptime; free -m; pgrep -a -u chenzc_intern25 -x spectre || true')
    result=dict(simulator={k:lic.get(k) for k in ['ok','spectre_path','version']},resources=resources,
                profile='t28_io',OA_mutations=False,CIW_tunnel='not running; netlist-only SSH route')
    dump(OUT/'preflight.json',result);print(json.dumps(result,indent=2));assert lic.get('ok')


def replace_cell(text,name,block):
    pattern=r'(?ms)^subckt '+name+r' .*?^ends '+name+r'\s*$'
    result,n=re.subn(pattern,lambda m:block.rstrip()+'\n',text)
    assert n==1,name
    return result


def design(order,rg,drive,stepcap):
    text,_=prior.modified_dut('reset_first',20)
    before=cells(text);changed={TOP};new=[]
    ref=before['sar8p_refword'].replace('sar8p_refword','sar8s_refword')
    top=before[TOP].replace('sar8p_refword','sar8s_refword')
    if order!='parallel':
        step=before['sar8p_delay_capture'].replace('sar8p_delay_capture','sar8s_step')
        step,n=re.subn(r'(spm=3 multi=)10\b',rf'\g<1>{stepcap}',step);assert n==2
        new.append(step)
        # Existing SAMPLE still resets request logic promptly. Only store resets stagger.
        seq=[];order_bits=list(range(8)) if order=='lsb' else list(reversed(range(8)))
        for stage,bit in enumerate(order_bits):
            tap='SAMPLE' if stage==0 else f'TAP{stage}'
            if stage:
                source='SAMPLE' if stage==1 else f'TAP{stage-1}'
                seq.append(f'    XRSTEP{stage} ({source} VDD VSS {tap}) sar8s_step')
            seq.append(f'    XRR{bit} (SAMPLE {tap} VDD VSS RST{bit}) sar8p_and2')
            pattern=rf'(XSTORE{bit} \([^\n]+?) SAMPLE VDD VSS\)'
            ref,n=re.subn(pattern,rf'\g<1> RST{bit} VDD VSS)',ref);assert n==1
        seq.append(f'    XRDONE (RST{order_bits[-1]} VDD VSS RST_DONE) sar8p_buf')
        lines=ref.splitlines();lines[0]+=' RST_DONE'
        ref='\n'.join([lines[0],*seq,*lines[1:]])
        top=top.replace('XSEQ (SAMPLE_INT VDD! 0 SEQ_SAMPLE)','XSEQ (RST_DONE VDD! 0 SEQ_SAMPLE)')
        top,n=re.subn(r'(XREF \([^\n]+?) VDD! 0\)(\s+sar8s_refword)',r'\1 VDD! 0 RST_DONE)\2',top);assert n==1
    for bit in range(8):
        old=f'sar8p_refdrv_b{bit}';name=f'sar8s_refdrv_b{bit}'
        if rg==1 and drive==1:continue
        block=before[old].replace(old,name)
        if rg!=1:
            # Native resistor multiplicity doubles parallel paths, preserving each geometry.
            block,n=re.subn(r'(rupolym[^\n]*?\bm=)(\d+)',lambda m:m[1]+str(int(m[2])*rg),block)
            assert n==40,(bit,n)
        if drive!=1:
            block,n=re.subn(r'(?m)(^\s*G(?:NN|NP|PN|PP)C[NP] .*?\bmulti=)(\d+)',
                            lambda m:m[1]+str(int(m[2])*drive),block)
            assert n==8,(bit,n)
        new.append(block);ref=ref.replace(old,name)
    new.append(ref)
    text=replace_cell(text,TOP,top)+'\n'+'\n'.join(new)+'\n'
    after=cells(text)
    assert all(compact(after[k])==compact(v) for k,v in before.items() if k not in changed)
    assert compact(after['sar8j_r1_cdac'])==compact(before['sar8j_r1_cdac'])
    return text,sorted(set(after)-set(before))


def inventory(text):
    c=cells(text);devices=[]
    def walk(master,path,bindings):
        for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)',c[master]):
            name,ns,model,_=m.groups();ns=ns.split();inst=path+'.'+name
            resolved=[bindings.get(n,n if n in ('0','VDD!') else path+'.'+n) for n in ns]
            if model in c:
                ports=c[model].splitlines()[0].split()[2:];assert len(ports)==len(ns),(inst,ports,ns)
                walk(model,inst,dict(zip(ports,resolved)))
            elif model in ('nch_mac','pch_mac','nch_18_mac','pch_18_mac'):
                group=('reference' if inst.startswith('XDUT.XCDAC.') else
                       'comparator' if inst.startswith('XDUT.XCOMP.') else
                       'bootstrap' if inst.startswith(('XDUT.XBOOTN.','XDUT.XBOOTP.')) else
                       'reference_driver' if inst.startswith('XDUT.XREF.XDRV') else
                       'sequencer' if inst.startswith(('XDUT.XSEQ.','XDUT.XREF.XRSTEP','XDUT.XREF.XRR','XDUT.XREF.XRDONE')) else None)
                if group:
                    assert len(ns)==4
                    devices.append(dict(instance=inst,model=model,nodes=dict(zip('dgsb',resolved)),
                                        group=group,limit_v=1.98 if '_18_' in model else .99))
    ports=c[TOP].splitlines()[0].split()[2:];walk(TOP,'XDUT',dict(zip(ports,ports)))
    assert sum(d['group']=='reference' for d in devices)==32
    return devices


def prepare(a):
    assert re.fullmatch(r'[a-z0-9_]+',a.name)
    assert a.rg>=1 and a.drive>=1 and a.stepcap>=1 and 0<=a.outputstart<a.stop
    folder=OUT/a.name;assert not folder.exists(),'Immutable case exists'
    assert sha(prior.FROZEN)==read(ROOT/'netlist/sar8_physical/provenance.json')['files']['dut.scs']
    src=prior.SOURCE/'sine_cx_1024_k461.scs';assert sha(src)==read(prior.SOURCE/'context.json')['deck_sha256']
    dut,new=design(a.order,a.rg,a.drive,a.stepcap);devices=inventory(dut)
    text=src.read_text();frozen=prior.FROZEN.read_text();assert text.count(frozen)==1
    text=text.replace(frozen,dut)
    saves={n for d in devices for n in d['nodes'].values() if n!='0'}
    saves.update(['SAMPLE','XDUT.SAMPLE_INT','XDUT.SEQ_SAMPLE','XDUT.CMP_CLK','XDUT.XCTRL.PHI_W',
                  'XDUT.PHI_U','XDUT.XREF.CAP_CLK','VINP_SRC','VINN_SRC','VINP','VINN','VREFP','VREFN','VDD!'])
    saves.update(f'D{i}' for i in range(8))
    for i in range(8):
        saves.add(f'XDUT.XREF.Q{i}')
        saves.update(f'XDUT.XREF.{x}{i}' for x in ['H','L'])
        if a.order!='parallel':saves.add(f'XDUT.XREF.RST{i}')
    if a.order!='parallel':saves.add('XDUT.RST_DONE')
    # Documented terminal-index form, verified by required signals in the native output.
    currents=['XDUT.XREF.XDRV3.RGNN0:1','XDUT.XREF.XDRV3.RGNN1_5__dmy0:2',
              'XDUT.XREF.XDRV6.RGPP0:1','XDUT.XREF.XDRV6.RGPP1_5__dmy0:2']
    saves.update(currents)
    text,n=re.subn(r'(?m)^tran_perf tran.*$',f'tran_perf tran stop={a.stop}n maxstep=10p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=all outputstart={a.outputstart}n',text);assert n==1
    text,n=re.subn(r'(?m)^save .*$','save '+' '.join(sorted(saves)),text);assert n==1
    folder.mkdir(parents=True)
    (folder/'dut.scs').write_text(dut);(folder/'test.scs').write_text(text)
    (folder/'r4_perf_monitor.va').write_bytes((prior.SOURCE/'r4_perf_monitor.va').read_bytes())
    args=['+preset=cx','+mt=4','+lqtimeout','60']+(['-preset_override'] if a.honor else [])
    ctx=dict(name=a.name,order=a.order,rg_parallel=a.rg,driver_factor=a.drive,stepcap=a.stepcap,
             stop_ns=a.stop,outputstart_ns=a.outputstart,kind='reset_first',spectre_args=args,
             frozen_DUT_sha256=sha(prior.FROZEN),DUT_sha256=sha(folder/'dut.scs'),deck_sha256=sha(folder/'test.scs'),
             monitor_sha256=sha(folder/'r4_perf_monitor.va'),stress_devices=devices,saved_signals=sorted(saves),
             current_signals=currents,added_cells=new,OA_changed=False)
    dump(folder/'context.json',ctx);print('PREPARED',a.name,len(devices),'MOS',len(saves),'signals')


def launch(names):
    raise RuntimeError(
        'Legacy batch launch disabled for new work. Freeze the prepared deck into '
        'management/recipes/<run>.yaml, then use scripts/management/project.py '
        'register / submit. Existing remote batches and legacy status/collect are unchanged.')


def status(names):
    ssh=client()
    for name in names:
        folder=OUT/name
        if (folder/'result.json').exists():print(name,'COLLECTED',read(folder/'result.json')['ok']);continue
        remote=read(folder/'launch.json')['remote'];q=shlex.quote
        summary="awk '/R4MEAS/{frames++} /WARNING \\(CMI-/{cmi++} END{printf \"frames=%d CMI_warnings=%d\\n\",frames,cmi}' "
        cmd=f'if test -f {q(remote+"/exit_code")}; then printf "native_exit="; cat {q(remote+"/exit_code")}; fi; '
        cmd+=f'if test -f {q(remote+"/spectre.out")}; then '+summary+q(remote+'/spectre.out')+'; else printf "queued\\n"; fi; '
        cmd+=f'if test -f {q(remote+"/test.raw/tran_perf.tran.tran")}; then tail -n 2000 {q(remote+"/test.raw/tran_perf.tran.tran")} | grep \'^"time"\' | tail -n 1; fi'
        output=command(ssh,cmd)
        print(name,output[-2000:])


def collect(name):
    folder=OUT/name;ctx=read(folder/'context.json');assert not (folder/'result.json').exists()
    ssh=client();remote=read(folder/'launch.json')['remote'];dest=folder/'spectre'
    assert not dest.exists(),'Do not overwrite partial recovery'
    code=int(command(ssh,'cat '+shlex.quote(remote+'/exit_code')));assert code==0,code
    dest.mkdir()
    with (folder/'collection.log').open('w') as f,contextlib.redirect_stdout(f):
        transfers=[(remote+'/spectre.out',dest/'spectre.out',False)]
        if ctx['stop_ns']<=600 and '-preset_override' not in ctx['spectre_args']:
            transfers.append((remote+'/test.raw',dest/'test.raw',True))
        else:
            raw=dest/'test.raw';raw.mkdir()
            native=remote+'/test.raw/tran_perf.tran.tran';compressed=remote+'/transfer_tran.gz'
            # Unique immutable transfer artifact. Never replace native waveform.
            remote_hash=command(ssh,'sha256sum '+shlex.quote(native),timeout=120).split()[0]
            command(ssh,'test ! -e '+shlex.quote(compressed)+' && gzip -1 -c '+shlex.quote(native)+' > '+shlex.quote(compressed),timeout=600)
            for fn in ['logFile','logStatus']:
                transfers.append((remote+'/test.raw/'+fn,raw/fn,False))
            transfers.append((compressed,dest/'transfer_tran.gz',False))
        for src,target,recursive in transfers:
            r=ssh.download(src,target,recursive=recursive,timeout=600);assert r.returncode==0,r.stderr
        if (dest/'transfer_tran.gz').exists():
            with gzip.open(dest/'transfer_tran.gz','rb') as src,(raw/'tran_perf.tran.tran').open('xb') as target:
                shutil.copyfileobj(src,target,length=1024*1024)
            assert sha(raw/'tran_perf.tran.tran')==remote_hash
            dump(folder/'transfer.json',dict(remote_native_sha256=remote_hash,local_uncompressed_match=True))
    process_local(name,code)


def process_local(name,code):
    folder=OUT/name;ctx=read(folder/'context.json');dest=folder/'spectre'
    assert code==0 and not (folder/'result.json').exists()
    log=(dest/'spectre.out').read_text(errors='replace');native_status=(dest/'test.raw/logStatus').read_text()
    assert 'spectre completes with 0 errors' in log and re.search(r'tran_perf\s+PASS',native_status)
    psf=dest/'test.raw/tran_perf.tran.tran';print('STREAM_READING',name,psf.stat().st_size,flush=True)
    w=stream(psf);expected={'time'}|{s.lower() for s in ctx['saved_signals']}
    assert set(w)==expected,(expected-set(w),set(w)-expected)
    assert w['time'][-1]>=ctx['stop_ns']*1e-9-1e-14
    # Long adaptive records favor uncompressed local arrays: avoid minutes of
    # repeated compression/decompression. Native PSF and hashes remain retained.
    writer=np.savez if ctx['stop_ns']>600 or '-preset_override' in ctx['spectre_args'] else np.savez_compressed
    writer(folder/'wave.npz',**w)
    dump(folder/'wave_receipt.json',dict(sha256=sha(folder/'wave.npz'),points=len(w['time']),signals=list(w)))
    dump(folder/'result.json',dict(ok=True,errors=[],native_exit_code=code,logStatus_PASS=True,
         native_log_sha256=sha(dest/'spectre.out'),psf_sha256=sha(psf),deck_sha256=ctx['deck_sha256'],
         parser='verified prior streaming PSF; every native sample preserved'))
    print('COLLECTED',name,len(w['time']),flush=True)


def await_collect(name):
    folder=OUT/name;assert not (folder/'result.json').exists()
    remote=read(folder/'launch.json')['remote'];ssh=client();deadline=time.monotonic()+1800
    while True:
        with (folder/'await.log').open('a') as f,contextlib.redirect_stdout(f):
            state=command(ssh,'if test -f '+shlex.quote(remote+'/exit_code')+'; then cat '+shlex.quote(remote+'/exit_code')+'; else printf "pending"; fi').strip()
        if state!='pending':
            assert state=='0',('Native simulation failed',name,state)
            print('NATIVE_COMPLETE',name,flush=True);break
        assert time.monotonic()<deadline,'Bounded wait expired; inspect existing job, never resubmit'
        print('NATIVE_PENDING',name,flush=True);time.sleep(45)
    collect(name)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preflight','prepare','launch','status','collect','await_collect']);p.add_argument('names',nargs='*')
    p.add_argument('--order',choices=['parallel','lsb','msb'],default='parallel');p.add_argument('--rg',type=int,default=1)
    p.add_argument('--drive',type=int,default=1);p.add_argument('--stepcap',type=int,default=6)
    p.add_argument('--stop',type=float,default=600);p.add_argument('--outputstart',type=float,default=0);p.add_argument('--honor',action='store_true')
    a=p.parse_args()
    if a.action=='preflight':preflight()
    elif a.action=='prepare':
        assert len(a.names)==1;a.name=a.names[0];prepare(a)
    elif a.action=='launch':
        path=OUT/('dispatch_'+str(time.time_ns())+'.log')
        with path.open('w') as f,contextlib.redirect_stdout(f):launch(a.names)
        print('Dispatch log:',path)
        for name in a.names:print(name,read(OUT/name/'launch.json')['state'])
    elif a.action=='status':status(a.names)
    elif a.action=='await_collect':
        for name in a.names:await_collect(name)
    else:
        for name in a.names:collect(name)
