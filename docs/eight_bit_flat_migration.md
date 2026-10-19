# 8-bit flat 主线迁移与验证

日期：2026-10-19。用户要求把 8-bit 方案补齐到原 10-bit 5+5 主线的
现有成熟度。不是把十位数据裁成八位，也不是重做一套 Bootstrap 拓扑。

## 1. 当前定义与保留边界

- 主线：全差分 8-bit SAR，10 MS/s，VDD=0.9 V，VCM=0.45 V，输入差分
  范围 ±0.9 V；顶板采样、200 MHz bit clock、40/60 ns 采集/转换预算不变。
- CDAC：每侧 `128:64:32:16:8:4:2:1` 加一个 dummy，总计 256Cu；无桥接电容、
  无低位子阵列。Cu=6.86047 fF 只是沿用比较参数，每侧 1.75628032 pF，
  **并未冻结 PDK MOM 单元**。
- ENOB ≥7 是暂定目标，沿用原方案留一位有效位数余量的思路；功耗 ≤1 mW
  目标仍保留，但本次没有完成系统功耗验证。
- `config/design_spec.yaml` 为新默认；`design_spec_10b.yaml` 是修改前的完整
  原始规格。十位 VA、旧 OA 与历史结果保留，不覆盖、不改名冒充八位结果。
- 新噪声与确定性预算见 [error_budget.md](error_budget.md)。新 LSB=7.03125 mV，
  0.25 LSB=1.7578125 mV。20 ps jitter 保留绝对时间，不能随位数简单乘四。

## 2. 已补齐到哪一层

| 阶段 | 方法与本次新证据 | 结论边界 |
| --- | --- | --- |
| 理想算法/静态 | 参数化 Python + ADCToolbox；256 码、每码 8 点 | 2048 点，无缺码，理想 DNL/INL=0 |
| 理想动态 | 16384 点相干正弦，bin 7373，约 4.500122 MHz，−1 dBFS | Python SNDR 48.745771 dB，ENOB 7.804945 |
| 时钟行为级 | 新八位 VA，真实 Spectre 编译/时域仿真 | 两次转换码 192/64，37.5 ns；全静态和动态复测通过 |
| 噪声行为级 | 采样事件/逐次比较中用 `$rdist_normal` 注入 | SNDR 45.882836 dB，ENOB 7.329375，不是 PDK 噪声结果 |
| 一阶模型 | RC 瞬态 + kT/C、再生、jitter 解析约束 | 四组 Spectre RC 对照；慢 RC/过小 C 负例分别失败 |
| 完整电气宏模型 | 实际 flat 电容网络、有限 R/Rref/Cref、再生比较器宏模型、闭环 VA 控制 | 10 个标称/边界点通过，3 组敏感性实验；不是全管级 ADC |
| 开关管级/完整负载 | 原用户 Canvas 拓扑，T28 1.8-V MOS 与物理反相器，接新完整差分 flat CDAC | 0.5 µm 失败，独立 1 µm 副本五点通过 |
| 比较器接口 | 现有真实 T28 StrongARM + native Bootstrap + flat CDAC，时钟开/关对照 | 小输入下判决与 kickback 专项；不是完整管级 SAR |
| 实物 CDAC/参考/后端 | 尚未落地 PDK 电容阵列、参考选择开关/缓冲器、数字实现与版图 | 仍是后续工作，未被这次迁移“自动完成” |

行为级相干正弦比较：Spectre VA 理想动态 SNDR=48.745920 dB，
ENOB=7.804970，SFDR=67.053527 dB；全部 16384 个码与按相同采样时刻
计算的 Python 结果逐码一致。静态 VA 同样覆盖 256 码、2048 点、无缺码。

噪声 VA 的三个源分别为 1.265625/1.265625/0.84375 mV RMS，保留原事件注入
机制和固定种子，不在最终数字码上加噪声。3798 个码相对于理想动态记录发生
变化；部分 RSS 预测为 46.024475 dB，与仿真相差约 −0.142 dB。该实验没有
加入采样时刻 jitter 或“未建模失真”，也不证明物理噪声独立/白噪声假设成立。

## 3. 一阶约束和完整宏模型

在 27 °C，Cside=1.75628032 pF：

- 差分 `sqrt(2kT/C)` ≈0.068696 mV，小于采样噪声分配；这是公式估算，
  不包含开关额外噪声、前端噪声或失配。
- 对最坏 1.8 V 差分台阶，3 ns 内残差 <0.25 LSB，单极点
  Rtotal 上限约 246.435 Ω。新分配 Rbottom=150 Ω、Rref=50 Ω、Cref=4 pF；
  它们是宏模型设计参数，不是已实现的晶体管测量值。
- R=200 Ω 的 Spectre 一阶差分残差 0.351449 mV，解析值 0.351609 mV。
  R=400 Ω 对照约 25.1559 mV，明确失败。Cu=0.01 fF 的小 C 对照虽然
  建立快，但差分 kT/C≈1.79931 mV，超过采样预算。
- 40 ns、同一残差要求下的一阶采集总电阻上限约 3.286 kΩ；
  真实 Bootstrap 不用常数 Ron 代替验证。
- 对假设 Cnode=20 fF、1.5 ns、0.45 V 输出判决门限，输入为 0.25 LSB 时，
  `C/t*ln(Vout/Vin)` 给出 gm_eff≈73.94 µS 的一阶再生要求。
  不是对现有 StrongARM 的 gm 拟合或噪声/offset 签核。

宏模型 6 个码中心（16、64、127、128、192、239）和 4 个 major-carry/中点
边界邻近输入全部通过八次电气判决。每次判决前 20 ps 读取顶板差分，逐次
对照电荷守恒 oracle；所有标称判决方向正确、锁存前输出差分 ≥0.45 V。
最坏建立残差 0.003207 LSB，转换约 39.52 ns。参考端瞬态偏移可达约
85 mV，不能用该峰值直接代替判决时的残差；参考供电仍要按脉冲电流设计。

敏感性实验：

- Rref=500 Ω、Rbottom=1800 Ω：仍可能得到正确的最终码，但建立残差
  4.40758 LSB，判定失败。**只看最终码会漏掉问题**。
- 顶板到 VCM 每侧 5 fF 寄生：用 `Vin − αVDAC`、
  `α=256Cu/(256Cu+Cpar)` 的新 oracle 对照，单点通过。
  这体现 DAC 步幅衰减/增益变化，不证明完整 INL 已过关。
- kickback 宏模型电容从每侧 0.05 fF 增到 1 fF：最大残差升至
  0.054574 LSB，单点仍过关；不是实际比较器 kickback 的替代品。

此闭环台的采样宏模型沿用原有限 R 理想开关，输入从 DC 工作点开始已建立，
因此不能用它证明一次动态输入翻转后的 40 ns 采集性能。该项由下面的管级
Bootstrap 输入翻转测试独立验证。

## 4. Bootstrap：原拓扑保留，只为新负载调主开关尺寸

新 native 副本 `sar_bootstrap_canvas_flat_8b` 从只读
`sar_bootstrap_canvas_cdac_t28` 复制。12 个 MOS 均为实际 `tsmcN28`
`nch_18_mac/pch_18_mac`；保留 Cboot=1 pF、物理两管反相器、全部连接。
Mmain 从 W=0.5 µm 调为 **1 µm**，L=150 nm、nf=multi=1；其余 11 管仍
W=1 µm、L=150 nm。CDF 的面积/周长随宽度正常更新；没有更换自举机制。
1 µm 已通过当前五点门限，所以没有继续跑无必要的 2 µm 版本。

比较台的两条独立路径，各接一套相同新 flat 差分 CDAC。原方案
`sar_bootstrap` 不变；两路各自独立输入源、每侧 50 Ω；0.9 V/0.45 V、
205 ns 输入翻转、PHI 211 ns 上升和 250.1 ns 下降，边沿均 100 ps。
底板采集时在 VCM，BASE 在 252 ns 开始回接 VCM，检查时刻 270 ns。
本台 VREFP/VREFN 均接 VCM，只测采样/保持，不执行 SAR 转换。

| Vdiff (V) | native 0.5 µm 采集误差 (mV) | native 0.5 µm 保持误差 (mV) | native 1 µm 采集误差 (mV) | native 1 µm 保持误差 (mV) |
| ---: | ---: | ---: | ---: | ---: |
| −0.8 | +12.910475 | +12.593497 | +0.031228 | +0.126413 |
| −0.4 | +2.734593 | +2.686154 | +0.009434 | +0.058773 |
| 0 | ≈0 | ≈0 | ≈0 | ≈0 |
| +0.4 | −2.734593 | −2.686154 | −0.009434 | −0.058773 |
| +0.8 | −12.910475 | −12.593497 | −0.031228 | −0.126413 |

采集误差在 249.9 ns 读取；保持误差是
`(TOPP−TOPN)−Vdiff_target`，没有拟合增益/去掉 offset/扣除误差。
1 µm 的五点均低于 ±1.7578125 mV；最坏保持误差约 0.01798 LSB。
原 core Bootstrap 的最坏保持误差约 0.219363 mV，但仍有核心管 SOA
warnings，不能因它满足电压误差指标就将其选为合格器件方案。

0.5 µm 的主要问题已在采集末尾存在，是较大 flat 负载的充电不足，
不是在最终数字输出上凭空产生的误差。增加 W 后导通能力提高；关断馈通和
电荷注入也会变化，所以同时重新测保持值，而不是只计算一个 Ron。

图由真实结果生成，包含理想零误差基准、±0.25 LSB 色带、图例和保持窗口：

- `output/eight_bit_flat/figures/bootstrap_timing.png`
- `output/eight_bit_flat/figures/bootstrap_size_screen.png`
- `output/eight_bit_flat/figures/macro_conversion.png`

时序图的灰色区从底板回接完成后约 252.15 ns 开始，是已进入保持、可用于
后续转换的观察窗口。250.1–252.1 ns 属于关断/底板回接过渡，图中的暂态
顶板偏移不能直接当作 270 ns 的保持误差。采样开关关断后电荷已开始保存，
但 reference handoff 完成之前节点还没到最终比较基准。

### 精度、warning 与真实比较器接口

选定 1 µm 在 ±0.8 V 下用 maxstep=5 ps、reltol=2e-6 复测，保持误差与
主比较相差最多 **0.00845 µV**。移除旧支路的 candidate-only 诊断与主比较
相差约 0.00362 µV，两次诊断均为零 CMI、零 suppressed warnings，仍各有
4 条继承的 SFE-1131 模型参数 warnings。旧支路有大量 SOA 警告及 suppression，
所以必须单独跑候选路径，不能从配对台“没打印新管警告”推断候选安全。

主开关在选定五点、210.8–251 ns 窗口内保存的端间峰值：
|Vgs|≤0.96108 V，|Vgd|≤1.59345 V，|Vgb|≤1.75220 V。
这是主开关的名义时域端间审计，不是全部 MOS 的可靠性或 foundry SOA 签核；
也不能用“绝对栅压高于 0.9 V”直接判定 1.8-V 管违规。

真实比较器接口用选定 1 µm Bootstrap、相同 flat CDAC 和既有
`sar_strongarm_t28`，每输出负载 5 fF。输入 −0.25 LSB、0、+0.25 LSB
各跑比较器时钟禁用/启用两组，255 ns 发起比较。非零小输入下，1.5 ns
时输出差分达到约 ±0.899951 V，方向均正确。比较前差分保持误差约
±0.000267 mV。开钟减去关钟的差分 kickback 峰值在非零输入下约
0.050848 mV，连零差分诊断在内最大 **0.051338 mV**；1.5 ns 时非零输入
残留约 ±0.000308 mV。六次运行均零 CMI/suppressed、各 4 条 SFE-1131。

零差分时最终落在哪一侧由数值微小不对称决定，不把它当成失配或 offset
测量。本接口没有参考逐位切换、没有数字闭环、没有真实 comparator noise，
因此不是“全管级 8-bit ADC 已通过”。原 0.5 µm 接口六组也保留，用于区分
小输入接口可用与满量程动态采集失败这两件不同的事。

## 5. OA 与仿真对应关系

远端库仍是 `/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28`，
technology `tsmcN28`，没有新建第二层项目或修改 PDK。

| 新 cell | 实际 view/性质 |
| --- | --- |
| `sar_cdac_flat_8b` | schematic/symbol；18 个电容组、52 个 relay，显式 dummy |
| `sar_macro_controller_8b` | symbol/veriloga；无浮空 schematic 占位图 |
| `sar_comparator_macro_8b` | schematic/symbol；独立宏模型副本，参数化 kickback |
| `tb_sar_macro_flat_8b` | schematic；完整八位电气闭环 |
| `sar_bootstrap_canvas_flat_8b` | schematic/symbol；原拓扑 T28 管级尺寸副本 |
| `tb_bootstrap_flat_8b` | schematic；旧方案/native 配对的完整 flat-CDAC 负载 |
| `tb_cdac_strongarm_flat_8b` | schematic；真实 StrongARM 接口专项 |

电气 schematic 均经 API readback、Check & Save 零 markers、OA 原样网表
导出后仿真。主比较只改顶层设计变量/精度/保存项/analysis，不手工改 DUT
接线。最终保存的 OA 再导出，与主仿真对应原始导出比较（忽略生成时间）。
全部六个只读依赖的实例/参数/位置/API readback 前后相同。
八位 controller 远端 VA 与本地源码逐字节核对。

数值环境：bridge 0.8.0，Spectre 21.1.0.509、基础 Spectre 模式、TT、27 °C。
PDK include 使用项目既有 embedded-usage 文件及 `pre_simu`、`noise_worst`、
`ttmacro_mos_moscap`、`tt_res_bip_dio_disres`、`tt_mom`、`tt_ind_jvar`、
`tt_r_metal` sections。include 中有 `noise_worst` 不等于启用了 transient noise。
原始日志/PSF/精确命令、唯一结果目录和输入 SHA256 均在对应 `_result.json`
及 `output/eight_bit_flat/spectre/`，不将专有模型或 OA 数据提交到 Git。

此次共 **49 次 result.ok 的 Spectre 运行**：4 VA、4 RC、13 电气闭环、
16 Bootstrap（含尺寸/单支路诊断/精度）、12 真实比较器接口。
`result.ok` 表示求解完成，不表示每个电路指标都通过；0.5 µm 采集和
慢 reference 等预设失败对照已按指标判为失败。
`scripts/eight_bit/audit_evidence.py` 核验这组固定实验的实际日志版本、
49 个 deck SHA256、结果目录、正负门限、精度和 OA 对应关系，写出
`output/eight_bit_flat/final_manifest.json`。

主仿真对应原始 OA 网表 SHA256（不提交网表内容）：

| Cell / tag | SHA256 |
| --- | --- |
| `tb_sar_macro_flat_8b / initial` | `4b0f3e21872a219f41290d31347fbec81c1c3c6288a96b543ebe3e07a5e02a38` |
| `tb_bootstrap_flat_8b / w1u` | `ca8a552d0811a6265114a274a8981a0eb87d280bd514651fb374fac9c19a08cd` |
| `tb_cdac_strongarm_flat_8b / w1u` | `64f7c1f6774599794936fc6b13e8d99e4b43f56ebdd2d3cf58e1315f044923f5` |

## 6. 源码和复现入口

```text
config/design_spec.yaml                 当前 8-bit 主规格
config/design_spec_10b.yaml              完整保留的 10-bit 规格
config/eight_bit_flat.yaml               电气负载、时序、门限与选定尺寸
models/veriloga/sar_adc_ideal_8b.va       理想/事件噪声时钟模型
models/veriloga/sar_macro_controller_8b.va 八位闭环控制
scripts/eight_bit/common.py              数据、来源与 Spectre 批量运行
scripts/eight_bit/build_oa.py            新 OA 创建、读回、导出、最终一致性
scripts/eight_bit/run_veriloga.py        4 组 VA Spectre 实验
scripts/eight_bit/run_electrical.py      RC/闭环/Bootstrap/真实比较器接口
scripts/eight_bit/analyze.py             电荷 oracle、判决/误差/日志门限
scripts/eight_bit/plot_results.py        数据驱动科学时序/对比图
scripts/eight_bit/audit_evidence.py      固定 49 次实验的完整证据门限
verification/eight_bit/test_migration.py 聚焦回归
```

本地分析使用项目 `.venv/Scripts/python.exe`；bridge/Spectre 使用
`E:/bridge-Agent-T28/virtuoso-bridge-lite/.venv/Scripts/python.exe`，
并设置进程内 `VB_DISABLE_CONTROL_MASTER=1`。例：

```powershell
.venv/Scripts/python.exe scripts/analysis/run_behavioral_baseline.py
# 以下 python 指 workspace bridge venv，连接 t28_io，运行真实远端 Spectre
python scripts/eight_bit/run_veriloga.py
python scripts/eight_bit/run_electrical.py first-order
python scripts/eight_bit/run_electrical.py macro
python scripts/eight_bit/run_electrical.py bootstrap --tag w1u
python scripts/eight_bit/run_electrical.py comparator --tag w1u
.venv/Scripts/python.exe scripts/eight_bit/analyze.py va
.venv/Scripts/python.exe scripts/eight_bit/analyze.py local
.venv/Scripts/python.exe scripts/eight_bit/analyze.py macro
.venv/Scripts/python.exe scripts/eight_bit/analyze.py bootstrap --tag w1u
.venv/Scripts/python.exe scripts/eight_bit/analyze.py comparator --tag w1u
.venv/Scripts/python.exe scripts/eight_bit/analyze.py candidate-only --tag w1u
.venv/Scripts/python.exe scripts/eight_bit/analyze.py bootstrap --tag w1u_tight
.venv/Scripts/python.exe scripts/eight_bit/audit_evidence.py
.venv/Scripts/python.exe scripts/eight_bit/plot_results.py --tag w1u
.venv/Scripts/python.exe verification/eight_bit/test_migration.py -v
.venv/Scripts/python.exe verification/system/test_behavioral_baseline.py -v
```

OA 构建器会拒绝覆盖已有目标/原始导出，不能把上述分析重跑与“重建 OA”混为
一谈。尺寸修改仅针对明确属于八位迁移的独立副本；用户未保存窗口会阻止修改。
旧十位系统回归和旧噪声 runner 已显式指向历史 spec，避免无意套用新门限。
现有 `review/` 交互审查台明确冻结为十位历史图表，绑定旧 spec；没有把旧
0.439-mV 证据悄悄改用八位门限。八位审查入口为本报告及新时序图，交互图谱
重编不属于本次电路迁移；两个已变化报告的指纹仍保留“需复核”提示，不批量
接受历史记录。其构建检查和直接相关的 23 个测试通过。

## 7. 下一设计落点与未完成项目

下一主线是 **8-bit flat CDAC 的 PDK 器件实现**：选 MOM、确定实际 Cu 与
单位阵列/匹配/寄生，再实现 reference selection switch 与 reference 驱动；
按新实际负载重新验证采样开关和比较器接口。1 µm 是当前固定比较电容下的
标称候选尺寸，不是最终面积/能耗最优点。

尚未完成：全量电气/全管级 ADC 静态动态、完整参考缓冲器/数字时钟与 SAR
电路、全器件可靠性、PVT、Monte Carlo、物理噪声、功耗、布局布线、DRC/LVS
及 PEX。旧 PDK 单管参数仍可作为初值，不需要因 N 从 10 变 8 就重测工艺库；
但不能把旧负载下的模块通过结论照搬成新负载通过。
