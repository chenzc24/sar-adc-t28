"""Isolated frozen-candidate PVT checks. Never edit OA or a previous case."""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import json
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/sar8_pvt_mismatch'
VERIFY = ROOT / 'verification/sar8_pvt_mismatch'
REMOTE = '/tmp/virtuoso_bridge_chenzc_intern25/90590/sar8_pvt_mismatch_20261024'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

idle = load('pvt_candidate', 'scripts/sar8_idle_performance/flow.py')
native = load('pvt_native', 'scripts/sar8_r4_idle/flow.py')
base = native.base
base.OUT = OUT; base.REMOTE = REMOTE
read, dump, sha = idle.read, idle.dump, idle.sha

def audit():
    OUT.mkdir(parents=True, exist_ok=True)
    dut, raw = idle.candidate()
    cells = base.cells(dut)
    old = load('pvt_old_comp', 'scripts/strongarm8/run.py')
    comp = old.dut_block(old.source())
    same = idle.blocks(comp)['sar_strongarm_t28'] == idle.blocks(cells['sar_strongarm_t28'])['sar_strongarm_t28']
    assert same, 'Comparator differs from previously characterized source'
    deck = (ROOT / 'netlist/sar8_physical/tt_nominal.scs').read_text()
    model = re.search(r'include "([^"]+)" section=pre_simu', deck)[1]
    with (OUT/'preflight.log').open('w') as f, contextlib.redirect_stdout(f):
        from virtuoso_bridge.spectre.runner import SpectreSimulator
        sim = SpectreSimulator.from_env(profile='t28_io', work_dir=OUT/'license', timeout=60)
        lic = sim.check_license()
        ssh = base.client()
        resources = base.command(ssh, 'hostname; uptime; nproc; free -m; df -h /tmp; pgrep -a -u chenzc_intern25 -x spectre || true')
        # Only the public interface section names and hash, not proprietary model bodies.
        info = base.command(ssh, 'sha256sum '+shlex.quote(model)+'; grep -iE "^[[:space:]]*(section|\\.lib)[[:space:]]" '+shlex.quote(model))
    required = ['ttmacro_mos_moscap','ssmacro_mos_moscap','ffmacro_mos_moscap',
                'ttglobalcorner_localmc_mos_moscap','tt_mom']
    assert all(re.search(r'(?im)^\s*(?:section|\.lib)\s+'+x+r'\s*$', info) for x in required), info
    result = dict(candidate_sha256=idle.EXPECTED, candidate_source='027b951',
        comparator_source_equal=same, comparator_load='native integrated MOM multi=2 per output plus real logic; NOT old 5/20 fF lumped bench',
        model_file=model, model_sha256=info.split()[0], sections=sorted(set(re.findall(r'(?im)^[ \t]*(?:section|\.lib)[ \t]+(\w+)[ \t\r]*$',info))),
        passive_policy='TT MOM/resistor/metal; this is MOS PVT, not full passive-corner signoff',
        cdac='18 aggregate instances, 512 nominal units; NOT proven independent local mismatch',
        simulator={k:lic.get(k) for k in ['ok','spectre_path','version']}, resources=resources,
        profile='t28_io', OA_changed=False, preflight_pass=bool(lic.get('ok')),
        historical_stress_screen_v={'core':.99,'io18':1.98},
        stress_limit_status='historical screen, native model CMI authoritative; not foundry reliability signoff')
    dump(VERIFY/'audit.json', result)
    assert lic.get('ok'), lic
    print(json.dumps({k:v for k,v in result.items() if k!='sections'},indent=2))

def write_case(name, text, ctx, monitor=True):
    folder=OUT/name
    assert not folder.exists(), 'Immutable case already exists: '+name
    folder.mkdir(parents=True)
    (folder/'test.scs').write_text(text)
    # Dispatcher always uploads this observer; harmless unused in probe decks.
    (folder/'r4_perf_monitor.va').write_bytes((base.prior.SOURCE/'r4_perf_monitor.va').read_bytes())
    ctx.update(name=name, deck_sha256=sha(folder/'test.scs'),
               spectre_args=['+preset=cx','+mt=4','+lqtimeout','60'], OA_changed=False)
    dump(folder/'context.json',ctx)

def probes():
    assert read(VERIFY/'audit.json')['preflight_pass']
    dut,_=idle.candidate(); c=base.cells(dut)
    header=(ROOT/'netlist/sar8_physical/tt_nominal.scs').read_text().split('include "dut.scs"')[0]
    header=header.replace('section=ttmacro_mos_moscap','section=ttglobalcorner_localmc_mos_moscap')
    # Native independent MOM units + identical MOS pair. Physical currents, not just RV count.
    flat=re.sub(r'\\\n\s*',' ', c['sar_strongarm_t28'])
    mos=re.search(r'(?m)^\s*MNINP .*$',flat)[0].strip()
    mos=mos[mos.index('nch_mac'):]
    cap='cfmom_2t nr=8 lr=2u w=50n s=50n stm=1 spm=3 multi=1 mismatchflag=1'
    circuits='\nVD (D 0) vsource dc=0.45\nVG (G 0) vsource dc=0.45\n'
    circuits+='M1 (D G 0 0) '+mos+'\nM2 (D G 0 0) '+mos+'\n'
    for i in range(2):
        circuits+=f'VC{i} (C{i} 0) vsource dc=0.45 mag=1\nC{i} (C{i} 0) {cap}\n'
    for seed in [9031,9032,9033,9034,9031]:
        name='activation_'+str(seed)+('_repeat' if seed==9031 and (OUT/'activation_9031').exists() else '')
        text=header+circuits+'\nopts options temp=27\nsaveOptions options save=selected\n'
        text+=f'mc montecarlo numruns=1 seed={seed} variations=mismatch sampling=standard donominal=no savemismatchparams=yes mismatchparamfile="params.txt" savefamilyplots=yes savedatainseparatedir=yes {{\nac_probe ac start=1Meg stop=2Meg lin=2\ndc_probe dc\n}}\nsave M1:1 M2:1 VC0:p VC1:p\n'
        write_case(name,text,dict(kind='model_activation',seed=seed,stop_ns=0))
    print('Prepared 4 seeds and deterministic repeated-seed probe')

def smoke():
    assert read(VERIFY/'audit.json')['preflight_pass']
    # Reuse frozen near-Nyquist source and all native terminal save points.
    from types import SimpleNamespace
    a=SimpleNamespace(name='tt_smoke_400',order='msb',rg=1,drive=1,stepcap=6,stop=400,outputstart=0,honor=False)
    base.prepare(a)
    p=OUT/a.name
    assert sha(p/'dut.scs')==idle.EXPECTED
    ctx=read(p/'context.json');ctx.update(kind='tt_smoke',vdd=.9,temperature_c=27,corner='tt')
    dump(p/'context.json',ctx)

def equivalent():
    folder=OUT/'tt_smoke_400'; original=(folder/'test.scs').read_text()
    dut=(folder/'dut.scs').read_text(); cells=base.cells(dut)
    cdac=cells['sar8j_r1_cdac']; count=0
    def expand(m):
        nonlocal count
        line=m[0]; n=int(re.search(r'\bmulti=(\d+)',line)[1]); count+=n
        name=re.match(r'\s*(\w+)',line)[1]
        return '\n'.join(re.sub(r'\bmulti=\d+','multi=1',line).replace(name,name+'_U'+str(i),1) for i in range(n))
    expanded=re.sub(r'(?m)^\s*CMOM[PN]\d+ .*$',expand,cdac)
    assert count==512
    alternate=base.replace_cell(dut,'sar8j_r1_cdac',expanded)
    assert original.count(dut)==1
    ctx=read(folder/'context.json');ctx.update(kind='nominal_independent_equivalence',independent_cdac_units=count)
    write_case('tt_independent_400',original.replace(dut,alternate),ctx)
    (OUT/'tt_independent_400/dut.scs').write_text(alternate)
    ctx=read(OUT/'tt_independent_400/context.json');ctx['DUT_sha256']=sha(OUT/'tt_independent_400/dut.scs')
    dump(OUT/'tt_independent_400/context.json',ctx)

def collect_probes():
    ssh=base.client()
    for name in ['activation_9031','activation_9032','activation_9033','activation_9034','activation_9031_repeat']:
        folder=OUT/name; remote=read(folder/'launch.json')['remote']
        assert base.command(ssh,'cat '+shlex.quote(remote+'/exit_code')).strip()=='0'
        dest=folder/'native'
        if dest.exists():continue
        dest.mkdir()
        for fn,rec in [('spectre.out',False),('test.raw',True)]:
            r=ssh.download(remote+'/'+fn,dest/fn,recursive=rec,timeout=60);assert r.returncode==0,r.stderr
    print('Probes recovered')

def verify_probes():
    import math
    rows=[]
    for name in ['activation_9031','activation_9032','activation_9033','activation_9034','activation_9031_repeat']:
        folder=OUT/name; raw=folder/'native/test.raw'; p=raw/'mc_separate/mc-001'
        log=(folder/'native/spectre.out').read_text(); status=(raw/'logStatus').read_text()
        assert 'spectre completes with 0 errors' in log and re.search(r'mc\s+PASS',status)
        ac=(p/'mc_ac_probe.ac').read_text().split('VALUE')[1]
        dc=(p/'mc_dc_probe.dc').read_text().split('VALUE')[1]
        caps=[-float(re.search(r'"VC'+str(i)+r':p" \(\S+ (\S+)\)',ac)[1])/(2*math.pi*1e6) for i in range(2)]
        currents=[float(re.search(r'"M'+str(i)+r':1" "I" (\S+)',dc)[1]) for i in (1,2)]
        rows.append(dict(name=name,seed=read(folder/'context.json')['seed'],capacitance_f=caps,current_a=currents,log_sha256=sha(folder/'native/spectre.out')))
    assert rows[0]['capacitance_f']==rows[-1]['capacitance_f'] and rows[0]['current_a']==rows[-1]['current_a']
    assert len({tuple(r['capacitance_f']) for r in rows[:4]})==4 and len({tuple(r['current_a']) for r in rows[:4]})==4
    assert all(r['capacitance_f'][0]!=r['capacitance_f'][1] and r['current_a'][0]!=r['current_a'][1] for r in rows)
    dump(VERIFY/'activation.json',dict(pass_activation=True,repeat_seed_exact=True,rows=rows,
        scope='Native nMOS and independent CDAC MOM local mismatch activation only; not integrated mismatch qualification'))
    print('MOS/MOM variation and seed repeat: PASS')

def reduce_start(names):
    ssh=base.client()
    for name in names:
        folder=OUT/name;ctx=read(folder/'context.json');remote=read(folder/'launch.json')['remote']
        assert base.command(ssh,'cat '+shlex.quote(remote+'/exit_code')).strip()=='0'
        assert not (folder/'reduction.json').exists()
        keys=['SAMPLE','VDD!','VINP_SRC','VINN_SRC','VINP','VINN','VREFP','VREFN',
              'XDUT.TOPP','XDUT.TOPN','XDUT.COMP_P','XDUT.COMP_N','XDUT.SAMPLE_INT','XDUT.SEQ_SAMPLE',
              'XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK','XDUT.RST_DONE',
              'XDUT.ACTIVE','XDUT.PRESET','XDUT.SAMPLE_MATCH','XDUT.XBOOTP.G','XDUT.XBOOTN.G']
        keys += [f'D{i}' for i in range(8)]+[f'XDUT.XREF.{p}{i}' for p in ['RST','Q','H','L'] for i in range(8)]
        ctx['timing_signals']=[k for k in keys if k in ctx['saved_signals']]
        dump(folder/'reduction_context.json',ctx)
        for path,fn in [(folder/'reduction_context.json','context.json'),(ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py','reduce.py')]:
            r=ssh.upload(path,remote+'/'+fn,timeout=60);assert r.returncode==0,r.stderr
        cmd='cd '+shlex.quote(remote)+' && python reduce.py > reduce.log 2>&1; echo $? > '+shlex.quote(remote+'/reduce_exit')
        pid=base.command(ssh,'nohup sh -c '+shlex.quote(cmd)+' > /dev/null 2>&1 < /dev/null & echo $!')
        dump(folder/'reduction.json',dict(remote=remote,pid=pid.strip(),reducer_sha256=sha(ROOT/'scripts/sar8_pvt_mismatch/reduce_remote.py')))
    print('REDUCTION_SUBMITTED',names)

def reduced_collect(names):
    ssh=base.client()
    for name in names:
        folder=OUT/name;remote=read(folder/'reduction.json')['remote']
        assert base.command(ssh,'cat '+shlex.quote(remote+'/reduce_exit')).strip()=='0'
        for fn in ['reduced.json.gz','spectre.out','test.raw/logStatus','reduce.log']:
            dest=folder/'reduced'/Path(fn).name
            assert not dest.exists(),'Do not overwrite collection'
            dest.parent.mkdir(exist_ok=True)
            r=ssh.download(remote+'/'+fn,dest,timeout=120);assert r.returncode==0,r.stderr
        dump(folder/'reduced_receipt.json',dict(native_exit=0,reduction_exit=0,compressed_sha256=sha(folder/'reduced/reduced.json.gz')))
    print('REDUCED_COLLECTED',names)

POINTS=[('tt_090_27','tt',.9,27),('ss_081_m40','ss',.81,-40),('ss_081_125','ss',.81,125),
        ('ff_099_m40','ff',.99,-40),('ff_099_125','ff',.99,125)]

def inventory_audit():
    dut,_=idle.candidate();cells=base.cells(dut);counts={};comp=[]
    def walk(master,path):
        for m in re.finditer(r'(?m)^\s*(\w+)\s+\(([^)]*)\)\s+(\w+)([^\n]*)',cells[master]):
            name,nodes,model,tail=m.groups();inst=path+'.'+name
            if model in cells:walk(model,inst);continue
            params=dict(re.findall(r'(\w+)=([^\s]+)',tail));multi=float(params.get('multi',params.get('m','1')).strip('()'))
            row=counts.setdefault(model,dict(hierarchical_instances=0,sum_explicit_parallel_multiplier=0))
            row['hierarchical_instances']+=1;row['sum_explicit_parallel_multiplier']+=multi
            if path=='XDUT.XCOMP':comp.append(dict(instance=inst,model=model,parameters=params,nodes=nodes.split()))
    walk('sar_adc8_join_r4','XDUT')
    audit=read(VERIFY/'audit.json')
    audit['sections']=sorted(set(x for x in audit['sections'] if re.fullmatch(r'\w+',x)))
    audit.update(device_inventory=counts,comparator_devices=comp,
        MOM_corner_options=[x for x in audit['sections'] if x.upper().endswith('_MOM')],
        no_ideal_internal_source=not re.search(r'\)\s+(?:vsource|isource|bsource)\b',dut))
    dump(VERIFY/'audit.json',audit)
    # Hash actual PDK and simulator-setting files observed by native Spectre, never copy their bodies.
    log=(OUT/'tt_smoke_400/reduced/spectre.out').read_text()
    paths=sorted(set(p.strip() for p in re.findall(r'(?m)^Reading file:\s+(.+)$',log)
        if ('/home/process/' in p and p.endswith(('.scs','.so'))) or p.endswith(('.cfg','.precfg'))))
    ssh=base.client();hashes=base.command(ssh,'sha256sum '+' '.join(shlex.quote(p) for p in paths))
    audit['native_loaded_dependency_sha256']={line.split(None,1)[1].strip():line.split()[0] for line in hashes.splitlines()}
    dump(VERIFY/'audit.json',audit)
    print('Inventory and native model dependency hashes verified',counts)

def prepare_risks():
    assert read(VERIFY/'gate.json')['pass_preflight']
    original=(OUT/'tt_smoke_400/test.scs').read_text();dut,_=idle.candidate()
    assert original.count(dut)==1
    # Small-signal probes plus full-range reversal; exact midscale allows either adjacent code.
    values=[.81,-.81,0,.25*1.8/256,-.25*1.8/256,.123046875]
    names=[]
    for point,corner,sup,temp in POINTS:
        for kind in ['static','sine']:
            text=original.replace('parameters SUP=0.9','parameters SUP='+str(sup))
            text=text.replace('section=ttmacro_mos_moscap','section='+corner+'macro_mos_moscap')
            text=text.replace('temp=27 tnom=27','temp='+str(temp)+' tnom=27')
            text=text.replace('VREFHIGH (VREFP_SRC 0) vsource dc=SUP','VREFHIGH (VREFP_SRC 0) vsource dc=0.9')
            text,n=re.subn(r'(?m)^(tran_perf tran stop=)400n',r'\g<1>600n',text);assert n==1
            if kind=='static':
                for node,sign in [('VINP',1),('VINN',-1)]:
                    pts=[(0,.45+sign*values[0]/2)]
                    for i,value in enumerate(values[1:],1):
                        # Before next SAMPLE rise at 101 ns (and before bootstrap enable).
                        pts.extend([(i*100+.2,.45+sign*values[i-1]/2),(i*100+.3,.45+sign*value/2)])
                    wave=' '.join(f'{t:g}n {v:.15g}' for t,v in pts)
                    text,n=re.subn(r'(?m)^V'+node+r' \([^\n]+$',f'V{node} ({node}_SRC 0) vsource type=pwl wave=[{wave}]',text);assert n==1
            assert idle.blocks(text)==idle.blocks(dut)
            name=point+'_'+kind;ctx=read(OUT/'tt_smoke_400/context.json')
            ctx.update(kind=kind,corner=corner,vdd=sup,temperature_c=temp,stop_ns=600,
                fixed_vref_v=[0,.9],input_cm_v=.45,frames=6,input_diff_v=values if kind=='static' else None,
                scope='First risk screen only; all startup frames scored; not FFT/INL/DNL/noise qualification')
            write_case(name,text,ctx);names.append(name)
    dump(VERIFY/'setup.json',dict(points=POINTS,cases=names,candidate_DUT_sha256=idle.EXPECTED,
        fixed_reference_v=[0,.9],fixed_input_cm_v=.45,MOM_corner='tt_mom',resistor_corner='tt_res_bip_dio_disres',
        frames_per_stimulus=6,reason='400 ns pilot produced 957 MiB native PSF; bounded first batch to retain all-time-step stress within 20 GiB remote budget',
        concurrency=2,threads_per_case=4,static_input_diff_v=values,sine_hz=4501953.125,sine_dbfs=-1,
        external_ideal=['VDD','reference sources with 50 ohm/4 pF rails','input through 50 ohm per side','10 MHz SAMPLE'],
        no_mismatch=True,no_transient_noise=True,no_PEX=True))
    print('Prepared',names)

def status_all():
    names=read(VERIFY/'setup.json')['cases'];ssh=base.client()
    program='''import os,json,re,time
root=%r
names=%r
rows=[]
for name in names:
 p=os.path.join(root,name)
 def readf(fn):
  q=os.path.join(p,fn)
  return open(q).read() if os.path.exists(q) else ''
 log=readf('spectre.out')
 rows.append(dict(name=name,exit=readf('exit_code').strip(),frames=len(re.findall('R4MEAS,',log)),CMI='WARNING (CMI-' in log,reduce_exit=readf('reduce_exit').strip()))
print(json.dumps(dict(epoch=time.time(),cases=rows)))
'''%(REMOTE,names)
    result=json.loads(base.command(ssh,'python -c '+shlex.quote(program)))
    result['remote_bytes']=int(base.command(ssh,'du -sb '+shlex.quote(REMOTE)).split()[0])
    dump(VERIFY/'status.json',result)
    print(json.dumps(result,indent=2))

def strict_checks():
    status=read(VERIFY/'status.json')
    assert all(c['exit']=='0' for c in status['cases']), 'Wait for the existing batch; never exceed two native jobs'
    for point in ['ff_099_m40','ff_099_125']:
        src=OUT/(point+'_static');ctx=read(src/'context.json')
        text=(src/'test.scs').read_text().replace('tran_perf tran stop=600n','tran_perf tran stop=200n')
        text=text.replace('reltol=1e-6','reltol=1e-7')
        name=point+'_strict200';ctx.update(kind='static',frames=2,stop_ns=200,input_diff_v=ctx['input_diff_v'][:2],accuracy_crosscheck_of=point+'_static')
        write_case(name,text,ctx)
        ctx=read(OUT/name/'context.json');ctx['spectre_args'].append('-preset_override');dump(OUT/name/'context.json',ctx)
    print('Prepared two FF strict-setting checks, first 200 ns only')

def stop_oversized_checks():
    ssh=base.client()
    targets={229560:REMOTE+'/ff_099_m40_strict200/test.scs',229586:REMOTE+'/ff_099_125_strict200/test.scs'}
    program='''import os,signal,json
targets=%r
rows=[]
for pid,deck in targets.items():
 p='/proc/'+str(pid)
 if not os.path.exists(p):
  rows.append(dict(pid=pid,deck=deck,state='already_exited'));continue
 assert os.stat(p).st_uid==os.getuid()
 args=open(p+'/cmdline','rb').read().split(chr(0))
 assert deck in args and open(p+'/comm').read().strip()=='spectre', args
 os.kill(pid,signal.SIGTERM)
 rows.append(dict(pid=pid,deck=deck,state='SIGTERM_sent',argv=args))
print(json.dumps(rows))
'''%targets
    result=json.loads(base.command(ssh,'python -c '+shlex.quote(program)))
    dump(VERIFY/'strict200_interruption.json',dict(reason='Full-node strict 200 ns projected to exceed 20 GiB task storage cap; preserve raw prefix and replace only diagnostic with new bounded window',
         processes=result,raw_deleted=False,main_batch_untouched=True))
    print(result)

def bounded_checks():
    assert (VERIFY/'strict200_interruption.json').exists()
    for point in ['ff_099_m40','ff_099_125']:
        src=OUT/(point+'_static');ctx=read(src/'context.json');report=read(VERIFY/(point+'_static.json'))
        chosen={s['instance'] for s in report['groups'].values()}
        devices=[d for d in ctx['stress_devices'] if d['instance'] in chosen]
        saves={n for d in devices for n in d['nodes'].values() if n!='0'}
        saves.update(['VDD!','SAMPLE','XDUT.PRESET','XDUT.CMP_CLK','XDUT.PHI_U','XDUT.XREF.CAP_CLK'])
        text=(src/'test.scs').read_text().replace('tran_perf tran stop=600n','tran_perf tran stop=80n')
        text,n=re.subn(r'(?m)^save .*$', 'save '+' '.join(sorted(saves)),text);assert n==1
        name=point+'_refine80';ctx.update(kind='stress_window',frames=0,stop_ns=80,
            stress_devices=devices,saved_signals=sorted(saves),current_signals=[],accuracy_crosscheck_of=point+'_static',
            qualification='Selected first-frame stress only, NOT complete frame/code or all-MOS qualification')
        write_case(name,text,ctx)
        ctx=read(OUT/name/'context.json');ctx['spectre_args'].append('-preset_override');dump(OUT/name/'context.json',ctx)
    print('Prepared selected-node 80 ns checks, reltol request 1e-6, maxstep 10 ps')

def summarize():
    setup=read(VERIFY/'setup.json');table=[]
    for point,corner,sup,temp in POINTS:
        a=read(VERIFY/(point+'_static.json'));b=read(VERIFY/(point+'_sine.json'))
        for name in [point+'_static',point+'_sine']:
            assert read(OUT/name/'reduced_receipt.json')['native_exit']==0
        core=max([v for r in [a,b] for g,v in r['groups'].items() if g!='bootstrap'],key=lambda v:v['peak_v'])
        io=max([r['groups']['bootstrap'] for r in [a,b]],key=lambda v:v['peak_v'])
        table.append(dict(point=point,corner=corner,vdd=sup,temperature_c=temp,
            native_completed_frames=len(a['frames'])+len(b['frames']),
            timing_pass=a['all_timing_pass'] and b['all_timing_pass'],idle_pass=a['all_idle_pass'] and b['all_idle_pass'],
            max_conversion_ns=max(f['conversion_ns'] for r in [a,b] for f in r['frames']),
            min_acquisition_ns=min(f['acquisition_ns'] for r in [a,b] for f in r['frames'] if f['acquisition_ns'] is not None),
            startup_static_code_error=a['frames'][0]['code_error_vs_ideal'],
            steady_static_pass=a['post_startup_static_code_pass'],
            steady_static_failures=[f for f in a['frames'][1:] if not f['static_code_pass']],
            static_codes=[f['code'] for f in a['frames']],sine_codes=[f['code'] for f in b['frames']],
            worst_core=core,worst_io=io,CMI=a['CMI'] or b['CMI'],
            native_suppressed_warning_totals={r['name']:r['suppressed_warning_total'] for r in [a,b]},
            observed_stress_pass=not(a['CMI'] or b['CMI'] or a['stress_failure_count'] or b['stress_failure_count'])))
    strict=[read(VERIFY/(n+'.json')) for n in ['ff_099_m40_refine80','ff_099_125_refine80'] if (VERIFY/(n+'.json')).exists()]
    result=dict(candidate_DUT_sha256=idle.EXPECTED,first_batch_cases=10,completed_frames=sum(r['native_completed_frames'] for r in table),
        matrix=table,bounded_accuracy_checks=strict,bounded_accuracy_checks_completed=len(strict)==2,
        strict200_status=read(VERIFY/'strict200_interruption.json'),
        gate=read(VERIFY/'gate.json'),activation=read(VERIFY/'activation.json'),
        scope='Five MOS PVT points with TT passives, six static/reversal and six sine frames per point; NO new FFT/INL/DNL qualification',
        limitations=['Startup accuracy not guaranteed; frame 0 not silently discarded',
            'Sine code changes include aperture/phase changes: not automatically distortion or code errors',
            'Representative nMOS/MOM statistical activation only; integrated MC, pMOS/IO/resistor activation remain future work',
            '445 selected MOS six-terminal-pair waveform screen plus whole-circuit native CMI; not all-node waveform signoff',
            '0.99 V core bound independently observed in native CMI; 1.98 V IO screen retained from prior project evidence',
            'No transient noise, power signoff, PEX or layout; circuit and PDK unchanged'],
        remote_bytes=read(VERIFY/'status.json')['remote_bytes'],
        local_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),
        source_hashes={n:read(OUT/n/'context.json')['deck_sha256'] for n in setup['cases']})
    dump(VERIFY/'results.json',result)
    print(json.dumps(table,indent=2))

def proof():
    names=read(VERIFY/'setup.json')['cases']+['tt_smoke_400','tt_independent_400','ff_099_m40_refine80','ff_099_125_refine80']
    ssh=base.client(); paths=[REMOTE+'/'+n+'/test.scs' for n in names]
    native=base.command(ssh,'sha256sum '+' '.join(shlex.quote(p) for p in paths))
    mapping={line.split(None,1)[1].strip():line.split()[0] for line in native.splitlines()}
    rows=[]
    for n,p in zip(names,paths):
        ctx=read(OUT/n/'context.json');assert mapping[p]==ctx['deck_sha256']==sha(OUT/n/'test.scs')
        rows.append(dict(name=n,remote_deck_sha256=mapping[p],local_match=True,
            monitor_sha256=sha(OUT/n/'r4_perf_monitor.va'),DUT_sha256=ctx['DUT_sha256']))
    ended=base.command(ssh,'cat '+shlex.quote(REMOTE+'/ff_099_m40_strict200/exit_code')+' '+shlex.quote(REMOTE+'/ff_099_125_strict200/exit_code'))
    dump(VERIFY/'provenance.json',dict(remote_deck_checks=rows,interrupted_strict200_exit_codes=ended.split(),
        untouched_readonly_dependencies={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'netlist/sar8_physical/dut.scs',ROOT/'netlist/sar8_r4_idle/idle_cells.scs',ROOT/'config/design_spec.yaml']},
        model_evidence=read(VERIFY/'audit.json')['native_loaded_dependency_sha256'],OA_changed=False,PDK_changed=False))
    print('Remote/local deck identity verified:',len(rows),'Interrupted diagnostic exit codes:',ended.split())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','inventory','probes','smoke','equivalent','prepare_risks','strict','stop_oversized','bounded','summary','proof','status_all','collect_probes','verify_probes','reduce','reduced_collect','launch','status','collect']);p.add_argument('names',nargs='*');a=p.parse_args()
    if a.action=='audit':audit()
    elif a.action=='inventory':inventory_audit()
    elif a.action=='probes':probes()
    elif a.action=='smoke':smoke()
    elif a.action=='equivalent':equivalent()
    elif a.action=='verify_probes':verify_probes()
    elif a.action=='prepare_risks':prepare_risks()
    elif a.action=='status_all':status_all()
    elif a.action=='strict':strict_checks()
    elif a.action=='stop_oversized':stop_oversized_checks()
    elif a.action=='bounded':bounded_checks()
    elif a.action=='summary':summarize()
    elif a.action=='proof':proof()
    elif a.action in ['reduce','reduced_collect']:
        with (OUT/(a.action+'_'+a.names[0]+'.log')).open('a') as f, contextlib.redirect_stdout(f):
            (reduce_start if a.action=='reduce' else reduced_collect)(a.names)
        print(a.action,a.names)
    elif a.action=='collect_probes':
        with (OUT/'collect_probes.log').open('a') as f, contextlib.redirect_stdout(f):collect_probes()
    elif a.action=='launch':
        with (OUT/('dispatch_'+a.names[0]+'.log')).open('x') as f, contextlib.redirect_stdout(f):base.launch(a.names)
        print('Submitted:',a.names)
    elif a.action=='status':base.status(a.names)
    else:
        for name in a.names:base.collect(name)
