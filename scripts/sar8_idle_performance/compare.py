"""Same-method final metrics/figures; refuses partial full-batch results."""
from pathlib import Path
import json
import numpy as np
from flow import ROOT, OUT, VERIFY, SINE, STATICS, EXPECTED, analyze, read, dump, sha


def figures(result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
    dest = ROOT/'docs/figures/sar8_idle_performance'; dest.mkdir(parents=True, exist_ok=True)
    baseline = result['baseline']; candidate = result['candidate']
    conditions = 'Transistor ADC | TT, 0.9 V, 27 C | 10 MS/s | no transient noise / mismatch / PEX'
    footer = 'Ideal VDD / reference sources / SAMPLE; Rin 50 ohm/side; Rref 50 ohm + Cref 4 pF/rail'
    entries = [('Original R4', baseline, '#cf6b4b'), ('Idle-tail reset', candidate, '#167c87')]
    fig, axes = plt.subplots(3,1,figsize=(11,9),layout='constrained')
    fig.suptitle(conditions,fontsize=11)
    for label, r, color in entries:
        s = r['static']
        axes[0].plot(np.arange(1,255),s['dnl_nominal_lsb'],label=label,color=color,lw=1.2)
        axes[1].plot(np.arange(1,256),s['inl_endpoint_lsb'],label=label,color=color,lw=1.2)
        axes[2].plot(np.arange(1,256),s['inl_raw_lsb'],label=label,color=color,lw=1.2)
    for ax, ylabel in zip(axes,['DNL (LSB)','Endpoint INL (LSB)','Raw transition error (LSB)']):
        ax.set(ylabel=ylabel,xlabel='Code / transition index',xlim=(0,256))
        ax.axhline(0,color='.5',lw=.7);ax.grid(alpha=.2);ax.legend(loc='best')
    fig.supxlabel(footer+'\n255 transitions / 256 code centers; bracket width 1/128 LSB; saturated endpoint widths excluded',fontsize=8)
    fig.savefig(dest/'static_comparison.png',dpi=180);plt.close(fig)

    fig, axes = plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
    fig.suptitle(conditions,fontsize=11)
    for ax, (label,r,color) in zip(axes,entries):
        d=r['dynamic']
        ax.plot(np.array(d['frequency_axis_hz'])/1e6,d['spectrum_dbc'],lw=1,color=color,label=label)
        ax.set(ylabel='Power (dBc)',xlim=(0,5),ylim=(-115,3))
        ax.set_title(f"{label}: SNDR {d['sndr_db']:.3f} dB | ENOB {d['enob_sndr_bits']:.4f} bit | SFDR {d['sfdr_db']:.3f} dB",fontsize=10)
        ax.grid(alpha=.2);ax.legend(loc='upper left')
    axes[-1].set_xlabel('Frequency (MHz)')
    fig.supxlabel(footer+'\nN=1024, fin=4.501953125 MHz, -1 dBFS; coherent rectangular FFT; no gain/phase correction',fontsize=8)
    fig.savefig(dest/'spectrum_comparison.png',dpi=180);plt.close(fig)

    old=np.array([f['code'] for f in baseline['dynamic_frames']])
    new=np.array([f['code'] for f in candidate['dynamic_frames']])
    fig,axes=plt.subplots(2,1,figsize=(11,6),layout='constrained')
    fig.suptitle(conditions,fontsize=11)
    axes[0].step(np.arange(24)*.1,old[:24],where='post',color=entries[0][2],lw=1.5,label='Original R4')
    axes[0].step(np.arange(24)*.1,new[:24],where='post',color=entries[1][2],lw=1.2,ls='--',label='Idle-tail reset')
    axes[0].set(xlabel='Readout time relative to first measured code (us)',ylabel='Output code',ylim=(0,255))
    axes[0].legend()
    axes[1].plot(np.arange(1024),new-old,'.',ms=3,color=entries[1][2])
    axes[1].axhline(0,color='.5',lw=.7)
    axes[1].set(xlabel='Measured sine sample index',ylabel='Idle minus R4 (code)',
                title=f"{np.count_nonzero(new-old)} / 1024 codes changed; not an input-referred sampling-error plot")
    for ax in axes:ax.grid(alpha=.2)
    fig.supxlabel(footer+'\nReadout at each frame +98 ns; first 4 frames excluded from FFT; no alignment or calibration applied',fontsize=8)
    fig.savefig(dest/'code_comparison.png',dpi=180);plt.close(fig)


def main():
    setup=read(VERIFY/'setup.json')
    baseline_path=ROOT/'verification/sar8_r4_performance/results.json'
    assert sha(baseline_path)==setup['original_R4_results_sha256']
    baseline=read(baseline_path)
    ss=[analyze.load(n)[0] for n in STATICS];dy,_=analyze.load(SINE);runs=ss+[dy]
    for r in runs:
        assert r['context']['source']['candidate_DUT_sha256']==EXPECTED
        assert read(OUT/'cases'/r['name']/'transfer_integrity.json')['match']
    thresholds=sorted([t for r in ss for t in r['thresholds']],key=lambda t:t['k'])
    centers={c['expected']:c for r in ss for c in r['centers']}
    assert sorted(centers)==list(range(256))
    sm=analyze.static_metrics(thresholds,[f['code'] for r in ss for f in r['frames'][r['context']['warmup']:]])
    frames=[f for r in runs for f in r['frames']]
    integrity=all(f['valid'] and f['conversion_s']<60e-9 and
                  (f['compares'],f['writes'],f['updates'],f['captures'])==(8,8,8,16) and
                  f['early_code']==f['code'] for f in frames)
    cmis=[r['name'] for r in runs if r['CMI']]
    numerical=all(not r['numerical_diagnostics'] for r in runs)
    centerpass=all(c['code']==c['expected'] for r in ss for c in r['centers'])
    dyframes=dy['frames'][dy['context']['warmup']:]
    assert len(dyframes)==1024 and len(thresholds)==255
    performance=bool(integrity and numerical and centerpass and sm['all_brackets_pass'] and
                     sm['ordered_disjoint_brackets'] and not sm['unobserved_codes'] and
                     max(abs(sm['dnl_min_lsb']),abs(sm['dnl_max_lsb']))<=1 and
                     sm['inl_endpoint_abs_max_lsb']<=1 and dy['metrics']['enob_sndr_bits']>=7)
    c=dict(static=sm,dynamic=dy['metrics'],dynamic_frames=dyframes,centers=list(centers.values()),
           frames_verified=len(frames),frame_integrity_pass=integrity,static_centers_match=centerpass,
           performance_targets_pass=performance,CMI_cases=cmis,numerical_diagnostics_pass=numerical,
           initial_DC_relaxation_cases=[r['name'] for r in runs if any('Tolerance relaxation' in s for s in r['initial_DC_diagnostics'])])
    oldcodes=np.array([f['code'] for f in baseline['dynamic_frames']]);newcodes=np.array(dy['codes'])
    delta=newcodes-oldcodes
    settings=[]
    for r in runs:
        # Baseline recovery suffix is not a different test condition.
        old=next(x for x in baseline['cases'] if rebase(x['name'])==r['name'])
        settings.append(dict(name=r['name'],original=old['effective_settings'],candidate=r['effective_settings'],
                             identical=old['effective_settings']==r['effective_settings']))
    compact_keys=['name','context','warnings','numerical_diagnostics','initial_DC_diagnostics',
                  'SOA_warning_examples','effective_settings','recovery','result_sha256','log_sha256','wave_sha256']
    result=dict(candidate_commit='027b951',candidate_DUT_sha256=EXPECTED,
                baseline_results_sha256=sha(baseline_path),scope=setup['scope'],
                candidate=c,baseline={k:baseline[k] for k in ['static','dynamic','dynamic_frames','CMI_cases','performance_targets_pass']},
                comparison=dict(dynamic_delta={k:dy['metrics'][k]-baseline['dynamic'][k]
                                               for k in ['sndr_db','enob_sndr_bits','sfdr_db']},
                                changed_sine_codes=int(np.count_nonzero(delta)),max_abs_code_change=int(abs(delta).max()),
                                code_delta_histogram={str(int(k)):int(v) for k,v in zip(*np.unique(delta,return_counts=True))},
                                solver_settings=settings),
                cases=[{k:r.get(k) for k in compact_keys} for r in runs],
                limits=['No PVT/mismatch/noise/PEX', '1 ns strobes do not bound analog internal peaks',
                        'No CMI is not full-node electrical sign-off',
                        'Idle-reset end-of-frame top voltage is not conversion residue',
                        'SAMPLE falling 50% is not a calibrated physical aperture'])
    dump(VERIFY/'results.json',result);figures(result)
    report(result)
    dump(OUT/'flow_status.json',dict(stage='complete_pending_visual_review',performance_targets_pass=performance,
                                   CMI_cases=cmis,report='docs/sar8_idle_performance.md'))
    setup['status']='complete_pending_visual_review';dump(VERIFY/'setup.json',setup)
    print(json.dumps(dict(static={k:v for k,v in sm.items() if not isinstance(v,list)},
                         dynamic={k:v for k,v in dy['metrics'].items() if not isinstance(v,list)},
                         comparison=result['comparison']['dynamic_delta'],CMI_cases=cmis),indent=2))


def rebase(name):
    return name.removesuffix('_r2')


def report(r):
    a=r['baseline'];b=r['candidate'];s=b['static'];d=b['dynamic'];delta=r['comparison']['dynamic_delta']
    rows=[('DNL (LSB)',f"{a['static']['dnl_min_lsb']:.5f} ~ {a['static']['dnl_max_lsb']:.5f}",f"{s['dnl_min_lsb']:.5f} ~ {s['dnl_max_lsb']:.5f}"),
          ('最大端点 INL (LSB)',f"{a['static']['inl_endpoint_abs_max_lsb']:.5f}",f"{s['inl_endpoint_abs_max_lsb']:.5f}"),
          ('SNDR (dB)',f"{a['dynamic']['sndr_db']:.3f}",f"{d['sndr_db']:.3f}"),
          ('ENOB (bit)',f"{a['dynamic']['enob_sndr_bits']:.4f}",f"{d['enob_sndr_bits']:.4f}"),
          ('SFDR (dB)',f"{a['dynamic']['sfdr_db']:.3f}",f"{d['sfdr_db']:.3f}"),
          ('有原生 CMI 告警的案例数',str(len(a['CMI_cases'])),str(len(b['CMI_cases'])))]
    table='\n'.join('| '+' | '.join(row)+' |' for row in rows)
    text=f'''# 空闲段复位版本：全码与频谱对照 R4

本轮固定候选 `027b951`，不调整器件尺寸或连接。TT、0.9 V、27°C、10 MS/s；
不包含 PVT、失配、瞬态噪声及 PEX。测试台沿用 R4：理想电源/参考源/SAMPLE，
输入每侧 50 Ω，参考每轨 50 Ω＋4 pF。候选仍为网表实验，未替换 R4 或 OA。

| 指标 | 原 R4 | 空闲段复位 |
| --- | --- | --- |
{table}

全部 255 个转换边界、256 个码中心、1024 个正弦输出已回收；
实际观察码覆盖 {len(s['observed_codes'])}/256。总计 {b['frames_verified']} 帧（含预热），
逐帧时序通过：{b['frame_integrity_pass']}；码中心正确：{b['static_centers_match']}。
性能筛选通过：{b['performance_targets_pass']}。这不是整机可靠性签核。

## 静态

![静态对比](figures/sar8_idle_performance/static_comparison.png)

同一真实码字反馈二分算法，7 次细化，最大搜索区间 {s['threshold_max_bracket_width_lsb']:.7f} LSB。
DNL 不包含两端饱和码宽。原始转换边界误差和去除端点增益/偏置后的 INL 分开显示；
小于搜索分辨率的差别不能解释为确定的电路改善。
候选端点增益误差 {s['endpoint_gain_error_percent']:.5f}%，首边界偏移 {s['offset_first_transition_mv']:.5f} mV。

## 动态

![频谱对比](figures/sar8_idle_performance/spectrum_comparison.png)

连续 -1 dBFS 正弦，4 帧预热＋1024 帧测量，fin=4.501953125 MHz、bin=461。
矩形窗相干 FFT，去 DC，SNDR 包含谐波；未校准增益、相位或码字。
直接 FFT 与 ADCToolbox 核对。ENOB=(SNDR−1.76)/6.02，未作 -1 dBFS 满幅补偿。
相对 R4：SNDR {delta['sndr_db']:+.4f} dB，ENOB {delta['enob_sndr_bits']:+.5f} bit，SFDR {delta['sfdr_db']:+.4f} dB。

![码字对比](figures/sar8_idle_performance/code_comparison.png)

{r['comparison']['changed_sine_codes']}/1024 个输出码不同，最大差 {r['comparison']['max_abs_code_change']} code。
这是相同外部激励下的版本差异，不直接等同于采样保持误差。
码字在每帧 98 ns 读取；监测 90–98 ns 无翻转，每帧 8 次比较、8 次写入、8 次更新、16 次捕获。
候选在空闲段复位参考，因此 98 ns 顶板电压不再作为上一轮转换残差。

## 原生日志与边界

- 候选 CMI 案例：{', '.join(b['CMI_cases']) or '无'}；原 R4 的过压记录保留。
- 瞬态数值诊断筛选通过：{b['numerical_diagnostics_pass']}；初始 DC 容差放宽案例：{', '.join(b['initial_DC_relaxation_cases']) or '无'}。
- 同长度案例实际求解设置相同：{all(x['identical'] for x in r['comparison']['solver_settings'])}。
  Spectre X CX 实际精度从各原生日志记录，不以网表请求值冒充实际值。
- 长跑仅保存 1 ns 频闪波形，应力依据原生 CMI；没有 CMI 不代表所有内部尖峰均被证明安全。
  上一轮高分辨率应力证据见 [空闲段复位实验](sar8_r4_idle.md)，不能外推为全部码的峰值证明。
- 原 R4 正弦是原生瞬态 PASS / 完整波形回收，缺少进程最终零错误摘要；本轮逐例要求 exit 0、PASS、END、哈希核对。

完整数值/逐例设置/日志哈希：`verification/sar8_idle_performance/results.json`；
原始记录：`output/sar8_idle_performance/`。未推送、未修改 PDK、OA 或原始 R4。
'''
    (ROOT/'docs/sar8_idle_performance.md').write_text(text,encoding='utf-8')


if __name__=='__main__': main()
