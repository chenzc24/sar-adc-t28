"""Immutable Mmain parallel-unit width experiment on frozen SAR8, isolated namespace."""
from pathlib import Path
import contextlib
import json
import re
import shlex
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/sar8_pvt_mismatch'))
import flow as prior
OUT=ROOT/'output/sar8_main_width'
VERIFY=ROOT/'verification/sar8_main_width'
REMOTE='/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_main_width_20261024'
OLD=ROOT/'output/sar8_pvt_mismatch'
base=prior.base
base.OUT=OUT;base.REMOTE=REMOTE
read,dump,sha=prior.read,prior.dump,prior.sha
NAMES=[f'ss_w{k}_bidir' for k in [1,2,3,4]]

def preflight():
    OUT.mkdir(exist_ok=True);VERIFY.mkdir(exist_ok=True)
    from virtuoso_bridge.spectre.runner import SpectreSimulator
    with (OUT/'preflight.log').open('w') as f,contextlib.redirect_stdout(f):
        sim=SpectreSimulator.from_env(profile='t28_io',work_dir=OUT/'license',timeout=60)
        lic=sim.check_license();ssh=base.client()
        resources=base.command(ssh,'hostname; df -h /tmp; free -m; pgrep -a -u chenzc_intern25 -x spectre || true')
        audit=read(ROOT/'verification/sar8_pvt_mismatch/audit.json')
        hashes=base.command(ssh,'sha256sum '+' '.join(shlex.quote(p) for p in audit['native_loaded_dependency_sha256']))
    actual={s.split(None,1)[1].strip():s.split()[0] for s in hashes.splitlines()}
    assert actual==audit['native_loaded_dependency_sha256']
    assert lic.get('ok');prior.idle.candidate()
    dump(VERIFY/'preflight.json',dict(ok=True,simulator={k:lic.get(k) for k in ['ok','version','spectre_path']},
        profile='t28_io',resources=resources,dependencies_sha256=actual,OA_changed=False))
    print('Preflight PASS')

def design(width):
    dut,_=prior.idle.candidate()
    cell=re.search(r'(?ms)^subckt sar_bootstrap_flat_8b_p .*?^ends sar_bootstrap_flat_8b_p',dut)[0]
    lines=cell.splitlines();start=next(i for i,s in enumerate(lines) if s.lstrip().startswith('Mmain '));end=start
    while lines[end].rstrip().endswith('\\'):end+=1
    old='\n'.join(lines[start:end+1]);assert 'w=1u multi=1 nf=1' in old
    add='\n'.join(old.replace('Mmain ',f'Mmain_U{i} ',1) for i in range(1,width))
    newcell=cell.replace(old,old+('\n'+add if add else ''),1)
    assert dut.count(cell)==1
    candidate=dut.replace(cell,newcell,1)
    # Exact inverse replacement proves no other subcircuit changed.
    assert candidate.replace(newcell,cell,1)==dut
    if width==1:assert candidate==dut
    return dut,candidate

def prepare(name,width,source,values=None):
    folder=OUT/name;assert not folder.exists()
    old,dut=design(width);text=(OLD/source/'test.scs').read_text()
    assert text.count(old)==1;text=text.replace(old,dut)
    ctx=read(OLD/source/'context.json')
    if values is not None:
        for node,sign in [('VINP',1),('VINN',-1)]:
            pts=[(0,.45+sign*values[0]/2)]
            for i,v in enumerate(values[1:],1):pts.extend([(i*100+.2,.45+sign*values[i-1]/2),(i*100+.3,.45+sign*v/2)])
            wave=' '.join(f'{t:g}n {v:.15g}' for t,v in pts)
            text,n=re.subn(r'(?m)^V'+node+r' \([^\n]+$',f'V{node} ({node}_SRC 0) vsource type=pwl wave=[{wave}]',text);assert n==1
        ctx['input_diff_v']=values
    # Save set unchanged: parallel main devices have exactly the same terminal nodes.
    folder.mkdir(parents=True);(folder/'test.scs').write_text(text);(folder/'dut.scs').write_text(dut)
    (folder/'r4_perf_monitor.va').write_bytes((OLD/source/'r4_perf_monitor.va').read_bytes())
    ctx.update(name=name,total_main_width_um=width,unit_main_width_um=1,main_parallel_units=width,
        width_implementation='Explicit identical 1um/150nm units, no shared diffusion. Original Mmain retained.',
        reference_case=source,deck_sha256=sha(folder/'test.scs'),DUT_sha256=sha(folder/'dut.scs'),
        source_DUT_sha256=prior.idle.EXPECTED,OA_changed=False,
        stress_scope='Original selected device terminal nodes; parallel Mmain units share all four nodes')
    dump(folder/'context.json',ctx)
    print('Prepared',name,ctx['DUT_sha256'])

def sweep():
    assert read(VERIFY/'preflight.json')['ok']
    for width,name in enumerate(NAMES,1):prepare(name,width,'ss_081_m40_static',[.81,-.81,.81,-.81,0,.123046875])
    dump(VERIFY/'setup.json',dict(sweep=NAMES,source='77d4426 / candidate 027b951',
        candidate_original_sha256=prior.idle.EXPECTED,concurrency=2,threads=4,
        selection_limit_v=.25*1.8/256,scope='No mismatch/noise/PEX; fixed reference .9V and input CM .45V'))

def pvt():
    selection=read(VERIFY/'selection.json');assert selection['selected_width_um'] is not None
    width=selection['selected_width_um'];names=[]
    for point,corner,sup,temp in prior.POINTS:
        for kind in ['static','sine']:
            name=f'w{width}_{point}_{kind}';prepare(name,width,point+'_'+kind);names.append(name)
    setup=read(VERIFY/'setup.json');setup.update(pvt=names,selected_width_um=width);dump(VERIFY/'setup.json',setup)

def launch(names):
    with (OUT/('dispatch_'+names[0]+'.log')).open('a') as f,contextlib.redirect_stdout(f):base.launch(names)
    print('Submitted',names)

def status():
    ssh=base.client();names=[p.parent.name for p in OUT.glob('*/launch.json')]
    program='''import os,json,re
root=%r
rows=[]
for name in %r:
 def readf(fn):
  p=os.path.join(root,name,fn)
  return open(p).read() if os.path.exists(p) else ''
 log=readf('spectre.out')
 rows.append(dict(name=name,exit=readf('exit_code').strip(),frames=len(re.findall('R4MEAS,',log)),reduce_exit=readf('reduce_exit').strip()))
print(json.dumps(rows))
'''%(REMOTE,names)
    rows=json.loads(base.command(ssh,'python -c '+shlex.quote(program)))
    result=dict(cases=rows,remote_bytes=int(base.command(ssh,'du -sb '+shlex.quote(REMOTE)).split()[0]))
    dump(VERIFY/'status.json',result);print(json.dumps(result,indent=2));return result

def reduce(names):
    ssh=base.client()
    for name in names:
        folder=OUT/name;remote=read(folder/'launch.json')['remote'];ctx=read(folder/'context.json')
        assert base.command(ssh,'cat '+shlex.quote(remote+'/exit_code')).strip()=='0'
        assert not (folder/'reduction.json').exists()
        ctx['timing_signals']=[s for s in ctx['saved_signals'] if s.startswith(('VIN','D')) or s in ['SAMPLE','VDD!','VREFP','VREFN']
            or s.startswith(('XDUT.XBOOT','XDUT.XREF.RST','XDUT.XREF.Q','XDUT.XREF.H','XDUT.XREF.L'))
            or s in ['XDUT.TOPP','XDUT.TOPN','XDUT.COMP_P','XDUT.COMP_N','XDUT.SAMPLE_INT','XDUT.SEQ_SAMPLE','XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK','XDUT.RST_DONE','XDUT.ACTIVE','XDUT.PRESET','XDUT.SAMPLE_MATCH']]
        dump(folder/'reduction_context.json',ctx)
        for src,dst in [(folder/'reduction_context.json','context.json'),(ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py','reduce.py')]:
            r=ssh.upload(src,remote+'/'+dst,timeout=60);assert r.returncode==0,r.stderr
        cmd='cd '+shlex.quote(remote)+' && python reduce.py > reduce.log 2>&1; echo $? > '+shlex.quote(remote+'/reduce_exit')
        pid=base.command(ssh,'nohup sh -c '+shlex.quote(cmd)+' > /dev/null 2>&1 < /dev/null & echo $!')
        dump(folder/'reduction.json',dict(remote=remote,pid=pid.strip(),reducer_sha256=sha(ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py')))
    print('Reduction submitted',names)

def collect(names):
    # Reuse proven collector, rebinding only the new task root.
    prior.OUT=OUT
    prior.reduced_collect(names)

if __name__=='__main__':
    action=sys.argv[1];names=sys.argv[2:]
    if action in ['preflight','sweep','pvt','status']:globals()[action]()
    elif action in ['launch','reduce','collect']:
        with (OUT/(action+'_'+names[0]+'.log')).open('a') as f,contextlib.redirect_stdout(f):globals()[action](names)
        print(action,names)
