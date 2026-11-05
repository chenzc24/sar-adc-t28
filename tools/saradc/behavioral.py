"""Shared B specification, generated VA defaults and model cross-validation."""
import bisect
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import shutil

from design.behav.python.sar_adc import AnalogConfig,SarAdcModel

ROOT=Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generated():
    a=load('specs/arch.json');b=a['behavior_models'];t=b['default_timing']
    clock=a['external_clock'];cdac=a['blocks']['cdac'];boot=a['blocks']['bootstrap']
    comp=a['blocks']['comparator'];corners=load(a['verification']['corners'])
    header='// Generated from specs/arch.json by python -m tools.saradc behav generate.\n'
    header+='`ifndef SAR8_B_DEFAULTS\n`define SAR8_B_DEFAULTS\n'
    header+=''.join('`define B_%s %.17g\n'%(key.upper(),value) for key,value in t.items())
    header+='`endif\n'
    lsb=a['input']['lsb_v'];budget=a['error_budget'];ref=a['reference']
    noise={k:budget[k]*lsb for k in ['sampling_noise_rms_lsb','comparator_noise_rms_lsb','reference_noise_rms_lsb','unmodeled_distortion_rms_lsb']}
    amplitude=ref['high_v']*10**(a['targets']['test_level_dbfs']/20)
    jitter=2*math.pi*budget['jitter_frequency_hz']*budget['jitter_rms_s']*amplitude/math.sqrt(2)
    quant=lsb/math.sqrt(12)
    rss=math.sqrt(quant**2+jitter**2+sum(x*x for x in noise.values()))
    projected=20*math.log10(amplitude/math.sqrt(2)/rss)
    lines=['# B 版总设计规格','',
      '本页由 [specs/arch.json](../specs/arch.json) 生成。电气实现是冻结 B，行为模型用于算法与协议交叉验证。测量、工程分配和未定项分别列出。','',
      '## 架构与外部接口','',
      '- 8 bit、10 MS/s，全差分异步 SAR，flat binary CDAC；每侧 255 单位二进制电容加 1 单位 dummy，无桥电容。',
      '- 顶层端口顺序：`'+' '.join(a['interface']['port_order'])+'`。',
      '- 数字输出为 D0..D7，无外部位时钟、BUSY、VALID 或 EOC 引脚。SAMPLE 高电平采样并复位 SAR；下降沿结束采样，内部自主推进 8 位。',
      '- 码字在转换中逐位变化，完成后、下一采样开始前读取。正差分极性为 VINP−VINN。','',
      '| 项目 | 当前定义 |','| --- | --- |',
      '| 核心电源 | 标称 %g V，验证范围 %g–%g V |'%(corners['tt']['vdd_v'],*a['supply_v']),
      '| 参考 | VREFN=%g V、VREFP=%g V，独立于核心电源 |'%(ref['low_v'],ref['high_v']),
      '| 输入 | 标称共模 %g V；差分 %g..%g V，单端 %g..%g V；完整共模范围尚未签核 |'%(a['input']['nominal_common_mode_v'],*a['input']['differential_range_v'],*a['input']['single_ended_nominal_range_v']),
      '| 量化 | 256 码，LSB=%.8f mV；理想边界 −0.9+k·LSB，上边码处理精确相等 |'%(lsb*1e3),
      '| 帧时序 | %g ns：高 %g ns 采样、低 %g ns 转换；启动先低 %g ns 预充，再进入正常周期 |'%tuple(clock[k]*1e9 for k in ['period_s','high_s','conversion_allocation_s','initial_low_s']),
      '| 实际激励 | delay=%g ns，rise/fall=%g/%g ps，width=%g ns；首次下降阈值在 %g ns |'%(clock['spectre_pulse_delay_s']*1e9,clock['source_rise_s']*1e12,clock['source_fall_s']*1e12,clock['spectre_pulse_width_s']*1e9,clock['first_falling_threshold_s']*1e9),
      '| 输入源 | 每端理想源串联 %g Ω |'%a['input']['source_resistance_ohm_per_pin'],
      '| 参考源 | 每轨理想源串联 %g Ω、旁路 %g pF，无片上参考缓冲器 |'%(ref['source_resistance_ohm_per_rail'],ref['decoupling_f_per_rail']*1e12),
      '| 输出负载 | 每位 %g fF；比较器输出及其时钟另有原生 MOM 负载 |'%(a['loading']['digital_output_capacitance_f_each']*1e15),'',
      '## 工况定义','',
      '| 工况 | MOS corner | 温度/°C | VDD/V |','| --- | --- | ---: | ---: |']
    lines += ['| %s | %s | %g | %g |'%(name,c['mos'],c['temperature_c'],c['vdd_v']) for name,c in corners.items() if isinstance(c,dict)]
    lines += ['',
      '各工况的实际 MOS、MOM 与无源模型 section 由冻结用例的 include 决定，不能从 MOS corner 名字推断其他器件角。用例身份见 [tests.json](../specs/tests.json)。','',
      '## 当前晶体管实现','',
      '- Bootstrap：每路 %d 只并联 %g µm/%g nm 的 `%s` 主开关，原生 MOM bootstrap 电容 multi=%d。'%(boot['main_switch_parallel_devices'],boot['main_switch_w_m_each']*1e6,boot['main_switch_l_m']*1e9,boot['main_switch_model'],boot['bootstrap_capacitor']['multi']),
      '- CDAC：18 个 `cfmom_2t` 实例；单位几何 nr=8、lr=2 µm、w=s=50 nm、stm=1、spm=3，multi 按 1..128 缩放。N/P 侧 dummy 分别接 VREFN/VREFP。同单位几何的既有低频 AC 提取约 4.00407 fF，每侧 256 单位约 1.02504 pF；这是有偏置/频率条件的表征值，不是恒定器件值。旧 6.86047 fF 比较值和 512 独立单元的失配统计不归给当前 18 个分组实例。',
      '- 参考开关：L=%g nm，NMOS W=%g nm、PMOS W=%g nm，multi=%d·2^bit。'%(cdac['reference_switch_l_m']*1e9,cdac['n_switch_w_m']*1e9,cdac['p_switch_w_m']*1e9,cdac['switch_multi_lsb_first'][0]),
      '- 比较器：%d MOS StrongARM；输入对 W=%g µm/L=%g nm，尾管 W=%g µm，再生 N/P W=%g/%g nm。'%(comp['MOS_count'],comp['input_pair_w_m']*1e6,comp['input_pair_l_m']*1e9,comp['tail_w_m']*1e6,comp['regeneration_n_w_m']*1e9,comp['regeneration_p_w_m']*1e9),
      '- 数字路径：原生标准单元；真实 RC、清除管、非交叠及模拟/升压域管级电路保留。',
      '- 原生标准单元 masters：`'+'`、`'.join(a['blocks']['standard_cells']['external_masters'])+'`。','',
      '## 时序合同','',
      '每帧正常事件为 8 次比较、8 次写入、8 次参考更新、16 次捕获。逐位 `cmp < write < update < next cmp`，每位两次捕获。新采样取消未完成事件。60 ns 是帧内转换分配，不代表硬件有超时检测引脚。',
      '八个 TT 行为事件间隔取十帧原生边沿的中位数；转换预算来自外部低相位，20 ps 输出平滑和算术正则化属于模型设定。cmp→write 包括比较器及数字接收流水，不是纯比较器再生常数。外部高相位为 40 ns，真实 Bootstrap 导通窗仍由内部栅控波形确定。','',
      '| 行为间隔 | 配置值/ns |','| --- | ---: |']
    for key,value in t.items():
        if key.endswith('_s'):lines.append('| `%s` | %.9f |'%(key,value*1e9))
    lines += ['',
      '该近似未拟合 SS/FF 角，也未包括晶体管局部失配引起的延时分布。真实时序资格由闭环逐位测量确定。模块比较器的 0.75 ns 探针和同 draw 保持差的 0.25 LSB 属于独立诊断 screen，不能代替整帧 deadline 或器件可靠性判据。','',
      '## 性能目标与工程误差分配','',
      '沿用已有 8-bit 工程目标：−1 dBFS 输入时 ENOB≥7 bit（SNDR≥43.9 dB），无缺码、单调，|DNL|≤1 LSB、端点 |INL|≤1 LSB，功耗预算≤1 mW。这些是工程目标；已完成测量的条件和范围见 [results](../results/README.md)。','',
      '| 分配 | RMS/mV |','| --- | ---: |','| 理想量化 | %.6f |'%(quant*1e3)]
    lines += ['| `%s` | %.6f |'%(k,v*1e3) for k,v in noise.items()]
    lines += ['| 20 ps、4.5 MHz 抖动 | %.6f |'%(jitter*1e3),
      '', 'RSS=%.6f mV，分配投影 SNDR=%.6f dB、ENOB=%.6f bit；该 RSS 不是当前 B 版的噪声实测。'%(rss*1e3,projected,(projected-1.76)/6.02),
      'CDAC 建立误差分配 0.25 LSB=%.7f mV。固定增益、偏置、延迟单列，避免并入随机噪声重复计数。'%(0.25*lsb*1e3),
      '', '## 校准、统计与未定项','',
      '- 当前未实现校准器。比较器 200 种子极值只给出已观察到的偏移，不定义所有工艺样本的校准范围。校准范围、步进、权重字长尚未选定。',
      '- 历史 0.25 LSB 偏移分配作为暂定校正后残差目标；当前未校准比较器没有被伪称满足这条线。',
      '- 200 种子模块测试与 SS/FF 冷角各 50 种子闭环的抽样范围见 [monte_carlo.json](../specs/monte_carlo.json)。闭环局部失配仅开启比较器和 CDAC。',
      '- 已有 B 版单个 TT 瞬态噪声种子，见 [噪声对照](../results/noise/comparison.json)；带宽和统计收敛尚未建立。全电路局部失配、PEX、完整共模范围、校准范围/精度、功耗积分收敛及端压可靠性仍分别保留未完成项。',
      '- PDK 给出的端压告警和正式寿命包络分开记录；0.99 V 核心供电上限不能替代“允许多少端压、持续多久”的可靠性签核。','',
      '## 行为视图与交叉验证','',
      '[Python 模型](../design/behav/python/sar_adc.py) 与 [VA 模型](../design/behav/veriloga/sar_adc_b.va) 共用总规格和生成默认参数。无噪声为默认，支持有效位权、偏移、有限建立和比较停滞等参数。',
      '两模型的随机数流不同；确定性交叉逐例比较，随机噪声仅按各自分布建模。物理启动充电、kickback、原生 PDK MC、端压和功耗需要晶体管级模型。',
      '[行为模型说明](../design/behav/README.md)列出模型层次、旧模型审查和运行方法。','']
    return {'design/behav/veriloga/b_defaults.vh':header,'docs/specification.md':'\n'.join(lines)}


def generate():
    for name,text in generated().items():
        p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')


def check_generated():
    for name,text in generated().items():
        if not (ROOT/name).is_file() or (ROOT/name).read_text(encoding='utf-8')!=text:
            raise ValueError('Run behav generate; stale file: '+name)
    a=load('specs/arch.json');manifest=load('design/manifest.json')
    if a['interface']['port_order']!=manifest['subcircuits'][manifest['top']]['ports']:
        raise ValueError('System interface differs from the physical B top')
    defaults=a['behavior_models'].get('module_defaults',{})
    declarations={
        'sampler_ron_ohm':[('sampler.va','ron')],
        'off_resistance_ohm':[('sampler.va','roff')],
        'cdac_unit_c_f':[('cdac.va','unit_c')],
        'cdac_unit_ron_ohm':[('cdac.va','unit_ron')],
        'comparator_input_c_f':[('comparator.va','input_c')],
        'behavioral_output_r_ohm':[(p,'rout') for p in ['comparator.va','sar.va','reference.va']],
        'reference_deadtime_s':[('reference.va','deadtime_s')]}
    scales={'':1,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3}
    for key,rows in declarations.items():
        if key not in defaults:continue
        for filename,param in rows:
            source=(ROOT/'design/behav/veriloga'/filename).read_text(encoding='utf-8')
            tokens=re.findall(r'parameter real '+param+r'=([0-9.eE+-]+)([fpnumk]?)\s',source)
            if not tokens or any(not math.isclose(float(n)*scales[s],defaults[key],rel_tol=1e-12,abs_tol=1e-25) for n,s in tokens):
                raise ValueError('VA default differs from the declared model specification: '+filename+' '+param)
    return {'shared_spec':'specs/arch.json','generated_defaults_match':True,'physical_ports_match':True,'electrical_defaults_match':True}


def stimuli():
    m=SarAdcModel();lsb=m.spec.lsb
    values=[(-m.spec.vref+(k+.5)*lsb,'center') for k in range(256)]
    for k in range(1,256):
        boundary=-m.spec.vref+k*lsb
        values.extend((boundary+delta*lsb,'boundary') for delta in [-1e-6,0,1e-6])
    values.extend((v,'saturation') for v in [-1.1,-.9,0,.9,1.1])
    with (ROOT/'results/fft/b_codes.csv').open(encoding='utf-8') as stream:
        values.extend((float(r['aperture_source_v']),'native_fft_aperture') for r in csv.DictReader(stream))
    return values


SCENARIOS=[
    dict(name='nominal',analog={},timing={},va=''),
    dict(name='sampling_gain_offset',analog={'gain':.999,'sampling_offset_v':.0005},timing={},va='gain=0.999 sampling_offset_v=0.0005'),
    dict(name='positive_offset',analog={'comparator_offset_v':.0017578125},timing={},va='comparator_offset_v=0.0017578125'),
    dict(name='MSB_weight_error',analog={'weight_errors':(0,0,0,0,0,0,0,.01)},timing={},va='weight_error7=0.01'),
    dict(name='finite_DAC_settling',analog={'dac_tau_s':2e-9},timing={},va='dac_tau_s=2n'),
    dict(name='comparison_deadline',analog={},timing={'compare_to_write_s':9e-9},va='compare_to_write_s=9n'),
    dict(name='stuck_bit3',analog={'stuck_bit':3},timing={},va='stuck_bit=3'),
    dict(name='input_dependent_delay',analog={},timing={'comparator_tau_s':80e-12},va='comparator_tau_s=80p'),
]


def local_report():
    check_generated();m=SarAdcModel();values=stimuli()
    failures=[]
    for i,(v,_) in enumerate(values):
        r=m.convert(v)
        if not r.completed or r.code!=m.ideal_code(v) or r.counts!=(8,8,8,16):failures.append(i)
    static=load('results/static/results.json')['b']
    measured=static['midpoints_v']
    center_errors=[]
    for k in range(256):
        v=-.9+(k+.5)*m.spec.lsb
        if bisect.bisect_right(measured,v)!=k:center_errors.append(k)
    fft_rows=list(csv.DictReader((ROOT/'results/fft/b_codes.csv').open(encoding='utf-8')))
    dynamic_deltas=[m.ideal_code(float(r['aperture_source_v']))-int(float(r['code'])) for r in fft_rows]
    native=load('results/migration/original_short.json')['frames'];timing_errors=[];code_errors=[]
    for f in native:
        v=-.9+(f['expected_code']+.5)*m.spec.lsb
        result=m.convert(v)
        if result.code!=f['code_98']:code_errors.append(f['frame'])
        timing_errors.append(result.conversion_s*1e9-f['conversion_ns'])
    report=dict(python_oracle_pass=not failures and not center_errors and not code_errors,
        nominal_test_vectors=len(values),center_codes=256,transition_probes=255*3,
        saturation_probes=5,native_aperture_inputs=len(fft_rows),
        binary_SAR_vs_closed_form_failures=failures,
        measured_static_boundaries=dict(source='results/static/results.json',center_failures=center_errors),
        native_TT_short=dict(source='results/migration/original_short.json',code_failures=code_errors,
            model_minus_native_conversion_ns=timing_errors,max_abs_difference_ns=max(map(abs,timing_errors)),
            interpretation='Median phase model approximation, not exact transistor timing correlation'),
        native_dynamic_comparison=dict(source='results/fft/b_codes.csv',
            different_codes=sum(d!=0 for d in dynamic_deltas),max_abs_difference_lsb=max(map(abs,dynamic_deltas)),
            interpretation='Ideal quantization of measured source-at-aperture values; finite acquisition, offset, gain and phase are absent, so differences are retained'),
        spec_sha256=sha(ROOT/'specs/arch.json'),model_sha256=sha(ROOT/'design/behav/python/sar_adc.py'))
    out=ROOT/'results/behav';out.mkdir(parents=True,exist_ok=True)
    (out/'python_crosscheck.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not report['python_oracle_pass']:raise ValueError('Behavioral oracle discrepancy; see results/behav/python_crosscheck.json')
    return report


def prepare(run_id='sar8-modules-v3'):
    from .modular import prepare as prepare_modules
    check_generated()
    return prepare_modules(run_id)


def collect(run_id):
    from tools.saradc.__main__ import engine
    e=engine();status=e.phase('status',run_id)
    out=ROOT/'results/behav'
    state=ROOT/'work/state/behav'/run_id
    state.mkdir(parents=True,exist_ok=True)
    (state/'status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    if status['simulation'].get('status')!='complete' or status['analysis'].get('status')!='complete':
        raise ValueError('Native simulation and analysis must complete before publishing a verdict')
    transfer=e.collect(run_id)
    folder=ROOT/transfer['local_path']
    source=folder/'derived/result.json'
    result=json.loads(source.read_text(encoding='utf-8'))
    if result.get('module_validation'):
        from .modular import publish
        (out/'modules_status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
        return publish(source,transfer,status)
    (out/'native_status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    if not result.get('analysis_complete') or not result.get('python_VA_crosscheck_pass'):
        raise ValueError('Native behavioral crosscheck failed; retain the collected evidence')
    files={k.replace('\\','/'):v for k,v in result['context']['source_files'].items()}
    for name in ['design/behav/python/sar_adc.py','design/behav/veriloga/sar_adc_b.va',
                 'design/behav/veriloga/b_defaults.vh','tb/behav/observer.va']:
        if sha(ROOT/name)!=files[name]:raise ValueError('Current model source differs from the native run: '+name)
    snapshot_path=ROOT/'work/behav'/run_id/'source_spec.json'
    if not snapshot_path.is_file():
        if run_id!='sar8-behav-cross-v1':
            raise ValueError('The native run has no retained source specification')
        snapshot_path=ROOT/'results/behav/native_source_spec_v1.json'
    if sha(snapshot_path)!=files['specs/arch.json']:
        raise ValueError('Source specification snapshot differs from native registration')
    snapshot=json.loads(snapshot_path.read_text(encoding='utf-8'))
    current=load('specs/arch.json')
    if snapshot['behavior_models']['default_timing']!=current['behavior_models']['default_timing']:
        raise ValueError('Current timing parameters differ from the native source spec')
    for key in ['input','interface','reference','resolution_bits','external_clock']:
        if snapshot[key]!=current[key]:
            raise ValueError('Current behavioral contract differs from the native source spec: '+key)
    shutil.copyfile(source,out/'native_crosscheck.json')
    retained_snapshot=out/'native_source_spec.json'
    shutil.copyfile(snapshot_path,retained_snapshot)
    proof=dict(run_id=run_id,registered_recipe_hash=status['registered']['recipe_hash'],
               result_sha256=sha(source),collection=transfer,
               source_spec_snapshot=retained_snapshot.relative_to(ROOT).as_posix(),
               source_spec_sha256=sha(retained_snapshot),current_spec_sha256=sha(ROOT/'specs/arch.json'),
               current_parameter_and_source_identity=True,
               spec_difference='The exact native spec is retained; current input, interface, timing and model source identities are verified separately',
               native_warning_codes=result['warning_codes'])
    (out/'native_provenance.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return dict(native_crosscheck_pass=True,frame_records=result['frame_records'],
                independent_pin_probes=result['independent_pin_probes'],max_time_error_s=result['max_time_error_s'])
