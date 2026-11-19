"""Independent module fixtures, composed views, and managed characterization receipts."""
import hashlib,json,re,time
from pathlib import Path
from . import views,candidates
ROOT=Path(__file__).resolve().parents[2]


def digest(blob):return hashlib.sha256(blob).hexdigest()
def catalog(root=None):return json.loads(((root or ROOT)/'specs/block_tests.json').read_text(encoding='utf-8'))


def prepare(run_id,modules=None,view='current',candidate=None,root=None,preview=False):
    root=root or ROOT
    from .__main__ import engine
    engine().valid_id(run_id)
    profile=views.resolve(view,root)
    if profile.get('regression_only'):raise ValueError('Independent module fixtures use current candidates, not a relabelled frozen regression')
    selected=candidates.selected(candidate,root)
    tests=catalog(root)['tests'];modules=list(modules or tests)
    if not modules or len(set(modules))!=len(modules) or set(modules)-set(tests):raise ValueError('Choose known, unique module tests')
    dest=root/'work/blocks'/run_id
    if dest.exists() and not preview:raise ValueError('Prepared identity already exists; resume it without regenerating inputs')
    blobs=views.build(view,root,candidate)
    # Common DUT includes carry native definitions. Required VA helper definitions
    # are also needed for fixture source switches and the SAR electrical environment.
    for path in (root/'design/behav/veriloga').iterdir():
        if path.suffix in {'.va','.vh'}:blobs[path.name]=path.read_bytes()
    common=views.build('behavioral',root)['dut.scs'].decode('utf-8')
    wrappers=common[common.index('subckt b_sampler_bridge'):common.index('simulator lang=spectre')]
    extra=''.join('ahdl_include "'+name+'"\n' for name in sorted(blobs) if name.endswith('.va'))
    # Avoid duplicating wrapper declarations already present in a mixed package.
    if 'subckt b_sampler_bridge' not in blobs['dut.scs'].decode('utf-8'):
        blobs['fixture_models.scs']=(extra+wrappers).encode('utf-8')
    else:blobs['fixture_models.scs']=b'// VA masters already included by dut.scs\n'
    va=views.registry(root)['modules'];mapping={module:(va[module]['va'] if profile[module]=='va' else va[module]['master']) for module in va}
    substitutions={k.upper():v for k,v in mapping.items()}
    timing_names=['sar8p_delay_valid','sar8p_delay_write','sar8p_delay_quiet','sar8p_delay_capture','sar8p_delay_bbm','sar8r_delay','sar8s_step','sar8i_guard','sar8r_edge','sar8p_clkbuf']
    substitutions.update({name:('b_'+name if profile['timing']=='va' else name) for name in timing_names})
    for module in modules:
        text=(root/tests[module]['template']).read_text(encoding='utf-8')
        for key,value in substitutions.items():text=text.replace('@'+key+'@',value)
        if re.search(r'@\w+@',text):raise ValueError('Unresolved fixture placeholder: '+module)
        blobs[module+'_fixture.scs']=text.encode('utf-8')
    if 'sar' in modules:
        sar_view=['behavioral','sar='+profile['sar'],'timing='+profile['timing']]
        overrides={k:v for k,v in (candidate or {}).items() if k in {'sar','timing'}}
        sb=views.build(sar_view,root,overrides)
        # Applying source-level mappings changes only the generated SAR definition
        # file. Keep it private to the standalone environment when needed.
        top=sb['top/adc_top.scs'].decode('utf-8').replace('sar_adc8_join_r4','tb_sar_top')
        stalled=top.replace('tb_sar_top','tb_sar_stalled_top')
        stalled,count=re.subn(r'(\)\s+b_comparator)(?=\s*(?:\n|$))',r'\1 force_stuck=1',stalled)
        if count!=1:raise ValueError('SAR stalled fixture must bind exactly one behavioral comparator')
        if profile['timing']=='va' or profile['sar']=='va':
            # The global source files already use the same selected module views.
            pass
        blobs['sar_environment.scs']=(top+'\n'+stalled).encode('utf-8')
    old=(root/'tb/top/short/test.scs').read_text(encoding='utf-8')
    platform='\n'.join(l for l in old.splitlines() if l.startswith('include "/home/process/') or l.startswith('include "library_include'))
    deck=['simulator lang=spectre','global 0 VDD!',platform,'include "dut.scs"','include "fixture_models.scs"',
          'ahdl_include "block_switch.va"','ahdl_include "observer.va"','VVDD (VDD! 0) vsource dc=0.9']
    if 'sar' in modules:deck.append('include "sar_environment.scs"')
    for module in modules:deck.append('include "'+module+'_fixture.scs"')
    signals=[]
    groups={'sampler':['b_clock','b_in','b_hold'],
            'cdac':['d_pre','d_n','d_p','d_rn','d_rp'],
            'comparator':['c_clock','c_n','c_p','c_outn','c_outp','k_clock','k_n','k_p'],
            'reference':['r_phi','r_reset','r_done']+['r_'+g+str(k) for g in ['gnn','gnp','gpn','gpp'] for k in range(8)],
            'timing':['t_clock']+['t_out'+str(k) for k in range(10)],
            'sar':['s_clock']+['s_d'+str(k) for k in range(8)]+['XSAR.'+n for n in ['CMP_CLK','PHI_U','SEQ_SAMPLE','COMP_N','COMP_P']]}
    groups['sar']+=['XSTALLED.CMP_CLK','XSTALLED.PHI_U']+['f_d'+str(k) for k in range(8)]
    for module in modules:signals.extend(groups[module])
    deck+=['simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-13 temp=27',
           'saveOptions options save=selected','tran_blocks tran stop=665n maxstep=100p errpreset=moderate','save '+' '.join(signals)]
    blobs['test.scs']=('\n'.join(deck)+'\n').encode('utf-8')
    blobs['block_switch.va']=(root/'tb/common/veriloga/block_switch.va').read_bytes()
    blobs['observer.va']=(root/'tb/behav/observer.va').read_bytes()
    blobs['library_include.scs']=views.standard_cell_library(root, blobs['dut.scs'])
    for name in ['analyze_blocks.py','native_stream.py']:blobs[name]=(root/'tools/saradc/measure'/name).read_bytes()
    sources=[root/'specs/block_tests.json',root/'specs/candidates.json',root/'specs/views.json',root/'specs/arch.json',
             *[root/tests[m]['template'] for m in modules],*[root/r['file'] for r in selected.values()],
             *sorted((root/'design/behav/veriloga').glob('*.*')),root/'tb/common/veriloga/block_switch.va',
             root/'tb/behav/observer.va',root/'tools/saradc/blocks.py',root/'tools/saradc/views.py',root/'tools/saradc/candidates.py']
    context=dict(run_id=run_id,modules=modules,module_views=profile,
                 sar_stalled='sar' in modules,
                 candidates={k:{key:v for key,v in row.items() if key!='definitions'} for k,row in selected.items()},
                 expected_codes=[0,12,127,128,243,255],reference_words=[128,0,255,85,170,128],
                 comparator_inputs_v=[.1,-.1,.03,-.03,.003515625,-.003515625,.001,-.001,.0001,-.0001],
                 required_signals=[s.lower() for s in signals],source_hashes={p.relative_to(root).as_posix():digest(p.read_bytes()) for p in sources},
                 conditions=catalog(root)['conditions'],contracts={m:tests[m] for m in modules})
    blobs['context.json']=(json.dumps(context,indent=2)+'\n').encode('utf-8')
    if preview:return blobs
    # Validate all outputs before creating an identity or writing its first input.
    dest.mkdir(parents=True)
    for name,body in blobs.items():
        path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    recipe=dict(schema_version=1,run_id=run_id,design_id='sar8_b_module_characterization',entry='test.scs',analyzer='analyze_blocks.py',
                inputs=[dict(name=n,source=(dest/n).relative_to(root).as_posix(),sha256=digest(b)) for n,b in blobs.items()],
                resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=1024,
                               max_output_mib=1024,simulation_wall_seconds=7200,analysis_wall_seconds=1800,queue_timeout_seconds=86400),
                spectre_args=['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],summary_signals=[signals[0].lower()],expected_stop_s=665e-9,
                qualification_scope='Independent TT module characterization with explicit electrical environments; no PVT, MC, power or SOA signoff',test_conditions=context)
    path=dest/'recipe.yaml';path.write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8',newline='\n')
    return path.relative_to(root).as_posix()


def collect(run_id,root=None):
    root=root or ROOT
    from .__main__ import engine
    transfer=engine().collect(run_id)
    folder=root/transfer['local_path'];source=folder/'derived/result.json'
    if not source.is_file():raise ValueError('No completed module analysis result; keep the run state')
    result=json.loads(source.read_text(encoding='utf-8'))
    if not result.get('analysis_complete'):raise ValueError('Incomplete module analysis')
    dest=root/'results/blocks'/run_id;dest.mkdir(parents=True,exist_ok=True)
    (dest/'result.json').write_bytes(source.read_bytes())
    proof=dict(run_id=run_id,result_sha256=digest(source.read_bytes()),collection=transfer)
    (dest/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    log=folder/'spectre.out'
    source_id=engine().recipe(run_id).get('source',{}).get('run_id')
    if not log.is_file() and source_id:
        source_folder=root/'work/output/managed_execution/runs'/source_id/'collected'
        log=source_folder/'spectre.out'
        if not log.is_file():
            source_transfer=engine().collect(source_id)
            log=root/source_transfer['local_path']/'spectre.out'
    if log.is_file():
        lines=log.read_text(encoding='utf-8').splitlines();warnings=[]
        for i,line in enumerate(lines):
            if 'WARNING (' in line:warnings.extend(lines[max(0,i-1):min(len(lines),i+3)])
        (dest/'warnings.txt').write_text('Run: '+run_id+'\nNative log source: '+(source_id or run_id)+'\nLog SHA256: '+digest(log.read_bytes())+'\n'+'\n'.join(warnings)+'\n',encoding='utf-8')
    return dict(path=dest.relative_to(root).as_posix(),pass_validation=result['pass_validation'],failure_count=len(result['failures']),diagnostics=result.get('diagnostics',[]))


def reanalyze(run_id,source_run_id,root=None):
    root=root or ROOT
    from .__main__ import engine
    e=engine();original=e.recipe(source_run_id)
    names=['analyze_blocks.py','native_stream.py']
    inputs=[dict(name=n,source='tools/saradc/measure/'+n,sha256=digest((root/'tools/saradc/measure'/n).read_bytes())) for n in names]
    spec=dict(schema_version=2,kind='analysis_only',source_run_id=source_run_id,run_id=run_id,
              design_id=original['design_id'],analyzer='analyze_blocks.py',inputs=inputs,resources=original['resources'],
              spectre_args=original['spectre_args'],summary_signals=original['summary_signals'],expected_stop_s=original['expected_stop_s'],
              qualification_scope='Read-only corrected measurements bound to a completed native source',test_conditions=original['test_conditions'])
    p=root/'work/blocks'/run_id/'recipe.yaml';p.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(spec,indent=2)+'\n'
    if p.exists() and p.read_text()!=text:raise ValueError('Analysis identity already has different inputs')
    p.write_text(text,encoding='utf-8')
    e.register(p.relative_to(root).as_posix())
    return e.phase('analyze',run_id,queue=True)


def follow(run_id,poll_s=60,timeout_s=172800):
    from .__main__ import engine
    started=time.monotonic()
    while time.monotonic()-started<timeout_s:
        status=engine().phase('status',run_id);sim=status.get('simulation',{}).get('status');ana=status.get('analysis',{}).get('status')
        print(json.dumps(dict(run_id=run_id,simulation=sim,analysis=ana)),flush=True)
        if sim not in {None,'not_applicable','not_started','submitted','queued','running','waiting','complete'}:raise RuntimeError('Simulation stopped: '+str(sim))
        if ana not in {None,'not_started','submitted','queued','running','waiting','complete'}:raise RuntimeError('Analysis stopped: '+str(ana))
        if sim=='complete' and ana in {None,'not_started'}:engine().phase('analyze',run_id,queue=True)
        elif ana=='complete':return collect(run_id)
        time.sleep(poll_s)
    raise TimeoutError('Managed run remains registered; resume follow with the same ID')
