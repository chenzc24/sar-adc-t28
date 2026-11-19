"""Native block/mixed tests and the existing TT-short view adapter."""
import hashlib
import json
from pathlib import Path
import re
import time
from . import views

ROOT=Path(__file__).resolve().parents[2]
PROFILES=['current','behavioral','comparator_xtor','cdac_xtor','sampler_xtor','control_xtor']
NATIVE_CODES=[0,12,127,128,243,255]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def adapt_short(blobs,context,root):
    """Mixed TT tests observe public top nodes, never assumed transistor internals."""
    text=blobs['test.scs'].decode('utf-8')
    text='\n'.join(line for line in text.splitlines() if not line.startswith(('XMEASURE','ahdl_include','save ')))
    pins=' '.join('D%d'%k for k in range(8))
    text+='\nahdl_include "observer.va"\nXPROBE (%s SAMPLE VDD! 0) b_behavior_observer\n'%pins
    text+='save '+pins+' SAMPLE VDD! XDUT.CMP_CLK XDUT.PHI_U XDUT.SEQ_SAMPLE XDUT.COMP_N XDUT.COMP_P\n'
    blobs['test.scs']=text.encode('utf-8')
    blobs['observer.va']=(root/'tb/behav/observer.va').read_bytes()
    for filename in ['analyze_modules.py','native_stream.py']:
        blobs[filename]=(root/'tools/saradc/measure'/filename).read_bytes()
    codes=list(context['expected_codes'])
    context.update(module_validation=True,profiles=[context['design_view']],expected_codes=codes,
                   frame_origin_s=100.05e-9,period_s=100e-9,fault_profile=None,
                   instance_names=['xdut'],pin_prefixes=[''],native_unit_tests=False,
                   signals=['d%d'%k for k in range(8)]+['sample','vdd!','xdut.cmp_clk','xdut.phi_u','xdut.seq_sample','xdut.comp_n','xdut.comp_p'],
                   measured_scope='TT public-pin codes and electrical event counts; inherited settling-band allocation is not a measured settling verdict')


def prepare(run_id='sar8-modules-v3'):
    from .__main__ import engine
    engine().valid_id(run_id)
    dest=ROOT/'work/behav'/run_id
    if dest.exists():raise ValueError('Existing prepared identity; use its frozen recipe or choose a new ID after a real change')
    dest.mkdir(parents=True)
    # One native run contains the module tests and six small mixed top tests.
    blobs=views.build('current')
    source_top=blobs.pop('top/adc_top.scs').decode('utf-8')
    blobs['dut.scs']=blobs['dut.scs'].replace(b'include "top/adc_top.scs"',b'')
    for p in (ROOT/'design/behav/veriloga').iterdir():
        if p.suffix in {'.va','.vh'}:blobs[p.name]=p.read_bytes()
    includes=''.join('ahdl_include "'+p+'"\n' for p in sorted(blobs) if p.endswith('.va'))
    common=views.build('behavioral')['dut.scs'].decode('utf-8')
    wrappers=common[common.index('subckt b_sampler_bridge'):common.index('simulator lang=spectre')]
    text=includes+wrappers+'\n'
    for index,name in enumerate(PROFILES):
        top=source_top if name=='current' else views.build(name)['top/adc_top.scs'].decode('utf-8')
        top=top.replace('sar_adc8_join_r4','profile_'+name)
        top=re.sub(r'\bb_sar\s*$', 'b_sar model_id='+str(index),top,flags=re.M)
        text+=top+'\n'
    text+='''subckt profile_stuck D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD VINN VINP VREFN VREFP VSS
XVA (D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD VINN VINP VREFN VREFP VSS) sar_adc_b force_stuck=1 model_id=6
ends profile_stuck
'''
    blobs['profiles.scs']=text.encode('utf-8')
    # Reuse the actual B platform includes, without its historical monitor.
    old=(ROOT/'tb/top/short/test.scs').read_text(encoding='utf-8')
    platform='\n'.join(line for line in old.splitlines() if line.startswith('include "/home/process/') or line.startswith('include "library_include'))
    deck=['simulator lang=spectre','global 0 VDD!',platform,'include "dut.scs"','include "profiles.scs"',
          'ahdl_include "observer.va"','VVDD (VDD! 0) vsource dc=0.9',
          'VSAMPLE (sample 0) vsource type=pulse val0=0 val1=0.9 delay=60n rise=100p fall=100p width=39.9n period=100n']
    vp=[];vn=[]
    for i,k in enumerate(NATIVE_CODES):
        diff=-.9+(k+.5)*1.8/256
        t=0 if not i else (i*100+59.8)*1e-9
        for points,sign in [(vp,1),(vn,-1)]:
            value=.45+sign*diff/2
            points.append((t,value))
    def wave(points):
        out=['0 %.17g'%points[0][1]]
        for (t,prev),(nt,nv) in zip(points,points[1:]):
            out+=['%.17g %.17g'%(nt,prev),'%.17g %.17g'%(nt+.1e-9,nv)]
        return ' '.join(out)
    deck+=['VIP (vps 0) vsource type=pwl wave=['+wave(vp)+']','VIN (vns 0) vsource type=pwl wave=['+wave(vn)+']']
    names=PROFILES+['stuck'];saves=['sample','VDD!','unit_hold','unit_outn','unit_outp','unit_clk']
    for i,name in enumerate(names):
        pins=' '.join('d%d_%d'%(i,k) for k in range(8))
        deck+=['X%d (%s sample VDD! vn%d vp%d rn%d rp%d 0) profile_%s'%(i,pins,i,i,i,i,name),
               'XM%d (%s sample VDD! 0) b_behavior_observer model_id=%d'%(i,pins,i),
               'RIP%d (vps vp%d) resistor r=50'%(i,i),'RIN%d (vns vn%d) resistor r=50'%(i,i),
               'VRP%d (rps%d 0) vsource dc=0.9'%(i,i),'VRN%d (rns%d 0) vsource dc=0'%(i,i),
               'RRP%d (rps%d rp%d) resistor r=50'%(i,i,i),'RRN%d (rns%d rn%d) resistor r=50'%(i,i,i),
               'CRP%d (rp%d 0) capacitor c=4p'%(i,i),'CRN%d (rn%d 0) capacitor c=4p'%(i,i)]
        for bit in range(8):
            deck.append('CL%d_%d (d%d_%d 0) capacitor c=5f'%(i,bit,i,bit))
        prefix='X%d.'%i
        if name!='stuck':saves += [prefix+x for x in ['CMP_CLK','PHI_U','SEQ_SAMPLE','COMP_N','COMP_P']]
        if name=='behavioral':saves += [prefix+p+str(k) for p in ['GNN','GNP','GPN','GPP'] for k in range(8)]
    deck+='''VUNIT (unit_in 0) vsource type=pwl wave=[0 0.2 120n 0.2 120.1n 0.8]
XSUNIT (sample unit_hold unit_in VDD! 0) b_sampler
CSUNIT (unit_hold 0) capacitor c=1p
VUC (unit_clk 0) vsource type=pulse val0=0 val1=0.9 delay=5n rise=100p fall=100p width=9.9n period=20n
VUN (unit_n 0) vsource dc=0.45
VUP (unit_p 0) vsource type=pwl wave=[0 0.47 160n 0.47 160.1n 0.43]
XCUNIT (unit_clk unit_outn unit_outp VDD! unit_n unit_p 0) b_comparator offset_v=0.01
CLUN (unit_outn 0) capacitor c=20f
CLUP (unit_outp 0) capacitor c=20f
simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-13 temp=27 method=gear2only
saveOptions options save=selected
tran_modules tran stop=665n maxstep=100p errpreset=moderate
'''.splitlines()
    deck.append('save '+' '.join(saves))
    blobs['test.scs']=('\n'.join(deck)+'\n').encode('utf-8')
    blobs['observer.va']=(ROOT/'tb/behav/observer.va').read_bytes()
    blobs['library_include.scs']=views.standard_cell_library(ROOT)
    for filename in ['analyze_modules.py','native_stream.py']:
        blobs[filename]=(ROOT/'tools/saradc/measure'/filename).read_bytes()
    sources=[ROOT/'specs/views.json',ROOT/'specs/arch.json',*sorted((ROOT/'design/behav').rglob('*.py')),*sorted((ROOT/'design/behav/veriloga').glob('*.*'))]
    context=dict(run_id=run_id,module_validation=True,profiles=names,expected_codes=NATIVE_CODES,
                 frame_origin_s=100.05e-9,period_s=100e-9,fault_profile=6,
                 instance_names=['x%d'%i for i in range(7)],pin_prefixes=['d%d_'%i for i in range(7)],
                 native_unit_tests=True,source_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sources})
    blobs['context.json']=(json.dumps(context,indent=2)+'\n').encode('utf-8')
    blobs['source_spec.json']=(ROOT/'specs/arch.json').read_bytes()
    for name,data in blobs.items():
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    inputs=[dict(name=name,source=(dest/name).relative_to(ROOT).as_posix(),sha256=sha(dest/name)) for name in blobs]
    recipe=dict(schema_version=1,run_id=run_id,design_id='sar8_b_modular',entry='test.scs',analyzer='analyze_modules.py',inputs=inputs,
                resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=1024,
                               max_output_mib=1536,simulation_wall_seconds=7200,analysis_wall_seconds=1800,queue_timeout_seconds=86400),
                spectre_args=['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],summary_signals=['sample'],expected_stop_s=665e-9,
                qualification_scope='TT modular behavior, loaded interfaces and short mixed-level function; no PVT, MC, power or reliability qualification',test_conditions=context)
    p=dest/'recipe.yaml';p.write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8',newline='\n')
    return p.relative_to(ROOT).as_posix()


def publish(source,transfer,status):
    result=json.loads(source.read_text(encoding='utf-8'))
    if not result.get('pass_validation'):raise ValueError('Modular native validation failed; retain its original evidence')
    for name,digest in result['context'].get('source_hashes',{}).items():
        if sha(ROOT/name)!=digest:raise ValueError('Native receipt is for an earlier model source: '+name)
    out=ROOT/'results/behav'
    (out/'modules_native.json').write_bytes(source.read_bytes())
    proof=dict(run_id=status['run_id'],recipe_hash=status['registered']['recipe_hash'],result_sha256=sha(source),collection=transfer)
    (out/'modules_provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    log=source.parent.parent/'spectre.out'
    if log.is_file():
        raw=log.read_text(encoding='utf-8').splitlines();warnings=[]
        for i,line in enumerate(raw):
            if 'WARNING (' in line:warnings.append('\n'.join(raw[max(0,i-1):min(len(raw),i+3)]))
        (out/'modules_warnings.txt').write_text('Run: '+status['run_id']+'\nLog SHA256: '+sha(log)+'\n\n'+'\n\n'.join(warnings)+'\n',encoding='utf-8',newline='\n')
    lines=['# B 版行为模型验证','',
           '当前模型按采样、CDAC、比较器、SAR 和参考控制拆分；Python 与电气 VA 的适用层次分别记录。','',
           '- [数值回归](modules_python.json)：16,400 条既有确定性记录，码字、计数、事件时间保持一致。',
           '- [原生模块与混合测试](modules_native.json)、[来源回执](modules_provenance.json)、[运行状态](modules_status.json)、[原始告警](modules_warnings.txt)。',
           '- [模型审查](model_audit.json)：历史去向、当前源码与哈希。','',
           '原生运行 `'+status['run_id']+'` 的仿真和分析均完成，失败数为 0，共 '+str(result['pin_probes'])+' 次独立输出引脚读取。','',
           '| 视图 | 测试结果 |','| --- | --- |']
    for name in result['profiles']:
        lines.append('| `'+name+'` | '+('强制不响应被识别，未误报完成' if name=='stuck' else '首帧及低/中/高码匹配，8 次比较及参考更新')+' |')
    lines+=['','采样器的跟踪/保持、带 10 mV 偏移的比较器正负输入及复位检查通过；核心全行为视图的 8 位参考门控波形未观察到 NMOS/PMOS 同开。',
            '实际警告代码：`'+'`、`'.join(result['warning_codes'])+'`。原始日志在运行回执的回收目录及服务器保存，端压/数值告警不等于已经通过可靠性或模拟精度验收。','',
            '[首轮测量失败](modules_initial_failure.json)：实例大小写导致内部信号漏存，另一个比较器探针处于复位相位；该次未计为验收通过。',
            '[第二轮资源失败](modules_resource_failure.json)：完整波形超出 768 MiB 磁盘预算；随后去掉未用于分析的数字输出保存项，磁盘预算改为 1536 MiB，RSS 上限仍为 1024 MiB。','',
            '本测试仅验证 TT 功能、模块接口和事件。VA 的电容、输入/驱动及延时参数尚非完整物理等效提取；Bootstrap 启动、栅电荷、PVT/原生失配、端压、功耗及 PEX 使用 current 管级视图。','',
            '历史整机宏模型的 [16,400 帧原生交叉](native_crosscheck.json) 属于上一次源码版本，见 [旧来源](native_provenance.json)，不冒充当前电气模块的波形精度。',
            '数值模型对 B 的 256 个实测中心码及十帧 TT 码字一致；TT 近似时间最大差约 0.13 ns。理想源采样量化与 B 高频码字仍有最多 3 LSB 差异，见 [数值范围](python_crosscheck.json)。','']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    return dict(modular_validation_pass=True,profiles=result['profiles'],pin_probes=result['pin_probes'])


def follow(run_id,poll_s=60,wait_s=172800):
    """One-shot completion of an already registered run; never resimulates it."""
    from .__main__ import engine
    from .behavioral import collect
    e=engine();deadline=time.monotonic()+wait_s;previous=None
    path=ROOT/'work/state/behav'/run_id;path.mkdir(parents=True,exist_ok=True)
    while time.monotonic()<deadline:
        status=e.phase('status',run_id)
        sim=status['simulation'].get('status');analysis=status['analysis'].get('status')
        (path/'status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
        if (sim,analysis)!=previous:
            print(json.dumps(dict(run_id=run_id,simulation=sim,analysis=analysis)),flush=True)
            previous=sim,analysis
        failed={'failed','limit_exceeded','rejected','interrupted'}
        if sim in failed or analysis in failed:raise RuntimeError('Native run retained an unsuccessful phase; inspect '+str(path))
        if sim=='complete':
            if analysis=='not_started':e.phase('analyze',run_id,queue=True)
            elif analysis=='complete':return collect(run_id)
        time.sleep(poll_s)
    raise TimeoutError('Completion wait elapsed; queued/in-flight work was preserved')
