"""Original30-sample module report and standalone scientific figures."""
import csv,hashlib,json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R=Path(__file__).resolve().parents[2];V=R/'verification/sar8_mc/blocks';F=V/'figures'
REV='v2'
def run_id(family,tag):return 'sar8mc-'+family+'-'+tag+'-'+REV

def load(run):
    p=V/'results'/run/'result.json';d=json.loads(p.read_text())
    receipt=json.loads((V/'result_receipts.json').read_text())[run]
    assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['result_sha256']
    assert d['analysis_complete'] and d['native_data_valid']
    return d

def stats(v):
    a=np.asarray(v,float)
    return {'n':len(a),'mean':float(a.mean()),'std_sample':float(a.std(ddof=1)),'min':float(a.min()),'max':float(a.max())}

def main():
    seeds=list(range(4101,4131));data={f:[load(run_id(f,'s%d'%i)) for i in seeds] for f in ['cdac','comp']}
    nominal={f:load(run_id(f,'nominal')) for f in data}
    repeats={f:load(run_id(f,'s4101-repeat')) for f in data}
    for f,rows in data.items():
        assert [r['context']['seed'] for r in rows]==seeds
        assert len(set(r['mismatch_evidence']['values_sha256'] for r in rows))==30
        assert rows[0]['mismatch_evidence']['values_sha256']==repeats[f]['mismatch_evidence']['values_sha256']
    cd=data['cdac'];co=data['comp'];good=[r for r in co if r['threshold_valid']]
    warnings={f:dict(Counter(k for r in rows for k in r['warning_codes'])) for f,rows in data.items()}
    metrics={'fixture_revision':2,'samples_each':30,'seeds':seeds,'source_dut_sha256':nominal['comp']['context']['parent_dut_sha256'],
        'independent_draws_verified':True,'repeatability_verified':True,
        'cdac':{'dac_dnl_abs_max_lsb':stats([r['weights']['dac_dnl_abs_max_lsb'] for r in cd]),
            'dac_inl_endpoint_abs_max_lsb':stats([r['weights']['dac_inl_endpoint_abs_max_lsb'] for r in cd]),
            'major_carry7_error_lsb':stats([r['weights']['major_carry'][7]['error_lsb'] for r in cd]),
            'monotonic_dac_samples':sum(r['weights']['dac_levels_monotonic'] for r in cd),
            'scope':'Native MOM linearized binary DAC levels at0.45V bias; not complete SAR ADC DNL/INL'},
        'comparator':{'valid_threshold_samples':len(good),'effective_offset_mv':stats([r['offset_midpoint_v']*1e3 for r in good]),
            'nominal_offset_interval_mv':[nominal['comp']['offset_lower_v']*1e3,nominal['comp']['offset_upper_v']*1e3],
            'threshold_resolution_mv':.125,'unresolved_speed_probes':sum(not p['resolved'] for r in co for p in r['speed_probes']),
            'scope':'B core plus defined native receiver/MOM loads; threshold at1.75ns, cm0.45V, TT, no transient noise'},
        'warning_runs_by_code':warnings,'electrical_verdict':'deferred_not_qualified',
        'limitations':['30local-mismatch draws per independent module, no process variation/PVT/noise/PEX or yield signoff',
            'MOM multi-aware mismatch retained; no arbitrary percentage mismatch injected',
            'Comparator input is low-impedance stimulus for threshold measurement: kickback not characterized',
            'Diagnostic5ns clock with2ns high; actual B roughly0.79–1.02ns high is a separate timing reference',
            'DATA register bank and full asynchronous feedback omitted from comparator fixture',
            'Initial v1 ideal-driven CDAC merged P/N instances; those statistics are invalid and retained separately. Revision2 preserves all18MOM instances and uses explicit case-correct saves',
            'AC text precision leaves a small nominal DNL floor; CDAC figures are binary-DAC weight predictions, not ADC transition scans',
            'Same numeric seed in different hierarchies does not guarantee same device sample; whole-chip replay requires explicit sample mapping']}
    boundary=V/'actual_B_boundary.json'
    if boundary.exists():
        b=json.loads(boundary.read_text());metrics['actual_B_boundary']={k:b[k] for k in ['native_cmp_high_ns_range','top_cm_at_evaluation_v_range','scope']}
    wrong=[{'seed':r['context']['seed'],'cycle':p['cycle'],'polarity':p['polarity'],'overdrive_v':p['overdrive_about_estimated_offset_v']} for r in co for p in r['speed_probes'] if p['resolved'] and p['polarity']!=(1 if p['overdrive_about_estimated_offset_v']>0 else -1)]
    metrics['comparator']['speed_wrong_polarity']=wrong
    metrics['comparator']['speed_probe_count']=sum(len(r['speed_probes']) for r in co)
    metrics['comparator']['minimum_reset_output_v']=min(p['reset_min_v'] for r in co for p in r['speed_probes'])
    metrics['comparator']['speed_scope']='Only tested +/-0.1,+/-0.25,+/-1LSB overdrive about each estimated threshold, not arbitrary near-zero/metastability tail'
    delay_groups={}
    for r in co:
        for p in r['speed_probes']:
            key=round(p['overdrive_about_estimated_offset_v']/(1.8/256),4)
            if p['receiver_decision_ns'] is not None:delay_groups.setdefault(key,[]).append(p['receiver_decision_ns'])
    metrics['comparator']['receiver_delay_ns_by_overdrive_lsb']={str(k):stats(v) for k,v in sorted(delay_groups.items())}
    metrics['comparator']['receiver_delay_ns_range']=[min(min(v) for v in delay_groups.values()),max(max(v) for v in delay_groups.values())]
    metrics['comparator']['offset_std_input_lsb']=s_lsb=metrics['comparator']['effective_offset_mv']['std_sample']/(1800/256)
    metrics['warning_run_ids_by_code']={f:{code:[r['context']['run_id'] for r in rows if code in r['warning_codes']] for code in warnings[f]} for f,rows in data.items()}
    metrics['monitor_evidence_files']=['monitor_v2_status.json','monitor_v2_wait_show.json','monitor_v2_evidence.json']
    F.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.25,'figure.dpi':120})
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    errs=np.array([r['weights']['weight_error_lsb'] for r in cd])
    ax[0,0].boxplot(errs,tick_labels=['b%d'%i for i in range(8)],showfliers=True);ax[0,0].set(ylabel='Differential weight error (LSB)',title='Native MOM bit-weight variation')
    carry=np.array([[x['error_lsb'] for x in r['weights']['major_carry']] for r in cd])
    ax[0,1].boxplot(carry,tick_labels=['b%d'%i for i in range(8)]);ax[0,1].set(ylabel='Binary carry-step error (LSB)',title='Carry sensitivity')
    n=np.arange(1,31)
    ax[1,0].plot(n,[r['weights']['dac_dnl_abs_max_lsb'] for r in cd],'o-',label='max |DAC DNL|')
    ax[1,0].plot(n,[r['weights']['dac_inl_endpoint_abs_max_lsb'] for r in cd],'s-',label='max |DAC endpoint INL|');ax[1,0].legend();ax[1,0].set(xlabel='Sample (seeds 4101–4130)',ylabel='LSB',title='Linearized binary-DAC prediction')
    for side in 'PN':
        vals=[100*(r['weights']['total_cap_f'][side]/nominal['cdac']['weights']['total_cap_f'][side]-1) for r in cd]
        ax[1,1].plot(n,vals,'o-',label=side+' array')
    ax[1,1].legend();ax[1,1].set(xlabel='Sample',ylabel='Total capacitance deviation (%)',title='Array total relative to nominal')
    fig.suptitle('B CDAC: 30 local mismatch samples | TT, 27 C | native MOM at 0.45 V bias\nStatic capacitor-weight results; excludes switch settling and full ADC transfer')
    fig.savefig(F/'cdac_30seed.png',dpi=180);fig.savefig(F/'cdac_30seed.svg');plt.close(fig)
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    offsets=np.array([r['offset_midpoint_v']*1e3 for r in good]);s=metrics['comparator']['effective_offset_mv']
    ax[0,0].hist(offsets,bins=10,edgecolor='white');ax[0,0].axvline(s['mean'],color='C1',label='mean %.3f mV, SD %.3f mV'%(s['mean'],s['std_sample']));ax[0,0].legend(fontsize=9);ax[0,0].set(xlabel='Effective input offset (mV)',ylabel='Samples',title='Threshold distribution (%d/30 valid)'%len(good))
    ax[0,1].errorbar(n,[r['offset_midpoint_v']*1e3 for r in co],yerr=[r['offset_width_v']*500 for r in co],fmt='o',capsize=2);ax[0,1].axhline(0,color='grey',lw=.8);ax[0,1].set(xlabel='Sample (seeds 4101–4130)',ylabel='Effective offset (mV)',title='Native search intervals (nominal resolution 0.125 mV)')
    keys=sorted(delay_groups);med=[np.median(delay_groups[k]) for k in keys];low=[np.quantile(delay_groups[k],.05) for k in keys];high=[np.quantile(delay_groups[k],.95) for k in keys]
    ax[1,0].plot(keys,med,'o-',label='Observed median');ax[1,0].fill_between(keys,low,high,alpha=.2,label='Observed 5–95%');ax[1,0].axhline(.75,ls='--',color='C3',label='0.75 ns diagnostic');ax[1,0].legend(fontsize=9);ax[1,0].set(xlabel='Overdrive relative to each sample threshold (LSB)',ylabel='Receiver decision time (ns)',title='Small-signal speed (resolved probes only)')
    history=[]
    for r in co:
        p={x['cycle']:x for x in r['speed_probes']};a=p[19]['receiver_decision_ns'];b=p[21]['receiver_decision_ns'];history.append((b-a)*1e3 if a is not None and b is not None else np.nan)
    ax[1,1].plot(n,history,'o');ax[1,1].axhline(0,color='grey',lw=.8);ax[1,1].set(xlabel='Sample',ylabel='Alternating minus repeated-history delay (ps)',title='History diagnostic: same +0.25 LSB after prior signs',ylim=(-5,5))
    ax[1,1].text(.02,.95,'Sub-ps differences are below diagnostic resolution',transform=ax[1,1].transAxes,va='top',fontsize=9)
    fig.suptitle('B loaded comparator: 30 local mismatch samples | TT, 0.9 V, cm 0.45 V\nThreshold window 1.75 ns; ideal input drive; noise and kickback not characterized')
    fig.savefig(F/'comparator_30seed.png',dpi=180);fig.savefig(F/'comparator_30seed.svg');plt.close(fig)
    with (V/'samples.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['seed','dac_max_abs_dnl_lsb','dac_max_abs_endpoint_inl_lsb','cmp_offset_mv','cmp_offset_width_mv','cmp_threshold_valid'])
        for i,a,b in zip(seeds,cd,co):w.writerow([i,a['weights']['dac_dnl_abs_max_lsb'],a['weights']['dac_inl_endpoint_abs_max_lsb'],b['offset_midpoint_v']*1e3,b['offset_width_v']*1e3,b['threshold_valid']])
    (V/'summary.json').write_text(json.dumps(metrics,indent=2)+'\n')
    d=metrics['cdac'];c=metrics['comparator']
    text='''# B版CDAC／比较器30种子模块结果

2026-11-04，最终采用保留独立实例的v2测试台。

[测试台替代边界与方法](methods.md)。

两模块各30个独立local-mismatch种子，另各有名义和同种子重复对照。全部结果来自
原生PDK／晶体管仿真，并完成实际波形/电流、随机参数及回收哈希检查。TT、0.9V、
27°C，无process variation、瞬态噪声、PVT矩阵或PEX。原B网表未修改。

| 指标 | 结果 |
|---|---:|
| CDAC静态二进制DAC最大绝对DNL，30样本最坏 | %.5f LSB |
| CDAC静态二进制DAC最大绝对端点INL，30样本最坏 | %.5f LSB |
| 比较器有效门限均值 | %.4f mV |
| 比较器有效门限样本标准差 | %.4f mV |
| 比较器有效门限范围 | %.4f～%.4f mV |
| 有效门限搜索 | %d/30 |
| 已测速度探针 | %d/%d次判决，%d次极性错误 |
| 已测接收端判决时间范围 | %.4f～%.4f ns |

CDAC的30组线性化DAC电平全部单调。比较器失调标准差约为%.3f个输入LSB
（1LSB=7.03125mV），当前更应关注比较器的失调预算；这不等于随机噪声，也不
直接代表SNDR损失。速度结果仅覆盖相对各自门限的±0.1、±0.25、±1LSB激励，
未覆盖任意接近零过驱动的亚稳态尾部，不能据此宣布整机时序通过。

![CDAC统计](figures/cdac_30seed.png)

![比较器统计](figures/comparator_30seed.png)

CDAC图是0.45V偏置下原生MOM线性化权重的二进制DAC预测，不是完整SAR转换边界
扫描；开关动态建立、参考下垂和电压依赖仍需独立验证。MOM倍率模型已含失配尺度
归一化，没有给每个大权重任意施加同一个百分比误差。

比较器包含B原强臂、原生输出MOM、两路真实标准单元缓冲及PR/NR逻辑输入负载；
未含全部存储和异步反馈。低阻VA输入用于定义门限，不能测出真实保持输入的反冲。
门限窗口为1.75ns、搜索分辨率0.125mV，诊断时钟不等于整机时序；实际判决延迟
单列。输入失调不直接等于逐周期噪声，也不能直接换算为SNDR损失。

同种子随机标量逐字节复现，模块目标参数及实际电容／门限随种子变化。跨模块或
整机层级变化后，同一seed不保证同一器件抽样，回接需保存参数映射。

原始告警与失败全部保留，本轮没有按种子更换样本。v2的30组随机样本中：

| 原生告警 | 范围／含义 |
|---|---|
| VACOMP-2435、SFE-1131 | 两模块每组均有：旧AHDL环境变量不再支持、模型scalefactor重复定义使用末值 |
| SPECTRE-17191 | 比较器seed4101：初始DC求解放宽容差，可能影响精度 |
| SPECTRE-16780 | 比较器seed4124：12.2393ns处接收器内部节点LTE容差暂时放宽 |

两组数值告警样本已标记并纳入统计，针对性复核前不作为精度签核；原文见
monitor_v2_evidence.json，完整逐运行告警列表见summary.json。旧整机CMI记录仍保留，
本模块结果不授予任何端压豁免。

初版CDAC的理想源导致优化合并、P/N统计完全相关，故已撤回初版统计。
本报告采用v2：preserve_inst=all、18个独立MOM实例和正确大小写的显式保存；
逐个核对抽样参数、P/N实际电容差异及原生向量，保留初版失败解释与数据。AC文本精度
使名义权重DNL有约0.0003LSB数值底限。30种子不构成高置信良率／尾部失效率结论。

逐样本见samples.csv，机器结果、范围和告警见summary.json，各运行回收回执位于results/。
模块状态不等于整机或端压可靠性通过；后续优先评估比较器失调预算及真实输入反冲，
再选择少量明确随机样本回接整机。没有自动调整器件尺寸或采用新基线。
'''%(d['dac_dnl_abs_max_lsb']['max'],d['dac_inl_endpoint_abs_max_lsb']['max'],s['mean'],s['std_sample'],s['min'],s['max'],len(good),c['speed_probe_count']-c['unresolved_speed_probes'],c['speed_probe_count'],len(c['speed_wrong_polarity']),c['receiver_delay_ns_range'][0],c['receiver_delay_ns_range'][1],s_lsb)
    (V/'README.md').write_text(text,encoding='utf-8');print(json.dumps(metrics['cdac']));print(json.dumps(metrics['comparator']))
if __name__=='__main__':main()
