# Verilog-A 事件级噪声注入方法与边界

## 核心结论

在 testbench 中设置 `0.316406 mV RMS`，不是在每次转换中固定加入
`+0.316406 mV`。这个数是高斯分布的标准差 `sigma`；Verilog-A 在指定
事件发生时生成新的单位高斯随机数，再乘以 `sigma` 得到该次实际噪声。

当前方法是“已积分的输入等效 RMS + 事件级随机抽样”。它适合验证系统
误差预算、SNDR 和模块噪声目标，但不包含晶体管噪声带宽、频谱形状、
相关性、kickback、reference memory、PVT 或版图寄生。

## 从预算数值到随机变量

项目的差分满量程为 `1.8 V`，分辨率为 10 bit：

```text
LSB = 1.8 / 1024 = 1.7578125 mV
```

三项已显式建模的随机噪声分配为：

| 噪声源 | 分配 | Verilog-A RMS 参数 |
| --- | ---: | ---: |
| Sampling thermal noise | 0.18 LSB | 0.31640625 mV |
| Comparator decision noise | 0.18 LSB | 0.31640625 mV |
| Reference/switching noise | 0.12 LSB | 0.21093750 mV |

testbench 只负责设置这些标准差和随机种子：

```spectre
sampling_noise_rms_v=316.40625u
comparator_noise_rms_v=316.40625u
reference_noise_rms_v=210.9375u
sampling_noise_seed=271828
comparator_noise_seed=314159
reference_noise_seed=161803
```

对应场景位于
[`netlist/tb/tb_sar_adc_allocated_noise_dynamic.scs`](../../netlist/tb/tb_sar_adc_allocated_noise_dynamic.scs)。
理想 testbench 不设置这些参数，因此模型的零噪声默认行为保持不变。

## 随机数的数学实现

Spectre Verilog-A 的 `$rdist_normal(seed, mean, standard_deviation)` 返回
整数正态随机数。当前模型先生成标准差为 `1000000` 的整数，再除以
`1000000`，得到近似单位高斯变量：

```text
r ~ Normal(0, 1000000^2)
z = r / 1000000
z ~ Normal(0, 1)
n = sigma * z
```

实现形式为：

```verilog
noise_v = noise_rms_v
    * $rdist_normal(seed_state, 0, 1000000)
    / 1000000.0;
```

因此 `noise_rms_v` 是分布参数，不是一次具体的噪声 realization。每次
调用可能得到正值、负值或接近零的值，长期统计标准差才接近所配置的
RMS。

## Sampling noise：每次转换抽样一次

在 `CLK_SAMPLE` 下降沿，模型生成一次新的采样噪声，并和差分输入一起
锁存：

```verilog
sample_noise_v = sampling_noise_rms_v
    * $rdist_normal(sample_seed_state, 0, 1000000)
    / 1000000.0;

sampled_diff_v = V(VINP, VINN) + sample_noise_v;
```

数学形式为：

```text
ns[k] ~ Normal(0, sigma_s^2)
Vsampled[k] = Vin,diff[k] + ns[k]
```

同一次转换的十个 SAR decision 使用同一个 `Vsampled[k]`，因此 sampling
noise 表示 sample-and-hold 在采样瞬间形成、随后被保持的误差，而不是每
个 bit 都重新变化的噪声。

## Comparator 和 reference noise：每个 bit 抽样一次

在每个 `CLK_SAR` 上升沿，模型分别生成新的 comparator 和 reference
噪声：

```verilog
comparator_noise_v = comparator_noise_rms_v
    * $rdist_normal(comparator_seed_state, 0, 1000000)
    / 1000000.0;

reference_noise_v = reference_noise_rms_v
    * $rdist_normal(reference_seed_state, 0, 1000000)
    / 1000000.0;
```

它们被加入当前 bit 的判决门限：

```verilog
decision_threshold_v = vdac_effective_v
    + comparator_offset_v
    + comparator_noise_v
    + reference_noise_v;

if (sampled_diff_v >= decision_threshold_v)
    code_work = trial_code;
```

数学形式为：

```text
nc[k,b] ~ Normal(0, sigma_c^2)
nr[k,b] ~ Normal(0, sigma_r^2)

Vsampled[k] >= VDAC[k,b] + Voffset + nc[k,b] + nr[k,b]
```

其中 `k` 是转换序号，`b` 是 SAR bit 序号。一次 10-bit 转换会产生十组
新的 comparator/reference 随机样本。数字输出码没有被事后随机修改；
码变化来自逐 bit 比较门限被噪声扰动后的真实 SAR decision。

完整实现位于
[`models/veriloga/sar_adc_ideal_10b.va`](../../models/veriloga/sar_adc_ideal_10b.va)。

## 固定 seed 不等于固定噪声电压

固定 seed 的含义是每次运行得到同一条随机序列，而不是每次转换加入
同一个电压。这样可以复现失败、比较代码修改并建立 deterministic
regression。

单个固定-seed 运行不是 Monte Carlo。需要统计置信区间时，应改变 seed
并统计多次运行的均值、标准差和尾部，而不是从一条序列推断 yield。

## 为什么这里不使用 `white_noise()`

`white_noise()` 更适合连续时间物理模型中的噪声谱密度 contribution，
并配合 Spectre noise、PNoise 或相应 transient-noise 流程。使用它时还需
定义电压或电流 PSD、传递函数和积分带宽。

当前模型是 event-driven SAR system model，预算已经给出每次采样或判决
的积分后输入等效 RMS。因此显式 `$rdist_normal()` 更适合当前目的：

- 注入时刻明确；
- sampling 和逐 bit decision 的状态语义明确；
- 普通 transient 即可执行；
- 固定 seed 可复现；
- RMS 参数可以直接对应顶层误差预算。

这不是说 `white_noise()` 不正确，而是两者回答的问题不同。事件级随机
抽样验证“这个输入等效 RMS 是否还能满足 ADC 指标”；连续时间噪声分析
用于从真实电路的 PSD、带宽和采样折叠推导该 RMS。

## Spectre 与 RSS 的验证结果

16,384 点、`4.500122 MHz`、`-1 dBFS` 的固定-seed Spectre 结果为：

| 指标 | 数值 |
| --- | ---: |
| 理想 SNDR | 60.954 dB |
| 三项噪声部分 RSS 预测 | 58.0657 dB |
| Verilog-A Spectre SNDR | 58.0588 dB |
| 预测与仿真差值 | -0.0069 dB |
| Verilog-A ENOB | 9.352 bit |
| 相对理想序列的变码数 | 3641 / 16384 |
| 最大码差 | 1 LSB |
| 平均码差 | -0.0010 LSB |

部分 RSS 包含理想量化噪声和三项已启用随机源：

```text
Vpartial,rms = sqrt(
    Vquant^2
  + Vsampling^2
  + Vcomparator^2
  + Vreference^2
)
= 0.708670 mV RMS
```

Spectre 与 RSS 只差 `0.0069 dB`，支持当前独立高斯抽象用于 top-down SNDR
预算。所有变码都只有 1 LSB，且均值接近零，符合小零均值噪声只在量化
阈值附近改变 decision 的预期。

结果可在生成的
`output/veriloga_allocated_noise_spectre/summary.json` 中复核；该目录为
忽略的仿真产物，不是 Git source of truth。

## SFDR 可能改善并不代表 ADC 更好

加入噪声后，某些确定性的量化 spur 会被 dither 打散到宽带噪声底，最大
单根 spur 可能下降，因此 SFDR 可能提高。本次 SFDR 从理想结果的
`82.213 dB` 变为 `87.453 dB`，同时 SNDR 从 `60.954 dB` 降到
`58.059 dB`。

这种情况下应以 SNDR/ENOB 判断总性能。不能因为 SFDR 数值增大，就得出
“加噪声改善了 ADC”的结论。

## 不能强行当作白噪声的项目

以下项目没有加入本次三项随机噪声运行：

1. **Clock jitter**：它首先是采样时刻扰动，应在 testbench 中改变采样
   edge；其输入等效电压随输入频率和斜率变化。
2. **Distortion/unmodeled guard**：当前只有 RMS guard band，没有定义
   HD2、HD3、码相关性或具体波形，直接替换成白噪声会掩盖 spur。
3. **Comparator offset**：是确定性门限偏移，应通过静态传输和 offset
   sweep 验证；FFT 去均值可能隐藏它。
4. **CDAC settling**：是 bit、码型和时间相关的 residual，应通过逐 bit
   建立和动态失真验证，而不是当作独立随机项。

## 适用边界与后续闭环

当前方法可以把模块设计目标写成可执行的行为级参数，但最终应按以下
路径替换假设：

```text
系统 RMS 分配
-> Verilog-A 事件级 sensitivity/组合验证
-> 晶体管级 noise/PNoise/transient-noise/PVT/Monte Carlo
-> 提取 input-referred RMS、相关性、带宽和尾部
-> 回填并重新平衡系统预算
```

建议的下一步验证顺序是：

1. sampling、comparator、reference 分别单独 sweep，建立 SNDR sensitivity；
2. 多 seed 运行，检查均值、方差和结果置信区间；
3. 在 testbench 中实现真正的采样 edge jitter；
4. 单独验证 comparator offset 和 CDAC settling；
5. 用 PDK 晶体管级证据逐步替换独立高斯假设。

最重要的工程纪律是：预算数值定义允许的统计规模，Verilog-A 定义抽样
与判决机制，晶体管级仿真最终决定真实噪声是否满足这一规模。三者不能
相互替代。
