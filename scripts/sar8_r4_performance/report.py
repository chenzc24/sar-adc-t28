"""Curate final measured results and standalone review figures."""
import argparse
import json
from pathlib import Path
import numpy as np
from common import ROOT,OUT,LSB,read,dump,sha
from analyze import load,static_metrics


def figures(result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    dest=ROOT/"docs/figures/sar8_r4_performance";dest.mkdir(parents=True,exist_ok=True)
    s=result["static"];d=result["dynamic"]
    conditions="R4 transistor core | TT, 0.9 V, 27 C | fs = 10 MS/s | no transient noise / mismatch"
    footer="External ideal VDD / reference sources / SAMPLE; Rin = 50 ohm per side; Rref = 50 ohm, Cref = 4 pF per rail"
    fig,axes=plt.subplots(3,1,figsize=(11,9),layout="constrained")
    fig.suptitle(conditions,fontsize=11)
    centers=result["centers"]
    xx=np.array([v["input_v"] for v in centers]);yy=np.array([v["code"] for v in centers])
    axes[0].step(np.r_[-.9,s['thresholds_v'],.9],np.r_[np.arange(256),255],where="post",label="Measured transition midpoints",color="#207c89")
    axes[0].plot(xx,yy,'.',ms=2,color='#207c89',label='Code-center probes')
    axes[0].plot([-.9,.9],[0,256],"--",color=".5",lw=1,label="Ideal transfer")
    axes[0].set(xlabel="Differential input (V)",ylabel="Output code",ylim=(-3,258));axes[0].legend()
    axes[1].plot(np.arange(1,255),s["dnl_nominal_lsb"],color="#207c89",label="DNL, nominal LSB")
    axes[1].fill_between(np.arange(1,255),s["dnl_lower_bound_lsb"],s["dnl_upper_bound_lsb"],alpha=.2,color="#207c89",label="Search bracket uncertainty")
    axes[1].set(xlabel="Code (saturated endpoints excluded)",ylabel="DNL (LSB)");axes[1].legend()
    axes[2].plot(np.arange(1,256),s["inl_raw_lsb"],label="Raw transition error",color="#d5663f")
    axes[2].plot(np.arange(1,256),s["inl_endpoint_lsb"],label="Endpoint INL",color="#207c89")
    axes[2].set(xlabel="Transition index",ylabel="INL (LSB)");axes[2].legend()
    for ax in axes:ax.grid(alpha=.2)
    for ax in axes[1:]:ax.axhline(0,color=".5",lw=.7)
    fig.supxlabel(footer,fontsize=8)
    fig.savefig(dest/"static_linearity.png",dpi=180);plt.close(fig)

    fig,ax=plt.subplots(figsize=(11,4.8),layout="constrained")
    fig.suptitle(conditions,fontsize=11)
    ax.plot(np.array(d["frequency_axis_hz"])/1e6,d["spectrum_dbc"],lw=1,color="#207c89",label="Output-code FFT")
    ax.set(xlabel="Frequency (MHz)",ylabel="Power (dBc)",xlim=(0,5),ylim=(-115,3))
    ax.set_title(f"N={d['samples']}, fin={d['frequency_hz']/1e6:.6f} MHz, -1 dBFS, rectangular window\nSNDR {d['sndr_db']:.2f} dB   ENOB {d['enob_sndr_bits']:.3f} bit   SFDR {d['sfdr_db']:.2f} dB",fontsize=11)
    ax.grid(alpha=.2);ax.legend(loc="upper left")
    fig.supxlabel(footer,fontsize=8)
    fig.savefig(dest/"spectrum.png",dpi=180);plt.close(fig)

    frames=result["dynamic_frames"][:24]
    ts=np.array([f["aperture_time_s"] for f in frames]);t0=ts[0]
    tt=np.linspace(ts[0],ts[-1],3000);amp=.9*10**(-1/20)
    fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True,layout="constrained")
    fig.suptitle(conditions,fontsize=11)
    axes[0].plot((tt-t0)*1e6,amp*np.sin(2*np.pi*d["frequency_hz"]*tt),color=".6",label="Continuous input")
    axes[0].plot((ts-t0)*1e6,[f["aperture_source_v"] for f in frames],"o",ms=4,color="#d5663f",label="Input at SAMPLE falling 50%")
    axes[0].set_ylabel("Differential input (V)")
    codes=np.array([f["code"] for f in frames]);ideal=np.clip(np.floor((np.array([f["aperture_source_v"] for f in frames])+.9)/LSB),0,255)
    axes[1].step((ts-t0)*1e6,codes,where="post",label="Actual output code",color="#207c89")
    axes[1].plot((ts-t0)*1e6,ideal,"x",ms=5,label="Ideal quantizer at clock marker (timing reference)",color="#d5663f")
    axes[1].set(xlabel="SAMPLE falling-50% time relative to first shown frame (us)",ylabel="Output code",ylim=(-3,258))
    for ax in axes:
        ax.legend(loc="lower left",bbox_to_anchor=(0,1.0),fontsize=8,ncol=2)
        ax.grid(alpha=.2)
    fig.supxlabel(footer+'\nReadout: frame +98 ns. Clock marker is not a calibrated physical aperture; no phase correction.',fontsize=8)
    fig.savefig(dest/"sine_codes.png",dpi=180);plt.close(fig)


def main():
    p=argparse.ArgumentParser();p.add_argument("--static",nargs="+",required=True);p.add_argument("--sine",required=True);a=p.parse_args()
    ss=[load(n)[0] for n in a.static];dy,_=load(a.sine)
    thresholds=sorted([t for r in ss for t in r["thresholds"]],key=lambda x:x["k"])
    centers={c["expected"]:c for r in ss for c in r["centers"]}
    assert sorted(centers)==list(range(256))
    sm=static_metrics(thresholds,[f["code"] for r in ss for f in r["frames"][r["context"]["warmup"]:]])
    allruns=ss+[dy]
    edge_counts=all((f['compares'],f['writes'],f['updates'],f['captures'])==(8,8,8,16)
                   and f['code']==f['early_code'] for r in allruns for f in r['frames'][r['context']['warmup']:])
    integrity=all(r["frame_integrity_pass"] for r in allruns) and edge_counts
    numerical=all(not r["numerical_diagnostics"] for r in allruns)
    result=dict(scope="R4 TT/0.9V/27C deterministic transistor-core characterization; external ideal sources",
        static=sm,centers=[centers[k] for k in sorted(centers)],dynamic=dy["metrics"],
        dynamic_frames=dy["frames"][dy["context"]["warmup"]:],
        frame_integrity_pass=integrity,numerical_diagnostics_pass=numerical,
        static_transition_count=len(thresholds),static_center_count=len(centers),
        static_centers_match=all(c['code']==c['expected'] for r in ss for c in r['centers']),
        total_simulated_frames=sum(len(r['frames']) for r in allruns),
        independent_edge_counts_pass=edge_counts,
        time_reference='aperture_time_s is SAMPLE_INT falling50% crossing, not calibrated physical aperture',
        CMI_cases=[r["name"] for r in allruns if r["CMI"]],
        initial_DC_relaxation_cases=[r["name"] for r in allruns if any("Tolerance relaxation" in x for x in r["initial_DC_diagnostics"])],
        cases=[dict(name=r["name"],context=r["context"],invalid_frames=r["invalid_frames"],
            warnings=r["warnings"],numerical_diagnostics=r["numerical_diagnostics"],initial_DC_diagnostics=r["initial_DC_diagnostics"],
            SOA_warning_examples=r["SOA_warning_examples"],effective_settings=r["effective_settings"],
            timing=r["timing"],recovery=r.get("recovery"),log_sha256=r["log_sha256"],wave_sha256=r["wave_sha256"]) for r in allruns],
        preflight=read(OUT/"preflight.json"),pilot_comparison=read(OUT/"pilot_comparison.json"))
    result["nominal_targets_pass"]=bool(integrity and numerical and not result["CMI_cases"] and sm["all_brackets_pass"] and
        sm["ordered_disjoint_brackets"] and not sm["unobserved_codes"] and max(abs(sm["dnl_min_lsb"]),abs(sm["dnl_max_lsb"]))<=1 and
        sm["inl_endpoint_abs_max_lsb"]<=1 and dy["metrics"]["enob_sndr_bits"]>=7)
    result['performance_targets_pass']=bool(integrity and numerical and sm['all_brackets_pass'] and
        sm['ordered_disjoint_brackets'] and not sm['unobserved_codes'] and result['static_centers_match'] and
        max(abs(sm['dnl_min_lsb']),abs(sm['dnl_max_lsb']))<=1 and sm['inl_endpoint_abs_max_lsb']<=1 and
        dy['metrics']['enob_sndr_bits']>=7)
    dump(OUT/"summary.json",result)
    curated=dict(result);curated["preflight"]={k:v for k,v in result["preflight"].items() if k not in ("resources",)}
    dump(ROOT/"verification/sar8_r4_performance/results.json",curated)
    figures(result)
    d=dy["metrics"]
    text=f"""# R4 全码扫描与正弦频谱

保持 `sar_adc8_join_r4` 的器件、连接和全部 MOS 参数不变。
测试条件：TT、0.9 V、27°C、10 MS/s；无瞬态噪声、无失配。
电源、参考源和外部 SAMPLE 为理想测试台源；输入每侧 50 Ω，参考每轨 50 Ω＋4 pF。

| 指标 | 实测 |
| --- | --- |
| 观察到的输出码 | {len(sm['observed_codes'])}/256 |
| 转换边界 / 码中心 | {len(thresholds)}/255 / {len(centers)}/256 |
| DNL，标称 LSB | {sm['dnl_min_lsb']:.5f} 至 {sm['dnl_max_lsb']:.5f} LSB |
| 最大原始转换边界偏差 | {sm['inl_raw_abs_max_lsb']:.5f} LSB |
| 最大端点 INL | {sm['inl_endpoint_abs_max_lsb']:.5f} LSB |
| 最大边界搜索区间 | {sm['threshold_max_bracket_width_lsb']:.6f} LSB |
| SNDR / ENOB | {d['sndr_db']:.3f} dB / {d['enob_sndr_bits']:.4f} bit |
| SFDR | {d['sfdr_db']:.3f} dB |
| 逐帧时序完整性 | {'通过' if integrity else '未通过，见结果记录'} |

器件应力告警涉及的测试：{', '.join(result['CMI_cases']) or '无'}。
{'因此该版本尚未通过器件应力要求；频谱/线性度数值保留为性能诊断，不能据此宣布整机通过。' if result['CMI_cases'] else '本轮没有原生 CMI 告警，仍不等同于全节点可靠性签核。'}

长跑采用 Spectre X CX。默认预设会重定义部分网表精度设置；每次运行的实际
reltol、积分方法和最大步长均从原生日志读取并保存在结果中。
与严格 APS 的短例对照用于评估数值偏差；速度比较不是等容差比较。

静态测试使用真实输出反馈二分搜索全部 255 个转换边界，并检查全部码中心。
DNL 排除两端饱和码的宽度；同时列出未经增益/偏置修正的转换偏差和端点 INL。
测试要求全部初始搜索区间有效：{sm['all_brackets_pass']}。
所有码中心均返回预期码：{result['static_centers_match']}；本次总计验证 {result['total_simulated_frames']} 帧（含预热）。
边界区间宽度约 0.0078125 LSB，因此图中的细小锯齿部分受搜索分辨率限制，
不能据此解释为同量级的真实器件非线性。原始边界偏差主要呈斜率变化，
端点增益误差约 {sm['endpoint_gain_error_percent']:.5f}%；这不等同于已定位到某一个模块。

![全码静态结果](figures/sar8_r4_performance/static_linearity.png)

动态测试为连续 −1 dBFS 正弦，{d['samples']} 点，fin={d['frequency_hz']:.6f} Hz。
矩形窗相干 FFT，去除 DC，SNDR 包含谐波；ENOB=(SNDR−1.76)/6.02，
不做满幅补偿或码字校准。直接 FFT 与 ADCToolbox 交叉核对。
−1 dBFS 下理想 8 bit 的量化信噪比估计约 48.92 dB；本次 7.802 bit
是未作满幅补偿的 ENOB，不应直接理解为丢失了 0.198 bit 的电路精度。

![输出码频谱](figures/sar8_r4_performance/spectrum.png)

![输入与输出码](figures/sar8_r4_performance/sine_codes.png)

码字按内部 SAMPLE 下降沿的 50% 时刻标注，实际读出位于每帧 98 ns。
该时钟标记不是经校准的物理孔径；理想量化码仅作时序参照，其与输出的逐点差异
混合了采样路径相移和转换误差，不能全部称为保持误差。FFT 未做相位/增益校准。
每个有效帧检查 8 次比较、8 次写入、8 次 UPDATE、16 次参考捕获，
并检查 90–98 ns 输出稳定性及读出电平。
全部案例未发现瞬态 LTE 放宽/收敛失败诊断；`static_cx_161_192_r2` 有初始 DC
求解容差放宽记录，保留在结果中，不将其混写为瞬态失败或隐去。

原始结果在 `output/sar8_r4_performance/`，完整数值、有效求解器设置、告警和哈希
在 `verification/sar8_r4_performance/results.json`。长测试使用稀疏保存，
不能据此宣称全部内部节点峰值应力通过。PVT、失配、噪声和版图仍未覆盖。
首个参考过压已另行高分辨率定位于采样启动/参考码复位交叠，见
[参考开关过压诊断](sar8_r4_reference_stress.md)。未因此修改本次冻结电路。

本批次曾发生 SSH 中断。正弦及第一段静态数据从原任务回收，以原生
`logStatus PASS`、完整帧数、PSF 结束标记和完整时长确认分析完成；原始 bridge
失败记录保留，未伪造进程退出码。正弦缺少整个进程的最终零错误摘要，
但原生瞬态 PASS 和全部 1024 点已验证。其余恢复案例、原案例映射及退出码
见 `output/sar8_r4_performance/recovery_20261022_r2.json` 和逐案例 recovery 字段。
"""
    (ROOT/"docs/sar8_r4_performance.md").write_text(text,encoding="utf-8")
    print(json.dumps(dict(nominal_targets_pass=result["nominal_targets_pass"],static={k:v for k,v in sm.items() if not isinstance(v,list)},dynamic={k:v for k,v in d.items() if not isinstance(v,list)}),indent=2))


if __name__=="__main__":main()
