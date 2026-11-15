# SAR8 总设计规格

本页由 [specs/arch.json](../specs/arch.json) 生成。当前电气实现采用最简参考驱动 `reference=minimal_msb_d2`，其余模块沿用 B。版本及验收状态见 [采用记录](../results/design/minimal_msb_d2_adoption_20261115.json)。行为模型仍是 B 的算法与协议近似，未拟合最简参考路径。

## 架构与外部接口

- 8 bit、10 MS/s，全差分异步 SAR，flat binary CDAC；每侧 255 单位二进制电容加 1 单位 dummy，无桥电容。
- 顶层端口顺序：`D0 D1 D2 D3 D4 D5 D6 D7 SAMPLE VDD! VINN VINP VREFN VREFP 0`。
- 数字输出为 D0..D7，无外部位时钟、BUSY、VALID 或 EOC 引脚。SAMPLE 高电平采样并复位 SAR；下降沿结束采样，内部自主推进 8 位。
- 码字在转换中逐位变化，完成后、下一采样开始前读取。正差分极性为 VINP−VINN。

| 项目 | 当前定义 |
| --- | --- |
| 核心电源 | 标称 0.9 V，验证范围 0.81–0.99 V |
| 参考 | VREFN=0 V、VREFP=0.9 V，独立于核心电源 |
| 输入 | 标称共模 0.45 V；差分 -0.9..0.9 V，单端 0..0.9 V；完整共模范围尚未签核 |
| 量化 | 256 码，LSB=7.03125000 mV；理想边界 −0.9+k·LSB，上边码处理精确相等 |
| 帧时序 | 100 ns：高 40 ns 采样、低 60 ns 转换；启动先低 60 ns 预充，再进入正常周期 |
| 实际激励 | delay=60 ns，rise/fall=100/100 ps，width=39.9 ns；首次下降阈值在 100.05 ns |
| 输入源 | 每端理想源串联 50 Ω |
| 参考源 | 每轨理想源串联 50 Ω、旁路 4 pF，无片上参考缓冲器 |
| 输出负载 | 每位 5 fF；比较器输出及其时钟另有原生 MOM 负载 |

## 工况定义

| 工况 | MOS corner | 温度/°C | VDD/V |
| --- | --- | ---: | ---: |
| tt | TT | 27 | 0.9 |
| ssc | SS | -40 | 0.81 |
| ssh | SS | 125 | 0.81 |
| ffc | FF | -40 | 0.99 |
| ffh | FF | 125 | 0.99 |

各工况的实际 MOS、MOM 与无源模型 section 由冻结用例的 include 决定，不能从 MOS corner 名字推断其他器件角。用例身份见 [tests.json](../specs/tests.json)。

## 当前晶体管实现

- Bootstrap：每路 2 只并联 1 µm/150 nm 的 `nch_18_mac` 主开关，原生 MOM bootstrap 电容 multi=200。
- CDAC：18 个 `cfmom_2t` 实例；单位几何 nr=8、lr=2 µm、w=s=50 nm、stm=1、spm=3，multi 按 1..128 缩放。N/P 侧 dummy 分别接 VREFN/VREFP。同单位几何的既有低频 AC 提取约 4.00407 fF，每侧 256 单位约 1.02504 pF；这是有偏置/频率条件的表征值，不是恒定器件值。旧 6.86047 fF 比较值和 512 独立单元的失配统计不归给当前 18 个分组实例。
- 参考开关：L=90 nm，NMOS W=150 nm、PMOS W=175 nm，multi=3·2^bit。
- 比较器：11 MOS StrongARM；输入对 W=1 µm/L=30 nm，尾管 W=1 µm，再生 N/P W=500/500 nm。
- 数字路径：原生标准单元；SAR 的 RC、清除管及模拟/升压域电路保留。参考侧采用 CODE + 公共 PRESET + 正反相驱动，取消额外 DFF/MUX、逐位复位/捕获、非交叠发生器及栅极串联电阻。
- 原生标准单元 masters：`DFCNQD1BWP12T30P140`、`INVD1BWP12T30P140`、`ND2D1BWP12T30P140`。

## 时序合同

当前最简版每帧要求 8 次比较与写入，按实际 CODE/栅控及逐位底板建立验证参考状态；参考侧已无捕获电路，不再要求 16 次捕获。新采样取消未完成事件，外部采样关闭沿保持不变。60 ns 是帧内转换分配，不代表硬件有超时检测引脚。历史冻结 B 与 B 行为模型仍有 8 次参考更新、16 次捕获的独立合同。
下表 TT 行为事件间隔取历史 B 十帧原生边沿的中位数，不能作为最简版实测时序。转换预算来自外部低相位，20 ps 输出平滑和算术正则化属于模型设定。cmp→write 包括比较器及数字接收流水，不是纯比较器再生常数。外部高相位为 40 ns，真实 Bootstrap 导通窗仍由内部栅控波形确定。

| 行为间隔 | 配置值/ns |
| --- | ---: |
| `sample_buffer_s` | 0.034436181 |
| `seq_buffer_s` | 0.043999306 |
| `first_compare_s` | 2.640679072 |
| `compare_to_write_s` | 0.382557673 |
| `write_to_update_s` | 0.448310391 |
| `update_to_capture_s` | 0.040319091 |
| `capture_gap_s` | 1.018781827 |
| `capture_to_next_compare_s` | 1.758258883 |
| `comparator_tau_s` | 0.000000000 |
| `conversion_budget_s` | 60.000000000 |
| `transition_s` | 0.020000000 |

该近似未拟合 SS/FF 角，也未包括晶体管局部失配引起的延时分布。真实时序资格由闭环逐位测量确定。模块比较器的 0.75 ns 探针和同 draw 保持差的 0.25 LSB 属于独立诊断 screen，不能代替整帧 deadline 或器件可靠性判据。

## 性能目标与工程误差分配

沿用已有 8-bit 工程目标：−1 dBFS 输入时 ENOB≥7 bit（SNDR≥43.9 dB），无缺码、单调，|DNL|≤1 LSB、端点 |INL|≤1 LSB，功耗预算≤1 mW。这些是工程目标；已完成测量的条件和范围见 [results](../results/README.md)。

| 分配 | RMS/mV |
| --- | ---: |
| 理想量化 | 2.029747 |
| `sampling_noise_rms_lsb` | 1.265625 |
| `comparator_noise_rms_lsb` | 1.265625 |
| `reference_noise_rms_lsb` | 0.843750 |
| `unmodeled_distortion_rms_lsb` | 1.054688 |
| 20 ps、4.5 MHz 抖动 | 0.320738 |

RSS=3.041486 mV，分配投影 SNDR=45.412833 dB、ENOB=7.251301 bit；该 RSS 不是当前 B 版的噪声实测。
CDAC 建立误差分配 0.25 LSB=1.7578125 mV。固定增益、偏置、延迟单列，避免并入随机噪声重复计数。

## 校准、统计与未定项

- 当前未实现校准器。比较器 200 种子极值只给出已观察到的偏移，不定义所有工艺样本的校准范围。校准范围、步进、权重字长尚未选定。
- 历史 0.25 LSB 偏移分配作为暂定校正后残差目标；当前未校准比较器没有被伪称满足这条线。
- 200 种子模块测试与 SS/FF 冷角各 50 种子闭环的抽样范围见 [monte_carlo.json](../specs/monte_carlo.json)。闭环局部失配仅开启比较器和 CDAC。
- 已有 B 版单个 TT 瞬态噪声种子，见 [噪声对照](../results/noise/comparison.json)；带宽和统计收敛尚未建立。全电路局部失配、PEX、完整共模范围、校准范围/精度、功耗积分收敛及端压可靠性仍分别保留未完成项。
- 端压工程判据唯一来源为 [soa_rule.yaml](../specs/soa_rule.yaml)。当前最简版五点短测 比较器五角通过该测量范围，FF 冷 SAR 存储 MM64 Vds 持续时间失败；设计采用不豁免违例，不代表可靠性签核。见 [逐管报告](../results/soa/msb_drive_d2_trial_20261115.md)。

## 行为视图与交叉验证

[Python 模型](../design/behav/python/sar_adc.py) 与 [VA 模型](../design/behav/veriloga/sar_adc_b.va) 共用总规格和生成默认参数。无噪声为默认，支持有效位权、偏移、有限建立和比较停滞等参数。
两模型的随机数流不同；确定性交叉逐例比较，随机噪声仅按各自分布建模。物理启动充电、kickback、原生 PDK MC、端压和功耗需要晶体管级模型。
[行为模型说明](../design/behav/README.md)列出模型层次、旧模型审查和运行方法。
