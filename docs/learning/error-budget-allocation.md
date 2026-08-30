# SAR ADC 自上而下误差预算方法

## 核心结论

> 这组数字的本质是第一版“自上而下的模块指标分配”。严格推导的是总误差上限；各模块占多少，是目前为了启动 CDAC、comparator、sampling 和 clock 设计而做的初始工程选择，后续会根据 PDK 仿真结果重新平衡。

因此，当前预算不能被解读为晶体管级仿真结果，也不能被解读为各模块已经满足指标。它的用途是把系统目标转换为第一版可执行的模块约束。

## 第一步：从系统规格推导不可随意改变的量

规格来源为 [`config/design_spec.yaml`](../../config/design_spec.yaml)：

- 分辨率：10 bit
- 差分输入范围：`[-0.9, 0.9] V`
- 动态测试幅度：-1 dBFS
- 最低 ENOB：9 bit

由此得到：

```text
VFS = 1.8 V
LSB = VFS / 2^10 = 1.7578125 mV
SNDRtarget = 6.02 × 9 + 1.76 = 55.94 dB
Vsignal,rms = 0.9 × 10^(-1/20) / sqrt(2) = 0.567189 V
Verror,max = Vsignal,rms / 10^(55.94/20) = 0.905164 mV RMS
```

`0.905164 mV RMS`，即 `0.514938 LSB RMS`，是当前动态测试条件下全部噪声与失真的总等效上限。这个上限由系统目标决定，不是模块设计者任意选择的。

理想量化噪声同样由分辨率决定：

```text
Vquant,rms = LSB / sqrt(12)
           = 0.507437 mV
           = 0.288675 LSB
```

量化噪声扣除后，其余模拟误差可使用的 RSS 空间约为 `0.750 mV RMS`，即 `0.427 LSB RMS`。

## 第二步：把剩余空间初步分配给模块

下面的数字是工程分配，而不是严格推导或 PDK 测量：

| 项目 | 初始分配 | 电压等效 | 分配意图 |
| --- | ---: | ---: | --- |
| Sampling thermal noise | 0.18 LSB RMS | 0.316406 mV RMS | 给采样网络一个可用于估算有效电容的起点 |
| Comparator decision noise | 0.18 LSB RMS | 0.316406 mV RMS | 与采样噪声同量级，作为 StrongARM 输入噪声目标 |
| Reference/switching noise | 0.12 LSB RMS | 0.210938 mV RMS | 因其可能码相关并形成谐波，分配更紧 |
| Clock jitter | 20 ps RMS @ 4.5 MHz | 0.320738 mV RMS | 约占 0.182464 LSB，和主要随机噪声同量级 |
| Distortion/unmodeled guard | 0.15 LSB RMS | 0.263672 mV RMS | 为尚未显式建模的失真与相关效应留空间 |

Clock jitter 使用正弦采样误差近似：

```text
Vjitter,rms = 2π × Fin × Vsignal,rms × sigma_t
```

将 `Fin = 4.5 MHz`、`Vsignal,rms = 0.567189 V` 和 `sigma_t = 20 ps` 代入，得到 `0.320738 mV RMS`。

## 第三步：检查 RSS 是否闭合

把量化噪声和上述初始分配作为互不相关的等效 RMS 项处理：

```text
Vallocated,rms = sqrt(
    Vquant^2
  + Vsampling^2
  + Vcomparator^2
  + Vreference^2
  + Vjitter^2
  + Vunmodeled^2
)
= 0.821345 mV RMS
= 0.467254 LSB RMS
```

对应系统性能为：

```text
SNDRprojected = 56.784 dB
ENOBprojected = 9.140 bit
SNDR margin = 0.844 dB
```

剩余 RSS 空间必须按平方差计算：

```text
Vheadroom,rms = sqrt(Verror,max^2 - Vallocated,rms^2)
              = 0.380414 mV
              = 0.216413 LSB
```

不能直接用两个 RMS 数值相减来解释剩余预算。

## 确定性 guardrail 与随机预算分开

当前另设：

- CDAC 最终建立误差 `< 0.25 LSB = 0.439453 mV`
- Comparator 系统 offset `< 0.25 LSB = 0.439453 mV`

这两个值是第一版保守 guardrail，不是独立加入 RSS 的随机噪声项。恒定 offset 主要改变转换器偏移和输入余量；CDAC settling 是码相关、时序相关的确定性误差。后续应分别通过传输曲线、瞬态建立和 Monte Carlo 验证，避免与 `distortion/unmodeled` 余量重复计算。

## 何时重新平衡

获得以下证据后应更新模块分配，但保持系统总上限不变，除非顶层规格本身改变：

1. PDK 电容类型、单位电容、`kT/C`、失配和寄生表征完成；
2. StrongARM 的输入噪声、系统 offset、kickback 和决策时间完成 PVT/Monte Carlo；
3. Sampling switch 的建立、导通电阻非线性、注入和 THD 已测得；
4. CDAC switching sequence、桥接比例误差和 reference 瞬态电流已确定；
5. Reference source/buffer 的输出阻抗、噪声和恢复时间已测得；
6. 实际 clock source 的 jitter 规格已知。

重平衡时应以可复现的 PVT/Monte Carlo 结果替换初始分配，明确 typical、worst case 和统计口径；码相关或谐波型误差应直接用 SNDR/INL 仿真验证，而不是全部强行等效为独立白噪声。

## 当前适用范围

这套方法适用于架构启动和模块指标拆分。它证明在当前分配假设下 9-bit ENOB 目标仍有理论余量，但不能证明管级电路、版图后电路或 5+5 split CDAC 已经满足指标。当前数值闭合结果可在 [`docs/error_budget.md`](../error_budget.md) 和生成的 `output/behavioral_baseline/summary.json` 中复核。
